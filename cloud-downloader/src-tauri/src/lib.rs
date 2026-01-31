use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::path::PathBuf;
use tokio::fs::OpenOptions;
use tauri::Emitter;
use tokio::io::AsyncWriteExt;

const BASE_URL: &str = "https://cloud.tsinghua.edu.cn";
const USER_AGENT: &str =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36";

#[derive(Debug, Deserialize)]
struct DirentResponse {
    #[serde(default)]
    dirent_list: Vec<DirentItem>,
}

#[derive(Debug, Deserialize)]
struct DirentItem {
    #[serde(default)]
    is_dir: bool,
    #[serde(default)]
    folder_path: String,
    #[serde(default)]
    folder_name: String,
    #[serde(default)]
    file_path: String,
    #[serde(default)]
    file_name: String,
    #[serde(default)]
    size: u64,
}

#[derive(Debug, Serialize, Clone)]
pub struct FileNode {
    pub id: String,
    pub name: String,
    pub parent: Option<String>,
    pub is_dir: bool,
    pub size: u64,
}

#[derive(Debug, Deserialize)]
pub struct DownloadItem {
    pub file_path: String,
    pub save_path: String,
}

#[derive(Debug, Serialize, Clone)]
pub struct DownloadProgress {
    pub file_path: String,
    pub downloaded: u64,
    pub total: Option<u64>,
    pub status: String,
    pub error: Option<String>,
}

pub async fn parse_share_key(share_link: String) -> Option<String> {
    let marker = format!("{}/d/", BASE_URL);
    let pos = share_link.find(&marker)?;
    let start = pos + marker.len();
    let end = share_link[start..].find('/').map(|i| start + i)?;
    Some(share_link[start..end].to_string())
}

pub async fn fetch_share_tree(
    share_key: String,
    password: Option<String>,
) -> Result<Vec<FileNode>, String> {
    let client = build_client()?;

    // 先检查是否需要密码
    let needs_password = check_needs_password(&client, &share_key).await?;
    if needs_password && password.is_none() {
        return Err("PASSWORD_REQUIRED".to_string());
    }
    if let Some(pwd) = password.as_deref() {
        verify_share_password(&client, &share_key, pwd).await?;
    }

    let mut nodes = Vec::<FileNode>::new();
    nodes.push(FileNode {
        id: "/".to_string(),
        name: "/".to_string(),
        parent: None,
        is_dir: true,
        size: 0,
    });

    let mut queue = VecDeque::new();
    queue.push_back("/".to_string());

    while let Some(path) = queue.pop_front() {
        let dirents = list_dirents(&client, &share_key, &path, password.as_deref()).await?;
        for item in dirents {
            if item.is_dir {
                let id = item.folder_path.clone();
                nodes.push(FileNode {
                    id: id.clone(),
                    name: item.folder_name.clone(),
                    parent: Some(path.clone()),
                    is_dir: true,
                    size: 0,
                });
                queue.push_back(id);
            } else {
                nodes.push(FileNode {
                    id: item.file_path.clone(),
                    name: item.file_name.clone(),
                    parent: Some(path.clone()),
                    is_dir: false,
                    size: item.size,
                });
            }
        }
    }

    Ok(nodes)
}

pub async fn download_files(
    window: tauri::Window,
    share_key: String,
    items: Vec<DownloadItem>,
    password: Option<String>,
) -> Result<(), String> {
    let client = build_client()?;
    if let Some(pwd) = password.as_deref() {
        verify_share_password(&client, &share_key, pwd).await?;
    }
    let mut errors: Vec<String> = Vec::new();
    for item in items {
        let result =
            download_with_retry(&client, &window, &share_key, &item, password.as_deref(), 3)
                .await;
        if let Err(err) = result {
            errors.push(err);
        }
    }
    if errors.is_empty() {
        Ok(())
    } else {
        Err(format!("部分文件下载失败: {}", errors.join("; ")))
    }
}

async fn list_dirents(
    client: &reqwest::Client,
    share_key: &str,
    path: &str,
    password: Option<&str>,
) -> Result<Vec<DirentItem>, String> {
    let encoded = urlencoding::encode(path);
    let url = format!(
        "{}/api/v2.1/share-links/{}/dirents/?path={}",
        BASE_URL, share_key, encoded
    );
    let mut request = client.get(url).header(reqwest::header::USER_AGENT, USER_AGENT);
    if let Some(pwd) = password {
        request = request
            .header("X-Seafile-Password", pwd)
            .query(&[("password", pwd)]);
    }
    let resp = request
        .send()
        .await
        .map_err(|e| format!("请求目录失败: {}", e))?;
    let status = resp.status();
    if !status.is_success() {
        let body = resp.text().await.unwrap_or_default();
        if let Some(code) = parse_password_error(status, &body, password.is_some()) {
            return Err(code.to_string());
        }
        return Err(format!("请求目录失败: HTTP {}", status));
    }
    let data = resp
        .json::<DirentResponse>()
        .await
        .map_err(|e| format!("解析目录失败: {}", e))?;
    Ok(data.dirent_list)
}

