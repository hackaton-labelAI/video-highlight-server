import json
import logging
import os
import re
from dataclasses import dataclass
import random
from typing import List
from openai import AsyncOpenAI
from services.transcibe import WhisperResponse

openai = AsyncOpenAI(
            api_key=os.environ.get('MLP_TOKEN', '1000097868.108975.YgRqz5fhVIpjGS1scLLlwRqLU0M6wSj5oiWYNfYo'),
            base_url="https://caila.io/api/adapters/openai"
        )

prompt_template = """
По тексту сформируй релевантное название, описание и теги.
Название должно КРИЧАТЬ, должно быть короткое и максимально заманивающее, чтобы завлечь пользователя 
Описание должно быть не большим, но характеризовать суть текста
Теги должны отображать суть видео и быть самыми популярными штуки 3-4
Входные данные:  
%s

Выходные данные:  
json 
[{"title": str, "sub_text": str, "tags": list}]
"""

prompt= """
Сейчас тебе придёт транскрипция видео, тебе надо найти в ней интересные моменты, которые можно без контекста показать людям и они поймут о чём это и заинтересуются.

Соблюдай правила ниже!

Максимум 3 момента, комбинировать чанки надо от 6 до 90 элементов. 

Момент может заканчиваются только на лингвистических конструкции завершающие мысли, рассказ, итог и тд.!  

Важно смотреть, что идёт после момента, если там продолжается обсуждение этого момента, то значит мы не правильно выбрали момент, так как мысль не до конца сформулирована.

Не пытайся сильно сокращать моменты, в норме моменты должны быть примерно 30 чанков.


Ответ должен содержать массивы с id, причем если в одном массиве несколько id, то они отражают последовательные моменты. Не нужно группировать id, если между ними нет логической связи.

Формат входных данных: 
<id>. <text>

Ответ:
%s

json
{
  "sequences": [
    [<ids>], 
    ...
  ]
}
"""

def prompt_find_two(data):
    return f"""
Найди два интригующие моменты в тексте (ВАЖНО: тема должна начинаться и заканчиваться в предложениях, которые ты вернул. Лучше захватить лишние, чем упустить важное). Необходимо комбинировать чанки от 6 до 90 элементов, при этом можно делать наложение но мение 50%. 

Ответ должен содержать массивы с id, причем если в одном массиве несколько id, то они отражают последовательные моменты. Не нужно группировать id, если между ними нет логической связи.

Формат входных данных: 
<id>. <text>

Ответ:
{data}

json
{{
  "sequences": [
    [<ids>], 
    ...
  ]
}}
"""

prompt_for_sort= """
Отсортируй текстовые фрагменты так, чтобы на первых местах оказались те, которые заканчиваются наиболее логически завершенными конструкциями. Если несколько фрагментов заканчиваются логично, выбери тот, который кажется наиболее интересным или интригующим. 

Ответ должен быть представлен в виде массива объектов с полями id и description. 
- Поле id должно содержать идентификатор фрагмента.
- Поле description должно содержать краткое объяснение, почему именно этот фрагмент был поставлен на это место в списке относительно других. 
Важно: описание должно основываться на содержании текста, а не на каких-либо завершающих фразах или формальных признаках. Оценивай тексты именно по их содержательной ценности и логической завершенности.

Формат входных данных:
<id>. [<texts>]

Формат ответа:
```json
{
  "sortedTexts": [
    {"id": "<id>", "description": "<description>"}
  ]
}
"""


@dataclass
class ResultMoment:
    whisper_response: List[WhisperResponse]
    description: str
    title: str
    sub_text: str
    tags: List[str]

    def to_dict(self):
        return {
            'whisper_response': [response.to_dict() for response in self.whisper_response],
            'description': self.description,
            'title': self.title,
            'sub_text': self.sub_text,
            'tags': self.tags
        }

def data_to_string(data: List[WhisperResponse]) -> str:
    res = ""
    for id, item in enumerate(data):
        text = item.text.replace(".", "")
        cleaned_text = re.sub(r'[^a-zA-Zа-яА-Я0-9\s]', '', text)
        res += f"{id}. {cleaned_text.strip()}\n"
    return res

async def find_two_moments(data: List[WhisperResponse])->List[List[WhisperResponse]]:
    data.sort(key=lambda response: response.start_time)
    cleaned_data_string = data_to_string(data)
    gpt_response = await fetch_completion(prompt_find_two(cleaned_data_string))
    logging.info(prompt % data_to_string(data))
    logging.info(gpt_response['full_text'])
    tt = json.loads(gpt_response['full_text'])['sequences']
    results =[]
    res = []
    for item in tt:
        if item:
            if isinstance(item, list) and len(item) == 1 and isinstance(item[0], list):
                res.append(item[0])
            elif 5 < len(item) < 90:
                res.append(item[0:29])
    for moment in res:
        results.append([data[item] for item in moment])
    return results


async def find_interesting_moment(data: List[WhisperResponse])-> List[List[WhisperResponse]]:
    data.sort(key=lambda response: response.start_time)
    results = []
    for i in range((len(data) // 100 )+ 1):
        start = i * 100
        end = min(len(data), (i+1) * 100)
        current_data = data[start:end]
        gpt_response = await fetch_completion(prompt % data_to_string(current_data))
        logging.info(prompt % data_to_string(current_data))
        logging.info(gpt_response['full_text'])
        tt = json.loads(gpt_response['full_text'])['sequences']
        res = []
        for item in tt:
            if item:
                if isinstance(item, list) and len(item) == 1 and isinstance(item[0], list):
                    res.append(item[0])
                elif 5 < len(item) < 90:
                    res.append(item[0:29])
        for moment in res:
            results.append([data[item + start] for item in moment])
    return results

def sort_result_string(data: List[List[WhisperResponse]]):
    res = ""
    for id, item in enumerate(data):
        res += f"{id}. "
        for tt in item:
         res += f"{tt.text},"
        res += "\n"
    return res

async def sort_results(data: List[List[WhisperResponse]])-> List[ResultMoment]:
    #random.shuffle(data)
    gpt_response = await fetch_completion(prompt_for_sort %sort_result_string(data))
    logging.info(prompt_for_sort % sort_result_string(data))
    logging.info(gpt_response['full_text'])
    tt = json.loads(gpt_response['full_text'])['sortedTexts']
    tt = tt[0:20]
    moments =[]
    for item in tt:
        current_transcribe =  data[item['id']]
        response_content = await fetch_completion(prompt_template % str([text_and_time.text for text_and_time in current_transcribe ]))
        response_json = json.loads(response_content['full_text'])
        moments.append(ResultMoment(whisper_response=data[item['id']], description=item['description'],
                                    sub_text=response_json.get("sub_text", ""), tags=response_json.get("tags", []), title=response_json.get("title", "")))
    return moments

async def fetch_completion(prompt: str, count = 0):
    try:
        res = await openai.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="just-ai/openai-proxy/gpt-4o-mini",
            temperature=0,
            response_format={"type": "json_object"},
            stream=False
        )

        response_json = res
        input_tokens = int(res.usage.prompt_tokens)
        output_tokens = int(res.usage.completion_tokens)
        content = res.choices[0].message.content

        return {
            "response_json": response_json,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "full_text": content
        }
    except Exception as e:
      print(e)