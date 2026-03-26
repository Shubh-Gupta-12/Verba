# pyre-ignore-all-errors
import json
import logging
from typing import List

from django.conf import settings  # type: ignore
from django.contrib.auth.decorators import login_required  # type: ignore
from django.http import JsonResponse, HttpResponseBadRequest, StreamingHttpResponse  # type: ignore
from django.shortcuts import render, get_object_or_404  # type: ignore
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from django.views.decorators.http import require_http_methods  # type: ignore
from django.views.decorators.cache import cache_page  # type: ignore
from django_ratelimit.decorators import ratelimit  # type: ignore

from .models import Document, ChatMessage, ChatSession  # type: ignore
from .rag import answer_question, stream_answer_question, process_document, SUPPORTED_EXTENSIONS  # type: ignore
from django.core.cache import cache  # type: ignore
import time
from datetime import datetime


logger = logging.getLogger(__name__)

def check_chat_limit(user):  # type: ignore
	# Free tier: 50 messages per 3 hours
	limit = 50
	window_hours = 3
	cache_key = f"user_msg_limit_{user.id}"  # type: ignore
	
	data = cache.get(cache_key)  # type: ignore
	now = time.time()
	
	if not data or now > data["reset_time"]:  # type: ignore
		data = {"count": 0, "reset_time": now + (window_hours * 3600)}
	
	if data["count"] >= limit:  # type: ignore
		reset_dt = datetime.fromtimestamp(data["reset_time"])  # type: ignore
		time_str = reset_dt.strftime("%I:%M %p")  # type: ignore
		return False, f"You have reached your limit of {limit} questions per {window_hours} hours. Please try again after {time_str}."
		
	data["count"] += 1  # type: ignore
	cache.set(cache_key, data, timeout=int(data["reset_time"] - now))  # type: ignore
	return True, ""


@login_required  # type: ignore
def index(request):  # type: ignore
	return render(request, "documents/index.html")  # type: ignore


@login_required  # type: ignore
def api_docs(request):  # type: ignore
	return render(request, "documents/api_docs.html")  # type: ignore


@csrf_exempt  # type: ignore
@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def create_session(request):  # type: ignore
	session = ChatSession.objects.create(title="New Chat", user=request.user)  # type: ignore
	return JsonResponse({  # type: ignore
		"id": session.id,  # type: ignore
		"title": session.title,  # type: ignore
		"created_at": session.created_at.isoformat(),  # type: ignore
	})


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def list_sessions(request):  # type: ignore
	sessions = ChatSession.objects.filter(user=request.user).only('id', 'title', 'created_at', 'updated_at').order_by('-updated_at')[:30]  # type: ignore
	return JsonResponse({  # type: ignore
		"sessions": [
			{
				"id": s.id,  # type: ignore
				"title": s.title,  # type: ignore
				"created_at": s.created_at.isoformat(),  # type: ignore
				"updated_at": s.updated_at.isoformat(),  # type: ignore
			}
			for s in sessions  # type: ignore
		]
	})


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def get_session(request, session_id):  # type: ignore
	session = get_object_or_404(ChatSession, id=session_id, user=request.user)  # type: ignore
	messages = session.messages.all()  # type: ignore
	documents = session.documents.all()  # type: ignore
	return JsonResponse({  # type: ignore
		"id": session.id,  # type: ignore
		"title": session.title,  # type: ignore
		"messages": [
			{
				"id": msg.id,  # type: ignore
				"role": msg.role,  # type: ignore
				"content": msg.content,  # type: ignore
				"created_at": msg.created_at.isoformat(),  # type: ignore
			}
			for msg in messages  # type: ignore
		],
		"documents": [
			{
				"id": doc.id,  # type: ignore
				"name": doc.original_name,  # type: ignore
				"status": doc.status,  # type: ignore
				"uploaded_at": doc.uploaded_at.isoformat(),  # type: ignore
			}
			for doc in documents  # type: ignore
		]
	})


