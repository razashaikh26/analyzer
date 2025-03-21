import streamlit as st
import requests
import threading
import subprocess
import time
import signal
import os
import sys

# Set page config as the first Streamlit command
st.set_page_config(page_title="AI-Powered Document Analyzer", layout="wide")

# Load environment variables from Streamlit secrets
try:
    api_key = st.secrets["api"]["key"]
except KeyError:
    api_key = ""  # Provide default value if missing

try:
    openrouter_api_key = st.secrets["api"]["openrouter_api_key"]
except KeyError:
    openrouter_api_key = ""  # Provide default value if missing
    
try:
    backend_url = st.secrets["api"]["backend_url"]
except KeyError:
    backend_url = "http://localhost:8000"  # Default to localhost if not specified

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
print("API_KEY:", api_key and "Set" or "Missing")
print("OPENROUTER_API_KEY:", openrouter_api_key and "Set" or "Missing")

if not openrouter_api_key:
    st.warning("⚠️ OpenRouter API key is missing. Some features may not work.")
    with st.expander("API Key Information"):
        st.info("To use all features, you need to set up an OpenRouter API key.")
        st.markdown("""
        1. Get a free API key from [OpenRouter](https://openrouter.ai/)
        2. Add it to your `.streamlit/secrets.toml` file or as an environment variable
        """)

# In production deployment on Render, we don't need to start the backend
# as it will be running as a separate service
if os.getenv("RENDER") != "true":
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
        st.success("✅ Backend server running!")
    else:
        st.error("❌ Failed to start backend server. File processing will not work.")
else:
    # In production, show the configured backend URL
    print(f"Using backend URL: {backend_url}")

# Streamlit UI
st.title("📄 Intelligent Document Processing System")
st.write("Upload a document (PDF, DOCX, TXT) for automated analysis.")

# ========================
# UPLOAD SECTION
# ========================
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
            
            # Check if extraction was successful but returned no substantial content
            if "No text extracted from PDF" in text:
                st.warning("⚠️ The PDF appears to be scanned or contains no extractable text. OCR processing will be attempted.")
                st.info("If OCR fails, consider converting your resume to DOCX format for better results.")
            elif len(text) < 50:  # Very short text likely indicates a problem
                st.warning(f"⚠️ Very little text was extracted ({len(text)} characters). The file may not contain proper text content.")
            else:
                # Display success and preview text
                st.success(f"✅ Text extracted from {uploaded_file.name} ({len(text)} characters)")
            
            # Show preview with expandable text area
            with st.expander("Preview extracted text", expanded=True):
                st.text_area("Document content", text, height=300)
                
            # Show length as a metric
            st.metric("Document Length", f"{len(text)} characters", f"{len(text.split())} words")
            
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the backend server: {e}")
            st.warning("Make sure the backend server is running. Check console for details.")
            
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
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
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
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
        
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
                        st.info("This error typically occurs when the API key is missing or invalid. Check your OpenRouter API key configuration.")
    
    elif text:  # We have some text but it's very little
        st.warning("Not enough text was extracted to perform a meaningful analysis.")
        st.info("Try uploading a different file format or check that your document contains extractable text.")
        
    # Additional analysis options can still be available
    with st.expander("Advanced Options", expanded=False):
        st.subheader("Additional Analysis Tools")
        
        # ========================
        # ENTITY RECOGNITION
        # ========================
        if st.button("Extract Entities"):
            with st.spinner("Extracting entities..."):
                try:
                    entities_response = requests.post(f"{backend_url}/analyze/entities", data={"text": text, "api_key": openrouter_api_key})
                    entities_response.raise_for_status()
                    st.subheader("🧩 Extracted Entities")
                    st.json(entities_response.json()["entities"])
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error extracting entities: {e}")
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
        if st.button("Extract Key Elements"):
            with st.spinner("Extracting key elements..."):
                try:
                    key_elements_response = requests.post(f"{backend_url}/analyze/key_elements", data={"text": text, "api_key": openrouter_api_key})
                    key_elements_response.raise_for_status()
                    st.subheader("🔑 Key Elements")
                    st.write(key_elements_response.json()["key_elements"])
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error extracting key elements: {e}")
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
        if question and st.button("Get Answer"):
            with st.spinner("Generating answer..."):
                try:
                    qa_response = requests.post(f"{backend_url}/analyze/qa", data={"text": text, "question": question, "api_key": openrouter_api_key})
                    qa_response.raise_for_status()
                    st.subheader("❓ Q&A Response")
                    st.write(qa_response.json()["answer"])
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error in Q&A processing: {e}")
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
    st.subheader("📑 Compare Two Documents")
    st.info("Upload a second document to compare with your resume (e.g., a job description or another resume)")

    uploaded_file2 = st.file_uploader("Upload a second document", type=["pdf", "docx", "txt"], key="second_doc")

    if uploaded_file2:
        files2 = {"file": (uploaded_file2.name, uploaded_file2.getvalue(), uploaded_file2.type)}
        try:
            response2 = requests.post(f"{backend_url}/upload", files=files2)
            response2.raise_for_status()
            text2 = response2.json()["text"]
            
            st.success(f"✅ Text extracted from second document: {uploaded_file2.name}")
            
            compare_options = st.selectbox(
                "Choose comparison type",
                ["General Comparison", "Resume vs Job Description Match", "Skills Alignment", "Qualification Gap Analysis"]
            )
            
            if st.button("Compare Documents"):
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
                        
                        st.subheader("📊 Comparison Results")
                        st.write(compare_response.json()["answer"])
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Error comparing documents: {e}")
                        if debug_mode:
                            st.error("Debug info:")
                            st.write(f"API key status: {'Set' if openrouter_api_key else 'Missing'}")
                        st.info("API authentication error. Please ensure you have a valid OpenRouter API key.")
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to upload the second document: {e}")
            if debug_mode:
                st.error("Backend connectivity issue:")
                st.write(f"Backend URL: {backend_url}")
            st.info("Make sure the backend server is running and accessible.")