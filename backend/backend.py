from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import pdfplumber
import docx
import io
import os
import json
import asyncio
import concurrent.futures
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/llama-3.3-70b-instruct:free")

print(f"OpenRouter API Key: {'Configured' if OPENROUTER_API_KEY else 'Missing'}")
print(f"Using model: {MODEL_NAME}")

# Define your FastAPI app
app = FastAPI(
    title="Resume Analyzer API",
    description="API for analyzing resumes and other documents",
    version="1.0.0"
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"status": "healthy", "message": "Resume Analyzer API is running"}

# ==========================
# PARALLEL TEXT EXTRACTION
# ==========================
def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file using parallel processing."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                texts = list(executor.map(lambda page: page.extract_text() or "", pdf.pages))
        result = "\n".join(texts).strip()
        return result or "No text extracted from PDF. The document may be scanned or contain no selectable text."
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs).strip()
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

def extract_text_from_txt(content: bytes) -> str:
    """Extract text from a TXT file."""
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"Error extracting text from TXT: {str(e)}"

def extract_text(file: UploadFile) -> str:
    """Detect file type and extract text efficiently."""
    content = file.file.read()
    
    content_type = file.content_type.lower() if file.content_type else ""
    filename = file.filename.lower() if file.filename else ""
    
    # Try to determine file type from content type or filename
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return extract_text_from_pdf(content)
    elif (content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
          or filename.endswith(".docx")):
        return extract_text_from_docx(content)
    elif content_type == "text/plain" or filename.endswith(".txt"):
        return extract_text_from_txt(content)
    
    return "Unsupported file type. Please upload a PDF, DOCX, or TXT file."

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a document file."""
    # Validate file size
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
    
    # Extract text in a separate thread to avoid blocking
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, extract_text, file)

    if text.startswith("Error") or text == "Unsupported file type":
        raise HTTPException(status_code=400, detail=text)

    return JSONResponse({
        "filename": file.filename,
        "content_type": file.content_type,
        "text": text,
        "length": len(text),
        "word_count": len(text.split())
    })

# ==========================
# AI-POWERED ANALYSIS
# ==========================
def get_openai_client(api_key=None):
    """Create and return an OpenAI client with the specified API key."""
    # Use parameter API key if provided, otherwise use environment variable
    key_to_use = api_key or OPENROUTER_API_KEY
    
    if not key_to_use:
        raise ValueError("No API key available for OpenRouter. Please provide an API key.")
        
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key_to_use,
    )

def query_llm(prompt: str, text: str, api_key=None, model=None) -> str:
    """Query LLM model with document text while handling large inputs."""
    if not text.strip():
        return "Error: No content to process."

    try:
        # Get a client with the appropriate API key
        client = get_openai_client(api_key)
        
        # Use specified model or default
        model_to_use = model or MODEL_NAME
        
        # Truncate text if it's too long (most models have context limits)
        max_length = 25000
        truncated = False
        if len(text) > max_length:
            text = text[:max_length]
            truncated = True
            
        # Create system prompt
        system_prompt = (
            "You are an expert document analyzer specializing in resumes and professional documents. "
            "Provide detailed, accurate, and helpful analysis."
        )
        
        # Add truncation warning if applicable
        if truncated:
            prompt += "\n\nNote: The document was truncated due to length constraints."
        
        completion = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{prompt}\n\nDocument Text:\n{text}"}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/analyze/summarize")
async def summarize(text: str = Form(...), api_key: str = Form(None)):
    """Generate a summary of the document."""
    prompt = (
        "Provide a concise professional summary of this document. "
        "Identify the document type and key information. "
        "If this is a resume, highlight education, experience, skills, and qualifications."
    )
    return JSONResponse({"summary": query_llm(prompt, text, api_key)})

@app.post("/analyze/entities")
async def recognize_entities(text: str = Form(...), api_key: str = Form(None)):
    """Extract named entities (PERSON, ORG, GEO, DATE) and return in JSON format."""
    
    prompt = (
        "Extract named entities from the given text. "
        "Categorize them as PERSON, ORGANIZATION (ORG), GEOGRAPHICAL LOCATION (GEO), and DATE. "
        "For a resume, be sure to include the candidate name, companies, institutions, locations, and dates. "
        "Return results ONLY in valid JSON format as an array of objects with 'entity' and 'type' properties:\n"
        '[{"entity": "Elon Musk", "type": "PERSON"}, {"entity": "OpenAI", "type": "ORG"}]'
    )

    response = query_llm(prompt, text, api_key)

    try:
        # Find the JSON part in the response
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = response[json_start:json_end]
            parsed_response = json.loads(json_text)
            return JSONResponse({"entities": parsed_response}) if isinstance(parsed_response, list) else JSONResponse({"entities": []})
        else:
            return JSONResponse({"error": "Failed to find JSON in response", "raw_response": response}, status_code=500)
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        return JSONResponse({"error": f"Failed to parse entity recognition response: {str(e)}", "raw_response": response}, status_code=500)

@app.post("/analyze/key_elements")
async def key_elements(text: str = Form(...), api_key: str = Form(None)):
    """Extract key themes, topics, and concepts from the document."""
    prompt = (
        "Extract key themes, topics, and concepts from this document. "
        "If this is a resume, include skills, qualifications, education level, experience overview, and career highlights. "
        "Organize the information in a clear, structured format with appropriate headings."
    )
    return JSONResponse({"key_elements": query_llm(prompt, text, api_key)})

@app.post("/analyze/qa")
async def qa(text: str = Form(...), question: str = Form(...), api_key: str = Form(None)):
    """Answer a specific question about the document content."""
    prompt = f"Based on the document provided, answer this question: {question}"
    return JSONResponse({"answer": query_llm(prompt, text, api_key)})

@app.post("/analyze/compare")
async def compare_docs(text1: str = Form(...), text2: str = Form(...), api_key: str = Form(None)):
    """Compare two documents and identify similarities and differences."""
    prompt = (
        "Compare these two documents in detail. "
        "Identify key similarities and differences. "
        "If one is a resume and one is a job description, analyze how well the candidate matches the job requirements. "
        "Provide a compatibility score (0-100%) and specific recommendations."
    )
    return JSONResponse({"comparison": query_llm(prompt, f"Document 1:\n{text1}\n\nDocument 2:\n{text2}", api_key)})

@app.post("/analyze/skills")
async def extract_skills(text: str = Form(...), api_key: str = Form(None)):
    """Extract and categorize skills from a resume."""
    prompt = (
        "Extract and categorize all professional skills mentioned in this resume. "
        "Group them into categories such as Technical Skills, Soft Skills, Tools & Software, Languages, etc. "
        "For each skill, provide a confidence level (High/Medium/Low) based on how clearly it's demonstrated in the resume."
    )
    return JSONResponse({"skills": query_llm(prompt, text, api_key)})

@app.post("/analyze/experience")
async def analyze_experience(text: str = Form(...), api_key: str = Form(None)):
    """Analyze work experience from a resume."""
    prompt = (
        "Analyze the work experience section of this resume. "
        "Extract and summarize each position, including company name, job title, duration, and key responsibilities. "
        "Calculate the total years of experience and identify the primary industry sectors."
    )
    return JSONResponse({"experience": query_llm(prompt, text, api_key)})

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "api_key_configured": bool(OPENROUTER_API_KEY)}

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable for Render compatibility
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)