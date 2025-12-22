import os
import sys
import re
import fitz  # PyMuPDF

def get_file_from_folders(source_folders):
    """
    找到所有PDF文件
    """
    # 收集所有目录中的PDF文件
    pdf_files = []
    
    for source_folder in source_folders:
        if not os.path.exists(source_folder):
            print(f"警告：目录不存在: {source_folder}")
            continue
            
        print(f"扫描目录: {source_folder}")
        files_num = 0
        for file in os.listdir(source_folder):
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(source_folder, file))
                files_num += 1
                print(f"  找到文件: {file}")
        
        print(f"  目录 {source_folder} 共找到 {files_num} 个PDF文件")
    
    return pdf_files

# 读取发票金额
def read_invoice_amount(page):
    """
    从PDF文件中读取发票金额。
    核心思路：提取文本与坐标 -> 定位关键词 -> 匹配附近金额数字
    """
    amount = None

    # 提取带详细坐标信息的文本块
    # 使用 “dict” 或 “blocks” 格式以获得位置信息
    blocks = page.get_text("blocks")  # 每个block包含(x0, y0, x1, y1, "文本", ...)
    # 或使用：text_dict = page.get_text("dict")

    # 定义可能表示金额的关键词
    amount_keywords = ["价税合计", "合计", "金额", "¥", "￥", "小写"]

    # 可能存在多个金额，取最大的
    amount_max = None

    # 遍历文本块，寻找关键词及附近的金额
    for block in blocks:
        x0, y0, x1, y1, text, block_no, block_type = block
        text_clean = text.strip()

        # 检查当前文本块是否包含关键词
        for keyword in amount_keywords:
            if keyword in text_clean:
                # 策略A：关键词和金额在同一文本块内 (如“合计：¥128.50”)
                # 使用正则表达式直接在当前文本块中查找金额数字
                pattern = r'[¥￥]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'  # 匹配千分位和小数
                match = re.search(pattern, text_clean)
                if match:
                    amount = match.group(1).replace(',', '')  # 去除千分位逗号
                    
                    # 更新最大金额
                    if amount_max is None or float(amount) > float(amount_max):
                        amount_max = amount

    return amount_max  # 如果未找到，返回None

def merge_invoices_fitz(all_pdf_files, output_path):
    """
    使用PyMuPDF将所有PDF文件，每4张合并到一个横向的A4页面上。
    """

    if not all_pdf_files:
        print("未找到任何PDF文件。")
        return
    else:
        print(f"\n共 {len(all_pdf_files)} 个PDF文件，开始合并...")
    
    # 创建一个新的PDF文档
    new_pdf = fitz.open()

    amount_sum = 0.0
    
    # A4横向尺寸（以点为单位）
    a4_width = 842  # 横向宽度
    a4_height = 595  # 横向高度
    
    margin = 2 # 页边距
    usable_width = a4_width - 2 * margin # 可用宽度
    usable_height = a4_height - 2 * margin # 可用高度
    sub_width = usable_width / 2.0 # 子页面宽度
    sub_height = usable_height / 2.0 # 子页面高度
    
    # 处理每个PDF文件
    for index, pdf_file in enumerate(all_pdf_files):
        position_in_page = index % 4
        
        # 创建新页面
        if position_in_page == 0:
            page = new_pdf.new_page(width=a4_width, height=a4_height)
            # 画两条线四等分页面
            page.draw_line((margin, margin + sub_height), (margin + usable_width, margin + sub_height))
            page.draw_line((margin + sub_width, margin), (margin + sub_width, margin + usable_height))
        
        try:
            # 打开单个发票PDF
            single_pdf = fitz.open(pdf_file)
            
            
            # 获取第一页
            invoice_page = single_pdf[0]
            
            # 读取发票金额
            amount = read_invoice_amount(invoice_page)
            if amount:
                amount_sum += float(amount)

            print(f"  发票 {os.path.basename(pdf_file)} 金额: {amount}")

            # 获取页面的矩形
            src_rect = invoice_page.rect
            
            # 计算目标位置
            col = position_in_page % 2
            row = position_in_page // 2
            
            x = margin + col * sub_width
            y = margin + row * sub_height
            
            # 计算缩放比例
            scale_width = sub_width / src_rect.width
            scale_height = sub_height / src_rect.height
            scale = min(scale_width, scale_height) * 0.95
            
            # 创建目标矩形
            dest_width = src_rect.width * scale
            dest_height = src_rect.height * scale
            
            # 居中
            x_offset = x + (sub_width - dest_width) / 2.0
            y_offset = y + (sub_height - dest_height) / 2.0
            
            dest_rect = fitz.Rect(x_offset, y_offset, 
                                  x_offset + dest_width, 
                                  y_offset + dest_height)
            
            # 将发票页面插入到新页面
            page.show_pdf_page(dest_rect, single_pdf, 0)
            
            single_pdf.close()
            
            print(f"  已处理: {os.path.basename(pdf_file)} -> 第{index//4+1}页，位置{position_in_page+1}")
            
        except Exception as e:
            print(f"  处理文件 {pdf_file} 时出错: {e}")
    
    # 保存合并的PDF
    new_pdf.save(output_path)
    new_pdf.close()
    
    print(f"\n处理完成！共合并了 {len(all_pdf_files)} 张发票。")
    print(f"输出文件已保存至: {output_path}")
    print(f"总金额: {amount_sum:.2f}")

def log_help():
    print("使用方法: python main.py [路径1] [路径2] ... [输出文件名.pdf]")
    print("或者: python main.py [目录列表.txt]")
    print("默认输出文件名: out.pdf")
    print("-h: 查看目录列表格式")

def help_use_path_file():
    print("*.txt 格式:")
    print("每个目录占一行")
    print("第一行或最后一行如果是*.pdf，会作为输出文件名")
    print("示例:")
    print("./差旅补助")
    print("./出行住宿")
    print("out1.pdf")

def main():
    # 获取命令行参数
    args = sys.argv[1:]
    
    if not args:
        log_help()
        return
    
    if args[0] == "-h":
        help_use_path_file()
        return
    
    # 默认输出文件名
    output_file = "out.pdf"
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
            return
    else:
        file_paths = args

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
    
    # 收集所有目录中的PDF文件
    all_pdf_files = get_file_from_folders(source_paths)
    merge_invoices_fitz(all_pdf_files, output_file)
# 使用示例
if __name__ == "__main__":
    # test_main()
    main()