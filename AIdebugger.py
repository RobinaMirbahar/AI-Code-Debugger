import streamlit as st
import json
import os
import google.generativeai as genai
from google.cloud import vision
from google.oauth2 import service_account
import subprocess

# Set Google Cloud Credentials
def set_google_credentials():
    service_account_info = json.loads(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    return credentials

# Configure Gemini AI API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
SAFETY_SETTINGS = {
    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE'
}
GENERATION_CONFIG = genai.types.GenerationConfig(
    max_output_tokens=4000,
    temperature=0.25
)
MODEL = genai.GenerativeModel('gemini-pro',
    safety_settings=SAFETY_SETTINGS,
    generation_config=GENERATION_CONFIG
)

# AI Assistant Sidebar with Tooltips
def ai_assistant():
    st.sidebar.title("🧠 AI Assistant")
    st.sidebar.write("Ask me anything about debugging and coding!")
    user_query = st.sidebar.text_input("🔍 Your question:", help="Type your query here and get AI-generated insights.")
    if user_query:
        response = MODEL.generate_content(f"Provide guidance for: {user_query}")
        st.sidebar.write(response.text if response else "⚠️ No response from AI")

# Code Execution Function
def execute_code(code, language):
    try:
        if language == "python":
            result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=5)
        elif language == "javascript":
            result = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=5)
        elif language == "java":
            with open("Temp.java", "w") as f:
                f.write(code)
            result = subprocess.run(["javac", "Temp.java"], capture_output=True, text=True)
            if result.returncode == 0:
                result = subprocess.run(["java", "Temp"], capture_output=True, text=True, timeout=5)
        else:
            return "⚠️ Execution not supported for this language."
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Execution Error: {str(e)}"

# AI Code Analysis Function
def analyze_code(code_snippet, language="python"):
    if not code_snippet.strip():
        return {"error": "⚠️ No code provided"}
    
    execution_result = execute_code(code_snippet, language)
    
    if "Error" not in execution_result and "Exception" not in execution_result:
        return {
            "bugs": "✅ No issues detected in the code.",
            "fix": "No fixes needed as the code is correctly implemented.",
            "corrected_code": "The uploaded code is already correct. No modifications were necessary.",
            "execution_result": execution_result,
            "optimization": "No further optimizations required."
        }
    
    prompt = f"""Analyze and correct this {language} code:
    ```{language}
    {code_snippet}
    ```
    Provide structured JSON output:
    {{
        "bugs": "Identified issues in the code",
        "fix": "Steps to fix the issues",
        "corrected_code": "Fixed version of the code",
        "execution_result": "Expected execution results",
        "optimization": "Suggested improvements"
    }}
    """
    try:
        response = MODEL.generate_content(prompt)
        structured_response = json.loads(response.text) if response else {}
        structured_response["execution_result"] = execute_code(structured_response.get("corrected_code", ""), language)
        return structured_response
    except Exception as e:
        return {"error": f"⚠️ Analysis failed: {str(e)}"}

# Extract Code from Image
def extract_code_from_image(image):
    credentials = set_google_credentials()
    client = vision.ImageAnnotatorClient(credentials=credentials)
    content = image.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    if texts:
        return texts[0].description
    return "⚠️ No text detected in image."

# Initialize Credentials
credentials = set_google_credentials()

# Streamlit UI
st.title("🛠️ AI Code Debugger with Google Vision & Gemini API")
st.write("Upload an image of handwritten or printed code, upload a code file, or paste code manually for debugging and optimization.")

# Initialize AI Assistant
ai_assistant()

# Image Upload Debugging Feature
st.subheader("🖼️ Upload Image with Code")
st.write("Upload an image containing code, and AI will extract and debug it.")
uploaded_image = st.file_uploader("📂 Choose an image file", type=["png", "jpg", "jpeg"], help="Supported formats: PNG, JPG, JPEG")
if uploaded_image is not None:
    st.image(uploaded_image, caption="Uploaded Image", use_container_width=True)
    extracted_code = extract_code_from_image(uploaded_image)
    st.subheader("📜 Extracted Code:")
    st.code(extracted_code, language="python")
    analysis_result = analyze_code(extracted_code)
    st.subheader("🔍 AI Debugging Analysis:")
    st.write(analysis_result)

# File Upload Debugging Feature
st.subheader("📂 Upload Code File for Debugging")
st.write("Upload a code file for AI analysis and debugging.")
uploaded_code_file = st.file_uploader("Choose a code file", type=["py", "java", "js"], help="Supported formats: Python (.py), Java (.java), JavaScript (.js)")
if uploaded_code_file is not None:
    code_text = uploaded_code_file.read().decode("utf-8")
    
    extension = uploaded_code_file.name.split(".")[-1]
    language_map = {"py": "python", "java": "java", "js": "javascript"}
    language = language_map.get(extension, "python")
    
    st.subheader("📜 Uploaded Code:")
    st.code(code_text, language=language)
    
    analysis_result = analyze_code(code_text, language)
    st.subheader("🔍 AI Debugging Analysis:")
    st.write(analysis_result)
