import asyncio
import json
import logging
import re
from time import sleep
from typing import List

from services.find_best import find_interesting_moment, sort_results
from services.transcibe import WhisperResponse, make_prediction

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M")


with open('whisper_responses.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

whisper_responses = [WhisperResponse(**item) for item in data]

print(whisper_responses)

async def process_batches(whisper_responses: List[WhisperResponse]):
    whisper_responses.sort(key=lambda x: x.start_time)
    results = []
    for i in range((len(whisper_responses) // 50 )+ 1):
        start = i * 50
        end = min(len(whisper_responses), (i+1) * 50)
        res = await find_interesting_moment(whisper_responses[start:end])
        for moment in res:
            results.append([item + start for item in moment])
    print(results)
    if len(results) >= 2:
        for_sort_request = []
        for moment in results:
            whisper_responses_result = [whisper_responses[index] for index in moment]
            for_sort_request.append(whisper_responses_result)
        print(for_sort_request)
        sort_results(for_sort_request)
# запуск асинхронного кода
asyncio.run(process_batches(whisper_responses))