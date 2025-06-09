# core/L3_OPTIMIZE.py
# 重构后的L3时间合并处理器

import os
import logging

from core.engines import FlvFileManager, FolderIndexerFactory, FileOperations, MergeOperations, TimeInterval
from .folder import FolderProcessor


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
        return TimeInterval.is_within_interval(time1, time2, self.merge_interval)
    
    def find_merge_chains(self, folder_list, flv_manager):
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
            
            current_folder_info = folder_list[i]
            current_folder = current_folder_info.path
            
            # 检查当前文件夹是否有FLV文件
            flv_mod_time = flv_manager.get_flv_modification_time(current_folder)
            if not flv_mod_time:
                logging.debug(f"[L3] 文件夹 {os.path.basename(current_folder)} 没有FLV文件，跳过")
                continue
            
            # 找出所有可以合并到当前文件夹的后续文件夹
            merge_targets = [current_folder]
            used_indices.add(i)
            
            for j in range(i + 1, len(folder_list)):
                if j in used_indices:
                    continue
                
                next_folder_info = folder_list[j]
                next_folder = next_folder_info.path
                next_time = next_folder_info.date
                
                # 检查时间间隔
                if self.should_merge(flv_mod_time, next_time):
                    merge_targets.append(next_folder)
                    used_indices.add(j)
                    
                    time_diff = abs(flv_mod_time - next_time).total_seconds()
                    logging.debug(f"[L3] 发现可合并文件夹: {os.path.basename(current_folder)} <- {os.path.basename(next_folder)} (时间差: {time_diff:.1f}秒)")
                else:
                    time_diff = abs(flv_mod_time - next_time).total_seconds()
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
                merged_count = MergeOperations.merge_folder_list_to_target(folders_to_merge, target_folder)
                total_merged += merged_count
                
                if merged_count > 0:
                    logging.info(f"[L3] 已合并 {merged_count} 个文件夹到: {target_folder}")
                
            except Exception as e:
                logging.error(f"[L3] 合并失败: {target_folder}, 错误: {e}")
        
        self.merge_count += total_merged
        return total_merged


class L3Processor(FolderProcessor):
    """
    L3时间合并处理器
    
    负责根据时间间隔合并录播文件夹，使用统一的通用模块。
    """
    
    def __init__(self, path_config, skip_folders, merge_interval, enable=True):
        super().__init__(path_config, [], skip_folders, enable)
        self.merge_interval = merge_interval
        self.flv_manager = FlvFileManager()
        self.indexer = FolderIndexerFactory.create_time_based_indexer(self.flv_manager)
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
        处理用户文件夹，使用统一的索引器和文件操作
        """
        logging.info(f"[L3] 开始处理用户: {user_folder_name}")
        
        try:
            # 使用统一的索引器扫描构建索引
            folder_groups = self.indexer.scan_and_index(user_folder_path)
            
            # 获取可合并的文件夹组
            mergeable_groups = self.indexer.get_mergeable_groups()
            
            if not mergeable_groups:
                self.stats.add_skipped(user_folder_name, "无可合并文件夹")
                return
            
            total_merged = 0
            
            # 处理每个文件夹组
            for key, folder_list in mergeable_groups:
                date, title = key
                logging.debug(f"[L3] 处理文件夹组: {title} ({date}), 共{len(folder_list)}个文件夹")
                
                # 找出合并链
                merge_chains = self.merger.find_merge_chains(folder_list, self.flv_manager)
                
                if merge_chains:
                    # 执行合并
                    merged_count = self.merger.execute_merges(merge_chains)
                    total_merged += merged_count
            
            # 使用统一的文件操作清理空文件夹
            empty_folders_removed = FileOperations.cleanup_empty_folders(user_folder_path)
            
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
        finally:
            # 记录缓存统计信息
            self.flv_manager.log_cache_stats()