# core/L9_OPTIMIZE.py
# L9最终移动处理器

import os
import shutil
import logging

from core.engines import MergeOperations, FileOperations
from core.reporting import Statistics
from .folder import FolderProcessor


class L9Processor(FolderProcessor):
    """
    L9文件移动处理器
    
    负责将处理完成的文件夹从源路径移动到目标路径。
    支持智能合并，当目标路径已存在时进行合并操作。
    """

    def __init__(self, path_config, social_folders, skip_folders, enable=True):
        """
        初始化L9处理器
        
        参数:
            path_config (dict): 路径配置映射
            social_folders (list): 社团文件夹名称列表
            skip_folders (list): 需要跳过的文件夹名称列表
            enable (bool): 是否启用移动操作
        """
        super().__init__(path_config, social_folders, skip_folders, enable)

    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组
        
        参数:
            folder_id (str): 路径组标识
            paths (dict): 路径配置字典
        """
        source_path = paths["source"]
        target_path = paths["target"]

        if not os.path.exists(source_path):
            return

        self._log_debug(f"开始处理L9路径组：{folder_id}")

        # 使用统一的文件夹结构处理
        self._process_folder_structure(source_path, self._process_single_folder, target_path)

    def _process_single_folder(self, folder_path, folder_name, target_path):
        """
        处理单个文件夹
        
        参数:
            folder_path (str): 文件夹路径
            folder_name (str): 文件夹名称
            target_path (str): 目标路径（完整的目标文件夹路径）
        """
        try:
            # 检查参数是否正确
            if target_path is None:
                self._log_error(f"目标路径为空，跳过处理文件夹: {folder_name}")
                self.stats.add_skipped(folder_name, "目标路径为空")
                return
            
            # 直接使用传入的target_path，不再自己构建路径
            self._process_user_folder_move(folder_path, target_path, folder_name)
        except Exception as e:
            self._log_error(f"处理文件夹 {folder_name} 失败: {e}")
            self.stats.add_failed(folder_name, str(e))

    def _process_user_folder_move(self, user_folder_path, target_folder_path, folder_name):
        """
        处理用户文件夹的移动操作，支持智能合并
        
        参数:
            user_folder_path (str): 用户文件夹路径
            target_folder_path (str): 目标文件夹路径（完整路径）
            folder_name (str): 文件夹名称
        """
        # 添加源路径和目标路径相同的跳过统计
        if os.path.abspath(user_folder_path) == os.path.abspath(target_folder_path):
            self.stats.add_skipped(folder_name, "源路径与目标路径相同")
            return

        # 添加目标路径在源路径下的跳过统计
        if os.path.abspath(target_folder_path).startswith(os.path.abspath(user_folder_path)):
            self.stats.add_skipped(folder_name, "目标路径在源路径下")
            return

        # 获取子文件夹列表
        subfolders = [f for f in os.listdir(user_folder_path) 
                     if os.path.isdir(os.path.join(user_folder_path, f))]

        if len(subfolders) == 1:
            try:
                # 确保目标文件夹的父目录存在
                target_parent = os.path.dirname(target_folder_path)
                if not FileOperations.ensure_directory_exists(target_parent):
                    raise Exception(f"无法创建目标父目录: {target_parent}")
                
                # 检查目标路径是否已存在
                if os.path.exists(target_folder_path):
                    self._log_debug(f"目标路径已存在，执行智能合并: {folder_name}")
                    self._smart_merge_folders(user_folder_path, target_folder_path, folder_name)
                else:
                    # 直接移动
                    shutil.move(user_folder_path, target_folder_path)
                    self._log_debug(f"[L9] 成功移动文件夹: {folder_name}")
                
                self.stats.add_success()
                
            except Exception as e:
                self.stats.add_failed(folder_name, str(e))
                self._log_error(f"[L9] 移动文件夹失败: {folder_name}, 错误: {e}")
        else:
            self.stats.add_skipped(folder_name, f"子文件夹数量为 {len(subfolders)}")

    def _smart_merge_folders(self, source_folder, target_folder, folder_name):
        """
        智能合并文件夹
        
        参数:
            source_folder (str): 源文件夹路径
            target_folder (str): 目标文件夹路径
            folder_name (str): 文件夹名称
        """
        try:
            # 遍历源文件夹中的所有内容
            for item_name in os.listdir(source_folder):
                source_item = os.path.join(source_folder, item_name)
                target_item = os.path.join(target_folder, item_name)
                
                if os.path.isdir(source_item):
                    # 如果是文件夹
                    if os.path.exists(target_item):
                        # 目标文件夹已存在，递归合并
                        self._smart_merge_folders(source_item, target_item, f"{folder_name}/{item_name}")
                        # 合并完成后删除源文件夹（如果为空）
                        try:
                            os.rmdir(source_item)
                            self._log_debug(f"删除空源文件夹: {source_item}")
                        except OSError:
                            # 文件夹不为空，说明有其他内容，记录警告
                            self._log_warning(f"源文件夹非空，无法删除: {source_item}")
                    else:
                        # 目标文件夹不存在，直接移动
                        shutil.move(source_item, target_item)
                        self._log_debug(f"移动子文件夹: {source_item} -> {target_item}")
                else:
                    # 如果是文件
                    if os.path.exists(target_item):
                        # 目标文件已存在，检查是否相同
                        if self._files_are_identical(source_item, target_item):
                            # 文件相同，删除源文件
                            os.remove(source_item)
                            self._log_debug(f"删除重复文件: {source_item}")
                        else:
                            # 文件不同，重命名源文件后移动
                            new_name = self._generate_unique_filename(target_item)
                            shutil.move(source_item, new_name)
                            self._log_debug(f"重命名并移动文件: {source_item} -> {new_name}")
                    else:
                        # 目标文件不存在，直接移动
                        shutil.move(source_item, target_item)
                        self._log_debug(f"移动文件: {source_item} -> {target_item}")
            
            # 尝试删除源文件夹（如果为空）
            try:
                os.rmdir(source_folder)
                self._log_debug(f"删除空源文件夹: {source_folder}")
            except OSError:
                self._log_warning(f"源文件夹非空，无法删除: {source_folder}")
                
        except Exception as e:
            raise Exception(f"智能合并失败: {e}")

    def _files_are_identical(self, file1, file2):
        """
        检查两个文件是否相同（基于大小和修改时间）
        
        参数:
            file1 (str): 文件1路径
            file2 (str): 文件2路径
            
        返回:
            bool: 文件是否相同
        """
        try:
            stat1 = os.stat(file1)
            stat2 = os.stat(file2)
            
            # 比较文件大小和修改时间
            return (stat1.st_size == stat2.st_size and 
                   abs(stat1.st_mtime - stat2.st_mtime) < 1)  # 允许1秒的时间差异
        except Exception:
            return False

    def _generate_unique_filename(self, filepath):
        """
        生成唯一的文件名
        
        参数:
            filepath (str): 原文件路径
            
        返回:
            str: 唯一的文件路径
        """
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_filename = f"{name}_duplicate_{counter}{ext}"
            new_filepath = os.path.join(directory, new_filename)
            if not os.path.exists(new_filepath):
                return new_filepath
            counter += 1

    def _process_social_folder(self, social_folder_path, process_func, target_directory=None):
        """
        重写社团文件夹处理，适配L9的特殊需求
        
        参数:
            social_folder_path (str): 社团文件夹路径
            process_func (callable): 处理函数
            target_directory (str): 目标目录路径
        """
        social_folder_name = os.path.basename(social_folder_path)
        target_social_folder_path = os.path.join(target_directory, social_folder_name)

        # 确保目标社团目录存在
        if not self._ensure_target_directory(target_social_folder_path):
            self.stats.add_failed(social_folder_name, "创建目标目录失败")
            return

        for user_folder_name in os.listdir(social_folder_path):
            user_folder_path = os.path.join(social_folder_path, user_folder_name)

            if not os.path.isdir(user_folder_path):
                continue

            if user_folder_name in self.skip_folders:
                self.stats.add_skipped(user_folder_name, f"在跳过列表中 (社团: {social_folder_name})")
                continue

            # 构建正确的目标用户文件夹路径
            target_user_folder_path = os.path.join(target_social_folder_path, user_folder_name)
            
            # 检查目标路径是否与源路径相同
            if os.path.abspath(user_folder_path) == os.path.abspath(target_user_folder_path):
                self.stats.add_skipped(user_folder_name, f"源路径与目标路径相同 (社团: {social_folder_name})")
                continue

            # 检查目标路径是否在源路径下
            if os.path.abspath(target_user_folder_path).startswith(os.path.abspath(user_folder_path)):
                self.stats.add_skipped(user_folder_name, f"目标路径在源路径下 (社团: {social_folder_name})")
                continue

            try:
                # 直接调用用户文件夹移动方法，传入完整的目标路径
                self._process_user_folder_move(user_folder_path, target_user_folder_path, user_folder_name)
            except Exception as e:
                self.stats.add_failed(user_folder_name, f"处理失败 (社团: {social_folder_name}): {str(e)}")

        # 移动社团文件夹（如果为空）
        try:
            if os.path.exists(social_folder_path) and not os.listdir(social_folder_path):
                os.rmdir(social_folder_path)
                self._log_debug(f"[L9] 删除空的社团文件夹：{social_folder_path}")
        except Exception as e:
            self._log_warning(f"[L9] 删除空社团文件夹失败：{social_folder_path}, 错误: {e}")
    
    def _ensure_target_directory(self, target_directory):
        """
        确保目标目录存在
        
        参数:
            target_directory (str): 目标目录路径
            
        返回:
            bool: 目录是否存在或创建成功
        """
        if os.path.exists(target_directory):
            return True
            
        try:
            os.makedirs(target_directory)
            self._log_debug(f"[L9] 创建目标目录: {target_directory}")
            return True
        except Exception as e:
            self._log_error(f"[L9] 创建目录 {target_directory} 失败: {e}")
            return False


