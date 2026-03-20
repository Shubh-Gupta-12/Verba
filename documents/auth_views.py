import logging
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import render, redirect

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
	return render(request, "documents/auth/login.html", {"form": form})


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
