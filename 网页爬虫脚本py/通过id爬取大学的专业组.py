import os
import time
import random

import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_utils import launch_browser, wait_for_manual_login


class MajorsScraper:
    def __init__(
        self,
        gaokao_id_excel_path,
        js_script_path,
        save_majors_excel_path,
        base_dir,
    ):
        self.gaokao_id_excel_path = gaokao_id_excel_path
        self.js_script_path = js_script_path
        self.save_majors_excel_path = save_majors_excel_path
        self.base_dir = base_dir
        self.df = None
        self.majors_df = None
        self.gaokao_code = None
        self.school_name = None
        self.row_index = None
        self.url = None
        self.page = None
        self.context = None
        self.playwright = None
        self.js_code = None

    def _init_read_gaokao_id_map_excel(self):
        self.df = pd.read_excel(self.gaokao_id_excel_path)

    def find_row(self, index):
        row = self.df.loc[index]
        self.school_name = row["院校名称"]

        if "代码" in self.df.columns:
            self.gaokao_code = row["代码"]
        elif "高考教育映射代码" in self.df.columns:
            self.gaokao_code = row["高考教育映射代码"]
        else:
            raise KeyError("Excel 中缺少「代码」或「高考教育映射代码」列")

    def prepare_url(self):
        if self.gaokao_code is not None:
            self.url = f"https://www.gaokao.cn/school/{self.gaokao_code}/provinceline"

    def _init_browser(self):
        self.playwright = sync_playwright().start()
        self.context, self.page = launch_browser(self.playwright, self.base_dir)
        wait_for_manual_login(self.page)

    def _init_js_script(self):
        with open(self.js_script_path, "r", encoding="utf-8") as f:
            self.js_code = f.read()

    def _init_read_majors_excel(self):
        if os.path.exists(self.save_majors_excel_path):
            self.majors_df = pd.read_excel(self.save_majors_excel_path)
        else:
            self.majors_df = pd.DataFrame()
            self.majors_df.to_excel(self.save_majors_excel_path, index=False, header=False)

    def _wait_for_element(self, selector, timeout_ms=4000):
        try:
            self.page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except PlaywrightTimeoutError:
            print(f"等待元素 {selector} 超时")
            return False

    def scrape_web(self):
        try:
            time.sleep(random.uniform(0.3, 0.8))

            self.page.goto(self.url, wait_until="domcontentloaded")
            current_url = self.page.url.split("?")[0]

            if current_url != self.url:
                print(f"页面跳转失败，页面被重定向了：{self.url} -> {current_url}")
                return

            major_table_selector = "#zs_plan .province_score_line_table table tbody tr td"

            if not self._wait_for_element(major_table_selector, 4000):
                self.df.at[self.row_index, "状态"] = "失败"
                print("未找到专业组单元格，等待超时或其他错误")
                return

            self.page.evaluate(self.js_code)
            self.page.wait_for_selector("#schoolMajorsExcelDataStatus", timeout=36000)

            self.school_majors_data = self.page.evaluate(
                "() => window.schoolMajorsExcelData"
            )

            self._save_majors_result()
            self.df.at[self.row_index, "状态"] = "成功"

        except PlaywrightTimeoutError as e:
            self.df.at[self.row_index, "状态"] = "失败"
            print(f"处理URL时超时：{self.url}，错误信息：{e}")
        except Exception as e:
            self.df.at[self.row_index, "状态"] = "失败"
            print(f"处理URL时出错：{self.url}，错误信息：{e}")
        finally:
            self.save_gaokao_map_id_excel()

    def save_gaokao_map_id_excel(self):
        self.df.to_excel(self.gaokao_id_excel_path, index=False, header=False)

    def _save_majors_result(self):
        python_2d_list = [list(row) for row in self.school_majors_data]
        new_df = pd.DataFrame(python_2d_list)
        self.majors_df = pd.concat([self.majors_df, new_df], ignore_index=True)
        self.majors_df.to_excel(self.save_majors_excel_path, index=False, header=False)

    def run(self):
        self._init_read_gaokao_id_map_excel()
        self._init_browser()
        self._init_js_script()
        self._init_read_majors_excel()

        try:
            for index, row in self.df.iterrows():
                if row["状态"] != "成功":
                    self.row_index = index
                    self.find_row(index)
                    self.prepare_url()
                    self.scrape_web()
                    print(
                        f"处理行号: {self.row_index}, 学校名称: {self.school_name}, "
                        f"院校代码: {self.gaokao_code}"
                    )

            self.save_gaokao_map_id_excel()
            print("所有未成功的行已处理完成并保存。")
        finally:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))

    gaokao_id_excel_path = os.path.join(current_dir, "高考教育院校id_map_表.xlsx")
    js_script_path = os.path.join(current_dir, "控制台-中国教育-学校专业组.js")
    save_majors_excel_path = os.path.join(current_dir, "院校招生专业组专业明细.xlsx")

    scraper = MajorsScraper(
        gaokao_id_excel_path,
        js_script_path,
        save_majors_excel_path,
        current_dir,
    )
    scraper.run()
