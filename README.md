# Verba — Document Q&A Assistant

🔗 **Live**: [https://verba-6s5h.onrender.com](https://verba-6s5h.onrender.com)

AI-powered document Q&A app. Upload PDF, DOCX, TXT, XLSX, CSV, or images — then ask questions and get answers sourced only from your documents.

## Stack

- **Backend**: Django 5, Gunicorn
- **AI**: Gemini (embeddings) + Groq LLaMA (answers)
- **Vector DB**: Pinecone
- **Database**: Supabase (PostgreSQL)
- **Storage**: Supabase S3
- **Auth**: Django sessions + Supabase Google OAuth
- **Deploy**: Render (Docker)

## Features

- 📄 Upload PDF, DOCX, TXT, XLSX, CSV, images
- 🔍 RAG-powered Q&A (answers only from your docs)
- 💬 Session-based chat with streaming responses
- 📎 ChatGPT-style attachment UI
- 🔐 Login / Register + Google Sign-In
- 🌙 Dark / Light mode
- 📱 Responsive design
- 🌐 Multi-language (EN, DE, ES, FR, HI)

## Local Setup

```bash
# 1. Create venv and install deps
python -m venv .venv
.venv\Scripts\activate   # or source .venv/bin/activate
pip install -r requirements.txt

# 2. Set environment variables in .env
# 3. Run migrations and start server
python manage.py migrate
python manage.py runserver
```

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GROQ_API_KEY` | Groq API key |
| `PINECONE_API_KEY` | Pinecone API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_STORAGE_URL` | Supabase S3 storage URL |
| `SUPABASE_STORAGE_KEY` | Supabase S3 access key |
| `SUPABASE_STORAGE_SECRET` | Supabase S3 secret key |
| `SUPABASE_STORAGE_BUCKET` | Supabase S3 bucket name |
