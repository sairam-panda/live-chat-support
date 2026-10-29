
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient

load_dotenv()

# Read credentials from .env
gemini_api_key = os.getenv("GEMINI_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY missing from .env")

if not qdrant_url or not qdrant_api_key:
    raise ValueError("Qdrant credentials missing from .env")

# Initialize clients
gemini_client = genai.Client(api_key=gemini_api_key)

qdrant_client = QdrantClient(
    url=qdrant_url,
    api_key=qdrant_api_key,
)

COLLECTION_NAME = "support_knowledge"


def search_knowledge(question: str, limit: int = 3) -> list[dict]:
    """Find relevant support knowledge for a customer question."""

    # Convert customer question into a vector
    result = gemini_client.models.embed_content(
        model="gemini-embedding-2",
        contents=question,
        config=types.EmbedContentConfig(
            output_dimensionality=768
        ),
    )

    query_vector = result.embeddings[0].values

    # Search the Qdrant collection
    search_result = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )

    # Return useful information to the caller
    knowledge = []

    for point in search_result.points:
        payload = point.payload or {}

        knowledge.append({
            "question": payload.get("question", ""),
            "answer": payload.get("answer", ""),
            "category": payload.get("category", ""),
            "score": point.score,
        })

    return knowledge


# Simple test when this file is run directly
if __name__ == "__main__":
    question = "I forgot my password. How can I log in?"

    results = search_knowledge(question)

    for item in results:
        print("Question:", item["question"])
        print("Answer:", item["answer"])
        print("Score:", round(item["score"], 4))
        print("-" * 40)
