# core/L2_OPTIMIZE.py

import os
import re
import logging
from collections import defaultdict
from datetime import datetime

from .move import move_folder


class BLREC:
    """
    BLREC 类用于处理符合 BLREC 命名规则的文件夹的合并操作。
    """

    def __init__(self):
        self.pattern = r"(\d{8})-(\d{6})_(.+)【(blrec-flv|blrec-hls)】"

    def parse_folder_name(self, folder_name):
        """
        解析文件夹名，提取日期、标题和后缀。

        参数:
            folder_name (str): 文件夹名称。

        返回:
            tuple: (date, title, suffix) 或 (None, None, None) 如果无法解析。
        """
        match = re.match(self.pattern, folder_name)
        if match:
            date_str, time_str, title, suffix = match.groups()
            date = datetime.strptime(date_str + "-" + time_str, "%Y%m%d-%H%M%S")
            return date, title, suffix
        return None, None, None

    def merge_folders(self, folder_path):
        """
        合并符合条件的文件夹。

        参数:
            folder_path (str): 需要处理的文件夹路径。
        """
        logging.debug(f"[L2][BLREC] 开始处理路径：{folder_path}")

        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][BLREC] 路径不存在或不是目录：{folder_path}")
            return

        while True:
            folders = defaultdict(list)
            for root, dirs, files in os.walk(folder_path, topdown=True):
                for folder_name in dirs:
                    folder_full_path = os.path.join(root, folder_name)
                    date, title, suffix = self.parse_folder_name(folder_name)
                    if date and title and suffix:
                        folders[(date.date(), title, suffix)].append(
                            (date, folder_full_path)
                        )

            merge_completed = False
            for key, folder_list in folders.items():
                if len(folder_list) > 1:
                    logging.debug(f"[L2][BLREC] 发现可合并文件夹：{key}")
                    folder_list.sort(key=lambda x: x[0])
                    merge_to_folder = folder_list[0][1]
                    for _, folder_to_merge in folder_list[1:]:
                        logging.info(
                            f"[L2][BLREC] 合并: {folder_to_merge} -> {merge_to_folder}"
                        )
                        self.merge_files(merge_to_folder, folder_to_merge)
                        try:
                            os.rmdir(folder_to_merge)
                            merge_completed = True
                        except Exception as e:
                            logging.error(
                                f"[L2][BLREC] 删除文件夹失败：{folder_to_merge}, 错误：{e}"
                            )
                    if merge_completed:
                        break
                else:
                    logging.debug(f"[L2][BLREC] 没有找到可以合并的文件夹组：{key}")

            if not merge_completed:
                break

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
                if os.path.exists(target_file):
                    os.remove(target_file)
                os.rename(source_file, target_file)
                logging.info(f"[L2][BLREC] 文件移动：{source_file} -> {target_file}")
            except Exception as e:
                logging.error(
                    f"[L2][BLREC] 文件移动失败：{source_file} -> {target_file}, 错误：{e}"
                )


