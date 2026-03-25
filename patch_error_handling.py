import sys
import re

with open('documents/views.py', 'r', encoding='utf-8') as f:
    views_content = f.read()

target1 = '''	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")

	question = payload.get("question", "").strip()'''

replacement = '''	except json.JSONDecodeError:
		return HttpResponseBadRequest("Invalid JSON")

	try:
		from .rag import _ensure_api_keys
		_ensure_api_keys()
	except Exception as e:
		return JsonResponse({"error": f"{str(e)}. Please add the required keys to your Render environment variables."}, status=400)

	question = payload.get("question", "").strip()'''

views_content = views_content.replace(target1, replacement)
with open('documents/views.py', 'w', encoding='utf-8') as f:
    f.write(views_content)


with open('documents/templates/documents/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

target2 = '''      try {
        const response = await fetch("/api/ask/stream/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({ question, session_id: currentSessionId }),
        });

        const reader = response.body.getReader();'''

replacement2 = '''      try {
        const response = await fetch("/api/ask/stream/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({ question, session_id: currentSessionId }),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({error: "Server Error"}));
          throw new Error(errData.error || "Server Error");
        }

        const reader = response.body.getReader();'''

target3 = '''      } catch (err) {
        // Fallback to non-streaming
        const response = await fetch("/api/ask/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
          },
          body: JSON.stringify({ question, session_id: currentSessionId }),
        });
        const data = await response.json();
        contentDiv.textContent = data.answer;
      }'''

replacement3 = '''      } catch (err) {
        contentDiv.innerHTML = `<span style="color: #ef4444;">${err.message}</span>`;
      }'''

html_content = html_content.replace(target2, replacement2)
html_content = html_content.replace(target3, replacement3)

with open('documents/templates/documents/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print('Patch completed')
