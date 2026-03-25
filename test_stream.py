import requests
import time

s = requests.Session()
# Fetch index to get CSRF token
r = s.get("http://localhost:8000/")
csrf = r.cookies.get("csrftoken", "")

# Login first
login_data = {"username": "shubh", "password": "password123", "csrfmiddlewaretoken": csrf}
r_login = s.post("http://localhost:8000/login/", data=login_data, headers={"Referer": "http://localhost:8000/login/"})

# Ask question stream
headers = {"X-CSRFToken": csrf, "Content-Type": "application/json", "Referer": "http://localhost:8000/"}
r_ask = s.post("http://localhost:8000/api/ask/stream/", json={"question": "hello", "session_id": None}, headers=headers)
print(f"Status: {r_ask.status_code}")
print(r_ask.text)
