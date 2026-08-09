from django.contrib import admin
from utilisateur.models import (
    Utilisateur,
    Conversation,
    MessageEchange,
    CommunicationDirection,
    CommunicationLecture,
)


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('username', 'ecole', 'prenom', 'last_name', 'role', 'eleve', 'tuteur', 'is_active')
    list_filter = ('role', 'ecole', 'is_active')
    search_fields = ('username', 'prenom', 'last_name', 'email')


class MessageEchangeInline(admin.TabularInline):
    model = MessageEchange
    extra = 0
    readonly_fields = ('auteur', 'contenu', 'created_at', 'lu_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'classe', 'parent', 'enseignant', 'last_message_at', 'ecole')
    list_filter = ('ecole', 'classe', 'annee_scolaire')
    search_fields = ('sujet', 'inscription__eleve__nom', 'inscription__eleve__prenom')
    inlines = [MessageEchangeInline]


@admin.register(MessageEchange)
class MessageEchangeAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'auteur', 'created_at', 'lu_at')
    list_filter = ('created_at',)
    search_fields = ('contenu', 'auteur__prenom', 'auteur__username')


class CommunicationLectureInline(admin.TabularInline):
    model = CommunicationLecture
    extra = 0
    readonly_fields = ('parent', 'lu_at')
    can_delete = False


@admin.register(CommunicationDirection)
class CommunicationDirectionAdmin(admin.ModelAdmin):
    list_display = ('sujet', 'cible_type', 'ecole', 'auteur', 'created_at')
    list_filter = ('cible_type', 'ecole', 'created_at')
    search_fields = ('sujet', 'contenu')
    inlines = [CommunicationLectureInline]


@admin.register(CommunicationLecture)
class CommunicationLectureAdmin(admin.ModelAdmin):
    list_display = ('communication', 'parent', 'lu_at')
    list_filter = ('lu_at',)