@csrf_exempt  # type: ignore
@login_required  # type: ignore
@require_http_methods(["DELETE"])  # type: ignore
def delete_session(request, session_id):  # type: ignore
	session = get_object_or_404(ChatSession, id=session_id, user=request.user)  # type: ignore
	session.delete()  # type: ignore
	return JsonResponse({"status": "deleted"})  # type: ignore


@csrf_exempt  # type: ignore
@login_required  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def upload_document(request):  # type: ignore
	"""Upload one or more documents. Supports multi-file via request.FILES.getlist('file')."""
	try:
		files = request.FILES.getlist("file")  # type: ignore
		if not files:
			# Fallback: try single file key
			single = request.FILES.get("file")  # type: ignore
			if single:
				files = [single]
			else:
				return JsonResponse({"error": "No file provided."}, status=400)  # type: ignore

		session_id = request.POST.get("session_id")  # type: ignore
		session = None
		if session_id:
			try:
				session = ChatSession.objects.get(id=session_id, user=request.user)  # type: ignore
			except ChatSession.DoesNotExist:  # type: ignore
				return JsonResponse({"error": "Chat session not found."}, status=404)  # type: ignore

		# Enforce 5-document limit per session
		current_count = 0
		if session:
			current_count = session.documents.count()  # type: ignore
		if current_count + len(files) > 5:
			remaining = 5 - current_count
			return JsonResponse({  # type: ignore
				"error": f"Maximum 5 documents per chat. You can upload {remaining} more document(s)."
			}, status=400)

		results = []
		for upload in files:  # type: ignore
			# Validate file extension
			file_ext = '.' + upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''  # type: ignore
			if file_ext not in SUPPORTED_EXTENSIONS:
				results.append({"name": upload.name, "status": "failed", "error": f"Unsupported file type: {file_ext}"})  # type: ignore
				continue

			# Validate file size (10 MB limit)
			if upload.size and upload.size > 10 * 1024 * 1024:  # type: ignore
				results.append({"name": upload.name, "status": "failed", "error": "File too large. Maximum 10 MB."})  # type: ignore
				continue

			try:
				document = Document.objects.create(  # type: ignore
					file=upload,
					original_name=upload.name,  # type: ignore
					session=session
				)
			except Exception as exc:
				logger.error("Failed to save document %s: %s", upload.name, exc, exc_info=True)  # type: ignore
				results.append({"name": upload.name, "status": "failed", "error": f"Failed to save: {exc}"})  # type: ignore
				continue

			try:
				process_document(document)  # type: ignore
				document.status = Document.STATUS_READY  # type: ignore
				document.error_message = ""  # type: ignore
				logger.info("Document uploaded successfully: %s", upload.name)  # type: ignore
			except Exception as exc:
				document.status = Document.STATUS_FAILED  # type: ignore
				document.error_message = str(exc)  # type: ignore
				logger.error("Document processing failed: %s - %s", upload.name, exc, exc_info=True)  # type: ignore
			finally:
				document.save(update_fields=["status", "error_message"])  # type: ignore

			results.append({  # type: ignore
				"id": document.id,  # type: ignore
				"name": document.original_name,  # type: ignore
				"status": document.status,  # type: ignore
				"error": document.error_message or "",  # type: ignore
			})

		# Update session title based on first document if it's still "New Chat"
		if session and session.title == "New Chat" and results:  # type: ignore
			first_ok = next((r for r in results if r.get("status") == "ready"), None)  # type: ignore
			if first_ok:
				session.title = str(first_ok["name"])[:50]  # type: ignore
				session.save(update_fields=["title"])  # type: ignore

		# For single-file backward compatibility: return single object if only 1 file
		if len(results) == 1:
			return JsonResponse(results[0])  # type: ignore
		return JsonResponse({"documents": results})  # type: ignore

	except Exception as exc:
		logger.error("Upload handler crashed: %s", exc, exc_info=True)
		return JsonResponse({"error": f"Upload failed: {str(exc)}"}, status=500)  # type: ignore


