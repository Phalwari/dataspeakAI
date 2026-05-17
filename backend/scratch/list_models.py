import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

res = requests.get(url)
print(f"Status: {res.status_code}")
if res.status_code == 200:
    for model in res.json().get("models", []):
        print(model.get("name"))
else:
    print(res.text)
