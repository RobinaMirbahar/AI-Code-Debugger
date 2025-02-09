import google.generativeai as genai
import streamlit as st
import re
from datetime import datetime

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_data(show_spinner=False)
def correct_code(code_snippet, language, analysis_type="Full Audit"):
    """Enhanced code analysis with multiple modes"""
    try:
        lang = language.lower() if language != "Auto-Detect" else "python"
        code_block = f"```{lang}\n{code_snippet}\n```"
        
        base_prompt = f"""
        Analyze this {lang} code and provide:
        
        1. CORRECTED CODE with line numbers and change comments
        2. ERROR EXPLANATION with categorized errors and fixes
        3. BEST PRACTICES & RECOMMENDATIONS for improvement
        
        Format your response EXACTLY like this:
        
        ### CORRECTED CODE
        ```{lang}
        [Your corrected code here]
        ```
        
        ### ERROR EXPLANATION
        - [Error 1]
        - [Error 2]
        
        ### BEST PRACTICES & RECOMMENDATIONS
        - [Recommendation 1]
        - [Recommendation 2]
        """
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(base_prompt)
        return response.text
    except Exception as e:
        return f"**API Error**: {str(e)}"

def generate_code_from_text(prompt_text, language, template=None):
    """AI-powered code generation"""
    try:
        template_prompt = f" using {template} template" if template else ""
        prompt = f"""
        Generate {language} code{template_prompt} for:
        {prompt_text}
        
        Include:
        1. Production-ready code
        2. Error handling
        3. Documentation
        4. Security best practices
        """
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"**Generation Error**: {str(e)}"

def generate_api_documentation(code_snippet, language):
    """API documentation generator"""
    try:
        prompt = f"""
        Create OpenAPI documentation for this {language} code:
        ```{language}
        {code_snippet}
        ```
        Include:
        - Endpoints
        - Schemas
        - Examples
        - Security schemes
        """
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"**Docs Error**: {str(e)}"

def parse_response(response_text):
    """Robust response parser with fallbacks"""
    sections = {'code': '', 'explanation': '', 'recommendations': ''}

    try:
        # Case-insensitive regex patterns with fallback matches
        code_match = re.search(r'### CORRECTED CODE\s*```.*?\n(.*?)```', response_text, re.DOTALL | re.IGNORECASE)
        explanation_match = re.search(r'### ERROR EXPLANATION(.*?)(?:###|\Z)', response_text, re.DOTALL | re.IGNORECASE)
        recommendations_match = re.search(r'### BEST PRACTICES & RECOMMENDATIONS(.*?)(?:###|\Z)', response_text, re.DOTALL | re.IGNORECASE)

        sections['code'] = code_match.group(1).strip() if code_match else "No code corrections suggested"
        sections['explanation'] = explanation_match.group(1).strip() if explanation_match else "No errors detected"
        sections['recommendations'] = recommendations_match.group(1).strip() if recommendations_match else "No best practices available"

    except Exception as e:
        st.error(f"Parsing error: {str(e)}")

    return sections

# Streamlit UI Configuration
st.set_page_config(page_title="AI Code Debugger Pro", page_icon="🚀", layout="wide")

st.markdown("""
    <style>
        .stMarkdown pre {
            border-radius: 10px; 
            padding: 15px!important;
            white-space: pre-wrap; /* Ensures text wraps properly */
            word-wrap: break-word; /* Prevents text from being cut */
        }
        .stTextArea textarea {
            font-family: monospace !important;
            white-space: pre-wrap; /* Ensures text doesn't overflow */
        }
        .stTabs [role="tablist"] {
            flex-wrap: wrap; /* Allows tab labels to wrap */
        }
        .highlight {
            border-left: 3px solid #4CAF50; 
            padding-left: 10px;
        }
        .stButton>button {
            transition: all 0.3s ease;
            min-width: 150px; /* Prevents buttons from shrinking too much */
        }
        .stButton>button:hover {
            transform: scale(1.05);
        }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []
if 'code' not in st.session_state:
    st.session_state.code = ""

st.title("🚀 AI Code Suite Pro")
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader("📤 Upload Code", type=["py","js","java","cpp","cs","go"])
    if uploaded_file:
        try:
            st.session_state.code = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            st.error("⚠️ Invalid file format - please upload text-based source files")

    code = st.text_area("📝 Code Editor", height=300, value=st.session_state.code, help="Write or paste your code here")

    gen_prompt = st.text_area("💡 Code Generation Prompt", height=100, placeholder="Describe functionality to generate...")

with col2:
    lang = st.selectbox("🌐 Language", ["Auto-Detect", "Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust"])
    analysis_type = st.radio("🔍 Analysis Mode", ["Full Audit", "Quick Fix", "Security Review"])
    template = st.selectbox("📁 Code Template", ["None", "Web API", "CLI", "GUI", "Microservice"])

col3, col4 = st.columns(2, gap="medium")
with col3:
    analyze_btn = st.button("🔍 Analyze Code", use_container_width=True)
with col4:
    gen_btn = st.button("✨ Generate Code", use_container_width=True)

if analyze_btn:
    if code.strip():
        with st.spinner("🧠 Analyzing code..."):
            response = correct_code(code, lang, analysis_type)
            sections = parse_response(response)

            tab1, tab2, tab3 = st.tabs(["🛠 Corrected Code", "📖 Error Explanation", "🔍 Best Practices"])

            with tab1:
                st.code(sections['code'], language=lang.lower())

            with tab2:
                st.text_area("📖 Error Explanation", sections['explanation'], height=200)

            with tab3:
                st.text_area("🔍 Best Practices & Recommendations", sections['recommendations'], height=200)

            st.session_state.history.append({
                'code': code,
                'response': response,
                'timestamp': datetime.now()
            })
    else:
        st.error("⚠️ Please input code to analyze")

if gen_btn:
    if gen_prompt.strip():
        with st.spinner("🚀 Generating code..."):
            generated = generate_code_from_text(gen_prompt, lang, template)
            st.code(generated, language=lang.lower())
    else:
        st.error("⚠️ Please describe the functionality")

st.markdown("🔒 *Code processed securely via Google's AI APIs*")
