(function () {
    // 1. 抓取数据
    const rows = document.querySelectorAll('body table tbody tr');
    const data = [[]]; // 表头

    rows.forEach((row, index) => {

        if (index === 0) {
            const cols = row.querySelectorAll('td');

            for (let col of cols) {
                data[0].push(col.innerHTML);
            }

            return;
        }

        const cols = row.querySelectorAll('td');

        data[index] = []

        for (let col of cols) {
            data[index].push(col.innerHTML);
        }
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

