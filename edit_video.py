import json
import math
import os

import cv2
import moviepy.editor as mpe
import numpy as np
import pysrt
from deepface import DeepFace
from moviepy.editor import TextClip, CompositeVideoClip
from pydub import AudioSegment


def convert_seconds_to_time(seconds):
    # Получаем целую часть секунд (количество секунд)
    total_seconds = int(seconds)

    # Вычисляем часы, минуты и секунды
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    # Получаем миллисекунды
    milliseconds = int((seconds - total_seconds) * 1000)

    # Форматируем результат
    time_str = f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    return time_str


def generate_subtitles(json_filepath):
    print(json_filepath)
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data = data['whisper_response']

    lines = []
    i = 1
    shift = data[0]['start_time']
    for sentence in data:
        output_data = f'{i}\n{convert_seconds_to_time(sentence["start_time"] - shift)} --> {convert_seconds_to_time(sentence["end_time"] - shift)}\n{sentence["text"]}\n\n'
        i += 1
        lines.append(output_data)

    # Удаление содержимого существующего файла
    with open('subtitles.srt', 'w') as file:
        file.writelines(lines)

    with open('subtitles.srt', 'r') as f:
        data = f.read()
        return str(data)




def srt_to_utf8(filename='subtitles.srt'):
    try:
        # Открываем входной файл в кодировке UTF-8 с ignore-ошибками
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Сохраняем файл в кодировке UTF-8
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Файл '{filename}' успешно конвертирован в UTF-8 и сохранен как '{filename}'.")
    except UnicodeDecodeError:
        # Если возникла ошибка декодирования, пробуем открыть файл в другой кодировке
        try:
            with open(filename, 'r', encoding='cp1252') as f:
                content = f.read()
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Файл '{filename}' успешно конвертирован в UTF-8 и сохранен как '{filename}'.")
        except Exception as e:
            print(f"Ошибка при конвертации файла '{filename}': {e}")
    except Exception as e:
        print(f"Ошибка при конвертации файла '{filename}': {e}")


def ssim(matrix_1: np.ndarray, matrix_2: np.ndarray):
    def covariation(matrix_1: np.ndarray, matrix_2: np.ndarray):
        _width = matrix_1.shape[1]
        _height = matrix_1.shape[0]

        mean_m1 = np.mean(matrix_1)
        mean_m2 = np.mean(matrix_2)

        cov_sum = 0
        for y in range(_height):
            for x in range(_width):
                cov_sum += (matrix_1[y][x] - mean_m1) * (matrix_2[y][x] - mean_m2)

        return cov_sum / (_width * _height)

    mean_m1 = np.mean(matrix_1)
    mean_m2 = np.mean(matrix_2)
    var_m1 = np.var(matrix_1)
    var_m2 = np.var(matrix_2)
    return (
            (covariation(matrix_1, matrix_2) / (math.sqrt(var_m1) * math.sqrt(var_m2))) *
            ((2 * mean_m1 * mean_m2) / (mean_m1 ** 2 + mean_m2 ** 2)) *
            ((2 * math.sqrt(var_m1) * math.sqrt(var_m2)) / (var_m1 + var_m2))
    )


def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000


def create_subtitle_clips(subtitles, videosize, fontsize=24, font='Tahoma-Полужирный', color='white',
                          stroke_color='purple', subtitles_high=None, bg_color=None, debug=False):
    subtitle_clips = []

    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time

        video_width, video_height = videosize

        if not stroke_color:
            stroke_color = color

        if not bg_color:
            text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, stroke_color=stroke_color,
                                 stroke_width=1.0,
                                 size=(video_width * 3 / 4, None), method='caption').set_start(start_time).set_duration(
                duration)
        else:
            text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, stroke_color=stroke_color,
                                 bg_color=bg_color,
                                 stroke_width=1.0,
                                 size=(video_width * 3 / 4, None), method='caption').set_start(start_time).set_duration(
                duration)

        subtitle_x_position = 'center'
        subtitle_y_position = video_height * 3 / 5 if not subtitles_high else subtitles_high

        text_position = (subtitle_x_position, subtitle_y_position)
        subtitle_clips.append(text_clip.set_position(text_position))

    return subtitle_clips


