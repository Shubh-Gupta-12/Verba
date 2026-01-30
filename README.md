# Document Q&A Assistant

A Django full‑stack app that lets users upload documents (PDF, DOCX, TXT) and ask questions using a RAG pipeline. Documents are chunked, embedded with Gemini, stored in Chroma, and answers are generated via Groq Llama.

## Setup

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill in:
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
3. Run migrations and start the server.

## Commands

- Install dependencies: `pip install -r requirements.txt`
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Run server: `python manage.py runserver`

## Usage

- Upload documents on the home page.
- Ask questions in the chat panel.
- The assistant answers using only the uploaded content.
