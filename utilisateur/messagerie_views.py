"""Messagerie parent ↔ professeur titulaire (représentant de l'école)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Conversation, MessageEchange


def _personnel_connecte(user):
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).select_related('ecole').first()


def _inscription_courante(eleve):
    from inscription.models import Annee_Scolaire, Inscription

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    qs = (
        Inscription.objects.filter(eleve=eleve)
        .select_related('classe', 'classe__titulaire', 'classe__titulaire__utilisateur', 'annee_s')
        .order_by('-date')
    )
    if annee:
        courante = qs.filter(annee_s=annee).first()
        if courante:
            return courante
    return qs.first()


def _titulaire_utilisateur(inscription):
    """Compte Utilisateur du titulaire de la classe, s'il existe."""
    if not inscription or not inscription.classe_id:
        return None
    titulaire = inscription.classe.titulaire
    if not titulaire:
        return None
    return titulaire.utilisateur


def _parent_utilisateur_pour_inscription(inscription):
    tuteur = inscription.eleve.titeur
    return getattr(tuteur, 'compte_utilisateur', None)


def _conversations_visibles(user):
    qs = Conversation.objects.select_related(
        'inscription__eleve',
        'classe',
        'annee_scolaire',
        'parent',
        'enseignant',
        'ecole',
    )
    if user.is_parent:
        return qs.filter(parent=user)
    if user.is_professeur:
        return qs.filter(enseignant=user)
    return qs.none()


def _annoter_non_lus(qs, user):
    return qs.annotate(
        non_lus=Count(
            'messages',
            filter=Q(messages__lu_at__isnull=True) & ~Q(messages__auteur=user),
        )
    )


def _marquer_lus(conversation, user):
    MessageEchange.objects.filter(
        conversation=conversation,
        lu_at__isnull=True,
    ).exclude(auteur=user).update(lu_at=timezone.now())


def _peut_acceder(user, conversation):
    if user.is_parent:
        return conversation.parent_id == user.id
    if user.is_professeur:
        return conversation.enseignant_id == user.id
    return False


@login_required
def messagerie_inbox(request):
    """Boîte de réception parent ou titulaire."""
    if not (request.user.is_parent or request.user.is_professeur):
        return redirect('utilisateur:portail')

    conversations = _annoter_non_lus(
        _conversations_visibles(request.user),
        request.user,
    ).prefetch_related(
        Prefetch(
            'messages',
            queryset=MessageEchange.objects.order_by('-created_at'),
            to_attr='_last_msgs',
        )
    )

    rows = []
    for conv in conversations:
        dernier = conv._last_msgs[0] if getattr(conv, '_last_msgs', None) else None
        rows.append({
            'conversation': conv,
            'dernier': dernier,
            'non_lus': conv.non_lus,
        })

    return render(request, 'utilisateur/messagerie_inbox.html', {
        'rows': rows,
        'total_non_lus': sum(r['non_lus'] for r in rows),
        'est_parent': request.user.is_parent,
        'est_enseignant': request.user.is_professeur,
    })


@login_required
def messagerie_detail(request, pk):
    """Lecture / réponse dans une conversation."""
    if not (request.user.is_parent or request.user.is_professeur):
        return redirect('utilisateur:portail')

    conversation = get_object_or_404(
        Conversation.objects.select_related(
            'inscription__eleve',
            'classe',
            'annee_scolaire',
            'parent',
            'enseignant',
            'ecole',
            'classe__titulaire',
        ),
        pk=pk,
    )
    if not _peut_acceder(request.user, conversation):
        messages.error(request, "Vous n'avez pas accès à cette conversation.")
        return redirect('utilisateur:messagerie_inbox')

    if request.method == 'POST':
        contenu = (request.POST.get('contenu') or '').strip()
        if not contenu:
            messages.error(request, "Le message ne peut pas être vide.")
        else:
            MessageEchange.objects.create(
                conversation=conversation,
                auteur=request.user,
                contenu=contenu,
            )
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=['last_message_at'])
            messages.success(request, "Message envoyé.")
            return redirect('utilisateur:messagerie_detail', pk=conversation.pk)

    _marquer_lus(conversation, request.user)
    msgs = conversation.messages.select_related('auteur').all()

    interlocuteur = (
        conversation.enseignant if request.user.is_parent else conversation.parent
    )

    return render(request, 'utilisateur/messagerie_detail.html', {
        'conversation': conversation,
        'msgs': msgs,
        'interlocuteur': interlocuteur,
        'eleve': conversation.eleve,
        'est_parent': request.user.is_parent,
        'est_enseignant': request.user.is_professeur,
    })


