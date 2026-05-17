import sys
sys.path.append('.')
import os
import base64
import requests
import fitz
from dotenv import load_dotenv

# Load env variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
print(f"Loaded API Key: {api_key}")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    sys.exit(1)

# Extract image from PDF
file_path = "uploads/rag_test_document.pdf"
doc = fitz.open(file_path)
page = doc[0]
image_list = page.get_images(full=True)
if not image_list:
    print("Error: No images found in PDF")
    sys.exit(1)

xref = image_list[0][0]
base_image = doc.extract_image(xref)
image_bytes = base_image["image"]
image_b64 = base64.b64encode(image_bytes).decode('utf-8')

print("Sending request to Gemini 2.5 Flash API...")
gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
payload = {
    "contents": [{
        "parts": [
            {"text": "Analyze this chart, diagram, or image from a technical document. Perform high-precision OCR on any text, figures, and numbers, and generate a detailed visual analysis of the trends and key takeaways."},
            {
                "inlineData": {
                    "mimeType": "image/png",
                    "data": image_b64
                }
            }
        ]
    }]
}
headers = {"Content-Type": "application/json"}

try:
    res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
    print(f"Response Status Code: {res.status_code}")
    if res.status_code == 200:
        res_data = res.json()
        print("\n--- GEMINI RESPONSE ---")
        print(res_data["candidates"][0]["content"]["parts"][0]["text"])
        print("-----------------------")
    else:
        print(f"Error Response: {res.text}")
except Exception as e:
    print(f"HTTP Request failed: {e}")