@csrf_exempt  # type: ignore
@login_required  # type: ignore
@ratelimit(key='ip', rate='30/m', method='POST', block=True)  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def ask_question(request):  # type: ignore
	try:
		payload = json.loads(request.body or "{}")  # type: ignore
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")  # type: ignore

	try:
		from .rag import _ensure_api_keys  # type: ignore
		_ensure_api_keys()  # type: ignore
	except Exception as e:
		return JsonResponse({"error": f"{str(e)}. Please add the required keys to your Render environment variables."}, status=400)  # type: ignore

	question = payload.get("question", "").strip()  # type: ignore
	if not question:
		return HttpResponseBadRequest("Question is required")  # type: ignore

	if len(question) > 2000:  # type: ignore
		return JsonResponse({"error": "Question too long. Maximum 2000 characters."}, status=400)  # type: ignore

	is_allowed, limit_msg = check_chat_limit(request.user)  # type: ignore
	if not is_allowed:
		return JsonResponse({"error": limit_msg}, status=403)  # type: ignore

	session_id = payload.get("session_id")  # type: ignore
	session = None
	if session_id:
		session = get_object_or_404(ChatSession, id=session_id)  # type: ignore

	# Save user message
	ChatMessage.objects.create(  # type: ignore
		session=session,
		role=ChatMessage.ROLE_USER,  # type: ignore
		content=question
	)

	# Get document IDs for this session only
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))  # type: ignore

	if not document_ids:
		return JsonResponse({"error": "Please upload a document first. You can only ask questions about your uploaded documents."}, status=400)  # type: ignore

	# Build conversation history for memory
	chat_history = None
	if session:
		recent_messages = session.messages.order_by('-created_at')[:6]  # type: ignore
		chat_history = [
			{"role": msg.role, "content": msg.content}  # type: ignore
			for msg in reversed(recent_messages)  # type: ignore
		]

	# Get selected model
	selected_model = payload.get("model")  # type: ignore

	response = answer_question(question, document_ids=document_ids, chat_history=chat_history, model=selected_model)  # type: ignore

	# Save assistant response
	ChatMessage.objects.create(  # type: ignore
		session=session,
		role=ChatMessage.ROLE_ASSISTANT,  # type: ignore
		content=response["answer"]  # type: ignore
	)

	# Update session title from first question if still "New Chat"
	if session and session.title == "New Chat":  # type: ignore
		session.title = question[:50]  # type: ignore
		session.save(update_fields=["title"])  # type: ignore

	# Touch session to update updated_at
	if session:
		session.save()  # type: ignore

	return JsonResponse(response)  # type: ignore


