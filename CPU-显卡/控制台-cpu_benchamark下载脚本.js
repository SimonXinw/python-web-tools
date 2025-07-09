(async function () {
  // 动态插入 SheetJS
  if (!window.XLSX) {
    await new Promise((resolve) => {
      let script = document.createElement("script");
      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
      script.onload = resolve;
      document.body.appendChild(script);
    });
  }

  // 获取主列表容器
  const root = document.getElementById("mark");

  if (!root) {
    return alert("未找到 root 元素");
  }

  // 采集数据
  const rows = Array.from(root.querySelectorAll(".chartlist li"));

  rows.forEach((row) => {
    row.querySelector(".more_details")?.click();
  });

  await new Promise((resolve) => setTimeout(resolve, 320));

  // 采集新数据
  const newRows = Array.from(root.querySelectorAll(".chartlist li"));

  const data = newRows.map((row) => {
    // 提取 Rank: 后面的数字
    let num = "";
    const rowDetails = row.querySelector(".row_details");

    if (rowDetails) {
      const match = rowDetails.innerHTML.match(/Rank:\s*(\d+)/);
      num = match ? match[1] : "";
    }

    const title = row.querySelector(".prdname")?.textContent.trim() || "";

    // 兼容带逗号的数字格式
    const scoreText = row.querySelector(".count")?.textContent.trim().replace(/,/g, "");
    
    const score = scoreText ? parseFloat(scoreText) : "";

    return { 排名: num, 标题: title, 分数: score };
  });

  if (data.length === 0) {
    return alert("没有采集到数据");
  }

  // 生成sheet
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "数据");

  // 创建下载
  const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const blob = new Blob([wbout], { type: "application/octet-stream" });
  const filename = "cpu_benchamark数据.xlsx";

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
})();
