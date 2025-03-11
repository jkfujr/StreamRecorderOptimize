import os
import requests
import logging
from .move import move_folder, delete_empty_folders
from .statistics import Statistics

def fetch_recording_status():
    """
    请求API获取录制状态。

    返回:
        dict: {folder_name: {"recording": bool, "streaming": bool}, ...}
    """
    api_url = "http://127.0.0.1:11111/api/room"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        status_dict = {
            item["name"]: {
                "recording": item["recording"],
                "streaming": item["streaming"]
            } 
            for item in data
        }
        logging.debug(f"[L1][API] 获取到的所有直播状态: {status_dict}")
        return status_dict
    except requests.exceptions.RequestException as e:
        logging.error(f"[L1][API] 请求API失败: {e}")
        # API 请求失败时，应该停止所有移动操作
        raise RuntimeError(f"无法获取直播状态，为安全起见停止所有移动操作: {e}")

def move_folders(folder_path_id, social_folder_names, enable_move):
    """
    移动和合并文件夹。

    参数:
        folder_path_id (dict): 文件夹路径映射。
        social_folder_names (list): 社团文件夹名称列表。
        enable_move (bool): 是否启用移动操作。

    返回:
        Statistics: 统计信息对象
    """
    stats = Statistics()

    if not enable_move:
        logging.debug("[L1][移动] 移动文件夹功能被禁用")
        return stats

    try:
        # 检查录制状态 - 如果失败会抛出异常
        recording_status = fetch_recording_status()
    except Exception as e:
        logging.error(f"[L1][移动] 获取直播状态失败，停止所有移动操作: {e}")
        return stats

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
                continue

        # 检查源目录是否存在
        if not os.path.exists(source_directory):
            logging.debug(f"[L1][移动] 源路径 {source_directory} 不存在，跳过处理")
            continue

        logging.debug(f"[L1][移动] 开始处理源路径 {source_directory}")

        # 定义处理用户文件夹的内部函数
        def process_user_folder(source_folder_path, target_folder_path, folder_name):
            logging.debug(f"[L1][移动] 开始处理用户文件夹 {folder_name}")

            # 检查是否在直播或录制中
            folder_status = recording_status.get(folder_name)
            
            # 添加更详细的日志
            logging.debug(f"[L1][移动] 文件夹 {folder_name} 的状态: {folder_status}")
            
            if folder_status is not None:
                logging.debug(f"[L1][移动] 文件夹 {folder_name} 的录制状态: {folder_status['recording']}, 直播状态: {folder_status['streaming']}")
                if folder_status["recording"] or folder_status["streaming"]:
                    logging.debug(f"[L1][移动] 用户文件夹 {folder_name} 正在直播或者录制中，跳过移动")
                    stats.add_skipped(folder_name, "正在直播或录制")
                    return
            else:
                logging.debug(f"[L1][移动] 未找到用户文件夹 {folder_name} 的直播状态")

            try:
                move_folder(source_folder_path, target_folder_path, enable_move)
                logging.debug(f"[L1][移动] 成功移动文件夹 {folder_name}")
                stats.add_success()
            except Exception as e:
                logging.debug(f"[L1][移动] 移动或合并文件夹 {folder_name} 失败: {e}")
                stats.add_failed(folder_name, str(e))

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
                    process_user_folder(source_folder_path, target_folder_path, user_folder_name)
            else:
                # 直接处理用户文件夹
                source_folder_path = full_folder_path
                target_folder_path = os.path.join(target_directory, folder_name)
                process_user_folder(source_folder_path, target_folder_path, folder_name)

        # 删除空文件夹时传入录制状态
        delete_empty_folders(source_directory, recording_status)

    return stats
