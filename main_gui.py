import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import threading
import fitz  # PyMuPDF
from main import (
    read_invoice_amount,
    merge_invoices_fitz,
)

class InvoiceMergeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF发票合并工具")
        self.root.geometry("1000x600")
        
        # 文件列表数据
        self.file_data = []
        
        # 创建界面
        self.create_widgets()
        
        # 绑定事件
        self.bind_events()
        
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 添加按钮
        ttk.Button(button_frame, text="添加文件", command=self.add_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="删除", command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="清空", command=self.clear_all).pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 合并按钮
        ttk.Button(button_frame, text="合并选中", command=self.merge_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="合并全部", command=self.merge_all).pack(side=tk.LEFT, padx=(0, 5))
        
        # 分隔符
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 金额统计按钮
        ttk.Button(button_frame, text="金额统计", command=self.calculate_amounts).pack(side=tk.LEFT, padx=(0, 5))
        
        # 创建文件列表框架
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("文件名", "金额", "路径", "修改日期", "大小")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")
        
        # 设置列标题
        self.tree.heading("#0", text="序号")
        self.tree.column("#0", width=50)
        
        for col in columns:
            self.tree.heading(col, text=col)
            if col == "路径":
                self.tree.column(col, width=300)
            elif col == "文件名":
                self.tree.column(col, width=200)
            else:
                self.tree.column(col, width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 文件数量标签
        self.count_label = ttk.Label(status_frame, text="文件数量: 0")
        self.count_label.pack(side=tk.LEFT)
        
        # 金额统计标签
        self.amount_label = ttk.Label(status_frame, text="金额统计: 0.00")
        self.amount_label.pack(side=tk.LEFT, padx=(20, 0))
        
    def bind_events(self):
        # 绑定双击事件 - 打开文件所在目录
        self.tree.bind("<Double-1>", self.open_file_location)
        
        # 绑定右键菜单
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="打开文件所在目录", command=self.open_file_location)
        self.context_menu.add_command(label="复制文件路径", command=self.copy_file_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="删除", command=self.delete_selected)
        
    def add_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        for file_path in file_paths:
            self.add_file_to_list(file_path)
    
    def add_file_to_list(self, file_path):
        if not os.path.exists(file_path):
            return
            
        # 检查是否已存在
        for item in self.file_data:
            if item["path"] == file_path:
                return
        
        # 获取文件信息
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M")
        
        # 添加到数据列表
        file_info = {
            "name": file_name,
            "amount": "",
            "path": file_path,
            "mod_time": mod_time,
            "size": self.format_file_size(file_size)
        }
        self.file_data.append(file_info)
        
        # 添加到Treeview
        item_id = self.tree.insert("", "end", text=str(len(self.file_data)))
        self.tree.set(item_id, "文件名", file_name)
        self.tree.set(item_id, "金额", "")
        self.tree.set(item_id, "路径", file_path)
        self.tree.set(item_id, "修改日期", mod_time)
        self.tree.set(item_id, "大小", self.format_file_size(file_size))
        
        # 更新状态
        self.update_status()
    
    def format_file_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        for item in selected_items:
            # 获取序号
            item_text = self.tree.item(item, "text")
            index = int(item_text) - 1
            
            # 从数据列表中删除
            if 0 <= index < len(self.file_data):
                del self.file_data[index]
            
            # 从Treeview中删除
            self.tree.delete(item)
        
        # 重新编号
        self.renumber_items()
        
        # 更新状态
        self.update_status()
    
    def clear_all(self):
        if not self.file_data:
            return
            
        if messagebox.askyesno("确认", "确定要清空所有文件吗？"):
            self.file_data.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 更新状态
            self.update_status()
    
    def renumber_items(self):
        for i, item in enumerate(self.tree.get_children()):
            self.tree.item(item, text=str(i + 1))
    
    def update_status(self):
        # 更新文件数量
        self.count_label.config(text=f"文件数量: {len(self.file_data)}")
        
        # 计算总金额
        total_amount = 0.0
        for item in self.file_data:
            if item["amount"]:
                try:
                    total_amount += float(item["amount"])
                except ValueError:
                    pass
        
        self.amount_label.config(text=f"金额统计: {total_amount:.2f}")
    
    def open_file_location(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        item_text = self.tree.item(item, "text")
        index = int(item_text) - 1
        
        if 0 <= index < len(self.file_data):
            file_path = self.file_data[index]["path"]
            folder_path = os.path.dirname(file_path)
            
            # 打开文件所在目录
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                os.system(f"open '{folder_path}'")
            else:
                os.system(f"xdg-open '{folder_path}'")
    
    def copy_file_path(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        item_text = self.tree.item(item, "text")
        index = int(item_text) - 1
        
        if 0 <= index < len(self.file_data):
            file_path = self.file_data[index]["path"]
            
            # 复制到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(file_path)
    
    def show_context_menu(self, event):
        # 选中右键点击的项目
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def calculate_amounts(self):
        if not self.file_data:
            messagebox.showinfo("提示", "请先添加PDF文件")
            return
        
        # 在新线程中计算金额，避免界面卡顿
        threading.Thread(target=self._calculate_amounts_thread, daemon=True).start()
    
    def _calculate_amounts_thread(self):
        total_amount = 0.0
        
        for i, file_info in enumerate(self.file_data):
            try:
                # 从PDF中提取金额
                amount = self.extract_amount_from_pdf(file_info["path"])
                file_info["amount"] = amount
                
                if amount:
                    try:
                        total_amount += float(amount)
                    except ValueError:
                        pass
                
                # 更新Treeview中的金额
                self.root.after(0, self._update_item_amount, i, amount)
                
            except Exception as e:
                print(f"处理文件 {file_info['name']} 时出错: {e}")
        
        # 更新总金额
        self.root.after(0, self._update_total_amount, total_amount)
    
    def _update_item_amount(self, index, amount):
        items = self.tree.get_children()
        if index < len(items):
            item = items[index]
            self.tree.set(item, "金额", amount)
    
    def _update_total_amount(self, total_amount):
        self.amount_label.config(text=f"金额统计: {total_amount:.2f}")
        messagebox.showinfo("金额统计", f"金额统计完成\n总金额: {total_amount:.2f}")
    
    def extract_amount_from_pdf(self, pdf_path):
        """从PDF中提取金额信息"""
        try:
            doc = fitz.open(pdf_path)
            amount = ""
            
            # 使用main.py中的read_invoice_amount函数
            for page in doc:
                amount = read_invoice_amount(page)
                if amount:
                    break
            
            doc.close()
            return amount or ""
        except Exception as e:
            print(f"提取金额时出错: {e}")
            return ""
    
    def merge_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要合并的文件")
            return
        
        # 获取选中的文件路径
        file_paths = []
        for item in selected_items:
            item_text = self.tree.item(item, "text")
            index = int(item_text) - 1
            
            if 0 <= index < len(self.file_data):
                file_paths.append(self.file_data[index]["path"])
        
        # 选择输出路径
        output_path = filedialog.asksaveasfilename(
            title="保存合并后的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if output_path:
            # 在新线程中合并，避免界面卡顿
            threading.Thread(target=self._merge_invoices_thread, args=(file_paths, output_path), daemon=True).start()
    
    def merge_all(self):
        if not self.file_data:
            messagebox.showwarning("警告", "请先添加要合并的文件")
            return
        
        # 获取所有文件路径
        file_paths = [item["path"] for item in self.file_data]
        
        # 选择输出路径
        output_path = filedialog.asksaveasfilename(
            title="保存合并后的PDF",
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if output_path:
            # 在新线程中合并，避免界面卡顿
            threading.Thread(target=self._merge_invoices_thread, args=(file_paths, output_path), daemon=True).start()
    
    def _merge_invoices_thread(self, pdf_files, output_path):
        """在线程中执行PDF合并，避免界面卡顿"""
        try:
            self.root.after(0, lambda: messagebox.showinfo("提示", "开始合并PDF文件，请稍候..."))
            
            # 调用main.py中的合并函数
            merge_invoices_fitz(pdf_files, output_path)
            
            self.root.after(0, lambda: messagebox.showinfo("完成", f"PDF合并完成！\n保存路径: {output_path}"))
            
            # 询问是否打开文件所在目录
            if messagebox.askyesno("打开目录", "是否打开文件所在目录？"):
                folder_path = os.path.dirname(output_path)
                if sys.platform == "win32":
                    os.startfile(folder_path)
                elif sys.platform == "darwin":
                    os.system(f"open '{folder_path}'")
                else:
                    os.system(f"xdg-open '{folder_path}'")
                    
        except Exception:
            self.root.after(0, lambda e=Exception: messagebox.showerror("错误", f"合并PDF时出错: {str(e)}"))
    
def main():
    root = tk.Tk()
    InvoiceMergeGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()