import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
try:
    print(model.generate_content('test').text)
except Exception as e:
    print(f"Exception Type: {type(e)}")
    print(f"Exception String: {str(e)}")
