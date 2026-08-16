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


def projection_budget_minerval(ecole, annee):
    """
    Projette le budget annuel : pour chaque classe,
    capacité_max × somme des frais minerval de la section (année donnée).
    """
    return _projection_frais_par_capacite(
        ecole, annee, mode="minerval"
    )


def projection_budget_inscription(ecole, annee):
    """Capacité × frais d'inscription par section."""
    return _projection_frais_par_capacite(
        ecole, annee, mode="inscription"
    )


def _projection_frais_par_capacite(ecole, annee, mode="minerval"):
    from inscription.tenant import classes_for_ecole

    if ecole is None or annee is None:
        return {
            "lignes": [],
            "capacite_totale": 0,
            "total_usd": Decimal("0"),
            "total_cdf": Decimal("0"),
            "alertes": ["École ou année scolaire manquante."],
        }

    if mode == "inscription":
        types_filtre = types_frais_inscription_for_ecole(ecole)
        fallback_q = Q(type_frais__libelle__icontains="inscription") | Q(
            type_frais__libelle__icontains="inscr"
        )
        label_manquant = "inscription"
    else:
        types_filtre = types_frais_minerval_for_ecole(ecole)
        fallback_q = Q(type_frais__libelle__icontains="minerval") | Q(
            type_frais__libelle__icontains="scolar"
        )
        label_manquant = "minerval"

    frais_qs = (
        frais_for_ecole(ecole)
        .filter(annee=annee)
        .select_related("type_frais", "section", "devise")
    )
    if types_filtre.exists():
        frais_qs = frais_qs.filter(type_frais__in=types_filtre)
    else:
        frais_qs = frais_qs.filter(fallback_q)

    frais_par_section = {}
    for frais in frais_qs:
        frais_par_section.setdefault(frais.section_id, []).append(frais)

    classes = (
        classes_for_ecole(ecole)
        .select_related("section")
        .order_by("section__section", "classe")
    )

    lignes = []
    capacite_totale = 0
    total_usd = Decimal("0")
    total_cdf = Decimal("0")
    alertes = []
    sections_sans = set()

    for classe in classes:
        capacite = max(0, int(classe.capacite_max or 0))
        capacite_totale += capacite
        frais_section = frais_par_section.get(classe.section_id, [])

        if not frais_section:
            sections_sans.add(str(classe.section))
            lignes.append(
                {
                    "classe": classe,
                    "capacite": capacite,
                    "montant_unitaire": Decimal("0"),
                    "devise": None,
                    "sous_total": Decimal("0"),
                    "type_frais_libelle": "",
                    "sans_minerval": True,
                }
            )
            continue

        par_devise = {}
        libelles = []
        for f in frais_section:
            code = (f.devise.devise if f.devise else "").upper()
            par_devise.setdefault(code, {"montant": Decimal("0"), "devise": f.devise})
            par_devise[code]["montant"] += _decimal(f.montant)
            lib = getattr(f.type_frais, "libelle", "") or ""
            if lib and lib not in libelles:
                libelles.append(lib)

        if "USD" in par_devise:
            code = "USD"
        elif "CDF" in par_devise:
            code = "CDF"
        else:
            code = next(iter(par_devise))

        montant_unitaire = par_devise[code]["montant"]
        devise = par_devise[code]["devise"]
        sous_total = (montant_unitaire * Decimal(capacite)).quantize(Decimal("0.01"))

        if code == "USD":
            total_usd += sous_total
        elif code == "CDF":
            total_cdf += sous_total

        autres = [c for c in par_devise if c != code]
        if autres:
            alertes.append(
                f"Section {classe.section} : {label_manquant} multi-devises "
                f"({code} retenu, hors {', '.join(autres)})."
            )

        lignes.append(
            {
                "classe": classe,
                "capacite": capacite,
                "montant_unitaire": montant_unitaire,
                "devise": devise,
                "sous_total": sous_total,
                "type_frais_libelle": " + ".join(libelles),
                "sans_minerval": False,
            }
        )

    if sections_sans:
        alertes.append(
            f"Aucun frais {label_manquant} configuré pour : "
            + ", ".join(sorted(sections_sans))
            + "."
        )

    return {
        "lignes": lignes,
        "capacite_totale": capacite_totale,
        "total_usd": total_usd,
        "total_cdf": total_cdf,
        "alertes": alertes,
    }


