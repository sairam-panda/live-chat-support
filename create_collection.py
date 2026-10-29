
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

url = os.getenv("QDRANT_URL")
api_key = os.getenv("QDRANT_API_KEY")

if not url or not api_key:
    raise ValueError("QDRANT_URL or QDRANT_API_KEY missing from .env")

client = QdrantClient(
    url=url,
    api_key=api_key,
)

collection_name = "support_knowledge"

if client.collection_exists(collection_name):
    print(f"Collection '{collection_name}' already exists.")
else:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=768,
            distance=models.Distance.COSINE,
        ),
    )
    print(f"Collection '{collection_name}' created successfully!")

print("Collections:", client.get_collections())
