from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os

app = FastAPI()

# -----------------------------
# CORS SETUP (Frontend connect)
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
# SIMPLE IN-MEMORY STORAGE
# (Later DB use karna hai)
# -----------------------------
user_usage = {}
user_scores = {}

FREE_LIMIT = 3


# -----------------------------
# CHAT API (AI INTERVIEW)
# -----------------------------
@app.post("/chat")
def chat(data: dict):

    user_id = data.get("user_id", "guest")
    message = data.get("message", "")

    # usage limit check
    used = user_usage.get(user_id, 0)

    if used >= FREE_LIMIT:
        return {
            "reply": "🚫 Free limit over. Please upgrade to premium."
        }

    user_usage[user_id] = used + 1

    # AI CALL (FIXED)
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are a strict but helpful interview coach. Give short, clear answers."
            },
            {
                "role": "user",
                "content": message
            }
        ]
    )

    reply = completion.choices[0].message.content

    return {
        "reply": reply,
        "used": user_usage[user_id],
        "limit": FREE_LIMIT
    }


# -----------------------------
# DASHBOARD API
# -----------------------------
@app.get("/dashboard")
def dashboard(user_id: str = "guest"):

    usage = user_usage.get(user_id, 0)
    score = user_scores.get(user_id, 75)

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

    return {
        "msg": "score saved successfully",
        "user_id": user_id,
        "score": score
    }


# -----------------------------
# RESUME UPLOAD API
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
# ROOT CHECK
# -----------------------------
@app.get("/")
def home():

    return {
        "status": "running",
        "message": "InterviewGPT backend is live 🚀"
    }
