"""Calcul du bulletin scolaire selon le modele officiel RDC (MEPST).

Structure humanites / CTEB (semestriel) — meme logique pour trimestres :
  BRANCHES | 1e P. | 2e P. | EXAM. | TOT. | … | T.G. | %

- Colonnes de periode = Travaux journaliers (devoirs, interros, TP…)
- Colonne EXAM. = examen de fin de trimestre / semestre
- TOT. division = TJ(periode A) + TJ(periode B) + EXAM.
- T.G. = somme des TOT. de toutes les divisions
- % = T.G. / maxima generaux × 100

Les notes des travaux sont ramenees au maxima bulletin de la matiere
(maxima_periode pour TJ, 2×maxima_periode pour l'examen).
"""

from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Prefetch

from .models import DivisionAnnee, Matiere, NoteEleve, PeriodeBulletin, TravailCote


ZERO = Decimal("0")
CENT = Decimal("100")


def _q(value, places="0.01"):
    if value is None:
        return None
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _note_sur_maxima(note, bareme, maxima):
    """Convertit une note / bareme vers le maxima du bulletin."""
    if note is None or not bareme or bareme <= 0 or maxima is None:
        return None
    return _q((Decimal(note) / Decimal(bareme)) * Decimal(maxima))


def _moyenne_ponderee(lignes):
    """lignes = [(points_sur_maxima, coefficient), ...]"""
    total_pts = ZERO
    total_coef = ZERO
    for pts, coef in lignes:
        if pts is None:
            continue
        c = Decimal(coef or 1)
        total_pts += pts * c
        total_coef += c
    if total_coef <= 0:
        return None
    return _q(total_pts / total_coef)


def _travaux_notes_eleve(inscription, travaux_qs):
    """Map travail_id -> NoteEleve pour un eleve."""
    return {
        n.travail_id: n
        for n in NoteEleve.objects.filter(
            inscription=inscription,
            travail__in=travaux_qs,
            absent=False,
            note__isnull=False,
        ).select_related("travail")
    }


def score_tj_periode(inscription, matiere, periode, notes_map=None):
    """Points TJ d'une matiere pour une periode (colonne bulletin)."""
    travaux = TravailCote.objects.filter(
        classe=inscription.classe,
        annee_scolaire=inscription.annee_s,
        matiere=matiere,
        role_bulletin="TJ",
        periode=periode,
    )
    if notes_map is None:
        notes_map = _travaux_notes_eleve(inscription, travaux)

    maxima = matiere.maxima_periode
    lignes = []
    for t in travaux:
        n = notes_map.get(t.id)
        if not n:
            continue
        pts = _note_sur_maxima(n.note, t.bareme, maxima)
        lignes.append((pts, t.coefficient))
    return _moyenne_ponderee(lignes), maxima


def score_examen_division(inscription, matiere, division, notes_map=None):
    """Points EXAM. d'une matiere pour un trimestre/semestre."""
    travaux = TravailCote.objects.filter(
        classe=inscription.classe,
        annee_scolaire=inscription.annee_s,
        matiere=matiere,
        role_bulletin="EXAMEN",
        division=division,
    )
    if notes_map is None:
        notes_map = _travaux_notes_eleve(inscription, travaux)

    maxima = matiere.maxima_examen
    lignes = []
    for t in travaux:
        n = notes_map.get(t.id)
        if not n:
            continue
        pts = _note_sur_maxima(n.note, t.bareme, maxima)
        lignes.append((pts, t.coefficient))
    return _moyenne_ponderee(lignes), maxima


def bulletin_inscription(inscription):
    """Construit le bulletin RDC d'un eleve inscrit.

    Retourne un dict pret pour les templates :
    {
      mode, divisions: [{division, periodes, ...}],
      lignes: [{matiere, periodes: {id: {tj, max}}, examens: {id: {exam, max}},
                totaux_division, total_general, maxima_general, pourcentage}],
      totaux_generaux, pourcentage_general
    }
    """
    classe = inscription.classe
    annee = inscription.annee_s
    cycle = classe.section.cycle

    divisions = list(
        DivisionAnnee.objects.filter(annee_scolaire=annee, cycle=cycle)
        .prefetch_related(
            Prefetch("periodes", queryset=PeriodeBulletin.objects.order_by("numero"))
        )
        .order_by("numero")
    )
    periodes = [p for d in divisions for p in d.periodes.all()]
    mode = divisions[0].type_division if divisions else None

    matieres = list(
        Matiere.objects.filter(ecole=classe.ecole, section=classe.section).order_by("libelle")
    )

    travaux = TravailCote.objects.filter(
        classe=classe,
        annee_scolaire=annee,
        matiere__in=matieres,
    )
    notes_map = _travaux_notes_eleve(inscription, travaux)

    lignes = []
    somme_obtenus = ZERO
    somme_maxima = ZERO

    for matiere in matieres:
        blocs = []
        tg = ZERO
        max_tg = ZERO
        has_tg = False

        for division in divisions:
            periodes_cells = []
            tot = ZERO
            max_tot = ZERO
            has_any = False

            for periode in division.periodes.all():
                tj, max_tj = score_tj_periode(
                    inscription, matiere, periode, notes_map=notes_map
                )
                periodes_cells.append({
                    "periode": periode,
                    "points": tj,
                    "maxima": max_tj,
                })
                if tj is not None:
                    tot += tj
                    has_any = True
                max_tot += max_tj or ZERO

            exam, max_ex = score_examen_division(
                inscription, matiere, division, notes_map=notes_map
            )
            if exam is not None:
                tot += exam
                has_any = True
            max_tot += max_ex or ZERO

            blocs.append({
                "division": division,
                "periodes": periodes_cells,
                "examen": exam,
                "maxima_examen": max_ex,
                "total": _q(tot) if has_any else None,
                "maxima_total": max_tot,
            })
            if has_any:
                tg += tot
                has_tg = True
            max_tg += max_tot

        pct = _q((tg / max_tg) * CENT) if max_tg > 0 and has_tg else None
        lignes.append({
            "matiere": matiere,
            "blocs": blocs,
            "total_general": _q(tg) if has_tg else None,
            "maxima_general": max_tg,
            "pourcentage": pct,
        })
        if has_tg:
            somme_obtenus += tg
        somme_maxima += max_tg

    pct_gen = _q((somme_obtenus / somme_maxima) * CENT) if somme_maxima > 0 else None

    return {
        "inscription": inscription,
        "eleve": inscription.eleve,
        "classe": classe,
        "annee": annee,
        "cycle": cycle,
        "mode": mode,
        "divisions": divisions,
        "periodes": periodes,
        "lignes": lignes,
        "total_obtenus": _q(somme_obtenus) if somme_obtenus else ZERO,
        "total_maxima": somme_maxima,
        "pourcentage_general": pct_gen,
    }


