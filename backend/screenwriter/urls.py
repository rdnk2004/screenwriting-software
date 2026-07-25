from django.http import JsonResponse
from django.contrib import admin
from django.urls import path, include

def api_root(request):
    return JsonResponse({
        "name": "Screenwriter API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "admin": "/admin/",
            "api_root": "/api/",
            "scripts": "/api/scripts/",
            "characters": "/api/characters/",
            "relationships": "/api/relationships/",
            "beats": "/api/beats/",
        }
    })

urlpatterns = [
    path("", api_root, name="root"),
    path("admin/", admin.site.urls),
    path("api/", include("scripts.urls")),
]

