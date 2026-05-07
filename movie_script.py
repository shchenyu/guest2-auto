from seleniumwire import webdriver
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
# เปลี่ยนจาก --headless=new กลับมาใช้ตัวปกติเพื่อความเสถียรกับ selenium-wire
options.add_argument("--headless") 
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--mute-audio")

# 🌟 ปิดระบบความปลอดภัยและกราฟิกที่ทำให้ Chrome ปฏิเสธ Proxy บน GitHub Actions
options.add_argument("--disable-gpu")
options.add_argument("--disable-software-rasterizer")
options.add_argument("--disable-web-security")
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors")
options.add_argument("--allow-insecure-localhost")

service = Service(ChromeDriverManager().install())

# 🌟 ตั้งค่า selenium-wire เพิ่มเติม
sw_options = {
    'verify_ssl': False,
    'suppress_connection_errors': True,
    'enable_har': False, # ปิดโหมดเก็บประวัติแบบละเอียดเพื่อประหยัด RAM บน GitHub
    'connection_timeout': 30 # เพิ่มเวลาเชื่อมต่อ ป้องกันเน็ตเซิร์ฟเวอร์ช้า
}

driver = webdriver.Chrome(service=service, options=options, seleniumwire_options=sw_options)
# ตั้งเวลา Time Out ให้หน้าเว็บโหลด
driver.set_page_load_timeout(60)

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
    print(f"กวาดลิงก์มาได้ทั้งหมด: {len(all_movie_links)} เรื่อง")

    # ================== 2. ดึงข้อมูลทีละเรื่อง ==================
    movies_data = []
    
    for idx, movie_url in enumerate(all_movie_links, 1):
        print(f"\n[{idx}/{len(all_movie_links)}] กำลังดึง: {movie_url}")
        try:
            driver.get(movie_url)
            time.sleep(15) 
            
            # --- ดึงชื่อหนังและหน้าปก ---
            soup_detail = BeautifulSoup(driver.page_source, "html.parser")
            movie_title = "ไม่ทราบชื่อเรื่อง"
            movie_image = "https://via.placeholder.com/150"
            
            img_tag = soup_detail.find("img", class_="movie-thumb")
            if img_tag:
                movie_title = img_tag.get("alt", movie_title)
                movie_image = img_tag.get("src", movie_image)
            
            # --- ดักจับลิงก์ m3u8 เบื้องหลัง ---
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
                
            # เคลียร์ประวัติ Network สำหรับรอบต่อไป (สำคัญมาก)
            del driver.requests
            
        except Exception as e:
            print(f"  -> Error เกิดข้อผิดพลาดกับลิงก์นี้: {e}")

    # ================== 3. สร้างไฟล์ JSON (W3U) ==================
    print(f"\nรวบรวมสำเร็จ {len(movies_data)} เรื่อง, กำลังสร้างไฟล์ {OUTPUT_FILE}")
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
                "stations": movies_data
            }
        ]
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

finally:
    driver.quit()
    print("\nจบการทำงาน!")
