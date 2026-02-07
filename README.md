# stealth-mcp

[简体中文文档 (Chinese)](README.zh-CN.md)

A browser automation MCP Server built on Playwright + FastMCP, designed for more human-like behavior (stealth injection, optional proxy, multi-tab management, console/network logs).

## Project Structure

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

## Features

- Browser session and tab management
- Navigation, click/type/fill/scroll, and waits
- Content extraction (title/url/html/text/snapshot)
- Console and network logs for debugging
- `storage_state` save/load
- Screenshot and Base64 screenshot

## Requirements

- Python 3.10+
- Microsoft Edge or Google Chrome installed (default channel: `msedge`)
- Recommended: use local virtual environment `.venv`

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install mcp playwright
.\.venv\Scripts\python -m playwright install chromium
```

On macOS/Linux, replace `./.venv/Scripts/python` with `.venv/bin/python`.

## Start MCP Server

```powershell
.\.venv\Scripts\python mcp_server.py
```

`FastMCP` runs in `stdio` mode by default.

## Configuration

`config.toml` in project root controls defaults (`headless`, `channel`, `proxy`, `viewport`, launch args).

- `mcp_server.py` loads `config.toml` at startup
- `browser_start` params are optional:
- Omitted: use config defaults
- Provided: override config values

Environment override example:

```powershell
$env:BROWSER_HEADLESS="true"
$env:BROWSER_CHANNEL="msedge"
$env:BROWSER_PROXY="http://127.0.0.1:10809"
```

## Generic Client Config Example

```json
{
  "mcpServers": {
    "stealthkit-browser": {
      "command": "<PROJECT_ROOT>/.venv/Scripts/python.exe",
      "args": ["<PROJECT_ROOT>/mcp_server.py"]
    }
  }
}
```

## Codex Config Example

`~/.codex/config.toml`:

```toml
[mcp_servers.stealthkit_browser]
command = "<PROJECT_ROOT>\\.venv\\Scripts\\python.exe"
args = ["<PROJECT_ROOT>\\mcp_server.py"]
```

## OpenCode Local MCP Example

`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "xbrowser": {
      "type": "local",
      "command": [
        "<PROJECT_ROOT>/.venv/Scripts/python.exe",
        "<PROJECT_ROOT>/mcp_server.py"
      ]
    }
  }
}
```

`type: "local"` is required for OpenCode local MCP servers.

## Tool List (`mcp_server.py`)

### Session & Tabs

- `browser_start(headless=None, proxy=None, channel=None, storage_state=None)`
- `browser_close()`
- `browser_new_tab()`
- `browser_list_tabs()`
- `browser_select_tab(index)`
- `browser_close_tab(index=None)`

### Navigation & State

- `browser_navigate(url, wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_navigate_back(wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_reload(wait_until="domcontentloaded", timeout_ms=30000)`
- `browser_get_title()`
- `browser_get_url()`
- `browser_sleep(seconds)`

### Interactions

- `browser_click(selector, timeout_ms=10000)`
- `browser_type(selector, text, clear=true, submit=false, timeout_ms=10000)`
- `browser_fill(selector, text, timeout_ms=10000, submit=false)`
- `browser_press_key(key)`
- `browser_scroll_by(delta_y, delta_x=0)`
- `browser_scroll_into_view(selector, timeout_ms=10000)`

### Waiting & Reading

- `browser_wait_for_text(text, timeout_ms=10000)`
- `browser_wait_for_text_gone(text, timeout_ms=10000)`
- `browser_wait_for_selector(selector, state="visible", timeout_ms=10000)`
- `browser_get_text(selector, timeout_ms=10000)`
- `browser_get_attribute(selector, attribute, timeout_ms=10000)`

### Content & Evaluate

- `browser_get_html(max_chars=20000)`
- `browser_get_page_content(mode="text", selector=None, max_chars=20000, include_links=true, include_metadata=true)`
- `browser_snapshot(max_chars=30000)`
- `browser_evaluate(js_expression)`

### Screenshot & Storage

- `browser_take_screenshot(path="mcp_screenshot.png", full_page=true)`
- `browser_take_screenshot_base64(full_page=true, image_type="png", path=None)`
- `browser_save_storage(path="storage_state.json")`
- `browser_load_storage(path)`

### Debug Logs

- `browser_console_messages(only_errors=false, limit=200)`
- `browser_network_requests(limit=200)`

## Notes

- `headless` currently controls moving window off-screen; underlying launch remains `playwright.launch(headless=False)`.
- `browser_start(storage_state=...)` is best-effort and may rebuild context if needed.
