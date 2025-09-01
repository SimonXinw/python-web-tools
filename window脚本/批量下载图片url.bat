@echo off
setlocal enabledelayedexpansion

:: 新建 data 文件夹
if not exist "data" mkdir data

:: 问题1：set urls=^ 这样写，for %%u in (%urls%) do 实际上会把所有URL当成一个整体参数，不能逐个遍历
:: 问题2：URL带引号，%%~u 取出来会带引号，后续处理会有问题
:: 问题3：文件名提取逻辑复杂且容易出错
:: 问题4：curl 不是所有Windows自带，需确保已安装

:: 推荐写法：用文本文件保存URL列表，逐行读取
:: 下面是修正建议

:: 1. 先将所有URL写入 data_urls.txt
:: 2. 用for /f逐行读取并下载

:: 写入URL到data_urls.txt（只需运行一次，后续可注释掉）
(
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_banner_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_service_icon_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_service_icon_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_service_icon_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_service_icon_4.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_slider_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_card_icon_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_card_icon_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_card_icon_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_card_icon_4.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_slider_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/product_slider_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/media_report_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/media_report_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/media_report_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/media_report_4.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/moments_banner_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/image_with_text_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/user_avatar_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/user_avatar_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/user_avatar_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_gallary_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_gallary_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_gallary_logo_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_gallary_logo_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_news_1.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_news_2.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_news_3.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/homepage_news_4.webp
echo https://cdn.shopify.com/s/files/1/0676/9170/8603/files/arrow_right.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/socail_icons.webp
echo https://simon-plus-xinwang.myshopify.com/cdn/shop/files/footer_icons.webp
echo https://cdn.shopify.com/shopifycloud/preview-bar/assets/us.svg
) > data_urls.txt

:: 逐行读取并下载
for /f "usebackq delims=" %%u in ("data_urls.txt") do (
    set "url=%%u"
    for %%b in ("!url!") do set "full_filename=%%~nxb"
    for /f "tokens=1 delims=?" %%f in ("!full_filename!") do set "filename=%%f"
    echo Downloading !url! -> data\!filename!
    curl -L "!url!" -o "data\!filename!"
)

echo All downloads complete.
pause

:: 总结主要问题：
:: 1. 原脚本for循环不能正确遍历所有URL
:: 2. URL带引号，变量处理容易出错
:: 3. 建议用文本文件存储URL，逐行读取更安全
:: 4. curl需确保已安装
