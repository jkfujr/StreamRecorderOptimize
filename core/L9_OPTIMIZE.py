import os
import logging
from .move import move_folder
from .statistics import Statistics

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
        self.stats = Statistics()  # 添加统计对象

    def process(self):
        """
        执行 L9 移动操作，将处理完成的文件夹从源路径移动到目标路径。
        """
        if not self.L2_OPTIMIZE_GLOBAL_MOVE:
            logging.info("[L9][移动] 移动功能被禁用")
            return self.stats

        for id, paths in self.L9_OPTIMIZE_GLOBAL_PATH.items():
            source_path = paths["source"]
            target_path = paths["target"]

            if not os.path.exists(source_path):
                continue

            for folder_name in os.listdir(source_path):
                folder_path = os.path.join(source_path, folder_name)

                if not os.path.isdir(folder_path):
                    continue

                if folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                    self.stats.add_skipped(folder_name, "在跳过列表中")
                    continue

                try:
                    if folder_name in self.L2_OPTIMIZE_GLOBAL_SOCIAL_FOLDERS:
                        self.process_social_folder(folder_path, target_path)
                    else:
                        self.process_user_folder(folder_path, target_path)
                except Exception as e:
                    self.stats.add_failed(folder_name, str(e))

        return self.stats

    def process_user_folder(self, user_folder_path, target_path):
        """
        处理用户文件夹的移动操作，根据子文件夹的数量决定是否移动。
        参数:
            user_folder_path (str): 用户文件夹路径。
            target_path (str): 目标路径。
        """
        folder_name = os.path.basename(user_folder_path)
        target_folder_path = os.path.join(target_path, folder_name)

        # 添加源路径和目标路径相同的跳过统计
        if os.path.abspath(user_folder_path) == os.path.abspath(target_folder_path):
            self.stats.add_skipped(folder_name, "源路径与目标路径相同")
            return

        # 添加目标路径在源路径下的跳过统计
        if os.path.abspath(target_folder_path).startswith(os.path.abspath(user_folder_path)):
            self.stats.add_skipped(folder_name, "目标路径在源路径下")
            return

        # 获取子文件夹列表
        subfolders = [f for f in os.listdir(user_folder_path) 
                     if os.path.isdir(os.path.join(user_folder_path, f))]

        if len(subfolders) == 1:
            try:
                move_folder(user_folder_path, target_folder_path)
                self.stats.add_success()
            except Exception as e:
                self.stats.add_failed(folder_name, str(e))
        else:
            self.stats.add_skipped(folder_name, f"子文件夹数量为 {len(subfolders)}")

    def process_social_folder(self, social_folder_path, target_path):
        """
        处理社团文件夹，社团文件夹下是用户文件夹，检查用户文件夹的子文件夹数量。
        参数:
            social_folder_path (str): 社团文件夹路径。
            target_path (str): 目标路径。
        """
        social_folder_name = os.path.basename(social_folder_path)
        target_social_folder_path = os.path.join(target_path, social_folder_name)

        try:
            if not os.path.exists(target_social_folder_path):
                os.makedirs(target_social_folder_path)
                logging.debug(f"[L9][移动] 创建目标社团目录：{target_social_folder_path}")
        except Exception as e:
            self.stats.add_failed(social_folder_name, f"创建目标目录失败: {str(e)}")
            return

        for user_folder_name in os.listdir(social_folder_path):
            user_folder_path = os.path.join(social_folder_path, user_folder_name)

            if not os.path.isdir(user_folder_path):
                continue

            if user_folder_name in self.L2_OPTIMIZE_GLOBAL_SKIP_FOLDERS:
                self.stats.add_skipped(user_folder_name, f"在跳过列表中 (社团: {social_folder_name})")
                continue

            # 检查目标路径是否与源路径相同
            target_user_folder_path = os.path.join(target_social_folder_path, user_folder_name)
            if os.path.abspath(user_folder_path) == os.path.abspath(target_user_folder_path):
                self.stats.add_skipped(user_folder_name, f"源路径与目标路径相同 (社团: {social_folder_name})")
                continue

            # 检查目标路径是否在源路径下
            if os.path.abspath(target_user_folder_path).startswith(os.path.abspath(user_folder_path)):
                self.stats.add_skipped(user_folder_name, f"目标路径在源路径下 (社团: {social_folder_name})")
                continue

            try:
                self.process_user_folder(user_folder_path, target_social_folder_path)
            except Exception as e:
                self.stats.add_failed(user_folder_name, f"处理失败 (社团: {social_folder_name}): {str(e)}")

        # 移动社团文件夹（如果为空）
        if not os.listdir(social_folder_path):
            os.rmdir(social_folder_path)
            logging.debug(f"[L9][移动] 删除空的社团文件夹：{social_folder_path}")


