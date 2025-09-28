#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
L1-L9处理器一致性测试脚本

测试目标：
1. 验证各模块处理效果的一致性
2. 重现social文件夹内错误时间文件夹未被处理的问题
3. 确保代码逻辑调整后功能正常

使用虚拟数据，不依赖API
"""

import os
import sys
import shutil
import tempfile
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.processors.l1_move import L1Processor
from core.processors.l2_merge import L2Processor  
from core.processors.l3_time import L3Processor
from core.processors.l4_crossday import L4Processor
from core.processors.l5_errortime import L5Processor
from core.processors.l9_final import L9Processor


class VirtualDataGenerator:
    """虚拟测试数据生成器"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.users = [
            "TestUser1", 
            "TestUser2_Social",  # 模拟social类型用户
            "NormalUser"
        ]
        
    def create_test_structure(self):
        """创建测试文件夹结构"""
        
        # 创建基础目录结构
        source_dir = self.base_path / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建普通用户文件夹
        self._create_normal_user_folders(source_dir)
        
        # 创建social用户文件夹（包含子文件夹）
        self._create_social_user_folders(source_dir)
        
        # 创建错误时间文件夹场景
        self._create_error_time_scenarios(source_dir)
        
        return source_dir
    
    def _create_normal_user_folders(self, source_dir: Path):
        """创建普通用户文件夹"""
        user_dir = source_dir / "NormalUser"
        user_dir.mkdir(exist_ok=True)
        
        # 正常录播文件夹
        normal_folder = user_dir / "20250927-140000_测试直播【NormalUser】"
        normal_folder.mkdir(exist_ok=True)
        self._create_flv_files(normal_folder, "20250927-140000-123_测试直播")
        
        # 错误时间文件夹
        error_folder = user_dir / "19700101-080000_测试直播【NormalUser】"
        error_folder.mkdir(exist_ok=True)
        self._create_flv_files(error_folder, "20250927-140500-456_测试直播")
    
    def _create_social_user_folders(self, source_dir: Path):
        """创建social用户文件夹（包含子文件夹）"""
        user_dir = source_dir / "TestUser2_Social"
        user_dir.mkdir(exist_ok=True)
        
        # 创建子文件夹
        sub_folder = user_dir / "SubChannel1"
        sub_folder.mkdir(exist_ok=True)
        
        # 子文件夹中的正常录播
        normal_folder = sub_folder / "20250927-150000_子频道直播【SubChannel1】"
        normal_folder.mkdir(exist_ok=True)
        self._create_flv_files(normal_folder, "20250927-150000-789_子频道直播")
        
        # 子文件夹中的错误时间文件夹 - 这是关键测试点！
        error_folder = sub_folder / "19700101-080000_子频道直播【SubChannel1】"
        error_folder.mkdir(exist_ok=True)
        self._create_flv_files(error_folder, "20250927-150300-012_子频道直播")
    
    def _create_error_time_scenarios(self, source_dir: Path):
        """创建各种错误时间场景"""
        user_dir = source_dir / "TestUser1"
        user_dir.mkdir(exist_ok=True)
        
        # 场景1：标准错误时间修复
        normal1 = user_dir / "20250927-120000_游戏直播【TestUser1】"
        normal1.mkdir(exist_ok=True)
        self._create_flv_files(normal1, "20250927-120000-111_游戏直播")
        
        error1 = user_dir / "19700101-080000_游戏直播【TestUser1】"
        error1.mkdir(exist_ok=True)
        self._create_flv_files(error1, "20250927-120200-222_游戏直播")
        
        # 场景2：跨天录播
        normal2 = user_dir / "20250926-235500_深夜聊天【TestUser1】"
        normal2.mkdir(exist_ok=True)
        self._create_flv_files(normal2, "20250926-235500-333_深夜聊天")
        
        error2 = user_dir / "19700101-080000_深夜聊天【TestUser1】"
        error2.mkdir(exist_ok=True)
        self._create_flv_files(error2, "20250927-000100-444_深夜聊天")
    
    def _create_flv_files(self, folder: Path, base_name: str):
        """创建FLV相关文件"""
        # 创建FLV文件
        flv_file = folder / f"{base_name}.flv"
        flv_file.write_text("fake flv content")
        
        # 创建封面文件
        cover_file = folder / f"{base_name}.cover.jpg"
        cover_file.write_text("fake cover content")
        
        # 创建XML文件
        xml_file = folder / f"{base_name}.xml"
        xml_file.write_text("fake xml content")


