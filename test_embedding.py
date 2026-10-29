
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

client = genai.Client(api_key=api_key)

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="How can I reset my password?",
    config=types.EmbedContentConfig(
        output_dimensionality=768
    ),
)

embedding = result.embeddings[0].values

print("Embedding generated successfully!")
print("Vector dimensions:", len(embedding))
print("First 5 values:", embedding[:5])
