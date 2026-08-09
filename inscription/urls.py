from django.urls import path
from . import views

app_name = 'inscription'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Eleves
    path('eleves/', views.eleve_list, name='eleve_list'),
    path('eleves/nouveau/', views.eleve_create, name='eleve_create'),
    path('eleves/<int:pk>/modifier/', views.eleve_update, name='eleve_update'),
    path('eleves/<int:pk>/supprimer/', views.eleve_delete, name='eleve_delete'),
    
    # Tuteurs
    path('tuteurs/nouveau/', views.tuteur_create, name='tuteur_create'),
    
    # Inscriptions
    path('inscrire/', views.inscription_create, name='inscription_create'),
    path('inscriptions/', views.inscription_list, name='inscription_list'),
    path('inscriptions/<int:pk>/modifier/', views.inscription_update, name='inscription_update'),
    
    # Classes
    path('classes/', views.classe_list, name='classe_list'),
    path('classes/nouvelle/', views.classe_create, name='classe_create'),
    path('classes/<int:pk>/', views.classe_detail, name='classe_detail'),
    path('classes/<int:pk>/modifier/', views.classe_update, name='classe_update'),
    path('classes/<int:pk>/supprimer/', views.classe_delete, name='classe_delete'),
]
