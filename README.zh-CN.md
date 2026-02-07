# stealth-browser-mcp

[English README](README.md)

基于 Playwright + FastMCP 的浏览器自动化 MCP Server，目标是提供更拟人化的浏览器行为（Stealth 注入、可选代理、多标签管理、控制台/网络日志抓取）。

## 项目结构

```text
.
|-- config.toml
|-- mcp_server.py
|-- StealthKit/
|   |-- browser.py
|   |-- config.py
|   |-- js.py
|   `-- __init__.py
`-- README.md
```

## 功能概览

- 浏览器会话与标签页管理
- 导航、点击/输入/填充/滚动、等待
- 内容提取（标题/URL/HTML/文本/快照）
- Console 与 Network 日志调试
- `storage_state` 保存与加载
- 截图与 Base64 截图

## 依赖与环境

- Python 3.10+
- 已安装 Microsoft Edge 或 Google Chrome（默认 channel: `msedge`）
- 推荐使用本地虚拟环境 `.venv`

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install mcp playwright
.\.venv\Scripts\python -m playwright install chromium
```

macOS/Linux 将 `./.venv/Scripts/python` 替换为 `.venv/bin/python`。

## MCP Add 快速安装（Codex / Gemini / OpenCode）

重要：本项目是本地 Python MCP Server。`mcp add` 一般只注册启动命令，不会自动创建 `.venv` 或安装 Python 依赖。

请先执行对应系统的 bootstrap 脚本：

Windows（PowerShell）：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install mcp playwright
.\.venv\Scripts\python -m playwright install chromium
```

macOS（zsh/bash）：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mcp playwright
python -m playwright install chromium
```

Linux（bash）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mcp playwright
python -m playwright install chromium
```

然后执行 `mcp add`（示例）：

Codex

```powershell
codex mcp add stealth_browser -- .\.venv\Scripts\python.exe mcp_server.py
```

Gemini CLI

```powershell
gemini mcp add stealth_browser -- .\.venv\Scripts\python.exe mcp_server.py
```

OpenCode

```powershell
opencode mcp add stealth_browser -- .\.venv\Scripts\python.exe mcp_server.py
```

如果你的 CLI 版本不支持 `mcp add`，请使用下面的配置文件方式。

## 启动 MCP Server

```powershell
.\.venv\Scripts\python mcp_server.py
```

`FastMCP` 默认以 `stdio` 方式运行。

## 配置说明

项目根目录 `config.toml` 统一管理默认参数（`headless`、`channel`、`proxy`、`viewport`、launch args）。

- `mcp_server.py` 启动时加载 `config.toml`
- `browser_start` 参数可选：
- 不传：使用配置默认值
- 传值：覆盖配置值

环境变量覆盖示例：

```powershell
$env:BROWSER_HEADLESS="true"
$env:BROWSER_CHANNEL="msedge"
$env:BROWSER_PROXY="http://127.0.0.1:10809"
```

## 通用客户端配置示例

```json
{
  "mcpServers": {
    "stealth_browser": {
      "command": "<PROJECT_ROOT>/.venv/Scripts/python.exe",
      "args": ["<PROJECT_ROOT>/mcp_server.py"]
    }
  }
}
```

## Codex MCP 配置示例

`~/.codex/config.toml`：

```toml
[mcp_servers.stealth_browser]
command = "<PROJECT_ROOT>\\.venv\\Scripts\\python.exe"
args = ["<PROJECT_ROOT>\\mcp_server.py"]
```

## Gemini Cli MCP 配置示例

`~/.gemini/settings.json`：

```json
{
  "mcpServers": {
    "stealth_browser": {
      "type": "local",
      "command": [
        "<PROJECT_ROOT>/.venv/Scripts/python.exe",
        "<PROJECT_ROOT>/mcp_server.py"
      ]
    }
  }
}
```

## OpenCode MCP 配置示例

`~/.config/opencode/opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "stealth_browser": {
      "type": "local",
      "command": [
        "<PROJECT_ROOT>/.venv/Scripts/python.exe",
        "<PROJECT_ROOT>/mcp_server.py"
      ]
    }
  }
}
```

## 工具列表（`mcp_server.py`）

### 会话与标签页

- `browser_start(headless=None, proxy=None, channel=None, storage_state=None)`
- `browser_close()`
- `browser_new_tab()`
- `browser_list_tabs()`
- `browser_select_tab(index)`
- `browser_close_tab(index=None)`

### 导航与状态

- `browser_navigate(url, wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_navigate_back(wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_reload(wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_get_title()`
- `browser_get_url()`
- `browser_sleep(seconds)`

### 交互

- `browser_click(selector, timeout_ms=10000)`
- `browser_type(selector, text, clear=true, submit=false, timeout_ms=10000)`
- `browser_fill(selector, text, timeout_ms=10000, submit=false)`
- `browser_press_key(key)`
- `browser_scroll_by(delta_y, delta_x=0)`
- `browser_scroll_into_view(selector, timeout_ms=10000)`

### 等待与读取

- `browser_wait_for_text(text, timeout_ms=10000)`
- `browser_wait_for_text_gone(text, timeout_ms=10000)`
- `browser_wait_for_selector(selector, state="visible", timeout_ms=10000)`
- `browser_get_text(selector, timeout_ms=10000)`
- `browser_get_attribute(selector, attribute, timeout_ms=10000)`

### 内容与执行

- `browser_get_html(max_chars=20000)`
- `browser_get_page_content(mode="text", selector=None, max_chars=20000, include_links=true, include_metadata=true)`
- `browser_snapshot(max_chars=30000)`
- `browser_evaluate(js_expression)`

### 截图与状态

- `browser_take_screenshot(path="mcp_screenshot.png", full_page=true)`
- `browser_take_screenshot_base64(full_page=true, image_type="png", path=None)`
- `browser_save_storage(path="storage_state.json")`
- `browser_load_storage(path)`

### 调试日志

- `browser_console_messages(only_errors=false, limit=200)`
- `browser_network_requests(limit=200)`
