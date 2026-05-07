from selenium import webdriver # ใช้ selenium ธรรมดา
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
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--mute-audio")
options.add_argument("--disable-gpu")

# 🌟 ท่าไม้ตาย: เปิดการบันทึก Log ของ Network เพื่อดักจับลิงก์เบื้องหลัง (ไม่ต้องง้อ selenium-wire)
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
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
            time.sleep(15) # รอให้วิดีโอและ Network โหลด m3u8 ขึ้นมา
            
            # --- ดึงชื่อหนังและหน้าปก ---
            soup_detail = BeautifulSoup(driver.page_source, "html.parser")
            movie_title = "ไม่ทราบชื่อเรื่อง"
            movie_image = "https://via.placeholder.com/150"
            
            img_tag = soup_detail.find("img", class_="movie-thumb")
            if img_tag:
                movie_title = img_tag.get("alt", movie_title)
                movie_image = img_tag.get("src", movie_image)
            
            # --- 🌟 ดักจับลิงก์ m3u8 จาก Network Logs ของ Chrome โดยตรง ---
            m3u8_url = None
            logs = driver.get_log("performance") # ดึง log ออกมา (และมันจะเคลียร์ของเก่าให้ด้วยในตัว)
            
            for entry in logs:
                try:
                    log_data = json.loads(entry["message"])["message"]
                    
                    # เช็คตอนที่ Browser เริ่มส่ง Request หรือได้รับ Response
                    if log_data["method"] in ["Network.requestWillBeSent", "Network.responseReceived"]:
                        req_url = ""
                        if "request" in log_data["params"]:
                            req_url = log_data["params"]["request"]["url"]
                        elif "response" in log_data["params"]:
                            req_url = log_data["params"]["response"]["url"]
                            
                        # ค้นหาคำว่า .m3u8 ในลิงก์
                        if ".m3u8" in req_url:
                            m3u8_url = req_url
                            break
                except Exception:
                    continue # ข้าม error ย่อยๆ ตอนอ่าน json
            
            if m3u8_url:
                print(f"  -> สำเร็จ: {movie_title}")
                movies_data.append({
                    "name": movie_title,
                    "image": movie_image,
                    "url": m3u8_url
                })
            else:
                print("  -> ไม่พบลิงก์ m3u8")
                
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
