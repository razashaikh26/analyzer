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
import sys
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

# Load API keys
load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    print("🚨 API Key is missing! Please check your .env file.")
    API_KEY = "dummy_key_for_testing"  # Fallback for testing

print(f"API Key loaded: {API_KEY[:5]}...")  # Print first few characters for verification

MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

app = FastAPI()

# Add CORS middleware
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
    return {"message": "API is running!"}

# ==========================
# PARALLEL TEXT EXTRACTION
# ==========================
def is_tesseract_installed():
    """Check if Tesseract OCR is installed."""
    try:
        import shutil
        return shutil.which("tesseract") is not None
    except Exception:
        return False

def extract_text_from_pdf_with_ocr(content: bytes) -> str:
    """Extract text from PDF using OCR when regular extraction fails."""
    # Check if tesseract is available
    if not is_tesseract_installed():
        return "OCR extraction failed: Tesseract OCR is not installed on the server. Please try a different file format or a text-based PDF."
        
    try:
        print("Attempting OCR extraction for PDF...")
        # Convert PDF to images
        images = convert_from_bytes(content)
        
        if not images:
            return "Error: Could not convert PDF to images for OCR."
        
        print(f"Converted PDF to {len(images)} images for OCR processing")
        
        # Process each image with OCR
        texts = []
        for i, img in enumerate(images):
            try:
                text = pytesseract.image_to_string(img)
                if text.strip():
                    texts.append(text)
                else:
                    print(f"OCR extracted no text from page {i+1}")
            except Exception as e:
                print(f"OCR error on page {i+1}: {e}")
        
        if texts:
            return "\n".join(texts)
        else:
            return "OCR processing failed to extract text from the document. Try uploading a different format or a text-based PDF."
    except Exception as e:
        return f"OCR extraction error: {str(e)}"

def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF file using parallel processing with fallbacks."""
    try:
        # First attempt with pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            print(f"PDF has {len(pdf.pages)} pages")
            
            # Check if there are pages
            if len(pdf.pages) == 0:
                return "Error: PDF has no pages."
                
            # Try to extract with parallel processing
            with concurrent.futures.ThreadPoolExecutor() as executor:
                texts = list(executor.map(lambda page: page.extract_text() or "", pdf.pages))
            
            result = "\n".join(texts).strip()
            
            # If we got text, return it
            if result:
                return result
            
            # If no text was extracted, try page by page with detailed logging
            texts = []
            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        texts.append(page_text)
                    else:
                        print(f"Page {i+1} yielded no text")
                except Exception as e:
                    print(f"Error on page {i+1}: {e}")
            
            if texts:
                return "\n".join(texts)
            else:
                # Check if OCR is available
                if is_tesseract_installed():
                    # If still no text, this might be a scanned PDF
                    print("No text extracted. This may be a scanned PDF. Trying OCR...")
                    return extract_text_from_pdf_with_ocr(content)
                else:
                    # OCR not available
                    return "No text extracted from PDF. This appears to be a scanned document that requires OCR processing, but Tesseract OCR is not installed on the server. Please try a different file format."
                
    except Exception as e:
        error_msg = f"Error extracting PDF text: {str(e)}"
        print(error_msg)
        
        # Try OCR as fallback for any PDF extraction error
        if is_tesseract_installed():
            try:
                return extract_text_from_pdf_with_ocr(content)
            except Exception as ocr_e:
                return f"All PDF extraction methods failed: {str(e)}, OCR error: {str(ocr_e)}"
        else:
            return f"PDF extraction failed: {str(e)}. OCR might help but is not available on the server."

def extract_text_from_docx(content: bytes) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs).strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        return f"Error extracting DOCX text: {str(e)}"

def extract_text_from_txt(content: bytes) -> str:
    """Extract text from a TXT file."""
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        print(f"Error extracting TXT text: {e}")
        return f"Error extracting TXT text: {str(e)}"

def extract_text(file: UploadFile) -> str:
    """Detect file type and extract text efficiently."""
    content = file.file.read()
    filename = file.filename.lower()
    content_type = file.content_type
    
    print(f"Received file: {filename}, type: {content_type}, size: {len(content)} bytes")
    
    # Handle PDF files
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        return extract_text_from_pdf(content)
    # Handle DOCX files
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.endswith(".docx"):
        return extract_text_from_docx(content)
    # Handle TXT files
    elif content_type == "text/plain" or filename.endswith(".txt"):
        return extract_text_from_txt(content)
    # Handle CSV as text
    elif content_type == "text/csv" or filename.endswith(".csv"):
        return extract_text_from_txt(content)
    else:
        print(f"Unsupported file type: {content_type} for file {filename}")
        return f"Unsupported file type: {content_type} for file {filename}"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, extract_text, file)
        
        if text.startswith("Error") or text.startswith("Unsupported"):
            raise HTTPException(status_code=400, detail=text)
        
        return JSONResponse({
            "filename": file.filename,
            "text": text,
            "length": len(text)
        })
    except Exception as e:
        print(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

# ==========================
# AI-POWERED ANALYSIS
# ==========================
def query_llama(prompt: str, text: str) -> str:
    """Query Llama model with document text while handling large inputs."""
    if not text.strip():
        return "Error: No content to process."

    try:
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
async def summarize(text: str = Form(...)):
    return JSONResponse({"summary": query_llama("Summarize the document.", text)})

@app.post("/analyze/entities")
async def recognize_entities(text: str = Form(...)):
    """Extract named entities (PERSON, ORG, GEO, DATE) and return JSON format."""
    
    prompt = (
        "Extract named entities from the given text. "
        "Categorize them as PERSON, ORGANIZATION (ORG), GEOGRAPHICAL LOCATION (GEO), and DATE. "
        "Return results ONLY in JSON format:\n"
        '[{"entity": "Elon Musk", "type": "PERSON"}, {"entity": "OpenAI", "type": "ORG"}].'
    )

    response = query_llama(prompt, text)

    try:
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        json_text = response[json_start:json_end]
        parsed_response = json.loads(json_text)
        return JSONResponse({"entities": parsed_response}) if isinstance(parsed_response, list) else JSONResponse({"entities": []})
    except (json.JSONDecodeError, ValueError, AttributeError):
        return JSONResponse({"error": "Failed to parse entity recognition response"}, status_code=500)

@app.post("/analyze/key_elements")
async def key_elements(text: str = Form(...)):
    return JSONResponse({"key_elements": query_llama("Extract key themes, topics, and concepts.", text)})

@app.post("/analyze/qa")
async def qa(text: str = Form(...), question: str = Form(...)):
    return JSONResponse({"answer": query_llama(f"Answer this: {question}", text)})

@app.post("/analyze/compare")
async def compare_docs(text1: str = Form(...), text2: str = Form(...)):
    return JSONResponse({"comparison": query_llama("Compare these two documents.", f"Doc1:\n{text1}\n\nDoc2:\n{text2}")})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)