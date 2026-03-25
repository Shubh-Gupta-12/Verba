import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ragsite.settings")
django.setup()

from documents.rag import _get_pinecone_index
index = _get_pinecone_index()
try:
    index.query(vector=[0.1]*768, top_k=5, filter=None, include_metadata=True)
    print("SUCCESS: filter=None is accepted.")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
