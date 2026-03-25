"""
Patch script to enforce document-only chat and tighten response quality.
Changes:
1. views.py: ask_question + ask_question_stream require at least one ready document in the session
2. rag.py: Tighter system prompt to ONLY answer from document context
3. index.html: Disable Ask button and show placeholder when no docs uploaded
"""

# ===== 1. Patch views.py =====
with open('documents/views.py', 'r', encoding='utf-8') as f:
    views = f.read()

# Add document-required check to ask_question (non-streaming)
old_ask = '''	# Get document IDs for this session only
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))

	# Build conversation history for memory'''

new_ask = '''	# Get document IDs for this session only
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))

	if not document_ids:
		return JsonResponse({"error": "Please upload a document first. You can only ask questions about your uploaded documents."}, status=400)

	# Build conversation history for memory'''

views = views.replace(old_ask, new_ask)

# Add document-required check to ask_question_stream
old_stream = '''	# Get document IDs for this session
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))

	# Build conversation history'''

new_stream = '''	# Get document IDs for this session
	document_ids: List[int] = []
	if session:
		document_ids = list(session.documents.filter(status=Document.STATUS_READY).values_list("id", flat=True))

	if not document_ids:
		return JsonResponse({"error": "Please upload a document first. You can only ask questions about your uploaded documents."}, status=400)

	# Build conversation history'''

views = views.replace(old_stream, new_stream)

with open('documents/views.py', 'w', encoding='utf-8') as f:
    f.write(views)
print("[1/3] views.py patched: document-required enforcement added")


# ===== 2. Patch rag.py: Tighter system prompt =====
with open('documents/rag.py', 'r', encoding='utf-8') as f:
    rag = f.read()

old_prompt = '''    system_prompt = (
        "You are a helpful assistant. Answer strictly from the provided context. "
        "If the context does not contain the answer, say you do not have enough information."
    )'''

new_prompt = '''    system_prompt = (
        "You are Verba, a document Q&A assistant. You MUST answer ONLY using information "
        "found in the provided document context below. Do NOT use any outside knowledge. "
        "If the document context does not contain relevant information to answer the question, "
        "respond with: \\"I could not find the answer in your uploaded documents. "
        "Please try rephrasing your question or upload a document that contains this information.\\""
    )'''

rag = rag.replace(old_prompt, new_prompt)

with open('documents/rag.py', 'w', encoding='utf-8') as f:
    f.write(rag)
print("[2/3] rag.py patched: strict document-only system prompt")


# ===== 3. Patch index.html: Disable Ask when no docs =====
with open('documents/templates/documents/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Add check after renderDocuments to disable/enable question input
old_render_docs_call = '''      renderMessages(data.messages || []);
      renderDocuments(data.documents || []);
      showMainContent(true);'''

new_render_docs_call = '''      renderMessages(data.messages || []);
      renderDocuments(data.documents || []);
      showMainContent(true);

      // Enable/disable chat based on documents
      const hasReadyDocs = data.documents && data.documents.some(d => d.status === 'ready');
      questionInput.disabled = !hasReadyDocs;
      askButton.disabled = !hasReadyDocs;
      if (!hasReadyDocs) {
        questionInput.placeholder = "Upload a document first to start chatting...";
      } else {
        questionInput.placeholder = "Ask a question about your documents...";
      }'''

html = html.replace(old_render_docs_call, new_render_docs_call)

with open('documents/templates/documents/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("[3/3] index.html patched: Ask disabled without documents")

print("\nAll patches applied successfully!")
