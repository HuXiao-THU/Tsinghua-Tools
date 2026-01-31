from tkinter import filedialog, Tk
from datetime import datetime

header = {
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
}

def printlog(s, pre='', end='\n'):
    output = pre + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " " + s
    print(output, end=end)

def to_percent(temp):
    return '%2.2f'%(100*temp) + '%'

def convertFileSize(size):
    # 定义单位列表
    units = 'Bytes', 'KB', 'MB', 'GB', 'TB'
    # 初始化单位为Bytes
    unit = units[0]
    # 循环判断文件大小是否大于1024，如果大于则转换为更大的单位
    for i in range(1, len(units)):
        if size >= 1024:
            size /= 1024
            unit = units[i]
        else:
            break
    # 格式化输出文件大小，保留两位小数
    return '{:.2f} {}'.format(size, unit)

def get_share_key(share_link):
    key = None
    pos = share_link.find("https://cloud.tsinghua.edu.cn/d/")
    if pos == -1:
        return key
    else:
        start_pos = pos + len("https://cloud.tsinghua.edu.cn/d/")
        end_pos = share_link.find("/", start_pos)
        key = share_link[start_pos:end_pos]
    return key

def getSaveDir():
    root = Tk()
    root.withdraw()
    save_dir = filedialog.askdirectory(title='选择保存文件夹', initialdir='./')
    root.destroy()
    return save_dir