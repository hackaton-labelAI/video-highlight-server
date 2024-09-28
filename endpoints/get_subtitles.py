from fastapi import Depends
import logging
import os
from fastapi import APIRouter, HTTPException

@router.get("/project/{session_id}/subtitles")
async def get_subtitles(session_id: str, video_name: str):
    try:
        session_folder = f"session_info_{session_id}"
        subtitles_path = os.path.join(session_folder, f"{video_name}.srt")

        if not os.path.exists(subtitles_path):
            raise HTTPException(status_code=404, detail="Файл субтитров не найден")

        with open(subtitles_path, 'r', encoding='utf-8') as file:
            subtitles_content = file.read()

        return {"subtitles": subtitles_content}

    except Exception as e:
        logging.error(f"Ошибка получения субтитров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения субтитров: {str(e)}")
