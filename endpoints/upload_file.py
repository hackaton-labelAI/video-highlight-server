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

@dataclass
class UploadResponse:
    message: str
    session_id: str
    duration: int
    chunks: int
    websocket_url: str


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        session_id = str(uuid.uuid4())

        session_folder = f"session_info_{session_id}"
        os.makedirs(session_folder, exist_ok=True)

        video_path = os.path.join(session_folder, f"original_{session_id}.mp4")

        with open(video_path, 'wb') as temp_file:
            temp_file.write(await file.read())

        logging.info("Видео взято в обработку")

        video = VideoFileClip(video_path)
        duration = video.duration
        num_chunks = calculate_chunks(duration, 2)

        video_sessions[session_id] = video

        return UploadResponse(
            message="Файл успешно загружен",
            session_id=session_id,
            duration=duration,
            chunks=num_chunks,
            websocket_url=f"/ws/video-processing/{session_id}"
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")
        return JSONResponse(content={"message": f"Ошибка загрузки файла: {str(e)}"}, status_code=500)
