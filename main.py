import os
import sys
import re
import fitz  # PyMuPDF

class PDFLayoutsInfo:
    """PDF布局信息类，用于存储不同布局的配置参数"""
    
    def __init__(self, page_width: float, page_height: float, cols: int, rows: int):
        """
        初始化布局信息
        
        参数:
        - page_width: 页面宽度（单位：点）
        - page_height: 页面高度（单位：点）
        - cols: 列数
        - rows: 行数
        """
        self.page_width = page_width
        self.page_height = page_height
        self.cols = cols
        self.rows = rows
        self.items_per_page = cols * rows
        self.orientation = "横向" if page_width > page_height else "竖向"
    
    def get_description(self):
        """获取布局描述"""
        return f"{self.orientation} {self.cols}x{self.rows}"

# 定义A4页面尺寸
PAGE_SIZE = (595, 842)

# 定义所有布局
LAYOUTS = {
    "2x2_h": PDFLayoutsInfo(PAGE_SIZE[1], PAGE_SIZE[0], 2, 2),
    "1x2_v": PDFLayoutsInfo(PAGE_SIZE[0], PAGE_SIZE[1], 1, 2),
    "1x3_v": PDFLayoutsInfo(PAGE_SIZE[0], PAGE_SIZE[1], 1, 3),
    "2x4_v": PDFLayoutsInfo(PAGE_SIZE[0], PAGE_SIZE[1], 2, 4)
}
DEFAULT_LAYOUT = "2x2_h"
DEFAULT_ALIGN = "center"  # 默认对齐方式：center, left, right
def get_file_from_folders(source_folders):
    """
    从指定的文件夹列表中获取所有PDF文件
    """

    all_pdf_files = []
    
    for source_folder in source_folders:
        if not os.path.exists(source_folder):
            print(f"警告：目录不存在: {source_folder}")
            continue
            
        print(f"扫描目录: {source_folder}")
        files_num = 0
        for file in os.listdir(source_folder):
            if file.lower().endswith('.pdf'):
                all_pdf_files.append(os.path.join(source_folder, file))
                files_num += 1
                print(f"  找到文件: {file}")
        
        print(f"  目录 {source_folder} 共找到 {files_num} 个PDF文件")
    
    return all_pdf_files
# 读取发票金额
def read_pdf_amount(pdf_file_path) -> float:
    """
    从PDF文件中读取发票金额。
    """
    single_pdf = fitz.open(pdf_file_path)
    # 获取第一页
    invoice_page = single_pdf[0]

    amount_max = read_invoice_amount(invoice_page)
    print(f"  发票 {os.path.basename(pdf_file_path)} 金额: {amount_max}")
    return amount_max

# 读取发票金额
def read_invoice_amount(page) -> float:
    """
    从PDF文件中读取发票金额。
    核心思路：提取文本与坐标 -> 定位关键词 -> 匹配附近金额数字
    """
    amount = 0.0

    # 提取带详细坐标信息的文本块
    # 使用 “dict” 或 “blocks” 格式以获得位置信息
    blocks = page.get_text("blocks")  # 每个block包含(x0, y0, x1, y1, "文本", ...)
    # 或使用：text_dict = page.get_text("dict")

    # 定义可能表示金额的关键词
    amount_keywords = ["价税合计", "合计", "金额", "¥", "￥", "小写"]

    # 可能存在多个金额，取最大的
    amount_max = 0.0

    # 遍历文本块，寻找关键词及附近的金额
    print("-" * 20)
    print("  正在分析文本块以提取金额...")
    for block in blocks:
        x0, y0, x1, y1, text, block_no, block_type = block
        text_clean = text.strip()
        text_clean = text.replace(' ', '').strip()  # 去除空格

        # 检查当前文本块是否包含关键词
        for keyword in amount_keywords:
            if keyword in text_clean:
                # 策略A：关键词和金额在同一文本块内 (如"合计：¥155670.562")
                # 使用正则表达式直接在当前文本块中查找金额数字
                # 支持任意位数小数，支持间隔点作为小数点
                pattern = r'[¥￥]?\s*(\d+(?:,\d{3})*(?:[.·]\d+)?)'  # 匹配任意长度数字，支持千分位和任意位数小数，支持间隔点
                match = re.search(pattern, text_clean)
                if match:
                    print(f"    查找金额，关键词: '{keyword}'，文本: '{text_clean}'，匹配结果: {match.group(1)}")
                    amount = match.group(1).replace(',', '').replace('·', '.')  # 去除千分位逗号，将间隔点替换为小数点

                    # 更新最大金额
                    if float(amount) > amount_max:
                        amount_max = float(amount)
    return amount_max

