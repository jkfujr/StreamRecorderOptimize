"""
报告系统模块

包含统计功能和报告格式化等功能。
"""

from .statistics import Statistics, StatisticsManager
from .formatter import ReportFormatter

__all__ = [
    'Statistics',
    'StatisticsManager', 
    'ReportFormatter'
] 