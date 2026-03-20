import json
import logging
from typing import List

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .models import Document, ChatMessage, ChatSession
from .rag import answer_question, process_document, SUPPORTED_EXTENSIONS


logger = logging.getLogger(__name__)


@login_required
def index(request):
	return render(request, "documents/index.html")


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def create_session(request):
	session = ChatSession.objects.create(title="New Chat", user=request.user)
	return JsonResponse({
		"id": session.id,
		"title": session.title,
		"created_at": session.created_at.isoformat(),
	})


@login_required
@require_http_methods(["GET"])
def list_sessions(request):
	sessions = ChatSession.objects.filter(user=request.user).only('id', 'title', 'created_at', 'updated_at').order_by('-updated_at')[:30]
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


@login_required
@require_http_methods(["GET"])
def get_session(request, session_id):
	session = get_object_or_404(ChatSession, id=session_id, user=request.user)
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


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
	session = get_object_or_404(ChatSession, id=session_id, user=request.user)
	session.delete()
	return JsonResponse({"status": "deleted"})


@csrf_exempt
@login_required
@ratelimit(key='ip', rate='20/m', method='POST', block=True)
@require_http_methods(["POST"])
def upload_document(request):
	if "file" not in request.FILES:
		return HttpResponseBadRequest("Missing file")

	upload = request.FILES["file"]

	# Validate file extension
	file_ext = '.' + upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
	if file_ext not in SUPPORTED_EXTENSIONS:
		return JsonResponse({
			"error": f"Unsupported file type: {file_ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
		}, status=400)

	# Validate file size (10 MB limit)
	if upload.size > 10 * 1024 * 1024:
		return JsonResponse({"error": "File too large. Maximum size is 10 MB."}, status=400)

	session_id = request.POST.get("session_id")
	session = None
	if session_id:
		session = get_object_or_404(ChatSession, id=session_id)

	document = Document.objects.create(
		file=upload,
		original_name=upload.name,
		session=session
	)

	try:
		process_document(document)
		document.status = Document.STATUS_READY
		document.error_message = ""
		logger.info(f"Document uploaded successfully: {upload.name}")
	except Exception as exc:
		document.status = Document.STATUS_FAILED
		document.error_message = str(exc)
		logger.error(f"Document upload failed: {upload.name} - {exc}")
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


@csrf_exempt
@login_required
@ratelimit(key='ip', rate='30/m', method='POST', block=True)
@require_http_methods(["POST"])
def ask_question(request):
	try:
		payload = json.loads(request.body or "{}")
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")

	question = payload.get("question", "").strip()
	if not question:
		return HttpResponseBadRequest("Question is required")

	if len(question) > 2000:
		return JsonResponse({"error": "Question too long. Maximum 2000 characters."}, status=400)

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

	# Build conversation history for memory
	chat_history = None
	if session:
		recent_messages = session.messages.order_by('-created_at')[:6]
		chat_history = [
			{"role": msg.role, "content": msg.content}
			for msg in reversed(recent_messages)
		]

	# Get selected model
	selected_model = payload.get("model")

	response = answer_question(question, document_ids=document_ids, chat_history=chat_history, model=selected_model)

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


@login_required
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


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete_document(request, document_id):
	document = get_object_or_404(Document, id=document_id)
	# Delete associated chunks from Pinecone
	from .rag import delete_document_chunks
	delete_document_chunks(document_id)
	# Delete the file and database record
	if document.file:
		document.file.delete(save=False)
	document.delete()
	return JsonResponse({"status": "deleted"})


@login_required
@require_http_methods(["GET"])
def list_models(request):
	"""Return a list of available LLM models."""
	models = [
		{"id": model_id, **info}
		for model_id, info in settings.AVAILABLE_MODELS.items()
	]
	return JsonResponse({"models": models, "default": settings.GROQ_MODEL})


@login_required
@require_http_methods(["GET"])
def search_sessions(request):
	"""Search across all sessions by title or message content."""
	query = request.GET.get("q", "").strip()
	if not query:
		return JsonResponse({"sessions": []})

	from django.db.models import Q
	sessions = ChatSession.objects.filter(
		Q(title__icontains=query) |
		Q(messages__content__icontains=query)
	).distinct().order_by("-updated_at")[:20]

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


@login_required
@require_http_methods(["GET"])
def export_chat(request, session_id):
	"""Export a chat session as Markdown."""
	session = get_object_or_404(ChatSession, id=session_id)
	messages = session.messages.all()
	documents = session.documents.all()

	lines = [f"# {session.title}\n"]
	lines.append(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}\n")

	if documents:
		lines.append("## Documents\n")
		for doc in documents:
			lines.append(f"- {doc.original_name} ({doc.status})")
		lines.append("")

	lines.append("## Conversation\n")
	for msg in messages:
		role_label = "**You**" if msg.role == "user" else "**Assistant**"
		lines.append(f"{role_label}: {msg.content}\n")

	content = "\n".join(lines)

	from django.http import HttpResponse
	response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
	response["Content-Disposition"] = f'attachment; filename="{session.title[:50]}.md"'
	return response

