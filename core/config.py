"""
统一配置管理模块

整合所有配置项，提供各个处理模块需要的配置数据。
"""

class GlobalConfig:
    """全局配置管理类"""
    
    def __init__(self):
        # API配置
        self.api_config = {
            "gotify_ip": "http://10.0.0.101:18101",
            "gotify_token": "A43buC_qB8d8sfk", 
            "recording_url": "http://127.0.0.1:11111/api/room"
        }
        
        # 路径配置
        self.path_config = {
            "REC_PATHS": {
                "AAA": r"F:\Video\录播\综合",
                "PPP": r"F:\Video\录播\P家", 
                "TTT": r"F:\Video\录播\测试",
            },
            "PENDING_PATHS": {
                "AAA": r"F:\Video\AAAAAAAAAA",
                "PPP": r"F:\Video\PPPPPPPPPP",
                "TTT": r"F:\Video\TTTTTTTTTT",
            },
            "COMPLETE_PATHS": {
                "AAA": r"F:\Video\AAAAAAAAAA\综合",
                "PPP": r"F:\Video\PPPPPPPPPP\P家",
                "TTT": r"F:\Video\PPPPPPPPPP\测试",
            }
        }
        
        # 处理配置
        self.process_config = {
            # 社团文件夹
            "social_folders": ["NIJISANJI", "HOLOLIVE", "VSPO"],
            # 跳过文件夹
            "skip_folders": ["综合", "P家", "000", "111", "222", "333", "444"],
            # 子文件夹跳过关键字
            "recheme_skip_keys": ["【blrec-flv】", "【blrec-hls】", "000_部分丢失", "1970"],
            # L3合并时间间隔(s)
            "l3_merge_interval": 60,
            # L4跨天合并时间间隔(s)
            "l4_merge_interval": 60,
            # L4跨天检测时间范围
            "l4_cross_day_start_hour": 22,  # 前一天开始检测的小时(22点后)
            "l4_cross_day_end_hour": 2,     # 次日结束检测的小时(2点前)
            # L5错误时间修复配置
            "l5_error_time_pattern": "19700101-080000",  # 错误时间模式
        }
        
        # 模块开关配置
        self.module_switches = {
            "l1_enable": True,   # L1移动开关
            "l2_enable": True,   # L2合并开关  
            "l3_enable": True,   # L3时间合并开关
            "l4_enable": True,   # L4跨天合并开关
            "l5_enable": True,   # L5错误时间修复开关
            "l9_enable": True,   # L9移动开关
        }
        
        # 定时任务配置
        self.schedule_config = {
            "times": [
                "00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
                "12:00", "14:00", "16:00", "18:00", "20:00",
            ]
        }
    
    # API配置访问器
    @property
    def gotify_ip(self):
        return self.api_config["gotify_ip"]
        
    @property
    def gotify_token(self):
        return self.api_config["gotify_token"]
        
    @property
    def recording_url(self):
        return self.api_config["recording_url"]
    
    # 路径配置访问器
    @property
    def rec_paths(self):
        return self.path_config["REC_PATHS"]
        
    @property
    def pending_paths(self):
        return self.path_config["PENDING_PATHS"]
        
    @property
    def complete_paths(self):
        return self.path_config["COMPLETE_PATHS"]
    
    # 处理配置访问器
    @property
    def social_folders(self):
        return self.process_config["social_folders"]
        
    @property
    def skip_folders(self):
        return self.process_config["skip_folders"]
        
    @property
    def recheme_skip_keys(self):
        return self.process_config["recheme_skip_keys"]
        
    @property
    def l3_merge_interval(self):
        return self.process_config["l3_merge_interval"]
        
    @property
    def l4_merge_interval(self):
        return self.process_config["l4_merge_interval"]
    
    @property
    def l4_cross_day_start_hour(self):
        return self.process_config["l4_cross_day_start_hour"]
    
    @property
    def l4_cross_day_end_hour(self):
        return self.process_config["l4_cross_day_end_hour"]
    
    @property
    def l5_error_time_pattern(self):
        return self.process_config["l5_error_time_pattern"]
    
    # 模块开关访问器
    @property
    def l1_enable(self):
        return self.module_switches["l1_enable"]
        
    @property
    def l2_enable(self):
        return self.module_switches["l2_enable"]
        
    @property
    def l3_enable(self):
        return self.module_switches["l3_enable"]
        
    @property
    def l4_enable(self):
        return self.module_switches["l4_enable"]
        
    @property
    def l5_enable(self):
        return self.module_switches["l5_enable"]
        
    @property
    def l9_enable(self):
        return self.module_switches["l9_enable"]
    
    # 定时配置访问器
    @property
    def schedule_times(self):
        return self.schedule_config["times"]
    
    # 各模块路径映射方法
    def get_l1_paths(self):
        """获取L1移动路径映射"""
        return {
            key: {
                "source": self.rec_paths[key],
                "target": self.pending_paths[key]
            }
            for key in self.rec_paths
        }
    
    def get_l2_paths(self):
        """获取L2合并路径映射"""
        return {
            key: {"source": path}
            for key, path in self.pending_paths.items()
        }
    
    def get_l3_paths(self):
        """获取L3时间合并路径映射"""
        return {
            key: {"source": path}
            for key, path in self.pending_paths.items()
        }
    
    def get_l4_paths(self):
        """获取L4跨天合并路径映射"""
        return {
            key: {"source": path}
            for key, path in self.pending_paths.items()
        }
    
    def get_l5_paths(self):
        """获取L5错误时间修复路径映射"""
        return {
            key: {"source": path}
            for key, path in self.pending_paths.items()
        }
    
    def get_l9_paths(self):
        """获取L9移动路径映射"""
        return {
            key: {
                "source": self.pending_paths[key],
                "target": self.complete_paths[key]
            }
            for key in self.pending_paths
            if key in self.complete_paths
        }


# 全局配置实例
config = GlobalConfig() 