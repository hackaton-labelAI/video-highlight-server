import json
import re


# Helper function to convert seconds to SRT time format (HH:MM:SS,MS)
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    sec = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{sec:02},{milliseconds:03}"


# Function to filter and leave only Russian letters
def filter_russian(text):
    return re.sub(r'[^а-яА-ЯёЁ ]+', '', text)


# Function to convert JSON to SRT
def json_to_srt(json_data):
    srt_content = ""

    for index, entry in enumerate(json_data, start=1):
        start_time = format_time(entry['start_time'])
        end_time = format_time(entry['end_time'])

        # Filter text to include only Russian letters
        filtered_text = filter_russian(entry['text'].strip())

        srt_content += f"{index}\n{start_time} --> {end_time}\n{filtered_text}\n\n"

    # Write to file
    file_path = "output_russian_onlyd.srt"
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(srt_content)


# Load the input JSON data
json_data = [
    {
        "text": " .",
        "start_time": 0.0,
        "end_time": 2.0
    },
    {
        "text": " You",
        "start_time": 2.0,
        "end_time": 4.0
    },
    {
        "text": " You",
        "start_time": 4.0,
        "end_time": 6.0
    }
]
with open('data/vidio.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
# Convert JSON to SRT format
srt_output = json_to_srt(data)

# Print the SRT content
print(srt_output)
