import base64
import aiohttp
from typing import Tuple, Optional

from src.llm_models.utils_model import LLMRequest
from src.common.logger import get_logger
from src.plugin_system.apis import llm_api, person_api
from .models import get_avatar_description, set_avatar_description

logger = get_logger("avatar_analyzer")


class AvatarAnalyzer:
    """头像分析器
    
    负责获取用户头像、使用视觉模型分析并存储结果
    """

    def __init__(self):
        """初始化分析器"""
        self.default_prompt = (
            "这是一个用户的QQ头像，请根据图片内容分析并描述：\n"
            "1. 如果是真人照片，描述其大致特征和风格\n"
            "2. 如果是动漫/卡通形象，描述角色特点\n"
            "3. 如果是风景/物品，描述图片主题\n"
            "请用简洁的语言（50字内）总结这个头像给人的印象。"
        )

    async def analyze_and_store(
        self,
        user_id: str,
        platform: str,
        force_update: bool = False,
        custom_prompt: Optional[str] = None
    ) -> Tuple[bool, str]:
        """分析用户头像并存储到数据库
        
        Args:
            user_id: 用户ID
            platform: 平台类型
            force_update: 是否强制更新已有描述
            custom_prompt: 自定义分析提示词
            
        Returns:
            Tuple[bool, str]: (是否成功, 分析结果或错误信息)
        """
        # 1. 检查是否已有描述
        if not force_update:
            existing = await self._get_existing_description(user_id, platform)
            if existing:
                logger.info(f"用户 {user_id} 已有头像描述，跳过分析")
                return True, existing

        # 2. 获取头像
        avatar_data = await self._fetch_avatar(user_id, platform)
        if not avatar_data:
            return False, "无法获取用户头像"

        try:

            # 3. 使用视觉模型分析
            description = await self._analyze_avatar(avatar_data, custom_prompt)
            if not description:
                return False, "头像分析失败"

            # 4. 存储到数据库
            success = await self._store_description(user_id, platform, description)
            if not success:
                return False, "存储描述失败"

            logger.info(f"用户 {user_id} 头像分析完成: {description[:30]}...")
            return True, description

        except Exception as e:
            logger.error(f"分析头像失败: {e}", exc_info=True)
            return False, str(e)

    async def _get_existing_description(
        self,
        user_id: str,
        platform: str
    ) -> Optional[str]:
        """获取已有的头像描述
        
        Args:
            user_id: 用户ID
            platform: 平台类型
            
        Returns:
            已有描述，不存在返回None
        """
        try:
            # 使用person_api获取person_id，然后从插件数据库查询
            person_id = person_api.get_person_id(platform, user_id)
            if not person_id:
                logger.warning(f"无法获取用户 {user_id} 的person_id")
                return None

            # 从插件的avatar_descriptions表查询
            description = get_avatar_description(person_id)
            if description:
                logger.debug(f"用户 {user_id} 已有头像描述: {description[:30]}...")
            return description
        except Exception as e:
            logger.error(f"查询头像描述失败: {e}")
            return None

    async def _fetch_avatar(
        self,
        user_id: str,
        platform: str
    ) -> Optional[bytes]:
        """获取用户头像

        Args:
            user_id: 用户ID
            platform: 平台类型

        Returns:
            头像图片数据，失败返回None
        """
        try:
            if platform == "discord":
                # TODO: 使用Discord API获取头像
                return None

            if platform == "qq":

                url = f"http://q.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640&img_type=jpg"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.read()
                        else:
                            logger.error(f"获取QQ头像失败: {response.status}")
                            return None
            else:
                logger.warning(f"暂不支持平台 {platform} 的头像获取")
                return None

        except Exception as e:
            logger.error(f"获取头像失败: {e}", exc_info=True)
            return None

    async def _analyze_avatar(
        self,
        avatar_data: bytes,
        custom_prompt: Optional[str] = None
    ) -> Optional[str]:
        """使用视觉模型分析头像
        
        Args:
            avatar_data: 头像图片数据
            custom_prompt: 自定义提示词
            
        Returns:
            分析结果，失败返回None
        """
        try:
            # 将图片转为base64
            image_base64 = base64.b64encode(avatar_data).decode()

            # 构建提示词
            prompt = custom_prompt or self.default_prompt

            # 获取视觉模型配置
            models = llm_api.get_available_models()
            vision_model = models.get("vision_general")

            if not vision_model:
                logger.warning("未找到vision_general模型配置，使用默认描述")
                return "使用默认头像或无法分析的头像图片"

            llm_request = LLMRequest(
                model_set=vision_model,
                request_type="avatar_analysis"
            )

            # 调用图像分析方法
            response, _ = await llm_request.generate_response_for_image(
                prompt=prompt,
                image_base64=image_base64,
                image_format="jpeg"
            )

            if response:
                logger.info(f"头像分析成功: {response[:50]}...")
                return response.strip()
            else:
                logger.warning("视觉模型返回空响应，使用默认描述")
                return "使用默认头像或无法分析的头像图片"

        except Exception as e:
            logger.warning(f"调用视觉模型失败: {e}，使用默认描述")
            return "使用默认头像或无法分析的头像图片"

    async def _store_description(
        self,
        user_id: str,
        platform: str,
        description: str
    ) -> bool:
        """存储头像描述到数据库
        
        Args:
            user_id: 用户ID
            platform: 平台类型
            description: 头像描述
            
        Returns:
            是否成功
        """
        try:
            # 使用person_api获取person_id
            person_id = person_api.get_person_id(platform, user_id)
            if not person_id:
                logger.error(f"无法获取用户 {user_id} 的person_id")
                return False

            # 存储到插件的avatar_descriptions表
            success = set_avatar_description(
                person_id=person_id,
                platform=platform,
                user_id=user_id,
                description=description
            )

            if success:
                logger.info(f"成功存储用户 {user_id} 的头像描述: {description[:30]}...")

            return True

        except Exception as e:
            logger.error(f"存储头像描述失败: {e}", exc_info=True)
            return False
