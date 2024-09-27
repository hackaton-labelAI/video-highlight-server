import json
import logging
import os
import time
from dataclasses import asdict
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
from services.find_best import find_interesting_moment
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

        buffer = []

        def set_in_buffer(obj):
            buffer.append(obj)
            if len(buffer) % 3 == 0:
                end_chunk = len(buffer) // 3
                find_interesting_moment(buffer[end_chunk - 3:end_chunk])

        duration = video.duration
        # count_chunks = int(duration // 10)
        count_chunks = 10
        logging.info(f"Начата обработка: количество чанков {count_chunks}")
        start_time = time.time()

        async def transcribe_video_chunk(video, chunk_id, semaphore):
            async with semaphore:
                whisper_response = await transcribe_by_chunk_id(video, chunk_id)
                logging.info(whisper_response)
                set_in_buffer(whisper_response)
                await websocket.send_text("1")
                return whisper_response

        semaphore = asyncio.Semaphore(1)

        tasks = [
            transcribe_video_chunk(video, chunk_id, semaphore)
            for chunk_id in range(0, count_chunks + 1)
        ]

        results = await asyncio.gather(*tasks)
        results_as_dict = [asdict(result) for result in results]
        with open('data/vidio.json', 'w', encoding='utf-8') as f:
            json.dump(results_as_dict, f, ensure_ascii=False, indent=4)
        end_time = time.time() - start_time
        logging.info(f"Обработано {count_chunks} за {end_time}")

    except WebSocketDisconnect:
        logging.info(f"WebSocket для сессии {session_id} закрыт")
    finally:
        video_sessions.pop(session_id, None)


if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", log_level="debug")
    server = uvicorn.Server(config)
    server.run()