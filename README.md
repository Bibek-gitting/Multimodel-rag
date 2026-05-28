# Multimodal RAG Chat Application

A multimodal RAG (Retrieval-Augmented Generation) system built with JavaScript frontend and FastAPI backend.

## Project Structure

```
Multimodel-rag/
├── frontend/
│   ├── index.html    # Main HTML file
│   ├── styles.css    # CSS styles
│   └── app.js        # JavaScript functionality
├── backend/
│   ├── fastapi_main.py
│   └── rag_base/
├── models/
├── uploaded_media_files/
└── README.md
```

## Setup

### Backend (FastAPI)

1. Navigate to the backend directory:

   ```bash
   cd backend
   ```

2. Install Python dependencies:

   ```bash
   pip install -r ../requirements.txt
   ```

3. Run the FastAPI server:
   ```bash
   python fastapi_main.py
   ```

The API will be available at `http://localhost:8000`

### Frontend

Simply open `frontend/index.html` in a web browser. The frontend will connect to the FastAPI backend.

## Usage

1. Start the FastAPI backend
2. Open `frontend/index.html` in your browser
3. Start chatting with your documents!

## API Endpoints

- `POST /ask` - Ask a question to the RAG system
- `POST /upload` - Upload documents for processing
