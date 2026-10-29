from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app.database import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate

router = APIRouter(prefix="/users", tags=["Users"])

password_hash = PasswordHash.recommended()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) |
        (User.email == user.email)
    ).first()

    if existing_user:
        return {"message": "Username or email already exists"}

    hashed_password = password_hash.hash(user.password)

    
    new_user = User(
    username=user.username,
    email=user.email,
    password=hashed_password,
    role="customer"
     )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "username": new_user.username
    }
