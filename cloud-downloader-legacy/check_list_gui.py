from ttkwidgets import CheckboxTreeview
from tkinter import Tk, Frame, Scrollbar, Button, RIGHT, HORIZONTAL, CENTER, BOTTOM, X, Y
from SharedDirectory import SharedDirectory

class _CheckboxTreeview(CheckboxTreeview):  # python 3.11 原先get_all_checked方法没了
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
    
    def get_all_checked(self):
        """Return the list of checked items."""
        checked = []

        def get_all_checked_children(item):
            if not self.tag_has("unchecked", item):
                checked.append(item)
                ch = self.get_children(item)
                for c in ch:
                    get_all_checked_children(c)

        ch = self.get_children("")
        for c in ch:
            get_all_checked_children(c)
        return checked

def check_items_gui(SD:SharedDirectory):
    root = Tk()
    cl = Frame(root)

    def comfirm():
        checked_items = tree.get_all_checked()  # python 3.11 原先get_all_checked方法没了
        for iid in checked_items:
            SD.set_check(iid)
        root.destroy()

    tree = _CheckboxTreeview(cl)
    tree.column('#0', width = 800, anchor = CENTER)

    yscrollbar = Scrollbar(cl)
    yscrollbar.pack(side=RIGHT,fill=Y)
    xscrollbar = Scrollbar(cl, orient=HORIZONTAL)
    xscrollbar.pack(side=BOTTOM,fill=X)
    tree.pack()
    cl.pack()

    yscrollbar.config(command=tree.yview)
    xscrollbar.config(command=tree.xview)
    tree.configure(yscrollcommand=yscrollbar.set)
    tree.configure(xscrollcommand=xscrollbar.set)

    for parent, iid, tag in SD.get_all_nodes_info():
        tree.insert(parent, "end", iid, text=tag)

    tree.check_all()
    tree.item("/", open=True)

    check_all_b = Button(root,text="全选",command=tree.check_all).pack()
    uncheck_all_b = Button(root,text="全不选",command=tree.uncheck_all).pack()
    comfirm_b = Button(root,text="确认",command=comfirm)
    comfirm_b.pack()

    root.mainloop()

if __name__ == '__main__':
    check_items_gui(None)