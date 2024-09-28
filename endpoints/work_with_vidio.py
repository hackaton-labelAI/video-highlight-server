import logging
import tempfile
import uuid
from dataclasses import dataclass

from fastapi import File, UploadFile, APIRouter
from fastapi.responses import JSONResponse

import os

from moviepy.video.io.VideoFileClip import VideoFileClip
from starlette.websockets import WebSocket, WebSocketDisconnect

from services.chunks import calculate_chunks

router = APIRouter()

video_sessions = {}


@router.get("/project/{session_id}")
async def upload_video(session_id: str):
    try:
        session_id = str(uuid.uuid4())

        session_folder = f"session_info_{session_id}"

    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")
        return JSONResponse(content={"message": f"Ошибка загрузки файла: {str(e)}"}, status_code=500)
