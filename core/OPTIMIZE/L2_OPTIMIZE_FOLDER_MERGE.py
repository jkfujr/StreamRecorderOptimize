# core/L2_OPTIMIZE.py
# 高性能L2文件夹合并处理器

import os, re, logging
from collections import defaultdict
from datetime import datetime

from ..move import move_folder
from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor


class FolderIndex:
    """
    高效的文件夹索引管理器，避免重复扫描
    """
    
    def __init__(self):
        self.folders_by_key = defaultdict(list)  # {(date, title, suffix): [(datetime, path), ...]}
        self.pattern = r"(\d{8})-(\d{6})_(.+)【(blrec-flv|blrec-hls)】"
    
    def scan_and_index(self, folder_path):
        """
        一次性扫描并构建索引，避免重复扫描
        """
        self.folders_by_key.clear()
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return
        
        # 单次遍历构建完整索引
        for root, dirs, files in os.walk(folder_path, topdown=True):
            for folder_name in dirs:
                folder_full_path = os.path.join(root, folder_name)
                parsed_info = self._parse_folder_name(folder_name)
                
                if parsed_info:
                    date, title, suffix = parsed_info
                    key = (date.date(), title, suffix)
                    self.folders_by_key[key].append((date, folder_full_path))
        
        # 对每个组按时间排序
        for key in self.folders_by_key:
            self.folders_by_key[key].sort(key=lambda x: x[0])
    
    def _parse_folder_name(self, folder_name):
        """解析文件夹名"""
        match = re.match(self.pattern, folder_name)
        if match:
            date_str, time_str, title, suffix = match.groups()
            date = datetime.strptime(date_str + "-" + time_str, "%Y%m%d-%H%M%S")
            return date, title, suffix
        return None
    
    def get_mergeable_groups(self):
        """
        获取所有可合并的文件夹组
        返回: [(key, folder_list), ...] 其中folder_list长度>1
        """
        return [(key, folder_list) for key, folder_list in self.folders_by_key.items() 
                if len(folder_list) > 1]


class BLREC:
    """
    优化版本的BLREC处理器，解决O(n²)复杂度问题
    """
    
    def __init__(self):
        self.stats = Statistics()
        self.folder_index = FolderIndex()
    
    def merge_folders(self, folder_path):
        """
        优化的合并算法：O(n log n)复杂度
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][BLREC] 路径不存在或不是目录：{folder_path}")
            return False
        
        try:
            # 单次扫描构建索引
            logging.debug(f"[L2][BLREC] 开始索引文件夹：{folder_path}")
            self.folder_index.scan_and_index(folder_path)
            
            # 批量处理所有可合并的组
            mergeable_groups = self.folder_index.get_mergeable_groups()
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
        合并单个文件夹组
        """
        logging.debug(f"[L2][BLREC] 发现可合并文件夹组：{key}, 共{len(folder_list)}个文件夹")
        
        # 已按时间排序，第一个作为目标文件夹
        merge_to_folder = folder_list[0][1]
        
        # 批量合并其余文件夹
        for _, folder_to_merge in folder_list[1:]:
            if not os.path.exists(folder_to_merge):
                logging.warning(f"[L2][BLREC] 源文件夹不存在，跳过：{folder_to_merge}")
                continue
                
            logging.info(f"[L2][BLREC] 合并: {folder_to_merge} -> {merge_to_folder}")
            self._merge_files(merge_to_folder, folder_to_merge)
            
            try:
                os.rmdir(folder_to_merge)
                logging.debug(f"[L2][BLREC] 已删除空文件夹：{folder_to_merge}")
            except Exception as e:
                logging.error(f"[L2][BLREC] 删除文件夹失败：{folder_to_merge}, 错误：{e}")
        
        # 记录成功统计
        self.stats.add_success_with_name(key[1])  # 使用标题作为名称
    
    def _merge_files(self, target_folder, source_folder):
        """
        将源文件夹中的文件移动到目标文件夹
        """
        if not os.path.exists(source_folder):
            logging.warning(f"[L2][BLREC] 源文件夹不存在，无法合并: {source_folder}")
            return
        
        for filename in os.listdir(source_folder):
            source_file = os.path.join(source_folder, filename)
            target_file = os.path.join(target_folder, filename)
            
            try:
                if os.path.exists(target_file):
                    # 如果目标文件存在，删除旧文件
                    os.remove(target_file)
                    logging.debug(f"[L2][BLREC] 覆盖已存在的文件：{target_file}")
                
                os.rename(source_file, target_file)
                logging.debug(f"[L2][BLREC] 文件移动：{source_file} -> {target_file}")
                
            except Exception as e:
                logging.error(f"[L2][BLREC] 文件移动失败：{source_file} -> {target_file}, 错误：{e}")


