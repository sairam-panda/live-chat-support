
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)


def generate_ai_reply(customer_message: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=customer_message,
        config={
            "system_instruction": (
                "You are a helpful customer support assistant. "
                "Give clear, polite, and concise answers. "
                "If you do not know the answer, say so honestly "
                "and recommend contacting a human support agent."
            ),
            "temperature": 0.3,
        },
    )

    reply = response.text

    if not reply:
        return "Sorry, I couldn't generate a reply. Please contact support."

    return reply.strip()
