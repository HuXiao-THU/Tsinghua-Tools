import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { join } from "@tauri-apps/api/path";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

type FileNode = {
  id: string;
  name: string;
  parent: string | null;
  is_dir: boolean;
  size: number;
};

type DownloadProgress = {
  file_path: string;
  downloaded: number;
  total: number | null;
  status: string;
  error: string | null;
};

function App() {
  const [shareLink, setShareLink] = useState("");
  const [shareKey, setShareKey] = useState<string | null>(null);
  const [nodes, setNodes] = useState<FileNode[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [saveDir, setSaveDir] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [progressMap, setProgressMap] = useState<
    Record<string, DownloadProgress>
  >({});
  const [message, setMessage] = useState<string>("");
  const [passwordPromptOpen, setPasswordPromptOpen] = useState(false);
  const [passwordInput, setPasswordInput] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [pendingAction, setPendingAction] = useState<"parse" | "download" | null>(
    null
  );
  const [sharePassword, setSharePassword] = useState<string | null>(null);

  useEffect(() => {
    const unlisten = listen<DownloadProgress>(
      "download-progress",
      (event) => {
        setProgressMap((prev) => ({
          ...prev,
          [event.payload.file_path]: event.payload,
        }));
      }
    );
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const childrenMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    nodes.forEach((node) => {
      if (!node.parent) return;
      if (!map[node.parent]) map[node.parent] = [];
      map[node.parent].push(node.id);
    });
    return map;
  }, [nodes]);

  const orderedNodes = useMemo(() => {
    const result: FileNode[] = [];
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const dfs = (id: string) => {
      const node = nodeMap.get(id);
      if (!node) return;
      result.push(node);
      const children = childrenMap[id] || [];
      children.sort();
      children.forEach(dfs);
    };
    dfs("/");
    return result;
  }, [nodes, childrenMap]);

  const depthOf = useCallback((id: string) => {
    if (id === "/") return 0;
    return id.split("/").filter(Boolean).length;
  }, []);

  const markSubtree = useCallback(
    (id: string, value: boolean, draft: Record<string, boolean>) => {
      draft[id] = value;
      (childrenMap[id] || []).forEach((childId) => {
        markSubtree(childId, value, draft);
      });
    },
    [childrenMap]
  );

  const handleToggle = (node: FileNode) => {
    setChecked((prev) => {
      const next = { ...prev };
      const newValue = !prev[node.id];
      if (node.is_dir) {
        markSubtree(node.id, newValue, next);
      } else {
        next[node.id] = newValue;
      }
      return next;
    });
  };

  const parseWithPassword = async (passwordOverride?: string | null) => {
    // 清除旧的解析结果和下载进度
    setNodes([]);
    setChecked({});
    setProgressMap({});
    setShareKey(null);
    setMessage("");
    setLoading(true);

    // 确定本次解析使用的密码（用局部变量避免 React state 异步更新问题）
    const effectivePassword = passwordOverride !== undefined ? passwordOverride : null;
    if (passwordOverride === undefined) {
      setSharePassword(null);
    }

    try {
      const key = await invoke<string | null>("parse_share_key", {
        shareLink,
      });
      if (!key) {
        setMessage("分享链接格式不正确");
        setLoading(false);
        return;
      }
      setShareKey(key);
      const tree = await invoke<FileNode[]>("fetch_share_tree", {
        shareKey: key,
        password: effectivePassword,
      });
      setNodes(tree);
      const initialChecked: Record<string, boolean> = {};
      tree.forEach((n) => {
        initialChecked[n.id] = false;
      });
      setChecked(initialChecked);
    } catch (err) {
      if (String(err).includes("PASSWORD_REQUIRED")) {
        setPendingAction("parse");
        setPasswordInput("");
        setPasswordPromptOpen(true);
      } else if (String(err).includes("PASSWORD_INVALID")) {
        setPendingAction("parse");
        setPasswordInput("");
        setPasswordPromptOpen(true);
        setMessage("密码错误，请重新输入");
      } else {
        setMessage(`解析失败: ${String(err)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    await parseWithPassword();
  };

  const handlePickDir = async () => {
    setMessage("");
    try {
      const result = await open({ directory: true, multiple: false });
      if (typeof result === "string") {
        setSaveDir(result);
      }
    } catch (err) {
      setMessage(`打开选择目录失败: ${String(err)}`);
    }
  };

  const downloadWithPassword = async (passwordOverride?: string | null) => {
    if (!shareKey) {
      setMessage("请先解析分享链接");
      return;
    }
    if (!saveDir) {
      setMessage("请选择下载目录");
      return;
    }
    const fileNodes = nodes.filter((n) => !n.is_dir);
    const selectedFiles = fileNodes.filter((n) => checked[n.id]);
    if (selectedFiles.length === 0) {
      setMessage("未选择任何文件");
      return;
    }

    setMessage("");
    setLoading(true);
    try {
      setProgressMap((prev) => {
        const next = { ...prev };
        selectedFiles.forEach((file) => {
          next[file.id] = {
            file_path: file.id,
            downloaded: 0,
            total: file.size,
            status: "queued",
            error: null,
          };
        });
        return next;
      });
      const items = await Promise.all(
        selectedFiles.map(async (file) => {
          const relative = file.id.replace(/^\//, "");
          const savePath = await join(saveDir, relative);
          return { file_path: file.id, save_path: savePath };
        })
      );
      await invoke("download_files", {
        shareKey,
        items,
        password: passwordOverride ?? sharePassword,
      });
      setMessage("下载完成");
    } catch (err) {
      if (String(err).includes("PASSWORD_REQUIRED")) {
        setPendingAction("download");
        setPasswordInput("");
        setPasswordPromptOpen(true);
      } else if (String(err).includes("PASSWORD_INVALID")) {
        setPendingAction("download");
        setPasswordInput("");
        setPasswordPromptOpen(true);
        setMessage("密码错误，请重新输入");
      } else {
        setMessage(`下载失败: ${String(err)}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    await downloadWithPassword();
  };

  const handlePasswordConfirm = async () => {
    const pwd = passwordInput.trim();
    if (!pwd) {
      setMessage("请输入密码");
      return;
    }
    setSharePassword(pwd);
    setPasswordPromptOpen(false);
    if (pendingAction === "parse") {
      await parseWithPassword(pwd);
    } else if (pendingAction === "download") {
      await downloadWithPassword(pwd);
    }
    setPendingAction(null);
  };

  const handlePasswordCancel = () => {
    setPasswordPromptOpen(false);
    setPendingAction(null);
  };

  const selectedFiles = useMemo(() => {
    return nodes.filter((n) => !n.is_dir && checked[n.id]);
  }, [nodes, checked]);

  const sizeMap = useMemo(() => {
    const map: Record<string, number> = {};
    nodes.forEach((node) => {
      if (!node.is_dir) {
        map[node.id] = node.size;
      }
    });
    return map;
  }, [nodes]);

  const activeIds = useMemo(() => {
    const selectedIds = selectedFiles.map((file) => file.id);
    const progressIds = Object.keys(progressMap);
    const merged = new Set([...selectedIds, ...progressIds]);
    return Array.from(merged);
  }, [selectedFiles, progressMap]);

  const overallDownloaded = useMemo(() => {
    return activeIds.reduce((sum, id) => {
      const progress = progressMap[id];
      if (!progress) return sum;
      return sum + progress.downloaded;
    }, 0);
  }, [activeIds, progressMap]);

  const overallTotal = useMemo(() => {
    return activeIds.reduce((sum, id) => {
      const progress = progressMap[id];
      const size = sizeMap[id] ?? 0;
      const total = progress?.total ?? size;
      const normalized = Math.max(total ?? 0, progress?.downloaded ?? 0);
      return sum + normalized;
    }, 0);
  }, [activeIds, progressMap, sizeMap]);

  const overallPercent = useMemo(() => {
    if (overallTotal === 0) return 0;
    return Math.min(100, (overallDownloaded / overallTotal) * 100);
  }, [overallDownloaded, overallTotal]);

  return (
    <div className="app">
      <header className="header">
        <h1>清华云盘下载器</h1>
        <p>支持分享链接批量下载</p>
      </header>

      <section className="card">
        <label className="label">分享链接</label>
        <div className="row">
          <input
            className="input"
            value={shareLink}
            onChange={(e) => setShareLink(e.target.value)}
            placeholder="https://cloud.tsinghua.edu.cn/d/xxxxxx/"
          />
          <button className="button" onClick={handleParse} disabled={loading}>
            解析
          </button>
        </div>
      </section>

      <section className="card">
        <div className="row">
          <label className="label">下载目录</label>
          <button className="button ghost" onClick={handlePickDir}>
            选择文件夹
          </button>
        </div>
        <div className="path">{saveDir || "未选择"}</div>
      </section>

      <section className="card">
        <div className="row space-between">
          <label className="label">文件列表</label>
          <button className="button" onClick={handleDownload} disabled={loading}>
            开始下载
          </button>
        </div>
        <div className="tree">
          {orderedNodes.map((node) => (
            <div
              key={node.id}
              className={`tree-row ${node.is_dir ? "dir" : "file"}`}
              style={{ paddingLeft: `${depthOf(node.id) * 16 + 8}px` }}
            >
              <input
                type="checkbox"
                checked={Boolean(checked[node.id])}
                onChange={() => handleToggle(node)}
              />
              <span className="name">{node.name}</span>
              {!node.is_dir && (
                <span className="size">{formatSize(node.size)}</span>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <label className="label">下载进度</label>
        <div className="overall-progress">
          <div className="overall-info">
            <span>总体进度</span>
            <span>
              {formatSize(overallDownloaded)} / {formatSize(overallTotal)}
            </span>
          </div>
          <div className="progress-bar">
            <div
              className="progress-bar-inner"
              style={{ width: `${overallPercent}%` }}
            />
          </div>
        </div>
        <div className="progress-list">
          {Object.values(progressMap).map((item) => (
            <div className="progress-row" key={item.file_path}>
              <span className="progress-name">{item.file_path}</span>
              <span className="progress-value">
                {item.total
                  ? `${formatSize(item.downloaded)} / ${formatSize(
                      item.total
                    )}`
                  : formatSize(item.downloaded)}
              </span>
              <span className="progress-status">{item.status}</span>
            </div>
          ))}
        </div>
      </section>

      {message && <div className="message">{message}</div>}

      {passwordPromptOpen && (
        <div className="modal-backdrop">
          <div className="modal">
            <h3>需要密码</h3>
            <p>该分享链接已设置密码，请输入后继续。</p>
            <input
              className="input"
              type={passwordVisible ? "text" : "password"}
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              placeholder="请输入分享密码"
            />
            <label className="password-toggle">
              <input
                type="checkbox"
                checked={passwordVisible}
                onChange={(e) => setPasswordVisible(e.target.checked)}
              />
              显示密码
            </label>
            <div className="row modal-actions">
              <button className="button ghost" onClick={handlePasswordCancel}>
                取消
              </button>
              <button className="button" onClick={handlePasswordConfirm}>
                确认
              </button>
            </div>
          </div>
        </div>
      )}

      {loading && nodes.length === 0 && !passwordPromptOpen && (
        <div className="modal-backdrop">
          <div className="modal loading-modal">
            <div className="spinner"></div>
            <p>正在解析链接，请稍候...</p>
          </div>
        </div>
      )}
    </div>
  );
}

function formatSize(size: number) {
  const units = ["Bytes", "KB", "MB", "GB", "TB"];
  let value = size;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(2)} ${units[unitIndex]}`;
}

export default App;
