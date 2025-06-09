"""
时间解析工具模块

提供统一的时间解析接口，支持多种文件夹和文件命名格式。
"""

import re
import logging
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class FolderInfo:
    """文件夹信息数据类"""
    name: str
    path: str
    date: datetime
    title: str
    suffix: Optional[str] = None  # 用于BLREC格式


class TimeParser:
    """统一的时间解析工具"""
    
    # 常用时间格式模式
    FOLDER_PATTERN = r"(\d{8})-(\d{6})_(.+)"
    BLREC_PATTERN = r"(\d{8})-(\d{6})_(.+)【(blrec-flv|blrec-hls)】"
    FLV_PATTERN = r"(\d{8}-\d{6})"
    ERROR_TIME_PATTERN = r"19700101-080000_(.+)"
    
    @classmethod
    def parse_folder_name(cls, folder_name: str, folder_path: str) -> Optional[FolderInfo]:
        """
        解析文件夹名称，支持多种格式
        
        参数:
            folder_name (str): 文件夹名称
            folder_path (str): 文件夹路径
            
        返回:
            Optional[FolderInfo]: 解析成功返回FolderInfo，否则返回None
        """
        # 优先尝试BLREC格式
        if cls.is_blrec_format(folder_name):
            return cls._parse_blrec_format(folder_name, folder_path)
        
        # 尝试标准格式
        if cls.is_standard_format(folder_name):
            return cls._parse_standard_format(folder_name, folder_path)
        
        # 尝试错误时间格式
        if cls.is_error_time_format(folder_name):
            return cls._parse_error_time_format(folder_name, folder_path)
        
        return None
    
    @classmethod
    def is_blrec_format(cls, folder_name: str) -> bool:
        """判断是否为BLREC格式"""
        return "【blrec-" in folder_name
    
    @classmethod
    def is_standard_format(cls, folder_name: str) -> bool:
        """判断是否为标准格式"""
        return re.match(cls.FOLDER_PATTERN, folder_name) is not None
    
    @classmethod
    def is_error_time_format(cls, folder_name: str) -> bool:
        """判断是否为错误时间格式"""
        return folder_name.startswith("19700101-080000_")
    
    @classmethod
    def _parse_blrec_format(cls, folder_name: str, folder_path: str) -> Optional[FolderInfo]:
        """解析BLREC格式文件夹"""
        match = re.match(cls.BLREC_PATTERN, folder_name)
        if match:
            date_str, time_str, title, suffix = match.groups()
            try:
                date = datetime.strptime(f"{date_str}-{time_str}", "%Y%m%d-%H%M%S")
                return FolderInfo(
                    name=folder_name,
                    path=folder_path,
                    date=date,
                    title=title,
                    suffix=suffix
                )
            except ValueError as e:
                logging.debug(f"[TimeParser] BLREC格式时间解析失败: {folder_name}, 错误: {e}")
        return None
    
    @classmethod
    def _parse_standard_format(cls, folder_name: str, folder_path: str) -> Optional[FolderInfo]:
        """解析标准格式文件夹"""
        match = re.match(cls.FOLDER_PATTERN, folder_name)
        if match:
            date_str, time_str, title = match.groups()
            try:
                date = datetime.strptime(f"{date_str}-{time_str}", "%Y%m%d-%H%M%S")
                return FolderInfo(
                    name=folder_name,
                    path=folder_path,
                    date=date,
                    title=title
                )
            except ValueError as e:
                logging.debug(f"[TimeParser] 标准格式时间解析失败: {folder_name}, 错误: {e}")
        return None
    
    @classmethod
    def _parse_error_time_format(cls, folder_name: str, folder_path: str) -> Optional[FolderInfo]:
        """解析错误时间格式文件夹"""
        match = re.match(cls.ERROR_TIME_PATTERN, folder_name)
        if match:
            title = match.group(1)
            # 错误时间使用固定的1970年1月1日
            error_date = datetime(1970, 1, 1, 8, 0, 0)
            return FolderInfo(
                name=folder_name,
                path=folder_path,
                date=error_date,
                title=title
            )
        return None
    
    @classmethod
    def parse_flv_filename(cls, flv_name: str) -> Optional[datetime]:
        """
        从FLV文件名解析时间
        
        参数:
            flv_name (str): FLV文件名
            
        返回:
            Optional[datetime]: 解析成功返回时间，否则返回None
        """
        match = re.search(cls.FLV_PATTERN, flv_name)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, "%Y%m%d-%H%M%S")
            except ValueError as e:
                logging.debug(f"[TimeParser] FLV文件名时间解析失败: {flv_name}, 错误: {e}")
        return None
    
    @classmethod
    def extract_date_title_from_folder(cls, folder_name: str) -> Tuple[Optional[datetime], Optional[str]]:
        """
        从文件夹名快速提取日期和标题
        
        参数:
            folder_name (str): 文件夹名称
            
        返回:
            Tuple[Optional[datetime], Optional[str]]: (日期, 标题)
        """
        folder_info = cls.parse_folder_name(folder_name, "")
        if folder_info:
            return folder_info.date, folder_info.title
        return None, None


class TimeInterval:
    """时间间隔计算工具"""
    
    @staticmethod
    def calculate_seconds_between(time1: datetime, time2: datetime) -> float:
        """计算两个时间点之间的秒数差"""
        return abs((time2 - time1).total_seconds())
    
    @staticmethod
    def is_within_interval(time1: datetime, time2: datetime, max_interval: int) -> bool:
        """判断两个时间是否在指定间隔内"""
        return TimeInterval.calculate_seconds_between(time1, time2) <= max_interval
    
    @staticmethod
    def calculate_cross_day_interval(flv_time: datetime, folder_time: datetime) -> float:
        """
        计算跨天时间间隔（专用于L4处理器）
        
        参数:
            flv_time: 前一天文件夹的FLV修改时间
            folder_time: 次日文件夹的创建时间
            
        返回:
            float: 跨天间隔秒数，如果不是跨天情况返回无穷大
        """
        from datetime import timedelta
        
        # 检查是否为跨天情况
        if folder_time.date() != flv_time.date() + timedelta(days=1):
            return float('inf')
        
        # 计算跨天间隔：(午夜 - 前一天FLV时间) + (次日文件夹时间 - 午夜)
        midnight = datetime.combine(flv_time.date() + timedelta(days=1), datetime.min.time())
        interval_seconds = (midnight - flv_time).total_seconds() + (folder_time - midnight).total_seconds()
        
        return interval_seconds 