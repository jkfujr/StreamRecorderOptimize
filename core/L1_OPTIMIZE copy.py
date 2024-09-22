# core\L1_OPTIMIZE.py

import os
import shutil
import requests
import logging

def fetch_recording_status():
    """
    请求API获取录制状态。

    返回:
        dict: {folder_name: {"recording": bool, "streaming": bool}, ...}
    """
    api_url = "http://127.0.0.1:11111/api/data"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json().get("data", [])
        return {item["name"]: {"recording": item["recording"], "streaming": item["streaming"]} for item in data}
    except requests.exceptions.RequestException as e:
        logging.debug(f"[L1][API] 请求API失败: {e}")
        return {}

def ensure_directory_exists(directory_path):
    """
    确保目录存在，如果不存在则创建。

    参数:
        directory_path (str): 目录路径。
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logging.debug(f"[L1][目录] 创建目标目录: {directory_path}")
        except Exception as e:
            logging.debug(f"[L1][目录] 创建目录 {directory_path} 失败: {e}")

def move_folders(folder_path_id, enable_move):
    """
    移动和合并文件夹。

    参数:
        folder_path_id (dict): 文件夹路径映射。
        enable_move (bool): 是否启用移动操作。

    返回:
        tuple: (total_folders, moved_folders, failed_folders, failed_folder_names)
    """
    if not enable_move:
        logging.debug("[L1][移动] 移动文件夹功能被禁用")
        return None, None, None, None

    # 统计信息
    total_folders = {folder_id: 0 for folder_id in folder_path_id.keys()}
    moved_folders = {folder_id: 0 for folder_id in folder_path_id.keys()}
    failed_folders = {folder_id: 0 for folder_id in folder_path_id.keys()}
    failed_folder_names = {folder_id: [] for folder_id in folder_path_id.keys()}

    # 检查录制状态
    recording_status = fetch_recording_status()

    logging.debug("[L1][移动] 开始移动录播文件")
    for folder_id, paths in folder_path_id.items():
        source_directory = paths["source"]
        target_directory = paths["target"]

        # 确保目标目录存在
        ensure_directory_exists(target_directory)

        try:
            total_folders[folder_id] = len([item for item in os.listdir(source_directory) if os.path.isdir(os.path.join(source_directory, item))])
        except FileNotFoundError:
            logging.debug(f"[L1][移动] 源路径 {source_directory} 不存在")
            continue

        logging.debug(f"[L1][移动] 开始处理目标路径 {target_directory}, 总共有 {total_folders[folder_id]} 个文件夹")

        for folder_name in os.listdir(source_directory):
            if not os.path.isdir(os.path.join(source_directory, folder_name)):
                continue

            source_folder_path = os.path.join(source_directory, folder_name)
            target_folder_path = os.path.join(target_directory, folder_name)
            
            logging.debug(f"[L1][移动] 开始处理用户文件夹 {folder_name}")

            folder_status = recording_status.get(folder_name)
            if folder_status and (folder_status["recording"] or folder_status["streaming"]):
                logging.debug(f"[L1][移动] 用户文件夹 {folder_name} 正在直播或者录制中，跳过移动")
                continue

            if not os.path.exists(target_folder_path):
                try:
                    shutil.move(source_folder_path, target_folder_path)
                    logging.debug(f"[L1][移动] 已成功移动文件夹 {folder_name} 到 {target_directory}")
                    moved_folders[folder_id] += 1
                except Exception as e:
                    logging.debug(f"[L1][移动] 移动文件夹 {folder_name} 到 {target_folder_path} 失败: {e}")
                    failed_folders[folder_id] += 1
                    failed_folder_names[folder_id].append(folder_name)
            else:
                try:
                    for item in os.listdir(source_folder_path):
                        shutil.move(os.path.join(source_folder_path, item), target_folder_path)
                    os.rmdir(source_folder_path)
                    logging.debug(f"[L1][移动] 已合并文件夹 {folder_name} 到 {target_directory}")
                    moved_folders[folder_id] += 1
                except Exception as e:
                    logging.debug(f"[L1][移动] 合并文件夹 {folder_name} 失败: {e}")
                    failed_folders[folder_id] += 1
                    failed_folder_names[folder_id].append(folder_name)

    # 删除空的用户文件夹
    for paths in folder_path_id.values():
        source_directory = paths["source"]
        try:
            for folder_name in os.listdir(source_directory):
                folder_path = os.path.join(source_directory, folder_name)
                if os.path.isdir(folder_path) and not os.listdir(folder_path):
                    os.rmdir(folder_path)
        except FileNotFoundError:
            continue

    return total_folders, moved_folders, failed_folders, failed_folder_names
