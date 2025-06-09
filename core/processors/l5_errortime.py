# core/L5_OPTIMIZE_ERROR_TIME.py
# 重构后的L5错误时间修复处理器

import os
import logging

from core.engines import FlvFileManager, FolderIndexerFactory, FileOperations, MergeOperations
from .folder import FolderProcessor


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
            
            # 使用统一的文件合并操作
            success = MergeOperations.merge_folder_contents(error_folder_path, target_folder_path)
            
            if success:
                self.fix_count += 1
                logging.info(f"[L5] 已修复错误时间文件夹: {error_folder_path} -> {target_folder_path}")
                return True
            
        except Exception as e:
            logging.error(f"[L5] 修复错误时间文件夹失败: {error_folder_path}, 错误: {e}")
        
        return False


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
        self.flv_manager = FlvFileManager()
        self.indexer = FolderIndexerFactory.create_error_time_indexer(self.flv_manager)
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
            # 使用统一的错误时间索引器扫描并分类文件夹
            self.indexer.scan_and_index(user_folder_path)
            
            # 获取错误时间文件夹
            error_folders = self.indexer.get_error_folders()
            
            if not error_folders:
                self.stats.add_skipped(user_folder_name, "无错误时间文件夹")
                return
            
            total_fixed = 0
            
            # 处理每个错误时间文件夹
            for error_folder_info in error_folders:
                error_folder_path = error_folder_info.path
                error_title = error_folder_info.title
                error_date = error_folder_info.date  # 这里是从FLV文件提取的真实日期
                
                logging.debug(f"[L5] 处理错误文件夹: {os.path.basename(error_folder_path)}, 标题: {error_title}, FLV日期: {error_date.strftime('%Y-%m-%d')}")
                
                # 查找匹配的正常文件夹
                target_folder_info = self.indexer.find_matching_normal_folder(error_folder_info)
                
                if target_folder_info:
                    # 执行修复
                    if self.fixer.fix_error_folder(error_folder_path, target_folder_info.path):
                        total_fixed += 1
                else:
                    logging.warning(f"[L5] 未找到匹配的目标文件夹: {error_title} ({error_date.strftime('%Y-%m-%d')})")
            
            # 使用统一的文件操作清理空文件夹
            empty_folders_removed = FileOperations.cleanup_empty_folders(user_folder_path)
            
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
        finally:
            # 记录缓存统计信息
            self.flv_manager.log_cache_stats() 