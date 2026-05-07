import asyncio
import json
import re
import os
from datetime import datetime
from playwright.async_api import async_playwright

# --- ตั้งค่าสำหรับ TrueID ---
W3U_FILE = "Hub.w3u"
# ใช้ URL หน้าเว็บช่องที่ดูฟรีได้ เพื่อให้บอทเข้าถึง Token ได้ง่าย
TARGET_URL = "https://tv.trueid.net/th-th/live/tnn16" 

async def get_new_params():
    print("[SNIFFER] Starting Headless Browser for TrueID...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # จำลองเป็น Mobile เพื่อให้หน้าเว็บโหลดเบาลงและดักจับลิงก์ได้ง่ายขึ้น
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        found_params = asyncio.Future()

        async def handle_request(request):
            url = request.url
            # ดักจับลิงก์ m3u8 ที่มีพารามิเตอร์ mpass (เอกลักษณ์ของ TrueID)
            if ".m3u8" in url and "mpass=" in url and not found_params.done():
                if "?" in url:
                    params = url.split("?", 1)[1]
                    found_params.set_result(params)

        page.on("request", handle_request)
        
        try:
            await page.goto(TARGET_URL, wait_until='networkidle', timeout=60000)
            
            # จัดการปุ่มยอมรับ Cookie (ถ้ามี)
            try: await page.click("#onetrust-accept-btn-handler", timeout=5000)
            except: pass
            
            # รอให้ระบบ Player เริ่มโหลดสตรีม
            await asyncio.sleep(25)
        except Exception as e:
            print(f"[ERROR] Navigation failed: {e}")

        try:
            return await asyncio.wait_for(found_params, timeout=45)
        except:
            return None
        finally:
            await browser.close()

def update_w3u(new_params):
    if not new_params or not os.path.exists(W3U_FILE):
        print("[ERROR] Token not found or Hub.w3u missing")
        return

    with open(W3U_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    # จัดการส่วนที่เกินใน JSON
    content = re.sub(r',(\s*[\]}])', r'\1', content)
    data = json.loads(content)

    # วนลูปอัปเดตเฉพาะช่องที่เป็นของ TrueID
    stations = data.get("stations", data if isinstance(data, list) else [])
    updated_count = 0
    for s in stations:
        # ตรวจสอบว่าเป็นลิงก์ TrueID (สังเกตจากโดเมน trueid.net)
        if "url" in s and "trueid.net" in s["url"]:
            base = s["url"].split("?")[0]
            s["url"] = f"{base}?{new_params}"
            updated_count += 1

    # อัปเดตวันที่ (รูปแบบ พ.ศ. 2569 ตามโปรเจกต์เดิม)
    now = datetime.now()
    thai_year = (now.year + 543) % 100
    data["author"] = f" update {now.day}/{now.month}/{thai_year}"

    with open(W3U_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"[SUCCESS] Updated {updated_count} TrueID channels at {now.strftime('%H:%M:%S')}")

async def run():
    params = await get_new_params()
    if params:
        update_w3u(params)
    else:
        print("[FAILED] Could not sniff TrueID token.")

if __name__ == "__main__":
    asyncio.run(run())
