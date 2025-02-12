import streamlit as st

# Set page config FIRST
st.set_page_config(page_title="AI Code Debugger", layout="wide")

# Import other modules AFTER page config
import json
import os
import google.generativeai as genai
from google.cloud import vision
from google.oauth2 import service_account
from typing import Dict, List

# Initialize session state
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'current_code' not in st.session_state:
    st.session_state.current_code = ""

# Load credentials without Streamlit components
credentials = None
google_api_key = os.getenv("GOOGLE_API_KEY")

try:
    if cred_json := os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(cred_json)
        )
    genai.configure(api_key=google_api_key)
except Exception as e:
    credentials = None

# Start Streamlit UI components
st.title("🛠️ AI-Powered Code Debugger")

# Validate credentials and API key
if not credentials:
    st.error("❌ Missing or invalid Google Cloud credentials")
    st.info("Ensure GOOGLE_APPLICATION_CREDENTIALS_JSON is set with valid service account JSON")
    st.stop()

if not google_api_key:
    st.error("❌ Missing Google API Key")
    st.info("Set GOOGLE_API_KEY environment variable")
    st.stop()

# Configure AI model
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

def analyze_code(code: str, language: str) -> Dict:
    """Analyze code using Gemini AI"""
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
            
        cleaned_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
        
    except json.JSONDecodeError:
        return {"error": "❌ Failed to parse AI response"}
    except Exception as e:
        return {"error": f"❌ Analysis failed: {str(e)}"}

def extract_code_from_image(image) -> str:
    """Extract code from image using Google Vision"""
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

# Display Results
if st.session_state.analysis_results:
    results = st.session_state.analysis_results
    
    if "error" in results:
        st.error(results["error"])
    else:
        st.subheader("🔍 Analysis Results")
        
        with st.expander("🐛 Identified Bugs", expanded=True):
            for bug in results.get("bugs", []):
                st.error(f"- {bug}")
        
        with st.expander("🛠️ Suggested Fixes"):
            for fix in results.get("fixes", []):
                st.info(f"- {fix}")
        
        with st.expander("✅ Corrected Code"):
            st.code(results.get("corrected_code", ""), language=language)
        
        with st.expander("⚡ Optimizations"):
            for opt in results.get("optimizations", []):
                st.success(f"- {opt}")
        
        with st.expander("📚 Explanation"):
            for exp in results.get("explanation", []):
                st.write(f"- {exp}")
