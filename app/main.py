from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import async_session
from app.models import FSTenant, FSFiles
from app.storage.local_storage import LocalStorage
from app.config import BASE_DIR
import uuid
import os
import pylibmagic
import magic
import shutil

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
            new_user = FSTenant(code=code, configuration=user.configuration)
            session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return {"id": str(new_user.id), "code": new_user.code, "configuration": new_user.configuration}

@app.get("/user/{code}")
async def get_user(code: str):
    async with async_session() as session:
        result = await session.execute(
            FSTenant.__table__.select().where(FSTenant.code == code)
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
            FSTenant.__table__.select().where(FSTenant.code == user_code)
        )
        user = result.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_config = user.configuration

        # 2️⃣ Validate extension
        ext = os.path.splitext(file.filename)[1].lower().replace(".", "")
        allowed_exts = [e.lower() for e in user_config.get("allowed_extensions", [])]
        if ext not in allowed_exts:
            raise HTTPException(status_code=400, detail=f"Extension '{ext}' not allowed")

        # 3️⃣ Detect real mime type
        content = await file.read()
        real_mime = magic.from_buffer(content, mime=True)

        allowed_mime = user_config.get("allowed_media_types", [])
        if allowed_mime and real_mime not in allowed_mime:
            raise HTTPException(status_code=400, detail=f"MIME type '{real_mime}' not allowed")

        # 4️⃣ Check if file already exists for this user
        existing_file = await session.execute(
            FSFiles.__table__.select().where(
                (FSFiles.user_id == user.id) &
                (FSFiles.filename == file.filename)
            )
        )
        if existing_file.fetchone():
            raise HTTPException(status_code=400, detail="File already exists for this user")

        # 5️⃣ Save file
        relative_path = await storage.save_file(user_code, file.filename, content)

        # 6️⃣ Insert DB entry
        file_id = "fs_" + uuid.uuid4().hex[:8]
        new_file = FSFiles(
            id=file_id,
            user_id=user.id,
            filename=file.filename,
            size=len(content),
            media_type=real_mime,
            tag=tag,
            relative_path=relative_path,
            file_metadata={},
        )
        session.add(new_file)
        await session.commit()
        await session.refresh(new_file)

        abs_path = os.path.join(BASE_DIR, relative_path)
        return {
            "message": "File uploaded successfully",
            "file_id": new_file.id,
            "filename": new_file.filename,
            "relative_path": new_file.relative_path,
            "absolute_path": abs_path
        }


# -------------------------
# File retrieval endpoints
# -------------------------

# 1️⃣ Metadata endpoint
@app.get("/file/{file_id}")
async def get_file_metadata(file_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(FSFiles).where(FSFiles.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "id": file.id,
            "user_id": str(file.user_id),
            "filename": file.filename,
            "size": file.size,
            "media_type": file.media_type,
            "tag": file.tag,
            "relative_path": file.relative_path,
            "file_metadata": file.file_metadata,
        }

# 2️⃣ Download endpoint
@app.get("/file/{file_id}/download")
async def download_file(file_id: str):
    async with async_session() as session:
        result = await session.execute(
            FSFiles.__table__.select().where(FSFiles.id == file_id)
        )
        file_record = result.fetchone()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        abs_path = os.path.join(BASE_DIR, file_record.relative_path)
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        # ✅ Add filename so curl/wget/browser saves correctly
        return FileResponse(
            abs_path,
            filename=file_record.filename,
            media_type=file_record.media_type
        )


# -------------------------
# List files for a user
# -------------------------
@app.get("/user/{code}/files")
async def list_user_files(code: str):
    async with async_session() as session:
        # Find user
        result = await session.execute(
            select(FSTenant).where(FSTenant.code == code)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get all files for this user
        result = await session.execute(
            select(FSFiles).where(FSFiles.user_id == user.id)
        )
        files = result.scalars().all()

        return [
            {
                "id": f.id,
                "filename": f.filename,
                "size": f.size,
                "media_type": f.media_type,
                "tag": f.tag,
                "relative_path": f.relative_path,
                "file_metadata": f.file_metadata,
                # ✅ Add download URL
                "download_url": f"/file/{f.id}/download"
            }
            for f in files
        ]

# -------------------------
# Delete a single file
# -------------------------
@app.delete("/file/{file_id}")
async def delete_file(file_id: str):
    async with async_session() as session:
        # Find the file as ORM object
        result = await session.execute(
            select(FSFiles).where(FSFiles.id == file_id)
        )
        file = result.scalar_one_or_none()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # Compute absolute path
        abs_path = os.path.abspath(os.path.join(BASE_DIR, file.relative_path))
        print("Deleting file at:", abs_path)  # debug
        if not os.path.exists(abs_path):
            print("File not found on disk!")

        # Delete from storage
        await storage.delete_file(abs_path)

        # Delete from DB
        await session.delete(file)
        await session.commit()

        return {"message": f"File '{file.filename}' deleted successfully"}


# -------------------------
# Delete a user and all files
# -------------------------
@app.delete("/user/{code}")
async def delete_user(code: str):
    async with async_session() as session:
        # 1️⃣ Find user as ORM object
        result = await session.execute(
            select(FSTenant).where(FSTenant.code == code)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2️⃣ Get all files for this user
        result = await session.execute(
            select(FSFiles).where(FSFiles.user_id == user.id)
        )
        files = result.scalars().all()

        # 3️⃣ Delete files from storage and DB
        for f in files:
            abs_path = os.path.abspath(os.path.join(BASE_DIR, f.relative_path))
            print("Deleting file at:", abs_path)  # debug
            if not os.path.exists(abs_path):
                print("File not found on disk!")
            await storage.delete_file(abs_path)
            await session.delete(f)

        # 4️⃣ Delete user's folder from storage
        user_dir = os.path.join(BASE_DIR, user.code)
        if os.path.exists(user_dir):
            print("Deleting user folder:", user_dir)
            shutil.rmtree(user_dir)

        # 5️⃣ Delete user from DB
        await session.delete(user)
        await session.commit()

        return {"message": f"User '{code}' and all their files deleted successfully"}


