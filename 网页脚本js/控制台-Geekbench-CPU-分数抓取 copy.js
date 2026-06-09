(function () {
    // 1. 抓取数据
    const rows = document.querySelectorAll('.tab-content .active tbody tr');
    const data = [['名称', '分数', '核心']]; // 表头

    rows.forEach(row => {
        const name = row.querySelector('.name a').innerText;
        const core = row.querySelector('.name .description').innerText;
        const score = row.querySelector('.score').innerText;
        data.push([name, score, core]);
    });

    // 2. 引入SheetJS库
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.17.0/xlsx.full.min.js';
    script.onload = () => {
        // 3. 数据转化为Excel文件
        const ws = XLSX.utils.aoa_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');

        // 4. 下载Excel文件
        XLSX.writeFile(wb, 'Geekbench Browser.xlsx');
    };
    document.head.appendChild(script);
})()