@csrf_exempt  # type: ignore
@login_required  # type: ignore
@ratelimit(key='ip', rate='30/m', method='POST', block=True)  # type: ignore
@require_http_methods(["POST"])  # type: ignore
def ask_question_stream(request):  # type: ignore
	"""SSE streaming endpoint — tokens arrive in real-time."""
	try:
		payload = json.loads(request.body or "{}")  # type: ignore
	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")  # type: ignore

	try:
		from .rag import _ensure_api_keys  # type: ignore
		_ensure_api_keys()  # type: ignore
	except Exception as e:
		return JsonResponse({"error": f"{str(e)}. Please add the required keys to your Render environment variables."}, status=400)  # type: ignore

	question = payload.get("question", "").strip()  # type: ignore
	if not question:
		return HttpResponseBadRequest("Question is required")  # type: ignore

	if len(question) > 2000:  # type: ignore
		return JsonResponse({"error": "Question too long. Maximum 2000 characters."}, status=400)  # type: ignore

	is_allowed, limit_msg = check_chat_limit(request.user)  # type: ignore
	if not is_allowed:
		return JsonResponse({"error": limit_msg}, status=403)  # type: ignore

	session_id = payload.get("session_id")  # type: ignore
	session = None
	if session_id:
		session = get_object_or_404(ChatSession, id=session_id, user=request.user)  # type: ignore

	# Save user message
	ChatMessage.objects.create(  # type: ignore
		session=session,
		role=ChatMessage.ROLE_USER,  # type: ignore
		content=question
	)

	# Get document IDs for this session
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))  # type: ignore

	if not document_ids:
		return JsonResponse({"error": "Please upload a document first. You can only ask questions about your uploaded documents."}, status=400)  # type: ignore

	# Build conversation history
	chat_history = None
	if session:
		recent_messages = session.messages.order_by('-created_at')[:6]  # type: ignore
		chat_history = [
			{"role": msg.role, "content": msg.content}  # type: ignore
			for msg in reversed(recent_messages)  # type: ignore
		]

	selected_model = payload.get("model")  # type: ignore

	def event_stream():  # type: ignore
		for event in stream_answer_question(question, document_ids=document_ids, chat_history=chat_history, model=selected_model):  # type: ignore
			yield f"data: {json.dumps(event)}\n\n"  # type: ignore

			# When done, save the assistant message
			if event["type"] == "done":  # type: ignore
				ChatMessage.objects.create(  # type: ignore
					session=session,
					role=ChatMessage.ROLE_ASSISTANT,  # type: ignore
					content=event["answer"]  # type: ignore
				)
				if session and session.title == "New Chat":  # type: ignore
					session.title = question[:50]  # type: ignore
					session.save(update_fields=["title"])  # type: ignore
				if session:
					session.save()  # type: ignore

	response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")  # type: ignore
	response["Cache-Control"] = "no-cache"  # type: ignore
	response["X-Accel-Buffering"] = "no"  # type: ignore
	return response

@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def list_documents(request):  # type: ignore
	session_id = request.GET.get("session_id")  # type: ignore
	if session_id:
		documents = Document.objects.filter(session_id=session_id).order_by("-uploaded_at")  # type: ignore
	else:
		documents = Document.objects.filter(session__isnull=True).order_by("-uploaded_at")  # type: ignore

	return JsonResponse({  # type: ignore
		"documents": [
			{
				"id": doc.id,  # type: ignore
				"name": doc.original_name,  # type: ignore
				"status": doc.status,  # type: ignore
				"uploaded_at": doc.uploaded_at.isoformat(),  # type: ignore
			}
			for doc in documents  # type: ignore
		]
	})


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def preview_document(request, document_id):  # type: ignore
	"""Return first few chunks of a document for preview."""
	document = get_object_or_404(Document, id=document_id)  # type: ignore
	from .models import DocumentChunk  # type: ignore
	chunks = DocumentChunk.objects.filter(document=document).order_by("chunk_index")[:3]  # type: ignore
	preview_text = "\n\n".join(chunk.content for chunk in chunks)  # type: ignore
	return JsonResponse({  # type: ignore
		"id": document.id,  # type: ignore
		"name": document.original_name,  # type: ignore
		"status": document.status,  # type: ignore
		"preview": str(preview_text)[:3000],  # type: ignore
		"total_chunks": document.chunks.count(),  # type: ignore
	})



