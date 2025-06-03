# core/L1_OPTIMIZE.py

import os, requests, logging

from ..move import move_folder, delete_empty_folders
from ..statistics import Statistics
from ..processors.folder_processor import FolderProcessor

def fetch_recording_status(api_url):
    """
    请求API获取录制状态。

    参数:
        api_url (str): API的URL地址。
        
    返回:
        dict: {folder_name: {"recording": bool, "streaming": bool}, ...}
    """
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        status_dict = {
            item["name"]: {
                "recording": item["recording"],
                "streaming": item["streaming"]
            } 
            for item in data
        }
        logging.debug(f"[L1] 获取到的所有直播状态: {status_dict}")
        return status_dict
    except requests.exceptions.RequestException as e:
        logging.error(f"[L1] 请求API失败: {e}")
        raise RuntimeError(f"无法获取直播状态，为安全起见停止所有移动操作: {e}")


class L1Processor(FolderProcessor):
    """
    L1文件移动处理器
    
    负责将录播文件从录制目录移动到待处理目录。
    在移动前会检查录制状态，避免移动正在录制的文件。
    """
    
    def __init__(self, path_config, social_folders, api_url, enable=True):
        """
        初始化L1处理器
        
        参数:
            path_config (dict): 路径配置映射
            social_folders (list): 社团文件夹名称列表
            api_url (str): 录制状态API的URL地址
            enable (bool): 是否启用移动操作
        """
        super().__init__(path_config, social_folders, [], enable)  # L1不需要skip_folders
        self.api_url = api_url
        self.recording_status = {}
    
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
        
        self._log_debug(f"开始处理L1路径组：{folder_id}")
        
        # 确保目标目录存在
        if not self._ensure_target_directory(target_path):
            return
        
        # 使用统一的文件夹结构处理
        self._process_folder_structure(source_path, self._process_single_folder, target_path)
        
        # 删除空文件夹
        try:
            delete_empty_folders(source_path, self.recording_status)
        except Exception as e:
            self._log_error(f"清理空文件夹失败: {e}")
    
    def _process_single_folder(self, folder_path, folder_name, target_path):
        """
        处理单个用户文件夹
        
        参数:
            folder_path (str): 文件夹路径
            folder_name (str): 文件夹名称
            target_path (str): 目标路径
        """
        target_folder_path = os.path.join(target_path, folder_name)
        
        # 检查是否在直播或录制中
        folder_status = self.recording_status.get(folder_name)
        
        self._log_debug(f"处理用户文件夹 {folder_name}，状态: {folder_status}")
        
        if folder_status is not None:
            if folder_status["recording"] or folder_status["streaming"]:
                self._log_debug(f"用户 {folder_name} 正在直播或录制，跳过移动")
                self.stats.add_skipped(folder_name, "正在直播或录制")
                return
        else:
            self._log_debug(f"未找到用户 {folder_name} 的直播状态")

        try:
            move_folder(folder_path, target_folder_path, enable_move=True)
            self._log_debug(f"成功移动文件夹 {folder_name}")
            self.stats.add_success()
        except Exception as e:
            self._log_error(f"移动文件夹 {folder_name} 失败: {e}")
            self.stats.add_failed(folder_name, str(e))
    
    def process(self):
        """
        执行L1移动处理，重写以添加录制状态获取
        
        返回:
            Statistics: 统计信息对象
        """
        if not self.enable:
            self._log_debug("L1处理器已禁用，跳过处理")
            return self.stats
        
        try:
            # 获取录制状态
            self.recording_status = fetch_recording_status(self.api_url)
            self._log_debug("成功获取录制状态")
        except Exception as e:
            self._log_error(f"获取直播状态失败，停止所有移动操作: {e}")
            return self.stats
        
        # 调用父类的处理逻辑
        return super().process()
    
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


# 向后兼容的函数接口（简化版本）
def move_folders(folder_path_id, social_folder_names, enable_move, api_url):
    """
    移动和合并文件夹 - 向后兼容接口

    参数:
        folder_path_id (dict): 文件夹路径映射
        social_folder_names (list): 社团文件夹名称列表
        enable_move (bool): 是否启用移动操作
        api_url (str): 录制状态API的URL地址

    返回:
        Statistics: 统计信息对象
    """
    processor = L1Processor(
        path_config=folder_path_id,
        social_folders=social_folder_names,
        api_url=api_url,
        enable=enable_move
    )
    return processor.process()
