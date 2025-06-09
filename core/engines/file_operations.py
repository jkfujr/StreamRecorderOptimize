"""
文件操作工具模块

提供统一的文件和文件夹操作功能，包括基础操作、高级移动、MD5校验等完整功能。
"""

import os
import shutil
import logging
import hashlib
from typing import Optional


class FileOperations:
    """统一的文件操作工具类 - 完整版"""
    
    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """
        计算文件MD5值
        
        参数:
            file_path (str): 文件路径
            
        返回:
            str: MD5哈希值
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logging.error(f"[FileOps] 计算MD5失败: {file_path}, 错误: {e}")
            return ""
    
    @staticmethod
    def move_folder_advanced(source: str, target: str, enable_move: bool = True, recording_status: Optional[dict] = None) -> bool:
        """
        高级文件夹移动操作，支持MD5校验、智能合并和录制状态检查
        
        参数:
            source (str): 源文件夹路径
            target (str): 目标文件夹路径
            enable_move (bool): 是否启用移动功能
            recording_status (Optional[dict]): 录制状态字典，用于L1处理器
            
        返回:
            bool: 操作是否成功
        """
        if not enable_move:
            logging.info(f"[FileOps] 移动文件夹功能已禁用：{source} -> {target}")
            return False
            
        try:
            if not os.path.exists(source):
                logging.warning(f"[FileOps] 源文件夹不存在: {source}")
                return False
                
            if not os.path.exists(target):
                logging.info(f"[FileOps] 移动文件：{source} -> {target}")
                shutil.move(source, target)
                return True
            else:
                logging.info(f"[FileOps] 目标文件夹已存在，合并内容：{source} -> {target}")
                return FileOperations._merge_folder_contents_with_md5(source, target, recording_status)
                
        except Exception as e:
            logging.error(f"[FileOps] 高级移动操作失败: {source} -> {target}, 错误: {e}")
            return False
    
    @staticmethod
    def _merge_folder_contents_with_md5(source: str, target: str, recording_status: Optional[dict] = None) -> bool:
        """
        使用MD5校验合并文件夹内容
        """
        try:
            for item in os.listdir(source):
                source_item_path = os.path.join(source, item)
                target_item_path = os.path.join(target, item)
                
                if os.path.exists(target_item_path):
                    if os.path.isfile(source_item_path) and os.path.isfile(target_item_path):
                        # 使用MD5比较文件内容
                        source_md5 = FileOperations.calculate_md5(source_item_path)
                        target_md5 = FileOperations.calculate_md5(target_item_path)
                        
                        if source_md5 == target_md5:
                            logging.debug(f"[FileOps] 文件内容相同，删除源文件：{source_item_path}")
                            os.remove(source_item_path)
                            FileOperations.cleanup_empty_folders_recursive(os.path.dirname(source_item_path), recording_status)
                        else:
                            logging.debug(f"[FileOps] 目标位置已存在同名项且文件内容不同，跳过：{target_item_path}")
                    else:
                        logging.debug(f"[FileOps] 目标位置已存在同名项，跳过：{target_item_path}")
                    continue
                    
                logging.debug(f"[FileOps] 移动项：{source_item_path} -> {target_item_path}")
                shutil.move(source_item_path, target_item_path)
            
            # 尝试删除空的源文件夹
            try:
                FileOperations.cleanup_empty_folders_recursive(source, recording_status)
            except OSError:
                logging.debug(f"[FileOps] 源文件夹未完全清空，未删除：{source}")
            
            return True
            
        except Exception as e:
            logging.error(f"[FileOps] MD5合并失败: {source} -> {target}, 错误: {e}")
            return False
    
    @staticmethod
    def cleanup_empty_folders_recursive(directory: str, recording_status: Optional[dict] = None) -> int:
        """
        递归删除空文件夹，支持录制状态检查
        
        参数:
            directory (str): 需要检查并删除的文件夹路径
            recording_status (Optional[dict]): 文件夹的录制状态字典
            
        返回:
            int: 删除的文件夹数量
        """
        deleted_count = 0
        
        if not os.path.isdir(directory):
            return deleted_count
            
        try:
            # 先递归处理子文件夹
            for folder_name in os.listdir(directory):
                folder_path = os.path.join(directory, folder_name)
                if os.path.isdir(folder_path):
                    deleted_count += FileOperations.cleanup_empty_folders_recursive(folder_path, recording_status)
            
            # 检查文件夹是否为空
            if not os.listdir(directory):
                # 获取文件夹名称
                folder_name = os.path.basename(directory)
                
                # 如果提供了录制状态，检查是否正在录制或直播
                if recording_status is not None:
                    folder_status = recording_status.get(folder_name)
                    if folder_status and (folder_status["recording"] or folder_status["streaming"]):
                        logging.debug(f"[FileOps] 文件夹正在直播或录制中，跳过删除：{directory}")
                        return deleted_count

                # 删除空文件夹
                os.rmdir(directory)
                logging.debug(f"[FileOps] 已删除空文件夹：{directory}")
                deleted_count += 1
                
        except Exception as e:
            logging.error(f"[FileOps] 递归删除空文件夹失败: {directory}, 错误: {e}")
        
        return deleted_count

    @staticmethod
    def move_files_between_folders(source_folder: str, target_folder: str) -> bool:
        """
        将源文件夹中的所有文件移动到目标文件夹
        
        参数:
            source_folder (str): 源文件夹路径
            target_folder (str): 目标文件夹路径
            
        返回:
            bool: 操作是否成功
        """
        try:
            if not os.path.exists(source_folder):
                logging.warning(f"[FileOps] 源文件夹不存在: {source_folder}")
                return False
            
            if not os.path.exists(target_folder):
                logging.warning(f"[FileOps] 目标文件夹不存在: {target_folder}")
                return False
            
            for item in os.listdir(source_folder):
                source_path = os.path.join(source_folder, item)
                target_path = os.path.join(target_folder, item)
                
                if os.path.exists(target_path):
                    # 处理重名文件，添加时间戳后缀
                    base_name, ext = os.path.splitext(item)
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_name = f"{base_name}_{timestamp}{ext}"
                    target_path = os.path.join(target_folder, new_name)
                    logging.debug(f"[FileOps] 文件重名，重命名为: {new_name}")
                
                shutil.move(source_path, target_folder)
                logging.debug(f"[FileOps] 移动文件: {source_path} -> {target_folder}")
            
            return True
            
        except Exception as e:
            logging.error(f"[FileOps] 移动文件失败: {source_folder} -> {target_folder}, 错误: {e}")
            return False
    
    @staticmethod
    def cleanup_empty_folders(root_folder: str) -> int:
        """
        清理指定文件夹下的所有空文件夹（非递归，兼容性保持）
        
        参数:
            root_folder (str): 根文件夹路径
            
        返回:
            int: 清理的空文件夹数量
        """
        empty_count = 0
        
        try:
            if not os.path.exists(root_folder):
                return 0
                
            for folder_name in os.listdir(root_folder):
                folder_path = os.path.join(root_folder, folder_name)
                if os.path.isdir(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
                    logging.debug(f"[FileOps] 已删除空文件夹: {folder_path}")
                    empty_count += 1
                    
        except Exception as e:
            logging.error(f"[FileOps] 清理空文件夹失败: {root_folder}, 错误: {e}")
        
        return empty_count
    
    @staticmethod
    def remove_empty_folder(folder_path: str) -> bool:
        """
        删除单个空文件夹
        
        参数:
            folder_path (str): 文件夹路径
            
        返回:
            bool: 是否成功删除
        """
        try:
            if os.path.exists(folder_path) and not os.listdir(folder_path):
                os.rmdir(folder_path)
                logging.debug(f"[FileOps] 已删除空文件夹: {folder_path}")
                return True
            return False
        except Exception as e:
            logging.error(f"[FileOps] 删除文件夹失败: {folder_path}, 错误: {e}")
            return False
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> bool:
        """
        确保目录存在，不存在则创建
        
        参数:
            directory_path (str): 目录路径
            
        返回:
            bool: 目录是否存在或创建成功
        """
        if os.path.exists(directory_path):
            return True
        
        try:
            os.makedirs(directory_path)
            logging.debug(f"[FileOps] 创建目录: {directory_path}")
            return True
        except Exception as e:
            logging.error(f"[FileOps] 创建目录失败: {directory_path}, 错误: {e}")
            return False


class MergeOperations:
    """文件夹合并操作工具类"""
    
    @staticmethod
    def merge_folder_contents(source_folder: str, target_folder: str) -> bool:
        """
        将源文件夹的内容合并到目标文件夹，然后删除源文件夹
        
        参数:
            source_folder (str): 源文件夹路径
            target_folder (str): 目标文件夹路径
            
        返回:
            bool: 操作是否成功
        """
        try:
            # 移动文件
            if FileOperations.move_files_between_folders(source_folder, target_folder):
                # 删除空的源文件夹
                return FileOperations.remove_empty_folder(source_folder)
            return False
            
        except Exception as e:
            logging.error(f"[MergeOps] 合并文件夹失败: {source_folder} -> {target_folder}, 错误: {e}")
            return False
    
    @staticmethod
    def merge_folder_list_to_target(folder_list: list, target_folder: str) -> int:
        """
        将文件夹列表中的所有文件夹合并到目标文件夹
        
        参数:
            folder_list (list): 要合并的文件夹路径列表
            target_folder (str): 目标文件夹路径
            
        返回:
            int: 成功合并的文件夹数量
        """
        merge_count = 0
        
        for folder_path in folder_list:
            if folder_path != target_folder:  # 避免自己合并自己
                if MergeOperations.merge_folder_contents(folder_path, target_folder):
                    merge_count += 1
        
        return merge_count 