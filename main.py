import os
import fitz  # PyMuPDF

def merge_invoices_fitz(source_folder, output_path):
    """
    使用PyMuPDF将指定文件夹内的所有PDF文件，每4张合并到一个横向的A4页面上。
    """
    
    # 收集所有PDF文件
    pdf_files = []
    for file in os.listdir(source_folder):
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(source_folder, file))
    
    if not pdf_files:
        print("警告：在指定文件夹中未找到PDF文件。")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件，开始处理...")
    
    # 创建一个新的PDF文档
    new_pdf = fitz.open()
    
    # A4横向尺寸（以点为单位）
    a4_width = 842  # 横向宽度
    a4_height = 595  # 横向高度
    
    margin = 40
    usable_width = a4_width - 2 * margin
    usable_height = a4_height - 2 * margin
    sub_width = usable_width / 2.0
    sub_height = usable_height / 2.0
    
    # 处理每个PDF文件
    for index, pdf_file in enumerate(pdf_files):
        position_in_page = index % 4
        
        # 创建新页面
        if position_in_page == 0:
            page = new_pdf.new_page(width=a4_width, height=a4_height)
        
        try:
            # 打开单个发票PDF
            single_pdf = fitz.open(pdf_file)
            
            # 获取第一页
            invoice_page = single_pdf[0]
            
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
    
    print(f"\n处理完成！共合并了 {len(pdf_files)} 张发票。")
    print(f"输出文件已保存至: {output_path}")

# 使用示例
if __name__ == "__main__":
    source_directory = "path"
    output_file = "out.pdf"
    
    merge_invoices_fitz(source_directory, output_file)