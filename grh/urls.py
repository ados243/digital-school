from django.urls import path
from . import views

app_name = 'grh'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('generer-demo/', views.generer_donnees_demo, name='generer_demo'),
    
    # Personnel
    path('personnel/', views.personnel_list, name='personnel_list'),
    path('personnel/nouveau/', views.personnel_create, name='personnel_create'),
    path('personnel/<int:pk>/modifier/', views.personnel_update, name='personnel_update'),
    path('personnel/<int:pk>/supprimer/', views.personnel_delete, name='personnel_delete'),
    
    # Contrats
    path('contrats/', views.contrat_list, name='contrat_list'),
    path('contrats/nouveau/', views.contrat_create, name='contrat_create'),
    path('contrats/<int:pk>/modifier/', views.contrat_update, name='contrat_update'),
    
    # Congés
    path('conges/', views.conge_list, name='conge_list'),
    path('conges/demande/', views.conge_create, name='conge_create'),
    path('conges/<int:pk>/approuver/', views.conge_approve, name='conge_approve'),
    path('conges/<int:pk>/rejeter/', views.conge_reject, name='conge_reject'),
    
    # Présences
    path('presences/', views.presence_list, name='presence_list'),
    path('presences/pointer/', views.presence_record, name='presence_record'),
    
    # Paie
    path('paies/', views.paie_list, name='paie_list'),
    path('paies/generer/', views.paie_generate, name='paie_generate'),
    path('paies/<int:pk>/', views.paie_detail, name='paie_detail'),
    path('paies/<int:pk>/payer/', views.paie_pay, name='paie_pay'),
]
