import os
import requests
import logging
from .move import move_folder, delete_empty_folders

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

def move_folders(folder_path_id, social_folder_names, enable_move):
    """
    移动和合并文件夹。

    参数:
        folder_path_id (dict): 文件夹路径映射。
        social_folder_names (list): 社团文件夹名称列表。
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
        if not os.path.exists(target_directory):
            try:
                os.makedirs(target_directory)
                logging.debug(f"[L1][目录检查] 创建目标目录: {target_directory}")
            except Exception as e:
                logging.debug(f"[L1][目录检查] 创建目录 {target_directory} 失败: {e}")

        # 检查源目录是否存在
        if not os.path.exists(source_directory):
            logging.debug(f"[L1][移动] 源路径 {source_directory} 不存在，跳过处理")
            continue

        logging.debug(f"[L1][移动] 开始处理源路径 {source_directory}")

        # 定义处理用户文件夹的内部函数
        def process_user_folder(source_folder_path, target_folder_path, folder_name, folder_id):
            logging.debug(f"[L1][移动] 开始处理用户文件夹 {folder_name}")

            folder_status = recording_status.get(folder_name)
            if folder_status and (folder_status["recording"] or folder_status["streaming"]):
                logging.debug(f"[L1][移动] 用户文件夹 {folder_name} 正在直播或者录制中，跳过移动")
                return

            try:
                move_folder(source_folder_path, target_folder_path, enable_move)
                moved_folders[folder_id] += 1
            except Exception as e:
                logging.debug(f"[L1][移动] 移动或合并文件夹 {folder_name} 失败: {e}")
                failed_folders[folder_id] += 1
                failed_folder_names[folder_id].append(folder_name)

            total_folders[folder_id] += 1  # 更新总计数

        # 遍历源目录
        for folder_name in os.listdir(source_directory):
            full_folder_path = os.path.join(source_directory, folder_name)
            if not os.path.isdir(full_folder_path):
                continue

            if folder_name in social_folder_names:
                # 这是一个社团文件夹，进入其中处理用户文件夹
                social_folder_path = full_folder_path
                for user_folder_name in os.listdir(social_folder_path):
                    user_folder_path = os.path.join(social_folder_path, user_folder_name)
                    if not os.path.isdir(user_folder_path):
                        continue

                    source_folder_path = user_folder_path
                    target_folder_path = os.path.join(target_directory, user_folder_name)
                    process_user_folder(source_folder_path, target_folder_path, user_folder_name, folder_id)
            else:
                # 直接处理用户文件夹
                source_folder_path = full_folder_path
                target_folder_path = os.path.join(target_directory, folder_name)
                process_user_folder(source_folder_path, target_folder_path, folder_name, folder_id)

        # 删除空文件夹
        delete_empty_folders(source_directory)

    return total_folders, moved_folders, failed_folders, failed_folder_names
