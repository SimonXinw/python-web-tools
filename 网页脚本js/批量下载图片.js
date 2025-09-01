(async function() {
    'use strict';
    
    // 日志工具类
    class Logger {
        constructor() {
            this.startTime = Date.now();
        }
        
        log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const elapsed = ((Date.now() - this.startTime) / 1000).toFixed(1);
            const prefix = `[${timestamp}] [${elapsed}s]`;
            
            switch(type) {
                case 'error':
                    console.error(`${prefix} ❌ ${message}`);
                    break;
                case 'success':
                    console.log(`${prefix} ✅ ${message}`);
                    break;
                case 'warning':
                    console.warn(`${prefix} ⚠️ ${message}`);
                    break;
                default:
                    console.log(`${prefix} ℹ️ ${message}`);
            }
        }
        
        progress(current, total, message) {
            const percentage = Math.round((current / total) * 100);
            const progressBar = '█'.repeat(Math.floor(percentage / 5)) + '░'.repeat(20 - Math.floor(percentage / 5));
            this.log(`${message} [${progressBar}] ${current}/${total} (${percentage}%)`, 'info');
        }
    }
    
    // 图片下载器类
    class ImageDownloader {
        constructor() {
            this.logger = new Logger();
            this.downloadedImages = new Map();
            this.failedUrls = [];
        }
        
        // 动态加载JSZip库
        async loadJSZip() {
            this.logger.log('正在加载JSZip库...');
            
            return new Promise((resolve, reject) => {
                if (window.JSZip) {
                    this.logger.log('JSZip已存在，跳过加载', 'success');
                    resolve();
                    return;
                }
                
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
                script.onload = () => {
                    this.logger.log('JSZip库加载成功', 'success');
                    resolve();
                };
                script.onerror = () => {
                    this.logger.log('JSZip库加载失败', 'error');
                    reject(new Error('无法加载JSZip库'));
                };
                document.head.appendChild(script);
            });
        }
        
        // 提取所有图片URL
        extractImageUrls() {
            this.logger.log('开始提取页面中的图片URL...');
            
            const imageUrls = new Set();
            
            // 提取img元素
            const imgElements = document.querySelectorAll('img');
            this.logger.log(`找到 ${imgElements.length} 个img元素`);
            
            imgElements.forEach((img, index) => {
                try {
                    let src = img.src || img.getAttribute('data-src') || img.getAttribute('data-original');
                    if (src) {
                        // 去掉URL参数（?后面的内容）
                        src = src.split('?')[0];
                        
                        // 验证是否为有效的图片URL
                        if (this.isValidImageUrl(src)) {
                            imageUrls.add(src);
                            this.logger.log(`提取img[${index}]: ${src}`);
                        }
                    }
                } catch (error) {
                    this.logger.log(`处理img[${index}]时出错: ${error.message}`, 'warning');
                }
            });
            
            // 提取SVG元素
            const svgElements = document.querySelectorAll('svg');
            this.logger.log(`找到 ${svgElements.length} 个svg元素`);
            
            svgElements.forEach((svg, index) => {
                try {
                    // 将SVG转换为数据URL
                    const serializer = new XMLSerializer();
                    const svgString = serializer.serializeToString(svg);
                    const svgBlob = new Blob([svgString], { type: 'image/svg+xml' });
                    const svgUrl = URL.createObjectURL(svgBlob);
                    
                    imageUrls.add(svgUrl);
                    this.logger.log(`提取svg[${index}]: 已转换为Blob URL`);
                } catch (error) {
                    this.logger.log(`处理svg[${index}]时出错: ${error.message}`, 'warning');
                }
            });
            
            // 提取CSS背景图片
            const elementsWithBg = document.querySelectorAll('*');
            let bgImageCount = 0;
            
            elementsWithBg.forEach((element, index) => {
                try {
                    const computedStyle = window.getComputedStyle(element);
                    const bgImage = computedStyle.backgroundImage;
                    
                    if (bgImage && bgImage !== 'none') {
                        const urlMatch = bgImage.match(/url\(['"]?([^'"]+)['"]?\)/);
                        if (urlMatch) {
                            let url = urlMatch[1].split('?')[0];
                            if (this.isValidImageUrl(url)) {
                                imageUrls.add(url);
                                bgImageCount++;
                                this.logger.log(`提取背景图片[${bgImageCount}]: ${url}`);
                            }
                        }
                    }
                } catch (error) {
                    // 静默处理CSS背景图片错误，避免日志过多
                }
            });
            
            this.logger.log(`背景图片提取完成，共找到 ${bgImageCount} 个背景图片`);
            
            const urlArray = Array.from(imageUrls);
            this.logger.log(`图片URL提取完成，共找到 ${urlArray.length} 个有效图片`, 'success');
            
            return urlArray;
        }
        
        // 验证是否为有效的图片URL
        isValidImageUrl(url) {
            try {
                // 检查是否为有效URL
                new URL(url, window.location.href);
                
                // 检查文件扩展名
                const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'];
                const urlLower = url.toLowerCase();
                
                return imageExtensions.some(ext => urlLower.includes(ext)) || 
                       url.startsWith('data:image/') || 
                       url.startsWith('blob:');
            } catch {
                return false;
            }
        }
        
        // 下载单个图片
        async downloadImage(url, index, total) {
            try {
                this.logger.progress(index + 1, total, `正在下载图片`);
                
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'User-Agent': navigator.userAgent
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const blob = await response.blob();
                
                // 生成文件名
                const filename = this.generateFilename(url, index);
                
                this.downloadedImages.set(filename, blob);
                this.logger.log(`图片下载成功: ${filename} (${this.formatFileSize(blob.size)})`);
                
                return { filename, blob, success: true };
                
            } catch (error) {
                this.logger.log(`图片下载失败 [${index + 1}/${total}]: ${url} - ${error.message}`, 'error');
                this.failedUrls.push(url);
                return { url, error: error.message, success: false };
            }
        }
        
        // 生成文件名
        generateFilename(url, index) {
            try {
                const urlObj = new URL(url, window.location.href);
                let pathname = urlObj.pathname;
                
                // 如果是blob或data URL，使用索引命名
                if (url.startsWith('blob:') || url.startsWith('data:')) {
                    return `image_${index + 1}.png`;
                }
                
                // 提取文件名
                let filename = pathname.split('/').pop() || `image_${index + 1}`;
                
                // 确保有扩展名
                if (!filename.includes('.')) {
                    filename += '.jpg';
                }
                
                // 清理文件名，移除非法字符
                filename = filename.replace(/[<>:"/\\|?*]/g, '_');
                
                return filename;
                
            } catch {
                return `image_${index + 1}.jpg`;
            }
        }
        
        // 格式化文件大小
        formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        // 批量下载图片
        async downloadAllImages(urls) {
            this.logger.log(`开始批量下载 ${urls.length} 张图片...`);
            
            const downloadPromises = urls.map((url, index) => 
                this.downloadImage(url, index, urls.length)
            );
            
            // 并发下载，但限制并发数量避免浏览器崩溃
            const batchSize = 5;
            const results = [];
            
            for (let i = 0; i < downloadPromises.length; i += batchSize) {
                const batch = downloadPromises.slice(i, i + batchSize);
                const batchResults = await Promise.all(batch);
                results.push(...batchResults);
                
                // 给浏览器一点时间喘息
                if (i + batchSize < downloadPromises.length) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
            }
            
            const successCount = results.filter(r => r.success).length;
            const failCount = results.filter(r => !r.success).length;
            
            this.logger.log(`图片下载完成: 成功 ${successCount} 张，失败 ${failCount} 张`, 'success');
            
            if (failCount > 0) {
                this.logger.log(`失败的URL列表:`, 'warning');
                this.failedUrls.forEach(url => this.logger.log(`  - ${url}`, 'warning'));
            }
            
            return results;
        }
        
        // 创建ZIP文件
        async createZipFile() {
            this.logger.log('开始创建ZIP文件...');
            
            if (this.downloadedImages.size === 0) {
                throw new Error('没有成功下载的图片可以压缩');
            }
            
            const zip = new JSZip();
            
            // 添加图片到ZIP
            let addedCount = 0;
            for (const [filename, blob] of this.downloadedImages) {
                try {
                    zip.file(filename, blob);
                    addedCount++;
                    this.logger.log(`已添加到ZIP: ${filename}`);
                } catch (error) {
                    this.logger.log(`添加文件到ZIP失败: ${filename} - ${error.message}`, 'error');
                }
            }
            
            this.logger.log(`ZIP文件创建中，包含 ${addedCount} 张图片...`);
            
            // 生成ZIP文件
            const zipBlob = await zip.generateAsync({
                type: 'blob',
                compression: 'DEFLATE',
                compressionOptions: { level: 6 }
            });
            
            this.logger.log(`ZIP文件生成成功，大小: ${this.formatFileSize(zipBlob.size)}`, 'success');
            
            return zipBlob;
        }
        
        // 下载ZIP文件
        downloadZipFile(zipBlob) {
            this.logger.log('开始下载ZIP文件...');
            
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
            const siteName = window.location.hostname.replace(/[^a-zA-Z0-9]/g, '_');
            const filename = `images_${siteName}_${timestamp}.zip`;
            
            const url = URL.createObjectURL(zipBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // 清理URL对象
            setTimeout(() => URL.revokeObjectURL(url), 1000);
            
            this.logger.log(`ZIP文件下载完成: ${filename}`, 'success');
        }
        
        // 主执行函数
        async execute() {
            try {
                this.logger.log('=== 批量图片下载器启动 ===');
                this.logger.log(`当前页面: ${window.location.href}`);
                
                // 1. 加载必要的库
                await this.loadJSZip();
                
                // 2. 提取图片URL
                const imageUrls = this.extractImageUrls();
                
                if (imageUrls.length === 0) {
                    this.logger.log('页面中没有找到任何图片', 'warning');
                    return;
                }
                
                // 3. 下载所有图片
                await this.downloadAllImages(imageUrls);
                
                if (this.downloadedImages.size === 0) {
                    this.logger.log('没有成功下载任何图片', 'error');
                    return;
                }
                
                // 4. 创建ZIP文件
                const zipBlob = await this.createZipFile();
                
                // 5. 下载ZIP文件
                this.downloadZipFile(zipBlob);
                
                // 6. 显示总结
                this.showSummary();
                
            } catch (error) {
                this.logger.log(`执行过程中发生错误: ${error.message}`, 'error');
                console.error('详细错误信息:', error);
            }
        }
        
        // 显示执行总结
        showSummary() {
            const totalTime = ((Date.now() - this.logger.startTime) / 1000).toFixed(1);
            
            this.logger.log('=== 执行总结 ===');
            this.logger.log(`总耗时: ${totalTime} 秒`);
            this.logger.log(`成功下载: ${this.downloadedImages.size} 张图片`);
            this.logger.log(`下载失败: ${this.failedUrls.length} 张图片`);
            
            if (this.downloadedImages.size > 0) {
                const totalSize = Array.from(this.downloadedImages.values())
                    .reduce((sum, blob) => sum + blob.size, 0);
                this.logger.log(`总文件大小: ${this.formatFileSize(totalSize)}`);
                this.logger.log('ZIP文件已开始下载', 'success');
            }
            
            this.logger.log('=== 批量图片下载器完成 ===');
        }
    }
    
    // 兼容性检查
    function checkCompatibility() {
        const logger = new Logger();
        
        if (!window.fetch) {
            logger.log('浏览器不支持fetch API', 'error');
            return false;
        }
        
        if (!window.URL || !window.URL.createObjectURL) {
            logger.log('浏览器不支持URL API', 'error');
            return false;
        }
        
        if (!window.Blob) {
            logger.log('浏览器不支持Blob API', 'error');
            return false;
        }
        
        logger.log('浏览器兼容性检查通过', 'success');
        return true;
    }
    
    // 主执行逻辑
    if (!checkCompatibility()) {
        console.error('❌ 浏览器兼容性检查失败，无法执行脚本');
        return;
    }
    
    // 确认执行
    if (!confirm('确定要下载当前页面的所有图片并打包成ZIP吗？\n\n注意：\n- 这可能需要一些时间\n- 会消耗网络流量\n- 请确保页面已完全加载')) {
        console.log('ℹ️ 用户取消了操作');
        return;
    }
    
    // 创建下载器实例并执行
    const downloader = new ImageDownloader();
    await downloader.execute();
    
})();
