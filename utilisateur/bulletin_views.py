"""Bulletins scolaires RDC — espace enseignant (titulaire uniquement)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from inscription.models import Annee_Scolaire, Classe, Inscription
from pedagogie.affectations import est_titulaire_classe
from pedagogie.bulletin import actualiser_bulletin, assurer_bulletins_classe


def _personnel(user):
    from grh.models import Personnel
    return Personnel.objects.filter(utilisateur=user).select_related('ecole').first()


@login_required
def bulletin_classe(request, pk):
    """Crée/actualise les bulletins de la classe — réservé au titulaire."""
    if not request.user.is_professeur:
        return redirect('utilisateur:post_login')

    personnel = _personnel(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    classe = get_object_or_404(
        Classe.objects.select_related('section', 'section__cycle', 'ecole', 'titulaire'),
        pk=pk,
        ecole=personnel.ecole,
    )
    if not est_titulaire_classe(personnel, classe):
        messages.error(
            request,
            "Seul le professeur titulaire de la classe peut consulter les bulletins.",
        )
        return redirect('utilisateur:enseignant_dashboard')

    annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    rows = []
    if annee:
        bulletins = assurer_bulletins_classe(classe, annee)
        by_ins = {b.inscription_id: b for b in bulletins}
        inscriptions = (
            Inscription.objects.filter(classe=classe, annee_s=annee)
            .select_related('eleve')
            .order_by('eleve__nom', 'eleve__prenom')
        )
        for ins in inscriptions:
            b = by_ins.get(ins.id) or getattr(ins, 'bulletin', None)
            rows.append({
                'inscription': ins,
                'eleve': ins.eleve,
                'bulletin': b,
                'pourcentage': b.pourcentage if b else None,
                'total_obtenus': b.total_obtenus if b else None,
                'total_maxima': b.total_maxima if b else None,
                'updated_at': b.updated_at if b else None,
            })

    return render(request, 'utilisateur/bulletin_classe.html', {
        'classe': classe,
        'annee_courante': annee,
        'rows': rows,
        'mode': (
            'semestriel' if classe.section.cycle.cycle in ('SECONDAIRE', 'HUMANITE')
            else 'trimestriel'
        ),
    })


@login_required
def bulletin_eleve(request, inscription_pk):
    """Bulletin RDC d'un élève — réservé au titulaire de la classe."""
    if not request.user.is_professeur:
        return redirect('utilisateur:post_login')

    personnel = _personnel(request.user)
    if not personnel:
        messages.warning(request, "Aucune fiche personnel n'est rattachée à votre compte.")
        return redirect('utilisateur:enseignant_dashboard')

    inscription = get_object_or_404(
        Inscription.objects.select_related(
            'eleve', 'classe', 'classe__section', 'classe__section__cycle',
            'classe__ecole', 'classe__titulaire', 'annee_s',
        ),
        pk=inscription_pk,
        classe__ecole=personnel.ecole,
    )
    if not est_titulaire_classe(personnel, inscription.classe):
        messages.error(
            request,
            "Seul le professeur titulaire de la classe peut consulter ce bulletin.",
        )
        return redirect('utilisateur:enseignant_dashboard')

    bulletin_obj, data = actualiser_bulletin(inscription)
    return render(request, 'utilisateur/bulletin_eleve.html', {
        'bulletin': data,
        'bulletin_obj': bulletin_obj,
        'inscription': inscription,
    })