def check_file_exists(output_path):
    """
    检查输出文件是否存在。
    如果存在，会在文件名后添加数字后缀，直到找到一个不存在的文件名。
    """
    if os.path.exists(output_path):
        base_name, ext = os.path.splitext(output_path)
        counter = 1
        while True:
            new_output_path = f"{base_name}_{counter}{ext}"
            if not os.path.exists(new_output_path):
                return new_output_path
            counter += 1
    return output_path

def merge_invoices_fitz(all_pdf_files, output_path, layout=DEFAULT_LAYOUT, align=DEFAULT_ALIGN,sum_amount=True):
    """
    使用PyMuPDF将所有PDF文件按照指定布局合并到页面上。
    
    参数:
    - all_pdf_files: PDF文件列表
    - output_path: 输出文件路径
    - layout: 布局类型，默认值为DEFAULT_LAYOUT
    - align: 对齐方式，默认值为DEFAULT_ALIGN
    - sum_amount: 是否计算总金额，默认值为True
    """

    if not all_pdf_files:
        print("未找到任何PDF文件。")
        return
    else:
        print(f"\n共 {len(all_pdf_files)} 个PDF文件，开始合并...")
        print(f"使用布局: {layout}, 对齐方式: {align}")
    
    # 创建一个新的PDF文档
    new_pdf = fitz.open()

    amount_sum = 0.0
    
    # 获取布局配置
    if layout not in LAYOUTS:
        print(f"警告：未知布局 '{layout}'，使用默认布局 {DEFAULT_LAYOUT}")
        layout = DEFAULT_LAYOUT
    
    layout_info = LAYOUTS[layout]
    page_width = layout_info.page_width
    page_height = layout_info.page_height
    cols = layout_info.cols
    rows = layout_info.rows
    items_per_page = layout_info.items_per_page
    orientation = layout_info.orientation
    
    margin = 2  # 页边距
    usable_width = page_width - 2 * margin  # 可用宽度
    usable_height = page_height - 2 * margin  # 可用高度
    sub_width = usable_width / cols  # 子页面宽度
    sub_height = usable_height / rows  # 子页面高度
    
    # 处理每个PDF文件
    for index, pdf_file in enumerate(all_pdf_files):
        position_in_page = index % items_per_page
        
        # 创建新页面
        if position_in_page == 0:
            page = new_pdf.new_page(width=page_width, height=page_height)
            
            # 画分割线
            # 绘制水平分割线
            for i in range(1, rows):
                y = margin + i * sub_height
                page.draw_line((margin, y), (margin + usable_width, y))
            
            # 绘制垂直分割线
            for i in range(1, cols):
                x = margin + i * sub_width
                page.draw_line((x, margin), (x, margin + usable_height))
        
        try:
            # 打开单个发票PDF
            single_pdf = fitz.open(pdf_file)
            
            # 获取第一页
            invoice_page = single_pdf[0]
            
            # 读取发票金额
            if sum_amount:
                amount = read_invoice_amount(invoice_page)
                if amount:
                    amount_sum += float(amount)
                print(f"  发票 {os.path.basename(pdf_file)} 金额: {amount}")

            # 获取页面的矩形
            src_rect = invoice_page.rect
            
            # 计算目标位置
            col = position_in_page % cols
            row = position_in_page // cols
            
            x = margin + col * sub_width
            y = margin + row * sub_height
            
            # 计算缩放比例
            scale_width = sub_width / src_rect.width
            scale_height = sub_height / src_rect.height
            scale = min(scale_width, scale_height) * 0.95  # 稍微缩小一点以留出边距
            
            # 创建目标矩形
            dest_width = src_rect.width * scale
            dest_height = src_rect.height * scale
            
            # 根据对齐方式计算x_offset
            if align == "left":
                x_offset = x
            elif align == "right":
                x_offset = x + (sub_width - dest_width)
            else:  # center
                x_offset = x + (sub_width - dest_width) / 2.0
            
            # 垂直方向始终居中
            y_offset = y + (sub_height - dest_height) / 2.0
            
            dest_rect = fitz.Rect(x_offset, y_offset, 
                                  x_offset + dest_width, 
                                  y_offset + dest_height)
            
            # 将发票页面插入到新页面
            page.show_pdf_page(dest_rect, single_pdf, 0)
            
            single_pdf.close()
            
            print(f"  已处理: {os.path.basename(pdf_file)} -> 第{index//items_per_page+1}页，位置{position_in_page+1}")
            
        except Exception as e:
            print(f"  处理文件 {pdf_file} 时出错: {e}")
    
    # 保存合并的PDF
    output_path = check_file_exists(output_path)
    new_pdf.save(output_path)
    new_pdf.close()
    
    print(f"\n处理完成！共合并了 {len(all_pdf_files)} 张发票。")
    print(f"输出文件已保存至: {output_path}")
    print(f"布局: {orientation} {cols}x{rows}")
    print(f"对齐方式: {align}")
    if sum_amount:
        print(f"总金额: {amount_sum:.2f}")
    return output_path

