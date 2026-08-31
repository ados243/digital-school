from collections import defaultdict
from datetime import date
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


def caisse_disponible_par_devise(ecole):
    """
    Espèces réellement disponibles par devise :
    encaissements ESPECES − salaires PAYÉS en ESPECES.
    """
    totaux = defaultdict(lambda: Decimal("0"))
    for row in caisse_especes_par_devise(ecole):
        totaux[str(row["devise__devise"]).upper()] += _decimal(row["total"])

    if ecole is not None:
        from grh.models import Paie

        paies = (
            Paie.objects.filter(
                personnel__ecole=ecole,
                statut_paiement="PAYE",
                mode_paiement="ESPECES",
            )
            .select_related("devise")
        )
        for paie in paies:
            code = str(paie.devise.devise).upper() if paie.devise_id else "—"
            totaux[code] -= _decimal(paie.net_a_payer)

    return [
        {"devise__devise": code, "total": total}
        for code, total in sorted(totaux.items(), key=lambda x: (-x[1], x[0]))
    ]


def verifier_depense_contre_caisse(ecole, montant, devise_code, mode_paiement="ESPECES"):
    """
    Empêche une dépense supérieure au disponible.

    Retourne (ok, message, disponible).
    - ESPECES : contrôle par devise (encaissements − sorties)
    - Autres modes : solde du compte de trésorerie HOADA associé
    """
    montant = _decimal(montant)
    mode = (mode_paiement or "ESPECES").strip().upper() or "ESPECES"
    devise = (devise_code or "").strip().upper() or "—"

    if mode == "ESPECES":
        disponible = Decimal("0")
        for row in caisse_disponible_par_devise(ecole):
            if str(row["devise__devise"]).upper() == devise:
                disponible = _decimal(row["total"])
                break
        if montant > disponible:
            return (
                False,
                (
                    f"Dépense impossible : le montant ({montant} {devise}) dépasse "
                    f"la somme disponible en caisse ({disponible} {devise})."
                ),
                disponible,
            )
        return True, "", disponible

    comptes = {
        "VIREMENT": "521100",
        "CHEQUE": "521100",
        "MOBILE_MONEY": "565000",
    }
    numero = comptes.get(mode)
    if not numero:
        return True, "", None

    info = solde_caisse_comptable(ecole, numero)
    disponible = _decimal(info["solde"])
    if montant > disponible:
        return (
            False,
            (
                f"Dépense impossible : le montant ({montant} {devise}) dépasse "
                f"la somme disponible ({disponible}) sur le compte {numero}."
            ),
            disponible,
        )
    return True, "", disponible


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
        .prefetch_related("classes")
    )
    if types_filtre.exists():
        frais_qs = frais_qs.filter(type_frais__in=types_filtre)
    else:
        frais_qs = frais_qs.filter(fallback_q)

    frais_par_section = {}
    frais_par_classe = {}
    for frais in frais_qs:
        classes_cibles = list(frais.classes.all())
        if classes_cibles:
            for classe_cible in classes_cibles:
                frais_par_classe.setdefault(classe_cible.id, []).append(frais)
        elif frais.section_id:
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
        fusion = {}
        for f in frais_par_section.get(classe.section_id, []):
            fusion[f.id] = f
        for f in frais_par_classe.get(classe.id, []):
            fusion[f.id] = f
        frais_section = list(fusion.values())

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


def projection_salaires_annuels(ecole, annee=None):
    """
    Projection annuelle des salaires : contrats actifs × 12 mois.
    Si une année scolaire est fournie, ne retient que les contrats
    en vigueur pendant cette période (chevauchement des dates).
    """
    from grh.tenant import contrats_for_ecole

    total_usd = Decimal("0")
    total_cdf = Decimal("0")
    total_mensuel_usd = Decimal("0")
    total_mensuel_cdf = Decimal("0")
    if ecole is None:
        return {
            "total_usd": total_usd,
            "total_cdf": total_cdf,
            "total_mensuel_usd": total_mensuel_usd,
            "total_mensuel_cdf": total_mensuel_cdf,
            "nb_contrats": 0,
        }

    contrats = (
        contrats_for_ecole(ecole)
        .filter(statut="ACTIF")
        .select_related("devise", "personnel")
    )
    if annee is not None and getattr(annee, "date_debut", None) and getattr(annee, "date_fin", None):
        debut, fin = annee.date_debut, annee.date_fin
        contrats = contrats.filter(date_debut__lte=fin).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=debut)
        )

    nb = 0
    for c in contrats:
        nb += 1
        mensuel = _decimal(c.salaire_base)
        annuel = (mensuel * Decimal("12")).quantize(Decimal("0.01"))
        code = (c.devise.devise if c.devise else "").upper()
        if code == "USD":
            total_mensuel_usd += mensuel
            total_usd += annuel
        elif code == "CDF":
            total_mensuel_cdf += mensuel
            total_cdf += annuel
    return {
        "total_usd": total_usd,
        "total_cdf": total_cdf,
        "total_mensuel_usd": total_mensuel_usd.quantize(Decimal("0.01")),
        "total_mensuel_cdf": total_mensuel_cdf.quantize(Decimal("0.01")),
        "nb_contrats": nb,
    }


