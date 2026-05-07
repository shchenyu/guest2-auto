from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
import os
from datetime import datetime

# ================== CONFIG (ปรับปรุงสำหรับ GitHub) ==================
URL = "https://dooballfree.cam/"
SAVE_DIR = "output" # เปลี่ยนจาก D:\ เป็นโฟลเดอร์ในโปรเจกต์
OUTPUT_FILE = os.path.join(SAVE_DIR, "dbf.txt")

# ================== แปลงวันที่ไทย ==================
THAI_MONTHS = {
    "ม.ค": 1, "ก.พ": 2, "มี.ค": 3, "เม.ย": 4,
    "พ.ค": 5, "มิ.ย": 6, "ก.ค": 7, "ส.ค": 8,
    "ก.ย": 9, "ต.ค": 10, "พ.ย": 11, "ธ.ค": 12,
}

def thai_date_to_sort(date_str):
    try:
        parts = date_str.strip().split()
        day = int(parts[0])
        month = THAI_MONTHS.get(parts[1], 1)
        year = int(parts[2]) - 543
        return datetime(year, month, day)
    except:
        return datetime.now()

# ================== Selenium (ปรับปรุงสำหรับ Linux/GitHub) ==================
options = Options()
options.add_argument("--headless") # จำเป็นสำหรับการรันบน GitHub
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ใช้ webdriver-manager เพื่อติดตั้ง Chrome Driver อัตโนมัติ
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get(URL)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(5)
    # Scroll ลงมาเพื่อให้ Content โหลดครบ
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
finally:
    driver.quit()

# ================== Parse (คงเดิม) ==================
results = []
current_date = ""
current_league = ""

for el in soup.find_all(["b", "strong", "div"], recursive=True):
    # ---------- DATE ----------
    if el.name == "b" and "fs-4" in el.get("class", []):
        current_date = el.get_text(strip=True)

    # ---------- LEAGUE ----------
    elif el.name == "strong" and "text-white" in el.get("class", []):
        current_league = el.get_text(strip=True)

    # ---------- MATCH ----------
    elif el.name == "div" and "border-end" in el.get("class", []):
        match_time = el.get_text(strip=True)
        team_box = el.find_next_sibling("div", class_="bg-dark")
        if not team_box:
            continue

        teams = team_box.select("p[style]")
        logos = team_box.select("img[height='35px']")

        if len(teams) < 2:
            continue

        home_team = teams[0].get_text(strip=True)
        away_team = teams[-1].get_text(strip=True)
        home_logo = logos[0]["src"] if len(logos) > 0 else ""
        away_logo = logos[1]["src"] if len(logos) > 1 else ""

        channel_box = team_box.find_next_sibling("div", class_="bg-secondary")
        channels = []

        if channel_box:
            for ch in channel_box.select("img.iam-list-tv"):
                channels.append({
                    "name": f"{match_time} | {home_team} vs {away_team}",
                    "image": ch.get("src", ""),
                    "url": ch.get("data-url", ""),
                    "referer": URL,
                    "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X)"
                })

        try:
            hh, mm = match_time.split(":")
            time_sort = int(hh) * 60 + int(mm)
        except:
            time_sort = 0

        date_sort = thai_date_to_sort(current_date)

        results.append({
            "date": current_date,
            "date_sort": date_sort,
            "league": current_league,
            "time": match_time,
            "time_sort": time_sort,
            "match_name": f"{match_time} | {home_team} vs {away_team}",
            "match_image": home_logo or away_logo,
            "channels": channels
        })

# ================== เรียงวัน + เวลา ==================
results = sorted(results, key=lambda x: (x["date_sort"], x["time_sort"]))

# ================== Build W3U ==================
os.makedirs(SAVE_DIR, exist_ok=True)
groups_by_date = {}

for item in results:
    date = item["date"]
    if date not in groups_by_date:
        groups_by_date[date] = {
            "name": f"วันที่ {date}",
            "image": "https://dooballfree.cam/wp-content/uploads/2025/05/logo-1-1.png",
            "groups": []
        }
    groups_by_date[date]["groups"].append({
        "name": item["match_name"],
        "image": item["match_image"],
        "info": item["league"],
        "stations": item["channels"]
    })

final_data = {
    "name": f"dooballfree.cam@{results[0]['date'] if results else ''}",
    "author": f"Update@{results[0]['date'] if results else ''}",
    "info": f"dooballfree.cam@{results[0]['date'] if results else ''}",
    "image": "https://dooballfree.cam/wp-content/uploads/2025/05/logo-1-1.png",
    "groups": list(groups_by_date.values())
}

# ================== Save ==================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print(f"บันทึกไฟล์เรียบร้อย → {OUTPUT_FILE}")
print(f"จำนวนแมตช์ทั้งหมด: {len(results)}")
