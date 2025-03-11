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
    text += f"总数: {stats.total}\n"
    text += f"成功: {stats.success}\n"
    text += f"失败: {stats.failed}\n"
    text += f"跳过: {stats.skipped}\n"
    
    if stats.failed_names:
        text += "\n失败列表:\n"
        for item in stats.failed_names:
            text += f"- {item['name']}: {item['reason']}\n"
            
    if stats.skip_reasons:
        text += "\n跳过原因:\n"
        for reason, names in stats.skip_reasons.items():
            text += f"- {reason}: {len(names)} 个\n"
            for name in names:
                text += f"  * {name}\n"
                
    return text 