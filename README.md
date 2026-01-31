# Tsinghua Tools

清华大学相关工具集，解决校园网络服务使用中的痛点问题。

## 工具列表

### 云盘下载器 (cloud-downloader)

解决清华云盘（Seafile）分享链接无法批量下载大量文件/大文件夹的问题。

**功能特性**：
- 支持批量下载分享链接中的文件
- 支持大文件下载（流式传输，不占用大量内存）
- 支持断点续传
- 支持密码保护的分享链接
- 支持文件/文件夹选择性下载
- 实时下载进度显示

**下载安装**：
- 前往 [Releases](https://github.com/你的用户名/Tsinghua-Tools/releases) 页面下载
- **Mac 用户**：下载 `.dmg` 文件，双击打开后拖入"应用程序"
- **Windows 用户**：下载 `.msi` 或 `.exe` 安装包

**使用方法**：
1. 复制清华云盘分享链接（如 `https://cloud.tsinghua.edu.cn/d/xxxxxx/`）
2. 粘贴到应用中，点击"解析"
3. 选择需要下载的文件/文件夹
4. 选择本地保存目录
5. 点击"开始下载"

**技术栈**：Tauri 2 + React + TypeScript + Rust

---

### [归档] Python 版本 (cloud-downloader-legacy)

旧版 Python 命令行实现，不再维护。如需使用请参考 `cloud-downloader-legacy/` 目录。

---

## 开发

### 云盘下载器开发

```bash
cd cloud-downloader
npm install
npm run tauri:dev
```

### 构建

```bash
npm run tauri:build
```

产物位于 `cloud-downloader/src-tauri/target/release/bundle/`

---

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT](LICENSE)
