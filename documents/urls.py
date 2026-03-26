# pyre-ignore-all-errors
from django.urls import path  # type: ignore
from django.http import JsonResponse  # type: ignore
import os  # type: ignore

from . import views  # type: ignore
from . import auth_views  # type: ignore


def debug_check(request):  # type: ignore
    """Diagnostic endpoint to check server health."""
    import django  # type: ignore
    from django.conf import settings  # type: ignore
    checks = {
        "django_version": django.VERSION,  # type: ignore
        "debug": settings.DEBUG,  # type: ignore
        "storage_backend": str(settings.STORAGES.get("default", {}).get("BACKEND", "default")) if hasattr(settings, "STORAGES") else "django.core.files.storage.FileSystemStorage",  # type: ignore
        "supabase_storage_url_set": bool(os.getenv("SUPABASE_STORAGE_URL")),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "pinecone_key_set": bool(os.getenv("PINECONE_API_KEY")),
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "cache_backend": settings.CACHES.get("default", {}).get("BACKEND", "unknown"),  # type: ignore
        "media_root": str(settings.MEDIA_ROOT),  # type: ignore
    }
    # Test cache
    try:
        from django.core.cache import cache  # type: ignore
        cache.set("_test", "ok", 10)  # type: ignore
        checks["cache_works"] = cache.get("_test") == "ok"  # type: ignore
    except Exception as e:
        checks["cache_error"] = str(e)
    return JsonResponse(checks)  # type: ignore


urlpatterns = [
    # Auth routes
    path("login/", auth_views.login_view, name="login"),
    path("register/", auth_views.register_view, name="register"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("auth/google/callback/", auth_views.google_callback_view, name="google_callback"),
    # App routes
    path("", views.index, name="index"),
    path("api/docs/", views.api_docs, name="api_docs"),
    path("api/sessions/", views.list_sessions, name="list_sessions"),
    path("api/sessions/create/", views.create_session, name="create_session"),
    path("api/sessions/<int:session_id>/", views.get_session, name="get_session"),
    path("api/sessions/<int:session_id>/delete/", views.delete_session, name="delete_session"),
    path("api/sessions/<int:session_id>/export/", views.export_chat, name="export_chat"),
    path("api/upload/", views.upload_document, name="upload_document"),
    path("api/ask/", views.ask_question, name="ask_question"),
    path("api/ask/stream/", views.ask_question_stream, name="ask_question_stream"),
    path("api/documents/", views.list_documents, name="list_documents"),
    path("api/documents/<int:document_id>/delete/", views.delete_document, name="delete_document"),
    path("api/documents/<int:document_id>/preview/", views.preview_document, name="preview_document"),
    path("api/models/", views.list_models, name="list_models"),
    path("api/search/", views.search_sessions, name="search_sessions"),
    path("api/analytics/", views.analytics_dashboard, name="analytics"),
    path("analytics/", views.analytics_page, name="analytics_page"),
    path("api/debug/", debug_check, name="debug_check"),
]
