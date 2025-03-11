# main.py

import asyncio
import os
import time
import schedule
from datetime import datetime

from core.gotify import push_gotify
from core.logs import log, log_print
from core.L1_OPTIMIZE import move_folders
from core.L2_OPTIMIZE import L2_Main
from core.L9_OPTIMIZE import L9_Main
from core.statistics import format_statistics


log()

### 配置 ###

# Gotify
GLOBAL_GOTIFY_IP = "http://10.0.0.101:18101"
GLOBAL_GOTIFY_TOKEN = "A43buC_qB8d8sfk"

# 定时任务
GLOBAL_TIMES = [
    "00:00",
    "02:00",
    "04:00",
    "06:00",
    "08:00",
    "10:00",
    "12:00",
    "14:00",
    "16:00",
    "18:00",
    "20:00",
]

REC_PATH = {
    "AAA": r"F:\Video\录播\综合",
    "PPP": r"F:\Video\录播\P家",
    "TTT": r"F:\Video\录播\测试",
}

REC_PENDING_PATH = {
    "AAA": r"F:\Video\AAAAAAAAAA",
    "PPP": r"F:\Video\PPPPPPPPPP",
    "TTT": r"F:\Video\TTTTTTTTTT",
}

REC_COMPLETE_PATH = {
    "AAA": r"F:\Video\AAAAAAAAAA\综合",
    "PPP": r"F:\Video\PPPPPPPPPP\P家",
    "TTT": r"F:\Video\PPPPPPPPPP\测试",
}


### L1 ###
# (L1全局)路径
L1_OPTIMIZE_GLOBAL_PATH = {}
for key in REC_PATH:
    L1_OPTIMIZE_GLOBAL_PATH[key] = {
        "source": REC_PATH[key],
        "target": REC_PENDING_PATH[key]
    }

# (L1全局)是否启用移动文件夹
L1_OPTIMIZE_GLOBAL_MOVE = True
# (L1全局)社团文件夹名称列表
L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS = ["NIJISANJI", "HOLOLIVE", "VSPO"]

### L2 ###
# (L2全局)路径
L2_OPTIMIZE_GLOBAL_PATH = {}
for key in REC_PENDING_PATH:
    L2_OPTIMIZE_GLOBAL_PATH[key] = {
        "source": REC_PENDING_PATH[key]
    }


# (L2全局)需要跳过的特殊文件夹名称列表
L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS = ["综合", "P家", "000", "111", "222", "333", "444"]
# (L2录播姬)需要跳过的录播子文件夹
L2_OPTIMIZE_RECHEME_SKIP_KEY = [
    "【blrec-flv】",
    "【blrec-hls】",
    "000_部分丢失",
    "1970",
]


### L9 ###
# (L9全局)路径
L9_OPTIMIZE_GLOBAL_PATH = {}
for key in REC_PENDING_PATH:
    if key in REC_COMPLETE_PATH:
        L9_OPTIMIZE_GLOBAL_PATH[key] = {
            "source": REC_PENDING_PATH[key],
            "target": REC_COMPLETE_PATH[key]
        }

# (L9全局)是否启用移动文件夹
L9_OPTIMIZE_GLOBAL_MOVE = True


### 主要操作 ###


def get_l2_folder(directory_path):
    """
    获取指定目录下的所有子文件夹名称。

    参数:
        directory_path (str): 目录路径。

    返回:
        list: 子文件夹名称列表。
    """
    try:
        return [
            folder
            for folder in os.listdir(directory_path)
            if os.path.isdir(os.path.join(directory_path, folder))
        ]
    except FileNotFoundError:
        log_print(f"[统计] 目录不存在: {directory_path}")
        return []


def run_optimize():
    """执行优化操作"""
    log_print("[MAIN] 开始优化操作")

    # L1 移动操作
    log_print("[MAIN] 开始 L1 移动操作")
    l1_stats = move_folders(
        L1_OPTIMIZE_GLOBAL_PATH,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        enable_move=L1_OPTIMIZE_GLOBAL_MOVE
    )

    # L2 优化操作
    log_print("[MAIN] 开始 L2 优化操作")
    l2 = L2_Main(
        L2_OPTIMIZE_GLOBAL_PATH,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
        L2_OPTIMIZE_RECHEME_SKIP_KEY,
        L2_OPTIMIZE_GLOBAL_MOVE=True
    )
    l2_stats = l2.process()

    # L9 移动操作
    log_print("[MAIN] 开始 L9 移动操作")
    l9 = L9_Main(
        L9_OPTIMIZE_GLOBAL_PATH,
        L9_OPTIMIZE_GLOBAL_MOVE,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
    )
    l9_stats = l9.process()

    # 生成统计报告
    report = "文件夹处理统计报告\n"
    report += "==================\n"
    report += format_statistics(l1_stats, "L1 移动统计")
    report += format_statistics(l2_stats, "L2 合并统计")
    report += format_statistics(l9_stats, "L9 移动统计")
    
    # 在控制台打印统计报告
    log_print("\n" + report)
    
    # 推送统计信息
    try:
        asyncio.run(
            push_gotify(
                GLOBAL_GOTIFY_IP,
                GLOBAL_GOTIFY_TOKEN,
                "优化完成",
                report,
                priority=3
            )
        )
    except Exception as e:
        log_print(f"[Error] 推送统计信息失败: {e}")


def task_scheduler():
    """
    定时任务
    """
    for t in GLOBAL_TIMES:
        schedule.every().day.at(t).do(run_optimize)

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
    run_optimize()
    task_scheduler()
