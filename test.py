import asyncio
import json
import re

from services.find_best import find_interesting_moment
from services.transcibe import WhisperResponse



with open('whisper_responses.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

whisper_responses = [WhisperResponse(**item) for item in data]

print(whisper_responses)

asyncio.run(find_interesting_moment(whisper_responses[50:100]))
