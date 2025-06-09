"""
统计报告发送服务模块

负责将统计报告发送到各种外部服务（如Gotify等）。
"""

import logging
from typing import Dict, Any

from ..reporting.formatter import ReportFormatter


async def send_statistics_with_image_to_gotify(results: Dict[str, Any], gotify_config: Dict[str, str], 
                                             use_image: bool = True, use_base64: bool = True) -> bool:
    """
    发送包含图片的统计报告到Gotify
    
    参数：
        results: 处理器结果字典
        gotify_config: Gotify配置 {'ip': '', 'token': ''}
        use_image: 是否使用图片
        use_base64: 是否使用Base64嵌入图片
        
    返回:
        bool: 发送是否成功
    """
    try:
        from .gotify import push_gotify
        
        if use_image:
            # 生成带图片的报告 - 直接使用ReportFormatter
            report_data = ReportFormatter.create_statistics_report_with_image(results, use_base64, 'PNG')
            if not report_data or not report_data.get('image_data'):
                logging.debug("[StatsSender] 图片生成失败，切换到文本模式")
                use_image = False
            else:
                logging.debug("[StatsSender] 图片报告生成成功，准备发送到Gotify")
                
                # 使用Markdown格式发送
                extras = {
                    "client::display": {
                        "contentType": "text/markdown"
                    }
                }
                
                logging.debug(f"[StatsSender] 发送图片消息，标题: '📊 优化完成 - 统计报告'")
                logging.debug(f"[StatsSender] Markdown内容长度: {len(report_data['markdown_report'])} 字符")
                
                try:
                    success = await push_gotify(
                        gotify_config['ip'],
                        gotify_config['token'],
                        "📊 优化完成 - 统计报告",
                        report_data['markdown_report'],
                        priority=3,
                        extras=extras
                    )
                    
                    if success:
                        logging.info("[StatsSender] 图片消息发送成功")
                        return True
                    else:
                        logging.warning("[StatsSender] 图片消息发送失败 - push_gotify返回False")
                        use_image = False
                        
                except Exception as gotify_error:
                    logging.error(f"[StatsSender] Gotify推送异常: {type(gotify_error).__name__}: {str(gotify_error)}")
                    use_image = False
        
        if not use_image:
            logging.debug("[StatsSender] 使用文本模式发送")
            # 传统文本模式 - 直接使用ReportFormatter
            text_report = "📊 文件夹处理统计报告\n"
            text_report += f"⏰ {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text_report += "=" * 30 + "\n"
            text_report += ReportFormatter.format_statistics(results['L1'], "L1 移动统计")
            text_report += ReportFormatter.format_statistics(results['L2'], "L2 合并统计")
            text_report += ReportFormatter.format_statistics(results['L3'], "L3 时间合并统计")
            text_report += ReportFormatter.format_statistics(results['L4'], "L4 跨天优化统计")
            text_report += ReportFormatter.format_statistics(results['L5'], "L5 错误时间优化统计")
            text_report += ReportFormatter.format_statistics(results['L9'], "L9 移动统计")
            
            logging.debug(f"[StatsSender] 文本消息长度: {len(text_report)} 字符")
            
            try:
                success = await push_gotify(
                    gotify_config['ip'],
                    gotify_config['token'],
                    "✅ 优化完成",
                    text_report,
                    priority=3
                )
                
                if success:
                    logging.info("[StatsSender] 文本消息发送成功")
                else:
                    logging.warning("[StatsSender] 文本消息发送失败 - push_gotify返回False")
                    
                return success
                
            except Exception as text_error:
                logging.error(f"[StatsSender] 文本消息推送异常: {type(text_error).__name__}: {str(text_error)}")
                return False
            
    except Exception as e:
        logging.error(f"[StatsSender] send_statistics_with_image_to_gotify整体异常: {type(e).__name__}: {str(e)}")
        
        # 尝试发送简单的完成通知
        try:
            from .gotify import push_gotify
            await push_gotify(
                gotify_config['ip'],
                gotify_config['token'],
                "⚠️ 优化完成",
                f"优化已完成，但统计报告发送失败。\n错误: {str(e)}",
                priority=2
            )
        except:
            logging.error("[StatsSender] 连简单通知也发送失败")
        return False 


async def send_simple_statistics_to_gotify(results: Dict[str, Any], gotify_config: Dict[str, str]) -> bool:
    """
    发送简单的统计报告到Gotify（仅文本）
    
    参数：
        results: 处理器结果字典
        gotify_config: Gotify配置
        
    返回:
        bool: 发送是否成功
    """
    try:
        from .gotify import push_gotify
        
        # 生成简单的文本报告
        text_report = ReportFormatter.create_simple_summary(results)
        
        success = await push_gotify(
            gotify_config['ip'],
            gotify_config['token'],
            "✅ 优化完成",
            text_report,
            priority=3
        )
        
        if success:
            logging.info("[StatsSender] 简单统计消息发送成功")
        else:
            logging.warning("[StatsSender] 简单统计消息发送失败")
            
        return success
        
    except Exception as e:
        logging.error(f"[StatsSender] 简单统计发送异常: {e}")
        return False 