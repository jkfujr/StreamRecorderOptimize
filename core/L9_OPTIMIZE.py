import os
import logging
from .move import move_folder

class L9_Main:
    """
    L9_Main 类用于将处理完成的文件夹从源路径移动到目标路径。
    """

    def __init__(
        self,
        L9_OPTIMIZE_GLOBAL_PATH,
        L2_OPTIMIZE_GLOBAL_MOVE,
        L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS,
        L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS,
    ):
        self.L9_OPTIMIZE_GLOBAL_PATH = L9_OPTIMIZE_GLOBAL_PATH
        self.L2_OPTIMIZE_GLOBAL_MOVE = L2_OPTIMIZE_GLOBAL_MOVE
        self.L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS = L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS
        self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS = L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS

    def process(self):
        """
        执行 L9 移动操作，将处理完成的文件夹从源路径移动到目标路径。
        """
        if not self.L2_OPTIMIZE_GLOBAL_MOVE:
            logging.info("[L9][移动] 移动功能被禁用")
            return

        for id, paths in self.L9_OPTIMIZE_GLOBAL_PATH.items():
            source_path = paths["source"]
            target_path = paths["target"]

            if not os.path.exists(target_path):
                os.makedirs(target_path)
                logging.debug(f"[L9][移动] 创建目标目录：{target_path}")

            for folder_name in os.listdir(source_path):
                folder_path = os.path.join(source_path, folder_name)

                if not os.path.isdir(folder_path):
                    continue

                if folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                    logging.debug(f"[L9][移动] 跳过文件夹（在跳过列表中）：{folder_name}")
                    continue

                if folder_name in self.L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS:
                    # 处理社团文件夹
                    logging.debug(f"[L9][移动] 处理社团文件夹：{folder_name}")
                    self.process_social_folder(folder_path, target_path)
                    continue

                # 处理普通用户文件夹
                self.process_user_folder(folder_path, target_path)

        logging.info("[L9][移动] 移动操作完成")

    def process_user_folder(self, user_folder_path, target_path):
        """
        处理用户文件夹的移动操作，根据子文件夹的数量决定是否移动。
        参数:
            user_folder_path (str): 用户文件夹路径。
            target_path (str): 目标路径。
        """
        subfolders = [f for f in os.listdir(user_folder_path) if os.path.isdir(os.path.join(user_folder_path, f))]
        
        if len(subfolders) == 1:
            target_folder_path = os.path.join(target_path, os.path.basename(user_folder_path))
            move_folder(user_folder_path, target_folder_path)
            logging.debug(f"[L9][移动] 移动文件夹：{user_folder_path} -> {target_folder_path}")
        else:
            logging.debug(f"[L9][移动] 跳过用户文件夹（子文件夹数量超过 1）：{user_folder_path}")

    def process_social_folder(self, social_folder_path, target_path):
        """
        处理社团文件夹，社团文件夹下是用户文件夹，检查用户文件夹的子文件夹数量。
        参数:
            social_folder_path (str): 社团文件夹路径。
            target_path (str): 目标路径。
        """
        social_folder_name = os.path.basename(social_folder_path)
        target_social_folder_path = os.path.join(target_path, social_folder_name)

        if not os.path.exists(target_social_folder_path):
            os.makedirs(target_social_folder_path)
            logging.debug(f"[L9][移动] 创建目标社团目录：{target_social_folder_path}")

        for user_folder_name in os.listdir(social_folder_path):
            user_folder_path = os.path.join(social_folder_path, user_folder_name)

            if not os.path.isdir(user_folder_path):
                continue

            if user_folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                logging.debug(f"[L9][移动] 跳过用户文件夹（在跳过列表中）：{user_folder_name}")
                continue

            # 处理社团文件夹中的用户文件夹
            self.process_user_folder(user_folder_path, target_social_folder_path)

        # 移动社团文件夹（如果为空）
        if not os.listdir(social_folder_path):
            os.rmdir(social_folder_path)
            logging.debug(f"[L9][移动] 删除空的社团文件夹：{social_folder_path}")
