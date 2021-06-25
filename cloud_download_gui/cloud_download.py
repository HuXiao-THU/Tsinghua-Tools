import os
import requests
import tkinter as tk
from tkinter import filedialog

download_url = 'https://cloud.tsinghua.edu.cn/d/{}/files/?p={}&dl=1'

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

def download(save_dir, cloud_share_key, path='/'):
    r = requests.get('https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{}/dirents/?path={}'.format(cloud_share_key, path))
    if r.status_code == 404:
        print("内容不存在，T^T，看看是不是链接输错了？")
        return
    obj_list = r.json()['dirent_list']
    for obj in obj_list:
        if obj['is_dir']:
            new_save_dir = os.path.join(save_dir, obj['folder_path'][1:]).replace('\\', '/')
            if not os.path.exists(new_save_dir):
                os.mkdir(new_save_dir)
            print(new_save_dir + ' created.')
            download(save_dir, cloud_share_key, obj['folder_path'])
        else:
            file_url = download_url.format(cloud_share_key, obj['file_path'])
            success = True
            try:
                r = requests.get(file_url)
                save_file = os.path.join(save_dir, obj['file_path'][1:]).replace('\\', '/')
                with open(save_file, 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                success = False
                print('download for {} failed, {}'.format(obj['file_path'], str(e)))
            if success:
                print('{} downloaded.'.format(obj['file_path']))


def getSharedContent():
    pass

def getSaveDir():
    root = tk.Tk()
    root.withdraw()
    save_dir = filedialog.askdirectory(title='选择保存文件夹', initialdir='./')
    root.destroy()
    return save_dir

def main():
    while True:
        share_link = input("请粘贴分享下载链接：")
        cloud_share_key = get_share_key(share_link)
        if cloud_share_key != None:
            # TODO: 测试下载链接
            save_dir = getSaveDir()
            print("保存在{}，开始下载...".format(save_dir))
            download(save_dir, cloud_share_key, path='/')
            print("下载完毕！ヽ( ･∀･)ﾉ  ")
            input("按回车下载新的链接...")
        else:
            print("分享链接格式不正确，请重试！")
            continue


if __name__ == '__main__':
    main()