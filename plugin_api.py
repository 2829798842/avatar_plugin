from typing import Optional
from src.common.logger import get_logger
from .models import get_avatar_description

logger = get_logger("qq_avatar_meme.api")


def get_head_description_for_prompt(person_id: str) -> Optional[str]:
    """获取用于prompt的头像印象
    
    这个函数可以被MaiBot的prompt构建系统调用，
    用于在对话上下文中添加用户的头像印象信息。
    
    Args:
        person_id: 用户的person_id

    """
    try:
        description = get_avatar_description(person_id)
        if description:
            logger.debug(f"为person_id={person_id}获取头像印象: {description[:30]}...")
        return description
    except Exception as e:
        logger.error(f"获取头像印象失败: person_id={person_id}, error={e}")
        return None


def format_head_description_for_relation(head_description: str) -> str:
    """格式化头像描述用于关系信息
    
    Args:
        head_description: 原始头像描述
        
    Returns:
        格式化后的描述，适合添加到relation_info中
    """
    if not head_description:
        return ""

    # 简单格式化，可根据需要调整
    return f"ta的头像印象：{head_description}"


# 导出便捷函数
__all__ = [
    'get_head_description_for_prompt',
    'format_head_description_for_relation',
]
