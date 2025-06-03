# core/L3_OPTIMIZE.py
# 高性能L3时间合并处理器

import os
import glob
import shutil
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor


class FolderTimeIndex:
    """
    文件夹时间索引管理器，用于高效的时间合并
    """
    
    def __init__(self):
        self.folder_groups = defaultdict(list)  # {(date, title): [(datetime, path), ...]}
        self.flv_cache = {}  # {folder_path: (flv_file, mod_time)}
    
    def scan_user_folder(self, user_folder):
        """
        单次扫描用户文件夹，构建时间索引和FLV缓存
        """
        self.folder_groups.clear()
        self.flv_cache.clear()
        
        if not os.path.exists(user_folder):
            logging.warning(f"[L3] 用户文件夹不存在: {user_folder}")
            return
        
        logging.debug(f"[L3] 开始扫描用户文件夹: {user_folder}")
        
        for folder_name in os.listdir(user_folder):
            folder_path = os.path.join(user_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            try:
                # 解析文件夹名：日期_标题
                date_str, title = folder_name.split('_', 1)
                date_time = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                key = (date_time.date(), title)
                
                self.folder_groups[key].append((date_time, folder_path))
                
                # 同时缓存FLV文件信息
                self._cache_flv_info(folder_path)
                
            except ValueError:
                logging.debug(f"[L3] 跳过无法解析的文件夹名: {folder_name}")
        
        # 对每组按时间排序
        for key in self.folder_groups:
            self.folder_groups[key].sort(key=lambda x: x[0])
        
        logging.debug(f"[L3] 扫描完成，共发现 {len(self.folder_groups)} 个文件夹组")
    
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
                logging.debug(f"[L3] 缓存FLV信息: {folder_path} -> {latest_file}")
            else:
                self.flv_cache[folder_path] = (None, None)
        except Exception as e:
            logging.error(f"[L3] 缓存FLV信息失败: {folder_path}, 错误: {e}")
            self.flv_cache[folder_path] = (None, None)
    
    def get_mergeable_groups(self):
        """
        获取可能需要合并的文件夹组（包含2个或更多文件夹）
        """
        return [(key, folder_list) for key, folder_list in self.folder_groups.items() 
                if len(folder_list) >= 2]


class TimeBasedMerger:
    """
    基于时间的高效合并器，使用滑动窗口算法
    """
    
    def __init__(self, merge_interval_seconds=60):
        self.merge_interval = merge_interval_seconds
        self.merge_count = 0
    
    def should_merge(self, time1, time2):
        """
        判断两个时间是否在合并间隔内
        """
        delta = abs(time2 - time1)
        return delta <= timedelta(seconds=self.merge_interval)
    
    def find_merge_chains(self, folder_list, flv_cache):
        """
        找出所有可合并的文件夹链
        返回: [(merge_to_folder, folders_to_merge), ...]
        """
        merge_chains = []
        used_indices = set()
        
        logging.debug(f"[L3] 开始分析文件夹链，共{len(folder_list)}个文件夹")
        
        for i in range(len(folder_list)):
            if i in used_indices:
                continue
            
            current_time, current_folder = folder_list[i]
            
            # 检查当前文件夹是否有FLV文件
            _, flv_mod_time = flv_cache.get(current_folder, (None, None))
            if not flv_mod_time:
                logging.debug(f"[L3] 文件夹 {os.path.basename(current_folder)} 没有FLV文件，跳过")
                continue
            
            # 找出所有可以合并到当前文件夹的后续文件夹
            merge_targets = [current_folder]
            used_indices.add(i)
            
            for j in range(i + 1, len(folder_list)):
                if j in used_indices:
                    continue
                
                next_time, next_folder = folder_list[j]
                
                # 计算时间差
                time_diff = abs(flv_mod_time - next_time).total_seconds()
                
                # 检查时间间隔
                if self.should_merge(flv_mod_time, next_time):
                    merge_targets.append(next_folder)
                    used_indices.add(j)
                    logging.debug(f"[L3] 发现可合并文件夹: {os.path.basename(current_folder)} <- {os.path.basename(next_folder)} (时间差: {time_diff:.1f}秒)")
                else:
                    logging.debug(f"[L3] 时间间隔过大: {os.path.basename(current_folder)} -> {os.path.basename(next_folder)} (时间差: {time_diff:.1f}秒 > {self.merge_interval}秒)")
                    # 时间间隔太大，停止查找这个链
                    break
            
            # 如果找到了可合并的文件夹，加入链表
            if len(merge_targets) > 1:
                merge_chains.append((current_folder, merge_targets[1:]))
                logging.info(f"[L3] 形成合并链: {os.path.basename(current_folder)} <- {len(merge_targets)-1}个文件夹")
        
        if not merge_chains:
            logging.debug(f"[L3] 未找到可合并的文件夹链")
        
        return merge_chains
    
    def execute_merges(self, merge_chains):
        """
        执行所有合并操作
        """
        total_merged = 0
        
        for target_folder, folders_to_merge in merge_chains:
            try:
                for source_folder in folders_to_merge:
                    if os.path.exists(source_folder):
                        self._move_files(source_folder, target_folder)
                        self._remove_folder(source_folder)
                        total_merged += 1
                        logging.info(f"[L3] 已合并: {source_folder} -> {target_folder}")
                
            except Exception as e:
                logging.error(f"[L3] 合并失败: {target_folder}, 错误: {e}")
        
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
                logging.debug(f"[L3] 文件已存在，跳过: {dest_path}")
                continue
            
            try:
                shutil.move(src_path, dest_folder)
                logging.debug(f"[L3] 移动文件: {src_path} -> {dest_folder}")
            except Exception as e:
                logging.error(f"[L3] 移动文件失败: {src_path}, 错误: {e}")
    
    def _remove_folder(self, folder_path):
        """
        删除空文件夹
        """
        try:
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                logging.debug(f"[L3] 已删除空文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"[L3] 删除文件夹失败: {folder_path}, 错误: {e}")


class L3Processor(FolderProcessor):
    """
    L3时间合并处理器
    
    负责根据时间间隔合并录播文件夹，解决O(n²)复杂度问题。
    使用单次扫描和滑动窗口算法，大幅提升性能。
    """
    
    def __init__(self, path_config, skip_folders, merge_interval, enable=True):
        super().__init__(path_config, [], skip_folders, enable)
        self.merge_interval = merge_interval
        self.folder_index = FolderTimeIndex()
        self.merger = TimeBasedMerger(merge_interval)
    
    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组
        """
        source_path = paths["source"]
        
        if not os.path.exists(source_path):
            return
        
        self._log_debug(f"开始处理L3路径组：{folder_id}")
        
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
        处理用户文件夹，避免重复扫描
        """
        logging.info(f"[L3] 开始处理用户: {user_folder_name}")
        
        try:
            # 单次扫描构建索引
            self.folder_index.scan_user_folder(user_folder_path)
            
            # 获取可合并的文件夹组
            mergeable_groups = self.folder_index.get_mergeable_groups()
            
            if not mergeable_groups:
                self.stats.add_skipped(user_folder_name, "无可合并文件夹")
                return
            
            total_merged = 0
            
            # 处理每个文件夹组
            for key, folder_list in mergeable_groups:
                date, title = key
                logging.debug(f"[L3] 处理文件夹组: {title} ({date}), 共{len(folder_list)}个文件夹")
                
                # 找出合并链
                merge_chains = self.merger.find_merge_chains(folder_list, self.folder_index.flv_cache)
                
                if merge_chains:
                    # 执行合并
                    merged_count = self.merger.execute_merges(merge_chains)
                    total_merged += merged_count
            
            # 清理空文件夹
            empty_folders_removed = self._cleanup_empty_folders(user_folder_path)
            
            # 统计结果
            if total_merged > 0 or empty_folders_removed > 0:
                self.stats.add_success_with_name(
                    f"{user_folder_name} (合并:{total_merged}, 清理:{empty_folders_removed})"
                )
                logging.info(f"[L3] 用户 {user_folder_name} 处理完成: 合并{total_merged}个, 清理{empty_folders_removed}个空文件夹")
            else:
                self.stats.add_skipped(user_folder_name, "无需合并")
                
        except Exception as e:
            self.stats.add_failed(user_folder_name, str(e))
            logging.error(f"[L3] 处理用户文件夹 {user_folder_path} 失败: {e}")
    
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
                    logging.debug(f"[L3] 已删除空文件夹: {folder_path}")
                    empty_count += 1
        except Exception as e:
            logging.error(f"[L3] 清理空文件夹失败: {user_folder}, 错误: {e}")
        
        return empty_count