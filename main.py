import logging
import os
import time
from time import sleep
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from fastapi import FastAPI
from moviepy.video.io.VideoFileClip import VideoFileClip
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from endpoints.upload_file import router as UploadFile
from endpoints.upload_file import video_sessions
from services.transcibe import transcribe_by_chunk_id

app = FastAPI()

app.include_router(UploadFile)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.websocket("/ws/video-processing/{session_id}")
async def video_processing(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:

        if session_id not in video_sessions:
            await websocket.send_text("Ошибка: Видео для данной сессии не найдено")
            await websocket.close()
            return


        video: VideoFileClip = video_sessions[session_id]
        duration = video.duration
        count_chunks = 10
        results = []
        logging.info(f"Начата обработка: количество чанков {count_chunks}")
        start_time = time.time()

        async def transcribe_video_chunk(video, chunk_id, semaphore):
            async with semaphore:
                results = await transcribe_by_chunk_id(video, chunk_id)
                logging.info(results)
                return

        semaphore = asyncio.Semaphore(5)

        tasks = [
            transcribe_video_chunk(video, chunk_id, semaphore)
            for chunk_id in range(1, count_chunks + 1)
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.time() - start_time
        logging.info(f"Обработано {count_chunks} за {end_time}")

    except WebSocketDisconnect:
        logging.info(f"WebSocket для сессии {session_id} закрыт")
    finally:
        if session_id in video_sessions:
            video: VideoFileClip = video_sessions[session_id]
            os.remove(video.filename)

        video_sessions.pop(session_id, None)


if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", log_level="debug")
    server = uvicorn.Server(config)
    server.run()