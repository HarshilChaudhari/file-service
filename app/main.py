from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import async_session
from app.models import FSUser
import uuid

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "File Management Service is running"}

# Pydantic schema for creating a user
class UserCreate(BaseModel):
    configuration: dict

@app.post("/user")
async def create_user(user: UserCreate):
    async with async_session() as session:
        async with session.begin():
            # Generate a simple unique code (you can improve later)
            code = str(uuid.uuid4())[:8]
            new_user = FSUser(code=code, configuration=user.configuration)
            session.add(new_user)
        await session.commit()
        # Refresh to get the generated ID
        await session.refresh(new_user)
        return {"id": str(new_user.id), "code": new_user.code, "configuration": new_user.configuration}

@app.get("/user/{code}")
async def get_user(code: str):
    async with async_session() as session:
        result = await session.execute(
            FSUser.__table__.select().where(FSUser.code == code)
        )
        user = result.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": str(user.id), "code": user.code, "configuration": user.configuration}
