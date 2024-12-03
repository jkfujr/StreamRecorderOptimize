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
    "22:00",
]

REC_PATH = {
    "AAA": r"F:\Video\录播\综合",
    "PPP": r"F:\Video\录播\P家",
}

REC_PENDING_PATH = {
    "AAA": r"F:\Video\AAAAAAAAAA",
    "PPP": r"F:\Video\PPPPPPPPPP",
}

REC_COMPLETE_PATH = {
    "AAA": r"F:\Video\AAAAAAAAAA\综合",
    "PPP": r"F:\Video\PPPPPPPPPP\P家",
}


### L1 ###
# (L1全局)路径
L1_OPTIMIZE_GLOBAL_PATH = {
    "AAA": {"source": REC_PATH["AAA"], "target": REC_PENDING_PATH["AAA"]},
    "PPP": {"source": REC_PATH["PPP"], "target": REC_PENDING_PATH["PPP"]},
}

# (L1全局)是否启用移动文件夹
L1_OPTIMIZE_GLOBAL_MOVE = True
# (L1全局)社团文件夹名称列表
L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS = ["NIJISANJI", "HOLOLIVE", "VSPO"]

### L2 ###
# (L2全局)路径
L2_OPTIMIZE_GLOBAL_PATH = {
    "AAA": {"source": REC_PENDING_PATH["AAA"]},
    "PPP": {"source": REC_PENDING_PATH["PPP"]},
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
L9_OPTIMIZE_GLOBAL_PATH = {
    "AAA": {"source": REC_PENDING_PATH["AAA"], "target": REC_COMPLETE_PATH["AAA"]},
    "PPP": {"source": REC_PENDING_PATH["PPP"], "target": REC_COMPLETE_PATH["PPP"]},
}

# (L9全局)是否启用移动文件夹
L9_OPTIMIZE_GLOBAL_MOVE = True


### 主要操作 ###


def L2_OPTIMIZE():
    l2_main = L2_Main(
        L2_OPTIMIZE_GLOBAL_PATH,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
        L2_OPTIMIZE_RECHEME_SKIP_KEY,
    )
    l2_main.process()


def L9_OPTIMIZE():
    l9_main = L9_Main(
        L9_OPTIMIZE_GLOBAL_PATH,
        L9_OPTIMIZE_GLOBAL_MOVE,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
    )
    l9_main.process()


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


def statistics(L1_paths, total_L1, moved_L1, failed_L1, failed_names_L1, GLOBAL_GOTIFY_IP, GLOBAL_GOTIFY_TOKEN):
    message = f"\n===== L1 统计 =====\n"
    log_print("===== L1 统计 =====")

    for folder_id in L1_paths.keys():
        log_print(f"--- {folder_id} ---")
        message += f"--- {folder_id} ---\n"

        source_path = L1_paths[folder_id]["source"]
        target_path = L1_paths[folder_id]["target"]
        processed = total_L1.get(folder_id, 0) - moved_L1.get(folder_id, 0) - failed_L1.get(folder_id, 0)

        log_print(f"[统计] 源路径: {source_path}")
        message += f"[统计] 源路径: {source_path}\n"

        log_print(f"[统计] 处理前: {total_L1.get(folder_id, 0)}, 处理后: {processed}")
        message += f"[统计] 处理前: {total_L1.get(folder_id, 0)}, 处理后: {processed}\n"

        log_print(f"[统计] 移动成功: {moved_L1.get(folder_id, 0)}, 移动失败: {failed_L1.get(folder_id, 0)}")
        message += f"[统计] 移动成功: {moved_L1.get(folder_id, 0)}, 移动失败: {failed_L1.get(folder_id, 0)}\n"

        failed_folders = ", ".join(failed_names_L1.get(folder_id, []))
        log_print(f"[统计] 移动失败文件夹: {failed_folders}")
        message += f"[统计] 移动失败文件夹: {failed_folders}\n"

        log_print(f"[统计] 输出路径: {target_path}")
        message += f"[统计] 输出路径: {target_path}\n"

        try:
            current_folders = [
                folder for folder in os.listdir(target_path)
                if os.path.isdir(os.path.join(target_path, folder))
            ]
            current_folders_str = ", ".join(current_folders)
        except FileNotFoundError:
            current_folders_str = "目标路径不存在"

        log_print(f"[统计] 文件夹: {current_folders_str}")
        message += f"[统计] 文件夹: {current_folders_str}\n"

    # 推送统计信息到 Gotify
    try:
        asyncio.run(
            push_gotify(
                GLOBAL_GOTIFY_IP,
                GLOBAL_GOTIFY_TOKEN,
                "[优化录播文件2.0] L1统计数据",
                message,
                priority=3,
            )
        )
    except Exception as e:
        log_print(f"[Error] 推送统计信息失败: {e}")


def run_optimize():
    """
    执行 L1、L2 和 L9 的操作，并生成统计信息。
    """
    # L1 移动操作
    log_print("[MAIN] 开始 L1 移动操作")
    total_folders_L1, moved_folders_L1, failed_folders_L1, failed_folder_names_L1 = move_folders(
        L1_OPTIMIZE_GLOBAL_PATH,
        L1_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        enable_move=L1_OPTIMIZE_GLOBAL_MOVE
    )
    log_print("[MAIN] 完成 L1 移动操作")

    # L2 优化操作
    log_print("[MAIN] 开始 L2 优化操作")
    L2_OPTIMIZE()
    log_print("[MAIN] 完成 L2 优化操作")

    # L9 移动操作
    log_print("[MAIN] 开始 L9 移动操作")
    L9_OPTIMIZE()
    log_print("[MAIN] 完成 L9 移动操作")

    # 统计信息
    statistics(
        L1_OPTIMIZE_GLOBAL_PATH,
        total_folders_L1,
        moved_folders_L1,
        failed_folders_L1,
        failed_folder_names_L1,
        GLOBAL_GOTIFY_IP,
        GLOBAL_GOTIFY_TOKEN,
    )



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
