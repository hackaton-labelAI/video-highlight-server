import logging
import os

from fastapi import APIRouter, HTTPException

from edit_video import generate_subtitles

router = APIRouter()


@router.get("/project/{session_id}/subtitles/{filename}")
async def get_subtitles(session_id: str, filename: int):
    try:
        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Проверка существования папки сессии
        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        chunks_folder = os.path.join(session_folder, "chunks")

        json_path = os.path.join(chunks_folder, f"{filename}.json")

        if os.path.exists("users_subtitles.srt"):
            with open('users_subtitles.srt', 'r') as f:
                data = f.read()
            return data
        else:
            return generate_subtitles(json_path)

    except Exception as e:
        logging.error(f"Ошибка получения субтитров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения субтитров: {str(e)}")


@router.post("/project/{session_id}/subtitles/{filename}")
async def get_subtitles(session_id: str, filename: int, input_str):
    try:
        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Проверка существования папки сессии
        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        # if input_str[0] == '\"' and input_str[-1] == '\"':
        #     input_str = input_str[1:-1]
        lines = input_str.split('\n')

        with open(f'users_subtitles.srt', 'w') as file:
            print(lines)
            if input_str[0] == '\"' and input_str[-1] == '\"':
                input_str = input_str[1:-1].replace(r'\n', '\n')

            # for line in lines:
            #     file.write(line)
            #     file.write('\n')
            file.write(input_str)

    except Exception as e:
        logging.error(f"Ошибка записи субтитров: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка записи субтитров: {str(e)}")
