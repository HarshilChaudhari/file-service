from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import async_session
from app.models import FSUser, FSFiles
from app.storage.local_storage import LocalStorage
import uuid
import mimetypes
from datetime import datetime
import os

app = FastAPI()
storage = LocalStorage()  # our local storage handler

# -------------------------
# Root endpoint
# -------------------------
@app.get("/")
async def root():
    return {"message": "File Management Service is running"}

# -------------------------
# User endpoints
# -------------------------
class UserCreate(BaseModel):
    configuration: dict

@app.post("/user")
async def create_user(user: UserCreate):
    async with async_session() as session:
        async with session.begin():
            code = str(uuid.uuid4())[:8]
            new_user = FSUser(code=code, configuration=user.configuration)
            session.add(new_user)
        await session.commit()
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

# -------------------------
# File upload endpoint
# -------------------------
@app.post("/upload")
async def upload_file(
    user_code: str = Form(...),
    tag: str = Form(None),
    file: UploadFile = File(...)
):
    async with async_session() as session:
        # 1️⃣ Check if user exists
        result = await session.execute(
            FSUser.__table__.select().where(FSUser.code == user_code)
        )
        user = result.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_config = user.configuration

        # 2️⃣ Validate extension
        ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
        allowed_exts = [e.lower() for e in user_config.get("allowed_extensions", [])]
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"Extension '{ext}' not allowed for this user")

        # 3️⃣ Validate MIME type
        mime_type = file.content_type
        allowed_mime = user_config.get("allowed_media_types", [])
        if allowed_mime and mime_type not in allowed_mime:
            # allow if extension matches (user's responsibility)
            if ext not in allowed_exts:
                raise HTTPException(status_code=400, detail=f"MIME type '{mime_type}' not allowed for this user")

        # 4️⃣ Save file (no file_kind)
        content = await file.read()
        file_path = await storage.save_file(user_code, None, file.filename, content)

        # 5️⃣ Save DB entry
        file_id = "fs_" + uuid.uuid4().hex[:8]
        new_file = FSFiles(
            id=file_id,
            user_id=user.id,
            filename=file.filename,
            size=len(content),
            media_type=mime_type,
            tag=tag,
            file_metadata={},  # user can update later
        )
        session.add(new_file)
        await session.commit()
        await session.refresh(new_file)

        return {
            "message": "File uploaded successfully",
            "file_id": new_file.id,
            "filename": new_file.filename,
            "size": new_file.size,
            "path": file_path
        }
