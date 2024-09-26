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

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name


        logging.info("Видио взято в обработку")

        video = VideoFileClip(temp_file_path)

        duration = video.duration
        num_chunks = calculate_chunks(duration)
        video_sessions[session_id] = video

        # os.remove(temp_file_path)
        return UploadResponse(message="Файл успешно загружен",
                              session_id=session_id,
                              duration=duration,
                              chunks=num_chunks,
                              websocket_url=f"/ws/video-processing/{session_id}"
                              )

    except Exception as e:
        return JSONResponse(content={"message": f"Ошибка загрузки файла: {str(e)}"}, status_code=500)