def construire_postes_budget(ecole, annee, budget=None):
    """
    Construit la liste des postes (toutes rubriques actives) avec montants
    proposés (auto) ou déjà figés sur le budget.
    Les rubriques en calcul_auto (minerval, inscription, salaires) restent
    toujours recalculées depuis les données courantes. Les autres recettes
    issues de barèmes (labo, examen, etc.) s'ajoutent au snapshot s'ils
    ont été créés après la fixation.
    """
    from .defaults import assurer_rubriques_budget
    from .models import RubriqueBudget

    assurer_rubriques_budget()
    rubriques = list(RubriqueBudget.objects.filter(actif=True))

    proj_min = projection_budget_minerval(ecole, annee)
    proj_ins = projection_budget_inscription(ecole, annee)
    proj_sal = projection_salaires_annuels(ecole, annee)
    proj_frais = projection_frais_par_rubrique(ecole, annee)

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
        live_usd = Decimal("0")
        live_cdf = Decimal("0")

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
            if proj_sal["nb_contrats"]:
                note = (
                    f"{proj_sal['nb_contrats']} contrat(s) actifs · "
                    f"{proj_sal['total_mensuel_usd']} USD + "
                    f"{proj_sal['total_mensuel_cdf']} CDF / mois × 12"
                )
            else:
                note = "Aucun contrat actif — masse salariale à 0"
        else:
            bucket = proj_frais.get(rub.code) or _bucket_devise()
            live_usd = bucket["usd"]
            live_cdf = bucket["cdf"]
            montant_usd = live_usd
            montant_cdf = live_cdf
            if live_usd or live_cdf:
                note = "Barème actuel × capacité des classes"

        poste_saved = saved.get(rub.id)
        if poste_saved is not None and not rub.calcul_auto:
            # Snapshot figé, augmenté si de nouveaux frais ont été ajoutés depuis.
            fige_usd = _decimal(poste_saved.montant_usd)
            fige_cdf = _decimal(poste_saved.montant_cdf)
            montant_usd = max(fige_usd, live_usd)
            montant_cdf = max(fige_cdf, live_cdf)
            est_auto = poste_saved.est_auto
            if poste_saved.note:
                note = poste_saved.note
            if live_usd > fige_usd or live_cdf > fige_cdf:
                extra = []
                if live_usd > fige_usd:
                    extra.append(f"+{live_usd - fige_usd} USD")
                if live_cdf > fige_cdf:
                    extra.append(f"+{live_cdf - fige_cdf} CDF")
                ajout = "Frais ajoutés après fixation (" + ", ".join(extra) + ")"
                note = f"{note} · {ajout}".strip(" ·")[:255]
        elif poste_saved is not None and rub.calcul_auto and poste_saved.note and not note:
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


# Libellés de types de frais → rubrique recette (hors minerval / inscription).
_MOTS_RUBRIQUE_RECETTE = (
    ("R_EXAMEN", ("examen", "composition")),
    ("R_TENUE", ("tenue", "uniforme")),
    ("R_LABO", ("laboratoire", "labo", "informatique")),
    ("R_TRANSPORT", ("transport",)),
    ("R_CANTINE", ("cantine", "restauration")),
    ("R_COTI", ("cotisation", "association", "ape")),
    ("R_SUBVENTION", ("subvention", "don")),
)


def code_rubrique_pour_type_frais(type_frais_ou_libelle):
    """Associe un type de frais (objet ou libellé) à une rubrique recette."""
    if hasattr(type_frais_ou_libelle, "libelle"):
        lib = type_frais_ou_libelle.libelle or ""
        cible = type_frais_ou_libelle
    else:
        lib = type_frais_ou_libelle or ""
        cible = type("TypeFraisLibelle", (), {"libelle": lib})()
    if est_type_frais_inscription(cible):
        return "R_INSCRIPTION"
    if est_type_frais_minerval(cible):
        return "R_MINERVAL"
    lib_l = lib.lower()
    for code, mots in _MOTS_RUBRIQUE_RECETTE:
        if any(mot in lib_l for mot in mots):
            return code
    return "R_AUTRES"


