import streamlit as st
import json
import google.generativeai as genai
from google.cloud import vision
from google.oauth2 import service_account
import subprocess
from datetime import datetime
from typing import Dict, List
import os

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'current_code' not in st.session_state:
    st.session_state.current_code = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Load credentials correctly from GitHub Secrets
credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

if credentials_json:
    try:
        credentials_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp_credentials.json"
        print("✅ Google Cloud credentials successfully loaded!")
        print("🔍 PROJECT ID:", credentials.project_id)
        print("🔍 CLIENT EMAIL:", credentials.service_account_email)
    except Exception as e:
        print(f"⚠️ Error loading credentials: {str(e)}")
        credentials = None
else:
    print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON is missing!")
    credentials = None

# Test authentication
try:
    client = vision.ImageAnnotatorClient(credentials=credentials)
    print("✅ Successfully connected to Google Cloud Vision API!")
except Exception as e:
    print(f"⚠️ Failed to connect to Vision API: {str(e)}")

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = genai.GenerativeModel('gemini-pro',
    safety_settings={
        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE'
    },
    generation_config=genai.types.GenerationConfig(
        max_output_tokens=4000,
        temperature=0.25
    )
)

# Code Analysis Function
def analyze_code(code: str, language: str) -> Dict:
    """Analyze code using Gemini with error handling"""
    try:
        prompt = f"""Analyze this {language} code and provide:
        1. List of bugs with line numbers
        2. Suggested fixes
        3. Corrected code
        4. Performance optimizations
        5. Detailed explanation
        
        Format response as JSON with keys:
        - bugs (list of strings)
        - fixes (list of strings)
        - corrected_code (string)
        - optimizations (list of strings)
        - explanation (list of strings)
        
        Code:\n{code}"""

        response = MODEL.generate_content(prompt)
        
        if not response.text:
            return {"error": "❌ No response from AI model"}
            
        # Clean Gemini's response
        cleaned_response = response.text.replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
        
    except json.JSONDecodeError:
        return {"error": "❌ Failed to parse AI response"}
    except Exception as e:
        return {"error": f"❌ Analysis failed: {str(e)}"}

# AI Assistant Sidebar
def ai_assistant():
    st.sidebar.title("🧠 AI Assistant")
    st.sidebar.write("Ask coding questions or get debugging help!")
    sidebar_query = st.sidebar.text_input("Your question:")
    if sidebar_query:
        response = MODEL.generate_content(sidebar_query)
        st.sidebar.write(response.text if response else "⚠️ No response")
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Usage Tips**\n"
                    "1. Upload clear code images\n"
                    "2. Review analysis sections\n"
                    "3. Ask follow-up questions\n"
                    "4. Implement suggestions")

# Image Processing
def extract_code_from_image(image) -> str:
    """Extract code from image using Google Vision"""
    if not credentials:
        return "⚠️ Invalid credentials: Check your Google Cloud setup."

    try:
        client = vision.ImageAnnotatorClient(credentials=credentials)
        content = image.read()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        
        if response.error.message:
            return f"⚠️ Vision API Error: {response.error.message}"
        
        if response.text_annotations:
            return response.text_annotations[0].description.strip()
        
        return "⚠️ No text detected in image."
    except Exception as e:
        return f"⚠️ OCR Error: {str(e)}"

# Streamlit UI
st.set_page_config(page_title="AI Code Debugger", layout="wide")
st.title("🛠️ AI-Powered Code Debugger")
st.write("Upload code via image/file or paste directly for analysis")

# Initialize AI Assistant
ai_assistant()

# Input Methods
input_method = st.radio("Choose input method:", 
                       ["📷 Image Upload", "📁 File Upload", "📝 Paste Code"],
                       horizontal=True)

code_text = ""
language = "python"

# Handle Image Upload
if input_method == "📷 Image Upload":
    image_file = st.file_uploader("Upload code image", type=["png", "jpg", "jpeg"])
    if image_file:
        code_text = extract_code_from_image(image_file)
        st.code(code_text, language="python")

# Handle File Upload
elif input_method == "📁 File Upload":
    code_file = st.file_uploader("Upload code file", type=["py", "java", "js"])
    if code_file:
        code_text = code_file.read().decode("utf-8")
        ext = code_file.name.split(".")[-1]
        language = {"py": "python", "java": "java", "js": "javascript"}.get(ext, "python")
        st.code(code_text, language=language)

# Handle Paste Code
else:
    code_text = st.text_area("Paste your code here:", height=300)
    if code_text:
        st.code(code_text, language="python")

# Analysis Execution
if st.button("🚀 Analyze Code") and code_text.strip():
    st.session_state.current_code = code_text
    with st.spinner("🔍 Analyzing code..."):
        st.session_state.analysis_results = analyze_code(code_text, language)
