from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

# ================== CONFIG ==================
MAIN_URL = "https://www.123-hds.com/%e0%b8%ab%e0%b8%99%e0%b8%b1%e0%b8%87%e0%b9%83%e0%b8%ab%e0%b8%a1%e0%b9%88-2026"
SAVE_DIR = "output"
OUTPUT_FILE = os.path.join(SAVE_DIR, "movies.txt")

# 🌟 ตั้งค่าจำนวนหน้าที่ต้องการกวาดข้อมูล (จากภาพคือมีถึงหน้า 8)
MAX_PAGE = 8 

# ฟังก์ชันสำหรับควานหาลิงก์ .m3u8 ใน Log
def extract_m3u8(logs):
    for entry in logs:
        try:
            log_data = json.loads(entry["message"])["message"]
            if log_data["method"] in ["Network.requestWillBeSent", "Network.responseReceived"]:
                req_url = ""
                if "request" in log_data["params"]:
                    req_url = log_data["params"]["request"]["url"]
                elif "response" in log_data["params"]:
                    req_url = log_data["params"]["response"]["url"]
                    
                if ".m3u8" in req_url:
                    return req_url
        except:
            continue
    return None

# ================== ตั้งค่า Selenium ==================
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--mute-audio")
options.add_argument("--disable-gpu")

options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(60)

try:
    all_movie_links = []
    
    # ================== 1. วนลูปเข้าหน้ารวมตั้งแต่หน้า 1 ถึง 8 ==================
    for page in range(1, MAX_PAGE + 1):
        # ถ้ารอบแรกคือหน้า 1 ให้ใช้ลิงก์หลัก ถ้าหน้าอื่นให้เติม /page/ตัวเลข
        page_url = MAIN_URL if page == 1 else f"{MAIN_URL}/page/{page}"
        
        print(f"กำลังกวาดลิงก์จากหน้า {page}/{MAX_PAGE}: {page_url}")
        driver.get(page_url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        halim_box = soup.find("div", class_="halim_box")
        if halim_box:
            movie_articles = halim_box.find_all("article")
            for article in movie_articles:
                a_tag = article.find("a")
                if a_tag and "href" in a_tag.attrs:
                    all_movie_links.append(a_tag["href"])
                    
    # ลบลิงก์ที่ซ้ำกัน
    all_movie_links = list(set(all_movie_links))
    print(f"\n🎉 รวมกวาดลิงก์จากทั้ง {MAX_PAGE} หน้า มาได้ทั้งหมด: {len(all_movie_links)} เรื่อง")

    movies_data = []
    
    # ================== 2. ดึงข้อมูลทีละเรื่อง ==================
    for idx, movie_url in enumerate(all_movie_links, 1):
        print(f"\n[{idx}/{len(all_movie_links)}] กำลังดึง: {movie_url}")
        try:
            driver.get(movie_url)
            time.sleep(8) 
            
            soup_detail = BeautifulSoup(driver.page_source, "html.parser")
            movie_title = "ไม่ทราบชื่อเรื่อง"
            movie_image = "https://via.placeholder.com/150"
            
            img_tag = soup_detail.find("img", class_="movie-thumb")
            if img_tag:
                movie_title = img_tag.get("alt", movie_title)
                fetched_image = img_tag.get("src", movie_image)
                
                if fetched_image.startswith("/"):
                    movie_image = "https://www.123-hds.com" + fetched_image
                else:
                    movie_image = fetched_image
            
            m3u8_url = extract_m3u8(driver.get_log("performance"))
            
            if not m3u8_url:
                iframe = soup_detail.select_one("#ajax-player iframe, .halim-player-wrapper iframe")
                
                if not iframe:
                    try:
                        driver.execute_script("let btn = document.querySelector('.halim-list-server li a'); if(btn) btn.click();")
                        time.sleep(4)
                        soup_detail = BeautifulSoup(driver.page_source, "html.parser")
                        iframe = soup_detail.select_one("#ajax-player iframe, .halim-player-wrapper iframe")
                    except:
                        pass
                
                if iframe and iframe.has_attr("src"):
                    iframe_url = iframe["src"]
                    if iframe_url.startswith("//"):
                        iframe_url = "https:" + iframe_url
                        
                    print(f"  -> กำลังเจาะเข้า Player...")
                    driver.get(iframe_url)
                    time.sleep(5)
                    
                    try:
                        driver.execute_script("let v = document.querySelector('video'); if(v) v.play(); else document.body.click();")
                        time.sleep(4)
                    except:
                        pass
                    
                    m3u8_url = extract_m3u8(driver.get_log("performance"))

            if m3u8_url:
                print(f"  -> ✅ สำเร็จ: {m3u8_url[:60]}...")
                movies_data.append({
                    "name": movie_title,
                    "image": movie_image,
                    "url": m3u8_url
                })
            else:
                print("  -> ❌ ไม่พบลิงก์ m3u8")
                
        except Exception as e:
            print(f"  -> Error: {e}")

    # ================== 3. สร้างไฟล์ JSON ==================
    print(f"\nรวบรวมสำเร็จ {len(movies_data)} เรื่อง, กำลังสร้างไฟล์ {OUTPUT_FILE}")
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    final_data = {
        "name": f"หนังใหม่ 2026 @ {current_date}",
        "author": "Auto Update 8/5/26",
        "image": "https://www.123-hds.com/wp-content/uploads/2023/10/logo.png",
        "groups": [
            {
                "name": f"หนังใหม่ 2026 (รวม {MAX_PAGE} หน้า)",
                "image": "https://www.123-hds.com/wp-content/uploads/2023/10/logo.png",
                "stations": movies_data
            }
        ]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

finally:
    driver.quit()
    print("\nจบการทำงาน!")
