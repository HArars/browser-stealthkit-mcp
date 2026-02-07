from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from StealthKit import StealthBrowser
from StealthKit.config import load_config


mcp = FastMCP("stealthkit-browser")
APP_CONFIG = load_config()


def _to_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)
    except TypeError:
        return str(data)


class _Session:
    def __init__(self) -> None:
        self.sb: Optional[StealthBrowser] = None
        self.pages: List[Any] = []
        self.current_idx: int = -1
        self.console_logs: Dict[int, List[Dict[str, Any]]] = {}
        self.network_logs: Dict[int, List[Dict[str, Any]]] = {}
        self.last_start_args: Dict[str, Any] = {}
        self.pending_storage_state: Optional[str] = None

    def is_running(self) -> bool:
        return self.sb is not None and len(self.pages) > 0 and 0 <= self.current_idx < len(self.pages)

    def _attach_page(self, page: Any) -> None:
        pid = id(page)
        self.console_logs[pid] = []
        self.network_logs[pid] = []

        def _on_console(msg: Any) -> None:
            self.console_logs[pid].append(
                {
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location,
                }
            )

        def _on_request(req: Any) -> None:
            self.network_logs[pid].append(
                {
                    "method": req.method,
                    "url": req.url,
                    "resource_type": req.resource_type,
                }
            )

        page.on("console", _on_console)
        page.on("request", _on_request)

    async def start(
        self,
        headless: Optional[bool] = None,
        proxy: Optional[str] = None,
        channel: Optional[str] = None,
        storage_state: Optional[str] = None,
    ) -> str:
        if self.is_running():
            return "Browser session already running."

        browser_cfg = APP_CONFIG.browser
        resolved_headless = browser_cfg.headless if headless is None else headless
        resolved_proxy = browser_cfg.proxy if proxy is None else proxy
        resolved_channel = browser_cfg.channel if channel is None else channel

        self.last_start_args = {
            "headless": resolved_headless,
            "proxy": resolved_proxy,
            "channel": resolved_channel,
        }
        # Try to pass storage_state into StealthBrowser if supported.
        try:
            self.sb = StealthBrowser(
                headless=resolved_headless,
                proxy=resolved_proxy,
                channel=resolved_channel,
                user_agent=browser_cfg.user_agent,
                viewport={"width": browser_cfg.viewport.width, "height": browser_cfg.viewport.height},
                locale=browser_cfg.locale,
                timezone_id=browser_cfg.timezone_id,
                launch_args=browser_cfg.launch.args,
                ignore_default_args=browser_cfg.launch.ignore_default_args,
                storage_state=storage_state,
            )  # type: ignore
        except TypeError:
            self.sb = StealthBrowser(
                headless=resolved_headless,
                proxy=resolved_proxy,
                channel=resolved_channel,
                user_agent=browser_cfg.user_agent,
                viewport={"width": browser_cfg.viewport.width, "height": browser_cfg.viewport.height},
                locale=browser_cfg.locale,
                timezone_id=browser_cfg.timezone_id,
                launch_args=browser_cfg.launch.args,
                ignore_default_args=browser_cfg.launch.ignore_default_args,
            )
            # If storage_state is provided but StealthBrowser doesn't support it, we'll attempt to apply it later.
            self.pending_storage_state = storage_state

        await self.sb.__aenter__()
        page = await self.sb.get_page()
        # Best-effort: if we couldn't pass storage_state into StealthBrowser, try to recreate context with it.
        if self.pending_storage_state:
            try:
                browser_obj = getattr(self.sb, "browser", None)
                if browser_obj is not None:
                    # Close old context if present
                    try:
                        if getattr(self.sb, "context", None) is not None:
                            await self.sb.context.close()  # type: ignore
                    except Exception:
                        pass
                    new_ctx = await browser_obj.new_context(storage_state=self.pending_storage_state)
                    self.sb.context = new_ctx  # type: ignore
                    page = await new_ctx.new_page()
            except Exception:
                # Ignore and proceed; caller can still manually login.
                pass
            finally:
                self.pending_storage_state = None

        self.pages = [page]
        self.current_idx = 0
        self._attach_page(page)
        return "Browser started with tab 0."

    async def stop(self) -> str:
        if self.sb is None:
            self.pages = []
            self.current_idx = -1
            self.console_logs = {}
            self.network_logs = {}
            return "Browser session not running."

        await self.sb.__aexit__(None, None, None)
        self.sb = None
        self.pages = []
        self.current_idx = -1
        self.console_logs = {}
        self.network_logs = {}
        return "Browser closed."

    def current_page(self) -> Any:
        if not self.is_running():
            raise RuntimeError("Browser is not started. Call `browser_start` first.")
        return self.pages[self.current_idx]

    async def new_tab(self) -> int:
        if self.sb is None or self.sb.context is None:
            raise RuntimeError("Browser is not started. Call `browser_start` first.")
        page = await self.sb.context.new_page()
        self.pages.append(page)
        self.current_idx = len(self.pages) - 1
        self._attach_page(page)
        return self.current_idx

    async def list_tabs(self) -> List[Dict[str, Any]]:
        tabs: List[Dict[str, Any]] = []
        for idx, page in enumerate(self.pages):
            try:
                title = await page.title()
            except Exception:
                title = ""
            tabs.append(
                {
                    "index": idx,
                    "current": idx == self.current_idx,
                    "url": page.url,
                    "title": title,
                }
            )
        return tabs

    def select_tab(self, index: int) -> None:
        if not self.is_running():
            raise RuntimeError("Browser is not started. Call `browser_start` first.")
        if index < 0 or index >= len(self.pages):
            raise ValueError(f"Invalid tab index: {index}")
        self.current_idx = index

    async def close_tab(self, index: Optional[int] = None) -> str:
        if not self.is_running():
            raise RuntimeError("Browser is not started. Call `browser_start` first.")
        idx = self.current_idx if index is None else index
        if idx < 0 or idx >= len(self.pages):
            raise ValueError(f"Invalid tab index: {idx}")

        page = self.pages[idx]
        await page.close()
        del self.pages[idx]
        self.console_logs.pop(id(page), None)
        self.network_logs.pop(id(page), None)

        if len(self.pages) == 0:
            return await self.stop()
        if self.current_idx >= len(self.pages):
            self.current_idx = len(self.pages) - 1
        return f"Closed tab {idx}. Current tab is {self.current_idx}."


