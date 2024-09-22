import asyncio
import os
import time
import schedule
from datetime import datetime

from core.gotify import push_gotify
from core.L1_OPTIMIZE import move_folders
from core.L2_OPTIMIZE import BLREC, RECHEME
from core.logs import log, log_print

log()

### 配置 ###

# Gotify
GLOBAL_GOTIFY_IP = "http://100.111.200.61:18101"
GLOBAL_GOTIFY_TOKEN = "A43buC_qB8d8sfk"

# 定时任务
GLOBAL_TIMES = [
    "00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
    "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"
]

### L1 ###
# (L1全局)路径
L1_OPTIMIZE_GLOBAL_PATH = {
    "L1_AAA": {"source": r"F:\Video\录播\综合", "target": r"F:\Video\AAAAAAAAAA"},
    "L1_PPP": {"source": r"F:\Video\录播\P家", "target": r"F:\Video\PPPPPPPPPP"},
}

# (L1全局)是否启用移动文件夹
L1_OPTIMIZE_GLOBAL_MOVE = True

### L2 ###
# (L2全局)路径
L2_OPTIMIZE_GLOBAL_PATH = {
    "L2_AAA": {"source": r"F:\Video\AAAAAAAAAA", "target": r"F:\Video\AAAAAAAAAA\综合"},
    "L2_PPP": {"source": r"F:\Video\PPPPPPPPPP", "target": r"F:\Video\PPPPPPPPPP\P家"},
}

# (L2全局)是否启用移动文件夹
L2_OPTIMIZE_GLOBAL_MOVE = True
# (L2全局)社团文件夹名称列表
L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS = ["NIJISANJI", "HOLOLIVE", "VSPO"]
# (L2全局)需要跳过的特殊文件夹名称列表
L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS = ["000", "111", "222", "333", "444"]
# (L2录播姬)需要跳过的录播子文件夹
L2_OPTIMIZE_RECHEME_SKIP_KEY = ["【blrec-flv】", "【blrec-hls】", "000_部分丢失", "1970"]

### 主要操作 ###

def L2_OPTIMIZE():
    blrec = BLREC()
    log_print("[BLREC] 开始处理")
    blrec.blrec_main(
        L2_OPTIMIZE_GLOBAL_PATH,
        L2_OPTIMIZE_GLOBAL_MOVE,
        L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS
    )
    log_print("[BLREC] 处理完成")
    
    recheme = RECHEME()
    log_print("[录播姬] 开始处理")
    recheme.recheme_main(
        L2_OPTIMIZE_GLOBAL_PATH,
        L2_OPTIMIZE_GLOBAL_MOVE,
        L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
        L2_OPTIMIZE_RECHEME_SKIP_KEY
    )
    log_print("[录播姬] 处理完成")

def get_l2_folder(directory_path):
    """
    获取指定目录下的所有子文件夹名称。

    参数:
        directory_path (str): 目录路径。

    返回:
        list: 子文件夹名称列表。
    """
    try:
        return [folder for folder in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, folder))]
    except FileNotFoundError:
        log_print(f"[统计] 目录不存在: {directory_path}")
        return []

