# core/L2_OPTIMIZE.py

import os
import re
import logging
from collections import defaultdict
from datetime import datetime

from .move import move_folder


class BLREC:
    """
    BLREC 类用于处理 BLREC 文件夹的解析和合并操作。
    """

    def __init__(self):
        pass

    def parse_folder_name(self, folder_name):
        """
        解析文件夹名，提取日期、标题和后缀。

        参数:
            folder_name (str): 文件夹名称。

        返回:
            tuple: (date, title, suffix) 或 (None, None, None) 如果无法解析。
        """
        pattern = r"(\d{8})-(\d{6})_(.+)\【(blrec-flv|blrec-hls)\】"
        match = re.match(pattern, folder_name)
        if match:
            date_str, time_str, title, suffix = match.groups()
            date = datetime.strptime(date_str + "-" + time_str, "%Y%m%d-%H%M%S")
            return date, title, suffix
        # else:
        #     logging.warning(f"[L2][BLREC] 无法解析文件夹名：{folder_name}")
        return None, None, None

    def should_process_folder(self, folder_name, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS):
        """
        判断是否应该处理该文件夹。

        参数:
            folder_name (str): 文件夹名称。
            L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS (list): 社团文件夹列表。
            L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS (list): 需要跳过的文件夹列表。

        返回:
            bool: 如果应该处理则返回 True，否则返回 False。
        """
        if folder_name in L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
            logging.debug(f"[L2][BLREC] 跳过文件夹：{folder_name} (在跳过列表中)")
            return False
        if any(folder_name.startswith(social) for social in L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS):
            logging.debug(f"[L2][BLREC] 跳过社团文件夹：{folder_name}")
            return False
        return True

    def merge_files(self, target_folder, source_folder):
        """
        将 source_folder 中的文件移动到 target_folder。

        参数:
            target_folder (str): 目标文件夹路径。
            source_folder (str): 源文件夹路径。
        """
        if not os.path.exists(source_folder):
            logging.warning(f"[L2][BLREC] 源文件夹不存在，无法合并: {source_folder}")
            return

        for filename in os.listdir(source_folder):
            source_file = os.path.join(source_folder, filename)
            target_file = os.path.join(target_folder, filename)
            try:
                os.rename(source_file, target_file)
                logging.info(f"[L2][BLREC] 文件移动：{source_file} -> {target_file}")
            except Exception as e:
                logging.error(f"[L2][BLREC] 文件移动失败：{source_file} -> {target_file}, 错误：{e}")

    def merge_folders(self, L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_GLOBAL_MOVE, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS):
        """
        合并符合条件的文件夹。

        参数:
            L2_OPTIMIZE_GLOBAL_PATH (dict): 文件夹路径映射。
            L2_OPTIMIZE_GLOBAL_MOVE (bool): 是否启用移动操作。
            L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS (list): 社团文件夹列表。
            L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS (list): 需要跳过的文件夹列表。
        """
        logging.debug("[BLREC] 开始合并文件夹")

        for id, paths in L2_OPTIMIZE_GLOBAL_PATH.items():
            source_path = paths["source"]
            if not os.path.exists(source_path) or not os.path.isdir(source_path):
                logging.warning(f"[L2][BLREC] 源路径不存在或不是目录：{source_path}")
                continue

            while True:
                folders = defaultdict(list)
                for root, dirs, files in os.walk(source_path, topdown=True):
                    dirs[:] = [d for d in dirs if self.should_process_folder(d, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS)]
                    for folder_name in dirs:
                        folder_full_path = os.path.join(root, folder_name)
                        date, title, suffix = self.parse_folder_name(folder_name)
                        if date and title and suffix:
                            folders[(date.date(), title, suffix)].append((date, folder_full_path))

                merge_completed = False
                for key, folder_list in folders.items():
                    if len(folder_list) > 1:
                        logging.debug(f"[L2][BLREC] 发现可合并文件夹：{key}")
                        folder_list.sort(key=lambda x: x[0])
                        for i in range(len(folder_list) - 1):
                            time_diff = folder_list[i + 1][0] - folder_list[i][0]
                            if time_diff.total_seconds() <= 4 * 60 * 60:
                                merge_to_folder = folder_list[i][1]
                                for folder_to_merge in folder_list[i + 1:]:
                                    logging.info(f"[L2][BLREC] 合并: {folder_to_merge[1]} -> {merge_to_folder}")
                                    self.merge_files(merge_to_folder, folder_to_merge[1])
                                    try:
                                        os.rmdir(folder_to_merge[1])
                                        merge_completed = True
                                    except Exception as e:
                                        logging.error(f"[L2][BLREC] 删除文件夹失败：{folder_to_merge[1]}, 错误：{e}")
                        if merge_completed:
                            break
                    else:
                        logging.info(f"[L2][BLREC] 没有找到可以合并的文件夹组：{key}")

                if not merge_completed:
                    break

    def blrec_main(self, L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_GLOBAL_MOVE, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS):
        """
        BLREC 主函数，执行文件夹合并操作。

        参数:
            L2_OPTIMIZE_GLOBAL_PATH (dict): 文件夹路径映射。
            L2_OPTIMIZE_GLOBAL_MOVE (bool): 是否启用移动操作。
            L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS (list): 社团文件夹列表。
            L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS (list): 需要跳过的文件夹列表。
        """
        self.merge_folders(L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_GLOBAL_MOVE, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS)


