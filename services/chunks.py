from typing import List

from moviepy.video.io.VideoFileClip import VideoFileClip


def create_chunks(video: VideoFileClip, chunk_duration: int, overlap: int)-> List[VideoFileClip]:
    start = 0
    chunks = []
    while start < video.duration:
        end = min(start + chunk_duration, video.duration)
        chunk = video.subclip(start, end)
        chunks.append(chunk)
        start += chunk_duration - overlap
    return chunks

def calculate_chunks(duration, chunk_size=10):
    num_chunks = max(1, int(duration // chunk_size))
    return num_chunks
