
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.ai_service import generate_ai_reply
from app.database import SessionLocal
from app.models.chat_room import ChatRoom
from app.security import get_current_user
from app.models.message import Message
from pydantic import BaseModel
from fastapi import WebSocket, WebSocketDisconnect
from app.security import verify_access_token



class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        self.active_connections.setdefault(room_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)

            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: int):
        for connection in self.active_connections.get(room_id, []):
            await connection.send_text(message)


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


@router.post("/rooms")
def create_chat_room(
    room_name: str,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = ChatRoom(
        room_name=room_name,
        created_by=user_id
    )

    db.add(room)
    db.commit()
    db.refresh(room)

    return {
        "message": "Chat room created successfully",
        "room_id": room.id,
        "room_name": room.room_name,
        "created_by": room.created_by
    }


@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: int,
    message_data: MessageCreate,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Chat room not found"
        )

    new_message = Message(
        room_id=room_id,
        sender_id=user_id,
        content=message_data.content
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return {
        "message": "Message sent successfully",
        "message_id": new_message.id,
        "room_id": new_message.room_id,
        "sender_id": new_message.sender_id,
        "content": new_message.content,
        "created_at": new_message.created_at
    }

@router.get("/rooms/{room_id}/messages")
def get_messages(
    room_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    room = db.query(ChatRoom).filter(
        ChatRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Chat room not found"
        )
    
    if room.created_by != user_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this chat room"
    )


    messages = db.query(Message).filter(
        Message.room_id == room_id
    ).order_by(Message.created_at.asc()).all()

    return [
        {
            "message_id": msg.id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "created_at": msg.created_at
        }
        for msg in messages
    ]



@router.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int, token: str):
    db = SessionLocal()

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

        try:
            while True:
                data = await websocket.receive_text()

                new_message = Message(
                    room_id=room_id,
                    sender_id=user_id,
                    content=data
                )

                db.add(new_message)
                db.commit()
                db.refresh(new_message)

                await manager.broadcast(data, room_id)

        except WebSocketDisconnect:
            manager.disconnect(websocket, room_id)

    finally:
        db.close()
