from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv("configs/.env")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

response = client.chat.completions.create(
    model="claude-sonnet-4-6",
    messages=[
        {"role": "user", "content": "Say hello in Korean."}
    ],
)

print(response.choices[0].message.content)

load_dotenv("configs/.env")

# 추가
print(os.getenv("OPENAI_API_KEY"))
print(os.getenv("OPENAI_BASE_URL"))