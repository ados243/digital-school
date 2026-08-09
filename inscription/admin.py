from django.contrib import admin
from inscription.models import Section,Ecole,Quartier,Inscription,Eleve,Classe,Annee_Scolaire,Tuteur,Cycle,Commune

@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ('matricule','nom','Post_nom','prenom',
                    'titeur', 'sexe','date_de_naissance', 'nationalite', 'quartier','adresse')
    search_fields = ('nom',)
    list_filter = ('sexe','titeur')

@admin.register(Tuteur)
class Tuteur(admin.ModelAdmin):
    list_display = ('matricule','nom','Post_nom','prenom',
                    'lien_parente', 'telephone','telephone2', 'email')
    search_fields = ('nom',)

@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ('cycle'),
    search_fields = ('cycle',)

@admin.register(Annee_Scolaire)
class Annee_ScolaireAdmin(admin.ModelAdmin):
    list_display = ('anne_scolaire', 'date_debut', 'date_fin', 'est_encoure')
    list_filter = ('est_encoure',)
    search_fields = ('anne_scolaire',)
    ordering = ('-est_encoure', '-anne_scolaire')


@admin.register(Ecole)
class EcoleAdmin(admin.ModelAdmin):
    list_display = ('code_ecole','ecole','type_ecole','quartier','adresse',
                    'telephone1', 'telephone2','email', 'activation')
    search_fields = ('ecole',)
    list_filter = ('quartier','type_ecole')
@admin.register(Commune)
class CommuneAdmine(admin.ModelAdmin):
    list_display = ('commune',)

@admin.register(Quartier)
class QuartierAdmine(admin.ModelAdmin):
    list_display = ('commune', 'quartier')


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('ecole', 'section', 'classe', 'capacite_max',
                    'salle')
    search_fields = ('ecole','classe')
    list_filter = ('ecole', 'classe')

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('cycle','section')
    search_fields = ('cycle',)
    list_filter = ('cycle','section')


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('eleve','classe','annee_s','numero_ins',
                    'frais_inscription', 'date','type_iscription')
    search_fields = ('eleve',)
    list_filter = ('classe',)

