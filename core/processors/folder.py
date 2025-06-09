# core/processors/folder_processor.py

import os
from abc import abstractmethod

from .base import BaseProcessor


class FolderProcessor(BaseProcessor):
    """
    文件夹处理器基类
    
    提供统一的文件夹遍历和处理逻辑，
    L2/L3/L9等需要处理文件夹结构的处理器可以继承此类。
    """
    
    def __init__(self, path_config, social_folders, skip_folders, enable=True):
        """
        初始化文件夹处理器
        
        参数:
            path_config (dict): 路径配置映射
            social_folders (list): 社团文件夹名称列表
            skip_folders (list): 需要跳过的文件夹名称列表
            enable (bool): 是否启用此处理器
        """
        super().__init__(enable)
        self.path_config = path_config
        self.social_folders = social_folders
        self.skip_folders = skip_folders
    
    def _do_process(self):
        """
        实现基础的文件夹遍历处理逻辑
        
        返回:
            Statistics: 处理统计信息
        """
        for folder_id, paths in self.path_config.items():
            self._log_debug(f"开始处理路径组: {folder_id}")
            try:
                self._process_path_group(folder_id, paths)
            except Exception as e:
                self._log_error(f"处理路径组 {folder_id} 失败: {e}")
                self.stats.add_failed(folder_id, str(e))
        
        return self.stats
    
    @abstractmethod
    def _process_path_group(self, folder_id, paths):
        """
        处理单个路径组，由子类实现
        
        参数:
            folder_id (str): 路径组标识
            paths (dict): 路径配置字典
        """
        raise NotImplementedError("子类必须实现 _process_path_group 方法")
    
    def _process_folder_structure(self, source_directory, process_func, target_directory=None):
        """
        统一的文件夹结构处理逻辑
        
        参数:
            source_directory (str): 源目录路径
            process_func (callable): 处理函数，接收(folder_path, folder_name, target_path)参数
            target_directory (str, optional): 目标目录路径
        """
        if not os.path.exists(source_directory):
            self._log_debug(f"源路径不存在，跳过处理: {source_directory}")
            return
        
        self._log_debug(f"开始处理源路径: {source_directory}")
        
        for folder_name in os.listdir(source_directory):
            folder_path = os.path.join(source_directory, folder_name)
            
            # 只处理文件夹
            if not os.path.isdir(folder_path):
                continue
            
            # 检查是否在跳过列表中
            if folder_name in self.skip_folders:
                self.stats.add_skipped(folder_name, "在跳过列表中")
                continue
            
            try:
                if folder_name in self.social_folders:
                    # 处理社团文件夹
                    self._process_social_folder(folder_path, process_func, target_directory)
                else:
                    # 直接处理用户文件夹
                    target_path = os.path.join(target_directory, folder_name) if target_directory else None
                    process_func(folder_path, folder_name, target_path)
            except Exception as e:
                self._log_error(f"处理文件夹 {folder_name} 失败: {e}")
                self.stats.add_failed(folder_name, str(e))
    
    def _process_social_folder(self, social_folder_path, process_func, target_directory=None):
        """
        处理社团文件夹
        
        参数:
            social_folder_path (str): 社团文件夹路径
            process_func (callable): 处理函数
            target_directory (str, optional): 目标目录路径
        """
        social_folder_name = os.path.basename(social_folder_path)
        self._log_debug(f"开始处理社团文件夹: {social_folder_name}")
        
        # 如果有目标目录，确保社团目录存在
        target_social_path = None
        if target_directory:
            target_social_path = os.path.join(target_directory, social_folder_name)
            if not os.path.exists(target_social_path):
                try:
                    os.makedirs(target_social_path)
                    self._log_debug(f"创建目标社团目录: {target_social_path}")
                except Exception as e:
                    self._log_error(f"创建目标社团目录失败: {e}")
                    return
        
        # 遍历社团文件夹下的用户文件夹
        for user_folder_name in os.listdir(social_folder_path):
            user_folder_path = os.path.join(social_folder_path, user_folder_name)
            
            if not os.path.isdir(user_folder_path):
                continue
            
            if user_folder_name in self.skip_folders:
                self.stats.add_skipped(user_folder_name, f"在跳过列表中 (社团: {social_folder_name})")
                continue
            
            try:
                target_user_path = os.path.join(target_social_path, user_folder_name) if target_social_path else None
                process_func(user_folder_path, user_folder_name, target_user_path)
            except Exception as e:
                self._log_error(f"处理用户文件夹 {user_folder_name} 失败 (社团: {social_folder_name}): {e}")
                self.stats.add_failed(user_folder_name, f"处理失败 (社团: {social_folder_name}): {str(e)}")
    
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
            self._log_debug(f"创建目标目录: {target_directory}")
            return True
        except Exception as e:
            self._log_error(f"创建目录 {target_directory} 失败: {e}")
            return False 