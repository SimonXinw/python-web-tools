import os

from playwright.sync_api import Playwright


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

LOGIN_URL = "https://www.gaokao.cn"
PROFILE_DIR_NAME = ".playwright_gaokao_profile"


def get_profile_dir(base_dir):
    return os.path.join(base_dir, PROFILE_DIR_NAME)


def launch_browser(playwright: Playwright, base_dir):
    """有头模式启动浏览器，并复用登录态目录。"""
    profile_dir = get_profile_dir(base_dir)
    os.makedirs(profile_dir, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        user_agent=USER_AGENT,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 900},
    )

    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def wait_for_manual_login(page):
    """打开首页并暂停，等待用户在浏览器中手动登录。"""
    print("=" * 56)
    print("浏览器已打开（有头模式）。")
    print("请在浏览器中完成登录（扫码 / 账号均可）。")
    print("若页面弹出登录框，请先登录，不要关闭浏览器。")
    print("登录完成后，回到此终端按【回车键】继续爬取...")
    print("=" * 56)

    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    input()
