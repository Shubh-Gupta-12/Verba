from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/sessions/", views.list_sessions, name="list_sessions"),
    path("api/sessions/create/", views.create_session, name="create_session"),
    path("api/sessions/<int:session_id>/", views.get_session, name="get_session"),
    path("api/sessions/<int:session_id>/delete/", views.delete_session, name="delete_session"),
    path("api/upload/", views.upload_document, name="upload_document"),
    path("api/ask/", views.ask_question, name="ask_question"),
    path("api/documents/", views.list_documents, name="list_documents"),
    path("api/documents/<int:document_id>/delete/", views.delete_document, name="delete_document"),
]
