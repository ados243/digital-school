"""Relances WhatsApp des soldes impayés (vue Finances + commande)."""

from collections import defaultdict
from decimal import Decimal

from finances.models import ConfigWhatsApp, NotificationWhatsApp
from finances.paiement_utils import est_type_frais_minerval, frais_disponibles_pour_inscription
from finances.whatsapp import _envoyer_via_provider, normaliser_telephone, provider_effectif
from inscription.models import Annee_Scolaire, Inscription


def _code_devise(frais):
    devise = getattr(frais, "devise", None)
    return str(devise) if devise else ""


def formater_totaux(totaux):
    if not totaux:
        return "0"
    return " + ".join(f"{montant} {devise}".strip() for devise, montant in totaux.items())


def formater_message_relance(ecole, inscription, details, totaux, parent_nom=""):
    eleve = inscription.eleve
    parent = (parent_nom or "").strip() or "Parent"
    lignes_frais = [
        f"- {d['libelle']} : {d['reste']} {d['devise']}".strip()
        for d in details
    ]
    return (
        f"Rappel minerval — {ecole.ecole}\n"
        f"Bonjour {parent},\n"
        f"Minerval dû pour {eleve.prenom} {eleve.nom} ({inscription.classe.classe}) :\n"
        + "\n".join(lignes_frais)
        + f"\nTotal minerval dû : {formater_totaux(totaux)}.\n"
        f"Merci de régulariser à la caisse de l'établissement."
    )


def _details_et_totaux(dus):
    totaux = defaultdict(lambda: Decimal("0"))
    details = []
    for d in dus:
        frais = d["frais"]
        code = _code_devise(frais)
        reste = d["reste"]
        totaux[code] += reste
        details.append({
            "libelle": str(frais.type_frais),
            "reste": reste,
            "devise": code,
        })
    return details, dict(totaux)


def lister_dettes(ecole, annee=None):
    """Inscriptions dont le minerval n'est pas soldé (autres frais ignorés)."""
    if annee is None:
        annee = Annee_Scolaire.objects.filter(est_encoure=True).first()
    if not ecole or not annee:
        return [], annee

    config = ConfigWhatsApp.charger_pour_ecole(ecole)
    indicatif = getattr(config, "indicatif_pays", None) or "243"
    inscriptions = (
        Inscription.objects.filter(classe__ecole=ecole, annee_s=annee)
        .select_related("eleve", "eleve__titeur", "classe", "classe__section")
        .order_by("classe__classe", "eleve__nom", "eleve__prenom")
    )
    lignes = []
    for ins in inscriptions:
        dus = [
            d for d in frais_disponibles_pour_inscription(ecole, ins)
            if est_type_frais_minerval(d["frais"].type_frais)
        ]
        if not dus:
            continue
        tuteur = getattr(ins.eleve, "titeur", None)
        tel_brut = (getattr(tuteur, "telephone", None) or "") if tuteur else ""
        telephone = normaliser_telephone(tel_brut, indicatif)
        parent_nom = ""
        if tuteur:
            parent_nom = f"{tuteur.prenom} {tuteur.nom}".strip()
        details, totaux = _details_et_totaux(dus)
        lignes.append({
            "inscription": ins,
            "eleve": ins.eleve,
            "tuteur": tuteur,
            "parent_nom": parent_nom,
            "telephone": telephone,
            "tel_brut": tel_brut,
            "dus": details,
            "totaux": totaux,
            "totaux_affiche": formater_totaux(totaux),
            "nb_frais": len(details),
            "peut_envoyer": bool(telephone),
            "message": formater_message_relance(
                ecole, ins, details, totaux, parent_nom=parent_nom
            ),
        })
    return lignes, annee


def envoyer_relance(ecole, ligne, config=None):
    """Envoie un WhatsApp de relance pour une ligne de dette. Retourne (ok, erreur)."""
    if config is None:
        config = ConfigWhatsApp.charger_pour_ecole(ecole)
    if not config or not config.actif:
        return False, "WhatsApp inactif pour cette école."
    telephone = ligne.get("telephone")
    if not telephone:
        return False, "Numéro du tuteur manquant."

    inscription = ligne["inscription"]
    message = ligne.get("message") or formater_message_relance(
        ecole, inscription, ligne["dus"], ligne["totaux"], ligne.get("parent_nom") or ""
    )
    recap_frais = ", ".join(f"{d['libelle']} {d['reste']} {d['devise']}" for d in ligne["dus"][:4])
    from django.utils import timezone

    date_str = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
    contexte = {
        "parent": ligne.get("parent_nom") or "Parent",
        "eleve": f"{inscription.eleve.prenom} {inscription.eleve.nom}",
        "classe": str(inscription.classe.classe),
        "ecole": ecole.ecole,
        "numero_recu": f"MINERVAL-{inscription.pk}",
        "frais": recap_frais[:60] or "Minerval",
        "montant_affiche": ligne.get("totaux_affiche") or formater_totaux(ligne["totaux"]),
        "date": date_str,
        "mode": "Relance minerval",
    }
    canal = provider_effectif(config)
    if canal == "META":
        from finances.whatsapp import envoyer_relance_meta, langue_template, nom_template

        journal = (
            f"Template Meta : {nom_template(config, 'relance')} ({langue_template(config)})\n"
            f"ecole={contexte['ecole']}\nparent={contexte['parent']}\n"
            f"eleve={contexte['eleve']}\nclasse={contexte['classe']}\n"
            f"frais={contexte['frais']}\nmontant={contexte['montant_affiche']}"
        )
        ok, reponse, erreur = envoyer_relance_meta(config, contexte, telephone)
        message_journal = journal
    else:
        ok, reponse, erreur = _envoyer_via_provider(
            config, telephone, message, contexte=contexte
        )
        message_journal = message[:2000]

    NotificationWhatsApp.objects.create(
        ecole=ecole,
        paiement=None,
        destinataire=f"+{telephone}",
        message=message_journal[:2000],
        statut="ENVOYE" if ok else "ECHEC",
        provider=canal,
        reponse_api=(reponse or "")[:240],
        erreur=erreur or "",
    )
    return ok, erreur or ""


def relancer_dettes(ecole, lignes=None, inscription_id=None):
    """
    Envoie les relances. Si inscription_id est fourni, une seule fiche.
    Retourne {envoyes, echecs, ignores, erreurs}.
    """
    config = ConfigWhatsApp.charger_pour_ecole(ecole)
    if not config or not config.actif:
        return {
            "envoyes": 0,
            "echecs": 0,
            "ignores": 0,
            "erreurs": ["WhatsApp n'est pas actif pour cette école."],
        }
    if lignes is None:
        lignes, _ = lister_dettes(ecole)
    if inscription_id:
        lignes = [l for l in lignes if l["inscription"].pk == int(inscription_id)]

    stats = {"envoyes": 0, "echecs": 0, "ignores": 0, "erreurs": []}
    for ligne in lignes:
        if not ligne.get("peut_envoyer"):
            stats["ignores"] += 1
            continue
        ok, erreur = envoyer_relance(ecole, ligne, config=config)
        if ok:
            stats["envoyes"] += 1
        else:
            stats["echecs"] += 1
            if erreur:
                dest = ligne.get("telephone") or "?"
                stats["erreurs"].append(f"+{dest} : {erreur}")
    return stats