def statistics(
    L1_paths, total_L1, moved_L1, failed_L1, failed_names_L1,
    L2_paths,
    GLOBAL_GOTIFY_IP, GLOBAL_GOTIFY_TOKEN
):
    def process_L1_statistics(paths, total, moved, failed, failed_names):
        message = f"\n===== L1 统计 =====\n"
        log_print("===== L1 统计 =====")
        
        for folder_id in paths.keys():
            log_print(f"--- {folder_id} ---")
            message += f"--- {folder_id} ---\n"
            
            source_path = paths[folder_id]["source"]
            target_path = paths[folder_id]["target"]
            processed = total.get(folder_id, 0) - moved.get(folder_id, 0) - failed.get(folder_id, 0)
            
            log_print(f"[统计] 源路径: {source_path}")
            message += f"[统计] 源路径: {source_path}\n"
            
            log_print(f"[统计] 处理前: {total.get(folder_id, 0)}, 处理后: {processed}")
            message += f"[统计] 处理前: {total.get(folder_id, 0)}, 处理后: {processed}\n"
            
            log_print(f"[统计] 移动成功: {moved.get(folder_id, 0)}, 移动失败: {failed.get(folder_id, 0)}")
            message += f"[统计] 移动成功: {moved.get(folder_id, 0)}, 移动失败: {failed.get(folder_id, 0)}\n"
            
            failed_folders = ", ".join(failed_names.get(folder_id, []))
            log_print(f"[统计] 移动失败文件夹: {failed_folders}")
            message += f"[统计] 移动失败文件夹: {failed_folders}\n"
            
            log_print(f"[统计] 输出路径: {target_path}")
            message += f"[统计] 输出路径: {target_path}\n"
            
            try:
                current_folders = [folder for folder in os.listdir(target_path) if os.path.isdir(os.path.join(target_path, folder))]
                current_folders_str = ", ".join(current_folders)
            except FileNotFoundError:
                current_folders_str = "目标路径不存在"
            
            log_print(f"[统计] 文件夹: {current_folders_str}")
            message += f"[统计] 文件夹: {current_folders_str}\n"
        
        return message

    def process_L2_statistics(paths):
        message = f"\n===== L2 统计 =====\n"
        log_print("===== L2 统计 =====")
        
        for folder_id in paths.keys():
            log_print(f"--- {folder_id} ---")
            message += f"--- {folder_id} ---\n"
            
            source_path = paths[folder_id]["source"]
            target_path = paths[folder_id]["target"]
            
            log_print(f"[统计] 源路径: {source_path}")
            message += f"[统计] 源路径: {source_path}\n"
            
            source_folders = get_l2_folder(source_path)
            source_folders_str = ", ".join(source_folders)
            log_print(f"[统计] 文件夹: {source_folders_str}")
            message += f"[统计] 文件夹: {source_folders_str}\n"
            
            log_print(f"[统计] 输出路径: {target_path}")
            message += f"[统计] 输出路径: {target_path}\n"
            
            target_folders = get_l2_folder(target_path)
            target_folders_str = ", ".join(target_folders)
            log_print(f"[统计] 文件夹: {target_folders_str}")
            message += f"[统计] 文件夹: {target_folders_str}\n"
        
        return message

    # 生成统计信息
    statistics_message = ""
    statistics_message += process_L1_statistics(L1_paths, total_L1, moved_L1, failed_L1, failed_names_L1)
    statistics_message += process_L2_statistics(L2_paths)
    
    # 推送统计信息到 Gotify
    try:
        asyncio.run(push_gotify(
            GLOBAL_GOTIFY_IP, 
            GLOBAL_GOTIFY_TOKEN, 
            "[优化录播文件2.0] 统计数据", 
            statistics_message, 
            priority=5
        ))
    except Exception as e:
        log_print(f"[Error] 推送统计信息失败: {e}")

def run_optimize():
    """
    执行 L1 和 L2 的移动和优化操作，并生成统计信息。
    """
    # L1 移动操作
    log_print("[Run] 开始 L1 移动操作")
    total_folders_L1, moved_folders_L1, failed_folders_L1, failed_folder_names_L1 = move_folders(
        L1_OPTIMIZE_GLOBAL_PATH, enable_move=L1_OPTIMIZE_GLOBAL_MOVE
    )
    log_print("[Run] 完成 L1 移动操作")
    
    # L2 优化操作
    log_print("[Run] 开始 L2 优化操作")
    L2_OPTIMIZE()
    log_print("[Run] 完成 L2 优化操作")
    
    # 统计信息
    statistics(
        L1_OPTIMIZE_GLOBAL_PATH,
        total_folders_L1, moved_folders_L1, failed_folders_L1, failed_folder_names_L1,
        L2_OPTIMIZE_GLOBAL_PATH,
        GLOBAL_GOTIFY_IP, GLOBAL_GOTIFY_TOKEN
    )

def task_scheduler():
    """
    定时任务
    """
    for t in GLOBAL_TIMES:
        schedule.every().day.at(t).do(run_optimize)
    
    last_log_time = time.time()
    log_interval = 1800  # 30分钟
    
    while True:
        schedule.run_pending()
        time.sleep(1)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if time.time() - last_log_time >= log_interval:
            log_print(f"\n[计划] 当前时间: {current_time}")
            
            next_run = schedule.next_run()
            if next_run:
                next_run_time = next_run.strftime("%Y-%m-%d %H:%M:%S")
                log_print(f"[计划] 下次运行时间: {next_run_time}")
            else:
                log_print("[计划] 没有待执行的定时任务。")
            
            last_log_time = time.time()

if __name__ == "__main__":
    log_print("程序开始运行")
    run_optimize()
    task_scheduler()
