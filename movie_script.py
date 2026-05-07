from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

# ================== CONFIG ==================
MAIN_URL = "https://www.123-hds.com/%e0%b8%ab%e0%b8%99%e0%b8%b1%e0%b8%87%e0%b9%83%e0%b8%ab%e0%b8%a1%e0%b9%88-2026"
SAVE_DIR = "output"
OUTPUT_FILE = os.path.join(SAVE_DIR, "movies.txt")

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

# 🌟 1. เพิ่ม User-Agent ปลอมตัวเป็นคอมพิวเตอร์ทั่วไป (หลบการบล็อก Bot)
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.set_page_load_timeout(60)

try:
    # ================== เข้าหน้ารวม ==================
    print(f"กำลังเข้าหน้ารวม: {MAIN_URL}")
    driver.get(MAIN_URL)
    time.sleep(5)
    
    soup = BeautifulSoup(driver.page_source, "html.parser")
    all_movie_links = []
    
    halim_box = soup.find("div", class_="halim_box")
    if halim_box:
        movie_articles = halim_box.find_all("article")
        for article in movie_articles:
            a_tag = article.find("a")
            if a_tag and "href" in a_tag.attrs:
                all_movie_links.append(a_tag["href"])
                
    all_movie_links = list(set(all_movie_links))
    print(f"กวาดลิงก์มาได้ทั้งหมด: {len(all_movie_links)} เรื่อง")

    movies_data = []
    
    # ================== ดึงข้อมูลทีละเรื่อง ==================
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
                movie_image = img_tag.get("src", movie_image)
            
            m3u8_url = extract_m3u8(driver.get_log("performance"))
            
            # 🌟 2. ท่าไม้ตาย: ถ้าไม่เจอ m3u8 ให้เจาะเข้าไปหา iframe ของ Player
            if not m3u8_url:
                iframe = soup_detail.select_one("#ajax-player iframe, .halim-player-wrapper iframe")
                
                # ถ้ายังไม่มี iframe โผล่มา ลองจำลองการคลิกเลือกเซิร์ฟเวอร์
                if not iframe:
                    try:
                        driver.execute_script("let btn = document.querySelector('.halim-list-server li a'); if(btn) btn.click();")
                        time.sleep(4)
                        soup_detail = BeautifulSoup(driver.page_source, "html.parser")
                        iframe = soup_detail.select_one("#ajax-player iframe, .halim-player-wrapper iframe")
                    except:
                        pass
                
                # 🌟 3. เข้าไปที่หน้าเว็บของ Player โดยตรง (เพื่อตัดโฆษณากวนใจ)
                if iframe and iframe.has_attr("src"):
                    iframe_url = iframe["src"]
                    if iframe_url.startswith("//"):
                        iframe_url = "https:" + iframe_url
                        
                    print(f"  -> กำลังเจาะเข้า Player...")
                    driver.get(iframe_url)
                    time.sleep(5)
                    
                    # 🌟 4. จำลองการกดปุ่ม Play เผื่อวิดีโอรอให้คลิกก่อนถึงจะโหลด m3u8
                    try:
                        driver.execute_script("let v = document.querySelector('video'); if(v) v.play(); else document.body.click();")
                        time.sleep(4)
                    except:
                        pass
                    
                    # ค้นหาใน Log อีกรอบ
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

    # ================== สร้างไฟล์ JSON ==================
    print(f"\nรวบรวมสำเร็จ {len(movies_data)} เรื่อง, กำลังสร้างไฟล์ {OUTPUT_FILE}")
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    final_data = {
        "name": f"หนังใหม่ 2026 @ {current_date}",
        "author": "Auto Update",
        "image": "https://www.123-hds.com/wp-content/uploads/2023/10/logo.png",
        "groups": [
            {
                "name": "หนังใหม่ 2026",
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
