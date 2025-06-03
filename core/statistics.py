class Statistics:
    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.failed_names = []
        self.skip_reasons = {}  # 记录跳过原因
        
    def add_success(self):
        self.success += 1
        self.total += 1
        
    def add_failed(self, name, reason=""):
        self.failed += 1
        self.total += 1
        self.failed_names.append({"name": name, "reason": reason})
        
    def add_skipped(self, name, reason):
        self.skipped += 1
        self.total += 1
        if reason not in self.skip_reasons:
            self.skip_reasons[reason] = []
        self.skip_reasons[reason].append(name)

    def add_success_with_name(self, name):
        """添加成功记录，同时记录名称"""
        self.success += 1
        self.total += 1
        if "成功处理" not in self.skip_reasons:
            self.skip_reasons["成功处理"] = []
        self.skip_reasons["成功处理"].append(name)
    
    def merge_stats(self, other_stats):
        """合并另一个统计对象的数据"""
        self.total += other_stats.total
        self.success += other_stats.success
        self.failed += other_stats.failed
        self.skipped += other_stats.skipped
        self.failed_names.extend(other_stats.failed_names)
        for reason, names in other_stats.skip_reasons.items():
            if reason not in self.skip_reasons:
                self.skip_reasons[reason] = []
            self.skip_reasons[reason].extend(names)

    def get_summary(self):
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "failed_names": self.failed_names,
            "skip_reasons": self.skip_reasons
        }

    def reset(self):
        """重置所有统计数据"""
        self.total = 0
        self.success = 0
        self.failed = 0
        self.skipped = 0
        self.failed_names = []
        self.skip_reasons = {}

def format_statistics(stats, title):
    """格式化统计信息为易读的文本"""
    text = f"\n===== {title} =====\n"
    text += f"总数: {stats.total} | 成功: {stats.success} | 失败: {stats.failed} | 跳过: {stats.skipped}\n"
    
    if stats.failed_names:
        text += "\n失败列表:\n"
        for item in stats.failed_names:
            text += f"- {item['name']}: {item['reason']}\n"
            
    if stats.skip_reasons:
        text += "\n跳过原因:\n"
        
        # 对于L9，按子文件夹数量分组优化显示
        if "L9" in title:
            # 收集所有子文件夹数量相关的原因
            folder_count_users = []
            other_reasons = {}
            
            for reason, names in stats.skip_reasons.items():
                if not names:
                    continue
                    
                if reason.startswith("子文件夹数量为"):
                    folder_count = reason.split("子文件夹数量为")[1].strip()
                    for name in names:
                        folder_count_users.append(f"{name} ({folder_count})")
                else:
                    other_reasons[reason] = names
            
            # 显示其他原因
            for reason, names in other_reasons.items():
                text += f"- {reason}: {len(names)} 个\n"
                text += ", ".join(names) + "\n"
            
            # 显示子文件夹数量用户（统一标题）
            if folder_count_users:
                # 按数量排序
                folder_count_users.sort(key=lambda x: int(x.split('(')[1].split(')')[0]))
                text += f"- 子文件夹数量大于 2 的用户: {len(folder_count_users)} 个\n"
                text += ", ".join(folder_count_users) + "\n"
        
        else:
            # 普通格式：用户名用逗号分隔，一行显示
            for reason, names in stats.skip_reasons.items():
                if not names:
                    continue
                text += f"- {reason}: {len(names)} 个\n"
                text += ", ".join(names) + "\n"
                
    return text 