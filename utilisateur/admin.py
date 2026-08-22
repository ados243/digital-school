from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from utilisateur.models import (
    Utilisateur,
    Conversation,
    MessageEchange,
    CommunicationDirection,
    CommunicationLecture,
    JournalAcces,
    SessionConnexion,
)


class UtilisateurCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = (
            "username",
            "prenom",
            "last_name",
            "email",
            "role",
            "ecole",
            "telephone",
            "eleve",
            "tuteur",
        )


class UtilisateurChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Utilisateur
        fields = "__all__"


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    form = UtilisateurChangeForm
    add_form = UtilisateurCreationForm
    list_display = (
        "username",
        "prenom",
        "last_name",
        "role",
        "ecole",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("role", "ecole", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "prenom", "last_name", "email")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Informations personnelles"),
            {"fields": ("prenom", "last_name", "email", "telephone", "avatar")},
        ),
        (
            _("Profil Digital School"),
            {"fields": ("role", "ecole", "eleve", "tuteur")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Dates importantes"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "prenom",
                    "last_name",
                    "email",
                    "role",
                    "ecole",
                    "telephone",
                    "eleve",
                    "tuteur",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


class MessageEchangeInline(admin.TabularInline):
    model = MessageEchange
    extra = 0
    readonly_fields = ("auteur", "contenu", "created_at", "lu_at")
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("sujet", "classe", "parent", "enseignant", "last_message_at", "ecole")
    list_filter = ("ecole", "classe", "annee_scolaire")
    search_fields = ("sujet", "inscription__eleve__nom", "inscription__eleve__prenom")
    inlines = [MessageEchangeInline]


@admin.register(MessageEchange)
class MessageEchangeAdmin(admin.ModelAdmin):
    list_display = ("conversation", "auteur", "created_at", "lu_at")
    list_filter = ("created_at",)
    search_fields = ("contenu", "auteur__prenom", "auteur__username")


class CommunicationLectureInline(admin.TabularInline):
    model = CommunicationLecture
    extra = 0
    readonly_fields = ("parent", "lu_at")
    can_delete = False


@admin.register(CommunicationDirection)
class CommunicationDirectionAdmin(admin.ModelAdmin):
    list_display = ("sujet", "cible_type", "ecole", "auteur", "created_at")
    list_filter = ("cible_type", "ecole", "created_at")
    search_fields = ("sujet", "contenu")
    inlines = [CommunicationLectureInline]


@admin.register(CommunicationLecture)
class CommunicationLectureAdmin(admin.ModelAdmin):
    list_display = ("communication", "parent", "lu_at")
    list_filter = ("lu_at",)


@admin.register(JournalAcces)
class JournalAccesAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "utilisateur", "ressource", "identifiant", "ip")
    list_filter = ("action", "created_at")
    search_fields = ("utilisateur__username", "identifiant", "ip")
    readonly_fields = (
        "utilisateur", "action", "ressource", "identifiant", "ecole",
        "ip", "user_agent", "extra", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SessionConnexion)
class SessionConnexionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "utilisateur",
        "ip",
        "mfa",
        "last_seen",
        "ended_at",
        "revoquee",
    )
    list_filter = ("revoquee", "mfa", "created_at")
    search_fields = ("utilisateur__username", "ip", "cle_session")
    readonly_fields = (
        "utilisateur",
        "cle_session",
        "ip",
        "user_agent",
        "mfa",
        "created_at",
        "last_seen",
        "ended_at",
        "revoquee",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
