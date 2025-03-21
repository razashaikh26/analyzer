import os
import sys
import streamlit as st
import requests
import threading
import time

# Set environment variable to indicate we're on Streamlit Cloud
os.environ["STREAMLIT_SHARING"] = "true"

# Add backend directory to path for imports
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
sys.path.append(backend_dir)

# Set page config
st.set_page_config(page_title="AI-Powered Document Analyzer", layout="wide")

# Set up API keys from secrets
try:
    openrouter_api_key = st.secrets["api"]["openrouter_api_key"]
    backend_url = "http://localhost:8000"  # We'll use localhost since backend runs in same process
except Exception as e:
    st.error(f"Error loading secrets: {e}")
    st.write("Please configure secrets in the Streamlit Cloud dashboard")
    openrouter_api_key = ""
    backend_url = "http://localhost:8000"

# Add debug mode toggle in sidebar
with st.sidebar:
    st.title("Settings")
    debug_mode = st.toggle("Debug Mode", value=False)
    if debug_mode:
        st.write("⚠️ Debug mode enabled - error details will be shown")
        # Show backend connection info
        st.write(f"Backend URL: {backend_url}")
        st.write(f"OpenRouter API Key: {openrouter_api_key[:5]}..." if openrouter_api_key else "Not set")

# Print API key to check if it's being loaded
print("OPENROUTER_API_KEY:", openrouter_api_key and "Set" or "Missing")

if not openrouter_api_key:
    st.warning("⚠️ OpenRouter API key is missing. Features will not work.")
    st.info("To use this app, add your OpenRouter API key in the Streamlit Cloud dashboard under 'Secrets'")
    st.stop()

# Import and start backend
try:
    from backend import backend
    
    # Define function to run backend in a thread
    def run_backend():
        import uvicorn
        # Use environment variable for API key
        os.environ["OPENROUTER_API_KEY"] = openrouter_api_key
        uvicorn.run(backend.app, host="127.0.0.1", port=8000, log_level="error")
    
    # Start backend in thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Wait for backend to start
    time.sleep(2)
    try:
        response = requests.get(backend_url)
        if response.status_code == 200:
            st.success("✅ Backend API running successfully")
        else:
            st.warning("⚠️ Backend response code: " + str(response.status_code))
    except Exception as e:
        st.warning(f"⚠️ Backend connection issue: {e}")
except Exception as e:
    st.error(f"Failed to start backend: {e}")
    st.info("Try refreshing the page")
    st.stop()

# Main UI
st.title("📄 Intelligent Document Processing System")
st.write("Upload a document (PDF, DOCX, TXT) for automated analysis.")

# UPLOAD SECTION
st.info("💡 Upload a resume (PDF, DOCX, TXT) for analysis. The system will extract text and help you analyze it.")

with st.expander("Tips for best results", expanded=False):
    st.markdown("""
    ### Getting the best results
    
    - **PDF resumes**: For best results, use text-based PDFs rather than scanned documents
    - **Scanned documents**: The system will attempt OCR, but results may vary
    - **DOCX files**: Usually provide excellent extraction quality
    - **Text files**: Work perfectly but may lose formatting
    
    If you're having trouble with extraction, try converting your resume to DOCX format.
    """)

uploaded_file = st.file_uploader("Upload your document", type=["pdf", "docx", "txt"])
text = ""

if uploaded_file:
    st.write(f"📄 File uploaded: **{uploaded_file.name}** ({uploaded_file.type})")
    
    # Prepare the file for upload
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    
    with st.spinner("Extracting text from document..."):
        try:
            response = requests.post(f"{backend_url}/upload", files=files)
            response.raise_for_status()  # Raise an error for bad status codes
            data = response.json()
            text = data["text"]
            
            # Show preview with expandable text area
            with st.expander("Preview extracted text", expanded=True):
                st.text_area("Document content", text, height=300)
                
            # Show length as a metric
            st.metric("Document Length", f"{len(text)} characters", f"{len(text.split())} words")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the backend server: {e}")
            st.warning("Backend service is not responding. Try refreshing the page.")
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            
    # If we have text, show analysis options
    if text and len(text) > 10:  # Ensure we have meaningful text to analyze
        st.subheader("🔍 Resume Analysis Options")
        
        analysis_tabs = st.tabs(["Summary", "Skills & Keywords", "Experience", "Custom Analysis"])
        
        with analysis_tabs[0]:
            if st.button("Generate Resume Summary"):
                with st.spinner("Analyzing resume..."):
                    try:
                        prompt = "Provide a professional summary of this resume, highlighting key qualifications, experience, and skills."
                        custom_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        custom_analysis.raise_for_status()
                        
                        st.subheader("📋 Resume Summary")
                        st.write(custom_analysis.json()["answer"])
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error analyzing resume: {e}")
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
        with analysis_tabs[1]:
            if st.button("Extract Skills & Keywords"):
                with st.spinner("Extracting skills..."):
                    try:
                        prompt = "Extract and categorize all professional skills mentioned in this resume. Group them into categories like Technical Skills, Soft Skills, Tools & Software, Languages, etc."
                        skills_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        skills_analysis.raise_for_status()
                        
                        st.subheader("🔧 Skills Analysis")
                        st.write(skills_analysis.json()["answer"])
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error extracting skills: {e}")
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid.")
        
        with analysis_tabs[2]:
            if st.button("Analyze Experience"):
                with st.spinner("Analyzing experience..."):
                    try:
                        prompt = "Summarize the work experience in this resume, highlighting roles, responsibilities, and achievements. Include the duration at each position if available."
                        exp_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": prompt, "api_key": openrouter_api_key}
                        )
                        exp_analysis.raise_for_status()
                        
                        st.subheader("💼 Experience Analysis")
                        st.write(exp_analysis.json()["answer"])
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error analyzing experience: {e}")
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid.")
        
        with analysis_tabs[3]:
            custom_prompt = st.text_area("Enter a custom analysis prompt", "What are the candidate's strengths and areas for improvement based on this resume?")
            if st.button("Run Custom Analysis"):
                with st.spinner("Running custom analysis..."):
                    try:
                        custom_analysis = requests.post(
                            f"{backend_url}/analyze/qa", 
                            data={"text": text, "question": custom_prompt, "api_key": openrouter_api_key}
                        )
                        custom_analysis.raise_for_status()
                        
                        st.subheader("🔍 Custom Analysis Results")
                        st.write(custom_analysis.json()["answer"])
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error in custom analysis: {e}")
                        if debug_mode:
                            st.error("Detailed error info:")
                            try:
                                st.json(e.response.json())
                            except:
                                st.write(f"Status code: {e.response.status_code}")
                                st.write(f"Response text: {e.response.text}")
                        st.info("This error typically occurs when the API key is missing or invalid.") 