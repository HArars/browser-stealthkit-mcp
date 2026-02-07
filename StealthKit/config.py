from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


@dataclass(frozen=True)
class ViewportConfig:
    width: int = 960
    height: int = 1000


@dataclass(frozen=True)
class BrowserLaunchConfig:
    args: tuple[str, ...] = (
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-infobars",
        "--disable-extensions",
    )
    ignore_default_args: tuple[str, ...] = ("--enable-automation",)


@dataclass(frozen=True)
class BrowserConfig:
    headless: bool = False
    proxy: str | None = None
    channel: str = "msedge"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    )
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    viewport: ViewportConfig = ViewportConfig()
    launch: BrowserLaunchConfig = BrowserLaunchConfig()


@dataclass(frozen=True)
class MCPConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "INFO"


@dataclass(frozen=True)
class AppConfig:
    mcp: MCPConfig = MCPConfig()
    browser: BrowserConfig = BrowserConfig()


def _to_bool(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config(path: str | os.PathLike | None = None) -> AppConfig:
    if path is not None:
        cfg_path = Path(path)
    else:
        env_path = os.getenv("APP_CONFIG")
        if env_path:
            cfg_path = Path(env_path)
        else:
            # Prefer project-root config.toml regardless of process CWD.
            cfg_path = Path(__file__).resolve().parent.parent / "config.toml"
    data: dict = {}
    if cfg_path.exists():
        with cfg_path.open("rb") as f:
            data = tomllib.load(f)

    mcp_d = data.get("mcp", {})
    browser_d = data.get("browser", {})
    viewport_d = browser_d.get("viewport") or {}
    launch_d = browser_d.get("launch") or {}

    mcp_host = os.getenv("MCP_HOST", mcp_d.get("host", "127.0.0.1"))
    mcp_port = int(os.getenv("MCP_PORT", mcp_d.get("port", 8765)))
    mcp_log_level = os.getenv("MCP_LOG_LEVEL", mcp_d.get("log_level", "INFO"))

    b_headless = browser_d.get("headless", False)
    if "BROWSER_HEADLESS" in os.environ:
        b_headless = _to_bool(os.environ["BROWSER_HEADLESS"])

    b_proxy = os.getenv("BROWSER_PROXY", browser_d.get("proxy") or "") or None
    b_channel = os.getenv("BROWSER_CHANNEL", browser_d.get("channel", "msedge"))
    b_locale = os.getenv("BROWSER_LOCALE", browser_d.get("locale", "en-US"))
    b_tz = os.getenv(
        "BROWSER_TIMEZONE_ID",
        browser_d.get("timezone_id", "America/New_York"),
    )

    viewport = ViewportConfig(
        width=int(viewport_d.get("width", 960)),
        height=int(viewport_d.get("height", 1000)),
    )
    launch = BrowserLaunchConfig(
        args=tuple(launch_d.get("args", BrowserLaunchConfig().args)),
        ignore_default_args=tuple(
            launch_d.get(
                "ignore_default_args", BrowserLaunchConfig().ignore_default_args
            )
        ),
    )

    return AppConfig(
        mcp=MCPConfig(host=mcp_host, port=mcp_port, log_level=mcp_log_level),
        browser=BrowserConfig(
            headless=bool(b_headless),
            proxy=b_proxy,
            channel=b_channel,
            user_agent=browser_d.get("user_agent", BrowserConfig().user_agent),
            locale=b_locale,
            timezone_id=b_tz,
            viewport=viewport,
            launch=launch,
        ),
    )
