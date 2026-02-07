# stealth_kit/browser.py
import asyncio
from playwright.async_api import async_playwright
from .js import STEALTH_JS


class StealthBrowser:
    def __init__(
        self,
        headless=False,
        proxy=None,
        channel="msedge",
        user_agent=None,
        viewport=None,
        locale="en-US",
        timezone_id="America/New_York",
        launch_args=None,
        ignore_default_args=None,
    ):
        """
        初始化隐匿浏览器
        :param headless: 是否无头模式 (建议 False 以通过检测)
        :param proxy: 代理地址 (如 "http://127.0.0.1:10809")
        :param channel: 浏览器通道 ("msedge" 或 "chrome")
        """
        self.headless = headless
        self.proxy_cfg = {"server": proxy} if proxy else None
        self.channel = channel
        self.user_agent = user_agent
        self.viewport = viewport
        self.locale = locale
        self.timezone_id = timezone_id
        self.launch_args = launch_args
        self.ignore_default_args = ignore_default_args
        self.playwright = None
        self.browser = None
        self.context = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()

        # 1. 启动参数配置 (核心反爬)
        args = list(
            self.launch_args
            or [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-extensions",
            ]
        )
        if self.headless:
            # 伪造无头模式：把窗口挪到屏幕外，而不是真的开启 headless
            args.append("--window-position=-10000,-10000")

        self.browser = await self.playwright.chromium.launch(
            channel=self.channel,
            headless=False,  # 始终开启界面以保持指纹真实性
            ignore_default_args=list(self.ignore_default_args or ["--enable-automation"]),
            args=args,
            proxy=self.proxy_cfg,
        )

        # 2. 上下文配置
        self.context = await self.browser.new_context(
            user_agent=self.user_agent
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            viewport=self.viewport or {"width": 960, "height": 1000},
            locale=self.locale,
            timezone_id=self.timezone_id,
        )

        # 3. 注入 JS
        await self.context.add_init_script(STEALTH_JS)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def get_page(self):
        """获取一个新的隐匿页面"""
        return await self.context.new_page()

    def listen_json(self, page, url_fragment, callback):
        """
        辅助工具：监听特定 URL 的 JSON 响应
        :param page: 页面对象
        :param url_fragment: URL 片段 (如 "api/qt/clist/get")
        :param callback: 接收 json 数据的回调函数
        """
        async def _async_handle(response):
            if url_fragment in response.url and response.status == 200:
                try:
                    data = await response.json()
                    callback(data)
                except Exception:
                    pass

        def _handler(response):
            asyncio.create_task(_async_handle(response))

        page.on("response", _handler)
