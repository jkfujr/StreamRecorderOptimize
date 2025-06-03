# core/processors/__init__.py

"""
处理器模块包

包含所有文件处理器的基类和具体实现。
"""

from .base_processor import BaseProcessor
from .folder_processor import FolderProcessor

__all__ = ['BaseProcessor', 'FolderProcessor'] 