def projection_frais_par_rubrique(ecole, annee):
    """
    Projette tous les barèmes de l'année (section ou classes ciblées)
    vers les rubriques recettes : capacité × montant.
    """
    from collections import defaultdict
    from inscription.tenant import classes_for_ecole

    totaux = defaultdict(_bucket_devise)
    if ecole is None or annee is None:
        return totaux

    classes = list(classes_for_ecole(ecole).select_related("section"))
    par_section = defaultdict(list)
    for classe in classes:
        par_section[classe.section_id].append(classe)

    frais_qs = (
        frais_for_ecole(ecole)
        .filter(annee=annee)
        .select_related("type_frais", "section", "devise")
        .prefetch_related("classes")
    )
    for frais in frais_qs:
        code_rub = code_rubrique_pour_type_frais(frais.type_frais)
        code_dev = (frais.devise.devise if frais.devise_id else "").upper()
        cibles = list(frais.classes.all())
        if cibles:
            capacite = sum(max(0, int(c.capacite_max or 0)) for c in cibles)
        elif frais.section_id:
            capacite = sum(
                max(0, int(c.capacite_max or 0))
                for c in par_section.get(frais.section_id, [])
            )
        else:
            capacite = 0
        sous_total = (_decimal(frais.montant) * Decimal(capacite)).quantize(Decimal("0.01"))
        _ajouter_devise(totaux[code_rub], code_dev, sous_total)
    return totaux


def _bucket_devise():
    return {"usd": Decimal("0"), "cdf": Decimal("0")}


def _ajouter_devise(bucket, code_devise, montant):
    code = (code_devise or "").upper()
    montant = _decimal(montant)
    if code == "USD":
        bucket["usd"] += montant
    elif code == "CDF":
        bucket["cdf"] += montant


def _pct_execution(realise, budgete):
    realise = _decimal(realise)
    budgete = _decimal(budgete)
    if budgete <= 0:
        return None if realise <= 0 else Decimal("100.0")
    return (realise * Decimal("100") / budgete).quantize(Decimal("0.1"))


def _barre_pct(pct):
    if pct is None:
        return Decimal("0")
    pct = _decimal(pct)
    if pct < 0:
        return Decimal("0")
    if pct > 100:
        return Decimal("100")
    return pct


def _etat_execution(nature, pct):
    if pct is None:
        return "empty"
    pct = _decimal(pct)
    if nature == "DEPENSE":
        if pct > 100:
            return "full"
        if pct >= 80:
            return "warn"
        return "ok"
    if pct >= 90:
        return "ok"
    if pct >= 50:
        return "warn"
    return "empty"


_MOTS_RUBRIQUE_DEPENSE = (
    ("D_CHARGES_SOC", ("inss", "onem", "social", "cnss")),
    ("D_FOURNITURES", ("fourniture",)),
    ("D_DIDACTIQUE", ("didactique", "manuel", "livre")),
    ("D_EAU_ELEC", ("eau", "électricité", "electricite", "snel")),
    ("D_INTERNET", ("internet", "télécom", "telecom")),
    ("D_ENTRETIEN", ("entretien", "maintenance")),
    ("D_CARBURANT", ("carburant", "essence", "gasoil")),
    ("D_SECURITE", ("sécurité", "securite", "gardien")),
    ("D_IMPOTS", ("impôt", "impot", "taxe")),
    ("D_ASSURANCE", ("assurance",)),
    ("D_FORMATION", ("formation", "recyclage")),
    ("D_INVEST", ("investissement", "équipement", "equipement")),
    ("D_PARASCO", ("parascolaire",)),
)


def code_rubrique_pour_depense(libelle, numero=""):
    """Associe une charge comptable à une rubrique de dépense."""
    num = str(numero or "")
    lib = (libelle or "").lower()
    if num.startswith("66") or "salaire" in lib or "personnel" in lib:
        return "D_SALAIRES"
    for code, mots in _MOTS_RUBRIQUE_DEPENSE:
        if any(mot in lib for mot in mots):
            return code
    return "D_IMPREVUS"


