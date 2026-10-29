
from app.ai_service import generate_ai_reply

question = "I forgot my password. How can I log in?"

print("Customer:", question)

answer = generate_ai_reply(question)

print("\nAI Assistant:", answer)
