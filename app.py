from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os

app = FastAPI()

# CORS (frontend connect ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq Client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Simple in-memory storage (later DB use karna)
user_usage = {}
user_scores = {}

FREE_LIMIT = 3


# -----------------------------
# CHAT API (AI INTERVIEW)
# -----------------------------
@app.post("/chat")
def chat(data: dict):

    user_id = data.get("user_id", "guest")
    message = data.get("message")

    # usage limit check
    used = user_usage.get(user_id, 0)
    if used >= FREE_LIMIT:
        return {"reply": "🚫 Free limit over. Please upgrade to premium."}

    user_usage[user_id] = used + 1

    # AI CALL
    completion = client.chat.completions.create(
        model="llama3-70b-versatile",
    messages=[
        messages=[
            {"role": "system", "content": "You are an interview coach."},
            {"role": "user", "content": message}
        ]
    ]

    reply = completion.choices[0].message.content

    return {"reply": reply}


# -----------------------------
# DASHBOARD API
# -----------------------------
@app.get("/dashboard")
def dashboard(user_id: str = "guest"):

    usage = user_usage.get(user_id, 0)
    score = user_scores.get(user_id, 75)  # demo score

    return {
        "user_id": user_id,
        "used_interviews": usage,
        "free_limit": FREE_LIMIT,
        "score": score,
        "status": "free" if usage < FREE_LIMIT else "locked"
    }


# -----------------------------
# SAVE SCORE API
# -----------------------------
@app.post("/save-score")
def save_score(data: dict):

    user_id = data.get("user_id", "guest")
    score = data.get("score", 0)

    user_scores[user_id] = score

    return {"msg": "score saved"}


# -----------------------------
# RESUME UPLOAD (BASIC)
# -----------------------------
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    content = await file.read()

    return {
        "filename": file.filename,
        "size": len(content),
        "msg": "uploaded successfully"
    }
