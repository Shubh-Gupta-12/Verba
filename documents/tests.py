# pyre-ignore-all-errors
from django.test import TestCase, Client  # type: ignore
from django.urls import reverse  # type: ignore

from .models import ChatSession, Document, DocumentChunk, ChatMessage  # type: ignore


class ModelTests(TestCase):
    """Test model creation and string representations."""

    def test_create_chat_session(self):
        session = ChatSession.objects.create(title="Test Session")
        self.assertEqual(str(session), f"Test Session ({session.created_at.strftime('%Y-%m-%d %H:%M')})")
        self.assertEqual(session.title, "Test Session")

    def test_create_document(self):
        doc = Document.objects.create(
            original_name="test.pdf",
            status=Document.STATUS_PROCESSING
        )
        self.assertEqual(str(doc), "test.pdf (processing)")
        self.assertEqual(doc.status, "processing")

    def test_create_document_chunk(self):
        doc = Document.objects.create(original_name="test.pdf")
        chunk = DocumentChunk.objects.create(
            document=doc,
            chunk_index=0,
            content="This is a test chunk"
        )
        self.assertEqual(str(chunk), f"{doc.id}-0")

    def test_create_chat_message(self):
        msg = ChatMessage.objects.create(
            role=ChatMessage.ROLE_USER,
            content="Hello, world!"
        )
        self.assertEqual(str(msg), "user: Hello, world!")

    def test_document_status_choices(self):
        doc = Document.objects.create(
            original_name="test.pdf",
            status=Document.STATUS_READY
        )
        self.assertEqual(doc.status, "ready")

        doc.status = Document.STATUS_FAILED
        doc.error_message = "Something went wrong"
        doc.save()
        doc.refresh_from_db()
        self.assertEqual(doc.status, "failed")

    def test_chat_session_ordering(self):
        s1 = ChatSession.objects.create(title="Session 1")
        s2 = ChatSession.objects.create(title="Session 2")
        sessions = list(ChatSession.objects.all())
        self.assertEqual(sessions[0], s2)  # Most recent first

    def test_chat_message_ordering(self):
        session = ChatSession.objects.create(title="Test")
        m1 = ChatMessage.objects.create(session=session, role="user", content="First")
        m2 = ChatMessage.objects.create(session=session, role="assistant", content="Second")
        messages = list(session.messages.all())
        self.assertEqual(messages[0], m1)
        self.assertEqual(messages[1], m2)


class ViewTests(TestCase):
    """Test API endpoints."""

    def setUp(self):
        self.client = Client()

    def test_index_page(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_create_session(self):
        response = self.client.post(reverse("create_session"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["title"], "New Chat")

    def test_list_sessions(self):
        ChatSession.objects.create(title="Session 1")
        ChatSession.objects.create(title="Session 2")
        response = self.client.get(reverse("list_sessions"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["sessions"]), 2)

    def test_get_session(self):
        session = ChatSession.objects.create(title="Test Session")
        response = self.client.get(reverse("get_session", args=[session.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Test Session")

    def test_get_session_not_found(self):
        response = self.client.get(reverse("get_session", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_delete_session(self):
        session = ChatSession.objects.create(title="To Delete")
        response = self.client.delete(reverse("delete_session", args=[session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ChatSession.objects.filter(id=session.id).exists())

    def test_list_documents_empty(self):
        response = self.client.get(reverse("list_documents"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["documents"]), 0)

    def test_upload_no_file(self):
        response = self.client.post(reverse("upload_document"))
        self.assertEqual(response.status_code, 400)

    def test_ask_question_empty(self):
        response = self.client.post(
            reverse("ask_question"),
            data='{"question": ""}',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_ask_question_invalid_json(self):
        response = self.client.post(
            reverse("ask_question"),
            data="not json",
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_ask_question_too_long(self):
        response = self.client.post(
            reverse("ask_question"),
            data='{"question": "' + 'a' * 2001 + '"}',
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
