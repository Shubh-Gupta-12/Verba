from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

import google.generativeai as genai
from groq import Groq
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
import docx

from django.conf import settings

from .models import Document, DocumentChunk


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _ensure_api_keys() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set")
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not set")


def _get_chroma_collection():
    client = chromadb.PersistentClient(path=str(settings.CHROMA_PATH))
    return client.get_or_create_collection("documents")


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
    return chunks


def _embed_texts(texts: Iterable[str]) -> List[List[float]]:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    embeddings: List[List[float]] = []
    for text in texts:
        response = genai.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        embeddings.append(response["embedding"])
    return embeddings


def process_document(document: Document) -> None:
    _ensure_api_keys()
    file_path = Path(document.file.path)
    text = _extract_text(file_path)
    chunks = _chunk_text(text)

    collection = _get_chroma_collection()
    embeddings = _embed_texts(chunks)

    ids = [f"{document.id}-{index}" for index in range(len(chunks))]
    metadatas = [
        {
            "document_id": document.id,
            "document_name": document.original_name,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]

    collection.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)

    DocumentChunk.objects.filter(document=document).delete()
    DocumentChunk.objects.bulk_create(
        [
            DocumentChunk(document=document, chunk_index=index, content=chunk)
            for index, chunk in enumerate(chunks)
        ]
    )


def delete_document_chunks(document_id: int) -> None:
    """Delete all chunks for a document from ChromaDB and the database."""
    collection = _get_chroma_collection()
    # Get all chunk IDs for this document
    results = collection.get(where={"document_id": document_id})
    if results and results["ids"]:
        collection.delete(ids=results["ids"])
    # Delete from database
    DocumentChunk.objects.filter(document_id=document_id).delete()


def _build_prompt(question: str, context_chunks: List[str]) -> List[dict]:
    context_text = "\n\n".join(context_chunks)
    system_prompt = (
        "You are a helpful assistant. Answer strictly from the provided context. "
        "If the context does not contain the answer, say you do not have enough information."
    )
    user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def answer_question(question: str, document_ids: Optional[List[int]] = None) -> dict:
    _ensure_api_keys()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    collection = _get_chroma_collection()
    query_embedding = _embed_texts([question])[0]

    where = None
    if document_ids:
        where = {"document_id": {"$in": document_ids}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=_build_prompt(question, documents),
        temperature=0.2,
    )

    answer = response.choices[0].message.content

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
