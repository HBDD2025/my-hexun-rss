import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta # 导入 timedelta
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import re
import platform
import os
from selenium.common.exceptions import WebDriverException

# 定义六个页面及其分类
urls = [
    {"url": "https://insurance.hexun.com/bxgsxw/index.html", "category": "和讯-公司新闻"},
    {"url": "https://insurance.hexun.com/bxjgdt/index.html", "category": "和讯-监管动态"},
    {"url": "https://insurance.hexun.com/bxhyzx/index.html", "category": "和讯-行业资讯"},
    {"url": "https://insurance.hexun.com/bxscpl/", "category": "和讯-评论与研究"},
    {"url": "https://insurance.hexun.com/2007/bxrsbd/", "category": "和讯-人事变动"},
    {"url": "https://insurance.hexun.com/bxzjyy/index.html", "category": "和讯-保险资金运用"}
]

# 设置 Selenium Chrome 选项
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

# 初始化 ChromeDriver
print(f"当前操作系统: {platform.system()}")
try:
    if platform.system() == "Darwin": # macOS
        macos_path_arm = '/opt/homebrew/bin/chromedriver'
        macos_path_intel = '/usr/local/bin/chromedriver'
        if os.path.exists(macos_path_arm):
            print(f"macOS (ARM): 使用 ChromeDriver 路径: {macos_path_arm}")
            service = Service(macos_path_arm)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        elif os.path.exists(macos_path_intel):
            print(f"macOS (Intel): 使用 ChromeDriver 路径: {macos_path_intel}")
            service = Service(macos_path_intel)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            print("macOS: 未在 Homebrew 标准路径找到 ChromeDriver, 尝试从系统 PATH 查找...")
            driver = webdriver.Chrome(options=chrome_options)
    elif platform.system() == "Linux": # GitHub Actions 通常是 Linux
        linux_path = '/usr/local/bin/chromedriver'
        if os.path.exists(linux_path):
            print(f"Linux: 使用 ChromeDriver 路径: {linux_path}")
            service = Service(linux_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            print("Linux: 未在 /usr/local/bin/chromedriver 找到驱动, 尝试从系统 PATH 查找...")
            driver = webdriver.Chrome(options=chrome_options)
    else:
        print(f"未知操作系统 ({platform.system()}), 尝试从系统 PATH 查找 ChromeDriver...")
        driver = webdriver.Chrome(options=chrome_options)
    print("ChromeDriver 初始化成功。")
except WebDriverException as e:
    print(f"错误: ChromeDriver 初始化失败。请确保 ChromeDriver 已正确安装并配置在系统 PATH 中，或者脚本中的路径指向正确。错误信息: {e}")
    exit(1)

# 初始化 RSS Feed
fg = FeedGenerator()
fg.title('和讯保险综合新闻')
fg.link(href="https://insurance.hexun.com", rel='alternate')
fg.description('和讯保险频道多个分类新闻 RSS 订阅')
fg.language('zh-CN')

all_entries = []
first_page_processed_for_html_save = False

for page_info in urls:
    url = page_info["url"]
    category = page_info["category"]
    print(f"\n正在抓取页面: {url}")
    try:
        driver.get(url)
        print(f"页面 {url} 初步加载完成，等待动态内容 (10秒)...")
        time.sleep(10)
        print(f"等待结束，获取页面源代码...")
        page_source_html = driver.page_source

        if not first_page_processed_for_html_save and page_source_html: #只保存第一个成功处理的页面的HTML用于调试
            try:
                html_to_save = f'<meta charset="UTF-8">\n{page_source_html}'
                with open("selenium_page_content.html", "w", encoding="utf-8") as f:
                    f.write(html_to_save)
                print(f"提示：第一个被抓取页面 ({url}) 的HTML内容已保存到 selenium_page_content.html 文件中。")
                first_page_processed_for_html_save = True
            except Exception as e_save:
                print(f"保存页面HTML到文件时出错: {e_save}")

        soup = BeautifulSoup(page_source_html, 'html.parser')
        news_items = soup.select('div.temp01 ul li')

        if not news_items:
            print(f"在 {url} 未找到新闻条目。选择器: 'div.temp01 ul li'")
            if not first_page_processed_for_html_save: # 如果第一个页面就没找到，也保存一下HTML
                 try:
                    html_to_save_fail = f'<meta charset="UTF-8">\n{page_source_html}'
                    with open("selenium_page_content_fail.html", "w", encoding="utf-8") as f:
                        f.write(html_to_save_fail)
                    print(f"提示：页面 {url} 未找到新闻，但其HTML内容已保存到 selenium_page_content_fail.html。")
                    first_page_processed_for_html_save = True
                 except Exception as e_save_fail:
                    print(f"保存失败页面HTML到文件时出错: {e_save_fail}")
            continue

        print(f"在 {url} 找到 {len(news_items)} 条新闻条目。")

        for item in news_items:
            title_tag = item.select_one('a')
            date_span_tag = item.select_one('span')

            if title_tag and date_span_tag and title_tag.has_attr('href'):
                title = title_tag.text.strip()
                link = title_tag['href']
                date_str_from_span = date_span_tag.text.strip()
                pub_datetime_obj_utc = datetime.now(timezone.utc)
                date_match_in_url = re.search(r'/(\d{4}-\d{2}-\d{2})/', link)
                time_match_in_span = re.search(r'(\d{2}-\d{2}\s\d{2}:\d{2})', date_str_from_span)

                if date_match_in_url and time_match_in_span:
                    year_month_day_url = date_match_in_url.group(1)
                    time_from_span_str = time_match_in_span.group(1).split(' ')[1]
                    full_date_str = f"{year_month_day_url} {time_from_span_str}"
                    try:
                        naive_dt = datetime.strptime(full_date_str, '%Y-%m-%d %H:%M')
                        pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc)
                    except ValueError as e:
                        try:
                            naive_dt = datetime.strptime(year_month_day_url, '%Y-%m-%d')
                            pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass
                elif date_match_in_url:
                    year_month_day_url = date_match_in_url.group(1)
                    try:
                        naive_dt = datetime.strptime(year_month_day_url, '%Y-%m-%d')
                        pub_datetime_obj_utc = naive_dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
                all_entries.append({
                    "title": title,
                    "link": link,
                    "pub_datetime_obj_utc": pub_datetime_obj_utc,
                    "category": category
                })
            else:
                pass
    except Exception as e:
        print(f"错误: 抓取页面 {url} 失败: {e}")
        continue

