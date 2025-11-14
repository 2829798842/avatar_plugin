import time
from peewee import Model, TextField, FloatField
from src.common.database.database import db
from src.common.logger import get_logger

logger = get_logger("qq_avatar_meme.models")


class AvatarDescription(Model):
    """头像描述表
    
    存储用户头像的分析描述，与PersonInfo通过person_id关联
    """

    person_id = TextField(unique=True, index=True)  # 关联PersonInfo的person_id
    platform = TextField(index=True)  # 平台名称
    user_id = TextField(index=True)  # 用户ID
    head_description = TextField(null=True)  # 头像描述
    analyzed_at = FloatField(null=True)  # 分析时间戳
    avatar_url = TextField(null=True)  # 头像URL

    class Meta:
        database = db
        table_name = "avatar_descriptions"


def create_tables():
    """创建插件所需的数据库表"""
    try:
        db.create_tables([AvatarDescription], safe=True)
        logger.info("成功创建avatar_descriptions表")
        return True
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False


def get_avatar_description(person_id: str) -> str:
    """获取头像描述
    
    Args:
        person_id: 用户的person_id
        
    Returns:
        头像描述，不存在返回None
    """
    try:
        record = AvatarDescription.get_or_none(AvatarDescription.person_id == person_id)
        return record.head_description if record else None
    except Exception as e:
        logger.error(f"查询头像描述失败: {e}")
        return None


def set_avatar_description(person_id: str, platform: str, user_id: str, description: str, avatar_url: str = None) -> bool:
    """设置头像描述
    
    Args:
        person_id: 用户的person_id
        platform: 平台名称
        user_id: 用户ID
        description: 头像描述
        avatar_url: 头像URL（可选）
        
    Returns:
        是否成功
    """
    try:


        record = AvatarDescription.get_or_none(AvatarDescription.person_id == person_id)

        if record:
            # 更新现有记录
            record.head_description = description
            record.analyzed_at = time.time()
            if avatar_url:
                record.avatar_url = avatar_url
            record.save()
            logger.debug(f"更新头像描述: {person_id}")
        else:
            # 创建新记录
            AvatarDescription.create(
                person_id=person_id,
                platform=platform,
                user_id=user_id,
                head_description=description,
                analyzed_at=time.time(),
                avatar_url=avatar_url
            )
            logger.debug(f"创建头像描述: {person_id}")

        return True
    except Exception as e:
        logger.error(f"设置头像描述失败: {e}", exc_info=True)
        return False