async fn download_with_retry(
    client: &reqwest::Client,
    window: &tauri::Window,
    share_key: &str,
    item: &DownloadItem,
    password: Option<&str>,
    max_retry: usize,
) -> Result<(), String> {
    let mut attempt = 0;
    loop {
        attempt += 1;
        let result = download_single(client, window, share_key, item, password).await;
        match result {
            Ok(()) => return Ok(()),
            Err(err) => {
                if err == "PASSWORD_REQUIRED" || err == "PASSWORD_INVALID" {
                    return Err(err);
                }
                let _ = window.emit(
                    "download-progress",
                    DownloadProgress {
                        file_path: item.file_path.clone(),
                        downloaded: 0,
                        total: None,
                        status: "retrying".to_string(),
                        error: Some(err.clone()),
                    },
                );
                if attempt >= max_retry {
                    return Err(format!("{} (已重试{}次)", err, max_retry));
                }
                tokio::time::sleep(std::time::Duration::from_millis(
                    500 * attempt as u64,
                ))
                .await;
            }
        }
    }
}

async fn download_single(
    client: &reqwest::Client,
    window: &tauri::Window,
    share_key: &str,
    item: &DownloadItem,
    password: Option<&str>,
) -> Result<(), String> {
    let encoded = urlencoding::encode(&item.file_path);
    let url = format!(
        "{}/d/{}/files/?p={}&dl=1",
        BASE_URL, share_key, encoded
    );

    let save_path = PathBuf::from(&item.save_path);
    if let Some(parent) = save_path.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| format!("创建目录失败: {}", e))?;
    }

    let mut start = 0u64;
    if let Ok(meta) = tokio::fs::metadata(&save_path).await {
        start = meta.len();
    }

    let mut request = client.get(&url).header(reqwest::header::USER_AGENT, USER_AGENT);
    if start > 0 {
        request = request.header(reqwest::header::RANGE, format!("bytes={}-", start));
    }
    if let Some(pwd) = password {
        request = request
            .header("X-Seafile-Password", pwd)
            .query(&[("password", pwd)]);
    }

    let resp = request
        .send()
        .await
        .map_err(|e| format!("下载失败: {}", e))?;
    let mut status = resp.status();
    if !status.is_success()
        && status != reqwest::StatusCode::PARTIAL_CONTENT
        && status != reqwest::StatusCode::RANGE_NOT_SATISFIABLE
    {
        let body = resp.text().await.unwrap_or_default();
        if let Some(code) = parse_password_error(status, &body, password.is_some()) {
            return Err(code.to_string());
        }
        return Err(format!("下载失败: HTTP {}", status));
    }
    if status == reqwest::StatusCode::RANGE_NOT_SATISFIABLE && start > 0 {
        // 本地已有文件不匹配，清理后重新下载
        let _ = tokio::fs::remove_file(&save_path).await;
        start = 0;
        let mut retry_request = client
            .get(&url)
            .header(reqwest::header::USER_AGENT, USER_AGENT);
        if let Some(pwd) = password {
            retry_request = retry_request
                .header("X-Seafile-Password", pwd)
                .query(&[("password", pwd)]);
        }
        let resp_retry = retry_request
            .send()
            .await
            .map_err(|e| format!("下载失败: {}", e))?;
        status = resp_retry.status();
        if !status.is_success() && status != reqwest::StatusCode::PARTIAL_CONTENT {
            let body = resp_retry.text().await.unwrap_or_default();
            if let Some(code) = parse_password_error(status, &body, password.is_some()) {
                return Err(code.to_string());
            }
            return Err(format!("下载失败: HTTP {}", status));
        }
        return download_stream(resp_retry, status, save_path, window, item, start).await;
    }
    if !status.is_success() && status != reqwest::StatusCode::PARTIAL_CONTENT {
        return Err(format!("下载失败: HTTP {}", status));
    }

    download_stream(resp, status, save_path, window, item, start).await
}

async fn download_stream(
    resp: reqwest::Response,
    status: reqwest::StatusCode,
    save_path: PathBuf,
    window: &tauri::Window,
    item: &DownloadItem,
    mut start: u64,
) -> Result<(), String> {
    let mut total = resp.content_length();
    let mut stream = resp.bytes_stream();

    if start > 0 && status == reqwest::StatusCode::PARTIAL_CONTENT {
        total = total.map(|len| len + start);
    } else {
        start = 0;
    }

    let mut file = if start > 0 {
        OpenOptions::new()
            .create(true)
            .append(true)
            .open(&save_path)
            .await
            .map_err(|e| format!("打开文件失败: {}", e))?
    } else {
        tokio::fs::File::create(&save_path)
            .await
            .map_err(|e| format!("创建文件失败: {}", e))?
    };

    let mut downloaded: u64 = start;
    while let Some(chunk) = stream.next().await {
        let chunk = chunk.map_err(|e| format!("下载流失败: {}", e))?;
        file.write_all(&chunk)
            .await
            .map_err(|e| format!("写入失败: {}", e))?;
        downloaded += chunk.len() as u64;
        let _ = window.emit(
            "download-progress",
            DownloadProgress {
                file_path: item.file_path.clone(),
                downloaded,
                total,
                status: "downloading".to_string(),
                error: None,
            },
        );
    }

    let _ = window.emit(
        "download-progress",
        DownloadProgress {
            file_path: item.file_path.clone(),
            downloaded,
            total,
            status: "done".to_string(),
            error: None,
        },
    );

    Ok(())
}