driver.quit()

all_entries.sort(key=lambda x: x["pub_datetime_obj_utc"], reverse=False)

beijing_tz = timezone(timedelta(hours=8))

for entry in all_entries:
    fe = fg.add_entry()
    fe.title(f"【{entry['category']}】 {entry['title']}")
    fe.link(href=entry['link'])
    fe.category({'term': entry['category']})
    
    utc_time_obj = entry['pub_datetime_obj_utc']
    beijing_time_obj = utc_time_obj.astimezone(beijing_tz)
    display_time_str_beijing = beijing_time_obj.strftime('%Y-%m-%d %H:%M:%S 北京时间')
    
    # 修改点：将链接文字改为 "阅读原文"
    description_text = f"<p><b>来源：</b>{entry['category']}</p>" \
                       f"<p><b>发布时间：</b>{display_time_str_beijing}</p>" \
                       f"<p><b>原始链接：</b><a href='{entry['link']}' target='_blank' rel='noopener noreferrer'>阅读原文</a></p>" \
                       f"<hr><p>{entry['title']}</p>"
    fe.description(description_text)
    
    fe.pubDate(utc_time_obj)

fg.rss_file('hexun_insurance_rss.xml', pretty=True)
print(f"\nRSS 文件已生成：hexun_insurance_rss.xml")
print(f"总共抓取 {len(all_entries)} 条新闻")
