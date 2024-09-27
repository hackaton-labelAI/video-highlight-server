import os
from typing import List
from openai import AsyncOpenAI
from services.transcibe import WhisperResponse

openai = AsyncOpenAI(
            api_key=os.environ.get('MLP_TOKEN', '1000097868.108975.YgRqz5fhVIpjGS1scLLlwRqLU0M6wSj5oiWYNfYo'),
            base_url="https://caila.io/api/adapters/openai"
        )

prompt= """
Найди интригующий момент в тексте до 3 штук, который понятен без контекста длиной от 10 секунд до 180.
Ответ должен содержать массивы с id, каждый из которых отражает интересный момент последовательности, важно если они в одной массиве они должны быть последовательны.
Формат входных данных <id>. <start_sec>-><end_sec> <text>
Текст:
%s 

Ответ:
json
{sequences:[[<ids>], ...]}
"""



def data_to_string(data: List[WhisperResponse])-> str:
    res = ""
    for id, item in enumerate(data):
        res += f"{id}. {item.start_time}->{item.end_time} {item.text}\n"
    return res

async def find_interesting_moment(data: List[WhisperResponse]):
    data.sort(key=lambda response: response.start_time)
    gpt_response = await fetch_completion(prompt %data_to_string(data))
    print(prompt %data_to_string(data))
    print()
    print(gpt_response['full_text'])


async def fetch_completion(prompt: str):
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