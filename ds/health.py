"""Sonde de santé pour Coolify (proxy + base MySQL)."""
from django.db import connection
from django.http import HttpResponse


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return HttpResponse("ok", content_type="text/plain")
