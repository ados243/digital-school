from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # TypeFrais
    path('type-frais/', views.type_frais_list, name='type_frais_list'),
    path('type-frais/create/', views.type_frais_create, name='type_frais_create'),
    path('type-frais/<int:pk>/update/', views.type_frais_update, name='type_frais_update'),
    path('type-frais/<int:pk>/delete/', views.type_frais_delete, name='type_frais_delete'),

    # Frais Scolaires
    path('frais-scolaires/', views.frais_scolaire_list, name='frais_scolaire_list'),
    path('frais-scolaires/create/', views.frais_scolaire_create, name='frais_scolaire_create'),
    path('frais-scolaires/<int:pk>/update/', views.frais_scolaire_update, name='frais_scolaire_update'),
    path('frais-scolaires/<int:pk>/delete/', views.frais_scolaire_delete, name='frais_scolaire_delete'),

    # Paiements
    path("paiements/", views.paiement_list, name="paiement_list"),
    path("paiements/nouveau/", views.paiement_create, name="paiement_create"),
    path("paiements/demandes-modification/", views.demandes_modification_list, name="demandes_modification_list"),
    path(
        "paiements/demandes-modification/<int:pk>/rejeter/",
        views.demande_modification_rejeter,
        name="demande_modification_rejeter",
    ),
    path(
        "paiements/<int:pk>/demander-modification/",
        views.demande_modification_create,
        name="demande_modification_create",
    ),
    path("paiements/<int:pk>/modifier/", views.paiement_update, name="paiement_update"),
    path("paiements/<int:pk>/supprimer/", views.paiement_delete, name="paiement_delete"),
    path("paiements/<int:pk>/print/", views.paiement_print, name="paiement_print"),
    path("classes/<int:classe_id>/paiements/", views.classe_paiements, name="classe_paiements"),
    path("cloture/", views.cloture_caisse, name="cloture_caisse"),
    path("budget/", views.budget_annuel, name="budget_annuel"),

    # Taux de change CDF ↔ USD
    path("taux-change/", views.taux_change_list, name="taux_change_list"),

    # WhatsApp — notifications de paiement
    path("whatsapp/", views.whatsapp_config, name="whatsapp_config"),
    path("whatsapp/test/", views.whatsapp_test, name="whatsapp_test"),
    path("whatsapp/renvoyer/<int:pk>/", views.whatsapp_renvoyer, name="whatsapp_renvoyer"),

    # Salaires / Payer le personnel
    path("salaires/", views.salaires_list, name="salaires_list"),
    path("salaires/<int:pk>/payer/", views.salaire_payer, name="salaire_payer"),
    path("salaires/payer-lot/", views.salaires_payer_lot, name="salaires_payer_lot"),

    # -------------------------
    # HOADA - Comptabilité
    # -------------------------
    path('hoada/comptes/', views.hoada_plan_comptable_list, name='hoada_plan_comptable'),
    path('hoada/comptes/create/', views.hoada_plan_comptable_create, name='hoada_plan_comptable_create'),

    path('hoada/journaux/', views.hoada_journaux_list, name='hoada_journaux_list'),
    path('hoada/journaux/create/', views.hoada_journaux_create, name='hoada_journaux_create'),

    path('hoada/ecritures/', views.hoada_ecritures_list, name='hoada_ecritures_list'),
    path('hoada/ecritures/create/', views.hoada_ecritures_create, name='hoada_ecritures_create'),

    path('hoada/grand-livre/', views.hoada_grand_livre, name='hoada_grand_livre'),
    path('hoada/balance/', views.hoada_balance, name='hoada_balance'),

    # Inscription - Frais d'inscription non payés
    path('inscriptions/non-paye/', views.inscriptions_non_paye, name='inscriptions_non_paye'),

    # Seed finances/paiements
    path('seed/', views.seed_finances, name='seed_finances'),
]