@csrf_exempt  # type: ignore
@login_required  # type: ignore
@require_http_methods(["DELETE"])  # type: ignore
def delete_document(request, document_id):  # type: ignore
	document = get_object_or_404(Document, id=document_id)  # type: ignore
	# Delete associated chunks from Pinecone
	from .rag import delete_document_chunks  # type: ignore
	delete_document_chunks(document_id)  # type: ignore
	# Delete the file and database record
	if document.file:  # type: ignore
		document.file.delete(save=False)  # type: ignore
	document.delete()  # type: ignore
	return JsonResponse({"status": "deleted"})  # type: ignore


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
@cache_page(60 * 60)  # type: ignore
def list_models(request):  # type: ignore
	"""Return a list of available LLM models."""
	models = [  # type: ignore
		{"id": model_id, **info}  # type: ignore
		for model_id, info in settings.AVAILABLE_MODELS.items()  # type: ignore
	]
	return JsonResponse({"models": models, "default": settings.GROQ_MODEL})  # type: ignore


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def search_sessions(request):  # type: ignore
	"""Search across all sessions by title or message content."""
	query = request.GET.get("q", "").strip()  # type: ignore
	if not query:
		return JsonResponse({"sessions": []})  # type: ignore

	from django.db.models import Q  # type: ignore
	sessions = ChatSession.objects.filter(  # type: ignore
		Q(title__icontains=query) |  # type: ignore
		Q(messages__content__icontains=query)  # type: ignore
	).distinct().order_by("-updated_at")[:20]  # type: ignore

	return JsonResponse({  # type: ignore
		"sessions": [
			{
				"id": s.id,  # type: ignore
				"title": s.title,  # type: ignore
				"created_at": s.created_at.isoformat(),  # type: ignore
				"updated_at": s.updated_at.isoformat(),  # type: ignore
			}
			for s in sessions  # type: ignore
		]
	})


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def export_chat(request, session_id):  # type: ignore
	"""Export a chat session as Markdown."""
	session = get_object_or_404(ChatSession, id=session_id)  # type: ignore
	messages = session.messages.all()  # type: ignore
	documents = session.documents.all()  # type: ignore

	lines = [f"# {session.title}\n"]  # type: ignore
	lines.append(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}\n")  # type: ignore

	if documents:
		lines.append("## Documents\n")
		for doc in documents:  # type: ignore
			lines.append(f"- {doc.original_name} ({doc.status})")  # type: ignore
		lines.append("")

	lines.append("## Conversation\n")
	for msg in messages:  # type: ignore
		role_label = "**You**" if msg.role == "user" else "**Assistant**"  # type: ignore
		lines.append(f"{role_label}: {msg.content}\n")  # type: ignore

	content = "\n".join(lines)

	from django.http import HttpResponse  # type: ignore
	response = HttpResponse(content, content_type="text/markdown; charset=utf-8")  # type: ignore
	response["Content-Disposition"] = f'attachment; filename="{session.title[:50]}.md"'  # type: ignore
	return response


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
@cache_page(60 * 5)  # type: ignore
def analytics_dashboard(request):  # type: ignore
	"""Return aggregate analytics for the platform (admin only)."""
	if not request.user.is_staff:  # type: ignore
		return JsonResponse({"error": "Unauthorized"}, status=403)  # type: ignore
		
	from django.contrib.auth.models import User  # type: ignore
	from django.db.models import Count  # type: ignore
	
	total_users = User.objects.count()  # type: ignore
	total_sessions = ChatSession.objects.count()  # type: ignore
	total_messages = ChatMessage.objects.count()  # type: ignore
	total_documents = Document.objects.count()  # type: ignore
	
	# Top 5 users by session count
	top_users = User.objects.annotate(  # type: ignore
		session_count=Count('chatsession')  # type: ignore
	).order_by('-session_count')[:5]  # type: ignore
	
	top_users_data = [
		{"username": u.username, "sessions": u.session_count}  # type: ignore
		for u in top_users  # type: ignore
	]
	
	return JsonResponse({  # type: ignore
		"totals": {
			"users": total_users,
			"sessions": total_sessions,
			"messages": total_messages,
			"documents": total_documents,
		},
		"top_users": top_users_data
	})


@login_required  # type: ignore
@require_http_methods(["GET"])  # type: ignore
def analytics_page(request):  # type: ignore
	"""Render the analytics dashboard page (admin only)."""
	if not request.user.is_staff:  # type: ignore
		from django.shortcuts import redirect  # type: ignore
		from django.contrib import messages  # type: ignore
		messages.error(request, "You do not have permission to view this page.")  # type: ignore
		return redirect("index")  # type: ignore
	return render(request, "documents/analytics.html")  # type: ignore
