from django.contrib import admin
from .models import (
    Matiere, AffectationEnseignement, DivisionAnnee, PeriodeBulletin, BulletinEleve,
    TravailCote, NoteEleve, PresenceClasse, PresenceEleve, CoursEnLigne, ChapitreCours,
    LeconEnLigne, ProgressionLecon, CoursEnDirect, QuestionCoursDirect,
)


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ('code', 'libelle', 'coefficient', 'maxima_periode', 'section', 'enserignant', 'ecole')
    list_filter = ('section', 'ecole')
    search_fields = ('code', 'libelle')
    autocomplete_fields = ('enserignant', 'section', 'ecole')


@admin.register(AffectationEnseignement)
class AffectationEnseignementAdmin(admin.ModelAdmin):
    list_display = ('classe', 'matiere', 'enseignant', 'ecole')
    list_filter = ('ecole', 'classe', 'matiere')
    search_fields = (
        'classe__classe', 'matiere__libelle',
        'enseignant__nom', 'enseignant__prenom', 'enseignant__matricule',
    )
    autocomplete_fields = ('classe', 'matiere', 'enseignant', 'ecole')


class LeconEnLigneInline(admin.TabularInline):
    model = LeconEnLigne
    extra = 0
    fields = ('ordre', 'titre', 'type_contenu', 'duree_minutes', 'publie', 'video')
    fk_name = 'chapitre'


class ChapitreCoursInline(admin.StackedInline):
    model = ChapitreCours
    extra = 0
    fields = ('ordre', 'titre', 'publie', 'video', 'image')
    show_change_link = True


@admin.register(CoursEnLigne)
class CoursEnLigneAdmin(admin.ModelAdmin):
    list_display = (
        'titre', 'matiere', 'classe', 'niveau', 'enseignant',
        'publie', 'annee_scolaire', 'ecole',
    )
    list_filter = ('publie', 'niveau', 'ecole', 'classe', 'matiere')
    search_fields = ('titre', 'sous_titre', 'matiere__libelle', 'classe__classe')
    autocomplete_fields = ('classe', 'matiere', 'enseignant', 'annee_scolaire', 'ecole')
    inlines = [ChapitreCoursInline]


@admin.register(ChapitreCours)
class ChapitreCoursAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'ordre', 'publie')
    list_filter = ('publie', 'cours__ecole')
    search_fields = ('titre', 'cours__titre')
    inlines = [LeconEnLigneInline]


@admin.register(LeconEnLigne)
class LeconEnLigneAdmin(admin.ModelAdmin):
    list_display = ('titre', 'chapitre', 'cours', 'type_contenu', 'ordre', 'duree_minutes', 'publie')
    list_filter = ('publie', 'type_contenu', 'cours__ecole')
    search_fields = ('titre', 'cours__titre', 'chapitre__titre')


@admin.register(ProgressionLecon)
class ProgressionLeconAdmin(admin.ModelAdmin):
    list_display = ('inscription', 'lecon', 'vue', 'terminee', 'vue_at')
    list_filter = ('terminee', 'vue')


@admin.register(CoursEnDirect)
class CoursEnDirectAdmin(admin.ModelAdmin):
    list_display = (
        'titre', 'classe', 'matiere', 'enseignant',
        'date_heure_prevue', 'statut', 'ecole',
    )
    list_filter = ('statut', 'ecole', 'classe', 'matiere')
    search_fields = ('titre', 'matiere__libelle', 'classe__classe')
    autocomplete_fields = ('classe', 'matiere', 'enseignant', 'annee_scolaire', 'ecole')
    readonly_fields = ('jitsi_room_id', 'created_at', 'updated_at')


@admin.register(QuestionCoursDirect)
class QuestionCoursDirectAdmin(admin.ModelAdmin):
    list_display = ('seance', 'auteur_nom', 'statut', 'epinglee', 'created_at')
    list_filter = ('statut', 'epinglee', 'seance__ecole')
    search_fields = ('texte', 'reponse', 'auteur_nom', 'seance__titre')
    autocomplete_fields = ('seance', 'auteur')


class PeriodeBulletinInline(admin.TabularInline):
    model = PeriodeBulletin
    extra = 0
    fields = ('numero', 'libelle', 'date_debut', 'date_fin', 'est_encours')


@admin.register(DivisionAnnee)
class DivisionAnneeAdmin(admin.ModelAdmin):
    list_display = (
        'libelle', 'type_division', 'cycle', 'annee_scolaire',
        'date_debut', 'date_fin', 'est_encours',
    )
    list_filter = ('type_division', 'cycle', 'annee_scolaire', 'est_encours')
    search_fields = ('libelle',)
    list_editable = ('est_encours',)
    inlines = [PeriodeBulletinInline]


@admin.register(PeriodeBulletin)
class PeriodeBulletinAdmin(admin.ModelAdmin):
    list_display = (
        'libelle', 'numero', 'division', 'cycle', 'annee_scolaire',
        'date_debut', 'date_fin', 'est_encours',
    )
    list_filter = ('cycle', 'annee_scolaire', 'division__type_division', 'est_encours')
    search_fields = ('libelle',)
    list_editable = ('est_encours',)


@admin.register(BulletinEleve)
class BulletinEleveAdmin(admin.ModelAdmin):
    list_display = (
        'inscription', 'pourcentage', 'total_obtenus', 'total_maxima',
        'ecole', 'updated_at',
    )
    list_filter = ('ecole', 'updated_at')
    search_fields = (
        'inscription__eleve__nom', 'inscription__eleve__prenom',
        'inscription__eleve__matricule',
    )
    readonly_fields = ('snapshot', 'created_at', 'updated_at')


class NoteEleveInline(admin.TabularInline):
    model = NoteEleve
    extra = 0
    autocomplete_fields = ('inscription',)
    readonly_fields = ('note', 'absent')

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TravailCote)
class TravailCoteAdmin(admin.ModelAdmin):
    list_display = (
        'type_travail', 'role_bulletin', 'titre', 'matiere', 'classe',
        'periode', 'division', 'annee_scolaire', 'date_travail', 'bareme', 'coefficient', 'ecole',
    )
    list_filter = (
        'role_bulletin', 'type_travail', 'classe', 'matiere', 'periode',
        'division', 'annee_scolaire', 'ecole',
    )
    search_fields = ('titre', 'matiere__libelle', 'classe__classe')
    inlines = [NoteEleveInline]


@admin.register(NoteEleve)
class NoteEleveAdmin(admin.ModelAdmin):
    list_display = ('travail', 'inscription', 'note', 'absent')
    list_filter = ('travail__type_travail', 'absent')
    search_fields = ('inscription__eleve__nom', 'inscription__eleve__prenom')
    readonly_fields = ('travail', 'inscription', 'note', 'absent')

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PresenceEleveInline(admin.TabularInline):
    model = PresenceEleve
    extra = 0
    autocomplete_fields = ('inscription',)


@admin.register(PresenceClasse)
class PresenceClasseAdmin(admin.ModelAdmin):
    list_display = ('classe', 'date', 'annee_scolaire', 'saisi_par', 'ecole')
    list_filter = ('date', 'classe', 'annee_scolaire', 'ecole')
    search_fields = ('classe__classe',)
    inlines = [PresenceEleveInline]


@admin.register(PresenceEleve)
class PresenceEleveAdmin(admin.ModelAdmin):
    list_display = ('presence_classe', 'inscription', 'statut')
    list_filter = ('statut', 'presence_classe__date')
    search_fields = ('inscription__eleve__nom', 'inscription__eleve__prenom')
