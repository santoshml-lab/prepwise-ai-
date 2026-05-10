from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import os
import json

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
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

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

    return {
        "status": "AI Exam Engine Running 🚀"
    }

# ---------------- START EXAM ----------------
@app.get("/start/{topic}")
def start_exam(topic: str, mode: str = "exam"):

    system_prompt = f"""
{RULES.get(mode, RULES["exam"])}

Topic: {topic}

Generate exactly 5 questions.

Each question must contain:
- question
- answer

STRICT RULES:
- Return ONLY valid JSON
- No markdown
- No explanation
- No headings

Format:

[
  {{
    "question": "What is OOP?",
    "answer": "Object Oriented Programming"
  }},
  {{
    "question": "What is inheritance?",
    "answer": "Inheritance allows one class to use another class properties"
  }}
]
"""

    completion = client.chat.completions.create(

        model="llama-3.1-8b-instant",

        messages=[
            {
                "role": "system",
                "content": system_prompt
            }
        ]

    )

    ai_output = completion.choices[0].message.content

    try:

        questions = json.loads(ai_output)

    except:

        questions = {
            "raw_output": ai_output
        }

    return {

        "topic": topic,
        "mode": mode,
        "questions": questions
    }

# ---------------- ANSWER MODEL ----------------
class Answer(BaseModel):

    question: str
    expected: str
    user_answer: str

# ---------------- EVALUATE ANSWER ----------------
@app.post("/evaluate")
def evaluate(data: Answer):

    completion = client.chat.completions.create(

        model="llama-3.1-8b-instant",

        messages=[

            {
                "role": "system",
                "content": f"""
You are an AI answer evaluator.

Question:
{data.question}

Expected Answer:
{data.expected}

User Answer:
{data.user_answer}

Evaluate fairly.

Return format:

{{
  "score": 8,
  "status": "Correct",
  "feedback": "Good understanding of concept"
}}

ONLY RETURN JSON.
"""
            }

        ]

    )

    result = completion.choices[0].message.content

    try:

        parsed = json.loads(result)

    except:

        parsed = {
            "raw_output": result
        }

    return parsed
    