def realisations_budget(ecole, annee):
    """Montants réellement encaissés / dépensés, par code de rubrique."""
    totaux = defaultdict(_bucket_devise)
    if ecole is None or annee is None:
        return totaux

    paiements = (
        paiements_for_ecole(ecole)
        .filter(statut="VALIDE", eleve__annee_s=annee)
        .values("frais__type_frais__libelle", "devise__devise")
        .annotate(total=Sum("montant_paye"))
    )
    for row in paiements:
        code = code_rubrique_pour_type_frais(row["frais__type_frais__libelle"])
        _ajouter_devise(totaux[code], row["devise__devise"], row["total"])

    from grh.tenant import paies_for_ecole

    debut = annee.date_debut
    fin = annee.date_fin
    paies = paies_for_ecole(ecole).filter(statut_paiement="PAYE")
    for row in (
        paies.filter(date_paiement__gte=debut, date_paiement__lte=fin)
        .values("devise__devise")
        .annotate(total=Sum("net_a_payer"))
    ):
        _ajouter_devise(totaux["D_SALAIRES"], row["devise__devise"], row["total"])

    for paie in paies.filter(
        date_paiement__isnull=True,
        annee__gte=debut.year,
        annee__lte=fin.year,
    ).select_related("devise"):
        try:
            ref = date(int(paie.annee), int(paie.mois), 1)
        except (TypeError, ValueError):
            continue
        if debut <= ref <= fin:
            code = paie.devise.devise if paie.devise_id else ""
            _ajouter_devise(totaux["D_SALAIRES"], code, paie.net_a_payer)

    # Charges HOADA (classe 6) hors salaires déjà comptés via les paies.
    from .models import EcritureLigne

    charges = (
        EcritureLigne.objects.filter(
            ecriture__ecole=ecole,
            sens="DEBIT",
            compte__numero__startswith="6",
            ecriture__date_ecriture__gte=debut,
            ecriture__date_ecriture__lte=fin,
        )
        .exclude(compte__numero__startswith="66")
        .select_related("compte", "compte__devise")
    )
    for ligne in charges:
        code = code_rubrique_pour_depense(ligne.compte.libelle, ligne.compte.numero)
        if code == "D_SALAIRES":
            continue
        devise_code = (
            ligne.compte.devise.devise if ligne.compte.devise_id else "USD"
        )
        _ajouter_devise(totaux[code], devise_code, ligne.montant)

    return totaux


def _enrichir_poste_suivi(poste, realisations):
    code = poste["rubrique"].code
    reali = realisations.get(code) or _bucket_devise()
    nature = poste["rubrique"].nature
    enrichi = dict(poste)
    enrichi["realise_usd"] = reali["usd"]
    enrichi["realise_cdf"] = reali["cdf"]
    enrichi["ecart_usd"] = reali["usd"] - _decimal(poste["montant_usd"])
    enrichi["ecart_cdf"] = reali["cdf"] - _decimal(poste["montant_cdf"])
    enrichi["pct_usd"] = _pct_execution(reali["usd"], poste["montant_usd"])
    enrichi["pct_cdf"] = _pct_execution(reali["cdf"], poste["montant_cdf"])
    enrichi["barre_usd"] = _barre_pct(enrichi["pct_usd"])
    enrichi["barre_cdf"] = _barre_pct(enrichi["pct_cdf"])
    enrichi["etat_usd"] = _etat_execution(nature, enrichi["pct_usd"])
    enrichi["etat_cdf"] = _etat_execution(nature, enrichi["pct_cdf"])
    enrichi["inactif"] = (
        _decimal(poste["montant_usd"]) == 0
        and _decimal(poste["montant_cdf"]) == 0
        and reali["usd"] == 0
        and reali["cdf"] == 0
    )
    return enrichi


