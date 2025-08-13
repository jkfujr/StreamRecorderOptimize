# core/L4_OPTIMIZE_CROSS_DAY.py
# 重构后的L4跨天合并处理器

import os
import logging
from datetime import timedelta

from core.engines import FlvFileManager, FolderIndexerFactory, FileOperations, MergeOperations, TimeInterval
from .folder import FolderProcessor


class CrossDayMerger:
    """
    跨天合并器，专门处理跨午夜的录播文件夹合并
    """
    
    def __init__(self, merge_interval_seconds=60, start_hour=20, end_hour=4):
        self.merge_interval = merge_interval_seconds
        self.start_hour = start_hour  # 前一天开始检测的小时（默认晚上8点）
        self.end_hour = end_hour      # 次日结束检测的小时（默认凌晨4点）
        self.merge_count = 0
    
    def is_cross_day_candidate(self, flv_time, folder_time):
        """
        判断FLV时间和文件夹时间是否为跨天候选
        条件：FLV时间在前一天start_hour(20点)之后，文件夹时间在次日end_hour(4点)之前，且相邻日期
        """
        if folder_time.date() != flv_time.date() + timedelta(days=1):
            return False
        
        # FLV时间在前一天start_hour之后，文件夹时间在次日end_hour之前
        return flv_time.hour >= self.start_hour and folder_time.hour <= self.end_hour
    
    def calculate_cross_day_interval(self, flv_time, folder_time):
        """
        计算跨天时间间隔（秒）
        使用TimeInterval的跨天计算方法
        """
        return TimeInterval.calculate_cross_day_interval(flv_time, folder_time)
    
    def find_cross_day_pairs(self, folder_list, flv_manager):
        """
        找出所有可跨天合并的文件夹对
        返回: [(target_folder, source_folder), ...]
        """
        cross_day_pairs = []
        
        logging.debug(f"[L4] 开始分析跨天文件夹对，共{len(folder_list)}个文件夹")
        
        for i in range(len(folder_list) - 1):
            current_folder_info = folder_list[i]
            next_folder_info = folder_list[i + 1]
            
            current_folder = current_folder_info.path
            next_folder = next_folder_info.path
            current_time = current_folder_info.date
            next_time = next_folder_info.date
            
            # 检查是否为跨天候选（使用文件夹时间进行初步判断）
            if not self.is_cross_day_candidate(current_time, next_time):
                continue
            
            # 检查两个文件夹是否都有FLV文件
            current_flv_time = flv_manager.get_flv_modification_time(current_folder)
            next_flv_info = flv_manager.get_flv_info(next_folder)
            
            if not current_flv_time or not next_flv_info:
                logging.debug(f"[L4] 文件夹缺少FLV文件，跳过: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)}")
                continue
            
            # 使用当前文件夹最后一个FLV修改时间与下一个文件夹第一个FLV创建时间计算跨天间隔
            next_flv_creation_time = flv_manager.get_first_flv_creation_time(next_folder)
            if not next_flv_creation_time:
                logging.debug(f"[L4] 下一个文件夹第一个FLV文件创建时间获取失败，跳过: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)}")
                continue
            
            cross_day_interval = self.calculate_cross_day_interval(current_flv_time, next_flv_creation_time)
            
            # 详细记录时间比较信息
            logging.debug(f"[L4] 跨天时间分析: {os.path.basename(current_folder)} (最后FLV修改: {current_flv_time.strftime('%Y-%m-%d %H:%M:%S')}) -> {os.path.basename(next_folder)} (第一个FLV创建: {next_flv_creation_time.strftime('%Y-%m-%d %H:%M:%S')}) | 时间间隔: {cross_day_interval:.1f}秒 ({cross_day_interval/60:.1f}分钟)")
            
            # 检查跨天间隔是否在阈值内
            if cross_day_interval <= self.merge_interval:
                cross_day_pairs.append((current_folder, next_folder))
                logging.info(f"[L4] ✓ 发现跨天可合并对: {os.path.basename(current_folder)} <- {os.path.basename(next_folder)} | 间隔: {cross_day_interval:.1f}秒 ({cross_day_interval/60:.1f}分钟) ≤ 阈值: {self.merge_interval}秒")
            else:
                logging.info(f"[L4] ✗ 跨天间隔超出阈值: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)} | 间隔: {cross_day_interval:.1f}秒 ({cross_day_interval/60:.1f}分钟) > 阈值: {self.merge_interval}秒 ({self.merge_interval/60:.1f}分钟)")
        
        return cross_day_pairs
    
    def execute_cross_day_merges(self, cross_day_pairs):
        """
        执行所有跨天合并操作
        """
        total_merged = 0
        
        for target_folder, source_folder in cross_day_pairs:
            try:
                if os.path.exists(source_folder) and os.path.exists(target_folder):
                    if MergeOperations.merge_folder_contents(source_folder, target_folder):
                        total_merged += 1
                        logging.info(f"[L4] 已跨天合并: {source_folder} -> {target_folder}")
                
            except Exception as e:
                logging.error(f"[L4] 跨天合并失败: {target_folder} <- {source_folder}, 错误: {e}")
        
        self.merge_count += total_merged
        return total_merged