class TimeBasedFolder:
    """
    基于时间的文件夹管理器，用于RECHEME优化
    """
    
    def __init__(self):
        self.time_groups = defaultdict(list)  # {time_info: [folder_path, ...]}
    
    def scan_and_group(self, folder_path, skip_keys):
        """
        单次扫描并按时间分组
        """
        self.time_groups.clear()
        
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for subfolder in dirs:
                if any(substring in subfolder for substring in skip_keys):
                    continue
                
                subfolder_path = os.path.join(root, subfolder)
                match = re.search(r"(\d{8}-\d{6})", subfolder)
                if match:
                    time_info = match.group()
                    self.time_groups[time_info].append(subfolder_path)
    
    def get_mergeable_groups(self):
        """
        获取可合并的时间组
        """
        return [(time_info, folder_list) for time_info, folder_list in self.time_groups.items() 
                if len(folder_list) > 1]


class RECHEME:
    """
    优化版本的RECHEME处理器
    """
    
    def __init__(self):
        self.stats = Statistics()
        self.time_manager = TimeBasedFolder()
    
    def merge_folders(self, folder_path, skip_keys):
        """
        优化的RECHEME合并算法
        """
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][录播姬] 路径不存在或不是目录：{folder_path}")
            return False
        
        try:
            # 单次扫描并分组
            self.time_manager.scan_and_group(folder_path, skip_keys)
            
            # 批量处理所有可合并的组
            mergeable_groups = self.time_manager.get_mergeable_groups()
            
            for time_info, subfolder_list in mergeable_groups:
                main_folder = self._select_main_folder(subfolder_list)
                logging.info(f"[L2][录播姬] 合并时间组 {time_info}：{len(subfolder_list)}个文件夹")
                self._merge_subfolders(main_folder, subfolder_list, skip_keys)
                self.stats.add_success_with_name(f"时间组_{time_info}")
            
            return len(mergeable_groups) > 0
            
        except Exception as e:
            logging.error(f"[L2][录播姬] 合并失败：{folder_path}, 错误：{e}")
            return False
    
    def _select_main_folder(self, subfolder_list):
        """选择主文件夹（按字典序排序的第一个）"""
        return sorted(subfolder_list)[0]
    
    def _merge_subfolders(self, main_folder, subfolders_to_merge, skip_keys):
        """
        批量合并子文件夹到主文件夹
        """
        for folder in subfolders_to_merge:
            if folder == main_folder:
                continue
            if any(substring in folder for substring in skip_keys):
                continue
            
            if not os.path.exists(folder):
                continue
            
            try:
                for item in os.listdir(folder):
                    source_item_path = os.path.join(folder, item)
                    target_item_path = os.path.join(main_folder, item)
                    move_folder(source_item_path, target_item_path)
                
                os.rmdir(folder)
                logging.debug(f"[L2][录播姬] 已合并并删除文件夹：{folder}")
                
            except Exception as e:
                logging.error(f"[L2][录播姬] 合并文件夹失败：{folder}, 错误：{e}")


class L2Processor(FolderProcessor):
    """
    L2文件夹合并处理器
    
    负责合并符合条件的录播文件夹，支持BLREC和录播姬格式。
    使用优化算法，大幅提升性能，解决O(n²)复杂度问题。
    """
    
    def __init__(self, path_config, social_folders, skip_folders, recheme_skip_keys, enable=True):
        super().__init__(path_config, social_folders, skip_folders, enable)
        self.recheme_skip_keys = recheme_skip_keys
        self.blrec_processor = BLREC()
        self.recheme_processor = RECHEME()
    
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
        处理单个文件夹，使用优化算法
        """
        try:
            if self._is_blrec_folder(folder_name):
                # 使用优化的BLREC处理器
                self.blrec_processor.merge_folders(folder_path)
            else:
                # 使用优化的RECHEME处理器
                self.recheme_processor.merge_folders(folder_path, self.recheme_skip_keys)
                
        except Exception as e:
            self._log_error(f"处理文件夹 {folder_name} 失败: {e}")
            self.stats.add_failed(folder_name, str(e))
    
    def _is_blrec_folder(self, folder_name):
        """判断是否为BLREC格式的文件夹"""
        return "【blrec-" in folder_name 