# main.py

import asyncio
import time
import schedule
from datetime import datetime

from core.config import config
from core.logs import log, log_print, create_optimize_log
from core.services.statistics_sender import send_statistics_with_image_to_gotify
from core.reporting.formatter import ReportFormatter
from core.processors import L1Processor, L2Processor, L3Processor, L4Processor, L5Processor, L9Processor
from core.services import push_gotify


log()


def create_processors():
    """
    创建所有处理器实例
    
    返回:
        dict: 处理器字典
    """
    processors = {}
    
    # L1_文件移动
    processors['L1'] = L1Processor(
        path_config=config.get_l1_paths(),
        social_folders=config.social_folders,
        api_url=config.recording_url,
        enable=config.l1_enable
    )
    
    # L2_文件夹合并
    processors['L2'] = L2Processor(
        path_config=config.get_l2_paths(),
        social_folders=config.social_folders,
        skip_folders=config.skip_folders,
        recheme_skip_keys=config.recheme_skip_keys,
        enable=config.l2_enable
    )
    
    # L3_时间合并
    processors['L3'] = L3Processor(
        path_config=config.get_l3_paths(),
        skip_folders=config.skip_folders,
        merge_interval=config.l3_merge_interval,
        enable=config.l3_enable
    )
    
    # L4_跨天优化
    processors['L4'] = L4Processor(
        path_config=config.get_l4_paths(),
        skip_folders=config.skip_folders,
        merge_interval=config.l4_merge_interval,
        start_hour=config.l4_cross_day_start_hour,
        end_hour=config.l4_cross_day_end_hour,
        enable=config.l4_enable
    )
    
    # L5_错误时间优化
    processors['L5'] = L5Processor(
        path_config=config.get_l5_paths(),
        skip_folders=config.skip_folders,
        error_pattern=config.l5_error_time_pattern,
        enable=config.l5_enable
    )
    
    # L9_最终移动
    processors['L9'] = L9Processor(
        path_config=config.get_l9_paths(),
        social_folders=config.social_folders,
        skip_folders=config.skip_folders,
        enable=config.l9_enable
    )
    
    return processors


async def run_optimize():
    """执行优化操作"""
    log_print("[MAIN] 开始优化操作")
    
    optimize_log_file = None
    
    # 使用独立的日志文件记录本次优化过程
    with create_optimize_log() as log_file_path:
        optimize_log_file = log_file_path
        log_print(f"[MAIN] 优化日志保存到: {optimize_log_file}")
        processors = create_processors()
        results = {}
        start_time = time.time()
        
        for name, processor in processors.items():
            processor_start = time.time()
            log_print(f"[MAIN] 开始 {name} 操作")
            results[name] = processor.process()
            processor_end = time.time()
            log_print(f"[MAIN] {name} 操作完成，耗时: {processor_end - processor_start:.2f}秒")
        
        total_time = time.time() - start_time
        log_print(f"[MAIN] 所有处理器执行完成，总耗时: {total_time:.2f}秒")
        
        # 生成统计报告
        report = ReportFormatter.create_text_report(results)
        
        # 在控制台打印统计报告
        log_print("\n" + report)
        
        # 推送统计信息 - 优先尝试图片模式
        try:
            gotify_config = {
                'ip': config.gotify_ip,
                'token': config.gotify_token
            }
            
            # 尝试发送带图片的报告
            success = await send_statistics_with_image_to_gotify(
                results, 
                gotify_config, 
                use_image=config.image_push_enable, 
                use_base64=True
            )
            
            if success:
                mode = "图片模式" if config.image_push_enable else "文本模式"
                log_print(f"[MAIN] 统计报告（{mode}）推送成功")
            else:
                if config.image_push_enable:
                    log_print("[MAIN] 图片推送失败，降级为文本模式")
                else:
                    log_print("[MAIN] 文本推送失败")
                # 降级为传统文本推送
                await push_gotify(
                    config.gotify_ip,
                    config.gotify_token,
                    "优化完成",
                    report,
                    priority=3
                )
                log_print("[MAIN] 文本统计报告推送成功")
                
        except Exception as e:
            log_print(f"[Error] 推送统计信息失败: {e}")
    
    log_print(f"[MAIN] 优化操作完成，详细日志已保存到: {optimize_log_file}")


def task_scheduler():
    """
    定时任务
    """
    for t in config.schedule_times:
        schedule.every().day.at(t).do(lambda: asyncio.run(run_optimize()))

    last_log_time = time.time()
    log_interval = 1800

    while True:
        schedule.run_pending()
        time.sleep(1)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if time.time() - last_log_time >= log_interval:
            log_print(f"[计划] 当前时间: {current_time}")

            next_run = schedule.next_run()
            if next_run:
                next_run_time = next_run.strftime("%Y-%m-%d %H:%M:%S")
                log_print(f"[计划] 下次运行时间: {next_run_time}")
            else:
                log_print("[计划] 没有待执行的定时任务。")

            last_log_time = time.time()

if __name__ == "__main__":
    log_print("[MAIN] 程序开始运行")
    log_print(f"[CONFIG] 加载配置完成")
    log_print(f"[CONFIG] L1启用: {config.l1_enable}")
    log_print(f"[CONFIG] L2启用: {config.l2_enable}")
    log_print(f"[CONFIG] L3启用: {config.l3_enable}")
    log_print(f"[CONFIG] L3合并时间间隔: {config.l3_merge_interval}秒")
    log_print(f"[CONFIG] L4启用: {config.l4_enable}")
    log_print(f"[CONFIG] L4跨天合并时间间隔: {config.l4_merge_interval}秒")
    log_print(f"[CONFIG] L4跨天检测时间范围: {config.l4_cross_day_start_hour}:00 - 次日{config.l4_cross_day_end_hour}:00")
    log_print(f"[CONFIG] L5启用: {config.l5_enable}")
    # log_print(f"[CONFIG] L5错误时间模式: {config.l5_error_time_pattern}")
    log_print(f"[CONFIG] L9启用: {config.l9_enable}")
    log_print(f"[CONFIG] 图片推送启用: {config.image_push_enable}")
    
    asyncio.run(run_optimize())
    task_scheduler()
