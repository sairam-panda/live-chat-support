
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient, models

load_dotenv()

# Gemini client
gemini = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# Qdrant client
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

COLLECTION_NAME = "support_knowledge"

# Sample customer-support knowledge
faqs = [
    {
        "question": "How can I reset my password?",
        "answer": "Open the login page, click Forgot Password, and follow the instructions to reset your password.",
        "category": "account",
    },
    {
        "question": "How can I contact customer support?",
        "answer": "Open the live chat and send your question. If the AI cannot resolve your issue, a support agent can help.",
        "category": "support",
    },
    {
        "question": "How can I update my email address?",
        "answer": "Open your account settings and look for the email update option. Follow the verification instructions.",
        "category": "account",
    },
    {
        "question": "Why can't I log in to my account?",
        "answer": "Check your email and password, verify your internet connection, and use Forgot Password if needed.",
        "category": "login",
    },
]

points = []

for index, faq in enumerate(faqs, start=1):
    text = (
        f"Question: {faq['question']}\n"
        f"Answer: {faq['answer']}"
    )

    result = gemini.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        ),
    )

    vector = result.embeddings[0].values

    points.append(
        models.PointStruct(
            id=index,
            vector=vector,
            payload={
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "text": text,
            },
        )
    )

qdrant.upsert(
    collection_name=COLLECTION_NAME,
    points=points,
    wait=True,
)

print(f"Successfully stored {len(points)} FAQs in Qdrant!")
