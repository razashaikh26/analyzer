from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from openai import OpenAI
import pdfplumber
import docx
import io
import os
import json
import asyncio
import concurrent.futures

# OpenRouter API Configuration
# Try to load API keys from environment variables, with multiple fallback options
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# If not found in env vars, check if frontend passed it through as query param
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in environment variables.")
    print("Will attempt to use API key from frontend request at runtime.")

# Define your FastAPI app
app = FastAPI()

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "API is running!"}

# ==========================
# PARALLEL TEXT EXTRACTION
# ==========================
def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file using parallel processing."""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            texts = list(executor.map(lambda page: page.extract_text() or "", pdf.pages))
    return "\n".join(texts).strip() or "No text extracted from PDF."

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    doc = docx.Document(io.BytesIO(content))
    return "\n".join(para.text for para in doc.paragraphs).strip()

def extract_text_from_txt(content: bytes) -> str:
    """Extract text from a TXT file."""
    return content.decode("utf-8", errors="ignore").strip()

def extract_text(file: UploadFile) -> str:
    """Detect file type and extract text efficiently."""
    content = file.file.read()
    
    if file.content_type == "application/pdf":
        return extract_text_from_pdf(content)
    elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(content)
    elif file.content_type == "text/plain":
        return extract_text_from_txt(content)
    
    return "Unsupported file type"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, extract_text, file)

    if text.startswith("Error") or text == "Unsupported file type":
        raise HTTPException(status_code=400, detail=text)

    return JSONResponse({"filename": file.filename, "text": text, "length": len(text)})

# ==========================
# AI-POWERED ANALYSIS
# ==========================
def get_openai_client(api_key=None):
    """Create and return an OpenAI client with the specified API key."""
    # Use parameter API key if provided, otherwise use environment variable
    key_to_use = api_key or OPENROUTER_API_KEY
    
    if not key_to_use:
        raise ValueError("No API key available for OpenRouter")
        
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=key_to_use,
    )

def query_llama(prompt: str, text: str, api_key=None) -> str:
    """Query Llama model with document text while handling large inputs."""
    if not text.strip():
        return "Error: No content to process."

    try:
        # Get a client with the appropriate API key
        client = get_openai_client(api_key)
        
        MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert in document analysis."},
                {"role": "user", "content": f"{prompt}\n\nDocument Text:\n{text[:25000]}"}  # Large input handling
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.post("/analyze/summarize")
async def summarize(text: str = Form(...), api_key: str = Form(None)):
    return JSONResponse({"summary": query_llama("Summarize the document.", text, api_key)})

@app.post("/analyze/entities")
async def recognize_entities(text: str = Form(...), api_key: str = Form(None)):
    """Extract named entities (PERSON, ORG, GEO, DATE) and return JSON format."""
    
    prompt = (
        "Extract named entities from the given text. "
        "Categorize them as PERSON, ORGANIZATION (ORG), GEOGRAPHICAL LOCATION (GEO), and DATE. "
        "Return results ONLY in JSON format:\n"
        '[{"entity": "Elon Musk", "type": "PERSON"}, {"entity": "OpenAI", "type": "ORG"}].'
    )

    response = query_llama(prompt, text, api_key)

    try:
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        json_text = response[json_start:json_end]
        parsed_response = json.loads(json_text)
        return JSONResponse({"entities": parsed_response}) if isinstance(parsed_response, list) else JSONResponse({"entities": []})
    except (json.JSONDecodeError, ValueError, AttributeError):
        return JSONResponse({"error": "Failed to parse entity recognition response"}, status_code=500)

@app.post("/analyze/key_elements")
async def key_elements(text: str = Form(...), api_key: str = Form(None)):
    return JSONResponse({"key_elements": query_llama("Extract key themes, topics, and concepts.", text, api_key)})

@app.post("/analyze/qa")
async def qa(text: str = Form(...), question: str = Form(...), api_key: str = Form(None)):
    return JSONResponse({"answer": query_llama(f"Answer this: {question}", text, api_key)})

@app.post("/analyze/compare")
async def compare_docs(text1: str = Form(...), text2: str = Form(...), api_key: str = Form(None)):
    return JSONResponse({"comparison": query_llama("Compare these two documents.", f"Doc1:\n{text1}\n\nDoc2:\n{text2}", api_key)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)