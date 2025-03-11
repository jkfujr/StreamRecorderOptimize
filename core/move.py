import os
import shutil
import logging
import hashlib

# MD5计算
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def move_folder(source, target, enable_move=True):
    """
    移动文件夹或文件到目标目录，如果目标存在同名文件或文件夹，进行合并。

    参数:
        source (str): 源文件夹路径。
        target (str): 目标文件夹路径。
        enable_move (bool): 是否启用移动功能。
    """
    if enable_move:
        if not os.path.exists(target):
            logging.info(f"[move] 移动文件：{source} -> {target}")
            shutil.move(source, target)
        else:
            logging.info(f"[move] 目标文件夹已存在，合并内容：{source} -> {target}")
            for item in os.listdir(source):
                source_item_path = os.path.join(source, item)
                target_item_path = os.path.join(target, item)
                if os.path.exists(target_item_path):
                    if os.path.isfile(source_item_path) and os.path.isfile(target_item_path):
                        source_md5 = calculate_md5(source_item_path)
                        target_md5 = calculate_md5(target_item_path)
                        if source_md5 == target_md5:
                            logging.debug(f"[move] 文件内容相同，删除源文件：{source_item_path}")
                            os.remove(source_item_path)
                            delete_empty_folders(os.path.dirname(source_item_path))
                        else:
                            logging.debug(f"[move] 目标位置已存在同名项且文件内容不同，跳过：{target_item_path}")
                    else:
                        logging.debug(f"[move] 目标位置已存在同名项，跳过：{target_item_path}")
                    continue
                logging.debug(f"[move] 移动项：{source_item_path} -> {target_item_path}")
                shutil.move(source_item_path, target_item_path)
            try:
                delete_empty_folders(source)
            except OSError:
                logging.debug(f"[move] 源文件夹未完全清空，未删除：{source}")
    else:
        logging.info(f"[move] 移动文件夹功能已禁用：{source} -> {target}")

def delete_empty_folders(directory, recording_status=None):
    """
    递归删除空文件夹。

    参数:
        directory (str): 需要检查并删除的文件夹路径。
        recording_status (dict, optional): 文件夹的录制状态字典。
    """
    if os.path.isdir(directory):
        # 先递归处理子文件夹
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            if os.path.isdir(folder_path):
                delete_empty_folders(folder_path, recording_status)
        
        # 检查文件夹是否为空
        if not os.listdir(directory):
            # 获取文件夹名称
            folder_name = os.path.basename(directory)
            
            # 如果提供了录制状态，检查是否正在录制或直播
            if recording_status is not None:
                folder_status = recording_status.get(folder_name)
                if folder_status and (folder_status["recording"] or folder_status["streaming"]):
                    logging.debug(f"[move][delete] 文件夹正在直播或录制中，跳过删除：{directory}")
                    return

            # 删除空文件夹
            os.rmdir(directory)
            logging.debug(f"[move][delete] 已删除空文件夹：{directory}")
