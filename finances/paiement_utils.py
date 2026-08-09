from decimal import Decimal

from django.db.models import Count, Q, Sum

from .models import CompteComptable, EcritureLigne, Frais_Scolaire, Paiement, TypeFrais
from .tenant import paiements_for_ecole, frais_for_ecole, type_frais_for_ecole


def _decimal(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def convertir_montant(montant, taux, de_devise, vers_devise):
    """
    Convertit un montant entre CDF et USD.
    `taux` = nombre de CDF pour 1 USD.
    """
    montant = _decimal(montant)
    taux = _decimal(taux)
    if taux <= 0:
        raise ValueError("Le taux de change doit être supérieur à zéro.")
    de = (de_devise or "").upper()
    vers = (vers_devise or "").upper()
    if de == vers:
        return montant
    if de == "CDF" and vers == "USD":
        return (montant / taux).quantize(Decimal("0.01"))
    if de == "USD" and vers == "CDF":
        return (montant * taux).quantize(Decimal("0.01"))
    raise ValueError(f"Conversion non supportée : {de} → {vers}")


def est_type_frais_inscription(type_frais):
    """True si le libellé du type de frais désigne un frais d'inscription."""
    lib = (getattr(type_frais, "libelle", None) or "").lower()
    return "inscription" in lib or "inscr" in lib


def est_type_frais_minerval(type_frais):
    """True si le libellé désigne un minerval / frais de scolarité."""
    lib = (getattr(type_frais, "libelle", None) or "").lower()
    return any(token in lib for token in ("minerval", "scolarité", "scolarite", "mensuel"))


def types_frais_minerval_for_ecole(ecole):
    if ecole is None:
        return TypeFrais.objects.none()
    qs = type_frais_for_ecole(ecole)
    ids = [t.id for t in qs if est_type_frais_minerval(t)]
    return qs.filter(pk__in=ids)


def solde_caisse_comptable(ecole, compte_numero="571100"):
    """Solde comptable caisse (Σ débit − Σ crédit) pour le compte HOADA donné."""
    if ecole is None:
        return {
            "compte": None,
            "debit": Decimal("0"),
            "credit": Decimal("0"),
            "solde": Decimal("0"),
        }

    compte = CompteComptable.objects.filter(ecole=ecole, numero=str(compte_numero)).first()
    if not compte:
        return {
            "compte": None,
            "debit": Decimal("0"),
            "credit": Decimal("0"),
            "solde": Decimal("0"),
        }

    lignes = EcritureLigne.objects.filter(
        compte=compte,
        ecriture__ecole=ecole,
    )
    debit = _decimal(
        lignes.filter(sens="DEBIT").aggregate(total=Sum("montant"))["total"]
    )
    credit = _decimal(
        lignes.filter(sens="CREDIT").aggregate(total=Sum("montant"))["total"]
    )
    return {
        "compte": compte,
        "debit": debit,
        "credit": credit,
        "solde": debit - credit,
    }


def caisse_especes_par_devise(ecole):
    """
    Encaissements VALIDÉS en espèces par devise réellement reçue.

    Si un paiement a été reçu en CDF puis converti en USD (montant_origine /
    devise_origine), il est compté en CDF — pas dans la caisse USD.
    """
    if ecole is None:
        return []

    from collections import defaultdict

    totaux = defaultdict(lambda: Decimal("0"))
    paiements = (
        paiements_for_ecole(ecole)
        .filter(statut="VALIDE", mode_paiement="ESPECES")
        .select_related("devise", "devise_origine")
    )
    for p in paiements:
        if p.montant_origine is not None and p.devise_origine_id:
            code = str(p.devise_origine.devise).upper()
            totaux[code] += _decimal(p.montant_origine)
        elif p.montant_origine is not None and p.devise_id and str(p.devise.devise).upper() != "CDF":
            # Conversion CDF→USD sans devise_origine renseignée : traiter comme CDF reçu
            totaux["CDF"] += _decimal(p.montant_origine)
        else:
            code = str(p.devise.devise).upper() if p.devise_id else "—"
            totaux[code] += _decimal(p.montant_paye)

    return [
        {"devise__devise": code, "total": total}
        for code, total in sorted(totaux.items(), key=lambda x: (-x[1], x[0]))
    ]


def minerval_paiements_queryset(ecole, filters=None):
    """Paiements VALIDÉs de minerval/scolarité, avec filtres optionnels."""
    filters = filters or {}
    types = types_frais_minerval_for_ecole(ecole)
    qs = (
        paiements_for_ecole(ecole)
        .filter(statut="VALIDE")
        .select_related(
            "eleve",
            "eleve__classe",
            "eleve__classe__section",
            "frais",
            "frais__type_frais",
            "frais__annee",
            "devise",
        )
    )

    type_frais_id = filters.get("type_frais")
    if type_frais_id:
        qs = qs.filter(frais__type_frais_id=type_frais_id)
    elif types.exists():
        qs = qs.filter(frais__type_frais__in=types)
    else:
        # Fallback si aucun type « minerval » n'est nommé ainsi en base
        qs = qs.filter(
            Q(frais__type_frais__libelle__icontains="minerval")
            | Q(frais__type_frais__libelle__icontains="scolar")
        )

    if filters.get("annee"):
        qs = qs.filter(eleve__annee_s_id=filters["annee"])
    if filters.get("section"):
        qs = qs.filter(eleve__classe__section_id=filters["section"])
    if filters.get("classe"):
        qs = qs.filter(eleve__classe_id=filters["classe"])
    if filters.get("devise"):
        qs = qs.filter(devise_id=filters["devise"])
    if filters.get("mode_paiement"):
        qs = qs.filter(mode_paiement=filters["mode_paiement"])
    if filters.get("date_debut"):
        qs = qs.filter(date_encodage__date__gte=filters["date_debut"])
    if filters.get("date_fin"):
        qs = qs.filter(date_encodage__date__lte=filters["date_fin"])

    return qs


def minerval_par_classe(ecole, filters=None):
    """Agrège les paiements minerval par classe (et devise)."""
    qs = minerval_paiements_queryset(ecole, filters)
    return list(
        qs.values(
            "eleve__classe_id",
            "eleve__classe__classe",
            "eleve__classe__section__section",
            "devise__devise",
        )
        .annotate(total=Sum("montant_paye"), nb=Count("id"))
        .order_by("eleve__classe__section__section", "eleve__classe__classe")
    )


def types_frais_inscription_for_ecole(ecole):
    if ecole is None:
        return TypeFrais.objects.none()
    qs = TypeFrais.objects.filter(ecole=ecole)
    ids = [t.id for t in qs if est_type_frais_inscription(t)]
    return qs.filter(pk__in=ids)


def sync_frais_inscription(inscription):
    """Recalcule Inscription.frais_inscription à partir des paiements VALIDÉs.

    Marqué payé uniquement lorsque tous les barèmes de frais d'inscription
    applicables (section + année) sont entièrement soldés.
    """
    from inscription.models import Inscription

    if inscription is None:
        return

    try:
        ecole = inscription.classe.ecole
    except AttributeError:
        return

    types = types_frais_inscription_for_ecole(ecole)
    if not types.exists():
        return

    frais_qs = frais_for_ecole(ecole).filter(
        type_frais__in=types,
        annee_id=inscription.annee_s_id,
        section_id=inscription.classe.section_id,
    )
    if not frais_qs.exists():
        # Pas de barème : présence d'au moins un paiement VALIDE du type inscription.
        est_paye = Paiement.objects.filter(
            eleve=inscription,
            statut="VALIDE",
            frais__type_frais__in=types,
        ).exists()
    else:
        paye_par_frais = paiements_valides_par_frais(ecole)
        est_paye = all(
            solde_frais(frais, inscription.id, paye_par_frais)["est_solde"]
            for frais in frais_qs
        )

    Inscription.objects.filter(pk=inscription.pk).update(frais_inscription=est_paye)


def sync_frais_inscription_depuis_paiement(paiement):
    """Point d'entrée après création / modification / suppression d'un paiement."""
    if paiement is None:
        return
    inscription = getattr(paiement, "eleve", None)
    if inscription is None:
        return

    try:
        type_frais = paiement.frais.type_frais
    except AttributeError:
        type_frais = None

    # Ignore les paiements hors inscription, sauf pour remettre le flag à False.
    if type_frais and not est_type_frais_inscription(type_frais):
        if not getattr(inscription, "frais_inscription", False):
            return

    sync_frais_inscription(inscription)


def paiements_valides_par_frais(ecole, exclude_paiement_id=None):
    """Retourne {(inscription_id, frais_id): montant_paye} pour les paiements validés."""
    qs = paiements_for_ecole(ecole).filter(statut="VALIDE")
    if exclude_paiement_id:
        qs = qs.exclude(pk=exclude_paiement_id)

    result = {}
    for row in qs.values("eleve_id", "frais_id").annotate(total=Sum("montant_paye")):
        result[(row["eleve_id"], row["frais_id"])] = _decimal(row["total"])
    return result


def solde_frais(frais, inscription_id, paye_par_frais):
    total = _decimal(frais.montant)
    paye = paye_par_frais.get((inscription_id, frais.id), Decimal("0"))
    reste = total - paye
    return {
        "total": total,
        "paye": paye,
        "reste": reste,
        "est_solde": reste <= 0,
    }


def frais_disponibles_pour_inscription(ecole, inscription, exclude_paiement_id=None):
    """Frais encore dus pour une inscription, avec montants payé/reste."""
    if not inscription:
        return []

    paye_par_frais = paiements_valides_par_frais(ecole, exclude_paiement_id)
    frais_qs = frais_for_ecole(ecole).filter(
        section_id=inscription.classe.section_id,
        annee=inscription.annee_s,
    ).select_related("type_frais", "section", "annee", "devise")

    disponibles = []
    for frais in frais_qs:
        solde = solde_frais(frais, inscription.id, paye_par_frais)
        if solde["est_solde"]:
            continue
        disponibles.append({
            "frais": frais,
            **solde,
        })
    return disponibles


def build_frais_solde_context(ecole, inscriptions_qs, exclude_paiement_id=None):
    """Construit la structure JSON {inscription_id: {frais_id: {...}}}."""
    paye_par_frais = paiements_valides_par_frais(ecole, exclude_paiement_id)
    frais_qs = frais_for_ecole(ecole).select_related("type_frais", "section", "annee", "devise")

    frais_by_section_annee = {}
    for frais in frais_qs:
        key = (frais.section_id, frais.annee_id)
        frais_by_section_annee.setdefault(key, []).append(frais)

    result = {}
    for ins in inscriptions_qs:
        key = (ins.classe.section_id, ins.annee_s_id)
        result[str(ins.id)] = {}
        for frais in frais_by_section_annee.get(key, []):
            solde = solde_frais(frais, ins.id, paye_par_frais)
            if solde["est_solde"]:
                continue
            result[str(ins.id)][str(frais.id)] = {
                "libelle": frais.type_frais.libelle,
                "section": str(frais.section),
                "annee": str(frais.annee),
                "section_id": frais.section_id,
                "annee_id": frais.annee_id,
                "devise_id": frais.devise_id,
                "devise": str(frais.devise),
                "montant_total": str(solde["total"]),
                "montant_paye": str(solde["paye"]),
                "montant_restant": str(solde["reste"]),
                "a_avance": solde["paye"] > 0,
            }
    return result
