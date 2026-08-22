from django.urls import path

from . import views
from . import messagerie_views
from . import direction_views
from . import travaux_views
from . import bulletin_views
from . import evolution_views
from . import cours_views
from . import live_views
from . import profil_views
from . import auth_views
from . import ressource_views
from pedagogie import views as pedagogie_views
from pedagogie.video_views import servir_video_cours
from finances.mobile_views import parent_payer_mobile


app_name = 'utilisateur'

urlpatterns = [
    path('', views.root_redirect, name='root'),
    path(
        'politique-confidentialite/',
        views.politique_confidentialite,
        name='politique_confidentialite',
    ),
    path(
        'connexion/',
        auth_views.ConnexionView.as_view(),
        name='login',
    ),
    path('connexion/verification/', auth_views.mfa_view, name='mfa'),
    path('deconnexion/', auth_views.logout_view, name='logout'),
    path('creer-compte/', views.inscription_view, name='inscription'),
    path('verifier-compte/', auth_views.verifier_compte_view, name='verifier_compte'),
    path('bienvenue/', views.post_login_redirect, name='post_login'),

    # Recuperation de mot de passe (code WhatsApp)
    path(
        'mot-de-passe-oublie/',
        auth_views.mot_de_passe_oublie_view,
        name='password_reset',
    ),
    path(
        'mot-de-passe-oublie/code/',
        auth_views.mot_de_passe_oublie_code_view,
        name='password_reset_done',
    ),
    path(
        'reinitialiser-mot-de-passe/',
        auth_views.mot_de_passe_nouveau_view,
        name='password_reset_confirm',
    ),
    path(
        'reinitialiser-mot-de-passe/termine/',
        profil_views.MotDePasseResetCompleteView.as_view(),
        name='password_reset_complete',
    ),

    # Vidéos de cours (stockage local privé — hors /media/)
    path(
        'mon-espace/videos-cours/<path:relative_path>',
        servir_video_cours,
        name='cours_video',
    ),

    # Profil / personnalisation du compte
    path('mon-espace/profil/', profil_views.profil_view, name='profil'),

    path('mon-espace/', views.portail_view, name='portail'),
    path('mon-espace/enfant/<int:pk>/', views.parent_enfant_detail, name='parent_enfant'),
    path(
        'mon-espace/enfant/<int:pk>/payer-mobile/',
        parent_payer_mobile,
        name='parent_payer_mobile',
    ),
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

    # Ressources partagées (enseignant)
    path('mon-espace/enseignant/ressources/', ressource_views.ressource_enseignant_list, name='ressource_enseignant_list'),
    path('mon-espace/enseignant/ressources/nouveau/', ressource_views.ressource_enseignant_create, name='ressource_enseignant_create'),
    path('mon-espace/enseignant/ressources/<int:pk>/modifier/', ressource_views.ressource_enseignant_update, name='ressource_enseignant_update'),
    path('mon-espace/enseignant/ressources/<int:pk>/supprimer/', ressource_views.ressource_enseignant_delete, name='ressource_enseignant_delete'),

    # Cours en ligne (espace élève)
    path('mon-espace/etudier/', cours_views.cours_eleve_list, name='cours_eleve_list'),
    path('mon-espace/etudier/cours/<int:pk>/', cours_views.cours_eleve_detail, name='cours_eleve_detail'),
    path('mon-espace/etudier/chapitre/<int:pk>/', cours_views.chapitre_eleve_detail, name='chapitre_eleve_detail'),
    path('mon-espace/etudier/lecon/<int:pk>/', cours_views.lecon_eleve_detail, name='lecon_eleve_detail'),

    # Ressources partagées (élève)
    path('mon-espace/etudier/ressources/', ressource_views.ressource_eleve_list, name='ressource_eleve_list'),
    path('mon-espace/etudier/ressources/<int:pk>/', ressource_views.ressource_eleve_detail, name='ressource_eleve_detail'),

    # Cours en direct / visioconférence (enseignant)
    path('mon-espace/enseignant/direct/', live_views.direct_enseignant_list, name='direct_enseignant_list'),
    path('mon-espace/enseignant/direct/nouveau/', live_views.direct_enseignant_create, name='direct_enseignant_create'),
    path('mon-espace/enseignant/direct/<int:pk>/modifier/', live_views.direct_enseignant_update, name='direct_enseignant_update'),
    path('mon-espace/enseignant/direct/<int:pk>/salle/', live_views.direct_enseignant_salle, name='direct_enseignant_salle'),
    path(
        'mon-espace/enseignant/direct/<int:pk>/<str:action>/',
        live_views.direct_enseignant_statut,
        name='direct_enseignant_statut',
    ),

    # Cours en direct / visioconférence (élève)
    path('mon-espace/etudier/direct/', live_views.direct_eleve_list, name='direct_eleve_list'),
    path('mon-espace/etudier/direct/<int:pk>/salle/', live_views.direct_eleve_salle, name='direct_eleve_salle'),

    # Questions pendant la visioconférence
    path('mon-espace/direct/<int:pk>/questions/', live_views.direct_questions, name='direct_questions'),
    path('mon-espace/direct/<int:pk>/questions/nouvelle/', live_views.direct_question_create, name='direct_question_create'),
    path(
        'mon-espace/direct/<int:pk>/questions/<int:question_id>/<str:action>/',
        live_views.direct_question_action,
        name='direct_question_action',
    ),

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
