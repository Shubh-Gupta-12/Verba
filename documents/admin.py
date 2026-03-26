# pyre-ignore-all-errors
from django.contrib import admin  # type: ignore

from .models import ChatSession, Document, DocumentChunk, ChatMessage  # type: ignore


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at")
    search_fields = ("title",)
    list_filter = ("created_at",)
    ordering = ("-updated_at",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "session", "status", "uploaded_at")
    list_filter = ("status", "uploaded_at")
    search_fields = ("original_name",)
    ordering = ("-uploaded_at",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "created_at")
    list_filter = ("created_at",)
    search_fields = ("content",)
    raw_id_fields = ("document",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("role", "session", "content_preview", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content",)
    ordering = ("-created_at",)

    @admin.display(description="Content")
    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