fn parse_password_error(
    status: reqwest::StatusCode,
    body: &str,
    had_password: bool,
) -> Option<&'static str> {
    if status != reqwest::StatusCode::UNAUTHORIZED
        && status != reqwest::StatusCode::FORBIDDEN
        && status != reqwest::StatusCode::BAD_REQUEST
    {
        return None;
    }
    let trimmed = body.trim();
    let lower = trimmed.to_lowercase();

    // 只有明确包含密码相关提示时，才认为需要密码
    let is_password_related = lower.contains("password")
        || lower.contains("encrypted")
        || lower.contains("请输入密码")
        || lower.contains("密码");

    if !is_password_related {
        // 不是密码问题，返回 None 让调用方显示原始错误
        return None;
    }

    // 检查是否是密码错误（已输入但不正确）
    if lower.contains("invalid") && lower.contains("password") {
        return Some("PASSWORD_INVALID");
    }
    if lower.contains("incorrect") || lower.contains("wrong") {
        return Some("PASSWORD_INVALID");
    }

    // 需要密码
    Some(if had_password {
        "PASSWORD_INVALID"
    } else {
        "PASSWORD_REQUIRED"
    })
}

fn build_client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .cookie_store(true)
        .user_agent(USER_AGENT)
        .build()
        .map_err(|e| format!("初始化网络客户端失败: {}", e))
}

async fn check_needs_password(client: &reqwest::Client, share_key: &str) -> Result<bool, String> {
    let page_url = format!("{}/d/{}/", BASE_URL, share_key);
    let resp = client
        .get(&page_url)
        .header(reqwest::header::USER_AGENT, USER_AGENT)
        .send()
        .await
        .map_err(|e| format!("检查链接失败: {}", e))?;

    let html = resp.text().await.unwrap_or_default();

    // 检查页面是否包含密码输入表单
    let needs_password = html.contains("Please input the password")
        || html.contains("请输入密码")
        || html.contains("id=\"password\"")
        || html.contains("name=\"password\"");

    Ok(needs_password)
}

async fn verify_share_password(
    client: &reqwest::Client,
    share_key: &str,
    password: &str,
) -> Result<(), String> {
    let page_url = format!("{}/d/{}/", BASE_URL, share_key);

    // Step 1: GET 页面，获取 CSRF token 和 session cookie
    let get_resp = client
        .get(&page_url)
        .header(reqwest::header::USER_AGENT, USER_AGENT)
        .send()
        .await
        .map_err(|e| format!("获取页面失败: {}", e))?;

    let html = get_resp.text().await.unwrap_or_default();

    // 提取 CSRF token（从 <input name="csrfmiddlewaretoken" value="xxx"> 或 cookie）
    let csrf_token = extract_csrf_token(&html);

    // Step 2: POST 密码表单
    let mut form_params = vec![("password", password.to_string())];
    if let Some(token) = &csrf_token {
        form_params.push(("csrfmiddlewaretoken", token.clone()));
    }

    let post_resp = client
        .post(&page_url)
        .header(reqwest::header::USER_AGENT, USER_AGENT)
        .header(reqwest::header::REFERER, &page_url)
        .form(&form_params)
        .send()
        .await
        .map_err(|e| format!("验证密码失败: {}", e))?;

    let status = post_resp.status();

    // 成功：200 或重定向到文件列表页
    if status.is_success() || status.is_redirection() {
        // 检查响应体是否仍然是密码页面
        let body = post_resp.text().await.unwrap_or_default();
        if body.contains("Please input the password") || body.contains("请输入密码") {
            return Err("PASSWORD_INVALID".to_string());
        }
        return Ok(());
    }

    let body = post_resp.text().await.unwrap_or_default();
    if let Some(code) = parse_password_error(status, &body, true) {
        return Err(code.to_string());
    }
    Err(format!("验证密码失败: HTTP {}", status))
}

fn extract_csrf_token(html: &str) -> Option<String> {
    // 方法1: 从 <input name="csrfmiddlewaretoken" value="xxx"> 提取
    if let Some(pos) = html.find("csrfmiddlewaretoken") {
        let after = &html[pos..];
        if let Some(value_pos) = after.find("value=\"") {
            let start = value_pos + 7;
            let rest = &after[start..];
            if let Some(end) = rest.find('"') {
                return Some(rest[..end].to_string());
            }
        }
        // 也可能是 value='xxx'
        if let Some(value_pos) = after.find("value='") {
            let start = value_pos + 7;
            let rest = &after[start..];
            if let Some(end) = rest.find('\'') {
                return Some(rest[..end].to_string());
            }
        }
    }
    None
}
