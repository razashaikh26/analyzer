import streamlit as st
import requests
import threading
import subprocess
import time
import signal
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="AI-Powered Document Analyzer",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📄"
)

# Custom CSS for improved UI
    # Custom CSS for improved UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FFFFFF; /* White text */
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #CCCCCC; /* Light gray text */
    }
    .card {
        padding: 20px;
        border-radius: 10px;
        background-color: #2C3E50; /* Dark blue-gray background */
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        color: #FFFFFF; /* White text */
    }
    .info-box {
        background-color: #34495E; /* Darker blue-gray background */
        border-left: 5px solid #3498DB;
        padding: 10px 15px;
        border-radius: 5px;
        color: #FFFFFF; /* White text */
    }
    .warning-box {
        background-color: #F39C12; /* Orange background */
        border-left: 5px solid #E67E22;
        padding: 10px 15px;
        border-radius: 5px;
        color: #FFFFFF; /* White text */
    }
    .success-box {
        background-color: #28B463; /* Green background */
        border-left: 5px solid #1F8A4C;
        padding: 10px 15px;
        border-radius: 5px;
        color: #FFFFFF; /* White text */
    }
    .error-box {
        background-color: #E74C3C; /* Red background */
        border-left: 5px solid #C0392B;
        padding: 10px 15px;
        border-radius: 5px;
        color: #FFFFFF; /* White text */
    }
    .sidebar .sidebar-content {
        background-color: #34495E; /* Dark blue-gray background */
        color: #FFFFFF; /* White text */
    }
    .stButton>button {
        background-color: #28B463; /* Green background */
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #1F8A4C; /* Darker green on hover */
    }
    .stFileUploader>div>div>div>div {
        background-color: #34495E; /* Dark blue-gray background */
        border-radius: 5px;
        padding: 10px;
        color: #FFFFFF; /* White text */
    }
    .stTextArea>div>div>textarea {
        background-color: #34495E; /* Dark blue-gray background */
        border-radius: 5px;
        padding: 10px;
        color: #FFFFFF; /* White text */
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables directly
api_key = os.getenv("API_KEY", "")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Sidebar with improved styling
with st.sidebar:
    st.markdown("### 🛠️ Settings")
    st.markdown("---")
    
    # Add a cleaner debug toggle
    debug_mode = st.toggle("🐞 Debug Mode", value=False)
    
    st.markdown("### 📚 About")
    st.markdown("""
    <div class="info-box">
    This tool analyzes documents using AI to extract insights, skills, and key information.
    </div>
    """, unsafe_allow_html=True)
    
    if debug_mode:
        st.markdown("### 🔍 Debug Information")
        st.markdown(f"""
        <div class="warning-box">
        ⚠️ Debug mode enabled - error details will be shown
        </div>
        """, unsafe_allow_html=True)
        
        # Display configuration details
        st.markdown("#### Configuration")
        st.markdown(f"- **Backend URL**: `{backend_url}`")
        st.markdown(f"- **OpenRouter API Key**: `{openrouter_api_key[:5]}...`" if openrouter_api_key else "- **OpenRouter API Key**: Not set")

# Print API key to check if it's being loaded (for server logs only)
print("API_KEY:", "Set" if api_key else "Missing")
print("OPENROUTER_API_KEY:", "Set" if openrouter_api_key else "Missing")

if not openrouter_api_key:
    st.markdown("""
    <div class="warning-box">
    ⚠️ OpenRouter API key is missing. Some features may not work.
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("API Key Information"):
        st.markdown("""
        ### Setting Up API Keys
        
        To use all features, you need to set up an OpenRouter API key:
        
        1. Get a free API key from [OpenRouter](https://openrouter.ai/)
        2. Create a `.env` file in your project root with:
        ```
        OPENROUTER_API_KEY=your_api_key_here
        BACKEND_URL=http://localhost:8000
        ```
        3. Restart the application
        """)

# In production deployment on Render, we need special handling
is_render = os.getenv("RENDER") == "true"

if not is_render:
    # Local development - start backend as subprocess
    # Global variable to store the backend process
    backend_process = None

    # Start FastAPI backend
    def start_backend():
        global backend_process
        try:
            # Kill any existing processes on port 8000
            try:
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(["lsof", "-ti", "tcp:8000", "-sTCP:LISTEN", "|", "xargs", "kill", "-9"], shell=True)
                elif sys.platform.startswith('linux'):
                    subprocess.run(["fuser", "-k", "8000/tcp"], shell=True)
            except Exception as e:
                print(f"Warning when clearing port: {e}")
            
            # Start the backend process
            print("Starting backend server...")
            
            # Set up environment for the backend process
            process_env = os.environ.copy()
            if openrouter_api_key:
                process_env["OPENROUTER_API_KEY"] = openrouter_api_key
                print("API key set in environment for backend")
            
            backend_process = subprocess.Popen(
                ["python3", "-m", "uvicorn", "backend.backend:app", "--host", "0.0.0.0", "--port", "8000"],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                env=process_env
            )
            
            # Wait for the server to start
            for i in range(10):  # Try for up to 10 seconds
                time.sleep(1)
                # Check if server is running by making a request
                try:
                    response = requests.get("http://localhost:8000")
                    if response.status_code == 200:
                        print("Backend server started successfully!")
                        return True
                except requests.RequestException:
                    pass
                
                # Check if process is still running
                if backend_process.poll() is not None:
                    stderr = backend_process.stderr.read()
                    print(f"Backend process exited with error: {stderr}")
                    # Log more details about the failure
                    if "No module named" in stderr:
                        print("Error: Python module not found. Check if all required packages are installed.")
                    elif "No API Key is missing" in stderr or "OPENROUTER_API_KEY" in stderr:
                        print("Error: API key issue. Please check your OpenRouter API key configuration.")
                    elif "Address already in use" in stderr:
                        print("Error: Port 8000 is already in use by another application.")
                    return False
                    
            # If we get here, server didn't start successfully
            print("Backend server failed to start within timeout period")
            return False
        except Exception as e:
            print(f"Failed to start backend server: {e}")
            return False

    # Ensure backend is running before accepting uploads
    if start_backend():
        st.markdown("""
        <div class="success-box">
        ✅ Backend server running!
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="error-box">
        ❌ Failed to start backend server. File processing will not work.
        </div>
        """, unsafe_allow_html=True)
else:
    # On Render, just use the configured backend URL
    print(f"Using backend URL: {backend_url}")

# Streamlit UI - Main content
st.markdown('<h1 class="main-header">📄 Intelligent Document Processing System</h1>', unsafe_allow_html=True)
st.markdown("""
<div class="info-box">
Upload a document (PDF, DOCX, TXT) for automated analysis using AI. The system will extract text and provide insights.
</div>
""", unsafe_allow_html=True)

# ========================
# UPLOAD SECTION
# ========================
st.markdown('<h2 class="sub-header">📂 Document Upload</h2>', unsafe_allow_html=True)

st.markdown("""
<div class="card">
<p>💡 Upload a resume (PDF, DOCX, TXT) for analysis. The system will extract text and help you analyze it.</p>
</div>
""", unsafe_allow_html=True)

with st.expander("Tips for best results", expanded=False):
    st.markdown("""
    ### Getting the best results
    
    - **PDF resumes**: For best results, use text-based PDFs rather than scanned documents
    - **Scanned documents**: The system will attempt OCR, but results may vary
    - **DOCX files**: Usually provide excellent extraction quality
    - **Text files**: Work perfectly but may lose formatting
    
    If you're having trouble with extraction, try converting your resume to DOCX format.
    """)

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_file = st.file_uploader("Upload your document", type=["pdf", "docx", "txt"])
text = ""

if uploaded_file:
    st.markdown(f"""
    <div class="card">
    📄 File uploaded: <strong>{uploaded_file.name}</strong> ({uploaded_file.type})
    </div>
    """, unsafe_allow_html=True)
    
    # Prepare the file for upload
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    
    with st.spinner("Extracting text from document..."):
        try:
            response = requests.post(f"{backend_url}/upload", files=files)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()
            text = data["text"]
            
            # Check if extraction was successful but returned no substantial content
            if "No text extracted from PDF" in text:
                st.markdown("""
                <div class="warning-box">
                ⚠️ The PDF appears to be scanned or contains no extractable text. OCR processing will be attempted.
                </div>
                """, unsafe_allow_html=True)
                st.info("If OCR fails, consider converting your resume to DOCX format for better results.")
            elif len(text) < 50:  # Very short text likely indicates a problem
                st.markdown(f"""
                <div class="warning-box">
                ⚠️ Very little text was extracted ({len(text)} characters). The file may not contain proper text content.
                </div>
                """, unsafe_allow_html=True)
            else:
                # Display success and preview text
                st.markdown(f"""
                <div class="success-box">
                ✅ Text extracted from {uploaded_file.name} ({len(text)} characters)
                </div>
                """, unsafe_allow_html=True)
            
            # Show preview with expandable text area
            with st.expander("Preview extracted text", expanded=True):
                st.text_area("Document content", text, height=300)
            
            # Better metrics display
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
            
    # If we have text, show analysis options
    if text and len(text) > 10:  # Ensure we have meaningful text to analyze
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
        
    # Additional analysis options can still be available
    with st.expander("Advanced Options", expanded=False):
        st.markdown('<h3 class="sub-header">Additional Analysis Tools</h3>', unsafe_allow_html=True)
        
        # ========================
        # ENTITY RECOGNITION
        # ========================
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

        # ========================
        # KEY ELEMENTS
        # ========================
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

        # ========================
        # Q&A
        # ========================
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

    # ========================
    # DOCUMENT COMPARISON
    # ========================
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