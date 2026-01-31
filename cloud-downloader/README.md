# 清华云盘下载器

解决清华云盘（Seafile）分享链接无法批量下载大量文件/大文件夹的问题。

## 功能

- 批量下载分享链接中的文件
- 大文件流式下载（不占用大量内存）
- 断点续传
- 密码保护链接支持
- 文件/文件夹选择性下载
- 实时进度显示

## 开发

```bash
npm install
npm run tauri:dev
```

## 构建

```bash
npm run tauri:build
```

产物位于 `src-tauri/target/release/bundle/`

## 技术栈

- 前端：React + TypeScript
- 桌面框架：Tauri 2
- 后端：Rust
