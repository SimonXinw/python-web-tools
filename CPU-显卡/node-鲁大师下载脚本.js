const puppeteer = require("puppeteer");
const fs = require("fs");
const path = require("path");
const XLSX = require("xlsx");

(async () => {
  // 启动浏览器
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  // 打开目标页面
  await page.goto("https://www.ludashi.com/rank/index.html", { timeout: 0 });

  // 等待主列表数据元素出现
  await page.waitForSelector("#main-count-list-data .main-count-list");

  // 抓取数据
  const data = await page.evaluate(() => {
    const rows = Array.from(
      document.querySelectorAll("#main-count-list-data .main-count-list")
    );
    return rows.map((row) => {
      const num =
        row.querySelector(".main-count-list-num")?.textContent.trim() || "";
      const title =
        row.querySelector(".main-count-list-code-p")?.textContent.trim() || "";
      const score =
        row.querySelector(".main-count-list-code-score")?.textContent.trim() ||
        "";
      return { 排名: num, 标题: title, 分数: score };
    });
  });

  // 处理为 xlsx
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "数据");

  // 动态文件名
  const fileName = `主列表数据_${Date.now()}.xlsx`;
  const filePath = path.resolve(__dirname, fileName);

  XLSX.writeFile(wb, filePath);

  console.log("✅ 抓取成功，文件已保存:", filePath);

  await browser.close();
})();
