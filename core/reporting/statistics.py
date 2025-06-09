"""
统计功能模块

包含统计数据的收集、计算和管理功能。
"""

import logging
from typing import Dict, List, Any


class Statistics:
    """统计数据收集类"""
    
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.failed_names = []
        self.skip_reasons = {}  # 记录跳过原因
        
    def add_success(self):
        """添加成功记录"""
        self.success += 1
        self.total += 1
        
    def add_failed(self, name: str, reason: str = ""):
        """添加失败记录"""
        self.failed += 1
        self.total += 1
        self.failed_names.append({"name": name, "reason": reason})
        
    def add_skipped(self, name: str, reason: str):
        """添加跳过记录"""
        self.skipped += 1
        self.total += 1
        if reason not in self.skip_reasons:
            self.skip_reasons[reason] = []
        self.skip_reasons[reason].append(name)

    def add_success_with_name(self, name: str):
        """添加成功记录，同时记录名称"""
        self.success += 1
        self.total += 1
        if "成功处理" not in self.skip_reasons:
            self.skip_reasons["成功处理"] = []
        self.skip_reasons["成功处理"].append(name)
    
    def merge_stats(self, other_stats):
        """合并另一个统计对象的数据"""
        self.total += other_stats.total
        self.success += other_stats.success
        self.failed += other_stats.failed
        self.skipped += other_stats.skipped
        self.failed_names.extend(other_stats.failed_names)
        for reason, names in other_stats.skip_reasons.items():
            if reason not in self.skip_reasons:
                self.skip_reasons[reason] = []
            self.skip_reasons[reason].extend(names)

    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "failed_names": self.failed_names,
            "skip_reasons": self.skip_reasons
        }

    def reset(self):
        """重置所有统计数据"""
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.failed_names = []
        self.skip_reasons = {}
    
    def log_summary(self, title: str):
        """记录统计摘要到日志"""
        logging.info(f"[{title}] 总数: {self.total}, 成功: {self.success}, "
                    f"失败: {self.failed}, 跳过: {self.skipped}")


class StatisticsManager:
    """统计管理器，管理多个统计对象"""
    
    def __init__(self):
        self.stats_collection: Dict[str, Statistics] = {}
    
    def get_or_create_stats(self, name: str) -> Statistics:
        """获取或创建统计对象"""
        if name not in self.stats_collection:
            self.stats_collection[name] = Statistics()
        return self.stats_collection[name]
    
    def add_stats(self, name: str, stats: Statistics):
        """添加统计对象"""
        self.stats_collection[name] = stats
    
    def get_stats(self, name: str) -> Statistics:
        """获取统计对象"""
        return self.stats_collection.get(name, Statistics())
    
    def get_all_stats(self) -> Dict[str, Statistics]:
        """获取所有统计对象"""
        return self.stats_collection.copy()
    
    def get_combined_summary(self) -> Dict[str, Any]:
        """获取综合统计摘要"""
        combined = Statistics()
        for stats in self.stats_collection.values():
            combined.merge_stats(stats)
        return combined.get_summary()
    
    def reset_all(self):
        """重置所有统计数据"""
        for stats in self.stats_collection.values():
            stats.reset()
    
    def log_all_summaries(self):
        """记录所有统计摘要"""
        for name, stats in self.stats_collection.items():
            stats.log_summary(name) 