@login_required
def messagerie_nouveau_parent(request, eleve_pk):
    """Le parent contacte le titulaire au sujet d'un enfant."""
    if not request.user.is_parent or not request.user.tuteur_id:
        return redirect('utilisateur:portail')

    from inscription.models import Eleve

    eleve = get_object_or_404(
        Eleve.objects.select_related('ecole', 'titeur'),
        pk=eleve_pk,
        titeur=request.user.tuteur,
    )
    inscription = _inscription_courante(eleve)
    if not inscription:
        messages.warning(request, "Aucune inscription en cours pour cet enfant.")
        return redirect('utilisateur:parent_enfant', pk=eleve.pk)

    enseignant_user = _titulaire_utilisateur(inscription)
    if not enseignant_user:
        messages.warning(
            request,
            "Aucun professeur titulaire n'a encore de compte pour cette classe. "
            "Contactez l'administration de l'école.",
        )
        return redirect('utilisateur:parent_enfant', pk=eleve.pk)

    if request.method == 'POST':
        sujet = (request.POST.get('sujet') or '').strip()
        contenu = (request.POST.get('contenu') or '').strip()
        if not sujet or not contenu:
            messages.error(request, "Indiquez un sujet et un message.")
        else:
            conv = Conversation.objects.create(
                ecole=eleve.ecole,
                inscription=inscription,
                classe=inscription.classe,
                annee_scolaire=inscription.annee_s,
                sujet=sujet[:200],
                parent=request.user,
                enseignant=enseignant_user,
                cree_par=request.user,
            )
            MessageEchange.objects.create(
                conversation=conv,
                auteur=request.user,
                contenu=contenu,
            )
            messages.success(request, "Message envoyé au professeur titulaire.")
            return redirect('utilisateur:messagerie_detail', pk=conv.pk)

    return render(request, 'utilisateur/messagerie_nouveau.html', {
        'eleve': eleve,
        'inscription': inscription,
        'titulaire': inscription.classe.titulaire,
        'est_parent': True,
        'mode': 'parent',
    })


@login_required
def messagerie_nouveau_enseignant(request, classe_pk, inscription_pk):
    """Le titulaire contacte le parent d'un élève de sa classe."""
    if not request.user.is_professeur:
        return redirect('utilisateur:portail')

    from inscription.models import Classe, Inscription

    personnel = _personnel_connecte(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('titulaire'),
        pk=classe_pk,
        ecole=personnel.ecole,
        titulaire=personnel,
    )
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'eleve__titeur', 'annee_s', 'classe'),
        pk=inscription_pk,
        classe=classe,
    )

    parent_user = _parent_utilisateur_pour_inscription(inscription)
    if not parent_user:
        messages.warning(
            request,
            "Le parent / tuteur de cet élève n'a pas encore de compte. "
            "Invitez-le à créer un compte avec son matricule tuteur.",
        )
        return redirect('utilisateur:enseignant_classe', pk=classe.pk)

    if request.method == 'POST':
        sujet = (request.POST.get('sujet') or '').strip()
        contenu = (request.POST.get('contenu') or '').strip()
        if not sujet or not contenu:
            messages.error(request, "Indiquez un sujet et un message.")
        else:
            conv = Conversation.objects.create(
                ecole=personnel.ecole,
                inscription=inscription,
                classe=classe,
                annee_scolaire=inscription.annee_s,
                sujet=sujet[:200],
                parent=parent_user,
                enseignant=request.user,
                cree_par=request.user,
            )
            MessageEchange.objects.create(
                conversation=conv,
                auteur=request.user,
                contenu=contenu,
            )
            messages.success(request, "Message envoyé au parent.")
            return redirect('utilisateur:messagerie_detail', pk=conv.pk)

    return render(request, 'utilisateur/messagerie_nouveau.html', {
        'eleve': inscription.eleve,
        'inscription': inscription,
        'classe': classe,
        'parent_user': parent_user,
        'est_enseignant': True,
        'mode': 'enseignant',
    })
