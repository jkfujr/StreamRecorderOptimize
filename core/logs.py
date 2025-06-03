# core/logs.py

import os
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from contextlib import contextmanager


def log():
    """
    初始化程序运行日志记录器，记录程序启动、调度等信息。
    """
    logger = logging.getLogger()
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    # 日志目录
    script_directory = os.path.dirname(os.path.abspath(__file__))
    log_directory = os.path.abspath(os.path.join(script_directory, '..', 'logs'))
    
    if not os.path.exists(log_directory):
        try:
            os.makedirs(log_directory)
            print(f"[日志] 创建日志目录: {log_directory}")
        except Exception as e:
            print(f"[日志] 创建日志目录 {log_directory} 失败: {e}")

    # 程序运行日志文件（保持原有格式）
    default_log_file_name = "RECOPT"
    log_file_path = os.path.join(log_directory, default_log_file_name)

    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d.log"
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(processName)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def generate_optimize_log_path():
    """
    生成优化执行日志的文件路径
    
    返回:
        str: 日志文件完整路径
    """
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%Y%m%d-%H%M%S")
    
    # 使用毫秒确保文件名唯一性
    milliseconds = now.microsecond // 1000
    filename = f"{time_str}-{milliseconds:04d}.log"
    
    # 创建日期目录
    script_directory = os.path.dirname(os.path.abspath(__file__))
    log_directory = os.path.abspath(os.path.join(script_directory, '..', 'logs'))
    date_directory = os.path.join(log_directory, date_str)
    
    if not os.path.exists(date_directory):
        try:
            os.makedirs(date_directory)
        except Exception as e:
            print(f"[日志] 创建日期目录 {date_directory} 失败: {e}")
            # 如果创建失败，回退到主日志目录
            return os.path.join(log_directory, filename)
    
    return os.path.join(date_directory, filename)


class OptimizeLogContext:
    """
    优化执行日志上下文管理器
    
    为每次优化执行创建独立的日志文件，确保日志隔离。
    """
    
    def __init__(self):
        self.log_file_path = None
        self.handler = None
        self.logger = None
    
    def __enter__(self):
        # 生成日志文件路径
        self.log_file_path = generate_optimize_log_path()
        
        # 获取根logger
        self.logger = logging.getLogger()
        
        # 创建新的handler用于此次执行
        self.handler = logging.FileHandler(
            self.log_file_path,
            mode='w',  # 每次创建新文件
            encoding='utf-8'
        )
        self.handler.setLevel(logging.DEBUG)
        
        # 设置格式器
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(processName)s - %(message)s"
        )
        self.handler.setFormatter(formatter)
        
        # 添加到logger
        self.logger.addHandler(self.handler)
        
        return self.log_file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 移除handler并关闭文件
        if self.handler and self.logger:
            self.logger.removeHandler(self.handler)
            self.handler.close()


@contextmanager
def create_optimize_log():
    """
    创建优化执行日志的上下文管理器
    
    使用方式:
        with create_optimize_log() as log_file:
            # 执行优化操作
            logging.info("优化开始")
            
    返回:
        str: 日志文件路径
    """
    context = OptimizeLogContext()
    try:
        log_file = context.__enter__()
        yield log_file
    except Exception as e:
        context.__exit__(type(e), e, e.__traceback__)
        raise
    else:
        context.__exit__(None, None, None)


def log_print(message, level="INFO"):
    """
    记录日志并输出到控制台。

    参数:
    - message (str): 需要记录的消息内容。
    - level (str): 日志等级，默认为 'INFO'。可以设置为 'DEBUG'，'INFO'，'WARNING'，'ERROR'，'CRITICAL'。
    """
    logger = logging.getLogger()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.log(level, message)
    level_name = logging.getLevelName(level)
    prefix = f"{level_name}:     "
    print(prefix + message)