def _dec_json(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    return value


def _snapshot_depuis_calcul(data):
    """Version JSON-serialisable du bulletin calcule."""
    divisions = []
    for d in data["divisions"]:
        divisions.append({
            "id": d.id,
            "libelle": d.libelle,
            "type_division": d.type_division,
            "numero": d.numero,
            "periodes": [
                {"id": p.id, "numero": p.numero, "libelle": p.libelle}
                for p in d.periodes.all()
            ],
        })

    lignes = []
    for ligne in data["lignes"]:
        blocs = []
        for bloc in ligne["blocs"]:
            blocs.append({
                "division_id": bloc["division"].id,
                "periodes": [
                    {
                        "periode_id": c["periode"].id,
                        "numero": c["periode"].numero,
                        "points": _dec_json(c["points"]),
                        "maxima": _dec_json(c["maxima"]),
                    }
                    for c in bloc["periodes"]
                ],
                "examen": _dec_json(bloc["examen"]),
                "maxima_examen": _dec_json(bloc["maxima_examen"]),
                "total": _dec_json(bloc["total"]),
                "maxima_total": _dec_json(bloc["maxima_total"]),
            })
        lignes.append({
            "matiere_id": ligne["matiere"].id,
            "matiere": ligne["matiere"].libelle,
            "maxima_periode": _dec_json(ligne["matiere"].maxima_periode),
            "maxima_examen": _dec_json(ligne["matiere"].maxima_examen),
            "blocs": blocs,
            "total_general": _dec_json(ligne["total_general"]),
            "maxima_general": _dec_json(ligne["maxima_general"]),
            "pourcentage": _dec_json(ligne["pourcentage"]),
        })

    return {
        "mode": data["mode"],
        "cycle": data["cycle"].cycle,
        "classe": data["classe"].classe,
        "section": data["classe"].section.section,
        "annee": data["annee"].anne_scolaire,
        "eleve": str(data["eleve"]),
        "divisions": divisions,
        "lignes": lignes,
        "total_obtenus": _dec_json(data["total_obtenus"]),
        "total_maxima": _dec_json(data["total_maxima"]),
        "pourcentage_general": _dec_json(data["pourcentage_general"]),
    }


def obtenir_ou_creer_bulletin(inscription):
    """Garantit qu'un BulletinEleve existe pour l'inscription."""
    from .models import BulletinEleve

    bulletin, _ = BulletinEleve.objects.get_or_create(
        inscription=inscription,
        defaults={
            "ecole": inscription.classe.ecole,
            "total_obtenus": ZERO,
            "total_maxima": ZERO,
        },
    )
    return bulletin


def actualiser_bulletin(inscription):
    """Recalcule et persiste le bulletin d'un eleve."""
    from .models import BulletinEleve

    data = bulletin_inscription(inscription)
    bulletin, _ = BulletinEleve.objects.update_or_create(
        inscription=inscription,
        defaults={
            "ecole": inscription.classe.ecole,
            "total_obtenus": data["total_obtenus"] or ZERO,
            "total_maxima": data["total_maxima"] or ZERO,
            "pourcentage": data["pourcentage_general"],
            "snapshot": _snapshot_depuis_calcul(data),
        },
    )
    return bulletin, data


def actualiser_bulletins_inscriptions(inscriptions):
    """Recalcule les bulletins d'une liste d'inscriptions."""
    resultats = []
    for ins in inscriptions:
        resultats.append(actualiser_bulletin(ins)[0])
    return resultats


def actualiser_bulletins_classe(classe, annee):
    """Recalcule tous les bulletins d'une classe pour une annee."""
    from inscription.models import Inscription

    inscriptions = Inscription.objects.filter(classe=classe, annee_s=annee).select_related(
        "eleve", "classe", "classe__section", "classe__section__cycle", "classe__ecole", "annee_s"
    )
    return actualiser_bulletins_inscriptions(inscriptions)


def assurer_bulletins_classe(classe, annee):
    """Cree les bulletins manquants puis les actualise."""
    from inscription.models import Inscription
    from .models import BulletinEleve

    inscriptions = list(
        Inscription.objects.filter(classe=classe, annee_s=annee).select_related(
            "eleve", "classe", "classe__section", "classe__section__cycle", "classe__ecole", "annee_s"
        )
    )
    existants = set(
        BulletinEleve.objects.filter(inscription__in=inscriptions).values_list(
            "inscription_id", flat=True
        )
    )
    for ins in inscriptions:
        if ins.id not in existants:
            obtenir_ou_creer_bulletin(ins)
    return actualiser_bulletins_inscriptions(inscriptions)
