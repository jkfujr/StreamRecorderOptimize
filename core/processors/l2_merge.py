# core/L2_OPTIMIZE.py
# 重构后的L2文件夹合并处理器

import os, logging
from collections import defaultdict

from core.engines import FlvFileManager, FolderIndexerFactory, FileOperations, MergeOperations, TimeParser
from core.reporting import Statistics
from .folder import FolderProcessor


class BLREC:
    """
    重构后的BLREC处理器，使用统一的索引器和文件操作
    """
    
    def __init__(self, flv_manager):
        self.stats = Statistics()
        self.flv_manager = flv_manager
        self.indexer = FolderIndexerFactory.create_blrec_indexer(flv_manager)
    
    def merge_folders(self, folder_path):
        """
        使用统一的索引器进行BLREC合并
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][BLREC] 路径不存在或不是目录：{folder_path}")
            return False
        
        try:
            # 使用统一的BLREC索引器扫描
            logging.debug(f"[L2][BLREC] 开始索引文件夹：{folder_path}")
            folder_groups = self.indexer.scan_and_index(folder_path)
            
            # 获取可合并的组
            mergeable_groups = self.indexer.get_mergeable_groups()
            merge_completed = False
            
            for key, folder_list in mergeable_groups:
                if len(folder_list) > 1:
                    merge_completed = True
                    self._merge_folder_group(key, folder_list)
            
            return merge_completed
            
        except Exception as e:
            logging.error(f"[L2][BLREC] 合并失败：{folder_path}, 错误：{e}")
            return False
    
    def _merge_folder_group(self, key, folder_list):
        """
        合并单个文件夹组，使用统一的合并操作
        """
        logging.debug(f"[L2][BLREC] 发现可合并文件夹组：{key}, 共{len(folder_list)}个文件夹")
        
        # 第一个作为目标文件夹（已按时间排序）
        target_folder_info = folder_list[0]
        merge_to_folder = target_folder_info.path
        
        # 收集要合并的文件夹路径
        folders_to_merge = [info.path for info in folder_list[1:] if os.path.exists(info.path)]
        
        if folders_to_merge:
            # 使用统一的合并操作
            merged_count = MergeOperations.merge_folder_list_to_target(folders_to_merge, merge_to_folder)
            
            if merged_count > 0:
                logging.info(f"[L2][BLREC] 成功合并 {merged_count} 个文件夹到: {merge_to_folder}")
                # 提取标题作为名称（key是tuple: (date, title, suffix)）
                title = key[1] if isinstance(key, tuple) and len(key) > 1 else str(key)
                self.stats.add_success_with_name(title)


class RECHEME:
    """
    重构后的RECHEME处理器，使用统一的时间工具
    """
    
    def __init__(self, flv_manager):
        self.stats = Statistics()
        self.flv_manager = flv_manager
    
    def merge_folders(self, folder_path, skip_keys):
        """
        重构的RECHEME合并算法，使用统一的时间解析
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][录播姬] 路径不存在或不是目录：{folder_path}")
            return False
        
        try:
            # 使用统一的时间解析工具扫描并按时间分组
            time_groups = self._scan_and_group_by_time(folder_path, skip_keys)
            
            # 批量处理所有可合并的组
            mergeable_groups = [(time_info, folder_list) for time_info, folder_list in time_groups.items() 
                              if len(folder_list) > 1]
            
            for time_info, subfolder_list in mergeable_groups:
                main_folder = self._select_main_folder(subfolder_list)
                logging.info(f"[L2][录播姬] 合并时间组 {time_info}：{len(subfolder_list)}个文件夹")
                self._merge_subfolders(main_folder, subfolder_list, skip_keys)
                self.stats.add_success_with_name(f"时间组_{time_info}")
            
            return len(mergeable_groups) > 0
            
        except Exception as e:
            logging.error(f"[L2][录播姬] 合并失败：{folder_path}, 错误：{e}")
            return False
    
    def _scan_and_group_by_time(self, folder_path, skip_keys):
        """
        使用统一的时间解析工具扫描并按时间分组
        """
        time_groups = defaultdict(list)
        
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for subfolder in dirs:
                if any(substring in subfolder for substring in skip_keys):
                    continue
                
                subfolder_path = os.path.join(root, subfolder)
                
                # 使用统一的时间解析工具
                date_time, title = TimeParser.extract_date_title_from_folder(subfolder)
                if date_time:
                    time_info = date_time.strftime("%Y%m%d-%H%M%S")
                    time_groups[time_info].append(subfolder_path)
        
        return time_groups
    
    def _select_main_folder(self, subfolder_list):
        """选择主文件夹（按字典序排序的第一个）"""
        return sorted(subfolder_list)[0]
    
    def _merge_subfolders(self, main_folder, subfolders_to_merge, skip_keys):
        """
        使用统一的文件操作合并子文件夹
        """
        folders_to_merge = []
        
        for folder in subfolders_to_merge:
            if folder == main_folder:
                continue
            if any(substring in folder for substring in skip_keys):
                continue
            if os.path.exists(folder):
                folders_to_merge.append(folder)
        
        if folders_to_merge:
            # 使用统一的合并操作
            merged_count = MergeOperations.merge_folder_list_to_target(folders_to_merge, main_folder)
            
            if merged_count > 0:
                logging.info(f"[L2][录播姬] 成功合并 {merged_count} 个文件夹到: {main_folder}")


class L2Processor(FolderProcessor):
    """
    L2文件夹合并处理器
    
    负责合并符合条件的录播文件夹，支持BLREC和录播姬格式。
    使用统一的通用模块，大幅提升性能和代码复用性。
    """
    
    def __init__(self, path_config, social_folders, skip_folders, recheme_skip_keys, enable=True):
        super().__init__(path_config, social_folders, skip_folders, enable)
        self.recheme_skip_keys = recheme_skip_keys
        self.flv_manager = FlvFileManager()
        self.blrec_processor = BLREC(self.flv_manager)
        self.recheme_processor = RECHEME(self.flv_manager)
    
    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组
        """
        source_path = paths["source"]
        
        if not os.path.exists(source_path):
            return
        
        self._log_debug(f"开始处理L2路径组：{folder_id}")
        
        # 使用统一的文件夹结构处理
        self._process_folder_structure(source_path, self._process_single_folder)
        
        # 合并统计信息
        self.stats.merge_stats(self.blrec_processor.stats)
        self.stats.merge_stats(self.recheme_processor.stats)
    
    def _process_single_folder(self, folder_path, folder_name, target_path=None):
        """
        处理单个文件夹，使用重构后的处理器
        """
        try:
            if self._is_blrec_folder(folder_name):
                # 使用重构的BLREC处理器
                self.blrec_processor.merge_folders(folder_path)
            else:
                # 使用重构的RECHEME处理器
                self.recheme_processor.merge_folders(folder_path, self.recheme_skip_keys)
                
        except Exception as e:
            self._log_error(f"处理文件夹 {folder_name} 失败: {e}")
            self.stats.add_failed(folder_name, str(e))
        finally:
            # 记录缓存统计信息
            self.flv_manager.log_cache_stats()
    
    def _is_blrec_folder(self, folder_name):
        """判断是否为BLREC格式的文件夹"""
        return "【blrec-" in folder_name 