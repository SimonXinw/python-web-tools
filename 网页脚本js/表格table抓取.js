(function () {

    // 假设我们要抓取的第一个表格就是目标表格
    var rows = document.querySelectorAll('body table tbody tr');

    // 存储表格数据
    var data = [];

    // 遍历表格的行
    for (var i = 1; i < rows.length; i++) { // 从1开始，跳过表头
        var row = rows[i];
        var rowData = [];
        // 遍历单元格
        for (var j = 0; j < row.cells.length; j++) {
            rowData.push(row.cells[j].textContent || row.cells[j].innerText);
        }
        // 将行数据添加到数据数组
        data.push(rowData);
    }

    // 将数据转换为CSV格式
    var csvContent = "data:text/csv;charset=utf-8,";
    data.forEach(function (rowArray) {
        var row = rowArray.join(",");
        csvContent += row + "\r\n";
    });

    // 创建虚拟链接用于下载
    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "table_data.csv"); // 设置下载文件名

    // 模拟点击链接进行下载
    link.click();
})();