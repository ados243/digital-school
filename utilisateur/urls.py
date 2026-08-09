from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from . import messagerie_views
from . import direction_views
from . import travaux_views
from . import bulletin_views
from . import evolution_views
from . import cours_views
from .forms import ConnexionForm
from pedagogie import views as pedagogie_views


app_name = 'utilisateur'

urlpatterns = [
    path('', views.root_redirect, name='root'),
    path(
        'connexion/',
        auth_views.LoginView.as_view(
            template_name='utilisateur/login.html',
            authentication_form=ConnexionForm,
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path(
        'deconnexion/',
        auth_views.LogoutView.as_view(next_page='utilisateur:login'),
        name='logout',
    ),
    path('creer-compte/', views.inscription_view, name='inscription'),
    path('bienvenue/', views.post_login_redirect, name='post_login'),
    path('mon-espace/', views.portail_view, name='portail'),
    path('mon-espace/enfant/<int:pk>/', views.parent_enfant_detail, name='parent_enfant'),
    path('mon-espace/enseignant/', views.enseignant_dashboard, name='enseignant_dashboard'),
    path('mon-espace/enseignant/classe/<int:pk>/', views.enseignant_classe_detail, name='enseignant_classe'),

    # Travaux cotés (espace enseignant)
    path('mon-espace/enseignant/travaux/', travaux_views.travail_list, name='travail_list'),
    path('mon-espace/enseignant/travaux/nouveau/', travaux_views.travail_create, name='travail_create'),
    path('mon-espace/enseignant/travaux/<int:pk>/modifier/', travaux_views.travail_update, name='travail_update'),
    path('mon-espace/enseignant/travaux/<int:pk>/supprimer/', travaux_views.travail_delete, name='travail_delete'),
    path('mon-espace/enseignant/travaux/<int:pk>/notes/', travaux_views.travail_notes, name='travail_notes'),

    # Cours en ligne (espace enseignant)
    path('mon-espace/enseignant/cours/', cours_views.cours_enseignant_list, name='cours_enseignant_list'),
    path('mon-espace/enseignant/cours/nouveau/', cours_views.cours_enseignant_create, name='cours_enseignant_create'),
    path('mon-espace/enseignant/cours/<int:pk>/', cours_views.cours_enseignant_detail, name='cours_enseignant_detail'),
    path('mon-espace/enseignant/cours/<int:pk>/modifier/', cours_views.cours_enseignant_update, name='cours_enseignant_update'),
    path('mon-espace/enseignant/cours/<int:pk>/publier/', cours_views.cours_enseignant_publier, name='cours_enseignant_publier'),
    path('mon-espace/enseignant/cours/<int:pk>/supprimer/', cours_views.cours_enseignant_delete, name='cours_enseignant_delete'),
    path('mon-espace/enseignant/chapitres/<int:pk>/', cours_views.chapitre_enseignant_detail, name='chapitre_enseignant_detail'),
    path('mon-espace/enseignant/chapitres/<int:pk>/modifier/', cours_views.chapitre_enseignant_update, name='chapitre_enseignant_update'),
    path('mon-espace/enseignant/chapitres/<int:pk>/supprimer/', cours_views.chapitre_enseignant_delete, name='chapitre_enseignant_delete'),
    path('mon-espace/enseignant/lecons/<int:pk>/modifier/', cours_views.lecon_enseignant_update, name='lecon_enseignant_update'),
    path('mon-espace/enseignant/lecons/<int:pk>/supprimer/', cours_views.lecon_enseignant_delete, name='lecon_enseignant_delete'),

    # Cours en ligne (espace élève)
    path('mon-espace/etudier/', cours_views.cours_eleve_list, name='cours_eleve_list'),
    path('mon-espace/etudier/cours/<int:pk>/', cours_views.cours_eleve_detail, name='cours_eleve_detail'),
    path('mon-espace/etudier/chapitre/<int:pk>/', cours_views.chapitre_eleve_detail, name='chapitre_eleve_detail'),
    path('mon-espace/etudier/lecon/<int:pk>/', cours_views.lecon_eleve_detail, name='lecon_eleve_detail'),

    # Bulletins scolaires RDC
    path('mon-espace/enseignant/classe/<int:pk>/bulletins/', bulletin_views.bulletin_classe, name='bulletin_classe'),
    path('mon-espace/enseignant/bulletin/<int:inscription_pk>/', bulletin_views.bulletin_eleve, name='bulletin_eleve'),

    # Évolution des élèves (cours du professeur)
    path(
        'mon-espace/enseignant/classe/<int:pk>/evolution/',
        evolution_views.evolution_classe,
        name='evolution_classe',
    ),

    # Présences élèves (espace enseignant)
    path('mon-espace/enseignant/presences/', pedagogie_views.presence_list, name='presence_list'),
    path('mon-espace/enseignant/presences/classe/<int:pk>/', pedagogie_views.presence_classe, name='presence_classe'),
    path('mon-espace/enseignant/presences/classe/<int:pk>/recap/', pedagogie_views.presence_recap, name='presence_recap'),

    # Messagerie parent ↔ titulaire
    path('mon-espace/messages/', messagerie_views.messagerie_inbox, name='messagerie_inbox'),
    path('mon-espace/messages/<int:pk>/', messagerie_views.messagerie_detail, name='messagerie_detail'),
    path(
        'mon-espace/enfant/<int:eleve_pk>/messages/nouveau/',
        messagerie_views.messagerie_nouveau_parent,
        name='messagerie_nouveau_parent',
    ),
    path(
        'mon-espace/enseignant/classe/<int:classe_pk>/contacter/<int:inscription_pk>/',
        messagerie_views.messagerie_nouveau_enseignant,
        name='messagerie_nouveau_enseignant',
    ),

    # Annonces direction → parents (lecture parent)
    path('mon-espace/annonces/', direction_views.parent_annonces_list, name='parent_annonces'),
    path('mon-espace/annonces/<int:pk>/', direction_views.parent_annonce_detail, name='parent_annonce_detail'),

    # Espace direction → parents (staff)
    path('direction/communications/', direction_views.direction_communication_list, name='direction_communication_list'),
    path('direction/communications/nouvelle/', direction_views.direction_communication_create, name='direction_communication_create'),
    path('direction/communications/<int:pk>/', direction_views.direction_communication_detail, name='direction_communication_detail'),
]