session = _Session()


@mcp.tool()
async def browser_start(
    headless: Optional[bool] = None,
    proxy: Optional[str] = None,
    channel: Optional[str] = None,
    storage_state: Optional[str] = None,
) -> str:
    return await session.start(headless=headless, proxy=proxy, channel=channel, storage_state=storage_state)


@mcp.tool()
async def browser_close() -> str:
    return await session.stop()


@mcp.tool()
async def browser_new_tab() -> str:
    idx = await session.new_tab()
    return f"Opened tab {idx}."


@mcp.tool()
async def browser_list_tabs() -> str:
    return _to_json(await session.list_tabs())


@mcp.tool()
async def browser_select_tab(index: int) -> str:
    session.select_tab(index)
    return f"Selected tab {index}."


@mcp.tool()
async def browser_close_tab(index: Optional[int] = None) -> str:
    return await session.close_tab(index=index)


@mcp.tool()
async def browser_navigate(url: str, wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> str:
    page = session.current_page()
    resp = await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
    status = getattr(resp, "status", None) if resp else None
    return _to_json({"url": page.url, "status": status, "title": await page.title()})


@mcp.tool()
async def browser_navigate_back(wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> str:
    page = session.current_page()
    resp = await page.go_back(wait_until=wait_until, timeout=timeout_ms)
    status = getattr(resp, "status", None) if resp else None
    return _to_json({"url": page.url, "status": status, "title": await page.title()})


@mcp.tool()
async def browser_get_title() -> str:
    return await session.current_page().title()


@mcp.tool()
async def browser_get_html(max_chars: int = 20000) -> str:
    html = await session.current_page().content()
    return html[:max_chars]


@mcp.tool()
async def browser_click(selector: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    await page.click(selector=selector, timeout=timeout_ms)
    return f"Clicked: {selector}"


@mcp.tool()
async def browser_type(
    selector: str,
    text: str,
    clear: bool = True,
    submit: bool = False,
    timeout_ms: int = 10000,
) -> str:
    page = session.current_page()
    if clear:
        await page.fill(selector=selector, value="", timeout=timeout_ms)
    await page.type(selector=selector, text=text, timeout=timeout_ms)
    if submit:
        await page.press(selector=selector, key="Enter", timeout=timeout_ms)
    return f"Typed into {selector}."


@mcp.tool()
async def browser_press_key(key: str) -> str:
    page = session.current_page()
    await page.keyboard.press(key)
    return f"Pressed key: {key}"


@mcp.tool()
async def browser_get_url() -> str:
    return session.current_page().url


@mcp.tool()
async def browser_reload(wait_until: str = "domcontentloaded", timeout_ms: int = 30000) -> str:
    page = session.current_page()
    resp = await page.reload(wait_until=wait_until, timeout=timeout_ms)
    status = getattr(resp, "status", None) if resp else None
    return _to_json({"url": page.url, "status": status, "title": await page.title()})


@mcp.tool()
async def browser_sleep(seconds: float) -> str:
    await session.current_page().wait_for_timeout(int(seconds * 1000))
    return f"Slept {seconds} second(s)."


@mcp.tool()
async def browser_wait_for_text(text: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    await page.get_by_text(text).first.wait_for(state="visible", timeout=timeout_ms)
    return f"Text appeared: {text}"


@mcp.tool()
async def browser_wait_for_text_gone(text: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    await page.get_by_text(text).first.wait_for(state="hidden", timeout=timeout_ms)
    return f"Text disappeared: {text}"


@mcp.tool()
async def browser_fill(selector: str, text: str, timeout_ms: int = 10000, submit: bool = False) -> str:
    page = session.current_page()
    await page.fill(selector=selector, value=text, timeout=timeout_ms)
    if submit:
        await page.press(selector=selector, key="Enter", timeout=timeout_ms)
    return f"Filled: {selector}"


@mcp.tool()
async def browser_scroll_by(delta_y: float, delta_x: float = 0) -> str:
    page = session.current_page()
    try:
        await page.mouse.wheel(delta_x, delta_y)
    except Exception:
        # fallback
        await page.evaluate("([dx, dy]) => window.scrollBy(dx, dy)", [delta_x, delta_y])
    return f"Scrolled by dx={delta_x}, dy={delta_y}."


def _normalize_whitespace(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _soft_truncate(s: str, max_chars: int) -> Dict[str, Any]:
    total = len(s)
    if total <= max_chars:
        return {"text": s, "truncated": False, "total_chars": total}
    cut = s.rfind("\n\n", 0, max_chars)
    end = cut if cut >= int(max_chars * 0.6) else max_chars
    return {"text": s[:end], "truncated": True, "total_chars": total}


@mcp.tool()
async def browser_get_page_content(
    mode: str = "text",
    selector: Optional[str] = None,
    max_chars: int = 20000,
    include_links: bool = True,
    include_metadata: bool = True,
) -> str:
    allowed = {"text", "html", "markdown"}
    if mode not in allowed:
        raise ValueError(f"Invalid mode: {mode}. Allowed: {sorted(allowed)}")

    page = session.current_page()

    if mode == "html":
        raw = await page.locator(selector).first.inner_html(timeout=5000) if selector else await page.content()
    else:
        # text / markdown: use innerText to match visible content
        if selector:
            raw = await page.locator(selector).first.inner_text(timeout=5000)
        else:
            raw = await page.evaluate("() => document.body ? document.body.innerText : ''")
        raw = _normalize_whitespace(raw)

    trunc = _soft_truncate(raw, max_chars)

    result: Dict[str, Any] = {
        "mode": mode,
        "content": trunc["text"],
        "truncated": trunc["truncated"],
        "total_chars": trunc["total_chars"],
    }

    if include_metadata:
        result["url"] = page.url
        try:
            result["title"] = await page.title()
        except Exception:
            result["title"] = ""

    if include_links:
        links = await page.evaluate(
            """(sel) => {
                const root = sel ? document.querySelector(sel) : document;
                if (!root) return [];
                const as = Array.from(root.querySelectorAll('a[href]'));
                return as.map(a => ({
                    text: (a.textContent || '').trim().slice(0, 200),
                    href: a.href
                })).filter(x => x.href);
            }""",
            selector,
        )
        result["links"] = links

    return _to_json(result)


@mcp.tool()
async def browser_wait_for_selector(selector: str, state: str = "visible", timeout_ms: int = 10000) -> str:
    page = session.current_page()
    allowed = {"attached", "visible", "hidden", "detached"}
    if state not in allowed:
        raise ValueError(f"Invalid state: {state}. Allowed: {sorted(allowed)}")
    locator = page.locator(selector).first
    await locator.wait_for(state=state, timeout=timeout_ms)
    return f"Selector ready: {selector} (state={state})"


@mcp.tool()
async def browser_get_text(selector: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    locator = page.locator(selector).first
    await locator.wait_for(state="visible", timeout=timeout_ms)
    return await locator.inner_text()


@mcp.tool()
async def browser_get_attribute(selector: str, attribute: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    locator = page.locator(selector).first
    await locator.wait_for(state="attached", timeout=timeout_ms)
    val = await locator.get_attribute(attribute)
    return _to_json(val)


@mcp.tool()
async def browser_scroll_into_view(selector: str, timeout_ms: int = 10000) -> str:
    page = session.current_page()
    locator = page.locator(selector).first
    await locator.wait_for(state="attached", timeout=timeout_ms)
    await locator.scroll_into_view_if_needed(timeout=timeout_ms)
    return f"Scrolled into view: {selector}"


@mcp.tool()
async def browser_save_storage(path: str = "storage_state.json") -> str:
    if session.sb is None or getattr(session.sb, "context", None) is None:
        raise RuntimeError("Browser is not started. Call `browser_start` first.")
    await session.sb.context.storage_state(path=path)  # type: ignore
    return f"Saved storage_state to {path}"


@mcp.tool()
async def browser_load_storage(path: str) -> str:
    if not session.is_running() or session.sb is None:
        raise RuntimeError("Browser is not started. Call `browser_start` first.")

    browser_obj = getattr(session.sb, "browser", None)
    if browser_obj is None:
        raise RuntimeError("Underlying browser object not exposed; cannot load storage_state in-place.")

    # Close existing pages
    for p in list(session.pages):
        try:
            await p.close()
        except Exception:
            pass
    session.pages = []
    session.current_idx = -1

    # Close old context if present
    try:
        if getattr(session.sb, "context", None) is not None:
            await session.sb.context.close()  # type: ignore
    except Exception:
        pass

    new_ctx = await browser_obj.new_context(storage_state=path)
    session.sb.context = new_ctx  # type: ignore
    page = await new_ctx.new_page()
    session.pages = [page]
    session.current_idx = 0
    session._attach_page(page)
    return f"Loaded storage_state from {path} into a new context (tab 0)."


@mcp.tool()
async def browser_evaluate(js_expression: str) -> str:
    result = await session.current_page().evaluate(js_expression)
    return _to_json(result)


@mcp.tool()
async def browser_take_screenshot(path: str = "mcp_screenshot.png", full_page: bool = True) -> str:
    await session.current_page().screenshot(path=path, full_page=full_page)
    return f"Saved screenshot to {path}"


@mcp.tool()
async def browser_take_screenshot_base64(
    full_page: bool = True,
    image_type: str = "png",
    path: Optional[str] = None,
) -> str:
    img_type = image_type.lower()
    if img_type not in {"png", "jpeg"}:
        raise ValueError("image_type must be 'png' or 'jpeg'.")

    page = session.current_page()
    image_bytes = await page.screenshot(path=path, full_page=full_page, type=img_type)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return _to_json(
        {
            "mime_type": f"image/{img_type}",
            "data": encoded,
            "path": path,
        }
    )


@mcp.tool()
async def browser_snapshot(max_chars: int = 30000) -> str:
    page = session.current_page()
    text = await page.inner_text("body")
    snapshot = {
        "url": page.url,
        "title": await page.title(),
        "text": text[:max_chars],
    }
    return _to_json(snapshot)


@mcp.tool()
async def browser_console_messages(only_errors: bool = False, limit: int = 200) -> str:
    page = session.current_page()
    logs = session.console_logs.get(id(page), [])
    if only_errors:
        logs = [x for x in logs if x.get("type") == "error"]
    return _to_json(logs[-limit:])


@mcp.tool()
async def browser_network_requests(limit: int = 200) -> str:
    page = session.current_page()
    logs = session.network_logs.get(id(page), [])
    return _to_json(logs[-limit:])


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
