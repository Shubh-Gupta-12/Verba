from django.urls import path

from . import views
from . import auth_views

urlpatterns = [
    # Auth routes
    path("login/", auth_views.login_view, name="login"),
    path("register/", auth_views.register_view, name="register"),
    path("logout/", auth_views.logout_view, name="logout"),
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
    path("api/models/", views.list_models, name="list_models"),
    path("api/search/", views.search_sessions, name="search_sessions"),
]
