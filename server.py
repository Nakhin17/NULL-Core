# ระบบหลังบ้านสำหรับเปิดเซิร์ฟเวอร์ รวบรวมข้อมูล และยิงเข้า Discord
# วิธีใช้งาน: 
# 1. ติดตั้งไลบรารี: pip install fastapi uvicorn sqlite3 requests pydantic
# 2. รันเซิร์ฟเวอร์: uvicorn server:app --reload

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import sqlite3
import requests
import datetime

app = FastAPI(title="Backend Service (Admin API)")

# ==========================================
# ตั้งค่า Discord Webhook ของคุณที่นี่
# ==========================================
DISCORD_WEBHOOK_URL = "https://discordapp.com/api/webhooks/1519398387382878378/ibyXLVt6pY7OlSqXmIb4_XQOGTzCx3sZColnr8s2iKWK6e-P3jIt3wnMv6TzEwlRn_T-"

# ==========================================
# การเชื่อมต่อฐานข้อมูล (SQLite สำหรับความง่าย)
# ==========================================
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # สร้างตารางผู้ใช้
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, points INTEGER)''')
    # สร้างตารางประวัติเติมเงิน
    c.execute('''CREATE TABLE IF NOT EXISTS topups
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, amount INTEGER, slip_url TEXT, status TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# Models สำหรับรับข้อมูลจาก Frontend
# ==========================================
class TopupRequest(BaseModel):
    username: str
    amount: int
    slip_url: str # ในระบบจริง อาจส่งเป็น Base64 หรือลิงก์ไฟล์ที่อัปโหลดแล้ว

class UserRegister(BaseModel):
    username: str
    password: str

# ==========================================
# Functions แจ้งเตือน Discord
# ==========================================
def send_discord_notification(username: str, amount: int, slip_url: str):
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        print("กรุณาใส่ Discord Webhook URL ก่อน")
        return
    
    data = {
        "content": f"🚨 **มีการแจ้งโอนเงินใหม่!** 🚨",
        "embeds": [
            {
                "title": "รายละเอียดการเติมเงิน",
                "color": 3066993, # สีเขียว
                "fields": [
                    {"name": "ชื่อผู้ใช้ (Username)", "value": username, "inline": True},
                    {"name": "จำนวนเงินที่เติม", "value": f"{amount} บาท", "inline": True},
                    {"name": "เวลา", "value": str(datetime.datetime.now()), "inline": False}
                ],
                "image": {
                    "url": slip_url # แสดงสลิปในดิสคอสทันที
                }
            }
        ]
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    if response.status_code == 204:
        print("แจ้งเตือนเข้า Discord สำเร็จ")
    else:
        print(f"เกิดข้อผิดพลาดในการส่ง Discord: {response.status_code}")

# ==========================================
# API Endpoints
# ==========================================

@app.get("/")
def read_root():
    return {"message": "Server is running normally."}

@app.post("/register")
def register_user(user: UserRegister):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, points) VALUES (?, ?, 0)", (user.username, user.password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้นี้มีในระบบแล้ว")
    conn.close()
    return {"message": "ลงทะเบียนสำเร็จ"}

@app.post("/submit_topup")
def submit_topup(data: TopupRequest, background_tasks: BackgroundTasks):
    timestamp = str(datetime.datetime.now())
    
    # 1. บันทึกลงฐานข้อมูล
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO topups (username, amount, slip_url, status, timestamp) VALUES (?, ?, ?, ?, ?)",
              (data.username, data.amount, data.slip_url, "pending", timestamp))
    conn.commit()
    conn.close()

    # 2. ให้ระบบส่งแจ้งเตือนเข้า Discord แบบ Background อัตโนมัติทันที
    background_tasks.add_task(send_discord_notification, data.username, data.amount, data.slip_url)

    return {"message": "ส่งหลักฐานสำเร็จ แอดมินจะตรวจสอบผ่าน Discord เร็วๆ นี้"}

@app.get("/admin/users")
def get_all_users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, username, points FROM users")
    users = [{"id": row[0], "username": row[1], "points": row[2]} for row in c.fetchall()]
    conn.close()
    return users
