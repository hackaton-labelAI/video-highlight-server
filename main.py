import asyncio
import json
import logging
import os
import time
from dataclasses import asdict
from typing import List

import uvicorn
from fastapi import FastAPI
from moviepy.video.io.VideoFileClip import VideoFileClip
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from endpoints.upload_file import router as UploadFile
from endpoints.get_subtitles import router as Subtitles
from endpoints.upload_file import video_sessions
from endpoints.work_with_vidio import router as WorkWithFile
from services.find_best import find_interesting_moment, sort_results, find_two_moments, ResultMoment
from services.transcibe import transcribe_by_chunk_id

app = FastAPI(title='Video Highlighter API', docs_url='/docs')

app.include_router(UploadFile)
app.include_router(WorkWithFile)
app.include_router(Subtitles)

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


def save_moments(moments: List[ResultMoment], session_id: str):
    session_folder = f"session_info_{session_id}"
    video = VideoFileClip(f"{session_folder}/original_{session_id}.mp4")
    os.makedirs(f"{session_folder}/chunks", exist_ok=True)
    for id, moment in enumerate(moments):
        start_time = moment.whisper_response[0].start_time
        end_time = moment.whisper_response[-1].end_time
        video_subclip = video.subclip(start_time, end_time)
        video_subclip.write_videofile(f"{session_folder}/chunks/{id}.mp4")
        with open(f"{session_folder}/chunks/{id}.json", 'w', encoding='utf-8') as json_file:
            json.dump(moment.to_dict(), json_file, ensure_ascii=False, indent=4)


@app.websocket("/ws/video-processing/{session_id}")
async def video_processing(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:

        if session_id not in video_sessions:
            await websocket.send_text("Ошибка: Видео для данной сессии не найдено")
            await websocket.close()
            return

        session_folder = f"session_info_{session_id}"
        video: VideoFileClip = video_sessions[session_id]

        duration = video.duration
        count_chunks = duration // 2
        # count_chunks = 10
        logging.info(f"Начата обработка: количество чанков {count_chunks}")
        start_time = time.time()

        async def transcribe_video_chunk(video, chunk_id, semaphore):
            async with semaphore:
                whisper_response = await transcribe_by_chunk_id(video, chunk_id)
                logging.info(whisper_response)
                await websocket.send_text("1")
                return whisper_response

        semaphore = asyncio.Semaphore(1)

        tasks = [
            transcribe_video_chunk(video, chunk_id, semaphore)
            for chunk_id in range(0, int(count_chunks + 1))
        ]

        results = await asyncio.gather(*tasks)
        results_as_dict = [asdict(result) for result in results]
        with open(f'{session_folder}/transcribe.json', 'w', encoding='utf-8') as f:
            json.dump(results_as_dict, f, ensure_ascii=False, indent=4)
        end_time = time.time() - start_time
        logging.info(f"Обработано {count_chunks} за {end_time}")
        best_moments = await find_interesting_moment(results)
        if len(best_moments) >= 2:
            rang_best_moments = await sort_results(best_moments)
        else:
            best_moments = await find_two_moments(results)
            rang_best_moments = await sort_results(best_moments)
        save_moments(rang_best_moments, session_id)
        await websocket.send_text("2")

    except WebSocketDisconnect:
        logging.info(f"WebSocket для сессии {session_id} закрыт")
    finally:
        video_sessions.pop(session_id, None)


if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", log_level="debug")
    server = uvicorn.Server(config)
    server.run()
