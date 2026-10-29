import asyncio
import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai_service import generate_ai_reply
from app.database import SessionLocal
from app.models.chat_room import ChatRoom
from app.models.message import Message
from app.security import get_current_user, verify_access_token


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        self.active_connections.setdefault(room_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        connections = self.active_connections.get(room_id, [])

        if websocket in connections:
            connections.remove(websocket)

        if not connections:
            self.active_connections.pop(room_id, None)

    async def broadcast(self, message: str, room_id: int):
        disconnected = []

        for connection in self.active_connections.get(room_id, []):
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection, room_id)


manager = ConnectionManager()

router = APIRouter(prefix="/chat", tags=["Chat"])


class MessageCreate(BaseModel):
    content: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def message_payload(message: Message):
    return {
        "message_id": message.id,
        "room_id": message.room_id,
        "sender_id": message.sender_id,
        "sender_type": message.sender_type,
        "content": message.content,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at
            else None
        ),
    }


@router.post("/rooms")
def create_chat_room(
    room_name: str,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = ChatRoom(
        room_name=room_name,
        created_by=user_id,
    )

    db.add(room)
    db.commit()
    db.refresh(room)

    return {
        "message": "Chat room created successfully",
        "room_id": room.id,
        "room_name": room.room_name,
        "created_by": room.created_by,
    }


@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: int,
    message_data: MessageCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Chat room not found",
        )

    if room.created_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this chat room",
        )

    new_message = Message(
        room_id=room_id,
        sender_id=user_id,
        sender_type="customer",
        content=message_data.content,
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Message sent successfully",
        **message_payload(new_message),
    }


@router.get("/rooms/{room_id}/messages")
def get_messages(
    room_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Chat room not found",
        )

    if room.created_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this chat room",
        )

    messages = (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )

    return [message_payload(msg) for msg in messages]


@router.websocket("/ws/{room_id}")
async def websocket_chat(
    websocket: WebSocket,
    room_id: int,
    token: str,
):
    db = SessionLocal()
    connected = False

    try:
        try:
            user_id = verify_access_token(token)
        except HTTPException:
            await websocket.close(code=1008)
            return

        room = db.query(ChatRoom).filter(
            ChatRoom.id == room_id
        ).first()

        if not room or room.created_by != user_id:
            await websocket.close(code=1008)
            return

        await manager.connect(websocket, room_id)
        connected = True

        while True:
            data = await websocket.receive_text()
            data = data.strip()

            if not data:
                continue

            # 1. Save customer message
            customer_message = Message(
                room_id=room_id,
                sender_id=user_id,
                sender_type="customer",
                content=data,
            )

            db.add(customer_message)
            db.commit()
            db.refresh(customer_message)

            # 2. Broadcast customer message
            await manager.broadcast(
                json.dumps(message_payload(customer_message)),
                room_id,
            )

            # 3. Generate AI reply without blocking the async event loop
            try:
                ai_reply = await asyncio.to_thread(
                    generate_ai_reply,
                    data,
                )

                if not ai_reply or not ai_reply.strip():
                    ai_reply = (
                        "Sorry, I couldn't generate a reply. "
                        "Please contact human support."
                    )

            except Exception:
                ai_reply = (
                    "Sorry, I'm unable to respond right now. "
                    "Please contact human support."
                )

            # 4. Save AI reply with a separate sender type
            ai_message = Message(
                room_id=room_id,
                sender_id=None,
                sender_type="ai",
                content=ai_reply.strip(),
            )

            db.add(ai_message)
            db.commit()
            db.refresh(ai_message)

            # 5. Broadcast AI reply
            await manager.broadcast(
                json.dumps(message_payload(ai_message)),
                room_id,
            )

    except WebSocketDisconnect:
        pass

    except Exception:
        db.rollback()
        # Check the server terminal for debugging details.

    finally:
        if connected:
            manager.disconnect(websocket, room_id)

        db.close()
