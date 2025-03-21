import streamlit as st
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="AI-Powered Document Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📄"
)

# Custom CSS for improved UI
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #FFFFFF; margin-bottom: 1rem; }
    .sub-header { font-size: 1.5rem; color: #CCCCCC; }
    .card { padding: 20px; border-radius: 10px; background-color: #2C3E50; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 20px; color: #FFFFFF; }
    .info-box { background-color: #34495E; border-left: 5px solid #3498DB; padding: 10px 15px; border-radius: 5px; color: #FFFFFF; }
    .warning-box { background-color: #F39C12; border-left: 5px solid #E67E22; padding: 10px 15px; border-radius: 5px; color: #FFFFFF; }
    .success-box { background-color: #28B463; border-left: 5px solid #1F8A4C; padding: 10px 15px; border-radius: 5px; color: #FFFFFF; }
    .error-box { background-color: #E74C3C; border-left: 5px solid #C0392B; padding: 10px 15px; border-radius: 5px; color: #FFFFFF; }
    .stButton>button { background-color: #28B463; color: white; border-radius: 5px; padding: 10px 20px; border: none; font-size: 16px; }
    .stButton>button:hover { background-color: #1F8A4C; }
    .stFileUploader>div>div>div>div { background-color: #34495E; border-radius: 5px; padding: 10px; color: #FFFFFF; }
    .stTextArea>div>div>textarea { background-color: #34495E; border-radius: 5px; padding: 10px; color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# Load environment variables
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Sidebar
with st.sidebar:
    st.markdown("### 🛠️ Settings")
    st.markdown("---")
    debug_mode = st.toggle("🐞 Debug Mode", value=False)
    st.markdown("### 📚 About")
    st.markdown("""
    <div class="info-box">
    This tool analyzes documents using AI to extract insights, skills, and key information.
    </div>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<h1 class="main-header">📄 Intelligent Document Processing System</h1>', unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
Upload a document (PDF, DOCX, TXT) for automated analysis using AI. The system will extract text and provide insights.
</div>
""", unsafe_allow_html=True)

# Document upload
uploaded_file = st.file_uploader("Upload your document", type=["pdf", "docx", "txt"])
text = ""

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    with st.spinner("Extracting text from document..."):
        try:
            response = requests.post(f"{backend_url}/upload", files=files)
            response.raise_for_status()
            data = response.json()
            text = data["text"]
            
            if "No text extracted from PDF" in text:
                st.markdown("""
                <div class="warning-box">
                ⚠️ The PDF appears to be scanned or contains no extractable text. OCR processing will be attempted.
                </div>
                """, unsafe_allow_html=True)
            elif len(text) < 50:
                st.markdown(f"""
                <div class="warning-box">
                ⚠️ Very little text was extracted ({len(text)} characters). The file may not contain proper text content.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="success-box">
                ✅ Text extracted from {uploaded_file.name} ({len(text)} characters)
                </div>
                """, unsafe_allow_html=True)
            
            with st.expander("Preview extracted text", expanded=True):
                st.text_area("Document content", text, height=300)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Characters", f"{len(text)}")
            with col2:
                st.metric("Words", f"{len(text.split())}")
            with col3:
                st.metric("Lines", f"{len(text.splitlines())}")
                
        except requests.exceptions.RequestException as e:
            st.markdown(f"""
            <div class="error-box">
            ❌ Failed to connect to the backend server: {e}
            </div>
            """, unsafe_allow_html=True)
            st.warning("Make sure the backend server is running. Check console for details.")
            
        except Exception as e:
            st.markdown(f"""
            <div class="error-box">
            ❌ Error processing file: {str(e)}
            </div>
            """, unsafe_allow_html=True)
            
    # Analysis options
    if text and len(text) > 10:
        st.markdown('<h2 class="sub-header">🔍 Analysis Options</h2>', unsafe_allow_html=True)
        
        analysis_tabs = st.tabs(["✨ Summary", "🔧 Skills & Keywords", "💼 Experience", "🔍 Custom Analysis"])
        
        with analysis_tabs[0]:
            if st.button("Generate Resume Summary", use_container_width=True):
                with st.spinner("Analyzing resume..."):
                    try:
                        prompt = "Provide a professional summary of this resume, highlighting key qualifications, experience, and skills."
                        custom_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        custom_analysis.raise_for_status()
                        
                        st.markdown('<h3 class="sub-header">📋 Resume Summary</h3>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="card">
                        {custom_analysis.json()["answer"]}
                        </div>
                        """, unsafe_allow_html=True)
                    except requests.exceptions.RequestException as e:
                        st.markdown(f"""
                        <div class="error-box">
                        ❌ Error analyzing resume: {e}
                        </div>
                        """, unsafe_allow_html=True)
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
        with analysis_tabs[1]:
            if st.button("Extract Skills & Keywords", use_container_width=True):
                with st.spinner("Extracting skills..."):
                    try:
                        prompt = "Extract and categorize all professional skills mentioned in this resume. Group them into categories like Technical Skills, Soft Skills, Tools & Software, Languages, etc."
                        skills_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        skills_analysis.raise_for_status()
                        
                        st.markdown('<h3 class="sub-header">🔧 Skills Analysis</h3>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="card">
                        {skills_analysis.json()["answer"]}
                        </div>
                        """, unsafe_allow_html=True)
                    except requests.exceptions.RequestException as e:
                        st.markdown(f"""
                        <div class="error-box">
                        ❌ Error extracting skills: {e}
                        </div>
                        """, unsafe_allow_html=True)
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
        with analysis_tabs[2]:
            if st.button("Analyze Experience", use_container_width=True):
                with st.spinner("Analyzing experience..."):
                    try:
                        prompt = "Summarize the work experience in this resume, highlighting roles, responsibilities, and achievements. Include the duration at each position if available."
                        exp_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        exp_analysis.raise_for_status()
                        
                        st.markdown('<h3 class="sub-header">💼 Experience Analysis</h3>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="card">
                        {exp_analysis.json()["answer"]}
                        </div>
                        """, unsafe_allow_html=True)
                    except requests.exceptions.RequestException as e:
                        st.markdown(f"""
                        <div class="error-box">
                        ❌ Error analyzing experience: {e}
                        </div>
                        """, unsafe_allow_html=True)
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
        with analysis_tabs[3]:
            custom_prompt = st.text_area("Enter a custom analysis prompt", "What are the candidate's strengths and areas for improvement based on this resume?")
            if st.button("Run Custom Analysis", use_container_width=True):
                with st.spinner("Running custom analysis..."):
                    try:
                        custom_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": custom_prompt, "api_key": openrouter_api_key}
                        )
                        custom_analysis.raise_for_status()
                        
                        st.markdown('<h3 class="sub-header">🔍 Custom Analysis Results</h3>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="card">
                        {custom_analysis.json()["answer"]}
                        </div>
                        """, unsafe_allow_html=True)
                    except requests.exceptions.RequestException as e:
                        st.markdown(f"""
                        <div class="error-box">
                        ❌ Error in custom analysis: {e}
                        </div>
                        """, unsafe_allow_html=True)
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
    
    elif text:  # We have some text but it's very little
        st.markdown("""
        <div class="warning-box">
        ⚠️ Not enough text was extracted to perform a meaningful analysis.
        </div>
        """, unsafe_allow_html=True)
        st.info("Try uploading a different file format or check that your document contains extractable text.")
        
    # Additional analysis options
    with st.expander("Advanced Options", expanded=False):
        st.markdown('<h3 class="sub-header">Additional Analysis Tools</h3>', unsafe_allow_html=True)
        
        # Entity recognition
        if st.button("Extract Entities", use_container_width=True):
            with st.spinner("Extracting entities..."):
                try:
                    entities_response = requests.post(f"{backend_url}/analyze/entities", data={"text": text, "api_key": openrouter_api_key})
                    entities_response.raise_for_status()
                    st.markdown('<h3 class="sub-header">🧩 Extracted Entities</h3>', unsafe_allow_html=True)
                    st.json(entities_response.json()["entities"])
                except requests.exceptions.RequestException as e:
                    st.markdown(f"""
                    <div class="error-box">
                    ❌ Error extracting entities: {e}
                    </div>
                    """, unsafe_allow_html=True)
                    if debug_mode:
                        st.error("Detailed error info:")
                        try:
                            st.json(e.response.json())
                        except:
                            st.write(f"Status code: {e.response.status_code}")
                            st.write(f"Response text: {e.response.text}")
                    st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")

        # Key elements
        if st.button("Extract Key Elements", use_container_width=True):
            with st.spinner("Extracting key elements..."):
                try:
                    key_elements_response = requests.post(f"{backend_url}/analyze/key_elements", data={"text": text, "api_key": openrouter_api_key})
                    key_elements_response.raise_for_status()
                    st.markdown('<h3 class="sub-header">🔑 Key Elements</h3>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="card">
                    {key_elements_response.json()["key_elements"]}
                    </div>
                    """, unsafe_allow_html=True)
                except requests.exceptions.RequestException as e:
                    st.markdown(f"""
                    <div class="error-box">
                    ❌ Error extracting key elements: {e}
                    </div>
                    """, unsafe_allow_html=True)
                    if debug_mode:
                        st.error("Detailed error info:")
                        try:
                            st.json(e.response.json())
                        except:
                            st.write(f"Status code: {e.response.status_code}")
                            st.write(f"Response text: {e.response.text}")
                    st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")

        # Q&A
        question = st.text_input("Ask a question about the document:")
        if question and st.button("Get Answer", use_container_width=True):
            with st.spinner("Generating answer..."):
                try:
                    qa_response = requests.post(f"{backend_url}/analyze/qa", data={"text": text, "question": question, "api_key": openrouter_api_key})
                    qa_response.raise_for_status()
                    st.markdown('<h3 class="sub-header">❓ Q&A Response</h3>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="card">
                    {qa_response.json()["answer"]}
                    </div>
                    """, unsafe_allow_html=True)
                except requests.exceptions.RequestException as e:
                    st.markdown(f"""
                    <div class="error-box">
                    ❌ Error in Q&A processing: {e}
                    </div>
                    """, unsafe_allow_html=True)
                    if debug_mode:
                        st.error("Detailed error info:")
                        try:
                            st.json(e.response.json())
                        except:
                            st.write(f"Status code: {e.response.status_code}")
                            st.write(f"Response text: {e.response.text}")
                    st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")

    # Document comparison
    st.markdown('<h2 class="sub-header">📑 Compare Two Documents</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
    Upload a second document to compare with your resume (e.g., a job description or another resume)
    </div>
    """, unsafe_allow_html=True)

    uploaded_file2 = st.file_uploader("Upload a second document", type=["pdf", "docx", "txt"], key="second_doc")

    if uploaded_file2:
        files2 = {"file": (uploaded_file2.name, uploaded_file2.getvalue(), uploaded_file2.type)}
        try:
            response2 = requests.post(f"{backend_url}/upload", files=files2)
            response2.raise_for_status()
            text2 = response2.json()["text"]
            
            st.markdown(f"""
            <div class="success-box">
            ✅ Text extracted from second document: {uploaded_file2.name}
            </div>
            """, unsafe_allow_html=True)
            
            compare_options = st.selectbox(
                "Choose comparison type",
                ["General Comparison", "Resume vs Job Description Match", "Skills Alignment", "Qualification Gap Analysis"]
            )
            
            if st.button("Compare Documents", use_container_width=True):
                with st.spinner("Comparing documents..."):
                    try:
                        # Customize prompt based on comparison type
                        prompt = "Compare these two documents."
                        
                        if compare_options == "Resume vs Job Description Match":
                            prompt = "The first document is a resume and the second is a job description. Analyze how well the resume matches the job requirements. Highlight strengths and gaps."
                        elif compare_options == "Skills Alignment":
                            prompt = "Compare the skills mentioned in both documents. Identify matching skills, missing skills, and provide recommendations."
                        elif compare_options == "Qualification Gap Analysis":
                            prompt = "Analyze the qualifications in both documents and identify any gaps. Provide specific recommendations for improvement."
                        
                        # Use custom Q&A endpoint for more flexible prompting
                        compare_response = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": f"Doc1:\n{text}\n\nDoc2:\n{text2}", "question": prompt, "api_key": openrouter_api_key}
                        )
                        compare_response.raise_for_status()
                        
                        st.markdown('<h3 class="sub-header">📊 Comparison Results</h3>', unsafe_allow_html=True)
                        st.markdown(f"""
                        <div class="card">
                        {compare_response.json()["answer"]}
                        </div>
                        """, unsafe_allow_html=True)
                    except requests.exceptions.RequestException as e:
                        st.markdown(f"""
                        <div class="error-box">
                        ❌ Error comparing documents: {e}
                        </div>
                        """, unsafe_allow_html=True)
                        if debug_mode:
                            st.error("Debug info:")
                            st.write(f"API key status: {'Set' if openrouter_api_key else 'Missing'}")
                        st.info("API authentication error. Please ensure you have a valid OpenRouter API key.")
        except requests.exceptions.RequestException as e:
            st.markdown(f"""
            <div class="error-box">
            ❌ Failed to upload the second document: {e}
            </div>
            """, unsafe_allow_html=True)
            if debug_mode:
                st.error("Backend connectivity issue:")
                st.write(f"Backend URL: {backend_url}")
            st.info("Make sure the backend server is running and accessible.")