import asyncio
import json
import logging
import os
import re
from time import sleep
from typing import List

from moviepy.video.io.VideoFileClip import VideoFileClip
from requests import session

from services.find_best import find_interesting_moment, sort_results, find_two_moments, ResultMoment
from services.transcibe import WhisperResponse, make_prediction

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M")

session_id = "8f46a547-a786-46d5-9dc9-979dada0a7b0"
with open('session_info_8f46a547-a786-46d5-9dc9-979dada0a7b0/transcribe.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

whisper_responses = [WhisperResponse(**item) for item in data]

print(whisper_responses)

async def process_batches(whisper_responses: List[WhisperResponse]):
    whisper_responses.sort(key=lambda x: x.start_time)
    best_moments = await find_interesting_moment(whisper_responses)
    if len(best_moments) >= 2:
        rang_best_moments = await sort_results(best_moments)
    else:
        best_moments = await find_two_moments(whisper_responses)
        rang_best_moments = await sort_results(best_moments)
    save_moments(rang_best_moments, session_id)

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

# запуск асинхронного кода
asyncio.run(process_batches(whisper_responses))