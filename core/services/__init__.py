"""
外部服务模块

包含推送服务、图片生成等外部依赖服务。
"""

from .gotify import push_gotify
from .image_generator import StatisticsImageGenerator

__all__ = ['push_gotify', 'StatisticsImageGenerator'] 