def process_video(input_filename, json_filepath,
                  music_volume_delta=-20,
                  add_subtitles=True,
                  subtitles_highness=None,
                  subtitles_font_name="Tahoma-Полужирный",
                  subtitles_color_name="white",
                  subtitles_size=24,
                  subtitles_stroke=None,
                  subtitles_background=None,
                  background_filename=None,
                  music_filename=None):
    # Open the video file

    video = cv2.VideoCapture(input_filename)
    audio = AudioSegment.from_file(input_filename, "mp4")
    offset = 50
    fps = video.get(cv2.CAP_PROP_FPS)

    # Get the video dimensions
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    new_width_half = int((height * 9) / 32)
    ssim_threshold = 0.7
    last_frame = np.ones(shape=(0,))
    frame_number = 0

    # Create a VideoWriter object to save the cropped video
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output_video.avi', fourcc, fps, (new_width_half * 2, height))

    last_x1, last_y1 = width // 2 - new_width_half, 0
    last_x2, last_y2 = width // 2 + new_width_half, height

    # Loop through the video frames and crop them
    while True:
        ret, frame = video.read()

        if ret != True:
            break

        # вычисление метрики сходства кадров
        ssim_metric = ssim(cv2.resize(cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY), (32, 32)),
                           cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                                      (32, 32))) if not frame_number == 0 else 0
        if frame_number == 0 or ssim_metric < ssim_threshold:
            try:
                faces = DeepFace.extract_faces(frame, detector_backend='opencv')
            except ValueError:
                faces = None

            if faces:
                the_most_confident_face = max(faces, key=lambda x: x['confidence'])
                x1, y1 = the_most_confident_face['facial_area']['x'] - new_width_half + offset, 0  # Top-left corner
                x2, y2 = the_most_confident_face['facial_area']['x'] + new_width_half + offset, height
                if x1 < 0:
                    x1 = 0
                    x2 = new_width_half * 2
                if x2 > width:
                    x2 = width
                    x1 = width - new_width_half * 2
            else:
                x1, y1 = last_x1, 0
                x2, y2 = last_x2, height

        else:
            x1, y1 = last_x1, 0
            x2, y2 = last_x2, height

        cropped_frame = frame[y1:y2, x1:x2]
        last_frame = frame
        last_x1, last_y1 = x1, 0
        last_x2, last_y2 = x2, height
        frame_number += 1

        out.write(cropped_frame)

    # Release the video capture and output objects
    video.release()
    out.release()
    cv2.destroyAllWindows()

    my_clip = mpe.VideoFileClip("output_video.avi", has_mask=True)

    # считывание оригинального аудио
    original_video = mpe.VideoFileClip(input_filename)
    audio = original_video.audio

    # добавляем фон
    if background_filename:
        width, height = my_clip.size
        background_file = mpe.VideoFileClip(background_filename, target_resolution=(height, width))
        background_file = background_file.loop(duration=audio.duration)

        # resize clip
        width, height = my_clip.size
        my_clip = my_clip.resize(0.9)

        print(background_file.size)

        my_clip = mpe.CompositeVideoClip([background_file, my_clip.set_position((0.05, 0.05), relative=True)],
                                         use_bgclip=True)

    # добавление фоновой музыки
    if music_filename:
        if music_volume_delta:
            song = AudioSegment.from_mp3(music_filename)
            song = song + music_volume_delta
            song_format = music_filename.split('.')[-1]
            music_filename = music_filename.split('.')[0] + 'new_volume' + song_format
            song.export(music_filename, song_format)

        music = mpe.AudioFileClip(music_filename)
        music = mpe.afx.audio_loop(music, duration=audio.duration)
        mpe.CompositeAudioClip([audio, music]).write_audiofile("output_audio.mp3", fps=44100)
    else:
        # добавление аудио
        audio.write_audiofile("output_audio.mp3")

    audio_background = mpe.AudioFileClip('output_audio.mp3')
    final = my_clip.set_audio(audio_background)

    # добавление субтитров
    if add_subtitles:
        generate_subtitles(json_filepath)
        srtfilename = 'subtitles.srt'
        subtitles = pysrt.open(srtfilename)
        subtitle_clips = create_subtitle_clips(subtitles,
                                               final.size,
                                               fontsize=subtitles_size,
                                               font=subtitles_font_name,
                                               color=subtitles_color_name,
                                               stroke_color=subtitles_stroke,
                                               subtitles_high=subtitles_highness,
                                               bg_color=subtitles_background)
        final_video = CompositeVideoClip([final] + subtitle_clips)
    else:
        final_video = final

    # Удаление файлов
    os.remove('output_video.avi')
    os.remove('output_audio.mp3')
    os.remove('subtitles.srt')
    print('delegted')
    if music_filename:
        os.remove(music_filename)

    final_video.write_videofile(input_filename, codec='libx264', audio_codec='aac',
                                audio=True, threads=6)


if __name__ == '__main__':
    # process_video(background_filename='background.mp4', music_volume_delta=-15, music_filename='music_lofi.mp3')
    # generate_subtitles('session_info_8f46a547-a786-46d5-9dc9-979dada0a7b0/current_work_video.json')
    # print(TextClip.list('color'))
    with open('session_info_8f46a547-a786-46d5-9dc9-979dada0a7b0/current_work_video.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
