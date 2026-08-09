from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'pedagogie'

# Repartition bulletin RDC : /pedagogie/periodes/
urlpatterns = [
    path('', views.pedagogie_dashboard, name='dashboard'),
    path('matieres/', views.matiere_list, name='matiere_list'),
    path('matiere/nouvelle/', views.matiere_create, name='matiere_create'),
    path('matiere/<int:pk>/modifier/', views.matiere_update, name='matiere_update'),
    path('matiere/<int:pk>/supprimer/', views.matiere_delete, name='matiere_delete'),
    path('periodes/', views.periodes_bulletin, name='periodes_bulletin'),
    path(
        'periodes/division/<int:pk>/encours/',
        views.division_toggle_encours,
        name='division_toggle_encours',
    ),
    path(
        'periodes/periode/<int:pk>/encours/',
        views.periode_toggle_encours,
        name='periode_toggle_encours',
    ),
    path('classe/<int:pk>/enseignants/', views.affectations_classe, name='affectations_classe'),

    # Anciennes URLs travaux → espace enseignant
    path('travaux/', RedirectView.as_view(pattern_name='utilisateur:travail_list', permanent=False)),
    path('travaux/nouveau/', RedirectView.as_view(pattern_name='utilisateur:travail_create', permanent=False)),
    path('travaux/<int:pk>/modifier/', RedirectView.as_view(pattern_name='utilisateur:travail_update', permanent=False)),
    path('travaux/<int:pk>/supprimer/', RedirectView.as_view(pattern_name='utilisateur:travail_delete', permanent=False)),
    path('travaux/<int:pk>/notes/', RedirectView.as_view(pattern_name='utilisateur:travail_notes', permanent=False)),
]
