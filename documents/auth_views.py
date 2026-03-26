# pyre-ignore-all-errors
import json
import logging
from django.conf import settings  # type: ignore
from django.contrib.auth import login, logout, authenticate  # type: ignore
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  # type: ignore
from django.contrib.auth.models import User  # type: ignore
from django.http import JsonResponse  # type: ignore
from django.shortcuts import render, redirect  # type: ignore
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from django.views.decorators.http import require_http_methods  # type: ignore

logger = logging.getLogger(__name__)


def login_view(request):
	if request.user.is_authenticated:
		return redirect("index")
	if request.method == "POST":
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			user = form.get_user()
			login(request, user)
			logger.info(f"User logged in: {user.username}")
			return redirect("index")
	else:
		form = AuthenticationForm()
	return render(request, "documents/auth/login.html", {
		"form": form,
		"SUPABASE_URL": getattr(settings, 'SUPABASE_URL', ''),
		"SUPABASE_ANON_KEY": getattr(settings, 'SUPABASE_ANON_KEY', ''),
	})


def register_view(request):
	if request.user.is_authenticated:
		return redirect("index")
	if request.method == "POST":
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			logger.info(f"New user registered: {user.username}")
			return redirect("index")
	else:
		form = UserCreationForm()
	return render(request, "documents/auth/register.html", {"form": form})


def logout_view(request):
	logout(request)
	return redirect("login")


@csrf_exempt
@require_http_methods(["GET", "POST"])
def google_callback_view(request):
	"""Handle Supabase Google OAuth callback."""
	if request.method == "GET":
		# Render the callback page that processes Supabase's URL fragment
		return render(request, "documents/auth/google_callback.html", {
			"SUPABASE_URL": getattr(settings, 'SUPABASE_URL', ''),
			"SUPABASE_ANON_KEY": getattr(settings, 'SUPABASE_ANON_KEY', ''),
		})

	# POST: Frontend sends user info after Supabase auth
	try:
		data = json.loads(request.body)
	except json.JSONDecodeError:
		return JsonResponse({"error": "Invalid JSON"}, status=400)

	email = data.get("email", "").strip()
	full_name = data.get("full_name", "").strip()

	if not email:
		return JsonResponse({"error": "Email is required"}, status=400)

	# Create or get the Django user based on email
	username = email.split("@")[0]  # Use email prefix as username
	user, created = User.objects.get_or_create(
		email=email,
		defaults={
			"username": username,
			"first_name": full_name.split(" ")[0] if full_name else "",
			"last_name": " ".join(full_name.split(" ")[1:]) if full_name else "",
		}
	)

	if created:
		user.set_unusable_password()  # No password for OAuth users
		user.save()
		logger.info(f"New Google user created: {email}")
	else:
		logger.info(f"Existing Google user logged in: {email}")

	# Log the user in with Django's session auth
	login(request, user)
	return JsonResponse({"status": "ok"})

