import os
from requests import get
from urllib import parse
from treelib import Tree
from queue import Queue
from util import *

DIRECTORY = 0
FILE = 1
test_key = 'a50b389352f0408b9c1b'
download_url = 'https://cloud.tsinghua.edu.cn/d/{}/files/?p={}&dl=1'

class SharedDirectory():
    def __init__(self, share_key):
        self.tree = Tree()
        self.process_queue = Queue()
        self.share_key = share_key
        self.total_file = 0
        self.total_size = 0

        self.tree.create_node(tag='/', identifier='/', parent=None, data={'is_dir':True, 'size':0, 'checked': True})
        # tag 为文件名或目录名(obj_name)
        # ID 为文件或目录的路径(path)
        # data 中包含其是否为目录，文件的size（单位为字节，目录的size为0）

    def get_dir(self, path='/'):
        # the path here is also the parent node ID
        r = get('https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{}/dirents/?path={}'.format(self.share_key, parse.quote(path)))
        obj_list = r.json()['dirent_list']
        self.process_queue.put(('/', obj_list))

        while not self.process_queue.empty():
            parent_node, obj_list = self.process_queue.get()
            for obj in obj_list:
                # 如果是子目录，加入目录节点并获取子目录后加入队列
                if obj['is_dir']:
                    current_path = obj['folder_path']
                    self.tree.create_node(tag=obj['folder_name'], identifier=current_path, parent=parent_node, data={'is_dir':True, 'size':0, 'checked':False})
                    r = get('https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{}/dirents/?path={}'.format(self.share_key, parse.quote(current_path)))
                    self.process_queue.put((current_path, r.json()['dirent_list']))
                # 如果是文件，加入文件节点
                else:
                    self.tree.create_node(tag=obj['file_name'], identifier=obj['file_path'], parent=parent_node, data={'is_dir':False, 'size':obj['size'], 'checked':False})

    def get_total_info(self):
        for node_id in self.tree.expand_tree():
            self.total_size += self.tree[node_id].data['size']
            if not self.tree[node_id].data['is_dir']:
                self.total_file += 1
        return self.total_size, self.total_file
    
    def get_checked_info(self):
        self.total_file = 0
        self.total_size = 0
        for node_id in self.tree.expand_tree():
            # if node_id == '/':  # python 3.11 新版本好像把根目录也会遍历到了
            #     continue

            assert 'checked' in self.tree[node_id].data.keys(), node_id
            if self.tree[node_id].data['checked']:
                self.total_size += self.tree[node_id].data['size']
                if not self.tree[node_id].data['is_dir']:
                    self.total_file += 1
        return self.total_size, self.total_file
    
    def download(self, save_dir):
        if self.total_file == 0:
            print("")
            printlog("该目录中没有文件")
            return False
        downloaded_file = 0
        downloaded_size = 0
        
        for node_id in self.tree.expand_tree():
            # print(node_id, self.tree[node_id].data)
            # 如果没有选中该节点，直接跳过
            if not self.tree[node_id].data['checked']:
                continue
            # 如果是目录，就建立对应的目录
            if self.tree[node_id].data['is_dir']:
                new_dir = os.path.join(save_dir, self.tree[node_id].identifier[1:]).replace('\\', '/')
                if not os.path.exists(new_dir):
                    os.mkdir(new_dir)
                    printlog("创建目录：{:s}".format(new_dir)+' '*50)
                    printlog("下载进度：总共{:d}个文件，目前第{:d}个 {:s}/{:s}已下载".format(self.total_file, downloaded_file, convertFileSize(downloaded_size), convertFileSize(self.total_size)), end='\r')
            # 如果是文件，就下载到对应的位置
            else:
                success = True
                save_file = os.path.join(save_dir, self.tree[node_id].identifier[1:]).replace('\\', '/')
                file_url = download_url.format(self.share_key, parse.quote(self.tree[node_id].identifier))

                try:
                    r = get(file_url, headers='', stream=True)
                    with open(save_file, 'wb') as f:
                        # f.write(r.content)
                        for bl in r.iter_content(chunk_size=1048576):   # 1MB
                            if bl:
                                f.write(bl)

                except Exception as e:
                    success = False
                    printlog('文件 {} 下载失败, {}'.format(self.tree[node_id].identifier, str(e))+' '*50)
                    printlog("下载进度：总共{:d}个文件，目前第{:d}个 {:s}/{:s}已下载".format(self.total_file, downloaded_file, convertFileSize(downloaded_size), convertFileSize(self.total_size)), end='\r')
                if success:
                    downloaded_size += self.tree[node_id].data['size']
                    downloaded_file += 1
                    printlog('{} 下载成功'.format(self.tree[node_id].identifier)+' '*50)
                    printlog("下载进度：总共{:d}个文件，目前第{:d}个 {:s}/{:s}已下载".format(self.total_file, downloaded_file, convertFileSize(downloaded_size), convertFileSize(self.total_size)), end='\r')

        print("\n下载结束")
        if downloaded_file == self.total_file:
            return True
        else:
            return False
    
    def get_all_nodes_info(self):
        info = []   #(parent, iid, text)
        for node_id in self.tree.expand_tree():
            if node_id == '/':
                parent = ""
            else:
                parent = self.tree.parent(node_id).identifier
            iid = self.tree[node_id].identifier
            text = self.tree[node_id].tag
            info.append((parent, iid, text))
        return info

    def set_check(self, node_id):
        self.tree[node_id].data['checked'] = True

if __name__ == '__main__':
    SD = SharedDirectory()
    SD.get_dir(test_key)
    SD.tree.show()
    total_size, total_file = SD.get_total_info()
    print("total file: ", total_file)
    print(convertFileSize(total_size))