// 在 release 模式下隐藏 Windows 控制台窗口
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use cloud_download_tauri as core;

#[tauri::command]
async fn parse_share_key(share_link: String) -> Option<String> {
    core::parse_share_key(share_link).await
}

#[tauri::command]
async fn fetch_share_tree(
    share_key: String,
    password: Option<String>,
) -> Result<Vec<core::FileNode>, String> {
    core::fetch_share_tree(share_key, password).await
}

#[tauri::command]
async fn download_files(
    window: tauri::Window,
    share_key: String,
    items: Vec<core::DownloadItem>,
    password: Option<String>,
) -> Result<(), String> {
    core::download_files(window, share_key, items, password).await
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            parse_share_key,
            fetch_share_tree,
            download_files
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
