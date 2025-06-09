"""
图片生成模块

将统计文本转换为图片，用于Gotify消息推送
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import textwrap
import base64
import io
from datetime import datetime
import asyncio
import httpx


class StatisticsImageGenerator:
    def __init__(self, width=800, height=1200, bg_color=(255, 255, 255), text_color=(33, 37, 41), use_background_image=True):
        """
        初始化图片生成器
        
        参数：
            width: 图片宽度
            height: 图片高度 
            bg_color: 背景颜色 (R, G, B)
            text_color: 文字颜色 (R, G, B)
            use_background_image: 是否使用随机背景图
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.use_background_image = use_background_image
        
        # 背景图API设置
        self.background_api = "https://www.loliapi.com/acg/pe"
        self.background_timeout = 5
        
        # 高对比度颜色
        self.text_primary = (15, 25, 35)
        self.text_secondary = (60, 70, 85)
        self.text_muted = (100, 110, 125)
        
        self.primary_color = (30, 80, 160)
        self.primary_light = (90, 140, 200)
        
        # 状态
        self.success_color = (10, 120, 80)
        self.success_light = (60, 160, 120)
        self.warning_color = (180, 120, 0)
        self.warning_light = (220, 160, 40)
        self.danger_color = (160, 40, 40)
        self.danger_light = (200, 80, 80)
        
        # 背景和边框
        self.bg_primary = (255, 255, 255)
        self.bg_secondary = (249, 250, 251)
        self.bg_tertiary = (243, 244, 246)
        
        self.border_light = (229, 231, 235)
        self.border_medium = (209, 213, 219)
        
        # 卡片
        self.card_bg = (255, 255, 255)
        self.card_hover_bg = (249, 250, 251)
        
        # 字体
        self.font_path = self._get_font_path()
        self.title_font_size = 28
        self.subtitle_font_size = 14
        self.header_font_size = 16
        self.normal_font_size = 13
        self.small_font_size = 11
        
        # 布局
        self.margin = 24
        self.card_margin = 16
        self.card_padding = 20
        self.card_radius = 8
        self.section_spacing = 32
        
        # 阴影
        self.shadow_color = (0, 0, 0, 25)
        self.shadow_blur = 1
        self.shadow_offset = 2
        
    def _get_font_path(self):
        """获取系统字体路径"""
        fonts = [
            "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
        ]
        
        for font_path in fonts:
            if os.path.exists(font_path):
                print(f"DEBUG: 使用字体: {font_path}")
                return font_path
        
        print("DEBUG: 未找到系统字体，将使用默认字体")
        return None
    
    def _get_font(self, size):
        """获取指定大小的字体"""
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, size)
            return ImageFont.load_default()
        except:
            return ImageFont.load_default()
    
    def _draw_text(self, draw, text, position, fill, font):
        """绘制纯文本"""
        try:
            draw.text(position, text, fill=fill, font=font)
        except Exception as e:
            print(f"DEBUG: 文本绘制失败: {e}")
            try:
                safe_text = text.encode('ascii', 'ignore').decode('ascii')
                draw.text(position, safe_text, fill=fill, font=font)
            except:
                draw.text(position, text, fill=fill, font=ImageFont.load_default())
    
    def _wrap_text(self, text, font, max_width):
        """文本换行处理"""
        lines = []
        for line in text.split('\n'):
            if not line.strip():
                lines.append('')
                continue
                
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                lines.append(line)
            else:
                words = line.split(' ')
                current_line = ''
                
                for word in words:
                    test_line = current_line + ' ' + word if current_line else word
                    bbox = font.getbbox(test_line)
                    test_width = bbox[2] - bbox[0]
                    
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
        
        return lines
    
    async def generate_statistics_image_async(self, report_text, title="处理统计报告"):
        """
        异步生成统计图片
        
        参数：
            report_text: 统计报告文本
            title: 图片标题
            
        返回：
            PIL.Image: 生成的图片对象
        """
        try:
            print("DEBUG: 开始生成统计图片...")
            
            # 解析报告文本，提取统计数据
            stats_data = self._parse_report_text(report_text)
            print(f"DEBUG: 解析到 {len(stats_data)} 个统计项目")
            
            # 计算总体统计
            total_overview = self._calculate_overview(stats_data)
            
            # 动态计算高度 - 使用实际绘制需要的高度
            header_height = 120
            overview_height = 140  
            
            # 计算详情区域的实际高度（与绘制函数保持一致）
            actual_details_height = self._calculate_actual_details_height(stats_data)
            
            estimated_height = header_height + overview_height + actual_details_height + self.margin
            dynamic_height = max(600, estimated_height)
            
            # 如果数据量很大，考虑增加宽度
            active_stats = [stat for stat in stats_data if stat['title'] and stat['total'] > 0]
            if len(active_stats) > 6:
                original_width = self.width
                self.width = min(1200, self.width + (len(active_stats) - 6) * 50)
                print(f"DEBUG: 数据量大，调整宽度: {original_width} -> {self.width}")
            
            print(f"DEBUG: 计算图片尺寸: {self.width}x{dynamic_height}")
            
            # 更新高度以便背景图处理
            original_height = self.height
            self.height = dynamic_height
            
            # 处理背景
            background_img = None
            if self.use_background_image:
                background_img = await self._download_background_image()
                if background_img:
                    background_img = self._process_background_image(background_img)
            
            # 创建最终背景
            img = self._create_background_with_overlay(background_img)
            draw = ImageDraw.Draw(img)
            print("DEBUG: 背景创建完成")
            
            # 恢复原始尺寸设置
            self.height = original_height
            if len(active_stats) > 6:
                self.width = original_width
            
            # 获取字体
            title_font = self._get_font(self.title_font_size)
            subtitle_font = self._get_font(self.subtitle_font_size)
            header_font = self._get_font(self.header_font_size)
            normal_font = self._get_font(self.normal_font_size)
            print("DEBUG: 字体加载完成")
            
            y_position = self.margin
            
            # 绘制页面标题
            self._draw_page_header(draw, title, y_position, title_font, subtitle_font)
            y_position += header_height
            
            # 绘制统计概览
            self._draw_overview_section(draw, total_overview, y_position, header_font, normal_font)
            y_position += overview_height
            
            # 绘制处理详情网格
            self._draw_details_grid(draw, stats_data, y_position, header_font, normal_font)
            
            print("DEBUG: 现代Dashboard统计图片生成完成")
            return img
            
        except Exception as e:
            print(f"DEBUG: 图片生成过程中出错: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _calculate_overview(self, stats_data):
        """计算总体统计概览"""
        total_all = sum(stat['total'] for stat in stats_data)
        total_success = sum(stat['success'] for stat in stats_data)
        total_failed = sum(stat['failed'] for stat in stats_data)
        total_skipped = sum(stat['skipped'] for stat in stats_data)
        
        # 统计各个处理器的状态
        active_processors = len([stat for stat in stats_data if stat['total'] > 0])
        
        return {
            'total': total_all,
            'success': total_success,
            'failed': total_failed,
            'skipped': total_skipped,
            'active_processors': active_processors,
            'total_processors': len(stats_data)
        }
    
    def _calculate_details_height(self, stats_data):
        """统一计算详情区域的准确高度，确保包含所有内容"""
        active_stats = [stat for stat in stats_data if stat['title'] and stat['total'] > 0]
        
        if not active_stats:
            return 100
        
        total_height = 70
        
        for i, stat in enumerate(active_stats):
            # 如果不是第一个处理器，添加分隔线空间
            if i > 0:
                total_height += 15
            
            # 处理器基础行高（标题行 + 统计数字 + 状态）
            processor_height = 60
            
            # 计算用户详情高度
            detail_lines = 0
            
            # 失败用户详情
            if stat.get('failed_users'):
                failed_count = len(stat['failed_users'])
                detail_lines += min(3, failed_count)
                if failed_count > 3:
                    detail_lines += 1
            
            # 跳过用户详情  
            if stat.get('skipped_users'):
                for skip_group in stat['skipped_users']:
                    if skip_group.get('users'):
                        detail_lines += 1
            
            # 处理器总高度：基础高度 + 详情行高度
            processor_total_height = processor_height + detail_lines * 22
            total_height += processor_total_height
        
        total_height += 40
        
        print(f"DEBUG: 计算详情区域高度: {total_height}px，活跃处理器: {len(active_stats)}个")
        
        return total_height
    
    def _calculate_row_height(self, stat):
        """计算单个处理器行的精确高度"""
        # 基础行高（标题行 + 统计数字 + 状态）
        row_height = 60
        
        # 计算用户详情高度
        detail_lines = 0
        
        # 失败用户详情
        if stat.get('failed_users'):
            failed_count = len(stat['failed_users'])
            detail_lines += min(3, failed_count)
            if failed_count > 3:
                detail_lines += 1
        
        # 跳过用户详情  
        if stat.get('skipped_users'):
            for skip_group in stat['skipped_users']:
                if skip_group.get('users'):
                    detail_lines += 1
        
        # 每行详情22px + 行间距15px
        row_height += detail_lines * 22 + 15
        
        return row_height
    
    def _calculate_actual_details_height(self, stats_data):
        """计算详情区域的实际高度（与绘制函数完全一致）"""
        active_stats = [stat for stat in stats_data if stat['title'] and stat['total'] > 0]
        
        # 标题行高度
        title_height = 20 + 40
        
        if not active_stats:
            return title_height + 30 + 30
        
        total_content_height = 0
        for stat in active_stats:
            row_height = self._calculate_row_height(stat)
            total_content_height += row_height
        
        # 总高度 = 标题高度 + 内容高度 + 底部边距
        total_height = title_height + total_content_height + 30
        
        return total_height
    
    def _draw_page_header(self, draw, title, y_pos, title_font, subtitle_font):
        """绘制页面标题区域"""
        # 主标题
        title_text = f"[统计] {title}"
        title_bbox = title_font.getbbox(title_text)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_width) // 2
        
        self._draw_text(
            draw, title_text, (title_x, y_pos),
            self.primary_color, title_font
        )
        
        # 时间副标题
        time_formatted = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        time_text = f"生成时间: {time_formatted}"
        time_bbox = subtitle_font.getbbox(time_text)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = (self.width - time_width) // 2
        
        self._draw_text(
            draw, time_text, (time_x, y_pos + 40),
            self.text_secondary, subtitle_font
        )
    
    def _draw_overview_section(self, draw, overview, y_pos, header_font, normal_font):
        """绘制统计概览区域"""
        # 概览卡片
        card_x1 = self.margin
        card_y1 = y_pos
        card_x2 = self.width - self.margin
        card_y2 = y_pos + 120
        
        # 绘制概览卡片
        self._draw_modern_card(draw, (card_x1, card_y1, card_x2, card_y2))
        
        # 卡片标题
        title_y = card_y1 + 15
        title_text = "[OPTIMIZE] 模块统计总览"
        self._draw_text(
            draw, title_text, (card_x1 + 20, title_y),
            self.primary_color, header_font
        )
        
        # 第一行：基本统计数据 - 真正居中显示
        content_y = title_y + 35
        
        overview_items = [
            ('总计', overview['total'], self.text_primary),
            ('成功', overview['success'], self.success_color),
            ('失败', overview['failed'], self.danger_color),
            ('跳过', overview['skipped'], self.warning_color)
        ]
        
        # 计算每个项目的实际宽度
        item_widths = []
        for label, count, color in overview_items:
            # 计算标签和数字的最大宽度
            label_bbox = normal_font.getbbox(label)
            count_bbox = header_font.getbbox(str(count))
            item_width = max(label_bbox[2] - label_bbox[0], count_bbox[2] - count_bbox[0])
            item_widths.append(item_width + 20)
        
        # 计算总宽度和起始位置实现居中
        total_width = sum(item_widths)
        available_width = card_x2 - card_x1 - 40
        start_x = card_x1 + 20 + (available_width - total_width) // 2
        
        current_x = start_x
        for i, (label, count, color) in enumerate(overview_items):
            # 计算每个项目的居中位置
            item_center_x = current_x + item_widths[i] // 2
            
            # 标签居中
            label_bbox = normal_font.getbbox(label)
            label_width = label_bbox[2] - label_bbox[0]
            label_x = item_center_x - label_width // 2
            self._draw_text(
                draw, label, (label_x, content_y),
                self.text_secondary, normal_font
            )
            
            # 数字居中
            count_text = str(count)
            count_bbox = header_font.getbbox(count_text)
            count_width = count_bbox[2] - count_bbox[0]
            count_x = item_center_x - count_width // 2
            self._draw_text(
                draw, count_text, (count_x, content_y + 25),
                color, header_font
            )
            
            current_x += item_widths[i]
        
        # 第二行：处理器状态信息
        status_y = content_y + 55
        status_text = f"活跃处理器: {overview['active_processors']}/{overview['total_processors']}"
        self._draw_text(
            draw, status_text, (card_x1 + 20, status_y),
            self.text_secondary, normal_font
            )
    
    def _draw_details_grid(self, draw, stats_data, y_pos, header_font, normal_font):
        """绘制OPTIMIZE处理详情"""
        # 整合详情卡片
        card_x1 = self.margin
        card_y1 = y_pos
        card_x2 = self.width - self.margin
        
        active_stats = [stat for stat in stats_data if stat['title'] and stat['total'] > 0]
        
        # 卡片标题
        title_y = card_y1 + 20
        section_title = "[详情] OPTIMIZE处理器详情"
        
        # 绘制每个活跃处理器的详情，计算实际需要的高度
        detail_y = title_y + 40
        current_y = detail_y
        
        if not active_stats:
            # 没有活跃处理器时显示提示
            empty_text = "暂无处理器运行数据"
            current_y += 30  # 为空提示预留空间
        else:
            for stat in active_stats:
                row_height = self._calculate_row_height(stat)
                current_y += row_height
        
        # 计算实际的卡片底部位置，加上底部边距
        card_y2 = current_y + 30  # 底部边距
        
        # 绘制整合卡片（现在有了准确的高度）
        self._draw_modern_card(draw, (card_x1, card_y1, card_x2, card_y2))
        
        # 绘制卡片标题
        self._draw_text(
            draw, section_title, (card_x1 + 20, title_y),
            self.text_primary, header_font
        )
        
        # 重新绘制内容（现在卡片背景已经绘制好了）
        current_y = detail_y
        
        if not active_stats:
            # 没有活跃处理器时显示提示
            empty_text = "暂无处理器运行数据"
            empty_bbox = normal_font.getbbox(empty_text)
            empty_width = empty_bbox[2] - empty_bbox[0]
            empty_x = card_x1 + (card_x2 - card_x1 - empty_width) // 2
            self._draw_text(
                draw, empty_text, (empty_x, current_y),
                self.text_muted, normal_font
            )
        else:
            for stat in active_stats:
                row_height = self._draw_integrated_detail_row(
                    draw, stat, current_y,
                    card_x1, card_x2, normal_font
                )
                current_y += row_height
    
    def _draw_integrated_detail_row(self, draw, stat, y_pos, card_x1, card_x2, normal_font):
        """绘制整合的处理器详情行"""
        padding = 20
        current_y = y_pos
        
        # 微妙的分隔线（除第一行外）
        if y_pos > card_x1 + 80:  # 不是第一行
            line_y = y_pos - 10
            draw.line([(card_x1 + padding, line_y), (card_x2 - padding, line_y)], 
                     fill=self.border_light, width=1)
        
        # 处理器标题行
        processor_name = stat['title'].replace(' 统计', '').replace('L', 'L')
        name_text = f"[{processor_name}]"
        self._draw_text(
            draw, name_text, (card_x1 + padding, current_y),
            self.text_primary, normal_font
        )
        
        # 右侧：统计数字
        stats_x_start = card_x1 + 200
        stat_spacing = 80
        
        stat_items = []
        if stat['total'] > 0:
            stat_items.append(('总数', stat['total'], self.text_primary))
            if stat['success'] > 0:
                stat_items.append(('成功', stat['success'], self.success_color))
            if stat['failed'] > 0:
                stat_items.append(('失败', stat['failed'], self.danger_color))
            if stat['skipped'] > 0:
                stat_items.append(('跳过', stat['skipped'], self.warning_color))
        
        for i, (label, count, color) in enumerate(stat_items):
            x_pos = stats_x_start + i * stat_spacing
            if x_pos + 60 <= card_x2 - padding:
                stat_text = f"{label}:{count}"
                self._draw_text(
                    draw, stat_text, (x_pos, current_y),
                    color, normal_font
                )
        
        # 状态指示
        status_text = ""
        status_color = self.text_secondary
        
        if stat['total'] == 0:
            status_text = "[未运行]"
            status_color = self.text_muted
        elif stat['failed'] == 0 and stat['success'] > 0:
            status_text = "[完美]"
            status_color = self.success_color
        elif stat['failed'] > 0:
            status_text = "[有问题]"
            status_color = self.warning_color
        
        if status_text:
            status_x = card_x2 - padding - 80
            self._draw_text(
                draw, status_text, (status_x, current_y + 20),
                status_color, normal_font
            )
        
        current_y += 40  # 基础行高
        
        # 绘制失败用户详情
        if stat.get('failed_users'):
            failed_to_show = stat['failed_users'][:3]  # 最多显示3个
            for i, failed_user in enumerate(failed_to_show):
                detail_text = f"  失败: {failed_user['name']} - {failed_user['reason']}"
                self._draw_text(
                    draw, detail_text, (card_x1 + padding + 20, current_y),
                    self.danger_color, normal_font
                )
                current_y += 20
            
            if len(stat['failed_users']) > 3:
                more_text = f"  ...还有 {len(stat['failed_users']) - 3} 个失败用户"
                self._draw_text(
                    draw, more_text, (card_x1 + padding + 20, current_y),
                    self.text_muted, normal_font
                )
                current_y += 20
        
        # 绘制跳过用户详情
        if stat.get('skipped_users'):
            for skip_group in stat['skipped_users']:
                if skip_group.get('users'):
                    user_list = skip_group['users'][:5]  # 最多显示5个用户
                    users_text = ', '.join(user_list)
                    if len(skip_group['users']) > 5:
                        users_text += f" ...等{len(skip_group['users'])}个"
                    
                    detail_text = f"  跳过({skip_group['reason']}): {users_text}"
                    self._draw_text(
                        draw, detail_text, (card_x1 + padding + 20, current_y),
                        self.warning_color, normal_font
                    )
                    current_y += 20
        
        return current_y - y_pos + 15  # 返回总高度
    
    def _draw_modern_card(self, draw, coords):
        """绘制卡片"""
        x1, y1, x2, y2 = coords
        
        # 绘制更柔和的多层渐变阴影 - 使用真正的RGBA透明度
        shadow_layers = 8  # 增加层数创建更平滑的阴影
        max_offset = 2.5   # 减小最大偏移距离
        max_alpha = 20     # 降低最大透明度，创建更微妙的效果
        
        for i in range(shadow_layers):
            # 使用非线性渐变，外层阴影更加透明
            progress = i / (shadow_layers - 1)  # 0到1的进度
            # 使用平方根函数创建柔和的渐变曲线
            eased_progress = progress ** 0.7
            
            # 透明度：内层较强，外层极弱
            shadow_alpha = int(max_alpha * (1 - eased_progress))
            
            # 偏移：使用更小的渐进偏移
            shadow_offset_x = max_offset * eased_progress
            shadow_offset_y = max_offset * eased_progress * 1.2  # Y方向稍微多一点
            
            # 阴影颜色：使用RGBA格式的真正透明度
            shadow_color = (80, 80, 80, shadow_alpha)  # 深灰色带透明度
            
            self._draw_rounded_rectangle(
                draw, 
                (x1 + shadow_offset_x, y1 + shadow_offset_y, 
                 x2 + shadow_offset_x, y2 + shadow_offset_y),
                self.card_radius, 
                shadow_color, 
                None, 0
            )
        
        # 绘制真正透明的毛玻璃卡片 - 使用RGBA格式
        glass_alpha = 40  # 约15%的不透明度 (40/255 ≈ 0.16)
        glass_color_rgba = (255, 255, 255, glass_alpha)  # 白色带真正的透明度
        
        # 边框也使用真正的透明度
        border_alpha = 60  # 约23%的不透明度
        border_color_rgba = (200, 200, 220, border_alpha)  # 淡蓝灰色带透明度
        
        self._draw_rounded_rectangle(
            draw, coords, self.card_radius,
            glass_color_rgba, border_color_rgba, 1
        )
    
    def _parse_report_text(self, report_text):
        """解析报告文本，提取统计数据和详细用户信息"""
        stats_data = []
        lines = report_text.split('\n')
        current_section = None
        parsing_failed = False
        parsing_skipped = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 检测节标题
            if line.startswith('=====') and line.endswith('====='):
                section_name = line.replace('=', '').strip()
                current_section = {
                    'title': section_name,
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'skipped': 0,
                    'failed_users': [],      # 失败用户详情
                    'skipped_users': [],     # 跳过用户详情
                    'success_users': []      # 成功用户列表
                }
                stats_data.append(current_section)
                parsing_failed = False
                parsing_skipped = False
            elif current_section and line.startswith('总数:'):
                # 解析统计数字
                parts = line.split('|')
                for part in parts:
                    part = part.strip()
                    if part.startswith('总数:'):
                        current_section['total'] = int(part.split(':')[1].strip())
                    elif part.startswith('成功:'):
                        current_section['success'] = int(part.split(':')[1].strip())
                    elif part.startswith('失败:'):
                        current_section['failed'] = int(part.split(':')[1].strip())
                    elif part.startswith('跳过:'):
                        current_section['skipped'] = int(part.split(':')[1].strip())
            elif current_section:
                # 解析详细信息
                if line == '失败:':
                    parsing_failed = True
                    parsing_skipped = False
                elif line == '跳过:':
                    parsing_failed = False
                    parsing_skipped = True
                elif line.startswith('- ') and parsing_failed:
                    # 解析失败用户：格式 "- 用户名: 原因"
                    if ':' in line:
                        user_info = line[2:].split(':', 1)
                        if len(user_info) == 2:
                            current_section['failed_users'].append({
                                'name': user_info[0].strip(),
                                'reason': user_info[1].strip()
                            })
                elif line.startswith('- ') and parsing_skipped:
                    # 解析跳过原因和数量
                    if ':' in line:
                        reason_info = line[2:].split(':', 1)
                        if len(reason_info) == 2:
                            reason = reason_info[0].strip()
                            count_text = reason_info[1].strip()
                            # 提取数量
                            if '个' in count_text:
                                count_part = count_text.split('个')[0].strip()
                                try:
                                    count = int(count_part)
                                    current_section['skipped_users'].append({
                                        'reason': reason,
                                        'count': count,
                                        'users': []
                                    })
                                except ValueError:
                                    pass
                elif parsing_skipped and current_section['skipped_users'] and not line.startswith('- '):
                    # 这行是跳过用户的列表（逗号分隔）
                    if current_section['skipped_users']:
                        last_skip_entry = current_section['skipped_users'][-1]
                        users = [u.strip() for u in line.split(',') if u.strip()]
                        last_skip_entry['users'].extend(users)
        
        return stats_data
    
    def generate_statistics_image(self, report_text, title="处理统计报告"):
        """
        同步生成统计图片
        
        参数：
            report_text: 统计报告文本
            title: 图片标题
            
        返回：
            PIL.Image: 生成的图片对象
        """
        try:
            # 尝试获取现有事件循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步环境中，创建新的事件循环
                import threading
                result = [None]
                exception = [None]
                
                def run_async():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result[0] = new_loop.run_until_complete(self.generate_statistics_image_async(report_text, title))
                        new_loop.close()
                    except Exception as e:
                        exception[0] = e
                
                thread = threading.Thread(target=run_async)
                thread.start()
                thread.join()
                
                if exception[0]:
                    raise exception[0]
                return result[0]
            else:
                # 直接运行异步方法
                return loop.run_until_complete(self.generate_statistics_image_async(report_text, title))
        except:
            # 如果没有事件循环，创建新的
            return asyncio.run(self.generate_statistics_image_async(report_text, title))
    

    
    def _draw_elegant_progress_bar(self, draw, x, y, width, stat):
        """进度条"""
        progress_height = 8
        bg_y1 = y
        bg_y2 = y + progress_height
        
        # 进度条背景
        self._draw_rounded_rectangle(
            draw,
            (x, bg_y1, x + width, bg_y2),
            4,
            (241, 245, 249),  # 浅背景色
            None,
            0
        )
        
        if stat['total'] > 0:
            # 成功进度
            success_ratio = stat['success'] / stat['total']
            success_width = int(width * success_ratio)
            
            if success_width > 6:  # 只有当宽度足够时才绘制
                self._draw_rounded_rectangle(
                    draw,
                    (x, bg_y1, x + success_width, bg_y2),
                    4,
                    self.success_color,
                    None,
                    0
                )
            
            # 失败进度（如果有）
            if stat['failed'] > 0:
                failed_ratio = stat['failed'] / stat['total']
                failed_width = int(width * failed_ratio)
                failed_start = x + success_width
                
                if failed_width > 6 and failed_start + failed_width <= x + width:
                    self._draw_rounded_rectangle(
                        draw,
                        (failed_start, bg_y1, failed_start + failed_width, bg_y2),
                        4,
                        self.danger_color,
                        None,
                        0
                    )
    
    def save_image(self, image, filename=None, output_dir="temp_images"):
        """
        保存图片到文件
        
        参数：
            image: PIL.Image对象
            filename: 文件名，如果为None则自动生成
            output_dir: 输出目录
            
        返回：
            str: 保存的文件路径
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"statistics_{timestamp}.png"
        
        # 确保文件名以.png结尾
        if not filename.lower().endswith('.png'):
            filename += '.png'
        
        file_path = os.path.join(output_dir, filename)
        image.save(file_path, 'PNG', optimize=True)
        
        return file_path

    def image_to_base64(self, image, format='PNG', optimize=True, quality=85):
        """
        将PIL图片对象转换为Base64编码的Data URL
        
        参数：
            image: PIL.Image对象
            format: 图片格式 ('PNG', 'JPEG')
            optimize: 是否优化图片
            quality: JPEG质量 (1-100)
            
        返回：
            str: Base64编码的Data URL
        """
        buffer = io.BytesIO()
        
        if format.upper() == 'JPEG':
            # JPEG不支持透明度，需要转换为RGB
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(buffer, format='JPEG', optimize=optimize, quality=quality)
            mime_type = 'image/jpeg'
        else:
            image.save(buffer, format='PNG', optimize=optimize)
            mime_type = 'image/png'
        
        buffer.seek(0)
        image_data = buffer.getvalue()
        
        # 转换为Base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # 创建Data URL
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        return data_url
    
    def generate_markdown_with_image(self, report_text, title="处理统计报告", use_base64=True):
        """
        生成包含图片的Markdown文本
        
        参数：
            report_text: 统计报告文本
            title: 图片标题
            use_base64: 是否使用Base64嵌入图片
            
        返回：
            tuple: (markdown_text, image_data_url_or_path)
        """
        # 生成图片
        image = self.generate_statistics_image_async(report_text, title)
        
        if use_base64:
            # 转换为Base64 Data URL
            data_url = self.image_to_base64(image, format='PNG')
            
            # 创建包含图片的Markdown
            markdown_text = f"""# {title}

