from django.db import models


class ChatSession(models.Model):
	title = models.CharField(max_length=255, default="New Chat")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self) -> str:
		return f"{self.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class Document(models.Model):
	STATUS_PROCESSING = "processing"
	STATUS_READY = "ready"
	STATUS_FAILED = "failed"

	STATUS_CHOICES = [
		(STATUS_PROCESSING, "Processing"),
		(STATUS_READY, "Ready"),
		(STATUS_FAILED, "Failed"),
	]

	session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="documents", null=True, blank=True)
	file = models.FileField(upload_to="uploads/")
	original_name = models.CharField(max_length=255)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSING)
	error_message = models.TextField(blank=True)

	def __str__(self) -> str:
		return f"{self.original_name} ({self.status})"


class DocumentChunk(models.Model):
	document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
	chunk_index = models.IntegerField()
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ("document", "chunk_index")

	def __str__(self) -> str:
		return f"{self.document_id}-{self.chunk_index}"


class ChatMessage(models.Model):
	ROLE_USER = "user"
	ROLE_ASSISTANT = "assistant"

	ROLE_CHOICES = [
		(ROLE_USER, "User"),
		(ROLE_ASSISTANT, "Assistant"),
	]

	session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
	role = models.CharField(max_length=20, choices=ROLE_CHOICES)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at"]

	def __str__(self) -> str:
		return f"{self.role}: {self.content[:50]}"
