from fastapi import APIRouter, Depends
from sqlmodel import Session
from src.building_blocks.infrastructure.database import get_session
from src.modules.iam.application.services import IAMService

router = APIRouter()

@router.post("/register")
async def register(data: dict, session: Session = Depends(get_session)):
    service = IAMService(session)
    user = await service.register_user(data)
    return {"message": "User created", "user_id": user.id}
