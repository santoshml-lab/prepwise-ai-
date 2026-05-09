Python
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
import sqlite3
import random
import re

app = FastAPI()

# ---------------------------------------------------
# CORS
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# GROQ CLIENT
# ---------------------------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------------------------
# DATABASE
# ---------------------------------------------------
conn = sqlite3.connect("prepwise.db", check_same_thread=False)
cursor = conn.cursor()

# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    usage INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0
)
""")

# HISTORY TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    question TEXT,
    answer TEXT,
    score INTEGER
)
""")

conn.commit()

FREE_LIMIT = 10

# ---------------------------------------------------
# PYDANTIC MODELS
# ---------------------------------------------------
class ChatRequest(BaseModel):
    user_id: str
    question: str
    expected_answer: str
    message: str

class ScoreRequest(BaseModel):
    user_id: str
    score: int

# ---------------------------------------------------
# QUESTION BANK
# ---------------------------------------------------
question_bank = {

    "python": [

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
        }

    ],

    "programming": [

        {
            "question": "Difference between compiler and interpreter?",
            "answer": "Compiler translates whole code while interpreter executes line by line"
        }

    ],

    "hr": [

        {
            "question": "Tell me about yourself.",
            "answer": "Short professional self introduction"
        },

        {
            "question": "Why should we hire you?",
            "answer": "Skills confidence and value to company"
        }

    ]
}

# ---------------------------------------------------
# ROOT
# ---------------------------------------------------
@app.get("/")
def home():

    return {
        "status": "running",
        "message": "PrepWise AI backend live 🚀"
    }

# ---------------------------------------------------
# GET CATEGORIES
# ---------------------------------------------------
@app.get("/categories")
def get_categories():

    return {
        "categories": list(question_bank.keys())
    }

# ---------------------------------------------------
# GET QUESTION
# ---------------------------------------------------
@app.get("/get-question/{category}")
def get_question(category: str):

    if category not in question_bank:

        return {
            "error": "Invalid category"
        }

    q = random.choice(question_bank[category])

    return {
        "category": category,
        "question": q["question"],
        "expected_answer": q["answer"]
    }

# ---------------------------------------------------
# CHAT API
# ---------------------------------------------------
@app.post("/chat")
def chat(data: ChatRequest):

    user_id = data.user_id
    question = data.question
    expected_answer = data.expected_answer
    message = data.message

    # -------------------------------------------
    # CHECK USER
    # -------------------------------------------
    cursor.execute(
        "SELECT usage, score FROM users WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row:
        usage, old_score = row
    else:
        usage, old_score = 0, 0

    # -------------------------------------------
    # LIMIT CHECK
    # -------------------------------------------
    if usage >= FREE_LIMIT:

        return {
            "reply": "🚫 Free limit over. Please upgrade."
        }

    usage += 1

    # -------------------------------------------
    # AI EVALUATION
    # -------------------------------------------
    completion = client.chat.completions.create(

        model="llama-3.1-8b-instant",

        messages=[

            {
                "role": "system",
                "content": f"""
You are a smart AI Interview Evaluator.

Question:
{question}

Expected Answer:
{expected_answer}

Student Answer:
{message}

Instructions:
- Evaluate fairly.
- Minor wording mistakes are acceptable.
- Focus on concept understanding.
- Give realistic scores.
- Be concise and encouraging.

Return EXACTLY in this format:

Status: Correct / Partial / Wrong
Score: X/10
Feedback: short feedback
"""
            }

        ]
    )

    reply = completion.choices[0].message.content

    # -------------------------------------------
    # SCORE EXTRACTION
    # -------------------------------------------
    new_score = old_score

    try:

        match = re.search(r"(\\d+)/10", reply)

        if match:
            new_score = int(match.group(1))

    except:
        pass

    # -------------------------------------------
    # SAVE USER SCORE
    # -------------------------------------------
    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, usage, score)
        VALUES (?, ?, ?)
    """, (user_id, usage, new_score))

    # -------------------------------------------
    # SAVE HISTORY
    # -------------------------------------------
    cursor.execute("""
        INSERT INTO history
        (user_id, question, answer, score)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        question,
        message,
        new_score
    ))

    conn.commit()

    return {

        "reply": reply,
        "used": usage,
        "limit": FREE_LIMIT,
        "score": new_score
    }

# ---------------------------------------------------
# DASHBOARD
# ---------------------------------------------------
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

# ---------------------------------------------------
# SAVE SCORE
# ---------------------------------------------------
@app.post("/save-score")
def save_score(data: ScoreRequest):

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
    """, (
        data.user_id,
        data.user_id,
        data.score
    ))

    conn.commit()

    return {

        "msg": "score saved",
        "user_id": data.user_id,
        "score": data.score
    }

# ---------------------------------------------------
# HISTORY API
# ---------------------------------------------------
@app.get("/history/{user_id}")
def get_history(user_id: str):

    cursor.execute("""
        SELECT question, answer, score
        FROM history
        WHERE user_id=?
    """, (user_id,))

    rows = cursor.fetchall()

    history = []

    for row in rows:

        history.append({

            "question": row[0],
            "answer": row[1],
            "score": row[2]
        })

    return {
        "history": history
    }

# ---------------------------------------------------
# RESUME UPLOAD
# ---------------------------------------------------
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    content = await file.read()

    return {

        "filename": file.filename,
        "size": len(content),
        "msg": "resume uploaded successfully"
    }
