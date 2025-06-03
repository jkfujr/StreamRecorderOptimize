# core/processors/base_processor.py

import logging
from abc import ABC, abstractmethod

from ..statistics import Statistics


class BaseProcessor(ABC):
    """
    处理器基类
    
    定义所有处理器的统一接口和通用处理逻辑。
    使用模板方法模式，子类只需实现具体的处理逻辑。
    """
    
    def __init__(self, enable=True):
        """
        初始化处理器
        
        参数:
            enable (bool): 是否启用此处理器
        """
        self.enable = enable
        self.stats = Statistics()
        self.processor_name = self.__class__.__name__
    
    def process(self):
        """
        统一的处理入口
        
        使用模板方法模式，定义处理流程：
        1. 检查是否启用
        2. 执行具体处理逻辑
        3. 处理异常
        4. 返回统计结果
        
        返回:
            Statistics: 处理统计信息
        """
        if not self.enable:
            self._log_disabled()
            return self.stats
        
        try:
            logging.info(f"[{self.processor_name}] 开始处理")
            result = self._do_process()
            logging.info(f"[{self.processor_name}] 处理完成")
            return result
        except Exception as e:
            self._handle_error(e)
            return self.stats
    
    @abstractmethod
    def _do_process(self):
        """
        具体的处理逻辑，由子类实现
        
        返回:
            Statistics: 处理统计信息
        """
        raise NotImplementedError("子类必须实现 _do_process 方法")
    
    def _log_disabled(self):
        """记录处理器被禁用的日志"""
        logging.info(f"[{self.processor_name}] 处理器已禁用")
    
    def _handle_error(self, error):
        """
        统一的错误处理
        
        参数:
            error (Exception): 发生的异常
        """
        error_msg = f"处理过程中发生错误: {str(error)}"
        logging.error(f"[{self.processor_name}] {error_msg}")
        self.stats.add_failed("系统错误", error_msg)
    
    def _log_debug(self, message):
        """记录调试日志"""
        logging.debug(f"[{self.processor_name}] {message}")
    
    def _log_info(self, message):
        """记录信息日志"""
        logging.info(f"[{self.processor_name}] {message}")
    
    def _log_warning(self, message):
        """记录警告日志"""
        logging.warning(f"[{self.processor_name}] {message}")
    
    def _log_error(self, message):
        """记录错误日志"""
        logging.error(f"[{self.processor_name}] {message}") 