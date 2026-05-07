from seleniumwire import webdriver # ใช้ seleniumwire ดัก Network
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

# ================== ตั้งค่า Selenium ==================
options = Options()
options.add_argument("--headless=new") # รันแบบซ่อนหน้าจอสำหรับ GitHub Actions
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--mute-audio")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # ================== 1. เข้าหน้ารวมเพื่อกวาดลิงก์ ==================
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
    print(f"กวาดลิงก์มาได้: {len(all_movie_links)} เรื่อง")

    # ================== 2. ดึงข้อมูลทีละเรื่อง ==================
    movies_data = []
    
    # วนลูป (เพื่อไม่ให้รันนานเกินไปบน GitHub อาจจะลิมิตไว้ที่ 20-30 เรื่อง หรือปล่อยรันหมดก็ได้)
    for idx, movie_url in enumerate(all_movie_links, 1):
        print(f"[{idx}/{len(all_movie_links)}] กำลังดึง: {movie_url}")
        try:
            driver.get(movie_url)
            time.sleep(12) # รอวิดีโอและ Network โหลด
            
            # ดึงชื่อและหน้าปก
            soup_detail = BeautifulSoup(driver.page_source, "html.parser")
            movie_title = "ไม่ทราบชื่อเรื่อง"
            movie_image = "https://via.placeholder.com/150"
            
            img_tag = soup_detail.find("img", class_="movie-thumb")
            if img_tag:
                movie_title = img_tag.get("alt", movie_title)
                movie_image = img_tag.get("src", movie_image)
            
            # ดักจับ m3u8
            m3u8_url = None
            for request in driver.requests:
                if request.response and request.url:
                    if ".m3u8" in request.url:
                        m3u8_url = request.url
                        break
            
            if m3u8_url:
                print(f"  -> สำเร็จ: {movie_title}")
                movies_data.append({
                    "name": movie_title,
                    "image": movie_image,
                    "url": m3u8_url
                })
            else:
                print("  -> ไม่พบลิงก์ m3u8")
                
            # เคลียร์ Network สำหรับรอบต่อไป
            del driver.requests
            
        except Exception as e:
            print(f"  -> Error: {e}")

    # ================== 3. สร้างไฟล์ JSON W3U ==================
    print(f"รวบรวมสำเร็จ {len(movies_data)} เรื่อง, กำลังสร้างไฟล์ {OUTPUT_FILE}")
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    current_date = datetime.now().strftime("%d/%m/%Y")
    
    final_data = {
        "name": f"หนังใหม่ 2026 @ {current_date}",
        "author": "Auto Update",
        "image": "https://www.123-hds.com/wp-content/uploads/2023/10/logo.png",
        "groups": [
            {
                "name": "หนังใหม่ 2026 (อัปเดตอัตโนมัติ)",
                "image": "https://www.123-hds.com/wp-content/uploads/2023/10/logo.png",
                "stations": movies_data # ใส่ข้อมูลหนังที่กวาดมาได้ตรงนี้
            }
        ]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

finally:
    driver.quit()
    print("จบการทำงาน")
