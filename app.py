from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- AI CLIENT ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- RULE ENGINE ----------------
RULES = {
    "exam": """
You are an exam system.

Rules:
- Ask 5 structured questions
- Mix easy, medium, hard
- Give expected answers
""",

    "interview": """
You are an interview system.

Rules:
- Professional questions
- Real-world thinking
- Evaluation focused
""",

    "quiz": """
You are a quiz system.

Rules:
- Short questions
- Quick answers
- Simple evaluation
"""
}

# ---------------- ROOT ----------------
@app.get("/")
def home():
    return {"status": "AI Exam Engine Running 🚀"}

# ---------------- START EXAM ----------------
@app.get("/start/{topic}")
def start_exam(topic: str, mode: str = "exam"):
    system_prompt = f"""
You are an AI exam generator.

Topic: {topic}

Rules:
- Generate exactly 5 questions
- Each must have:
  - question
  - expected answer

STRICT OUTPUT FORMAT (VERY IMPORTANT):

Return ONLY valid JSON like this:

[
  {
    "question": "...",
    "answer": "..."
  },
  {
    "question": "...",
    "answer": "..."
  }
]

NO extra text. NO headings. NO markdown. ONLY JSON.
"""
    

    








   


   


   


   


   


    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt}
        ]
    )

    return {
        "topic": topic,
        "mode": mode,
        "exam": completion.choices[0].message.content
    }

# ---------------- EVALUATE ANSWER ----------------
class Answer(BaseModel):
    question: str
    expected: str
    user_answer: str

@app.post("/evaluate")
def evaluate(data: Answer):

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": f"""
Evaluate this answer:

Question: {data.question}
Expected: {data.expected}
User: {data.user_answer}

Give:
Score /10
Status (Correct/Partial/Wrong)
Short Feedback
"""
            }
        ]
    )

    return {
        "result": completion.choices[0].message.content
    }
