import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import shutil
import os

from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить запросы от любых источников
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
)

UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return JSONResponse(content={"message": "Файл успешно загружен", "filename": file.filename})

    except Exception as e:
        return JSONResponse(content={"message": f"Ошибка загрузки файла: {str(e)}"}, status_code=500)


@app.get("/process_video/{filename}")
async def process_video(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        return JSONResponse(content={"message": "Файл не найден"}, status_code=404)

    return JSONResponse(content={"message": f"Видео обработано: {filename}"})

if __name__ == "__main__":
    print("hi")
    config = uvicorn.Config("main:app", host="0.0.0.0", log_level="debug")
    server = uvicorn.Server(config)
    server.run()