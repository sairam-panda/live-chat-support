
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient

load_dotenv()

gemini = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

# Customer ka sample question
question = "I forgot my password. How can I log in?"

# Question ko vector mein convert karo
result = gemini.models.embed_content(
    model="gemini-embedding-2",
    contents=question,
    config=types.EmbedContentConfig(
        output_dimensionality=768
    ),
)

query_vector = result.embeddings[0].values

# Qdrant se similar FAQs search karo
search_result = qdrant.query_points(
    collection_name="support_knowledge",
    query=query_vector,
    limit=3,
    with_payload=True,
)

print("\nRelevant FAQs:\n")

for point in search_result.points:
    print("Score:", round(point.score, 4))
    print("Question:", point.payload.get("question"))
    print("Answer:", point.payload.get("answer"))
    print("-" * 40)