class L1L9ConsistencyTester:
    """L1-L9处理器一致性测试器"""
    
    def __init__(self):
        # 在当前运行目录下创建测试目录
        current_dir = os.getcwd()
        
        # 生成时间戳子文件夹 (年月日-时分秒格式)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # 创建带时间戳的测试目录
        base_test_dir = Path(current_dir) / "test_results"
        self.test_dir = base_test_dir / timestamp
        
        # 确保基础目录存在
        base_test_dir.mkdir(exist_ok=True)
        
        # 创建时间戳子目录
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        self.source_dir = self.test_dir / "source"
        self.results = {}
        
        # 配置日志
        self.setup_logging()
        
        print(f"测试目录: {self.test_dir}")
        print(f"时间戳: {timestamp}")
        
        # 创建虚拟数据
        self.create_test_data()
        
    def create_test_data(self):
        """创建测试数据"""
        generator = VirtualDataGenerator(self.test_dir)
        self.source_dir = generator.create_test_structure()
    
    def setup_logging(self):
        """设置日志配置"""
        log_file = self.test_dir / "test_log.log"
        
        # 清除现有的处理器
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s')
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # 配置根日志器
        logging.root.setLevel(logging.DEBUG)
        logging.root.addHandler(file_handler)
        logging.root.addHandler(console_handler)
    
    def run_full_test(self):
        """运行完整的L1-L9测试流程"""
        print("=" * 60)
        print("开始L1-L9处理器一致性测试")
        print("=" * 60)
        
        source_dir = self.source_dir
        
        print(f"测试数据已生成: {source_dir}")
        self._print_folder_structure(source_dir)
        
        # 创建路径配置
        path_config = {
            "group1": {
                "source": str(source_dir),
                "target": str(self.test_dir / "target")
            }
        }
        
        skip_folders = ["skip_test"]
        
        # 测试各个处理器
        processors = [
            ("L1", L1Processor(path_config, [], skip_folders)),
            ("L2", L2Processor(path_config, [], skip_folders, [])),  # social_folders, skip_folders, recheme_skip_keys
            ("L3", L3Processor(path_config, skip_folders, 60)),  # merge_interval
            ("L4", L4Processor(path_config, skip_folders, 60)),  # merge_interval
            ("L5", L5Processor(path_config, skip_folders)),  # 关键测试点
            ("L9", L9Processor(path_config, [], skip_folders))  # social_folders
        ]
        
        # 为每个处理器创建独立的测试环境
        for name, processor in processors:
            print(f"\n{'='*20} 测试 {name} 处理器 {'='*20}")
            
            # 复制测试数据
            test_source = self.test_dir / f"{name}_test_source"
            if test_source.exists():
                shutil.rmtree(test_source)
            shutil.copytree(source_dir, test_source)
            
            # 更新处理器配置
            processor.path_config = {
                "group1": {
                    "source": str(test_source),
                    "target": str(self.test_dir / f"{name}_target")
                }
            }
            
            # 执行处理
            try:
                processor.process()
                self.results[name] = {
                    "success": True,
                    "stats": processor.stats.get_summary(),
                    "source_after": self._analyze_folder_structure(test_source)
                }
                print(f"{name} 处理完成")
                print(f"统计信息: {processor.stats.get_summary()}")
                
            except Exception as e:
                self.results[name] = {
                    "success": False,
                    "error": str(e),
                    "source_after": self._analyze_folder_structure(test_source)
                }
                print(f"{name} 处理失败: {e}")
        
        # 分析结果
        self._analyze_results()
        
    def _print_folder_structure(self, root_path: Path, prefix=""):
        """打印文件夹结构"""
        if not root_path.exists():
            return
            
        items = sorted(root_path.iterdir())
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir():
                next_prefix = prefix + ("    " if is_last else "│   ")
                self._print_folder_structure(item, next_prefix)
    
    def _analyze_folder_structure(self, root_path: Path):
        """分析文件夹结构，返回统计信息"""
        if not root_path.exists():
            return {"total_folders": 0, "error_time_folders": 0, "normal_folders": 0}
        
        total_folders = 0
        error_time_folders = 0
        normal_folders = 0
        
        for root, dirs, files in os.walk(root_path):
            for dir_name in dirs:
                total_folders += 1
                if dir_name.startswith("19700101-080000_"):
                    error_time_folders += 1
                elif "-" in dir_name and "_" in dir_name:
                    normal_folders += 1
        
        return {
            "total_folders": total_folders,
            "error_time_folders": error_time_folders,
            "normal_folders": normal_folders
        }
    
    def _analyze_results(self):
        """分析测试结果"""
        print("\n" + "="*60)
        print("测试结果分析")
        print("="*60)
        
        # L5关键问题分析
        if "L5" in self.results:
            l5_result = self.results["L5"]
            print(f"\n【L5错误时间处理器分析】")
            print(f"处理成功: {l5_result['success']}")
            
            if l5_result['success']:
                after_stats = l5_result['source_after']
                print(f"处理后错误时间文件夹数量: {after_stats['error_time_folders']}")
                
                if after_stats['error_time_folders'] > 0:
                    print("⚠️  警告：仍有错误时间文件夹未被处理！")
                    print("   这证实了L5处理器无法处理social文件夹内的子文件夹")
                else:
                    print("✅ 所有错误时间文件夹已被处理")
            else:
                print(f"❌ L5处理失败: {l5_result.get('error', 'Unknown error')}")
        
        # 整体一致性分析
        print(f"\n【整体一致性分析】")
        successful_processors = [name for name, result in self.results.items() if result['success']]
        failed_processors = [name for name, result in self.results.items() if not result['success']]
        
        print(f"成功的处理器: {successful_processors}")
        print(f"失败的处理器: {failed_processors}")
        
        # 保存详细结果
        detailed_results_file = self.test_dir / "detailed_results.txt"
        with open(detailed_results_file, 'w', encoding='utf-8') as f:
            f.write("L1-L9处理器测试详细结果\n")
            f.write("=" * 50 + "\n\n")
            
            for name, result in self.results.items():
                f.write(f"处理器: {name}\n")
                f.write(f"成功: {result['success']}\n")
                f.write(f"统计: {result['stats']}\n")
                if result.get('error'):
                    f.write(f"错误: {result['error']}\n")
                f.write("\n")
        
        print(f"\n详细结果已保存到: {detailed_results_file}")


def main():
    """主函数"""
    try:
        tester = L1L9ConsistencyTester()
        tester.run_full_test()
        
        print(f"\n测试完成！结果保存在: {tester.test_dir}")
        print("请检查测试结果以验证L5处理器是否正确处理了social文件夹内的错误时间文件夹")
        
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()