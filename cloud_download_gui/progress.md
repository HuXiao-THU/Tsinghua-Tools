# Progress

## Utility

* 下载方式
    * 预先载入所有待下载文件，包括文件大小...done!
    * 统一下载...done!
    * 显示全局进度...done!

* 找到下载为空文件的bug
    * 添加header
    * 每个文件下载完之后校验一下大小

* 解决加密目录的下载问题
* 多线程下载
* 大文件下载...done!

```Python
r = requests.get(image_url, stream=True)
with open("python.pdf", "wb") as f:
    for bl in r.iter_content(chunk_size=1048576):   # 1MB
        if bl:
            f.write(bl)
```

## GUI

* 做一个勾选框，实现选择性下载...done!
* 针对图片分享，做预览窗口

## 导出exe文件
`pyinstaller cloud_download.spec`