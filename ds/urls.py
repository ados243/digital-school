"""ds URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

from ds.health import healthz

# Django Admin réservé aux superutilisateurs uniquement
admin.site.has_permission = lambda request: bool(
    getattr(request.user, "is_active", False)
    and getattr(request.user, "is_superuser", False)
)

urlpatterns = [
    path('sante/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('', include('utilisateur.urls')),
    path('grh/', include('grh.urls')),
    path('inscription/', include('inscription.urls')),
    path('finances/', include('finances.urls')),
    path('pedagogie/', include(('pedagogie.urls', 'pedagogie'), namespace='pedagogie')),
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
