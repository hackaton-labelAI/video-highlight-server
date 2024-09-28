import json
import logging
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from moviepy.video.io.VideoFileClip import VideoFileClip
from starlette.responses import FileResponse

from edit_video import process_video, generate_subtitles

router = APIRouter()

video_sessions = {}


@router.get("/project/{session_id}/videos")
async def get_videos(session_id: str):
    try:
        # Проверка session_id
        if not session_id:
            raise HTTPException(status_code=404, detail="Нет session_id")

        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Проверка существования папки сессии
        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        # Путь к папке 'chunks'
        chunks_folder = os.path.join(session_folder, "chunks")

        # Проверка существования папки 'chunks'
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'chunks' не найдена")

        # Получение всех mp4 файлов в папке 'chunks'
        mp4_files: List[str] = [f for f in os.listdir(chunks_folder) if f.endswith(".mp4")]

        if not mp4_files:
            raise HTTPException(status_code=404, detail="Нет mp4 файлов")

        videos_data = []

        for mp4_file in mp4_files:
            mp4_path = os.path.join(chunks_folder, mp4_file)

            # Путь к JSON файлу с таким же именем
            json_file = mp4_file.replace(".mp4", ".json")
            json_path = os.path.join(chunks_folder, json_file)

            # Проверка существования JSON файла
            if not os.path.exists(json_path):
                continue  # Пропускаем, если нет соответствующего JSON файла

            # Чтение JSON файла
            with open(json_path, "r") as file:
                json_data = json.load(file)

            # Добавляем данные в список
            videos_data.append({
                "file_name": mp4_file,
                "json_data": json_data
            })

        def extract_id_from_filename(filename):
            return int(filename.split(".mp4")[0])

        videos_data_sorted = sorted(videos_data, key=lambda x: extract_id_from_filename(x["file_name"]))

        return JSONResponse(content=videos_data_sorted)

    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файлов: {str(e)}")


@router.get("/project/{session_id}/open_video/{file_name}")
async def load_video_and_json(
        session_id: str,
        file_name: str,
        add_subtitles: bool,
        music_filename: Optional[str] = None,
        music_volume_delta: Optional[int] = 0,
        background_filename: Optional[str] = None

):
    try:
        if not session_id:
            raise HTTPException(status_code=404, detail="Нет session_id")

        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Проверка существования папки сессии
        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        # Путь к папке 'chunks'
        chunks_folder = os.path.join(session_folder, "chunks")

        # Путь к папке с фонами
        background_folder = os.path.join("data", "backgrounds")
        # Путь к папке с музыкой
        music_folder = os.path.join("data", "music")

        music_filename = os.path.join(music_folder, music_filename)
        background_filename = os.path.join(background_folder, background_filename)

        # Проверка существования папки 'chunks'
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'chunks' не найдена")
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'backgrounds' не найдена")
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'music' не найдена")
        if not os.path.exists(music_filename):
            raise HTTPException(status_code=404, detail="Указанная песня не существует. Выбирете другую")
        if not os.path.exists(background_filename):
            raise HTTPException(status_code=404, detail="Указанный фон не существует. Выбирете другой")

        mp4_path = os.path.join(chunks_folder, f"{file_name}.mp4")

        json_path = os.path.join(chunks_folder, f"{file_name}.json")
        video = VideoFileClip(mp4_path)
        video.write_videofile(os.path.join(session_folder, "current_work_video.mp4"))
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        json_path = os.path.join(session_folder, "current_work_video.json")
        with open(json_path, "w", encoding='utf-8') as json_file:  # Открываем в текстовом режиме
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        video_path = os.path.join(session_folder, "current_work_video.mp4")
        # ф-ция для создания файла с субтитрами
        generate_subtitles(json_path)
        process_video(video_path,
                      json_path,
                      path_to_save=session_folder,
                      add_subtitles=add_subtitles,
                      # subtitles_font_name
                      # subtitles_color_name
                      # subtitles_size
                      # subtitles_stroke
                      # subtitles_background
                      music_volume_delta=music_volume_delta,
                      music_filename=music_filename,
                      background_filename=background_filename,

                      )
        return FileResponse(video_path, media_type="video/mp4")

    except Exception as e:
        logging.error(f"Ошибка получения фрейма: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения фрейма: {str(e)}")


@router.get("/project/{session_id}/current_video")
async def get_current_work_video(session_id: str):
    try:
        session_folder = f"session_info_{session_id}"
        video_path = os.path.join(session_folder, "current_work_video.mp4")

        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Видео не найдено")

        return FileResponse(video_path, media_type="video/mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении видео: {str(e)}")


@router.get("/project/{session_id}/video/{file_name}/frame")
async def get_video_frame(session_id: str, file_name: str):
    try:
        # Проверка session_id
        if not session_id:
            raise HTTPException(status_code=404, detail="Нет session_id")

        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Путь к папке 'chunks'
        chunks_folder = os.path.join(session_folder, "chunks")

        # Проверка существования папки 'chunks'
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'chunks' не найдена")

        # Путь к mp4 файлу
        mp4_path = os.path.join(chunks_folder, file_name)

        # Проверка существования mp4 файла
        if not os.path.exists(mp4_path) or not file_name.endswith(".mp4"):
            raise HTTPException(status_code=404, detail="mp4 файл не найден")

        # Загружаем видео и сохраняем первый фрейм
        clip = VideoFileClip(mp4_path)
        frame_path = os.path.join(chunks_folder, f"{file_name}_first_frame.png")
        clip.save_frame(frame_path, t=0)

        # Возвращаем фрейм как изображение
        return FileResponse(frame_path, media_type="image/png")

    except Exception as e:
        logging.error(f"Ошибка получения фрейма: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения фрейма: {str(e)}")


@router.get("/project/{session_id}/{file_id}")
async def upload_video(session_id: str, file_id: int):
    try:
        # Путь к папке сессии
        session_folder = f"session_info_{session_id}"

        # Проверка существования папки сессии
        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        # Путь к папке 'chunks' внутри папки сессии
        chunks_folder = os.path.join(session_folder, "chunks")

        # Проверка существования папки 'chunks'
        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'chunks' не найдена")

        # Путь к видео и JSON файлам
        video_path = os.path.join(chunks_folder, f"{file_id}.mp4")
        json_path = os.path.join(chunks_folder, f"{file_id}.json")

        # Проверка существования видео и JSON файлов
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Видео не найдено")
        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="JSON файл не найден")

        # Чтение JSON файла
        with open(json_path, "r") as file:
            json_data = json.load(file)

        # Возврат видео файла и JSON данных
        return {
            "video": FileResponse(video_path, media_type="video/mp4"),
            "json_data": json_data
        }

    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")


@router.post("/project/{session_id}/{file_id}")
async def upload_video(session_id: str, file_id: int):
    try:
        session_folder = f"session_info_{session_id}"

        if not os.path.exists(session_folder):
            raise HTTPException(status_code=404, detail="Файл не найден")

        chunks_folder = os.path.join(session_folder, "chunks")

        if not os.path.exists(chunks_folder):
            raise HTTPException(status_code=404, detail="Папка 'chunks' не найдена")

        video_path = os.path.join(chunks_folder, f"{file_id}.mp4")
        json_path = os.path.join(chunks_folder, f"{file_id}.json")

        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Видео не найдено")
        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="JSON файл не найден")


    except Exception as e:
        logging.error(f"Ошибка загрузки видео: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")