def log_help():
    print("使用方法:")
    print("当第一个或最后一个参数是*.pdf时，会作为输出文件名")
    print("python main.py [路径1] [路径2] ... [输出文件名.pdf]")
    print("当第一个参数是*.txt时，会读取txt文件中的参数，忽略后面的参数")
    print("python main.py [目录列表.txt]")
    print("默认输出文件名: out.pdf")
    print(f"默认布局: {LAYOUTS[DEFAULT_LAYOUT].get_description()}")
    print(f"默认对齐方式: {DEFAULT_ALIGN}")
    print("布局选项:")
    for layout_key, layout_info in LAYOUTS.items():
        print(f"  --layout={layout_key} ({layout_info.get_description()})")
    print("对齐选项:")
    print("  --align=left (左对齐)")
    print("  --align=right (右对齐)")
    print("  --align=center (居中对齐，默认)")
    print("-h: 查看目录列表格式")

def help_use_path_file():
    print("""
目录列表.txt 格式:
    每个目录占一行
    如果存在--layout=参数，会覆盖默认布局
    第一行或最后一行如果是*.pdf，会作为输出文件名
    示例:
./差旅补助
./出行住宿
--layout=2x4_v
--align=right
out1.pdf
""")

def parse_arguments(args):
    """
    解析命令行参数，返回源路径列表、输出文件名、布局类型和对齐方式
    """
    if not args:
        log_help()
        return None, None, None, None
    
    if args[0] == "-h":
        log_help()
        help_use_path_file()
        return None, None, None, None
    
    # 默认输出文件名、布局和对齐方式
    output_file = "out.pdf"
    layout = DEFAULT_LAYOUT  # 默认布局
    align = DEFAULT_ALIGN  # 默认对齐方式
    path_from_txt = False
    
    # 检查第一个参数是否是.txt文件
    if args and args[0].lower().endswith('.txt'):
        path_from_txt = True

    # 文件路径列表
    file_paths = []
    # 从txt文件读取路径
    if path_from_txt:
        try:
            with open(args[0], 'r', encoding='utf-8') as f:
                file_paths = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"读取文件 {args[0]} 时出错: {e}")
            return None, None, None
    else:
        file_paths = args


    # 检查是否有布局参数
    layout_args = [arg for arg in file_paths if arg.startswith("--layout=")]
    if layout_args:
        layout = layout_args[0].split("=")[1]
        file_paths = [arg for arg in file_paths if not arg.startswith("--layout=")]
        
        # 验证布局参数
        valid_layouts = LAYOUTS.keys()
        if layout not in valid_layouts:
            print(f"错误: 无效的布局参数 {layout}，有效选项: {', '.join(valid_layouts)}")
            return None, None, None, None
    
    # 检查是否有对齐参数
    align_args = [arg for arg in file_paths if arg.startswith("--align=")]
    if align_args:
        align = align_args[0].split("=")[1]
        file_paths = [arg for arg in file_paths if not arg.startswith("--align=")]
        
        # 验证对齐参数
        valid_aligns = ["left", "right", "center"]
        if align not in valid_aligns:
            print(f"错误: 无效的对齐参数 {align}，有效选项: {', '.join(valid_aligns)}")
            return None, None, None, None

    # 检查第一个和最后一个参数是否是.pdf文件
    if file_paths and file_paths[0].lower().endswith('.pdf'):
        output_file = file_paths[0]
        file_paths = file_paths[1:]  # 移除输出文件名
    elif file_paths and file_paths[-1].lower().endswith('.pdf'):
        output_file = file_paths[-1]
        file_paths = file_paths[:-1]  # 移除输出文件名

    # 收集所有源路径
    source_paths = []
    for file_path in file_paths:
        if os.path.isdir(file_path):
            source_paths.append(file_path)
    
    return source_paths, output_file, layout, align

def main():
    # 获取命令行参数
    args = sys.argv[1:]
    
    # 解析参数，获取源路径、输出文件名、布局和对齐方式
    source_paths, output_file, layout, align = parse_arguments(args)
    
    # 如果解析失败，直接返回
    if source_paths is None:
        return
    
    # 收集所有目录中的PDF文件
    all_pdf_files = get_file_from_folders(source_paths)
    
    # 如果没有找到PDF文件，直接返回
    if not all_pdf_files:
        return
    
    # 合并PDF文件
    merge_invoices_fitz(all_pdf_files, output_file, layout, align)
# 使用示例
if __name__ == "__main__":
    main()