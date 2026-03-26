"""
URL configuration for ragsite project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
import traceback
import sys


def handler500_json(request):
    """Return JSON error for API requests, HTML for normal pages."""
    exc_info = sys.exc_info()
    error_detail = ""
    if exc_info[1]:
        error_detail = f"{exc_info[0].__name__}: {exc_info[1]}"
    
    if request.path.startswith("/api/"):
        return JsonResponse({
            "error": f"Internal server error: {error_detail}",
            "traceback": traceback.format_exception(*exc_info) if exc_info[1] else []
        }, status=500)
    
    from django.views.defaults import server_error
    return server_error(request)


handler500 = 'ragsite.urls.handler500_json'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('', include('documents.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
