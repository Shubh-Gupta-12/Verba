from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Iterable, List, Optional

from google import genai
from google.genai import types as genai_types
from groq import Groq
from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import docx

from django.conf import settings

from .models import Document, DocumentChunk


logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds


def _retry(func, *args, retries=MAX_RETRIES, **kwargs):
    """Retry a function with exponential backoff."""
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Failed after {retries} attempts: {e}")
                raise
            wait = RETRY_BACKOFF * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)


def _ensure_api_keys() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set")
    if not settings.PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY is not set")


def _get_pinecone_index():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc.Index(settings.PINECONE_INDEX_NAME)


def _extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        doc = docx.Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)

    return file_path.read_text(encoding="utf-8", errors="ignore")


def _chunk_text(text: str) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
    logger.info(f"Split text into {len(chunks)} chunks")
    return chunks


def _embed_texts(texts: Iterable[str]) -> List[List[float]]:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = settings.GEMINI_EMBEDDING_MODEL.removeprefix("models/")
    dims = getattr(settings, "GEMINI_EMBEDDING_DIMENSIONS", 768)
    text_list = list(texts)

    if not text_list:
        return []

    # Batch embed — up to 100 texts per API call (Gemini limit)
    all_embeddings: List[List[float]] = []
    batch_size = 100
    for i in range(0, len(text_list), batch_size):
        batch = text_list[i:i + batch_size]
        logger.info(f"Embedding batch {i // batch_size + 1} ({len(batch)} texts)")
        response = _retry(
            client.models.embed_content,
            model=model_name,
            contents=batch,
            config=genai_types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=dims,
            ),
        )
        for emb in response.embeddings:
            all_embeddings.append(list(emb.values))

    logger.info(f"Embedded {len(all_embeddings)} texts total")
    return all_embeddings


def process_document(document: Document) -> None:
    logger.info(f"Processing document: {document.original_name} (ID: {document.id})")
    _ensure_api_keys()
    file_path = Path(document.file.path)
    text = _extract_text(file_path)
    chunks = _chunk_text(text)

    index = _get_pinecone_index()
    embeddings = _embed_texts(chunks)

    vectors = []
    for i, chunk in enumerate(chunks):
        vectors.append({
            "id": f"{document.id}-{i}",
            "values": embeddings[i],
            "metadata": {
                "document_id": str(document.id),
                "document_name": document.original_name,
                "chunk_index": i,
                "text": chunk
            }
        })

    # Upsert in batches of 100 to avoid Pinecone limits
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        _retry(index.upsert, vectors=vectors[i:i + batch_size])

    DocumentChunk.objects.filter(document=document).delete()
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(document=document, chunk_index=idx, content=chunk)
            for idx, chunk in enumerate(chunks)
        ]
    )
    logger.info(f"Document processed successfully: {document.original_name}")


def delete_document_chunks(document_id: int) -> None:
    """Delete all chunks for a document from Pinecone and the database."""
    logger.info(f"Deleting chunks for document ID: {document_id}")
    try:
        index = _get_pinecone_index()
        chunks = DocumentChunk.objects.filter(document_id=document_id)
        ids_to_delete = [f"{document_id}-{chunk.chunk_index}" for chunk in chunks]

        if ids_to_delete:
            batch_size = 100
            for i in range(0, len(ids_to_delete), batch_size):
                _retry(index.delete, ids=ids_to_delete[i:i + batch_size])
    except Exception as e:
        logger.error(f"Error deleting from Pinecone: {e}")

    DocumentChunk.objects.filter(document_id=document_id).delete()
    logger.info(f"Chunks deleted for document ID: {document_id}")


def _build_prompt(question: str, context_chunks: List[str], chat_history: Optional[List[dict]] = None) -> List[dict]:
    context_text = "\n\n".join(context_chunks)
    system_prompt = (
        "You are a helpful assistant. Answer strictly from the provided context. "
        "If the context does not contain the answer, say you do not have enough information."
    )
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history for memory (Phase 3 item 14)
    if chat_history:
        for msg in chat_history[-6:]:  # Last 6 messages for context window
            messages.append({"role": msg["role"], "content": msg["content"]})

    user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
    messages.append({"role": "user", "content": user_prompt})
    return messages


def answer_question(question: str, document_ids: Optional[List[int]] = None, chat_history: Optional[List[dict]] = None, model: Optional[str] = None) -> dict:
    logger.info(f"Answering question: {question[:100]}...")
    _ensure_api_keys()

    index = _get_pinecone_index()
    query_embedding = _embed_texts([question])[0]

    filter_dict = None
    if document_ids:
        str_ids = [str(did) for did in document_ids]
        filter_dict = {"document_id": {"$in": str_ids}}

    results = _retry(
        index.query,
        vector=query_embedding,
        top_k=5,
        filter=filter_dict,
        include_metadata=True
    )

    documents = []
    metadatas = []

    matches = getattr(results, 'matches', None) or results.get('matches', []) if isinstance(results, dict) else getattr(results, 'matches', [])
    for match in matches:
        metadata = getattr(match, 'metadata', None) or (match.get('metadata', {}) if isinstance(match, dict) else {})
        text = metadata.get('text', '') if isinstance(metadata, dict) else getattr(metadata, 'text', '')
        documents.append(text)
        metadatas.append(dict(metadata) if not isinstance(metadata, dict) else metadata)

    # Use the selected model or fall back to default
    selected_model = model if model and model in settings.AVAILABLE_MODELS else settings.GROQ_MODEL
    logger.info(f"Using model: {selected_model}")

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = _retry(
        client.chat.completions.create,
        model=selected_model,
        messages=_build_prompt(question, documents, chat_history),
        temperature=0.2,
    )

    answer = response.choices[0].message.content
    logger.info(f"Answer generated successfully ({len(answer)} chars)")

    sources = []
    for doc_text, metadata in zip(documents, metadatas):
        sources.append(
            {
                "document_id": metadata.get("document_id"),
                "document_name": metadata.get("document_name"),
                "chunk_index": metadata.get("chunk_index"),
                "content": doc_text,
            }
        )

    return {"answer": answer, "sources": sources}
