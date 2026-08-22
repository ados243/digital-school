#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Génère le Manuel d'utilisation Digital School (PDF).

Usage :
    python docs/generer_manuel_utilisation.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT = BASE_DIR / "Manuel_Utilisation_Digital_School.pdf"

pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))

PRIMARY = colors.HexColor("#1e3a5f")
ACCENT = colors.HexColor("#0077C5")
LIGHT = colors.HexColor("#f1f5f9")
MUTED = colors.HexColor("#64748b")
AMBER = colors.HexColor("#b45309")


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", fontName="Arial-Bold", fontSize=28, leading=34, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="CoverSub", fontName="Arial", fontSize=13, leading=18, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="H1", fontName="Arial-Bold", fontSize=16, leading=20, textColor=PRIMARY, spaceBefore=18, spaceAfter=10))
    styles.add(ParagraphStyle(name="H2", fontName="Arial-Bold", fontSize=12.5, leading=16, textColor=ACCENT, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle(name="H3", fontName="Arial-Bold", fontSize=11, leading=14, textColor=PRIMARY, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Body", fontName="Arial", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6))
    styles.add(ParagraphStyle(name="BulletBody", fontName="Arial", fontSize=10, leading=13, leftIndent=4, spaceAfter=2))
    styles.add(ParagraphStyle(name="Tip", fontName="Arial-Italic", fontSize=9.5, leading=13, textColor=AMBER, leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=8, backColor=colors.HexColor("#fffbeb"), borderPadding=6))
    styles.add(ParagraphStyle(name="TOC", fontName="Arial", fontSize=11, leading=18, textColor=PRIMARY, leftIndent=10))
    styles.add(ParagraphStyle(name="TableCell", fontName="Arial", fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="TableHeader", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=colors.white))
    styles.add(ParagraphStyle(name="Step", fontName="Arial", fontSize=10, leading=14, leftIndent=14, spaceAfter=3))
    return styles


def bullets(items, styles):
    return ListFlowable(
        [ListItem(Paragraph(i, styles["BulletBody"]), leftIndent=12, bulletColor=ACCENT) for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=15,
        bulletFontName="Arial",
        bulletFontSize=10,
        spaceBefore=2,
        spaceAfter=8,
    )


def info_table(rows, styles, col_widths=None):
    data = [[Paragraph(c, styles["TableHeader"]) for c in rows[0]]]
    for row in rows[1:]:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=8)


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    page = canvas.getPageNumber()
    if page > 1:
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Digital School — Manuel d'utilisation  |  Page {page}")
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.restoreState()


def etapes(story, styles, items):
    for i, step in enumerate(items, 1):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))


def build():
    styles = make_styles()
    story = []
    W = A4[0] - 4 * cm

    # ========== COUVERTURE ==========
    story.append(Spacer(1, 3.2 * cm))
    story.append(Paragraph("DIGITAL SCHOOL", styles["CoverTitle"]))
    story.append(hr())
    story.append(Paragraph("Manuel d'utilisation", styles["CoverTitle"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Guide pratique pour piloter un établissement :<br/>"
        "inscriptions, pédagogie, finances, ressources humaines et portails.",
        styles["CoverSub"],
    ))
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph(
        "Logiciel édité par NTT S.A.R.L — NTOBO'S TECHNOLOGY<br/>"
        "République Démocratique du Congo",
        styles["CoverSub"],
    ))
    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph("Version 2.0 — août 2026", styles["CoverSub"]))
    story.append(Paragraph("À remettre à la direction, la caisse, le secrétariat, le corps professoral et les familles.", styles["CoverSub"]))
    story.append(PageBreak())

    # ========== SOMMAIRE ==========
    story.append(Paragraph("Sommaire", styles["H1"]))
    story.append(hr())
    for item in [
        "1. Présentation",
        "2. Connexion, comptes et profil",
        "3. Rôles et droits d'accès",
        "4. Navigation",
        "5. Inscriptions &amp; élèves",
        "6. Pédagogie &amp; classes",
        "7. Finances &amp; paiements",
        "8. Ressources humaines (GRH)",
        "9. Portail enseignant",
        "10. Portail parent",
        "11. Portail élève",
        "12. Procédures pas à pas",
        "13. Bonnes pratiques et incidents courants",
        "14. Glossaire",
    ]:
        story.append(Paragraph(item, styles["TOC"]))
    story.append(PageBreak())

    # ========== 1 ==========
    story.append(Paragraph("1. Présentation", styles["H1"]))
    story.append(hr())
    story.append(Paragraph(
        "<b>Digital School</b> centralise la vie d'un établissement scolaire congolais : "
        "dossiers élèves, bulletins RDC, caisse (CDF et USD), paie du personnel, "
        "cours en ligne, visioconférence et messages aux familles. "
        "Chaque compte est rattaché à <b>une école</b> : les données des autres établissements restent invisibles.",
        styles["Body"],
    ))
    story.append(Paragraph("1.1 Publics concernés", styles["H2"]))
    story.append(bullets([
        "<b>Direction / Manager</b> — pilotage de l'établissement",
        "<b>Secrétariat</b> — tuteurs, élèves, inscriptions, classes",
        "<b>Direction des études</b> — matières, périodes, emploi du temps, affectations",
        "<b>Caisse / Trésorerie</b> — frais, encaissements, budget, relances, paie",
        "<b>Préfet / GRH</b> — personnel, contrats, congés, pointage",
        "<b>Enseignants</b> — notes, appel, cours, visio, ressources, messages",
        "<b>Parents / tuteurs</b> — scolarité, frais, Mobile Money, annonces",
        "<b>Élèves</b> — notes, cours en ligne, visio, fichiers partagés",
    ], styles))
    story.append(Paragraph("1.2 Modules", styles["H2"]))
    story.append(info_table(
        [
            ["Module", "Contenu"],
            ["Inscriptions", "Tuteurs, élèves, inscriptions, classes, communications direction"],
            ["Pédagogie", "Matières, périodes bulletin RDC, affectations, emploi du temps"],
            ["Finances", "Frais, caisse, budget, relances WhatsApp, Mobile Money, HOADA, salaires"],
            ["GRH", "Personnel, contrats, congés, pointage, génération des paies"],
            ["Portails", "Espaces enseignant, parent et élève (Mon espace)"],
        ],
        styles,
        col_widths=[4.2 * cm, W - 4.2 * cm],
    ))
    story.append(Spacer(1, 0.35 * cm))
    story.append(Paragraph(
        "Ce manuel décrit l'écran tel qu'il apparaît à l'utilisateur. "
        "Certaines options (WhatsApp, visioconférence, paiement mobile) dépendent de la configuration de l'école.",
        styles["Tip"],
    ))

    # ========== 2 ==========
    story.append(Paragraph("2. Connexion, comptes et profil", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("2.1 Se connecter", styles["H2"]))
    story.append(Paragraph(
        "Ouvrez l'adresse fournie par l'école, puis la page <b>Connexion</b>. "
        "Saisissez identifiant et mot de passe. Après validation, vous êtes dirigé vers l'écran de votre métier.",
        styles["Body"],
    ))
    story.append(info_table(
        [
            ["Profil", "Écran d'arrivée"],
            ["Parent / Élève", "Mon espace"],
            ["Enseignant / Professeur", "Espace enseignant"],
            ["Caissier", "Liste des paiements"],
            ["Trésorier", "Tableau de bord Finances"],
            ["Direction des études", "Synthèse Pédagogie"],
            ["Secrétaire", "Synthèse Inscriptions"],
            ["Préfet", "Synthèse GRH"],
            ["Directeur / Manager", "Tableau de bord Finances (vue large)"],
        ],
        styles,
        col_widths=[6 * cm, W - 6 * cm],
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("2.2 Créer un compte (auto-inscription)", styles["H2"]))
    story.append(Paragraph(
        "Sur <b>Créer un compte</b>, choisissez le profil Parent, Élève ou Corps professoral, "
        "sélectionnez l'établissement actif, puis saisissez le <b>matricule</b> déjà enregistré par l'école.",
        styles["Body"],
    ))
    story.append(info_table(
        [
            ["Profil", "Matricule", "Préfixe"],
            ["Parent / tuteur", "Fiche tuteur existante", "TUT-…"],
            ["Élève", "Fiche élève existante", "ELV-…"],
            ["Enseignant", "Fiche personnel existante", "PER-…"],
        ],
        styles,
        col_widths=[4.5 * cm, 7.5 * cm, 4 * cm],
    ))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph(
        "Les comptes Direction, Caissier, Trésorier, Secrétaire et Préfet sont créés par l'administration, "
        "pas depuis la page publique. La fiche métier (élève, tuteur ou personnel) doit exister <b>avant</b> le compte.",
        styles["Tip"],
    ))
    story.append(Paragraph("2.3 Mot de passe oublié", styles["H2"]))
    story.append(Paragraph(
        "Sur la page de connexion, cliquez sur <b>Mot de passe oublié</b>. "
        "Saisissez votre identifiant ou votre numéro WhatsApp. Un code est envoyé sur WhatsApp. "
        "Saisissez ce code, puis choisissez un nouveau mot de passe.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Le numéro WhatsApp doit être renseigné sur le compte (profil) ou sur la fiche tuteur / personnel. "
        "Sans numéro, la récupération automatique n'est pas possible : contactez l'école.",
        styles["Tip"],
    ))
    story.append(Paragraph("2.4 Mon profil", styles["H2"]))
    story.append(Paragraph(
        "Dans la barre du haut, menu <b>Compte → Mon profil</b> : photo, prénom, numéro WhatsApp, changement de mot de passe. "
        "Déconnectez-vous après usage d'un poste partagé.",
        styles["Body"],
    ))

    # ========== 3 ==========
    story.append(Paragraph("3. Rôles et droits d'accès", styles["H1"]))
    story.append(hr())
    story.append(info_table(
        [
            ["Rôle", "Peut surtout", "Ne peut pas (en général)"],
            ["Manager / Directeur", "Piloter tous les modules de l'école", "—"],
            ["Secrétaire", "Élèves, tuteurs, inscriptions, classes", "Finances, paie, notes"],
            ["Directeur des études", "Matières, périodes, EDT, classes", "Caisse et GRH complet"],
            ["Trésorier", "Frais, budget, paiements, HOADA, salaires", "Modifier un reçu déjà validé sans procédure"],
            ["Caissier", "Encaisser, relancer, clôturer la journée", "Modifier ou supprimer un paiement validé"],
            ["Préfet", "Consulter largement ; écrire surtout en GRH", "Saisir la caisse"],
            ["Promoteur (fonction GRH)", "Consulter", "Modifier (sauf son profil)"],
            ["Enseignant", "Portail : classes, notes, cours, visio", "Back-office inscriptions / caisse"],
            ["Parent", "Ses enfants, frais, messages, annonces", "Les autres familles"],
            ["Élève", "Ses notes, cours, visio, fichiers", "Les dossiers des camarades"],
        ],
        styles,
        col_widths=[4.2 * cm, 6.4 * cm, 5.4 * cm],
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Un professeur dont la fiche GRH a la fonction <b>Caissier</b> peut encaisser, même si son compte est « Enseignant ». "
        "La fonction GRH (Directeur, Préfet, etc.) affine aussi les menus.",
        styles["Tip"],
    ))

    # ========== 4 ==========
    story.append(Paragraph("4. Navigation", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("4.1 Barre d'applications", styles["H2"]))
    story.append(Paragraph(
        "En haut de l'écran, une barre affiche le logo Digital School et les applications de votre métier. "
        "Cliquez une icône : un menu déroulant liste les écrans (ex. Paiements → Encaisser). "
        "Le fil d'Ariane sous le titre permet de revenir en arrière.",
        styles["Body"],
    ))
    story.append(Paragraph("4.2 Back-office (personnel administratif)", styles["H2"]))
    story.append(bullets([
        "<b>Inscriptions</b> — synthèse, fiches élèves, tuteurs, inscriptions, classes, communications",
        "<b>Pédagogie</b> — synthèse, matières, périodes bulletin, emploi du temps, classes",
        "<b>Finances</b> — synthèse, frais, budget, paiements, relances, clôture, salaires, HOADA, taux, WhatsApp",
        "<b>GRH</b> — personnel, contrats, congés, présences, rémunération",
        "<b>Compte</b> — profil et déconnexion",
    ], styles))
    story.append(Paragraph("4.3 Portail (Mon espace)", styles["H2"]))
    story.append(Paragraph(
        "Parents, élèves et enseignants n'utilisent pas les mêmes menus. "
        "L'enseignant voit notamment Classes, Cours, Ressources, Messages, Présences, Travaux. "
        "L'élève voit Espace, Cours, Ressources. Le parent voit Enfants, Annonces, Messages.",
        styles["Body"],
    ))

    # ========== 5 ==========
    story.append(Paragraph("5. Inscriptions &amp; élèves", styles["H1"]))
    story.append(hr())
    story.append(Paragraph(
        "Cycle habituel : tuteur → élève → inscription dans une classe pour l'année en cours.",
        styles["Body"],
    ))
    story.append(Paragraph("5.1 Écrans", styles["H2"]))
    story.append(info_table(
        [
            ["Écran", "Utilité"],
            ["Synthèse", "Effectifs, accès rapides"],
            ["Fiches élèves", "Créer / modifier un élève (photo, sexe, tuteur, quartier)"],
            ["Tuteurs", "Liste et fiches parents (matricule TUT-…, téléphone WhatsApp)"],
            ["Inscriptions", "Lier un élève à une classe et une année"],
            ["Classes &amp; salles", "Section, capacité, titulaire, salle"],
            ["Communications parents", "Annonces de la direction (une famille, une classe, une section ou toute l'école)"],
        ],
        styles,
        col_widths=[5.5 * cm, W - 5.5 * cm],
    ))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("5.2 Nouveau tuteur depuis la fiche élève", styles["H2"]))
    story.append(Paragraph(
        "Lors de la création d'un élève, vous pouvez ouvrir une fenêtre <b>Nouveau tuteur</b> "
        "(identité, coordonnées, lien de parenté) sans quitter le formulaire. "
        "Le tuteur est alors disponible immédiatement pour rattacher l'élève.",
        styles["Body"],
    ))
    story.append(Paragraph("5.3 Types d'inscription", styles["H2"]))
    story.append(bullets([
        "<b>Nouvelle</b> — première inscription dans l'établissement",
        "<b>Réinscription</b> — poursuite l'année suivante",
        "<b>Transfert</b> — arrivée depuis un autre établissement",
    ], styles))
    story.append(Paragraph(
        "Un bulletin scolaire est préparé automatiquement à l'inscription. "
        "Communiquez ensuite les matricules TUT / ELV aux familles pour qu'elles créent leur compte.",
        styles["Tip"],
    ))

    # ========== 6 ==========
    story.append(Paragraph("6. Pédagogie &amp; classes", styles["H1"]))
    story.append(hr())
    story.append(Paragraph(
        "Le référentiel suit les cycles RDC (maternelle, primaire, CTEB / secondaire, humanités) "
        "et le bulletin avec travaux journaliers (TJ) et examens de division.",
        styles["Body"],
    ))
    story.append(Paragraph("6.1 Matières", styles["H2"]))
    story.append(Paragraph(
        "Pour chaque matière : code, libellé, coefficient, maxima TJ par période, section, "
        "et éventuellement un enseignant de référence (surtout au secondaire). "
        "Au primaire et en maternelle, le <b>titulaire de classe</b> assure les cours sauf affectation contraire.",
        styles["Body"],
    ))
    story.append(Paragraph("6.2 Périodes bulletin", styles["H2"]))
    story.append(Paragraph(
        "Les trimestres ou semestres (divisions) et leurs périodes se paramètrent ici. "
        "Marquez la période ou la division <b>en cours</b> pour autoriser la saisie des notes. "
        "Une seule période « en cours » par cycle à la fois.",
        styles["Body"],
    ))
    story.append(Paragraph("6.3 Enseignants de la classe", styles["H2"]))
    story.append(Paragraph(
        "Depuis une classe : affectez un professeur à une matière (remplace le titulaire ou l'enseignant de référence). "
        "Vous pouvez rétablir le défaut ensuite.",
        styles["Body"],
    ))
    story.append(Paragraph("6.4 Emploi du temps", styles["H2"]))
    story.append(Paragraph(
        "Choisissez une classe, puis ajoutez des créneaux (jour, heures, matière, enseignant, salle). "
        "Supprimez un créneau s'il n'est plus valable.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Les notes, appels et bulletins se saisissent surtout depuis le <b>portail enseignant</b>, pas depuis ce module.",
        styles["Tip"],
    ))

    # ========== 7 ==========
    story.append(Paragraph("7. Finances &amp; paiements", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("7.1 Tableau de bord", styles["H2"]))
    story.append(Paragraph(
        "La synthèse affiche la caisse (par devise), les paiements validés, les dépenses (dont salaires), "
        "les entrées et sorties du jour / de la semaine / du mois, un aperçu du minerval par classe et les derniers encaissements.",
        styles["Body"],
    ))
    story.append(Paragraph("7.2 Types de frais et barèmes", styles["H2"]))
    story.append(Paragraph(
        "Créez d'abord les <b>types</b> (Minerval, Inscription, Uniforme…). "
        "Puis un <b>frais scolaire</b> : année, montant, devise (CDF ou USD), échéance, obligatoire ou non.",
        styles["Body"],
    ))
    story.append(Paragraph("Portée du barème :", styles["Body"]))
    story.append(bullets([
        "<b>Toute une section</b> — ex. tout le primaire",
        "<b>Une ou plusieurs classes</b> — cochez uniquement les classes concernées (laboratoire, examen d'une filière, etc.)",
    ], styles))
    story.append(Paragraph("7.3 Encaisser (caissier)", styles["H2"]))
    story.append(bullets([
        "Paiements → <b>Encaisser un paiement</b>",
        "Rechercher l'élève (nom, matricule, classe)",
        "Choisir le frais dû, le montant, la devise et le mode (Espèces, Mobile Money, Virement, Chèque)",
        "Valider : un reçu <b>REC-AAAA-MM-####</b> est généré ; impression possible",
        "Un message WhatsApp de confirmation peut partir au parent si WhatsApp est configuré",
    ], styles))
    story.append(Paragraph(
        "Le caissier ne peut ni modifier ni supprimer un paiement validé. "
        "Pour une erreur, il ouvre une <b>demande de correction</b> ; un responsable la traite.",
        styles["Tip"],
    ))
    story.append(Paragraph("7.4 Mobile Money (parent)", styles["H2"]))
    story.append(Paragraph(
        "Le parent peut initier un paiement depuis Mon espace (USSD Airtel, Orange, M-Pesa selon l'école). "
        "Le paiement apparaît <b>en attente</b>. La caisse le <b>confirme</b> après vérification de l'opérateur. "
        "Tant qu'il n'est pas confirmé, il ne compte pas comme encaissé.",
        styles["Body"],
    ))
    story.append(Paragraph("7.5 Relances d'impayés", styles["H2"]))
    story.append(Paragraph(
        "Finances → <b>Relances minerval</b> : liste des familles en retard. "
        "Envoi groupé ou ciblé de messages WhatsApp. Un journal évite de relancer trop souvent le même parent.",
        styles["Body"],
    ))
    story.append(Paragraph("7.6 Clôture de journée", styles["H2"]))
    story.append(Paragraph(
        "En fin de service, le caissier ouvre <b>Clôture de journée</b>, vérifie les totaux par devise et mode, "
        "puis confirme. Cela fige le bilan du jour pour le contrôle.",
        styles["Body"],
    ))
    story.append(Paragraph("7.7 Budget annuel", styles["H2"]))
    story.append(Paragraph(
        "Finances → <b>Budget</b> : prévisions automatiques (capacité des classes × barèmes, charges) "
        "puis fixation du budget. Le suivi compare le <b>budgété</b> et le <b>réalisé</b> "
        "(encaissements élèves + salaires et autres charges). Export Excel possible.",
        styles["Body"],
    ))
    story.append(Paragraph("7.8 Taux de change et WhatsApp", styles["H2"]))
    story.append(bullets([
        "<b>Taux CDF ↔ USD</b> — à tenir à jour pour les conversions à l'encaissement",
        "<b>WhatsApp central</b> — réservé à l'administrateur plateforme (identifiants du prestataire). L'école utilise ensuite les reçus et relances sans retaper les clés",
    ], styles))
    story.append(Paragraph("7.9 Payer le personnel", styles["H2"]))
    story.append(Paragraph(
        "Après génération des fiches en GRH : Finances → <b>Payer le personnel</b>. "
        "Paiement unitaire ou par lot. Les salaires payés alimentent les dépenses du tableau de bord et la comptabilité.",
        styles["Body"],
    ))
    story.append(Paragraph("7.10 Comptabilité HOADA", styles["H2"]))
    story.append(bullets([
        "Plan comptable, journaux, écritures manuelles",
        "Grand livre et balance",
        "Les paiements élèves <b>VALIDÉS</b> et les salaires <b>PAYÉS</b> peuvent produire des écritures automatiquement",
    ], styles))

    # ========== 8 ==========
    story.append(Paragraph("8. Ressources humaines (GRH)", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("8.1 Personnel", styles["H2"]))
    story.append(Paragraph(
        "Fiche : identité, quartier, téléphone (jusqu'à 13 chiffres, ex. 243…), e-mail, fonction "
        "(Directeur, Préfet, Enseignant, Caissier, etc.), photo. "
        "Le matricule <b>PER-……</b> est attribué à l'enregistrement. "
        "Le compte de connexion se crée ensuite via l'inscription « Corps professoral » avec ce matricule.",
        styles["Body"],
    ))
    story.append(Paragraph("8.2 Contrats", styles["H2"]))
    story.append(Paragraph(
        "Un <b>seul contrat par personne</b> dans l'établissement. "
        "À la création, choisissez le membre du personnel : le libellé affiche aussi sa <b>fonction</b> "
        "(ex. Jean Mbala — Enseignant). Type (CDI, CDD, Prestataire, Stage), dates, salaire de base, devise, statut.",
        styles["Body"],
    ))
    story.append(Paragraph("8.3 Congés", styles["H2"]))
    story.append(Paragraph("Enregistrez la demande, puis <b>Approuver</b> ou <b>Rejeter</b>.", styles["Body"]))
    story.append(Paragraph("8.4 Pointage du personnel", styles["H2"]))
    story.append(Paragraph(
        "Pointez l'arrivée, éventuellement le départ, ou un statut Absent / Retard. "
        "La liste du jour distingue les agents déjà arrivés et ceux encore à pointer.",
        styles["Body"],
    ))
    story.append(Paragraph("8.5 Paie", styles["H2"]))
    story.append(bullets([
        "Générer les fiches pour un mois (à partir des contrats actifs)",
        "Consulter le bulletin (base, primes, déductions, net)",
        "Marquer payé depuis GRH ou depuis Finances → Payer le personnel",
    ], styles))

    # ========== 9 ==========
    story.append(Paragraph("9. Portail enseignant", styles["H1"]))
    story.append(hr())
    story.append(Paragraph(
        "Menu typique : <b>Classes</b>, <b>Cours</b>, <b>Ressources</b>, <b>Messages</b>, <b>Présences</b>, <b>Travaux</b>.",
        styles["Body"],
    ))
    story.append(Paragraph("9.1 Mes classes", styles["H2"]))
    story.append(Paragraph(
        "Cartes des classes dont vous êtes titulaire ou où vous enseignez une matière. "
        "Ouvrez une classe pour la liste des élèves, l'évolution, les bulletins (titulaire), l'appel, "
        "un raccourci visio ou le partage d'un fichier.",
        styles["Body"],
    ))
    story.append(Paragraph("9.2 Travaux cotés et notes", styles["H2"]))
    story.append(bullets([
        "Créer un travail : classe, matière, type (devoir, interrogation, examen…), date, barème, période ou division",
        "Un examen de fin de trimestre / semestre se rattache à la <b>division</b>",
        "Saisir les notes élève par élève ; une note déjà enregistrée peut être verrouillée",
        "Consulter l'<b>évolution</b> de la classe et les <b>bulletins</b> (titulaire)",
    ], styles))
    story.append(Paragraph("9.3 Présences élèves", styles["H2"]))
    story.append(Paragraph(
        "Seul le <b>titulaire</b> fait l'appel quotidien (Présent, Absent, Retard, Excusé) et consulte le récapitulatif.",
        styles["Body"],
    ))
    story.append(Paragraph("9.4 Cours en ligne (leçons)", styles["H2"]))
    story.append(Paragraph(
        "Cours → cours enregistrés : créez un parcours (titre, matière, <b>plusieurs classes</b> si vous donnez le même cours, "
        "niveau, couverture). Ajoutez des chapitres puis des sous-chapitres (texte, vidéo hébergée, PDF). "
        "Publiez lorsque le contenu est prêt : les élèves des classes cochées le voient dans Étudier en ligne.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Les vidéos sont hébergées par l'école (pas YouTube). Taille maximale configurable (souvent 70 Mo par fichier).",
        styles["Tip"],
    ))
    story.append(Paragraph("9.5 Cours en visioconférence", styles["H2"]))
    story.append(bullets([
        "Planifier une séance : titre, matière, <b>une ou plusieurs classes</b>, date et heure, durée",
        "Quand vous êtes prêt : <b>Démarrer</b> — la salle s'ouvre (navigateur)",
        "Les élèves rejoignent lorsque la séance est en cours (ou 15 minutes avant l'horaire prévu)",
        "Pendant le direct : panneau Questions ; vous pouvez répondre ou épingler",
        "Terminer ou annuler la séance ensuite",
    ], styles))
    story.append(Paragraph("9.6 Ressources (fichiers)", styles["H2"]))
    story.append(Paragraph(
        "Espace <b>Ressources</b> : déposez une vidéo, un PDF, une image ou un document Office / ZIP, "
        "cochez les classes, éventuellement une matière, puis publiez. "
        "Les élèves concernés ouvrent ou téléchargent le fichier. Un brouillon reste invisible.",
        styles["Body"],
    ))
    story.append(Paragraph("9.7 Messages", styles["H2"]))
    story.append(Paragraph(
        "Échangez avec le parent d'un élève de votre classe (titulaire). "
        "Le parent écrit aussi depuis son portail.",
        styles["Body"],
    ))

    # ========== 10 ==========
    story.append(Paragraph("10. Portail parent", styles["H1"]))
    story.append(hr())
    story.append(Paragraph(
        "Connexion avec le compte créé via le matricule tuteur. Écrans principaux :",
        styles["Body"],
    ))
    story.append(bullets([
        "<b>Enfants</b> — cartes de suivi : classe, notes, absences, reste à payer",
        "Fiche d'un enfant : détail des frais, lien vers un paiement Mobile Money si proposé",
        "<b>Annonces</b> — communications de la direction (non lues mises en évidence)",
        "<b>Messages</b> — conversation avec le titulaire",
        "<b>Compte</b> — profil et numéro WhatsApp (utile pour reçus et relances)",
    ], styles))
    story.append(Paragraph(
        "Le parent ne voit que ses enfants rattachés à sa fiche tuteur. "
        "En cas d'enfant manquant, le secrétariat doit vérifier le lien tuteur sur la fiche élève.",
        styles["Tip"],
    ))

    # ========== 11 ==========
    story.append(Paragraph("11. Portail élève", styles["H1"]))
    story.append(hr())
    story.append(bullets([
        "<b>Espace</b> — classe, année, dernières notes",
        "<b>Cours</b> — leçons publiées et séances de visioconférence de sa classe",
        "<b>Ressources</b> — fichiers partagés par les enseignants (vidéo, PDF, documents)",
        "Dans une leçon : lecture / vidéo, marquer comme terminé, progression du parcours",
        "Dans une visio : Rejoindre lorsque l'enseignant a démarré (ou dans la fenêtre horaire)",
    ], styles))
    story.append(Paragraph(
        "L'élève n'accède qu'aux contenus de <b>sa</b> classe et de l'année en cours.",
        styles["Tip"],
    ))

    # ========== 12 ==========
    story.append(Paragraph("12. Procédures pas à pas", styles["H1"]))
    story.append(hr())

    story.append(Paragraph("12.1 Inscrire un nouvel élève", styles["H2"]))
    etapes(story, styles, [
        "Vérifier l'année scolaire en cours et l'existence de la classe.",
        "Créer le tuteur (ou le saisir depuis la fiche élève).",
        "Créer l'élève et le rattacher au tuteur.",
        "Inscrire l'élève (classe + année, type d'inscription).",
        "Remettre les matricules TUT et ELV pour les comptes portail.",
    ])

    story.append(Paragraph("12.2 Paramétrer l'année pédagogique", styles["H2"]))
    etapes(story, styles, [
        "Créer ou vérifier les classes (section, titulaire, capacité).",
        "Charger / vérifier les matières de chaque section.",
        "Ouvrir les périodes bulletin et marquer la période en cours.",
        "Affecter les enseignants par matière si besoin.",
        "Saisir l'emploi du temps de chaque classe.",
    ])

    story.append(Paragraph("12.3 Encaisser les frais", styles["H2"]))
    etapes(story, styles, [
        "Types de frais puis barèmes (section entière ou classes ciblées).",
        "Se connecter en caissier.",
        "Encaisser : élève, frais, montant, devise, mode.",
        "Imprimer le reçu ; vérifier l'entrée du jour sur la synthèse.",
        "En fin de journée : clôturer la caisse.",
    ])

    story.append(Paragraph("12.4 Relancer un impayé", styles["H2"]))
    etapes(story, styles, [
        "Finances → Relances minerval.",
        "Contrôler la liste (classe, reste dû, dernier contact).",
        "Envoyer la relance WhatsApp (unitaire ou lot).",
        "Noter le retour du parent ; encaisser dès paiement.",
    ])

    story.append(Paragraph("12.5 Payer les salaires du mois", styles["H2"]))
    etapes(story, styles, [
        "Contrats actifs avec salaire et devise.",
        "GRH → Générer les paies (mois / année).",
        "Finances → Payer le personnel (fiche ou lot).",
        "Contrôler les dépenses du mois sur le dashboard.",
    ])

    story.append(Paragraph("12.6 Saisir les notes d'une période", styles["H2"]))
    etapes(story, styles, [
        "Pédagogie : activer la période (ou division pour un examen).",
        "Enseignant : Travaux → nouveau travail coté.",
        "Saisir les notes, puis consulter bulletin / évolution.",
    ])

    story.append(Paragraph("12.7 Dispenser un cours à distance", styles["H2"]))
    etapes(story, styles, [
        "Cours visio → Nouveau : classes, matière, horaire.",
        "À l'heure : Démarrer ; partager le lien en classe si besoin.",
        "Animer ; répondre aux questions.",
        "Terminer la séance.",
        "Compléter éventuellement par un fichier dans Ressources ou une leçon publiée.",
    ])

    story.append(Paragraph("12.8 Partager un support (PDF / vidéo)", styles["H2"]))
    etapes(story, styles, [
        "Ressources → Partager un fichier.",
        "Titre, classes (plusieurs possibles), matière optionnelle.",
        "Déposer le fichier (PDF, vidéo MP4/WebM, image, document).",
        "Laisser « Visible par les élèves » coché, enregistrer.",
        "Les élèves ouvrent le fichier dans Ressources.",
    ])

    story.append(Paragraph("12.9 Annoncer aux parents", styles["H2"]))
    etapes(story, styles, [
        "Direction → Communications → Nouvelle.",
        "Cible : un parent, une classe, une section ou l'école.",
        "Rédiger et publier.",
        "Les parents voient l'annonce (badge non lu).",
    ])

    # ========== 13 ==========
    story.append(Paragraph("13. Bonnes pratiques et incidents courants", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("13.1 Bonnes pratiques", styles["H2"]))
    story.append(bullets([
        "Paramétrer année, classes et matières avant les inscriptions massives.",
        "Toujours créer le tuteur avant l'élève (sauf fenêtre « nouveau tuteur »).",
        "Compte caissier dédié pour la traçabilité des encaissements.",
        "Vérifier la devise (CDF / USD) à chaque saisie.",
        "Tenir le taux de change à jour.",
        "Ne jamais partager un mot de passe ; se déconnecter sur un poste commun.",
        "Publier un cours ou une ressource seulement lorsqu'elle est complète.",
        "Pour la visio : tester micro et navigateur avant l'heure du cours.",
    ], styles))
    story.append(Paragraph("13.2 Incidents fréquents", styles["H2"]))
    story.append(info_table(
        [
            ["Situation", "Que faire"],
            ["« Matricule introuvable » à l'inscription du compte", "La fiche n'existe pas encore, ou le mauvais établissement est choisi."],
            ["Parent sans enfant dans Mon espace", "Vérifier le tuteur sur la fiche élève et l'inscription de l'année en cours."],
            ["Enseignant sans classes", "Le désigner titulaire ou l'affecter à une matière."],
            ["Impossible de saisir des notes", "Activer la période / division « en cours » ; vérifier classe et matière."],
            ["L'élève ne voit pas le cours ou le fichier", "Le contenu n'est pas publié, ou sa classe n'est pas cochée."],
            ["Visio : l'élève ne peut pas rejoindre", "L'enseignant n'a pas démarré, ou la séance est terminée / annulée."],
            ["Paiement Mobile Money non visible en caisse validée", "Il est « en attente » : le confirmer après le reçu opérateur."],
            ["Pas de reçu WhatsApp", "Numéro manquant sur le tuteur, ou WhatsApp non configuré par l'admin."],
            ["Mot de passe oublié sans SMS WhatsApp", "Renseigner le numéro sur le profil, ou faire réinitialiser par l'école."],
            ["Erreur de montant en caisse", "Demande de correction (le caissier ne modifie pas un reçu validé)."],
        ],
        styles,
        col_widths=[6.2 * cm, W - 6.2 * cm],
    ))

    # ========== 14 ==========
    story.append(Paragraph("14. Glossaire", styles["H1"]))
    story.append(hr())
    story.append(info_table(
        [
            ["Terme", "Définition"],
            ["Matricule", "Identifiant unique : ELV (élève), TUT (tuteur), PER (personnel)"],
            ["Minerval", "Frais de scolarité périodiques"],
            ["Portée d'un frais", "Section entière, ou seulement certaines classes"],
            ["HOADA / SYSCOHADA", "Comptabilité d'entreprise du référentiel OHADA"],
            ["TJ", "Travaux journaliers (évaluation continue)"],
            ["Division", "Trimestre ou semestre du bulletin"],
            ["EXAM.", "Examen de fin de division"],
            ["Bulletin RDC", "Bulletin conforme aux pratiques MEPST"],
            ["CTEB", "Cycle Terminal de l'Éducation de Base"],
            ["Reçu REC-…", "Justificatif d'encaissement"],
            ["Clôture", "Arrêté de caisse de la journée"],
            ["Relance", "Message WhatsApp de rappel d'impayé"],
            ["Cours en ligne", "Parcours de leçons (chapitres) publié aux élèves"],
            ["Ressource", "Fichier isolé (PDF, vidéo…) partagé avec des classes"],
            ["Visio", "Séance synchrone en visioconférence"],
            ["Titulaire", "Professeur responsable de la classe (appel, bulletins)"],
            ["Net à payer", "Salaire après primes et déductions"],
        ],
        styles,
        col_widths=[4.4 * cm, W - 4.4 * cm],
    ))

    story.append(Spacer(1, 1.1 * cm))
    story.append(hr())
    story.append(Paragraph(
        "— Fin du manuel —<br/><br/>"
        "<b>Digital School</b> · Manuel d'utilisation · Version 2.0 · août 2026<br/>"
        "Éditeur : NTT S.A.R.L — NTOBO'S TECHNOLOGY<br/>"
        "Les écrans peuvent légèrement varier selon le rôle et la configuration de l'établissement.",
        styles["CoverSub"],
    ))

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2.2 * cm,
        title="Manuel d'utilisation — Digital School",
        author="NTT S.A.R.L — Digital School",
        subject="Guide utilisateur complet (version 2.0)",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF généré : {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
