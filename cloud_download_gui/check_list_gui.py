from ttkwidgets import CheckboxTreeview
import tkinter as tk
from SharedDirectory import SharedDirectory

def check_items_gui(SD:SharedDirectory):
    root = tk.Tk()

    def comfirm():
        checked_items = tree.get_all_checked()
        for iid in checked_items:
            SD.set_check(iid)
        root.destroy()

    tree = CheckboxTreeview(root)
    tree.pack()

    for parent, iid, tag in SD.get_all_nodes_info():
        tree.insert(parent, "end", iid, text=tag)

    tree.check_all()
    tree.item("/", open=True)

    check_all_b = tk.Button(root,text="全选",command=tree.check_all).pack()
    uncheck_all_b = tk.Button(root,text="全不选",command=tree.uncheck_all).pack()
    comfirm_b = tk.Button(root,text="确认",command=comfirm)
    comfirm_b.pack()

    root.mainloop()

if __name__ == '__main__':
    check_items_gui(None)