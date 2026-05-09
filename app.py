from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os
import sqlite3

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# GROQ CLIENT
# -----------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -----------------------------
# DATABASE (NEW UPGRADE)
# -----------------------------
conn = sqlite3.connect("prepwise.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    usage INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0
)
""")

conn.commit()

FREE_LIMIT = 3


# -----------------------------
# CHAT API (AI INTERVIEW + SCORE)
# -----------------------------
@app.post("/chat")
def chat(data: dict):

    user_id = data.get("user_id", "guest")
    message = data.get("message", "")

    cursor.execute("SELECT usage, score FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        usage, score = row
    else:
        usage, score = 0, 0

    if usage >= FREE_LIMIT:
        return {
            "reply": "🚫 Free limit over. Please upgrade."
        }

    usage += 1

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": """
You are an AI Interview Evaluator.

Return:
- Status (Correct / Wrong / Partial)
- Score out of 10
- Short feedback
"""
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    reply = completion.choices[0].message.content

    # extract score (simple fallback logic)
    new_score = score
    if "Score" in reply:
        try:
            import re
            match = re.search(r"(\d+)", reply)
            if match:
                new_score = int(match.group(1))
        except:
            pass

    # save to DB
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, usage, score)
        VALUES (?, ?, ?)
    """, (user_id, usage, new_score))

    conn.commit()

    return {
        "reply": reply,
        "used": usage,
        "limit": FREE_LIMIT
    }


# -----------------------------
# DASHBOARD API (REAL DATA)
# -----------------------------
@app.get("/dashboard")
def dashboard(user_id: str = "guest"):

    cursor.execute("SELECT usage, score FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if not row:
        return {
            "user_id": user_id,
            "used_interviews": 0,
            "score": 0,
            "free_limit": FREE_LIMIT,
            "status": "free"
        }

    usage, score = row

    return {
        "user_id": user_id,
        "used_interviews": usage,
        "score": score,
        "free_limit": FREE_LIMIT,
        "status": "locked" if usage >= FREE_LIMIT else "free"
    }


# -----------------------------
# SAVE SCORE (OPTIONAL)
# -----------------------------
@app.post("/save-score")
def save_score(data: dict):

    user_id = data.get("user_id", "guest")
    score = data.get("score", 0)

    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, usage, score)
        VALUES (?, COALESCE((SELECT usage FROM users WHERE user_id=?),0), ?)
    """, (user_id, user_id, score))

    conn.commit()

    return {
        "msg": "score saved",
        "user_id": user_id,
        "score": score
    }


# -----------------------------
# RESUME UPLOAD
# -----------------------------
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    content = await file.read()

    return {
        "filename": file.filename,
        "size": len(content),
        "msg": "resume uploaded successfully"
    }


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
def home():
    return {
        "status": "running",
        "message": "PrepWise AI backend live 🚀"
    }