class RECHEME:
    """
    RECHEME 类用于处理录播姬文件夹的合并和移动操作。
    """

    def __init__(self):
        pass

    def merge_folders(self, main_folder, folders_to_merge, L2_OPTIMIZE_RECHEME_SKIP_KEY):
        """
        合并多个文件夹到主文件夹。

        参数:
            main_folder (str): 主文件夹路径。
            folders_to_merge (list): 需要合并的文件夹列表。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        if not folders_to_merge:
            logging.warning(f"[L2][录播姬] 未找到可合并的文件夹: {main_folder}")
            return

        logging.debug(f"[L2][录播姬] 合并文件夹: {main_folder} <- {folders_to_merge}")
        for folder in folders_to_merge:
            if any(substring in folder for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY):
                logging.debug(f"[L2][录播姬] 跳过文件夹：{folder}")
                continue

            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                target_item_path = os.path.join(main_folder, item)
                logging.debug(f"[L2][录播姬] 将 {item_path} 移动到 {target_item_path}")
                move_folder(item_path, target_item_path)

            os.rmdir(folder)

    def process_user_folder(
        self, id, user_folder, L2_OPTIMIZE_GLOBAL_MOVE, L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_RECHEME_SKIP_KEY
    ):
        """
        处理单个用户的文件夹。

        参数:
            id (str): 用户ID。
            user_folder (str): 用户文件夹名称。
            L2_OPTIMIZE_GLOBAL_MOVE (bool): 是否启用移动操作。
            L2_OPTIMIZE_GLOBAL_PATH (dict): 文件夹路径映射。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        logging.info(f"[L2][录播姬] 开始处理文件夹: {user_folder}")
        source_path = L2_OPTIMIZE_GLOBAL_PATH[id]["source"]
        target_path = L2_OPTIMIZE_GLOBAL_PATH[id].get("target")

        if not target_path and L2_OPTIMIZE_GLOBAL_MOVE:
            logging.warning(f"[L2][录播姬] 未提供目标路径，移动操作被禁用: {source_path}")
            L2_OPTIMIZE_GLOBAL_MOVE = False

        user_folder_path = os.path.join(source_path, user_folder)
        target_user_folder_path = os.path.join(target_path, user_folder) if target_path else None

        if not os.path.exists(user_folder_path):
            logging.error(f"[L2][录播姬] 文件夹不存在，无法处理: {user_folder_path}")
            return

        # 检查是否试图将文件夹移动到其自身的子目录中
        if target_user_folder_path and os.path.commonpath([user_folder_path]) == os.path.commonpath([user_folder_path, target_user_folder_path]):
            logging.error(f"[L2][录播姬] 无法将目录 '{user_folder_path}' 移动到其子目录 '{target_user_folder_path}'，操作被跳过。")
            return

        while True:
            subfolders = os.listdir(user_folder_path)
            if len(subfolders) == 0:
                break

            # 逻辑1: 只有一个子文件夹
            if len(subfolders) == 1:
                if L2_OPTIMIZE_GLOBAL_MOVE and target_user_folder_path:
                    move_folder(user_folder_path, target_user_folder_path)
                break

            # 逻辑2: 有多个子文件夹
            subfolder_info = defaultdict(list)
            for subfolder in subfolders:
                if any(substring in subfolder for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY):
                    logging.debug(f"[L2][录播姬] 跳过文件夹：{subfolder}")
                    continue
                subfolder_path = os.path.join(user_folder_path, subfolder)

                match = re.search(r"(\d{8}-\d{6})", subfolder)
                if match:
                    time_info = match.group()
                    subfolder_info[time_info].append(subfolder)
                else:
                    logging.debug(f"[L2][录播姬] 子文件夹命名不符合规则，跳过：{subfolder}")

            if not subfolder_info:
                break

            # 逻辑2.1: 合并操作
            merge_completed = False
            for time_info, subfolder_list in subfolder_info.items():
                if len(subfolder_list) >= 2:
                    merge_logic_result = self.process_merge_logic(
                        id,
                        user_folder,
                        {time_info: subfolder_list},
                        L2_OPTIMIZE_GLOBAL_PATH,
                        L2_OPTIMIZE_RECHEME_SKIP_KEY,
                    )
                    if merge_logic_result:
                        merge_completed = True
                        break

            if not merge_completed:
                break

        logging.info(f"[L2][录播姬] 处理完成文件夹: {user_folder}")

    def get_valid_subfolders(self, subfolder_list, skip_substrings):
        """
        获取有效的子文件夹，排除包含跳过子字符串的文件夹。

        参数:
            subfolder_list (list): 子文件夹列表。
            skip_substrings (list): 需要跳过的子字符串列表。

        返回:
            list: 有效的子文件夹列表。
        """
        valid_subfolders = [
            subfolder
            for subfolder in subfolder_list
            if not any(skip_str in subfolder for skip_str in skip_substrings)
        ]
        logging.debug(f"[L2][录播姬] 有效子文件夹筛选结果：{valid_subfolders}")
        return valid_subfolders

    def process_flv_files(self, subfolder_list, user_folder_path):
        """
        处理 FLV 文件，找到最新日期的文件夹。

        参数:
            subfolder_list (list): 子文件夹列表。
            user_folder_path (str): 用户文件夹路径。

        返回:
            str: 包含最新 FLV 文件的文件夹名称，或 None 如果未找到。
        """
        flv_time_mapping = {}
        for subfolder in subfolder_list:
            subfolder_path = os.path.join(user_folder_path, subfolder)
            flv_files = [f for f in os.listdir(subfolder_path) if f.endswith(".flv")]
            if flv_files:
                flv_files.sort(
                    key=lambda f: datetime.strptime(
                        re.search(r"(\d{8}-\d{6})", f).group(), "%Y%m%d-%H%M%S"
                    )
                )
                max_date_flv = flv_files[-1]
                flv_time_mapping[subfolder] = datetime.strptime(
                    re.search(r"(\d{8}-\d{6})", max_date_flv).group(), "%Y%m%d-%H%M%S"
                )
        max_date_folder = (
            max(flv_time_mapping, key=flv_time_mapping.get) if flv_time_mapping else None
        )
        logging.debug(f"[L2][录播姬] FLV文件处理结果：{max_date_folder}")
        return max_date_folder

    def process_merge_logic(
        self, id, user_folder, subfolder_info, L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_RECHEME_SKIP_KEY
    ):
        """
        处理合并逻辑，根据 FLV 文件选择主文件夹并合并其他文件夹。

        参数:
            id (str): 用户ID。
            user_folder (str): 用户文件夹名称。
            subfolder_info (dict): 子文件夹信息。
            L2_OPTIMIZE_GLOBAL_PATH (dict): 文件夹路径映射。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。

        返回:
            bool: 如果进行了合并操作则返回 True，否则返回 False。
        """
        logging.debug(f"[L2][录播姬] 开始处理合并逻辑，用户ID：{id}, 用户文件夹：{user_folder}")
        source_path = L2_OPTIMIZE_GLOBAL_PATH[id]["source"]
        user_folder_path = os.path.join(source_path, user_folder)

        for time_info, subfolder_list in subfolder_info.items():
            valid_subfolders = self.get_valid_subfolders(subfolder_list, L2_OPTIMIZE_RECHEME_SKIP_KEY)
            if not valid_subfolders:
                logging.debug(f"[L2][录播姬] 没有有效的子文件夹，跳过当前时间信息：{time_info}")
                continue

            max_date_folder = self.process_flv_files(valid_subfolders, user_folder_path)
            if not max_date_folder:
                logging.debug(f"[L2][录播姬] 找不到有效的FLV文件，跳过：{time_info}")
                continue

            main_subfolder_path = os.path.join(user_folder_path, max_date_folder)
            if any(
                substring in main_subfolder_path for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY
            ):
                logging.debug(
                    f"[L2][录播姬] 主文件夹包含跳过子字符串，跳过：{main_subfolder_path}"
                )
                continue

            logging.info(f"[L2][录播姬] 合并文件夹：{main_subfolder_path}")
            self.merge_folders(
                main_subfolder_path,
                [
                    os.path.join(user_folder_path, subfolder)
                    for subfolder in valid_subfolders
                    if subfolder != max_date_folder
                ],
                L2_OPTIMIZE_RECHEME_SKIP_KEY,
            )

            if not os.listdir(main_subfolder_path):
                os.rmdir(main_subfolder_path)
                logging.debug(f"[L2][录播姬] 删除空文件夹：{main_subfolder_path}")
            return True

        logging.debug(f"[L2][录播姬] 合并逻辑处理完成，用户文件夹：{user_folder}")
        return False

    def merge_folders_logic(self, main_folder, folders_to_merge, L2_OPTIMIZE_RECHEME_SKIP_KEY):
        """
        合并多个文件夹到主文件夹，封装 BLREC 的 merge_folders 方法。

        参数:
            main_folder (str): 主文件夹路径。
            folders_to_merge (list): 需要合并的文件夹列表。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        if not folders_to_merge:
            logging.warning(f"[L2][录播姬] 未找到可合并的文件夹: {main_folder}")
            return

        logging.debug(f"[L2][录播姬] 合并文件夹: {main_folder} <- {folders_to_merge}")
        for folder in folders_to_merge:
            if any(substring in folder for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY):
                logging.debug(f"[L2][录播姬] 跳过文件夹：{folder}")
                continue

            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                target_item_path = os.path.join(main_folder, item)
                logging.debug(f"[L2][录播姬] 将 {item_path} 移动到 {target_item_path}")
                move_folder(item_path, target_item_path)

            os.rmdir(folder)

    def recheme_main(
        self, L2_OPTIMIZE_GLOBAL_PATH, L2_OPTIMIZE_GLOBAL_MOVE, L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS, L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS, L2_OPTIMIZE_RECHEME_SKIP_KEY
    ):
        """
        RECHEME 主函数，处理录播姬文件夹的合并和移动操作。

        参数:
            L2_OPTIMIZE_GLOBAL_PATH (dict): 文件夹路径映射。
            L2_OPTIMIZE_GLOBAL_MOVE (bool): 是否启用移动操作。
            L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS (list): 社团文件夹列表。
            L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS (list): 需要跳过的文件夹列表。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        # 遍历用户文件夹
        for id, paths in L2_OPTIMIZE_GLOBAL_PATH.items():
            source_path = paths["source"]
            target_path = paths.get("target")

            # 检查源路径是否存在
            if not os.path.exists(source_path):
                logging.warning(f"[L2][录播姬] 源路径不存在：{source_path}")
                continue

            logging.info(f"[L2][录播姬] 开始处理源路径: {source_path}")

            # 跳过文件夹
            for user_folder in os.listdir(source_path):
                if user_folder in L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                    continue

                user_folder_path = os.path.join(source_path, user_folder)
                if not os.path.isdir(user_folder_path):
                    continue

                # 检查是否是社团文件夹，如果是则进入下一层文件夹
                is_social_folder = user_folder in L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS
                if is_social_folder:
                    for sub_user_folder in os.listdir(user_folder_path):
                        sub_user_folder_path = os.path.join(user_folder_path, sub_user_folder)
                        if not os.path.isdir(sub_user_folder_path):
                            continue
                        logging.info(f"[L2][录播姬] 开始处理子文件夹: {sub_user_folder_path}")
                        self.process_user_folder(
                            id,
                            os.path.join(user_folder, sub_user_folder),
                            L2_OPTIMIZE_GLOBAL_MOVE,
                            L2_OPTIMIZE_GLOBAL_PATH,
                            L2_OPTIMIZE_RECHEME_SKIP_KEY,
                        )
                else:
                    logging.info(f"[L2][录播姬] 开始处理文件夹: {user_folder_path}")
                    self.process_user_folder(
                        id,
                        user_folder,
                        L2_OPTIMIZE_GLOBAL_MOVE,
                        L2_OPTIMIZE_GLOBAL_PATH,
                        L2_OPTIMIZE_RECHEME_SKIP_KEY,
                    )

            # 删除空文件夹
            if not os.listdir(source_path):
                os.rmdir(source_path)