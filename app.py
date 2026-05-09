
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import os
import sqlite3
import random
import re

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
# DATABASE
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

FREE_LIMIT = 10

# -----------------------------
# QUESTION BANK
# -----------------------------
questions = [

    {
        "question": "What is OOP?",
        "answer": "Object Oriented Programming"
    },

    {
        "question": "Explain inheritance.",
        "answer": "Inheritance allows one class to acquire properties of another class"
    },

    {
        "question": "What is polymorphism?",
        "answer": "Polymorphism means many forms"
    },

    {
        "question": "Difference between compiler and interpreter?",
        "answer": "Compiler translates whole code while interpreter executes line by line"
    }

]

# -----------------------------
# GET QUESTION API
# -----------------------------
@app.get("/get-question")
def get_question():

    q = random.choice(questions)

    return {
        "question": q["question"],
        "expected_answer": q["answer"]
    }

# -----------------------------
# CHAT API (AI EVALUATION)
# -----------------------------
@app.post("/chat")
def chat(data: dict):

    user_id = data.get("user_id", "guest")

    question = data.get("question", "")
    expected_answer = data.get("expected_answer", "")
    message = data.get("message", "")

    cursor.execute(
        "SELECT usage, score FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:
        usage, old_score = row
    else:
        usage, old_score = 0, 0

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
                "content": f"""
You are an AI Exam Evaluator.

Question:
{question}

Expected Answer:
{expected_answer}

Student Answer:
{message}

Evaluate the student answer carefully.

Return in this format:

Status: Correct / Partial / Wrong
Score: X/10
Feedback: short feedback
"""
            }

        ]
    )

    reply = completion.choices[0].message.content

    # -----------------------------
    # SCORE EXTRACTION
    # -----------------------------
    new_score = old_score

    try:

        match = re.search(r"(\d+)/10", reply)

        if match:
            new_score = int(match.group(1))

    except:
        pass

    # -----------------------------
    # SAVE USER DATA
    # -----------------------------
    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, usage, score)
        VALUES (?, ?, ?)
    """, (user_id, usage, new_score))

    conn.commit()

    return {
        "reply": reply,
        "used": usage,
        "limit": FREE_LIMIT,
        "score": new_score
    }

# -----------------------------
# DASHBOARD API
# -----------------------------
@app.get("/dashboard")
def dashboard(user_id: str = "guest"):

    cursor.execute(
        "SELECT usage, score FROM users WHERE user_id=?",
        (user_id,)
    )

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
# SAVE SCORE API
# -----------------------------
@app.post("/save-score")
def save_score(data: dict):

    user_id = data.get("user_id", "guest")
    score = data.get("score", 0)

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, usage, score)

        VALUES (
            ?,
            COALESCE(
                (SELECT usage FROM users WHERE user_id=?),
                0
            ),
            ?
        )
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
# ROOT
# -----------------------------
@app.get("/")
def home():

    return {

        "status": "running",
        "message": "PrepWise AI backend live 🚀"
    }
