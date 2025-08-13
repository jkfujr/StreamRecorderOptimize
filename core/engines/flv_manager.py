"""
FLV文件管理模块

提供统一的FLV文件处理接口，包括缓存机制和时间提取功能。
"""

import os
import glob
import logging
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from .time_utils import TimeParser


@dataclass
class FlvInfo:
    """FLV文件信息数据类"""
    file_path: str
    filename: str
    modification_time: datetime
    size: int = 0


class FlvFileManager:
    """统一的FLV文件管理器"""
    
    def __init__(self):
        """初始化FLV文件管理器"""
        self.cache: Dict[str, Optional[FlvInfo]] = {}  # {folder_path: FlvInfo}
        self._hit_count = 0
        self._miss_count = 0
    
    def get_flv_info(self, folder_path: str) -> Optional[FlvInfo]:
        """
        获取文件夹中的FLV文件信息（带缓存）
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            Optional[FlvInfo]: FLV文件信息，如果没有FLV文件返回None
        """
        if folder_path in self.cache:
            self._hit_count += 1
            return self.cache[folder_path]
        
        self._miss_count += 1
        flv_info = self._extract_flv_info(folder_path)
        self.cache[folder_path] = flv_info
        return flv_info
    
    def _extract_flv_info(self, folder_path: str) -> Optional[FlvInfo]:
        """
        从文件夹中提取FLV文件信息
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            Optional[FlvInfo]: FLV文件信息
        """
        try:
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                logging.debug(f"[FlvManager] 文件夹不存在或不是目录: {folder_path}")
                return None
            
            # 查找所有FLV文件
            flv_files = glob.glob(os.path.join(folder_path, "*.flv"))
            
            if not flv_files:
                logging.debug(f"[FlvManager] 文件夹中没有FLV文件: {folder_path}")
                return None
            
            # 按修改时间排序，取最新的
            flv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            latest_file = flv_files[0]
            
            # 获取文件信息
            stat_info = os.stat(latest_file)
            modification_time = datetime.fromtimestamp(stat_info.st_mtime)
            
            flv_info = FlvInfo(
                file_path=latest_file,
                filename=os.path.basename(latest_file),
                modification_time=modification_time,
                size=stat_info.st_size
            )
            
            logging.debug(f"[FlvManager] 找到FLV文件: {latest_file}, 修改时间: {modification_time}")
            return flv_info
            
        except Exception as e:
            logging.error(f"[FlvManager] 提取FLV文件信息失败: {folder_path}, 错误: {e}")
            return None
    
    def extract_flv_date_from_filename(self, folder_path: str) -> Optional[datetime]:
        """
        从FLV文件名中提取日期时间
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            Optional[datetime]: 从文件名解析的时间
        """
        flv_info = self.get_flv_info(folder_path)
        if not flv_info:
            return None
        
        return TimeParser.parse_flv_filename(flv_info.filename)
    
    def get_flv_modification_time(self, folder_path: str) -> Optional[datetime]:
        """
        获取文件夹中按修改时间排序后最后一个FLV文件的修改时间
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            Optional[datetime]: 最后一个FLV文件的修改时间
        """
        try:
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                return None
            
            # 查找所有FLV文件
            flv_files = glob.glob(os.path.join(folder_path, "*.flv"))
            
            if not flv_files:
                return None
            
            # 按修改时间排序，取最后一个（最新的）
            flv_files.sort(key=lambda x: os.path.getmtime(x))
            last_file = flv_files[-1]
            
            # 获取修改时间
            modification_time = datetime.fromtimestamp(os.path.getmtime(last_file))
            
            logging.debug(f"[FlvManager] 找到最后一个FLV文件: {last_file}, 修改时间: {modification_time}")
            return modification_time
            
        except Exception as e:
            logging.error(f"[FlvManager] 获取最后一个FLV文件修改时间失败: {folder_path}, 错误: {e}")
            return None
    
    def get_first_flv_creation_time(self, folder_path: str) -> Optional[datetime]:
        """
        获取文件夹中按创建时间排序后第一个FLV文件的创建时间
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            Optional[datetime]: 第一个FLV文件的创建时间
        """
        try:
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                return None
            
            # 查找所有FLV文件
            flv_files = glob.glob(os.path.join(folder_path, "*.flv"))
            
            if not flv_files:
                return None
            
            # 按创建时间排序，取第一个（最早的）
            flv_files.sort(key=lambda x: os.path.getctime(x))
            first_file = flv_files[0]
            
            # 获取创建时间
            creation_time = datetime.fromtimestamp(os.path.getctime(first_file))
            
            logging.debug(f"[FlvManager] 找到第一个FLV文件: {first_file}, 创建时间: {creation_time}")
            return creation_time
            
        except Exception as e:
            logging.error(f"[FlvManager] 获取第一个FLV文件创建时间失败: {folder_path}, 错误: {e}")
            return None
    
    def has_flv_file(self, folder_path: str) -> bool:
        """
        检查文件夹是否包含FLV文件
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            bool: 是否包含FLV文件
        """
        return self.get_flv_info(folder_path) is not None
    
    def get_all_cached_folders(self) -> list:
        """
        获取所有已缓存的文件夹路径
        
        返回:
            list: 已缓存的文件夹路径列表
        """
        return [path for path, info in self.cache.items() if info is not None]
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logging.debug("[FlvManager] 缓存已清空")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息
        
        返回:
            Dict[str, int]: 缓存统计信息
        """
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "cached_folders": len(self.cache)
        }
    
    def log_cache_stats(self):
        """记录缓存统计信息"""
        stats = self.get_cache_stats()
        logging.info(f"[FlvManager] 缓存统计 - 命中: {stats['hit_count']}, "
                    f"未命中: {stats['miss_count']}, 命中率: {stats['hit_rate']}%, "
                    f"已缓存文件夹: {stats['cached_folders']}")


class FlvProcessor:
    """FLV文件处理器，提供高级处理功能"""
    
    def __init__(self, flv_manager: FlvFileManager):
        """
        初始化FLV处理器
        
        参数:
            flv_manager (FlvFileManager): FLV文件管理器实例
        """
        self.flv_manager = flv_manager
    
    def batch_scan_folders(self, folder_paths: list) -> Dict[str, Optional[FlvInfo]]:
        """
        批量扫描多个文件夹的FLV文件
        
        参数:
            folder_paths (list): 文件夹路径列表
            
        返回:
            Dict[str, Optional[FlvInfo]]: 文件夹路径到FLV信息的映射
        """
        results = {}
        
        for folder_path in folder_paths:
            try:
                flv_info = self.flv_manager.get_flv_info(folder_path)
                results[folder_path] = flv_info
            except Exception as e:
                logging.error(f"[FlvProcessor] 批量扫描失败: {folder_path}, 错误: {e}")
                results[folder_path] = None
        
        logging.info(f"[FlvProcessor] 批量扫描完成，处理了 {len(folder_paths)} 个文件夹")
        return results
    
    def find_folders_with_flv(self, folder_paths: list) -> list:
        """
        查找包含FLV文件的文件夹
        
        参数:
            folder_paths (list): 文件夹路径列表
            
        返回:
            list: 包含FLV文件的文件夹路径列表
        """
        return [path for path in folder_paths if self.flv_manager.has_flv_file(path)]
    
    def find_folders_without_flv(self, folder_paths: list) -> list:
        """
        查找不包含FLV文件的文件夹
        
        参数:
            folder_paths (list): 文件夹路径列表
            
        返回:
            list: 不包含FLV文件的文件夹路径列表
        """
        return [path for path in folder_paths if not self.flv_manager.has_flv_file(path)]