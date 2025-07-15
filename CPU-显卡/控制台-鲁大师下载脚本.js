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
  const root = document.getElementById("main-count-list-data");
  if (!root) {
    alert("未找到id为 main-count-list-data 的元素");
    return;
  }

  // 采集数据
  const rows = Array.from(root.querySelectorAll(".main-count-list"));
  const data = rows.map((row) => {
    const num =
      row.querySelector(".main-count-list-num")?.textContent.trim() || "";
    const title =
      row.querySelector(".main-count-list-code-p")?.textContent.trim() || "";
    const score =
      parseFloat(
        row.querySelector(".main-count-list-code-score")?.textContent.trim()
      ) || "";
    return { 排名: num, 标题: title, 分数: score };
  });

  if (data.length === 0) {
    alert("没有采集到数据");
    return;
  }

  // 生成sheet
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "数据");

  // 创建下载
  const wbout = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const blob = new Blob([wbout], { type: "application/octet-stream" });
  const filename = "鲁大师显卡排行数据.xlsx";

  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
})();
