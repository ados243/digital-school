from django.contrib import admin
from .models import Personnel, Contrat, Conge, Presence, Paie

@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    list_display = ('matricule', 'nom', 'prenom', 'sexe', 'fonction', 'telephone', 'ecole')
    search_fields = ('nom', 'prenom', 'matricule', 'fonction')
    list_filter = ('sexe', 'fonction', 'ecole')

@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'type_contrat', 'date_debut', 'date_fin', 'salaire_base', 'devise', 'statut')
    list_filter = ('type_contrat', 'statut', 'devise')
    search_fields = ('personnel__nom', 'personnel__prenom')

@admin.register(Conge)
class CongeAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'type_conge', 'date_debut', 'date_fin', 'statut')
    list_filter = ('type_conge', 'statut')
    search_fields = ('personnel__nom', 'personnel__prenom')

@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'date', 'statut', 'heure_arrivee', 'heure_depart')
    list_filter = ('statut', 'date')
    search_fields = ('personnel__nom', 'personnel__prenom')

@admin.register(Paie)
class PaieAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'mois', 'annee', 'salaire_base', 'primes', 'deductions', 'net_a_payer', 'devise', 'statut_paiement')
    list_filter = ('mois', 'annee', 'statut_paiement', 'devise')
    search_fields = ('personnel__nom', 'personnel__prenom')
