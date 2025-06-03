# core/L9_OPTIMIZE.py
# L9最终移动处理器

import os, logging

from ..move import move_folder
from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor


class L9Processor(FolderProcessor):
    """
    L9文件移动处理器
    
    负责将处理完成的文件夹从源路径移动到目标路径。
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
        处理用户文件夹的移动操作，根据子文件夹的数量决定是否移动。
        
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
                move_folder(user_folder_path, target_folder_path)
                self.stats.add_success()
                logging.debug(f"[L9] 成功移动文件夹: {folder_name}")
            except Exception as e:
                self.stats.add_failed(folder_name, str(e))
                logging.error(f"[L9] 移动文件夹失败: {folder_name}, 错误: {e}")
        else:
            self.stats.add_skipped(folder_name, f"子文件夹数量为 {len(subfolders)}")

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
                logging.debug(f"[L9] 删除空的社团文件夹：{social_folder_path}")
        except Exception as e:
            logging.warning(f"[L9] 删除空社团文件夹失败：{social_folder_path}, 错误: {e}")
    
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
            logging.debug(f"[L9] 创建目标目录: {target_directory}")
            return True
        except Exception as e:
            logging.error(f"[L9] 创建目录 {target_directory} 失败: {e}")
            return False


