from util import *
from SharedDirectory import *
from check_list_gui import *

def download(tree):
    pass

def main():
    print("注意：使用时请关闭代理！！！！！！")
    while True:
        share_link = input("请粘贴分享下载链接：")
        share_key = get_share_key(share_link)
        if share_key != None:
            SD = SharedDirectory(share_key)
            printlog("开始解析分享下载链接......")
            # TODO: 测试测试是否成功
            SD.get_dir()

            printlog("下载内容目录结构如下：")
            SD.tree.show()
            total_size, total_file = SD.get_total_info()
            printlog("总共包含{:d}个文件，总大小为{:s}".format(total_file, convertFileSize(total_size)))
            if total_file == 0:
                printlog("该分享链接中没有文件！下载取消！")
                continue

            print("请选择需要下载的文件......")
            check_items_gui(SD)
            total_size, total_file = SD.get_checked_info()
            printlog("总共选择了{:d}个文件，总大小为{:s}".format(total_file, convertFileSize(total_size)))

            print("请选择下载位置......")
            save_dir = getSaveDir()
            print("保存在{}，开始下载...".format(save_dir))

            success = SD.download(save_dir)

            if success:
                print("")
                printlog("所有文件下载完毕！ヽ( ･∀･)ﾉ  ")
            input("按回车下载新的链接...")

        else:
            print("分享链接格式不正确，请重试！")
            continue

        

if __name__ == '__main__':
    main()