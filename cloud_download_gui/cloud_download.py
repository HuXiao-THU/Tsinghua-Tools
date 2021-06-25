import os
import requests

cloud_share_key = '5a288xxxxxxxxxe3b0dd'
download_url = 'https://cloud.tsinghua.edu.cn/d/{}/files/?p={}&dl=1'

if not os.path.exists('./{}/'.format(cloud_share_key)):
    os.mkdir('./{}/'.format(cloud_share_key))


def downloadFile(path):
    obj_list = requests.get(
        'https://cloud.tsinghua.edu.cn/api/v2.1/share-links/{}/dirents/?path={}'.format(cloud_share_key, path)).json()[
        'dirent_list']
    for obj in obj_list:
        if obj['is_dir']:
            new_local_path = ('./{}'.format(cloud_share_key)) + obj['folder_path']
            if not os.path.exists(new_local_path):
                os.mkdir(new_local_path)
            print(new_local_path + ' created.')
            downloadFile(obj['folder_path'])
        else:
            file_url = download_url.format(cloud_share_key, obj['file_path'])
            try:
                r = requests.get(file_url)
                with open('./{}/{}'.format(cloud_share_key, obj['file_path']), 'ab') as f:
                    f.write(r.content)
            except Exception as e:
                print('download for {} failed, {}'.format(obj['file_path'], str(e)))
            print('{} downloaded.'.format(obj['file_path']))


if __name__ == '__main__':
    downloadFile('/')
    print('download task completed.')
