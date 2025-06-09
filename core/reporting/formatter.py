"""
报告格式化模块

包含各种格式的报告生成和输出功能。
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .statistics import Statistics


class ReportFormatter:
    """报告格式化器"""
    
    @staticmethod
    def format_statistics(stats: Statistics, title: str) -> str:
        """格式化统计信息为易读的文本"""
        text = f"\n===== {title} =====\n"
        text += f"总数: {stats.total} | 成功: {stats.success} | 失败: {stats.failed} | 跳过: {stats.skipped}\n"
        
        if stats.failed_names:
            text += "\n失败:\n"
            for item in stats.failed_names:
                text += f"- {item['name']}: {item['reason']}\n"
                
        if stats.skip_reasons:
            text += "\n跳过:\n"
            
            # 对于L9，按子文件夹数量分组优化显示
            if "L9" in title:
                # 收集所有子文件夹数量相关的原因
                folder_count_users = []
                other_reasons = {}
                
                for reason, names in stats.skip_reasons.items():
                    if not names:
                        continue
                        
                    if reason.startswith("子文件夹数量为"):
                        folder_count = reason.split("子文件夹数量为")[1].strip()
                        for name in names:
                            folder_count_users.append(f"{name} ({folder_count})")
                    else:
                        other_reasons[reason] = names
                
                # 显示其他原因
                for reason, names in other_reasons.items():
                    text += f"- {reason}: {len(names)} 个\n"
                    text += ", ".join(names) + "\n"
                
                # 显示子文件夹数量用户（统一标题）
                if folder_count_users:
                    # 按数量排序
                    folder_count_users.sort(key=lambda x: int(x.split('(')[1].split(')')[0]))
                    text += f"- 子文件夹数量大于 2 的用户: {len(folder_count_users)} 个\n"
                    text += ", ".join(folder_count_users) + "\n"
            
            else:
                # 普通格式：用户名用逗号分隔，一行显示
                for reason, names in stats.skip_reasons.items():
                    if not names:
                        continue
                    text += f"- {reason}: {len(names)} 个\n"
                    text += ", ".join(names) + "\n"
                    
        return text
    
    @staticmethod
    def create_text_report(results: Dict[str, Statistics]) -> str:
        """创建文本格式的统计报告"""
        text_report = "文件夹处理统计报告\n"
        text_report += "==================\n"
        text_report += ReportFormatter.format_statistics(results.get('L1', Statistics()), "L1 移动统计")
        text_report += ReportFormatter.format_statistics(results.get('L2', Statistics()), "L2 合并统计")
        text_report += ReportFormatter.format_statistics(results.get('L3', Statistics()), "L3 时间合并统计")
        text_report += ReportFormatter.format_statistics(results.get('L4', Statistics()), "L4 跨天优化统计")
        text_report += ReportFormatter.format_statistics(results.get('L5', Statistics()), "L5 错误时间优化统计")
        text_report += ReportFormatter.format_statistics(results.get('L9', Statistics()), "L9 移动统计")
        return text_report
    
    @staticmethod
    def create_markdown_report(results: Dict[str, Statistics], title: str = "文件夹处理统计报告") -> str:
        """创建Markdown格式的统计报告"""
        report = f"# 📊 {title}\n\n"
        report += f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 生成摘要表格
        report += "## 📋 处理器摘要\n\n"
        report += "| 处理器 | 总数 | 成功 | 失败 | 跳过 |\n"
        report += "|--------|------|------|------|------|\n"
        
        processor_names = ['L1', 'L2', 'L3', 'L4', 'L5', 'L9']
        processor_titles = ['移动', '合并', '时间合并', '跨天优化', '错误时间修复', '最终移动']
        
        for name, title in zip(processor_names, processor_titles):
            stats = results.get(name, Statistics())
            report += f"| {name} {title} | {stats.total} | {stats.success} | {stats.failed} | {stats.skipped} |\n"
        
        # 详细信息
        report += "\n## 📖 详细信息\n\n"
        text_report = ReportFormatter.create_text_report(results)
        report += f"```\n{text_report}\n```\n"
        
        return report
    
    @staticmethod
    def create_statistics_report_with_image(results: Dict[str, Statistics], 
                                          use_base64: bool = True, 
                                          image_format: str = 'PNG') -> Optional[Dict[str, Any]]:
        """
        创建包含图片的统计报告
        
        参数：
            results: 处理器结果字典
            use_base64: 是否使用Base64嵌入图片
            image_format: 图片格式 ('PNG' 或 'JPEG')
            
        返回：
            dict: 包含文本报告、Markdown报告和图片信息的字典
        """
        try:
            from ..services.image_generator import StatisticsImageGenerator
        except ImportError:
            logging.warning("无法导入图片生成模块，请安装 Pillow: pip install Pillow")
            return None
        
        # 生成文本报告
        text_report = ReportFormatter.create_text_report(results)
        
        if use_base64:
            try:
                # 使用原始尺寸图片，不压缩
                generator = StatisticsImageGenerator()
                image = generator.generate_statistics_image(text_report, "文件夹处理统计报告")
                
                # 根据用户指定的格式生成base64
                if image_format.upper() == 'JPEG':
                    image_data = generator.image_to_base64(image, format='JPEG', quality=85)
                else:
                    image_data = generator.image_to_base64(image, format='PNG', optimize=True)
                
                base64_size = len(image_data)
                logging.debug(f"生成原始图片，Base64大小: {base64_size/1024:.1f}KB，格式: {image_format}")
                
                # 生成简洁的markdown - 只包含图片，不包含额外文字
                markdown_report = f"![📊 统计报告]({image_data})"
                
            except Exception as e:
                logging.error(f"生成图片失败: {str(e)}")
                # 回退到无图片模式
                markdown_report = ReportFormatter.create_markdown_report(results)
                image_data = None
                
        else:
            # 生成图片和Markdown
            generator = StatisticsImageGenerator()
            markdown_report, image_data = generator.generate_markdown_with_image(
                text_report, "文件夹处理统计报告", use_base64=False
            )
        
        return {
            'text_report': text_report,
            'markdown_report': markdown_report,
            'image_data': image_data,
            'use_base64': use_base64
        }
    
    @staticmethod
    def format_processor_summary(stats: Statistics, processor_name: str) -> str:
        """格式化单个处理器的摘要"""
        if stats.total == 0:
            return f"[{processor_name}] 未执行"
        
        success_rate = (stats.success / stats.total * 100) if stats.total > 0 else 0
        return (f"[{processor_name}] 总计:{stats.total} 成功:{stats.success} "
                f"失败:{stats.failed} 跳过:{stats.skipped} 成功率:{success_rate:.1f}%")
    
    @staticmethod
    def create_simple_summary(results: Dict[str, Statistics]) -> str:
        """创建简单的摘要报告"""
        summary = "📊 处理摘要:\n"
        
        processor_names = ['L1', 'L2', 'L3', 'L4', 'L5', 'L9']
        processor_titles = ['移动', '合并', '时间合并', '跨天优化', '错误时间修复', '最终移动']
        
        for name, title in zip(processor_names, processor_titles):
            stats = results.get(name, Statistics())
            summary += f"{ReportFormatter.format_processor_summary(stats, f'{name} {title}')}\n"
        
        return summary 