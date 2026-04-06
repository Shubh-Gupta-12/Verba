# Verba — Document Q&A Assistant

🔗 **Live**: [https://verba-6s5h.onrender.com](https://verba-6s5h.onrender.com)

Verba is a high-performance, production-ready Document Q&A Assistant. Upload any file — from complex scanned PDFs to Excel spreadsheets — and get instant, accurate answers sourced exclusively from your documents.

## ✨ Modern Performance Features

- **🚀 Parallel OCR Pipeline**: Scanned PDFs are processed up to **5x faster** using a concurrent `ThreadPoolExecutor` and Gemini 2.0 Flash Vision.
- **⚡ Asynchronous Processing**: Background document ingestion prevents "Server Error" timeouts. The UI instantly responds and auto-polls the backend for a seamless user experience.
- **📎 ChatGPT-Style UI**: Modern chat interface with inline document attachments, interactive chips, and polished toast notifications (no more browser alerts).
- **📝 Professional Formatting**: AI delivers answers in structured Markdown with headers, bolding, and clear bullet points for maximum readability.
- **🛑 Smart Rate Limiting**: Built-in conversational usage tracking with a rolling 3-hour window (50 messages) to manage API quotas gracefully.

## 🛠️ Technology Stack

- **Frontend**: Vanilla JavaScript + CSS (Glassmorphism & Dark Mode)
- **Backend**: Django 5 + Gunicorn
- **AI Models**: 
  - **Vision/OCR**: Gemini 2.0 Flash
  - **Reasoning**: Groq LLaMA 3 (70B)
  - **Embeddings**: Google Generative AI
- **Vector Storage**: Pinecone (Serverless)
- **Database/Cloud**: 
  - **PostgreSQL**: Supabase
  - **File Storage**: Supabase S3
- **Authentication**: Supabase Google OAuth + Session-based Auth

## 📄 File Support

| Format | Category |
|---|---|
| **PDF** | Standard & Scanned (via Vision OCR) |
| **DOCX / DOC** | Microsoft Word Documents |
| **TXT** | Plain Text Files |
| **XLSX / XLS / CSV** | Structured Spreadsheets & Data |
| **Images** | JPEG, PNG (via Vision OCR) |

## 🚀 Local Setup

```bash
# 1. Create venv and install dependencies
python -m venv .venv
.venv\Scripts\activate   # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure Environment Variables
# Copy your credentials into a .env file (see table below)

# 3. Run Migrations & Start Server
python manage.py migrate
python manage.py runserver
```

## 🔐 Environment Configuration

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Your Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Google AI Studio API Key |
| `GROQ_API_KEY` | GroqCloud API Key |
| `PINECONE_API_KEY` | Pinecone Console API Key |
| `SUPABASE_URL` | Supabase Project URL |
| `SUPABASE_ANON_KEY` | Supabase Anon/Public Key |
| `SUPABASE_STORAGE_URL` | S3 Endpoint for Supabase Storage |
| `SUPABASE_STORAGE_KEY` | S3 Access Key ID |
| `SUPABASE_STORAGE_SECRET` | S3 Secret Access Key |
| `SUPABASE_STORAGE_BUCKET` | Your S3 Bucket Name |

---
*Verba uses RAG (Retrieval-Augmented Generation) to ensure all answers are grounded in your uploaded documents.*
