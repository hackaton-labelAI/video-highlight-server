import base64
import os
import tempfile
import httpx

from moviepy.video.io.VideoFileClip import VideoFileClip
from starlette.websockets import WebSocket


def _encode_audio_to_base64(audio_path):
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
        base64_encoded = base64.b64encode(audio_data).decode('utf-8')
    return base64_encoded

async def transcribe_by_chunk_id(vidio: VideoFileClip, chunk_id: int):
    start_time = chunk_id * 10
    end_time = min(vidio.duration, start_time+15)
    chunk: VideoFileClip = vidio.subclip(start_time, end_time)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
        temp_audio_path = temp_audio_file.name
        chunk.audio.write_audiofile(temp_audio_path)

    base64_string = _encode_audio_to_base64(temp_audio_path)
    text = await make_prediction(base64_string)
    return start_time, end_time, text


async def make_prediction(base64_string: str)-> str:
    api_token = os.environ.get('MLP_TOKEN', '1000097868.108975.YgRqz5fhVIpjGS1scLLlwRqLU0M6wSj5oiWYNfYo')
    url = 'https://caila.io/api/mlpgate/account/just-ai/model/faster-whisper-large/predict'

    headers = {
        'MLP-API-KEY': api_token,
        'Content-Type': 'application/json',
    }

    body = {
        "audio_base64": base64_string
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)

        if response.status_code == 200:
            return response.json()['text']
        else:
            response.raise_for_status()