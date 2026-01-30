import json
from typing import List

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import Document, ChatMessage, ChatSession
from .rag import answer_question, process_document


def index(request):
	return render(request, "documents/index.html")


@require_http_methods(["POST"])
def create_session(request):
	session = ChatSession.objects.create(title="New Chat")
	return JsonResponse({
		"id": session.id,
		"title": session.title,
		"created_at": session.created_at.isoformat(),
	})


@require_http_methods(["GET"])
def list_sessions(request):
	sessions = ChatSession.objects.all()
	return JsonResponse({
		"sessions": [
			{
				"id": s.id,
				"title": s.title,
				"created_at": s.created_at.isoformat(),
				"updated_at": s.updated_at.isoformat(),
			}
			for s in sessions
		]
	})


@require_http_methods(["GET"])
def get_session(request, session_id):
	session = get_object_or_404(ChatSession, id=session_id)
	messages = session.messages.all()
	documents = session.documents.all()
	return JsonResponse({
		"id": session.id,
		"title": session.title,
		"messages": [
			{
				"id": msg.id,
				"role": msg.role,
				"content": msg.content,
				"created_at": msg.created_at.isoformat(),
			}
			for msg in messages
		],
		"documents": [
			{
				"id": doc.id,
				"name": doc.original_name,
				"status": doc.status,
				"uploaded_at": doc.uploaded_at.isoformat(),
			}
			for doc in documents
		]
	})


@require_http_methods(["DELETE"])
def delete_session(request, session_id):
	session = get_object_or_404(ChatSession, id=session_id)
	session.delete()
	return JsonResponse({"status": "deleted"})


@require_http_methods(["POST"])
def upload_document(request):
	if "file" not in request.FILES:
		return HttpResponseBadRequest("Missing file")

	session_id = request.POST.get("session_id")
	session = None
	if session_id:
		session = get_object_or_404(ChatSession, id=session_id)

	upload = request.FILES["file"]
	document = Document.objects.create(
		file=upload,
		original_name=upload.name,
		session=session
	)

	try:
		process_document(document)
		document.status = Document.STATUS_READY
		document.error_message = ""
	except Exception as exc:
		document.status = Document.STATUS_FAILED
		document.error_message = str(exc)
	finally:
		document.save(update_fields=["status", "error_message"])

	# Update session title based on first document if it's still "New Chat"
	if session and session.title == "New Chat":
		session.title = upload.name[:50]
		session.save(update_fields=["title"])

	return JsonResponse({
		"id": document.id,
		"name": document.original_name,
		"status": document.status,
		"error": document.error_message,
	})


@require_http_methods(["POST"])
def ask_question(request):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")

	question = payload.get("question", "").strip()
	if not question:
		return HttpResponseBadRequest("Question is required")

	session_id = payload.get("session_id")
	session = None
	if session_id:
		session = get_object_or_404(ChatSession, id=session_id)

	# Save user message
	ChatMessage.objects.create(
		session=session,
		role=ChatMessage.ROLE_USER,
		content=question
	)

	# Get document IDs for this session only
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))

	response = answer_question(question, document_ids=document_ids)

	# Save assistant response
	ChatMessage.objects.create(
		session=session,
		role=ChatMessage.ROLE_ASSISTANT,
		content=response["answer"]
	)

	# Update session title from first question if still "New Chat"
	if session and session.title == "New Chat":
		session.title = question[:50]
		session.save(update_fields=["title"])

	# Touch session to update updated_at
	if session:
		session.save()

	return JsonResponse(response)


@require_http_methods(["GET"])
def list_documents(request):
	session_id = request.GET.get("session_id")
	if session_id:
		documents = Document.objects.filter(session_id=session_id).order_by("-uploaded_at")
	else:
		documents = Document.objects.filter(session__isnull=True).order_by("-uploaded_at")

	return JsonResponse({
		"documents": [
			{
				"id": doc.id,
				"name": doc.original_name,
				"status": doc.status,
				"uploaded_at": doc.uploaded_at.isoformat(),
			}
			for doc in documents
		]
	})


@require_http_methods(["DELETE"])
def delete_document(request, document_id):
	document = get_object_or_404(Document, id=document_id)
	# Delete associated chunks from ChromaDB
	from .rag import delete_document_chunks
	delete_document_chunks(document_id)
	# Delete the file and database record
	if document.file:
		document.file.delete(save=False)
	document.delete()
	return JsonResponse({"status": "deleted"})