class L4Processor(FolderProcessor):
    """
    L4跨天合并处理器
    
    负责处理跨午夜的录播文件夹合并，解决L3无法处理的跨日期问题。
    专门检测和合并可配置时间范围内的连续录播。
    
    检测逻辑：
    - 前一天文件夹最后一个FLV修改时间 vs 次日文件夹第一个FLV创建时间
    - 时间范围：前一天20:00之后 到 次日04:00之前的跨天录播
    - 例如：前一天23:50的最后FLV文件 vs 次日00:22的第一个FLV文件 = 32分钟间隔
    
    使用示例：
    文件夹A: 20250523-235053_【直播标题】 (最后FLV修改时间: 2025-05-23 23:58:25)
    文件夹B: 20250524-002258_【直播标题】 (第一个FLV创建时间: 2025-05-24 00:22:58)
    跨天间隔: (00:00:00 - 23:58:25) + (00:22:58 - 00:00:00) = 1分35秒 + 22分58秒 = 24分33秒
    """
    
    def __init__(self, path_config, skip_folders, merge_interval, start_hour=20, end_hour=4, enable=True):
        super().__init__(path_config, [], skip_folders, enable)
        self.merge_interval = merge_interval
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.flv_manager = FlvFileManager()
        self.indexer = FolderIndexerFactory.create_title_based_indexer(self.flv_manager)
        self.merger = CrossDayMerger(merge_interval, start_hour, end_hour)
    
    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组
        """
        source_path = paths["source"]
        
        if not os.path.exists(source_path):
            return
        
        self._log_debug(f"开始处理L4路径组：{folder_id}")
        
        # 遍历用户文件夹
        for user_folder_name in os.listdir(source_path):
            user_folder_path = os.path.join(source_path, user_folder_name)
            
            if not os.path.isdir(user_folder_path):
                continue
            
            if user_folder_name in self.skip_folders:
                self.stats.add_skipped(user_folder_name, "在跳过列表中")
                continue
            
            self._process_user_folder(user_folder_path, user_folder_name)
    
    def _process_user_folder(self, user_folder_path, user_folder_name):
        """
        处理用户文件夹的跨天合并
        """
        logging.info(f"[L4] 开始处理用户跨天合并: {user_folder_name}")
        
        try:
            # 使用基于标题的索引器扫描构建索引
            folder_groups = self.indexer.scan_and_index(user_folder_path)
            
            # 获取跨天候选组（按标题分组）
            cross_day_candidates = self.indexer.get_mergeable_groups()
            
            if not cross_day_candidates:
                self.stats.add_skipped(user_folder_name, "无跨天候选文件夹")
                return
            
            total_merged = 0
            
            # 处理每个标题组的跨天合并
            for title, folder_list in cross_day_candidates:
                logging.debug(f"[L4] 处理标题组: {title}, 共{len(folder_list)}个文件夹")
                
                # 找出跨天文件夹对
                cross_day_pairs = self.merger.find_cross_day_pairs(folder_list, self.flv_manager)
                
                if cross_day_pairs:
                    # 执行跨天合并
                    merged_count = self.merger.execute_cross_day_merges(cross_day_pairs)
                    total_merged += merged_count
            
            # 使用统一的文件操作清理空文件夹
            empty_folders_removed = FileOperations.cleanup_empty_folders(user_folder_path)
            
            # 统计结果
            if total_merged > 0 or empty_folders_removed > 0:
                self.stats.add_success_with_name(
                    f"{user_folder_name} (跨天合并:{total_merged}, 清理:{empty_folders_removed})"
                )
                logging.info(f"[L4] 用户 {user_folder_name} 跨天处理完成: 合并{total_merged}个, 清理{empty_folders_removed}个空文件夹")
            else:
                self.stats.add_skipped(user_folder_name, "无需跨天合并")
                
        except Exception as e:
            self.stats.add_failed(user_folder_name, str(e))
            logging.error(f"[L4] 处理用户文件夹 {user_folder_path} 跨天合并失败: {e}")
        finally:
            # 记录缓存统计信息
            self.flv_manager.log_cache_stats()