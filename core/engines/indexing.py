"""
文件夹索引模块

提供统一的文件夹索引和分组功能，支持不同的分组策略。
"""

import os
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, List, Optional, Iterator
from datetime import timedelta

from .time_utils import TimeParser, FolderInfo
from .flv_manager import FlvFileManager


class BaseFolderIndexer(ABC):
    """
    通用文件夹索引基类
    
    定义了文件夹扫描、解析和分组的通用流程，
    子类只需实现具体的分组策略。
    """
    
    def __init__(self, flv_manager: FlvFileManager):
        """
        初始化索引器
        
        参数:
            flv_manager (FlvFileManager): FLV文件管理器实例
        """
        self.flv_manager = flv_manager
        self.groups = defaultdict(list)  # {group_key: [FolderInfo, ...]}
        self.skipped_folders = []  # 跳过的文件夹列表
    
    @abstractmethod
    def get_grouping_key(self, folder_info: FolderInfo) -> Any:
        """
        获取分组键，由子类实现
        
        参数:
            folder_info (FolderInfo): 文件夹信息
            
        返回:
            Any: 分组键
        """
        pass
    
    def scan_and_index(self, folder_path: str) -> Dict[Any, List[FolderInfo]]:
        """
        扫描文件夹并构建索引
        
        参数:
            folder_path (str): 要扫描的文件夹路径
            
        返回:
            Dict[Any, List[FolderInfo]]: 分组后的文件夹信息
        """
        self.groups.clear()
        self.skipped_folders.clear()
        
        if not os.path.exists(folder_path):
            logging.warning(f"[Indexer] 文件夹不存在: {folder_path}")
            return self.groups
        
        logging.debug(f"[Indexer] 开始扫描文件夹: {folder_path}")
        folder_count = 0
        
        for folder_info in self._iterate_folders(folder_path):
            folder_count += 1
            
            # 获取分组键
            group_key = self.get_grouping_key(folder_info)
            
            if group_key is not None:
                self.groups[group_key].append(folder_info)
            else:
                self.skipped_folders.append(folder_info)
        
        # 对每组内的文件夹按时间排序
        for group_key in self.groups:
            self.groups[group_key].sort(key=lambda x: x.date)
        
        logging.debug(f"[Indexer] 扫描完成，共处理 {folder_count} 个文件夹，"
                     f"分组数: {len(self.groups)}, 跳过: {len(self.skipped_folders)}")
        
        return self.groups
    
    def _iterate_folders(self, folder_path: str) -> Iterator[FolderInfo]:
        """
        迭代文件夹并解析
        
        参数:
            folder_path (str): 文件夹路径
            
        生成:
            FolderInfo: 解析成功的文件夹信息
        """
        try:
            for folder_name in os.listdir(folder_path):
                full_path = os.path.join(folder_path, folder_name)
                
                if not os.path.isdir(full_path):
                    continue
                
                # 解析文件夹信息
                folder_info = TimeParser.parse_folder_name(folder_name, full_path)
                
                if folder_info:
                    yield folder_info
                else:
                    logging.debug(f"[Indexer] 跳过无法解析的文件夹: {folder_name}")
                    
        except Exception as e:
            logging.error(f"[Indexer] 遍历文件夹失败: {folder_path}, 错误: {e}")
    
    def get_mergeable_groups(self, min_size: int = 2) -> List[tuple]:
        """
        获取可合并的文件夹组
        
        参数:
            min_size (int): 最小组大小
            
        返回:
            List[tuple]: [(group_key, folder_list), ...]
        """
        return [(key, folder_list) for key, folder_list in self.groups.items() 
                if len(folder_list) >= min_size]
    
    def get_group_count(self) -> int:
        """获取分组数量"""
        return len(self.groups)
    
    def get_total_folders(self) -> int:
        """获取总文件夹数量"""
        return sum(len(folder_list) for folder_list in self.groups.values())
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取索引统计信息
        
        返回:
            Dict[str, int]: 统计信息
        """
        mergeable_groups = self.get_mergeable_groups()
        mergeable_folders = sum(len(folder_list) for _, folder_list in mergeable_groups)
        
        return {
            "total_groups": self.get_group_count(),
            "total_folders": self.get_total_folders(),
            "skipped_folders": len(self.skipped_folders),
            "mergeable_groups": len(mergeable_groups),
            "mergeable_folders": mergeable_folders
        }


class TimeBasedIndexer(BaseFolderIndexer):
    """基于时间的索引器（用于L3）"""
    
    def get_grouping_key(self, folder_info: FolderInfo) -> Optional[tuple]:
        """
        按日期和标题分组
        
        返回:
            Optional[tuple]: (date, title) 或 None
        """
        return (folder_info.date.date(), folder_info.title)


class TitleBasedIndexer(BaseFolderIndexer):
    """基于标题的索引器（用于L4跨天）"""
    
    def get_grouping_key(self, folder_info: FolderInfo) -> Optional[str]:
        """
        仅按标题分组，忽略日期
        
        返回:
            Optional[str]: title 或 None
        """
        return folder_info.title


class BlrecIndexer(BaseFolderIndexer):
    """BLREC格式索引器（用于L2）"""
    
    def get_grouping_key(self, folder_info: FolderInfo) -> Optional[tuple]:
        """
        按日期、标题和后缀分组
        
        返回:
            Optional[tuple]: (date, title, suffix) 或 None
        """
        if folder_info.suffix:  # 确保是BLREC格式
            return (folder_info.date.date(), folder_info.title, folder_info.suffix)
        return None


class ErrorTimeIndexer(BaseFolderIndexer):
    """错误时间索引器（用于L5）"""
    
    def __init__(self, flv_manager: FlvFileManager):
        super().__init__(flv_manager)
        self.error_folders = []  # 错误时间文件夹
        self.normal_folders = {}  # {(date, title): FolderInfo}
    
    def scan_and_index(self, folder_path: str) -> Dict[Any, List[FolderInfo]]:
        """
        重写扫描方法，分离错误和正常文件夹
        """
        self.error_folders.clear()
        self.normal_folders.clear()
        
        if not os.path.exists(folder_path):
            logging.warning(f"[ErrorTimeIndexer] 文件夹不存在: {folder_path}")
            return {}
        
        logging.debug(f"[ErrorTimeIndexer] 开始扫描文件夹: {folder_path}")
        
        for folder_info in self._iterate_folders(folder_path):
            if TimeParser.is_error_time_format(folder_info.name):
                # 错误时间文件夹，需要提取真实日期
                real_date = self.flv_manager.extract_flv_date_from_filename(folder_info.path)
                if real_date:
                    # 创建带真实日期的错误文件夹信息
                    error_info = FolderInfo(
                        name=folder_info.name,
                        path=folder_info.path,
                        date=real_date,
                        title=folder_info.title
                    )
                    self.error_folders.append(error_info)
            else:
                # 正常文件夹
                key = (folder_info.date.date(), folder_info.title)
                self.normal_folders[key] = folder_info
        
        logging.debug(f"[ErrorTimeIndexer] 扫描完成，错误文件夹: {len(self.error_folders)}，"
                     f"正常文件夹: {len(self.normal_folders)}")
        
        return {}  # 错误时间索引器不使用通用分组
    
    def get_grouping_key(self, folder_info: FolderInfo) -> Any:
        """错误时间索引器不使用通用分组"""
        return None
    
    def find_matching_normal_folder(self, error_folder: FolderInfo) -> Optional[FolderInfo]:
        """
        查找匹配的正常文件夹
        
        参数:
            error_folder (FolderInfo): 错误时间文件夹信息（包含真实日期）
            
        返回:
            Optional[FolderInfo]: 匹配的正常文件夹信息
        """
        # 首先尝试精确日期匹配
        key = (error_folder.date.date(), error_folder.title)
        exact_match = self.normal_folders.get(key)
        if exact_match:
            return exact_match
        
        # 如果精确匹配失败，尝试跨天匹配（匹配前一天的文件夹）
        # 这种情况通常发生在跨午夜的直播中
        prev_day = error_folder.date.date() - timedelta(days=1)
        prev_day_key = (prev_day, error_folder.title)
        prev_day_match = self.normal_folders.get(prev_day_key)
        
        if prev_day_match:
            # 验证是否为合理的跨天情况
            # 错误文件夹的FLV时间应该在凌晨（比如0-6点之间）
            if 0 <= error_folder.date.hour <= 6:
                logging.info(f"[ErrorTimeIndexer] 找到跨天匹配文件夹: {error_folder.title} "
                           f"({error_folder.date.date()}) -> ({prev_day})")
                return prev_day_match
        
        return None
    
    def get_error_folders(self) -> List[FolderInfo]:
        """获取所有错误时间文件夹"""
        return self.error_folders.copy()


class FolderIndexerFactory:
    """文件夹索引器工厂"""
    
    @staticmethod
    def create_time_based_indexer(flv_manager: FlvFileManager) -> TimeBasedIndexer:
        """创建基于时间的索引器"""
        return TimeBasedIndexer(flv_manager)
    
    @staticmethod
    def create_title_based_indexer(flv_manager: FlvFileManager) -> TitleBasedIndexer:
        """创建基于标题的索引器"""
        return TitleBasedIndexer(flv_manager)
    
    @staticmethod
    def create_blrec_indexer(flv_manager: FlvFileManager) -> BlrecIndexer:
        """创建BLREC索引器"""
        return BlrecIndexer(flv_manager)
    
    @staticmethod
    def create_error_time_indexer(flv_manager: FlvFileManager) -> ErrorTimeIndexer:
        """创建错误时间索引器"""
        return ErrorTimeIndexer(flv_manager) 