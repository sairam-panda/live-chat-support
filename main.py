
from fastapi import FastAPI
from app.database import Base, engine
from app.models.user import User
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router
from app.models.chat_room import ChatRoom
from app.models.message import Message
from app.routers.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Live Chat Support System")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
def home():
    return {
        "message": "Live Chat Support System Backend is running!"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
