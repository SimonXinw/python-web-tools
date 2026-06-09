import os
import time
import asyncio
import random
import threading
from datetime import datetime
from urllib.parse import quote

import pandas as pd
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from playwright_utils import get_profile_dir, USER_AGENT, LOGIN_URL

# 并发开关：True 时启用多标签页并发；False 时单标签页顺序执行
ENABLE_CONCURRENT = True
CONCURRENT_WORKERS = 3

SCHOOL_NAME_SELECTOR = (
    ".head-search_schoolSearchItem__vOFho .head-search_schoolName__2ozme em"
)


class MajorsScraper:
    def __init__(
        self,
        school_name_excel_path,
        js_script_path,
        save_majors_excel_path,
        base_dir,
        enable_concurrent=ENABLE_CONCURRENT,
        concurrent_workers=CONCURRENT_WORKERS,
    ):
        self.school_name_excel_path = school_name_excel_path
        self.js_script_path = js_script_path
        self.save_majors_excel_path = save_majors_excel_path
        self.base_dir = base_dir
        self.enable_concurrent = enable_concurrent
        self.concurrent_workers = max(1, concurrent_workers if enable_concurrent else 1)

        self.df = None
        self.majors_df = None
        self.js_code = None
        self._save_lock = threading.Lock()

    def _init_read_school_name_excel(self):
        self.df = pd.read_excel(self.school_name_excel_path)
        if "状态" not in self.df.columns:
            self.df["状态"] = ""
        self.df["状态"] = self.df["状态"].fillna("").astype(str)

    def _init_js_script(self):
        with open(self.js_script_path, "r", encoding="utf-8") as f:
            self.js_code = f.read()

    def _init_read_majors_excel(self):
        if os.path.exists(self.save_majors_excel_path):
            self.majors_df = pd.read_excel(self.save_majors_excel_path)
        else:
            self.majors_df = pd.DataFrame()
            self.majors_df.to_excel(
                self.save_majors_excel_path, index=False, header=False
            )

    def _build_search_url(self, school_name):
        return f"https://www.gaokao.cn/headSearch?search={school_name}"

    def _save_status(self, row_index, status):
        with self._save_lock:
            self.df.at[row_index, "状态"] = status
            self.df.to_excel(self.school_name_excel_path, index=False)

    def _append_majors_result(self, school_majors_data):
        with self._save_lock:
            python_2d_list = [list(row) for row in school_majors_data]
            new_df = pd.DataFrame(python_2d_list)
            self.majors_df = pd.concat([self.majors_df, new_df], ignore_index=True)
            self.majors_df.to_excel(
                self.save_majors_excel_path, index=False, header=False
            )

    async def _wait_for_element(self, page, selector, timeout_ms=4000):
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            print(f"等待元素 {selector} 超时")
            return False

    async def _init_worker_pages(self, context, login_page):
        """登录后创建 worker 标签页（同一浏览器窗口内的多个 tab）"""
        worker_pages = []

        for worker_id in range(self.concurrent_workers):
            if worker_id == 0:
                page = login_page
            else:
                page = await context.new_page()
                await page.goto(LOGIN_URL, wait_until="domcontentloaded")
                await page.evaluate(
                    f"document.title = '[Worker {worker_id + 1}] 掌上高考'"
                )

            worker_pages.append(page)
            print(f"  - Worker {worker_id + 1} 标签页已就绪")

        print(
            f"【浏览器】当前同一窗口内共 {len(context.pages)} 个标签页 "
            f"（请查看浏览器顶部标签栏，不是 3 个独立窗口）"
        )
        return worker_pages

    async def _scrape_school(self, page, row_index, school_name, worker_id):
        url = self._build_search_url(school_name)
        school_page = None

        try:
            await page.bring_to_front()
            await asyncio.sleep(random.uniform(0.3, 0.8))
            await page.goto(url, wait_until="domcontentloaded")

            current_url = page.url
            encoded_url = quote(url, safe=":/?=")
            if encoded_url not in current_url:
                print(
                    f"[W{worker_id}] 页面跳转失败，被重定向：{url} -> {current_url}"
                )
                self._save_status(row_index, "失败")
                return

            if not await self._wait_for_element(page, SCHOOL_NAME_SELECTOR, 8000):
                print(f"[W{worker_id}] 加载失败，找不到院校名称元素: {school_name}")
                self._save_status(row_index, "失败")
                return

            await asyncio.sleep(random.uniform(0.1, 0.3))

            school_item = page.locator(".head-search_schoolSearchItem__vOFho").first
            school_name_element = school_item.locator(
                ".head-search_schoolName__2ozme em span"
            ).first
            matched_name = (await school_name_element.inner_text()).strip()

            if matched_name != school_name:
                print(
                    f"[W{worker_id}] 搜索结果名称不匹配：页面「{matched_name}」，"
                    f"Excel「{school_name}」"
                )
                self._save_status(row_index, "失败")
                return

            async with page.context.expect_page() as new_page_info:
                await school_name_element.click()

            school_page = await new_page_info.value
            await school_page.wait_for_selector(
                ".school-tab_tabNavs__1wdWg img", timeout=6000
            )
            await school_page.evaluate(self.js_code)
            await school_page.wait_for_selector(
                "#schoolMajorsExcelDataStatus", timeout=64000
            )

            school_majors_data = await school_page.evaluate(
                "() => window.schoolMajorsExcelData"
            )
            self._append_majors_result(school_majors_data)
            self._save_status(row_index, "成功")
            print(f"[W{worker_id}] 成功 | 行号 {row_index} | {school_name}")

        except PlaywrightTimeoutError as err:
            self._save_status(row_index, "失败")
            print(f"[W{worker_id}] 超时 | 行号 {row_index} | {school_name} | {err}")
        except Exception as err:
            self._save_status(row_index, "失败")
            print(f"[W{worker_id}] 出错 | 行号 {row_index} | {school_name} | {err}")
        finally:
            if school_page and not school_page.is_closed():
                await school_page.close()
            print(
                f"[W{worker_id}] 完成 | 行号 {row_index} | "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

    async def _worker(self, worker_id, page, queue):
        while True:
            try:
                row_index, school_name = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            await self._scrape_school(page, row_index, school_name, worker_id)

    async def _run_async(self):
        start_time = time.time()

        self._init_js_script()
        self._init_read_majors_excel()
        self._init_read_school_name_excel()

        pending_tasks = [
            (index, str(row["院校名称"]).strip())
            for index, row in self.df.iterrows()
            if str(row.get("状态", "")).strip() != "成功"
            and str(row["院校名称"]).strip()
            and str(row["院校名称"]).strip().lower() != "nan"
        ]

        if not pending_tasks:
            print("没有待爬取的院校。")
            return

        profile_dir = get_profile_dir(self.base_dir)
        os.makedirs(profile_dir, exist_ok=True)

        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                user_agent=USER_AGENT,
                ignore_https_errors=True,
                viewport={"width": 1280, "height": 900},
            )

            login_page = context.pages[0] if context.pages else await context.new_page()
            print("=" * 56)
            print("浏览器已打开（有头模式）。")
            print("请在浏览器中完成登录（扫码 / 账号均可）。")
            print("登录完成后，回到此终端按【回车键】继续爬取...")
            print("=" * 56)
            await login_page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await login_page.evaluate("document.title = '[Worker 1] 掌上高考'")
            await asyncio.to_thread(input)

            print(f"\n正在打开 {self.concurrent_workers} 个并发标签页...")
            worker_pages = await self._init_worker_pages(context, login_page)

            queue = asyncio.Queue()
            for task in pending_tasks:
                await queue.put(task)

            mode_text = (
                f"并发 {self.concurrent_workers} 标签页"
                if self.enable_concurrent
                else "单标签页顺序执行"
            )
            print(f"开始爬取，共 {len(pending_tasks)} 所院校，模式：{mode_text}")

            workers = [
                asyncio.create_task(
                    self._worker(worker_id + 1, worker_pages[worker_id], queue)
                )
                for worker_id in range(self.concurrent_workers)
            ]
            await asyncio.gather(*workers)

            for page in worker_pages[1:]:
                if not page.is_closed():
                    await page.close()

            await context.close()

        end_time = time.time()
        print(
            f"脚本全部执行完成 >>>>>>>>> 处理总用时: {end_time - start_time:.2f} 秒"
        )

    def run(self):
        asyncio.run(self._run_async())


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))

    school_name_excel_path = os.path.join(current_dir, "还需要爬取的院校.xlsx")
    js_script_path = os.path.join(current_dir, "控制台-中国教育-学校专业组.js")
    save_majors_excel_path = os.path.join(current_dir, "院校招生专业组专业明细.xlsx")

    scraper = MajorsScraper(
        school_name_excel_path=school_name_excel_path,
        js_script_path=js_script_path,
        save_majors_excel_path=save_majors_excel_path,
        base_dir=current_dir,
        enable_concurrent=ENABLE_CONCURRENT,
        concurrent_workers=CONCURRENT_WORKERS,
    )
    scraper.run()
