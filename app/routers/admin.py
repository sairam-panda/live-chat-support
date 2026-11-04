from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/test")
def test_admin_access(
    admin=Depends(get_current_admin)
):
    return {
        "message": "Admin access successful",
        "username": admin.username,
        "role": admin.role
    }

password_hash = PasswordHash.recommended()


@router.post("/agents", status_code=201)
def create_agent(
    user_data: UserCreate,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        (User.username == user_data.username) |
        (User.email == user_data.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Username or email already exists"
        )

    hashed_password = password_hash.hash(user_data.password)

    new_agent = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
        role="agent"
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return {
        "message": "Agent created successfully",
        "user_id": new_agent.id,
        "username": new_agent.username,
        "email": new_agent.email,
        "role": new_agent.role
    }