class RECHEME:
    """
    RECHEME 类用于处理其他文件夹的合并操作。
    """

    def __init__(self):
        pass

    def merge_folders(self, folder_path, L2_OPTIMIZE_RECHEME_SKIP_KEY):
        """
        处理录播姬文件夹的合并操作。

        参数:
            folder_path (str): 需要处理的文件夹路径。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        logging.debug(f"[L2][录播姬] 开始处理路径：{folder_path}")

        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            logging.warning(f"[L2][录播姬] 路径不存在或不是目录：{folder_path}")
            return

        for root, dirs, files in os.walk(folder_path, topdown=False):
            subfolder_info = defaultdict(list)
            for subfolder in dirs:
                if any(
                    substring in subfolder for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY
                ):
                    logging.debug(f"[L2][录播姬] 跳过文件夹：{subfolder}")
                    continue
                subfolder_path = os.path.join(root, subfolder)
                match = re.search(r"(\d{8}-\d{6})", subfolder)
                if match:
                    time_info = match.group()
                    subfolder_info[time_info].append(subfolder_path)

            for time_info, subfolder_list in subfolder_info.items():
                if len(subfolder_list) > 1:
                    main_folder = self.select_main_folder(subfolder_list)
                    logging.info(f"[L2][录播姬] 合并文件夹：{main_folder}")
                    self.merge_subfolders(
                        main_folder, subfolder_list, L2_OPTIMIZE_RECHEME_SKIP_KEY
                    )

    def select_main_folder(self, subfolder_list):
        """
        选择主文件夹。

        参数:
            subfolder_list (list): 子文件夹列表。

        返回:
            str: 主文件夹路径。
        """
        subfolder_list.sort()
        return subfolder_list[0]

    def merge_subfolders(
        self, main_folder, subfolders_to_merge, L2_OPTIMIZE_RECHEME_SKIP_KEY
    ):
        """
        合并子文件夹到主文件夹。

        参数:
            main_folder (str): 主文件夹路径。
            subfolders_to_merge (list): 需要合并的子文件夹列表。
            L2_OPTIMIZE_RECHEME_SKIP_KEY (list): 需要跳过的子字符串列表。
        """
        for folder in subfolders_to_merge:
            if folder == main_folder:
                continue
            if any(substring in folder for substring in L2_OPTIMIZE_RECHEME_SKIP_KEY):
                logging.debug(f"[L2][录播姬] 跳过文件夹：{folder}")
                continue

            for item in os.listdir(folder):
                source_item_path = os.path.join(folder, item)
                target_item_path = os.path.join(main_folder, item)
                move_folder(source_item_path, target_item_path)

            os.rmdir(folder)
            logging.debug(f"[L2][录播姬] 删除空文件夹：{folder}")


class L2_Main:
    """
    L2_Main 类用于管理 BLREC 和 RECHEME 的执行，不涉及文件夹的移动操作。
    """

    def __init__(
        self,
        L2_OPTIMIZE_GLOBAL_PATH,
        L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
        L2_OPTIMIZE_RECHEME_SKIP_KEY,
    ):
        self.L2_OPTIMIZE_GLOBAL_PATH = L2_OPTIMIZE_GLOBAL_PATH
        self.L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS = L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS
        self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS = L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS
        self.L2_OPTIMIZE_RECHEME_SKIP_KEY = L2_OPTIMIZE_RECHEME_SKIP_KEY

        self.blrec = BLREC()
        self.recheme = RECHEME()

    def process(self):
        """
        执行 L2 优化的主流程，仅处理源路径中的合并操作。
        """
        for id, paths in self.L2_OPTIMIZE_GLOBAL_PATH.items():
            source_path = paths["source"]

            # 确保源目录存在
            if not os.path.exists(source_path):
                logging.warning(f"[L2] 源路径不存在：{source_path}")
                continue

            # 遍历源目录
            for folder_name in os.listdir(source_path):
                folder_path = os.path.join(source_path, folder_name)

                if not os.path.isdir(folder_path):
                    continue

                if folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                    logging.debug(
                        f"[L2] 跳过文件夹（在跳过列表中）：{folder_name}"
                    )
                    continue

                if folder_name in self.L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS:
                    # 处理社团文件夹
                    logging.debug(f"[L2] 处理社团文件夹：{folder_name}")
                    self.process_social_folder(folder_path)
                    continue

                # 判断文件夹是否符合 BLREC 的命名规则
                if self.is_blrec_folder(folder_name):
                    logging.debug(f"[L2] 处理 BLREC 文件夹：{folder_name}")
                    self.blrec.merge_folders(folder_path)
                else:
                    logging.debug(f"[L2] 处理 RECHEME 文件夹：{folder_name}")
                    self.recheme.merge_folders(
                        folder_path, self.L2_OPTIMIZE_RECHEME_SKIP_KEY
                    )

        logging.info("[L2] L2 优化处理完成")

    def is_blrec_folder(self, folder_name):
        """
        判断文件夹名称是否符合 BLREC 的命名规则。

        参数:
            folder_name (str): 文件夹名称。

        返回:
            bool: 如果符合 BLREC 规则，返回 True，否则返回 False。
        """
        pattern = r"(\d{8})-(\d{6})_(.+)【(blrec-flv|blrec-hls)】"
        return re.match(pattern, folder_name) is not None

    def process_social_folder(self, social_folder_path):
        """
        处理社团文件夹。

        参数:
            social_folder_path (str): 社团文件夹路径。
        """
        for folder_name in os.listdir(social_folder_path):
            folder_path = os.path.join(social_folder_path, folder_name)

            if not os.path.isdir(folder_path):
                continue

            if folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                logging.debug(f"[L2] 跳过文件夹（在跳过列表中）：{folder_name}")
                continue
            if self.is_blrec_folder(folder_name):
                logging.debug(f"[L2] 处理 BLREC 文件夹：{folder_name}")
                self.blrec.merge_folders(folder_path)
            else:
                logging.debug(f"[L2] 处理 RECHEME 文件夹：{folder_name}")
                self.recheme.merge_folders(
                    folder_path, self.L2_OPTIMIZE_RECHEME_SKIP_KEY
                )