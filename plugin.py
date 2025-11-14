import base64
import random
import subprocess
import sys
from typing import List, Tuple, Type, Optional

from src.plugin_system import (
    BasePlugin,
    register_plugin,
    BaseAction,
    BaseCommand,
    ComponentInfo,
    ActionActivationType,
    ConfigField,
    PythonDependency,
)
from src.common.logger import get_logger

from .avatar_analyzer import AvatarAnalyzer

logger = get_logger("qq_avatar_meme")


def check_and_install_dependency():
    """检查并安装 meme-generator 依赖"""
    try:
        import meme_generator
        return True
    except ImportError:
        logger.info("未找到 meme-generator，正在自动安装...")

        # 检查是否有 uv
        has_uv = False
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            has_uv = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            has_uv = False

        # 根据是否有 uv 选择安装方式
        try:
            if has_uv:
                logger.info("使用 uv pip 安装 meme-generator...")
                subprocess.check_call(
                    ["uv", "pip", "install", "meme-generator"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                logger.info("使用 pip 安装 meme-generator...")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "meme-generator"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            logger.info("meme-generator 安装成功")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"安装 meme-generator 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"安装过程出错: {e}")
            return False



get_memes = None
load_memes = None
memes_dir = None




class MemeManager:
    """表情包管理器"""

    _instance = None
    _memes = {}
    _meme_list = []
    is_initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not MemeManager.is_initialized:
            self._load_memes()

    def _load_memes(self):
        # 首次初始化时检查并加载依赖
        if not self._check_and_load_meme_generator():
            logger.warning("meme-generator未安装或加载失败，表情包功能不可用")
            return

        try:
            load_memes(memes_dir())
            all_memes = get_memes()

            for meme in all_memes:
                MemeManager._memes[meme.key] = meme
                for keyword in meme.keywords:
                    MemeManager._memes[keyword.lower()] = meme

            MemeManager._meme_list = all_memes
            MemeManager.is_initialized = True
            logger.info(f"已加载 {len(all_memes)} 个表情包")
        except Exception as e:
            logger.error(f"加载表情包失败: {e}")

    def find_meme(self, key: str):
        if not self.is_initialized:
            return None
        key_lower = key.lower()
        if key_lower in self._memes:
            return self._memes[key_lower]
        for meme_key, meme in self._memes.items():
            if key_lower in meme_key:
                return meme
        return None

    def get_all_memes(self):
        return self._meme_list if self.is_initialized else []

    def get_random_meme(self):
        if not self.is_initialized or not self._meme_list:
            return None
        return random.choice(self._meme_list)

    @classmethod
    def _check_and_load_meme_generator(cls):
        """检查并加载meme_generator模块"""
        global get_memes, load_memes, memes_dir

        # 如果已经加载过，直接返回
        if get_memes is not None:
            return True

        # 尝试导入
        try:
            from meme_generator import get_memes as _get_memes
            from meme_generator.manager import load_memes as _load_memes
            from meme_generator.dirs import memes_dir as _memes_dir

            get_memes = _get_memes
            load_memes = _load_memes
            memes_dir = _memes_dir
            return True
        except ImportError:
            # 尝试安装
            if check_and_install_dependency():
                try:
                    from meme_generator import get_memes as _get_memes
                    from meme_generator.manager import load_memes as _load_memes
                    from meme_generator.dirs import memes_dir as _memes_dir

                    get_memes = _get_memes
                    load_memes = _load_memes
                    memes_dir = _memes_dir
                    return True
                except ImportError:
                    return False
            return False

    async def generate(self, meme, images=None, texts=None, args=None):
        try:
            return meme(images=images or [], texts=texts or [], args=args or {})
        except Exception as e:
            logger.error(f"生成表情包失败: {e}")
            return None


def init_plugin_database():
    try:
        from .models import create_tables
        return create_tables()
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        return False


init_plugin_database()


class MemeMenuCommand(BaseCommand):
    command_name = "meme_menu"
    command_description = "查看所有可用的表情包列表"
    command_pattern = r"^/menu\s*$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        meme_mgr = MemeManager.get_instance()
        if not meme_mgr.is_initialized:
            await self.send_text("表情包功能未启用，请安装: pip install meme-generator")
            return False, "未安装meme-generator", True

        enabled_memes = meme_mgr.get_all_memes()
        if not enabled_memes:
            await self.send_text("当前没有可用的表情包")
            return True, "无可用表情包", True

        menu_lines = ["表情包菜单", "", "使用: /meme <名称> [文字]", ""]

        categories = {}
        for meme in enabled_memes[:50]:
            tag = list(meme.tags)[0] if meme.tags else "其他"
            if tag not in categories:
                categories[tag] = []
            keywords = "、".join(meme.keywords[:2]) if meme.keywords else meme.key
            categories[tag].append(keywords)

        for category, memes in categories.items():
            menu_lines.append(f"[{category}]")
            menu_lines.append(", ".join(memes[:10]))
            menu_lines.append("")

        menu_lines.append(f"共{len(enabled_memes)}个可用")
        await self.send_text("\n".join(menu_lines))
        return True, "菜单已发送", True


class MemeGenerateCommand(BaseCommand):
    command_name = "meme_generate"
    command_description = "生成指定的表情包"
    command_pattern = r"^/meme\s+(?P<meme_key>\S+)(?P<params>.*)?$"

    async def execute(self) -> Tuple[bool, Optional[str], bool]:
        meme_mgr = MemeManager.get_instance()
        if not meme_mgr.is_initialized:
            await self.send_text("表情包功能未启用")
            return False, "未安装meme-generator", True

        meme_key = self.matched_groups.get("meme_key", "").strip()
        params_str = self.matched_groups.get("params", "").strip()

        meme = meme_mgr.find_meme(meme_key)
        if not meme:
            await self.send_text(f"未找到表情包: {meme_key}\n使用 /menu 查看可用表情包")
            return False, f"未找到: {meme_key}", True

        texts = params_str.split() if params_str else []
        result = await meme_mgr.generate(meme, texts=texts)

        if result:
            image_base64 = base64.b64encode(result.getvalue()).decode()
            await self.send_image(image_base64)
            return True, f"已生成{meme_key}", True
        else:
            await self.send_text("生成失败")
            return False, "生成失败", True


class AutoMemeAction(BaseAction):
    action_name = "auto_meme"
    action_description = "智能选择并生成表情包发送"
    activation_type = ActionActivationType.RANDOM
    random_activation_probability = 0.15

    action_parameters = {
        "meme_key": "表情包名称或关键词",
        "texts": "表情包文字内容",
    }

    action_require = [
        "需要以幽默方式回应时",
        "想表达情绪但文字不够生动时",
    ]

    associated_types = ["image"]
    parallel_action = False

    async def execute(self) -> Tuple[bool, str]:
        meme_mgr = MemeManager.get_instance()
        if not meme_mgr.is_initialized:
            return False, "未安装meme-generator"

        meme_key = self.action_data.get("meme_key", "")
        texts = self.action_data.get("texts", [])

        if not isinstance(texts, list):
            texts = [str(texts)] if texts else []

        meme = meme_mgr.find_meme(meme_key) if meme_key else meme_mgr.get_random_meme()
        if not meme:
            return False, "没有可用的表情包"

        result = await meme_mgr.generate(meme, texts=texts)

        if result:
            image_base64 = base64.b64encode(result.getvalue()).decode()
            await self.send_image(image_base64)
            return True, f"发送了表情包: {meme.key}"
        else:
            return False, "生成失败"


class AnalyzeAvatarAction(BaseAction):
    action_name = "analyze_avatar"
    action_description = "分析用户头像并存储描述信息"
    activation_type = ActionActivationType.NEVER

    action_parameters = {
        "user_id": "要分析头像的用户ID",
        "force_update": "是否强制更新已有描述",
    }

    action_require = ["需要了解用户头像信息时"]
    associated_types = []

    async def execute(self) -> Tuple[bool, str]:
        try:


            user_id = self.action_data.get("user_id") or self.user_id
            force_update = self.action_data.get("force_update", False)

            if not user_id:
                return False, "缺少用户ID"

            analyzer = AvatarAnalyzer()
            success, description = await analyzer.analyze_and_store(
                user_id=user_id,
                platform=self.platform,
                force_update=force_update
            )

            if success:
                return True, f"头像分析完成: {description[:50]}..."
            else:
                return False, "头像分析失败"
        except Exception as e:
            logger.error(f"头像分析失败: {e}")
            return False, f"分析失败: {e}"


@register_plugin
class QQAvatarMemePlugin(BasePlugin):
    plugin_name = "qq_avatar_meme"
    enable_plugin = True
    dependencies = []

    python_dependencies = [
        PythonDependency(
            package_name="meme-generator",
            version=">=0.1.0",
            optional=False,
            description="表情包生成核心库"
        ),
    ]

    config_file_name = "config.toml"

    config_section_descriptions = {
        "plugin": "插件基本配置",
        "meme": "表情包生成配置",
        "avatar": "头像分析配置",
    }

    config_schema = {
        "plugin": {
            "enabled": ConfigField(
                type=bool,
                default=True,
                description="是否启用插件"
            ),
        },
        "meme": {
            "enable_command_mode": ConfigField(
                type=bool,
                default=True,
                description="是否启用命令模式"
            ),
            "enable_action_mode": ConfigField(
                type=bool,
                default=True,
                description="是否启用Action模式"
            ),
        },
        "avatar": {
            "enable_analysis": ConfigField(
                type=bool,
                default=True,
                description="是否启用头像分析功能"
            ),
            "analysis_prompt": ConfigField(
                type=str,
                default="分析这个QQ头像，简洁描述图片内容（50字内）",
                description="头像分析提示词"
            ),
        },
    }

    def get_plugin_components(self) -> List[Tuple[ComponentInfo, Type]]:
        components = []

        if self.get_config("meme.enable_command_mode", True):
            components.append((MemeMenuCommand.get_command_info(), MemeMenuCommand))
            components.append((MemeGenerateCommand.get_command_info(), MemeGenerateCommand))

        if self.get_config("meme.enable_action_mode", True):
            components.append((AutoMemeAction.get_action_info(), AutoMemeAction))

        if self.get_config("avatar.enable_analysis", True):
            components.append((AnalyzeAvatarAction.get_action_info(), AnalyzeAvatarAction))

        return components
