# core/L4_OPTIMIZE_CROSS_DAY.py
# 高性能L4跨天合并处理器

import os
import glob
import shutil
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor


class CrossDayFolderIndex:
    """
    跨天文件夹索引管理器，用于高效的跨天合并检测
    """
    
    def __init__(self):
        self.user_folder_groups = defaultdict(lambda: defaultdict(list))  # {user: {title: [(datetime, path), ...]}}
        self.flv_cache = {}  # {folder_path: (flv_file, mod_time)}
    
    def scan_user_folder(self, user_folder, user_name):
        """
        单次扫描用户文件夹，构建跨天索引和FLV缓存
        """
        self.user_folder_groups[user_name].clear()
        
        if not os.path.exists(user_folder):
            logging.warning(f"[L4] 用户文件夹不存在: {user_folder}")
            return
        
        logging.debug(f"[L4] 开始扫描用户文件夹: {user_name}")
        
        for folder_name in os.listdir(user_folder):
            folder_path = os.path.join(user_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            try:
                # 解析文件夹名：日期_标题
                date_str, title = folder_name.split('_', 1)
                date_time = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                
                # 按标题分组，不考虑日期（这是跟L3的关键区别）
                self.user_folder_groups[user_name][title].append((date_time, folder_path))
                
                # 同时缓存FLV文件信息
                self._cache_flv_info(folder_path)
                
            except ValueError:
                logging.debug(f"[L4] 跳过无法解析的文件夹名: {folder_name}")
        
        # 对每个标题组按时间排序
        for title in self.user_folder_groups[user_name]:
            self.user_folder_groups[user_name][title].sort(key=lambda x: x[0])
        
        logging.debug(f"[L4] 用户 {user_name} 扫描完成，共发现 {len(self.user_folder_groups[user_name])} 个标题组")
    
    def _cache_flv_info(self, folder_path):
        """
        缓存文件夹的FLV文件信息
        """
        try:
            flv_files = glob.glob(os.path.join(folder_path, "*.flv"))
            if flv_files:
                # 按修改时间排序，取最新的
                flv_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                latest_file = flv_files[0]
                modification_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
                self.flv_cache[folder_path] = (latest_file, modification_time)
                logging.debug(f"[L4] 缓存FLV信息: {folder_path} -> {latest_file}")
            else:
                self.flv_cache[folder_path] = (None, None)
        except Exception as e:
            logging.error(f"[L4] 缓存FLV信息失败: {folder_path}, 错误: {e}")
            self.flv_cache[folder_path] = (None, None)
    
    def get_cross_day_candidates(self, user_name):
        """
        获取指定用户的跨天合并候选组
        """
        if user_name not in self.user_folder_groups:
            return []
        
        candidates = []
        for title, folder_list in self.user_folder_groups[user_name].items():
            if len(folder_list) >= 2:  # 至少需要2个文件夹才可能跨天
                candidates.append((title, folder_list))
        
        return candidates


class CrossDayMerger:
    """
    跨天合并器，专门处理跨午夜的录播文件夹合并
    """
    
    def __init__(self, merge_interval_seconds=60, start_hour=22, end_hour=2):
        self.merge_interval = merge_interval_seconds
        self.start_hour = start_hour  # 前一天开始检测的小时
        self.end_hour = end_hour      # 次日结束检测的小时
        self.merge_count = 0
    
    def is_cross_day_candidate(self, flv_time, folder_time):
        """
        判断FLV时间和文件夹时间是否为跨天候选
        条件：FLV时间在前一天start_hour之后，文件夹时间在次日end_hour之前，且相邻日期
        """
        if folder_time.date() != flv_time.date() + timedelta(days=1):
            return False
        
        # FLV时间在前一天start_hour之后，文件夹时间在次日end_hour之前
        return flv_time.hour >= self.start_hour and folder_time.hour <= self.end_hour
    
    def calculate_cross_day_interval(self, flv_time, folder_time):
        """
        计算跨天时间间隔（秒）
        flv_time: 前一天文件夹的FLV修改时间
        folder_time: 次日文件夹的创建时间（从文件夹名解析）
        """
        if not self.is_cross_day_candidate(flv_time, folder_time):
            return float('inf')  # 不是跨天候选，返回无穷大
        
        # 计算跨天间隔：(午夜 - 前一天FLV时间) + (次日文件夹时间 - 午夜)
        midnight = datetime.combine(flv_time.date() + timedelta(days=1), datetime.min.time())
        interval_seconds = (midnight - flv_time).total_seconds() + (folder_time - midnight).total_seconds()
        
        return interval_seconds
    
    def find_cross_day_pairs(self, folder_list, flv_cache):
        """
        找出所有可跨天合并的文件夹对
        返回: [(target_folder, source_folder), ...]
        """
        cross_day_pairs = []
        
        logging.debug(f"[L4] 开始分析跨天文件夹对，共{len(folder_list)}个文件夹")
        
        for i in range(len(folder_list) - 1):
            current_time, current_folder = folder_list[i]
            next_time, next_folder = folder_list[i + 1]
            
            # 检查是否为跨天候选（使用文件夹时间进行初步判断）
            if not self.is_cross_day_candidate(current_time, next_time):
                continue
            
            # 检查两个文件夹是否都有FLV文件
            current_flv, current_flv_time = flv_cache.get(current_folder, (None, None))
            next_flv, next_flv_time = flv_cache.get(next_folder, (None, None))
            
            if not current_flv or not next_flv_time:
                logging.debug(f"[L4] 文件夹缺少FLV文件，跳过: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)}")
                continue
            
            # 使用当前文件夹的FLV修改时间与下一个文件夹的创建时间计算跨天间隔
            # 这里的关键修正：current_flv_time vs next_time（文件夹时间），而不是vs next_flv_time
            cross_day_interval = self.calculate_cross_day_interval(current_flv_time, next_time)
            
            # 检查跨天间隔是否在阈值内
            if cross_day_interval <= self.merge_interval:
                cross_day_pairs.append((current_folder, next_folder))
                logging.info(f"[L4] 发现跨天可合并对: {os.path.basename(current_folder)} <- {os.path.basename(next_folder)} (跨天间隔: {cross_day_interval:.1f}秒)")
            else:
                logging.debug(f"[L4] 跨天间隔过大: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)} (间隔: {cross_day_interval:.1f}秒 > {self.merge_interval}秒)")
        
        return cross_day_pairs
    
    def execute_cross_day_merges(self, cross_day_pairs):
        """
        执行所有跨天合并操作
        """
        total_merged = 0
        
        for target_folder, source_folder in cross_day_pairs:
            try:
                if os.path.exists(source_folder) and os.path.exists(target_folder):
                    self._move_files(source_folder, target_folder)
                    self._remove_folder(source_folder)
                    total_merged += 1
                    logging.info(f"[L4] 已跨天合并: {source_folder} -> {target_folder}")
                
            except Exception as e:
                logging.error(f"[L4] 跨天合并失败: {target_folder} <- {source_folder}, 错误: {e}")
        
        self.merge_count += total_merged
        return total_merged
    
    def _move_files(self, src_folder, dest_folder):
        """
        移动文件夹中的所有文件
        """
        if not os.path.exists(src_folder):
            return
        
        for item in os.listdir(src_folder):
            src_path = os.path.join(src_folder, item)
            dest_path = os.path.join(dest_folder, item)
            
            if os.path.exists(dest_path):
                # 处理重名文件，添加时间戳后缀
                base_name, ext = os.path.splitext(item)
                timestamp = datetime.now().strftime("%H%M%S")
                new_name = f"{base_name}_{timestamp}{ext}"
                dest_path = os.path.join(dest_folder, new_name)
                logging.debug(f"[L4] 文件重名，重命名为: {new_name}")
            
            try:
                shutil.move(src_path, dest_folder)
                logging.debug(f"[L4] 移动文件: {src_path} -> {dest_folder}")
            except Exception as e:
                logging.error(f"[L4] 移动文件失败: {src_path}, 错误: {e}")
    
    def _remove_folder(self, folder_path):
        """
        删除空文件夹
        """
        try:
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                logging.debug(f"[L4] 已删除空文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"[L4] 删除文件夹失败: {folder_path}, 错误: {e}")


class L4Processor(FolderProcessor):
    """
    L4跨天合并处理器
    
    负责处理跨午夜的录播文件夹合并，解决L3无法处理的跨日期问题。
    专门检测和合并可配置时间范围内的连续录播。
    
    检测逻辑：
    - 前一天文件夹的FLV修改时间 vs 次日文件夹的创建时间（从文件夹名解析）
    - 例如：前一天23:50的FLV文件 vs 次日00:22的文件夹 = 32分钟间隔
    
    使用示例：
    文件夹A: 20250523-235053_【直播标题】 (FLV修改时间: 2025-05-23 23:58:25)
    文件夹B: 20250524-002258_【直播标题】 (文件夹时间: 2025-05-24 00:22:58)
    跨天间隔: (00:00:00 - 23:58:25) + (00:22:58 - 00:00:00) = 1分35秒 + 22分58秒 = 24分33秒
    """
    
    def __init__(self, path_config, skip_folders, merge_interval, start_hour=22, end_hour=2, enable=True):
        super().__init__(path_config, [], skip_folders, enable)
        self.merge_interval = merge_interval
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.folder_index = CrossDayFolderIndex()
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
            # 单次扫描构建跨天索引
            self.folder_index.scan_user_folder(user_folder_path, user_folder_name)
            
            # 获取跨天候选组
            cross_day_candidates = self.folder_index.get_cross_day_candidates(user_folder_name)
            
            if not cross_day_candidates:
                self.stats.add_skipped(user_folder_name, "无跨天候选文件夹")
                return
            
            total_merged = 0
            
            # 处理每个标题组的跨天合并
            for title, folder_list in cross_day_candidates:
                logging.debug(f"[L4] 处理标题组: {title}, 共{len(folder_list)}个文件夹")
                
                # 找出跨天文件夹对
                cross_day_pairs = self.merger.find_cross_day_pairs(folder_list, self.folder_index.flv_cache)
                
                if cross_day_pairs:
                    # 执行跨天合并
                    merged_count = self.merger.execute_cross_day_merges(cross_day_pairs)
                    total_merged += merged_count
            
            # 清理空文件夹
            empty_folders_removed = self._cleanup_empty_folders(user_folder_path)
            
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
    
    def _cleanup_empty_folders(self, user_folder):
        """
        清理空文件夹
        """
        empty_count = 0
        
        try:
            for folder_name in os.listdir(user_folder):
                folder_path = os.path.join(user_folder, folder_name)
                if os.path.isdir(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
                    logging.debug(f"[L4] 已删除空文件夹: {folder_path}")
                    empty_count += 1
        except Exception as e:
            logging.error(f"[L4] 清理空文件夹失败: {user_folder}, 错误: {e}")
        
        return empty_count 