def enrichir_plan_suivi(plan, realisations):
    """Ajoute réalisé, écart et % d'exécution à chaque poste du plan."""
    recettes = [_enrichir_poste_suivi(p, realisations) for p in plan.get("recettes", [])]
    depenses = [_enrichir_poste_suivi(p, realisations) for p in plan.get("depenses", [])]
    postes = [_enrichir_poste_suivi(p, realisations) for p in plan.get("postes", [])]

    def _sum(rows, key):
        return sum((_decimal(r[key]) for r in rows), Decimal("0"))

    total_r_usd = plan.get("total_recettes_usd") or Decimal("0")
    total_r_cdf = plan.get("total_recettes_cdf") or Decimal("0")
    total_d_usd = plan.get("total_depenses_usd") or Decimal("0")
    total_d_cdf = plan.get("total_depenses_cdf") or Decimal("0")
    reali_r_usd = _sum(recettes, "realise_usd")
    reali_r_cdf = _sum(recettes, "realise_cdf")
    reali_d_usd = _sum(depenses, "realise_usd")
    reali_d_cdf = _sum(depenses, "realise_cdf")

    enrichi = dict(plan)
    enrichi["postes"] = postes
    enrichi["recettes"] = recettes
    enrichi["depenses"] = depenses
    enrichi["realise_recettes_usd"] = reali_r_usd
    enrichi["realise_recettes_cdf"] = reali_r_cdf
    enrichi["realise_depenses_usd"] = reali_d_usd
    enrichi["realise_depenses_cdf"] = reali_d_cdf
    enrichi["ecart_recettes_usd"] = reali_r_usd - _decimal(total_r_usd)
    enrichi["ecart_recettes_cdf"] = reali_r_cdf - _decimal(total_r_cdf)
    enrichi["ecart_depenses_usd"] = reali_d_usd - _decimal(total_d_usd)
    enrichi["ecart_depenses_cdf"] = reali_d_cdf - _decimal(total_d_cdf)
    enrichi["solde_realise_usd"] = reali_r_usd - reali_d_usd
    enrichi["solde_realise_cdf"] = reali_r_cdf - reali_d_cdf
    enrichi["pct_recettes_usd"] = _pct_execution(reali_r_usd, total_r_usd)
    enrichi["pct_recettes_cdf"] = _pct_execution(reali_r_cdf, total_r_cdf)
    enrichi["pct_depenses_usd"] = _pct_execution(reali_d_usd, total_d_usd)
    enrichi["pct_depenses_cdf"] = _pct_execution(reali_d_cdf, total_d_cdf)
    enrichi["barre_recettes_usd"] = _barre_pct(enrichi["pct_recettes_usd"])
    enrichi["barre_depenses_usd"] = _barre_pct(enrichi["pct_depenses_usd"])
    enrichi["etat_recettes"] = _etat_execution("RECETTE", enrichi["pct_recettes_usd"])
    enrichi["etat_depenses"] = _etat_execution("DEPENSE", enrichi["pct_depenses_usd"])
    return enrichi


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

    frais_qs = frais_applicables_pour_inscription(ecole, inscription).filter(
        type_frais__in=types
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


def frais_concerne_inscription(frais, inscription):
    """True si le barème s'applique à l'élève (section entière ou classes ciblées)."""
    if frais is None or inscription is None:
        return False
    if frais.annee_id != inscription.annee_s_id:
        return False
    cache = getattr(frais, "_prefetched_objects_cache", None)
    if cache is not None and "classes" in cache:
        classe_ids = {c.id for c in frais.classes.all()}
    else:
        classe_ids = set(frais.classes.values_list("id", flat=True))
    if classe_ids:
        return inscription.classe_id in classe_ids
    return bool(frais.section_id) and frais.section_id == inscription.classe.section_id


def frais_applicables_pour_inscription(ecole, inscription):
    """Barèmes dus par l'inscription : section ou classes ciblées."""
    if ecole is None or inscription is None:
        return Frais_Scolaire.objects.none()
    return (
        frais_for_ecole(ecole)
        .filter(annee=inscription.annee_s)
        .filter(
            Q(classes=inscription.classe)
            | Q(classes__isnull=True, section_id=inscription.classe.section_id)
        )
        .distinct()
        .select_related("type_frais", "section", "annee", "devise")
        .prefetch_related("classes")
    )


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


def frais_bloquants_pour_frais(ecole, inscription, frais, exclude_paiement_id=None):
    """
    Retourne la liste des frais applicables de niveau prioritaire supérieur (< frais.niveau_priorite)
    qui ne sont pas encore intégralement soldés pour cette inscription.
    """
    if not inscription or not frais:
        return []

    priorite_cible = getattr(frais, "niveau_priorite", 1) or 1
    paye_par_frais = paiements_valides_par_frais(ecole, exclude_paiement_id)
    frais_qs = frais_applicables_pour_inscription(ecole, inscription)

    bloquants = []
    for f in frais_qs:
        if f.id == frais.id:
            continue
        p_f = getattr(f, "niveau_priorite", 1) or 1
        if p_f < priorite_cible:
            solde = solde_frais(f, inscription.id, paye_par_frais)
            if not solde["est_solde"]:
                bloquants.append({
                    "frais": f,
                    "libelle": getattr(f.type_frais, "libelle", str(f)),
                    "niveau_priorite": p_f,
                    "reste": solde["reste"],
                    "devise": str(f.devise) if f.devise_id else "",
                    "solde": solde,
                })

    return bloquants


def frais_disponibles_pour_inscription(ecole, inscription, exclude_paiement_id=None, filtrer_priorite=False):
    """
    Frais encore dus pour une inscription, avec montants payé/reste.
    Si filtrer_priorite=True, exclut les frais bloqués par des frais de niveau supérieur non soldés.
    """
    if not inscription:
        return []

    paye_par_frais = paiements_valides_par_frais(ecole, exclude_paiement_id)
    frais_qs = frais_applicables_pour_inscription(ecole, inscription).order_by("niveau_priorite", "echeance", "id")

    dus_tous = []
    for frais in frais_qs:
        solde = solde_frais(frais, inscription.id, paye_par_frais)
        if solde["est_solde"]:
            continue
        dus_tous.append({
            "frais": frais,
            "niveau_priorite": getattr(frais, "niveau_priorite", 1) or 1,
            **solde,
        })

    if not filtrer_priorite or not dus_tous:
        return dus_tous

    # Identifier le niveau de priorité minimal non soldé
    min_priorite = min(d["niveau_priorite"] for d in dus_tous)
    # Seuls les frais du niveau minimal en attente sont disponibles
    return [d for d in dus_tous if d["niveau_priorite"] == min_priorite]


def build_frais_solde_context(ecole, inscriptions_qs, exclude_paiement_id=None):
    """Construit la structure JSON {inscription_id: {frais_id: {...}}} avec gestion des priorités."""
    paye_par_frais = paiements_valides_par_frais(ecole, exclude_paiement_id)
    frais_qs = list(
        frais_for_ecole(ecole)
        .select_related("type_frais", "section", "annee", "devise")
        .prefetch_related("classes")
        .order_by("niveau_priorite", "echeance", "id")
    )

    result = {}
    for ins in inscriptions_qs:
        result[str(ins.id)] = {}
        # Étape 1 : calculer les soldes de tous les frais applicables
        applicables = []
        for frais in frais_qs:
            if not frais_concerne_inscription(frais, ins):
                continue
            solde = solde_frais(frais, ins.id, paye_par_frais)
            if solde["est_solde"]:
                continue
            applicables.append((frais, solde))

        # Étape 2 : déterminer pour chaque frais s'il est bloqué par un niveau supérieur non soldé
        non_soldes_priorites = {
            frais.id: getattr(frais, "niveau_priorite", 1) or 1
            for frais, solde in applicables
        }

        for frais, solde in applicables:
            f_prio = getattr(frais, "niveau_priorite", 1) or 1
            bloquants = []
            for f_other, s_other in applicables:
                if f_other.id != frais.id:
                    o_prio = getattr(f_other, "niveau_priorite", 1) or 1
                    if o_prio < f_prio:
                        bloquants.append({
                            "libelle": f_other.type_frais.libelle,
                            "niveau_priorite": o_prio,
                            "reste": str(s_other["reste"]),
                            "devise": str(f_other.devise) if f_other.devise_id else "",
                        })

            est_bloque = bool(bloquants)
            msg_blocage = ""
            if est_bloque:
                niveaux = sorted({b["niveau_priorite"] for b in bloquants})
                noms = ", ".join(f"{b['libelle']} (reste {b['reste']} {b['devise']})" for b in bloquants)
                msg_blocage = (
                    f"Priorité bloquée : les frais de Niveau {', '.join(map(str, niveaux))} "
                    f"({noms}) doivent être intégralement soldés au préalable."
                )

            result[str(ins.id)][str(frais.id)] = {
                "libelle": frais.type_frais.libelle,
                "section": str(frais.section) if frais.section_id else frais.portee_libelle(),
                "annee": str(frais.annee),
                "section_id": frais.section_id,
                "annee_id": frais.annee_id,
                "devise_id": frais.devise_id,
                "devise": str(frais.devise),
                "montant_total": str(solde["total"]),
                "montant_paye": str(solde["paye"]),
                "montant_restant": str(solde["reste"]),
                "a_avance": solde["paye"] > 0,
                "niveau_priorite": f_prio,
                "est_bloque": est_bloque,
                "bloque_par": bloquants,
                "message_blocage": msg_blocage,
            }
    return result
