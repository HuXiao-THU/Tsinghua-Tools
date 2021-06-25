import requests
import os

def download_image(pic_url, pic_path):
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    }
    try:
        try:
            img = requests.get(pic_url, headers=headers, timeout=10)
            if img.encoding == 'utf-8':
                # no such file!
                return False
            with open(pic_path, 'ab') as f:
                f.write(img.content)
        except Exception as e:
            # print('this url not exists!')
            return False
        # print (pic_path + "保存完成")
        return True
    except Exception as e:
        # print(e)
        # print("保存图片失败: " + pic_url)
        return False

if __name__ == "__main__":
    if not os.path.exists('./photos/'):
        os.mkdir('./photos/')
    # print('文件路径：' + pic_path + ' 图片地址：' + pic_url)
    for i in range(650):
        url = ''
        path = './photos/{:d}.jpg'.format(i)
        succ = download_image(url, path)
        if succ:
            print("photo {:d} saved.\ttotal process:\t{:.2f}%".format(i, i/636*100))