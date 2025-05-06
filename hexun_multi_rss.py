import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import re

# 定义六个页面及其分类
urls = [
    {"url": "https://insurance.hexun.com/bxgsxw/index.html", "category": "和讯-公司新闻"},
    {"url": "https://insurance.hexun.com/bxjgdt/index.html", "category": "和讯-监管动态"},
    {"url": "https://insurance.hexun.com/bxhyzx/index.html", "category": "和讯-行业资讯"},
    {"url": "https://insurance.hexun.com/bxscpl/", "category": "和讯-评论与研究"},
    {"url": "https://insurance.hexun.com/2007/bxrsbd/", "category": "和讯-人事变动"},
    {"url": "https://insurance.hexun.com/bxzjyy/index.html", "category": "和讯-保险资金运用"}
]

# ... (中间的代码和之前一样，保持不变) ...
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")

service = Service('/opt/homebrew/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)

fg = FeedGenerator()
fg.title('和讯保险综合新闻')
fg.link(href="https://insurance.hexun.com", rel='alternate')
fg.description('和讯保险频道多个分类新闻 RSS 订阅')
fg.language('zh-CN')

all_entries = []

for page_info in urls:
    url = page_info["url"]
    category = page_info["category"]
    print(f"\n正在抓取页面: {url}")
    try:
        driver.get(url)
        time.sleep(10) # 增加等待时间
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        news_items = soup.select('div.temp01 ul li')

        if not news_items:
            print(f"在 {url} 未找到新闻条目。选择器: 'div.temp01 ul li'")
            continue

        print(f"在 {url} 找到 {len(news_items)} 条新闻条目。")

        for item in news_items:
            title_tag = item.select_one('a')
            date_span_tag = item.select_one('span')

            if title_tag and date_span_tag and title_tag.has_attr('href'):
                title = title_tag.text.strip()
                link = title_tag['href']
                date_str_from_span = date_span_tag.text.strip()
                pub_datetime_obj = datetime.now(timezone.utc)
                date_match_in_url = re.search(r'/(\d{4}-\d{2}-\d{2})/', link)
                time_match_in_span = re.search(r'(\d{2}-\d{2}\s\d{2}:\d{2})', date_str_from_span)

                if date_match_in_url and time_match_in_span:
                    year_month_day_url = date_match_in_url.group(1)
                    time_from_span_str = time_match_in_span.group(1).split(' ')[1]
                    full_date_str = f"{year_month_day_url} {time_from_span_str}"
                    try:
                        naive_dt = datetime.strptime(full_date_str, '%Y-%m-%d %H:%M')
                        pub_datetime_obj = naive_dt.replace(tzinfo=timezone.utc)
                    except ValueError as e:
                        try:
                            naive_dt = datetime.strptime(year_month_day_url, '%Y-%m-%d')
                            pub_datetime_obj = naive_dt.replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass
                elif date_match_in_url:
                    year_month_day_url = date_match_in_url.group(1)
                    try:
                        naive_dt = datetime.strptime(year_month_day_url, '%Y-%m-%d')
                        pub_datetime_obj = naive_dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass
                all_entries.append({
                    "title": title,
                    "link": link,
                    "pub_datetime_obj": pub_datetime_obj,
                    "category": category
                })
            else:
                pass
    except Exception as e:
        print(f"错误: 抓取页面 {url} 失败: {e}")
        continue

driver.quit()

# --- 修改点在这里 ---
all_entries.sort(key=lambda x: x["pub_datetime_obj"], reverse=False) # 改为 False
# --- 修改点结束 ---

for entry in all_entries:
    fe = fg.add_entry()
    fe.title(f"【{entry['category']}】 {entry['title']}")
    fe.link(href=entry['link'])
    fe.description(entry['title'])
    fe.pubDate(entry['pub_datetime_obj'])

fg.rss_file('hexun_insurance_rss.xml', pretty=True)
print(f"\nRSS 文件已生成：hexun_insurance_rss.xml")
print(f"总共抓取 {len(all_entries)} 条新闻")
