# core/L5_OPTIMIZE_ERROR_TIME.py
# 高性能L5错误时间修复处理器

import os
import glob
import shutil
import logging
import re
from datetime import datetime
from collections import defaultdict

from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor


class ErrorTimeFolderIndex:
    """
    错误时间文件夹索引管理器，用于分离和分析错误时间戳文件夹
    """
    
    def __init__(self, error_pattern="19700101-080000"):
        self.error_pattern = error_pattern
        self.error_folders = []     # [(title, folder_path, flv_date), ...]
        self.normal_folders = {}    # {(date, title): folder_path, ...}
        self.flv_cache = {}         # {folder_path: (flv_file, flv_date), ...}
    
    def scan_user_folder(self, user_folder, user_name):
        """
        扫描用户文件夹，分离错误和正常文件夹
        """
        self.error_folders.clear()
        self.normal_folders.clear()
        self.flv_cache.clear()
        
        if not os.path.exists(user_folder):
            logging.warning(f"[L5] 用户文件夹不存在: {user_folder}")
            return
        
        logging.debug(f"[L5] 开始扫描用户文件夹: {user_name}")
        
        for folder_name in os.listdir(user_folder):
            folder_path = os.path.join(user_folder, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            try:
                if folder_name.startswith(f"{self.error_pattern}_"):
                    # 错误时间文件夹
                    self._process_error_folder(folder_name, folder_path)
                else:
                    # 正常文件夹
                    self._process_normal_folder(folder_name, folder_path)
                    
            except Exception as e:
                logging.error(f"[L5] 处理文件夹 {folder_name} 失败: {e}")
        
        logging.debug(f"[L5] 用户 {user_name} 扫描完成: 错误文件夹{len(self.error_folders)}个, 正常文件夹{len(self.normal_folders)}个")
    
    def _process_error_folder(self, folder_name, folder_path):
        """
        处理错误时间文件夹
        """
        # 提取标题：去掉错误时间前缀
        title = folder_name[len(f"{self.error_pattern}_"):]
        
        # 获取FLV文件的真实日期
        flv_date = self._extract_flv_date(folder_path)
        if flv_date:
            self.error_folders.append((title, folder_path, flv_date))
            logging.debug(f"[L5] 发现错误时间文件夹: {folder_name} -> 真实日期: {flv_date.strftime('%Y-%m-%d')}")
        else:
            logging.warning(f"[L5] 错误时间文件夹 {folder_name} 中没有找到有效的FLV文件")
    
    def _process_normal_folder(self, folder_name, folder_path):
        """
        处理正常文件夹
        """
        try:
            # 解析文件夹名：日期_标题
            date_str, title = folder_name.split('_', 1)
            date_time = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
            key = (date_time.date(), title)
            self.normal_folders[key] = folder_path
            logging.debug(f"[L5] 正常文件夹: {folder_name}")
        except ValueError:
            logging.debug(f"[L5] 跳过无法解析的文件夹名: {folder_name}")
    
    def _extract_flv_date(self, folder_path):
        """
        从文件夹中提取FLV文件的日期
        """
        try:
            flv_files = glob.glob(os.path.join(folder_path, "*.flv"))
            if not flv_files:
                return None
            
            # 取第一个FLV文件分析日期
            flv_file = flv_files[0]
            flv_name = os.path.basename(flv_file)
            
            # 提取日期：YYYYMMDD-HHMMSS-xxx格式
            date_match = re.match(r'(\d{8}-\d{6})', flv_name)
            if date_match:
                date_str = date_match.group(1)
                flv_date = datetime.strptime(date_str, "%Y%m%d-%H%M%S")
                
                # 缓存FLV信息
                self.flv_cache[folder_path] = (flv_file, flv_date)
                return flv_date
                
        except Exception as e:
            logging.error(f"[L5] 提取FLV日期失败: {folder_path}, 错误: {e}")
        
        return None
    
    def get_error_folders(self):
        """
        获取所有错误时间文件夹
        """
        return self.error_folders
    
    def find_matching_normal_folder(self, title, flv_date):
        """
        查找匹配的正常文件夹
        """
        key = (flv_date.date(), title)
        return self.normal_folders.get(key)


class ErrorTimeMatcher:
    """
    错误时间匹配器，负责查找最佳匹配的目标文件夹
    """
    
    def __init__(self):
        self.match_count = 0
    
    def find_best_match(self, error_title, error_flv_date, normal_folders):
        """
        查找最佳匹配的正常文件夹
        
        匹配规则：
        1. 标题完全匹配
        2. FLV日期与文件夹日期匹配
        3. 如果有多个匹配，选择时间最近的
        """
        candidates = []
        
        for (date, title), folder_path in normal_folders.items():
            # 检查标题是否匹配
            if title == error_title and date == error_flv_date.date():
                candidates.append((folder_path, date))
        
        if not candidates:
            return None
        
        # 如果有多个候选，选择第一个（通常按时间排序）
        return candidates[0][0]


class ErrorTimeFixer:
    """
    错误时间修复器，执行文件合并操作
    """
    
    def __init__(self):
        self.fix_count = 0
    
    def fix_error_folder(self, error_folder_path, target_folder_path):
        """
        修复错误时间文件夹：将其内容合并到目标文件夹
        """
        try:
            if not os.path.exists(error_folder_path) or not os.path.exists(target_folder_path):
                logging.error(f"[L5] 文件夹不存在，无法修复: {error_folder_path} -> {target_folder_path}")
                return False
            
            # 移动所有文件
            success = self._move_files(error_folder_path, target_folder_path)
            
            if success:
                # 删除空的错误文件夹
                self._remove_folder(error_folder_path)
                self.fix_count += 1
                logging.info(f"[L5] 已修复错误时间文件夹: {error_folder_path} -> {target_folder_path}")
                return True
            
        except Exception as e:
            logging.error(f"[L5] 修复错误时间文件夹失败: {error_folder_path}, 错误: {e}")
        
        return False
    
    def _move_files(self, src_folder, dest_folder):
        """
        移动文件夹中的所有文件
        """
        try:
            for item in os.listdir(src_folder):
                src_path = os.path.join(src_folder, item)
                dest_path = os.path.join(dest_folder, item)
                
                if os.path.exists(dest_path):
                    # 处理重名文件，添加时间戳后缀
                    base_name, ext = os.path.splitext(item)
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_name = f"{base_name}_fixed_{timestamp}{ext}"
                    dest_path = os.path.join(dest_folder, new_name)
                    logging.debug(f"[L5] 文件重名，重命名为: {new_name}")
                
                shutil.move(src_path, dest_folder)
                logging.debug(f"[L5] 移动文件: {src_path} -> {dest_folder}")
            
            return True
            
        except Exception as e:
            logging.error(f"[L5] 移动文件失败: {src_folder}, 错误: {e}")
            return False
    
    def _remove_folder(self, folder_path):
        """
        删除空文件夹
        """
        try:
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                logging.debug(f"[L5] 已删除空的错误文件夹: {folder_path}")
        except Exception as e:
            logging.error(f"[L5] 删除错误文件夹失败: {folder_path}, 错误: {e}")


class L5Processor(FolderProcessor):
    """
    L5错误时间修复处理器
    
    负责处理录播软件创建的错误时间戳文件夹，将其合并到正确的文件夹中。
    
    处理逻辑：
    1. 识别19700101-080000格式的错误文件夹
    2. 提取其中FLV文件的真实日期和标题
    3. 查找同日期、同标题的正常文件夹
    4. 将错误文件夹内容合并到正常文件夹
    
    使用示例：
    错误文件夹: 19700101-080000_被窝小播电台【小柔Channel】
    FLV文件: 20250521-190844-838_被窝小播电台.flv
    目标文件夹: 20250521-191246_被窝小播电台【小柔Channel】
    操作: 将错误文件夹内容合并到目标文件夹
    """
    
    def __init__(self, path_config, skip_folders, error_pattern="19700101-080000", enable=True):
        super().__init__(path_config, [], skip_folders, enable)
        self.error_pattern = error_pattern
        self.folder_index = ErrorTimeFolderIndex(error_pattern)
        self.matcher = ErrorTimeMatcher()
        self.fixer = ErrorTimeFixer()
    
    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组
        """
        source_path = paths["source"]
        
        if not os.path.exists(source_path):
            return
        
        self._log_debug(f"开始处理L5路径组：{folder_id}")
        
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
        处理用户文件夹的错误时间修复
        """
        logging.info(f"[L5] 开始处理用户错误时间修复: {user_folder_name}")
        
        try:
            # 扫描并分类文件夹
            self.folder_index.scan_user_folder(user_folder_path, user_folder_name)
            
            # 获取错误时间文件夹
            error_folders = self.folder_index.get_error_folders()
            
            if not error_folders:
                self.stats.add_skipped(user_folder_name, "无错误时间文件夹")
                return
            
            total_fixed = 0
            
            # 处理每个错误时间文件夹
            for error_title, error_folder_path, error_flv_date in error_folders:
                logging.debug(f"[L5] 处理错误文件夹: {os.path.basename(error_folder_path)}, 标题: {error_title}, FLV日期: {error_flv_date.strftime('%Y-%m-%d')}")
                
                # 查找匹配的正常文件夹
                target_folder = self.folder_index.find_matching_normal_folder(error_title, error_flv_date)
                
                if target_folder:
                    # 执行修复
                    if self.fixer.fix_error_folder(error_folder_path, target_folder):
                        total_fixed += 1
                else:
                    logging.warning(f"[L5] 未找到匹配的目标文件夹: {error_title} ({error_flv_date.strftime('%Y-%m-%d')})")
            
            # 清理空文件夹
            empty_folders_removed = self._cleanup_empty_folders(user_folder_path)
            
            # 统计结果
            if total_fixed > 0 or empty_folders_removed > 0:
                self.stats.add_success_with_name(
                    f"{user_folder_name} (修复:{total_fixed}, 清理:{empty_folders_removed})"
                )
                logging.info(f"[L5] 用户 {user_folder_name} 错误时间修复完成: 修复{total_fixed}个, 清理{empty_folders_removed}个空文件夹")
            else:
                self.stats.add_skipped(user_folder_name, "无需修复")
                
        except Exception as e:
            self.stats.add_failed(user_folder_name, str(e))
            logging.error(f"[L5] 处理用户文件夹 {user_folder_path} 错误时间修复失败: {e}")
    
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
                    logging.debug(f"[L5] 已删除空文件夹: {folder_path}")
                    empty_count += 1
        except Exception as e:
            logging.error(f"[L5] 清理空文件夹失败: {user_folder}, 错误: {e}")
        
        return empty_count 