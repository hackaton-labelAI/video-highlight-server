from fastapi import Depends
import logging
import os
from fastapi import APIRouter, HTTPException


@router.get("/project/{session_id}/subtitles")
async def get_subtitles(session_id: str):
    try:
        session_folder = f"session_info_{session_id}"
        subtitles_path = os.path.join(session_folder, "subtitles.srt")

        if not os.path.exists(subtitles_path):
            raise HTTPException(status_code=404, detail="Файл с субтитрами нет")

        with open(subtitles_path, 'r', encoding='utf-8') as file:
            subtitles_content = file.read()

        return {"subtitles": subtitles_content}

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