def projection_salaires_annuels(ecole):
    """Projection annuelle des salaires : contrats actifs × 12 mois."""
    from grh.tenant import contrats_for_ecole

    total_usd = Decimal("0")
    total_cdf = Decimal("0")
    if ecole is None:
        return {"total_usd": total_usd, "total_cdf": total_cdf, "nb_contrats": 0}

    contrats = (
        contrats_for_ecole(ecole)
        .filter(statut="ACTIF")
        .select_related("devise")
    )
    nb = 0
    for c in contrats:
        nb += 1
        annuel = (_decimal(c.salaire_base) * Decimal("12")).quantize(Decimal("0.01"))
        code = (c.devise.devise if c.devise else "").upper()
        if code == "USD":
            total_usd += annuel
        elif code == "CDF":
            total_cdf += annuel
    return {"total_usd": total_usd, "total_cdf": total_cdf, "nb_contrats": nb}


def construire_postes_budget(ecole, annee, budget=None):
    """
    Construit la liste des postes (toutes rubriques actives) avec montants
    proposés (auto) ou déjà figés sur le budget.
    """
    from .defaults import assurer_rubriques_budget
    from .models import RubriqueBudget

    assurer_rubriques_budget()
    rubriques = list(RubriqueBudget.objects.filter(actif=True))

    proj_min = projection_budget_minerval(ecole, annee)
    proj_ins = projection_budget_inscription(ecole, annee)
    proj_sal = projection_salaires_annuels(ecole)

    saved = {}
    if budget is not None:
        for p in budget.postes.select_related("rubrique"):
            saved[p.rubrique_id] = p

    postes = []
    for rub in rubriques:
        montant_usd = Decimal("0")
        montant_cdf = Decimal("0")
        est_auto = bool(rub.calcul_auto)
        note = ""

        if rub.calcul_auto == "MINERVAL":
            montant_usd = proj_min["total_usd"]
            montant_cdf = proj_min["total_cdf"]
            note = f"Capacité {proj_min['capacite_totale']} places"
        elif rub.calcul_auto == "INSCRIPTION":
            montant_usd = proj_ins["total_usd"]
            montant_cdf = proj_ins["total_cdf"]
            note = f"Capacité {proj_ins['capacite_totale']} places"
        elif rub.calcul_auto == "SALAIRES":
            montant_usd = proj_sal["total_usd"]
            montant_cdf = proj_sal["total_cdf"]
            note = f"{proj_sal['nb_contrats']} contrat(s) × 12 mois"

        poste_saved = saved.get(rub.id)
        if poste_saved is not None:
            # Les montants figés priment ; on garde la note auto si vide
            montant_usd = _decimal(poste_saved.montant_usd)
            montant_cdf = _decimal(poste_saved.montant_cdf)
            est_auto = poste_saved.est_auto
            if poste_saved.note:
                note = poste_saved.note

        postes.append(
            {
                "rubrique": rub,
                "montant_usd": montant_usd,
                "montant_cdf": montant_cdf,
                "est_auto": est_auto,
                "note": note,
            }
        )

    recettes = [p for p in postes if p["rubrique"].nature == "RECETTE"]
    depenses = [p for p in postes if p["rubrique"].nature == "DEPENSE"]

    def _sum(rows, key):
        return sum((r[key] for r in rows), Decimal("0"))

    return {
        "postes": postes,
        "recettes": recettes,
        "depenses": depenses,
        "total_recettes_usd": _sum(recettes, "montant_usd"),
        "total_recettes_cdf": _sum(recettes, "montant_cdf"),
        "total_depenses_usd": _sum(depenses, "montant_usd"),
        "total_depenses_cdf": _sum(depenses, "montant_cdf"),
        "projection_minerval": proj_min,
        "projection_inscription": proj_ins,
        "projection_salaires": proj_sal,
    }


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
