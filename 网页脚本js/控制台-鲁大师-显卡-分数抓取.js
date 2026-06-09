(function () {
    // 1. 抓取数据
    const rows = document.querySelectorAll('#main-count-list-data .main-count-list .main-count-list-code');
    const data = [['名称', '分数']]; // 表头

    rows.forEach(row => {
        const name = row.querySelector('.main-count-list-code-p').innerText;
        const score = row.querySelector('.main-count-list-code-score').innerText;
        data.push([name, score]);
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
        XLSX.writeFile(wb, '鲁大师显卡.xlsx');
    };
    document.head.appendChild(script);
})()