![统计报告图片]({data_url})

---

### 详细信息：
```
{report_text}
```
"""
            return markdown_text, data_url
        else:
            # 保存图片并返回路径
            image_path = self.save_image(image)
            
            markdown_text = f"""# {title}

![统计报告图片]({image_path})

---

### 详细信息：
```
{report_text}
```
"""
            return markdown_text, image_path

    def _draw_rounded_rectangle(self, draw, coords, radius, fill_color, outline_color=None, outline_width=1):
        """绘制圆角矩形（支持透明度）"""
        x1, y1, x2, y2 = coords
        
        # 确保坐标是整数
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        # 如果颜色包含透明度，需要特殊处理
        if isinstance(fill_color, tuple) and len(fill_color) == 4:
            # 创建临时图层来处理透明度
            temp_img = Image.new('RGBA', (x2-x1, y2-y1), (0, 0, 0, 0))
            temp_draw = ImageDraw.Draw(temp_img)
            
            # 在临时图层上绘制圆角矩形
            temp_draw.rounded_rectangle(
                (0, 0, x2-x1, y2-y1),
                radius=radius,
                fill=fill_color
            )
            
            # 如果原图是RGB模式，需要转换
            if hasattr(draw, '_image') and draw._image.mode == 'RGB':
                # 创建一个与原图相同的RGBA图层
                overlay = Image.new('RGBA', draw._image.size, (0, 0, 0, 0))
                overlay.paste(temp_img, (x1, y1))
                
                # 转换原图为RGBA
                draw._image = draw._image.convert('RGBA')
                draw._image = Image.alpha_composite(draw._image, overlay)
                
                # 重新创建draw对象
                draw = ImageDraw.Draw(draw._image)
            else:
                # 直接粘贴透明图层
                if hasattr(draw, '_image'):
                    draw._image.paste(temp_img, (x1, y1), temp_img)
        else:
            # 普通颜色，使用标准方法
            try:
                # 尝试使用现代PIL的rounded_rectangle方法
                draw.rounded_rectangle(
                    coords,
                    radius=radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_width
                )
            except AttributeError:
                # 回退到手动绘制
                self._draw_rounded_rectangle_manual(draw, coords, radius, fill_color, outline_color, outline_width)
    
    def _draw_rounded_rectangle_manual(self, draw, coords, radius, fill_color, outline_color=None, outline_width=1):
        """手动绘制圆角矩形（兼容旧版PIL）"""
        x1, y1, x2, y2 = coords
        
        # 绘制圆角矩形的各个部分
        # 中间矩形
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill_color)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill_color)
        
        # 四个圆角
        draw.pieslice([x1, y1, x1 + 2*radius, y1 + 2*radius], 180, 270, fill=fill_color)
        draw.pieslice([x2 - 2*radius, y1, x2, y1 + 2*radius], 270, 360, fill=fill_color)
        draw.pieslice([x1, y2 - 2*radius, x1 + 2*radius, y2], 90, 180, fill=fill_color)
        draw.pieslice([x2 - 2*radius, y2 - 2*radius, x2, y2], 0, 90, fill=fill_color)
        
        # 绘制边框
        if outline_color:
            self._draw_rounded_rectangle_outline(draw, coords, radius, outline_color, outline_width)
    
    def _draw_rounded_rectangle_outline(self, draw, coords, radius, color, width):
        """绘制圆角矩形边框"""
        x1, y1, x2, y2 = coords
        
        # 绘制四条边
        for i in range(width):
            # 上边
            draw.line([(x1 + radius, y1 + i), (x2 - radius, y1 + i)], fill=color)
            # 下边
            draw.line([(x1 + radius, y2 - i), (x2 - radius, y2 - i)], fill=color)
            # 左边
            draw.line([(x1 + i, y1 + radius), (x1 + i, y2 - radius)], fill=color)
            # 右边
            draw.line([(x2 - i, y1 + radius), (x2 - i, y2 - radius)], fill=color)
        
        # 绘制圆角边框
        for i in range(width):
            draw.arc([x1 + i, y1 + i, x1 + 2*radius - i, y1 + 2*radius - i], 180, 270, fill=color)
            draw.arc([x2 - 2*radius + i, y1 + i, x2 - i, y1 + 2*radius - i], 270, 360, fill=color)
            draw.arc([x1 + i, y2 - 2*radius + i, x1 + 2*radius - i, y2 - i], 90, 180, fill=color)
            draw.arc([x2 - 2*radius + i, y2 - 2*radius + i, x2 - i, y2 - i], 0, 90, fill=color)
    
    def _draw_gradient_background(self, draw, width, height):
        """绘制更优雅的渐变背景"""
        for y in range(height):
            # 创建从上到下的柔和渐变
            ratio = y / height
            
            # 使用三次方函数创建更自然的渐变
            smooth_ratio = ratio * ratio * (3 - 2 * ratio)
            
            r = int(self.bg_primary[0] + (self.bg_secondary[0] - self.bg_primary[0]) * smooth_ratio)
            g = int(self.bg_primary[1] + (self.bg_secondary[1] - self.bg_primary[1]) * smooth_ratio)
            b = int(self.bg_primary[2] + (self.bg_secondary[2] - self.bg_primary[2]) * smooth_ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    def _draw_gradient_background_rgba(self, draw, width, height):
        """绘制支持RGBA的优雅渐变背景"""
        for y in range(height):
            # 创建从上到下的柔和渐变
            ratio = y / height
            
            # 使用三次方函数创建更自然的渐变
            smooth_ratio = ratio * ratio * (3 - 2 * ratio)
            
            r = int(self.bg_primary[0] + (self.bg_secondary[0] - self.bg_primary[0]) * smooth_ratio)
            g = int(self.bg_primary[1] + (self.bg_secondary[1] - self.bg_primary[1]) * smooth_ratio)
            b = int(self.bg_primary[2] + (self.bg_secondary[2] - self.bg_primary[2]) * smooth_ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    def _get_status_icon(self, status_type):
        """获取状态图标"""
        icons = {
            'success': '✅',
            'warning': '⚠️', 
            'danger': '❌',
            'info': 'ℹ️',
            'total': '📊',
            'folder': '📁',
            'chart': '📈',
            'check': '✔️',
            'cross': '✖️'
        }
        return icons.get(status_type, '•')

    def _draw_card_shadow(self, draw, coords, radius, shadow_color, offset=4):
        """绘制卡片阴影效果"""
        x1, y1, x2, y2 = coords
        # 绘制多层阴影创建柔和效果
        for i in range(offset):
            alpha = max(10, 40 - i * 8)  # 递减的透明度
            shadow_x1 = x1 + i + 1
            shadow_y1 = y1 + i + 1
            shadow_x2 = x2 + i + 1
            shadow_y2 = y2 + i + 1
            
            # 使用更简单的方法绘制阴影
            shadow_color_with_alpha = (*shadow_color[:3], alpha)
            self._draw_rounded_rectangle(
                draw,
                (shadow_x1, shadow_y1, shadow_x2, shadow_y2),
                radius,
                (200, 200, 200, alpha),  # 浅灰色阴影
                None,
                0
            )

    async def _download_background_image(self):
        """异步下载随机背景图"""
        try:
            print("DEBUG: 开始下载随机背景图...")
            async with httpx.AsyncClient(
                timeout=self.background_timeout, 
                follow_redirects=True  # 自动跟随重定向
            ) as client:
                response = await client.get(self.background_api)
                if response.status_code == 200:
                    # 检查响应是否真的是图片
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' in content_type:
                        image_data = response.content
                        background_img = Image.open(io.BytesIO(image_data))
                        print(f"DEBUG: 背景图下载成功，尺寸: {background_img.size}, 类型: {content_type}")
                        return background_img
                    else:
                        print(f"DEBUG: 响应不是图片格式，Content-Type: {content_type}")
                        return None
                else:
                    print(f"DEBUG: 背景图下载失败，状态码: {response.status_code}")
                    return None
        except Exception as e:
            print(f"DEBUG: 背景图下载异常: {e}")
            return None
    
    def _process_background_image(self, background_img):
        """智能背景图处理：等比缩放适配画布，无拉伸变形"""
        try:
            # 获取原始尺寸
            bg_width, bg_height = background_img.size
            canvas_ratio = self.width / self.height
            bg_ratio = bg_width / bg_height
            
            print(f"DEBUG: 原始背景图尺寸: {bg_width}x{bg_height}, 比例: {bg_ratio:.2f}")
            print(f"DEBUG: 画布尺寸: {self.width}x{self.height}, 比例: {canvas_ratio:.2f}")
            
            # 智能选择最佳缩放策略
            ratio_diff = abs(canvas_ratio - bg_ratio)
            
            if ratio_diff < 0.1:
                # 比例非常接近，直接等比缩放到画布大小
                scaling_mode = "直接适配"
                new_width = self.width
                new_height = self.height
                
                # 微调以保持等比例
                scale_w = self.width / bg_width
                scale_h = self.height / bg_height
                scale = min(scale_w, scale_h)  # 使用较小的缩放比例确保不拉伸
                
                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)
                
            else:
                # 比例差异较大，使用覆盖模式（裁剪显示）确保填满画布
                scaling_mode = "覆盖适配"
                scale_w = self.width / bg_width
                scale_h = self.height / bg_height
                scale = max(scale_w, scale_h)  # 使用较大的缩放比例确保填满
                
                new_width = int(bg_width * scale)
                new_height = int(bg_height * scale)
            
            print(f"DEBUG: 缩放策略: {scaling_mode}")
            print(f"DEBUG: 缩放后尺寸: {new_width}x{new_height}")
            
            # 高质量等比缩放
            background_img = background_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 创建画布（优雅的渐变背景色）
            canvas_img = Image.new('RGB', (self.width, self.height))
            
            # 使用渐变背景填充，而不是单色
            for y in range(self.height):
                ratio = y / self.height
                # 从淡蓝灰色到淡紫灰色的渐变
                r = int(235 + (245 - 235) * ratio)
                g = int(240 + (242 - 240) * ratio)  
                b = int(250 + (255 - 250) * ratio)
                for x in range(self.width):
                    canvas_img.putpixel((x, y), (r, g, b))
            
            # 计算居中位置（可能会裁剪）
            paste_x = (self.width - new_width) // 2
            paste_y = (self.height - new_height) // 2
            
            print(f"DEBUG: 背景图放置位置: ({paste_x}, {paste_y})")
            
            # 智能粘贴：处理超出画布的情况
            if new_width > self.width or new_height > self.height:
                # 背景图超出画布，需要居中裁剪
                crop_x = max(0, (new_width - self.width) // 2)
                crop_y = max(0, (new_height - self.height) // 2)
                
                crop_box = (
                    crop_x,
                    crop_y,
                    crop_x + self.width,
                    crop_y + self.height
                )
                
                cropped_bg = background_img.crop(crop_box)
                canvas_img.paste(cropped_bg, (0, 0))
                print(f"DEBUG: 背景图裁剪区域: {crop_box}")
            else:
                # 背景图小于画布，居中放置
                canvas_img.paste(background_img, (paste_x, paste_y))
            
            # 应用渐进式模糊效果，让背景更加柔和
            canvas_img = canvas_img.filter(ImageFilter.GaussianBlur(radius=1.8))
            
            # 智能亮度和对比度调整
            from PIL import ImageEnhance, ImageStat
            
            # 分析图像亮度，智能调整（使用PIL内置统计）
            stat = ImageStat.Stat(canvas_img)
            avg_brightness = sum(stat.mean) / len(stat.mean)  # RGB平均值
            
            if avg_brightness > 180:
                # 图像较亮，降低亮度和对比度更多
                brightness_factor = 0.70
                contrast_factor = 0.80
            elif avg_brightness > 120:
                # 图像中等亮度，适度调整
                brightness_factor = 0.75
                contrast_factor = 0.85
            else:
                # 图像较暗，轻微调整
                brightness_factor = 0.80
                contrast_factor = 0.90
            
            enhancer = ImageEnhance.Brightness(canvas_img)
            canvas_img = enhancer.enhance(brightness_factor)
            
            enhancer = ImageEnhance.Contrast(canvas_img)
            canvas_img = enhancer.enhance(contrast_factor)
            
            # 增加微妙的饱和度调整
            enhancer = ImageEnhance.Color(canvas_img)
            canvas_img = enhancer.enhance(0.85)  # 稍微降低饱和度
            
            print(f"DEBUG: 背景图智能处理完成 - 亮度调整: {brightness_factor:.2f}, 对比度: {contrast_factor:.2f}")
            return canvas_img
            
        except Exception as e:
            print(f"DEBUG: 背景图处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_background_with_overlay(self, background_img=None):
        """创建带黑色遮罩的背景，支持透明度绘制"""
        if background_img:
            # 转换为RGBA模式以支持透明度
            if background_img.mode != 'RGBA':
                background_img = background_img.convert('RGBA')
            
            # 创建半透明黑色遮罩，提高文字对比度
            black_overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 70))  # 黑色遮罩，透明度90
            
            # 合成背景图和黑色遮罩，保持RGBA模式以支持透明卡片
            final_bg = Image.alpha_composite(background_img, black_overlay)
            return final_bg  # 保持RGBA模式
        else:
            # 回退到渐变背景，同样使用RGBA模式
            img = Image.new('RGBA', (self.width, self.height), (*self.bg_primary, 255))
            draw = ImageDraw.Draw(img)
            # 修改渐变背景函数以支持RGBA
            self._draw_gradient_background_rgba(draw, self.width, self.height)
            return img


def generate_statistics_image(report_text, title="处理统计报告", save_path=None):
    """
    便捷函数：生成统计图片
    
    参数：
        report_text: 统计报告文本
        title: 图片标题
        save_path: 保存路径，如果为None则保存到temp_images目录
        
    返回：
        str: 保存的文件路径
    """
    generator = StatisticsImageGenerator()
    image = generator.generate_statistics_image(report_text, title)
    
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        image.save(save_path, 'PNG', optimize=True)
        return save_path
    else:
        return generator.save_image(image)


def generate_statistics_markdown(report_text, title="处理统计报告", use_base64=True):
    """
    便捷函数：生成包含图片的Markdown统计报告
    
    参数：
        report_text: 统计报告文本
        title: 图片标题
        use_base64: 是否使用Base64嵌入图片（True）还是保存为文件（False）
        
    返回：
        tuple: (markdown_text, image_data_or_path)
    """
    generator = StatisticsImageGenerator()
    return generator.generate_markdown_with_image(report_text, title, use_base64)