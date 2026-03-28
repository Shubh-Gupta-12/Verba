import os
import sys
from pathlib import Path
from dotenv import load_dotenv # type: ignore
load_dotenv()

# We need django settings configured to use rag.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ragsite.settings')
import django # type: ignore
django.setup()

from documents.rag import _extract_pdf_with_gemini # type: ignore

pdf_path = "dummy.pdf"
with open(pdf_path, "wb") as f:
    f.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Helvetica\n>>\nendobj\n5 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 24 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000219 00000 n \n0000000306 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n399\n%%EOF\n")

print("Testing Gemini Vision...")
result = _extract_pdf_with_gemini(Path(pdf_path))
print("Result:")
print(result)
os.remove(pdf_path)
