#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Génère le Manuel d'utilisation Digital School (PDF)."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
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

# Polices Windows (accents FR)
pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))

PRIMARY = colors.HexColor("#1e3a5f")
ACCENT = colors.HexColor("#2563eb")
LIGHT = colors.HexColor("#f1f5f9")
MUTED = colors.HexColor("#64748b")
AMBER = colors.HexColor("#b45309")


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontName="Arial-Bold",
            fontSize=28,
            leading=34,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSub",
            fontName="Arial",
            fontSize=14,
            leading=20,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1",
            fontName="Arial-Bold",
            fontSize=16,
            leading=20,
            textColor=PRIMARY,
            spaceBefore=18,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2",
            fontName="Arial-Bold",
            fontSize=12.5,
            leading=16,
            textColor=ACCENT,
            spaceBefore=14,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3",
            fontName="Arial-Bold",
            fontSize=11,
            leading=14,
            textColor=PRIMARY,
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            fontName="Arial",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletBody",
            fontName="Arial",
            fontSize=10,
            leading=13,
            leftIndent=4,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Tip",
            fontName="Arial-Italic",
            fontSize=9.5,
            leading=13,
            textColor=AMBER,
            leftIndent=8,
            rightIndent=8,
            spaceBefore=4,
            spaceAfter=8,
            backColor=colors.HexColor("#fffbeb"),
            borderPadding=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Footer",
            fontName="Arial",
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TOC",
            fontName="Arial",
            fontSize=11,
            leading=18,
            textColor=PRIMARY,
            leftIndent=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            fontName="Arial",
            fontSize=8.5,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            fontName="Arial-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Step",
            fontName="Arial",
            fontSize=10,
            leading=14,
            leftIndent=14,
            spaceAfter=3,
        )
    )
    return styles


def bullets(items, styles):
    return ListFlowable(
        [
            ListItem(Paragraph(i, styles["BulletBody"]), leftIndent=12, bulletColor=ACCENT)
            for i in items
        ],
        bulletType="bullet",
        start="•",
        leftIndent=15,
        bulletFontName="Arial",
        bulletFontSize=10,
        spaceBefore=2,
        spaceAfter=8,
    )


def info_table(rows, styles, col_widths=None):
    data = []
    header = [Paragraph(c, styles["TableHeader"]) for c in rows[0]]
    data.append(header)
    for row in rows[1:]:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def hr():
    return HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceBefore=4, spaceAfter=8)


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(MUTED)
    page = canvas.getPageNumber()
    if page > 1:
        canvas.drawCentredString(
            A4[0] / 2,
            1.2 * cm,
            f"Digital School — Manuel d'utilisation  |  Page {page}",
        )
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.restoreState()


def build():
    styles = make_styles()
    story = []
    W = A4[0] - 4 * cm

    # ========== COUVERTURE ==========
    story.append(Spacer(1, 3.5 * cm))
    story.append(Paragraph("DIGITAL SCHOOL", styles["CoverTitle"]))
    story.append(hr())
    story.append(Paragraph("Manuel d'utilisation", styles["CoverTitle"]))
    story.append(Spacer(1, 0.6 * cm))
    story.append(
        Paragraph(
            "Guide complet pour la gestion scolaire :<br/>inscriptions, pédagogie, finances, ressources humaines et portails.",
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 1.5 * cm))
    story.append(
        Paragraph(
            "Logiciel de gestion d'établissements scolaires<br/>République Démocratique du Congo",
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 2.5 * cm))
    story.append(Paragraph("Version 1.0 — Août 2026", styles["CoverSub"]))
    story.append(Paragraph("Document destiné aux utilisateurs de Digital School", styles["CoverSub"]))
    story.append(PageBreak())

    # ========== SOMMAIRE ==========
    story.append(Paragraph("Sommaire", styles["H1"]))
    story.append(hr())
    toc = [
        "1. Présentation du logiciel",
        "2. Premiers pas : connexion et comptes",
        "3. Rôles et droits d'accès",
        "4. Navigation générale",
        "5. Module Inscriptions &amp; Élèves",
        "6. Module Pédagogie &amp; Classes",
        "7. Module Finances &amp; Paiements",
        "8. Module Ressources Humaines (GRH)",
        "9. Portail enseignant",
        "10. Portail parent",
        "11. Portail élève",
        "12. Procédures métier pas à pas",
        "13. Conseils et bonnes pratiques",
        "14. Glossaire",
    ]
    for item in toc:
        story.append(Paragraph(item, styles["TOC"]))
    story.append(PageBreak())

    # ========== 1 ==========
    story.append(Paragraph("1. Présentation du logiciel", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "<b>Digital School</b> est une plateforme de gestion scolaire conçue pour les établissements "
            "de la République Démocratique du Congo (écoles publiques, privées ou conventionnées). "
            "Elle centralise les inscriptions, le suivi pédagogique (notes, bulletins, présences), "
            "la trésorerie (frais scolaires, salaires), la comptabilité HOADA et la gestion du personnel.",
            styles["Body"],
        )
    )
    story.append(Paragraph("1.1 À qui s'adresse le logiciel ?", styles["H2"]))
    story.append(
        bullets(
            [
                "<b>Direction / Administration</b> — pilotage global de l'établissement",
                "<b>Caissier / Trésorerie</b> — encaissement des frais scolaires",
                "<b>Service RH</b> — personnel, contrats, congés, paie",
                "<b>Enseignants</b> — classes, notes, présences, cours en ligne",
                "<b>Parents / Tuteurs</b> — suivi des enfants, frais, messages",
                "<b>Élèves</b> — scolarité, notes, cours en ligne",
            ],
            styles,
        )
    )
    story.append(Paragraph("1.2 Modules principaux", styles["H2"]))
    story.append(
        info_table(
            [
                ["Module", "Fonction"],
                ["Inscriptions &amp; Élèves", "Fiches élèves, tuteurs, inscriptions, classes, communications"],
                ["Pédagogie &amp; Classes", "Matières, périodes, affectations, bulletins RDC"],
                ["Finances &amp; Paiements", "Frais, encaissements, salaires, comptabilité HOADA"],
                ["Ressources Humaines", "Personnel, contrats, congés, pointage, paie"],
                ["Portails", "Espaces dédiés parents, élèves et enseignants"],
            ],
            styles,
            col_widths=[5.5 * cm, W - 5.5 * cm],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            "<b>Multi-écoles :</b> chaque utilisateur est rattaché à un établissement. "
            "Les données (élèves, paiements, personnel, etc.) sont isolées par école.",
            styles["Tip"],
        )
    )

    # ========== 2 ==========
    story.append(Paragraph("2. Premiers pas : connexion et comptes", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("2.1 Se connecter", styles["H2"]))
    story.append(
        Paragraph(
            "Ouvrez l'adresse du logiciel fournie par votre établissement, puis allez sur la page "
            "<b>Connexion</b>. Saisissez votre identifiant et votre mot de passe, puis validez.",
            styles["Body"],
        )
    )
    story.append(Paragraph("Après connexion, vous êtes redirigé selon votre profil :", styles["Body"]))
    story.append(
        bullets(
            [
                "Parent / Élève → <b>Mon espace</b>",
                "Caissier → <b>Liste des paiements</b>",
                "Enseignant / Professeur → <b>Espace enseignant</b>",
                "Direction / Manager / autres rôles internes → <b>Tableau de bord GRH</b>",
            ],
            styles,
        )
    )
    story.append(Paragraph("2.2 Créer un compte (auto-inscription)", styles["H2"]))
    story.append(
        Paragraph(
            "Sur la page <b>Créer un compte</b>, choisissez votre profil (<i>Parent</i>, <i>Élève</i> ou "
            "<i>Corps professoral</i>), sélectionnez l'établissement (actif), puis saisissez le "
            "<b>matricule</b> communiqué par l'école.",
            styles["Body"],
        )
    )
    story.append(
        info_table(
            [
                ["Profil", "Matricule requis", "Préfixe typique"],
                ["Parent / Tuteur", "Matricule du tuteur déjà enregistré", "TUT-…"],
                ["Élève", "Matricule de l'élève déjà enregistré", "ELV-…"],
                ["Enseignant", "Matricule du personnel déjà enregistré", "PER-…"],
            ],
            styles,
            col_widths=[4 * cm, 7.5 * cm, 4.5 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "<b>Important :</b> la fiche métier (élève, tuteur ou personnel) doit exister avant "
            "la création du compte. Les comptes Direction / Caissier / Trésorier sont créés par l'administration.",
            styles["Tip"],
        )
    )
    story.append(Paragraph("2.3 Se déconnecter", styles["H2"]))
    story.append(
        Paragraph(
            "Utilisez le lien <b>Déconnexion</b> en bas du menu latéral (back-office) ou dans la barre "
            "du portail. Fermez ensuite la session du navigateur sur un poste partagé.",
            styles["Body"],
        )
    )

    # ========== 3 ==========
    story.append(Paragraph("3. Rôles et droits d'accès", styles["H1"]))
    story.append(hr())
    story.append(
        info_table(
            [
                ["Rôle", "Accès principal", "Restrictions notables"],
                [
                    "Manager / Directeur",
                    "Back-office complet + Administration",
                    "Accès large à l'établissement",
                ],
                [
                    "Trésorier",
                    "Finances, salaires, HOADA",
                    "Selon droits internes",
                ],
                [
                    "Caissier",
                    "Liste des paiements + Encaisser",
                    "Ne peut pas modifier ni supprimer un paiement ; menu limité",
                ],
                [
                    "Enseignant / Professeur",
                    "Portail enseignant",
                    "Pas d'accès back-office (sauf cas caissier GRH)",
                ],
                ["Parent", "Portail parent", "Uniquement ses enfants"],
                ["Élève", "Portail élève + cours en ligne", "Ses propres données"],
            ],
            styles,
            col_widths=[4 * cm, 5.5 * cm, 6.5 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            "Un membre du personnel dont la fonction GRH est <b>Caissier</b> peut encaisser même si "
            "son rôle de compte est Enseignant.",
            styles["Tip"],
        )
    )

    # ========== 4 ==========
    story.append(Paragraph("4. Navigation générale", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("4.1 Interface back-office", styles["H2"]))
    story.append(
        Paragraph(
            "Le menu latéral gauche regroupe les modules. En haut de chaque page figurent le titre "
            "et un sous-titre. Un fil d'Ariane facilite le retour en arrière.",
            styles["Body"],
        )
    )
    story.append(Paragraph("Structure du menu (hors caissier) :", styles["Body"]))
    story.append(
        bullets(
            [
                "<b>Accueil / Dashboard</b>",
                "<b>Inscriptions &amp; Élèves</b> — Synthèse, Fiches Élèves, Inscriptions, Communications parents",
                "<b>Pédagogie &amp; Classes</b> — Synthèse, Matières, Périodes bulletin, Classes &amp; salles",
                "<b>Finances &amp; Paiements</b> — Synthèse, Paiements, Salaires, Plan comptable, Journaux, Écritures, Grand livre, Balance",
                "<b>Ressources Humaines</b> — Synthèse, Personnel, Contrats, Congés, Présences, Rémunération",
                "<b>Administration</b> — interface d'administration Django",
            ],
            styles,
        )
    )
    story.append(Paragraph("4.2 Interface portail", styles["H2"]))
    story.append(
        Paragraph(
            "Parents, élèves et enseignants utilisent une interface dédiée (<b>Mon espace</b>) avec "
            "une barre de navigation supérieure : menus adaptés au profil (enfants, messages, cours, etc.).",
            styles["Body"],
        )
    )

    # ========== 5 ==========
    story.append(Paragraph("5. Module Inscriptions &amp; Élèves", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Ce module gère le cycle de vie scolaire : tuteurs, fiches élèves, inscriptions et classes.",
            styles["Body"],
        )
    )
    story.append(Paragraph("5.1 Écrans principaux", styles["H2"]))
    story.append(
        info_table(
            [
                ["Écran", "Utilité"],
                ["Synthèse Inscriptions", "Vue d'ensemble et accès rapides"],
                ["Fiches Élèves / Registre", "Créer, consulter, modifier les élèves"],
                ["Enregistrer un parent / tuteur", "Créer la fiche tuteur (matricule TUT-…)"],
                ["Inscriptions", "Liste des inscriptions scolaires"],
                ["Inscrire un élève", "Lier un élève à une classe et une année"],
                ["Classes &amp; Salles", "Gérer les classes, capacité, section"],
                ["Communications parents", "Annonces / messages ciblés (direction)"],
            ],
            styles,
            col_widths=[6 * cm, W - 6 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("5.2 Types d'inscription", styles["H2"]))
    story.append(
        bullets(
            [
                "<b>Nouvelle</b> — première inscription dans l'établissement",
                "<b>Réinscription</b> — poursuite dans une année suivante",
                "<b>Transfert</b> — arrivée depuis un autre établissement",
            ],
            styles,
        )
    )
    story.append(Paragraph("5.3 Ordre recommandé", styles["H2"]))
    story.append(
        Paragraph(
            "1) Enregistrer le tuteur → 2) Enregistrer l'élève (lié au tuteur) → "
            "3) Inscrire l'élève dans une classe pour l'année en cours.",
            styles["Body"],
        )
    )

    # ========== 6 ==========
    story.append(Paragraph("6. Module Pédagogie &amp; Classes", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Le module pédagogique s'aligne sur le référentiel scolaire RDC (maternelle, primaire, "
            "CTEB / secondaire, humanités) et sur le bulletin avec travaux journaliers (TJ) et examens.",
            styles["Body"],
        )
    )
    story.append(Paragraph("6.1 Fonctions clés", styles["H2"]))
    story.append(
        bullets(
            [
                "<b>Matières</b> — libellé, coefficient, maxima période / examen",
                "<b>Périodes bulletin</b> — trimestres / semestres ; indiquer la période « en cours »",
                "<b>Enseignants de la classe</b> — affecter une matière à un enseignant",
                "<b>Classes &amp; salles</b> — accès depuis le menu pédagogie ou inscriptions",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "Les notes et bulletins sont saisis principalement depuis le <b>portail enseignant</b>. "
            "Un bulletin élève est créé automatiquement à l'inscription.",
            styles["Tip"],
        )
    )

    # ========== 7 ==========
    story.append(Paragraph("7. Module Finances &amp; Paiements", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Ce module couvre la caisse, les frais scolaires, le paiement du personnel et la "
            "comptabilité HOADA (plan, journaux, écritures, grand livre, balance).",
            styles["Body"],
        )
    )
    story.append(Paragraph("7.1 Tableau de bord Finances", styles["H2"]))
    story.append(
        Paragraph(
            "Le tableau de bord affiche notamment :",
            styles["Body"],
        )
    )
    story.append(
        bullets(
            [
                "Caisse réelle (comptable) et espèces en caisse par devise",
                "Nombre de paiements validés",
                "Total des <b>dépenses du mois</b> (salaires payés)",
                "Récapitulatif des <b>entrées</b> (jour / semaine / mois)",
                "Récapitulatif des <b>dépenses</b> (jour / semaine / mois)",
                "Tableau des paiements minerval par classe (avec filtres)",
                "Derniers paiements et statistiques des types de frais",
            ],
            styles,
        )
    )
    story.append(Paragraph("7.2 Paramétrer les frais", styles["H2"]))
    story.append(
        Paragraph(
            "1. Créez les <b>Types de frais</b> (ex. : Minerval, Inscription, Uniforme).<br/>"
            "2. Créez les <b>Frais scolaires</b> : type, section, montant, devise (CDF ou USD), "
            "échéance, caractère obligatoire.",
            styles["Body"],
        )
    )
    story.append(Paragraph("7.3 Encaisser un paiement (caissier)", styles["H2"]))
    story.append(
        bullets(
            [
                "Menu <b>Encaisser un paiement</b> (ou Paiements → Nouveau)",
                "Sélectionner l'élève / inscription et le frais concerné",
                "Saisir le montant, la devise et le mode (Espèces, Mobile Money, Virement, Chèque)",
                "Valider : un numéro de reçu est généré (ex. REC-AAAA-MM-####)",
                "Imprimer le reçu / facture si besoin",
            ],
            styles,
        )
    )
    story.append(
        Paragraph(
            "Seul un <b>caissier</b> peut effectuer un encaissement. Il ne peut ni modifier ni "
            "supprimer un paiement déjà enregistré.",
            styles["Tip"],
        )
    )
    story.append(Paragraph("7.4 Statuts de paiement", styles["H2"]))
    story.append(
        info_table(
            [
                ["Statut", "Signification"],
                ["VALIDE", "Encaissement confirmé (écriture comptable possible)"],
                ["EN_ATTENTE", "Paiement non encore validé"],
                ["ANNULE", "Paiement annulé"],
            ],
            styles,
            col_widths=[4 * cm, W - 4 * cm],
        )
    )
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("7.5 Payer le personnel", styles["H2"]))
    story.append(
        Paragraph(
            "Depuis <b>Finances → Payer le personnel</b>, consultez les fiches de paie générées en GRH. "
            "Vous pouvez payer une fiche ou plusieurs en lot (paiement groupé). Les salaires payés "
            "apparaissent dans le suivi des dépenses du dashboard.",
            styles["Body"],
        )
    )
    story.append(Paragraph("7.6 Comptabilité HOADA", styles["H2"]))
    story.append(
        bullets(
            [
                "<b>Plan comptable</b> — comptes de l'établissement",
                "<b>Journaux</b> — journaux de caisse, banque, salaires, etc.",
                "<b>Écritures</b> — saisie manuelle débit / crédit",
                "<b>Grand livre</b> et <b>Balance</b> — consultation",
                "Les paiements élèves VALIDÉS et les salaires PAYÉS peuvent générer des écritures automatiquement",
            ],
            styles,
        )
    )

    # ========== 8 ==========
    story.append(Paragraph("8. Module Ressources Humaines (GRH)", styles["H1"]))
    story.append(hr())
    story.append(Paragraph("8.1 Personnel", styles["H2"]))
    story.append(
        Paragraph(
            "Créez et gérez les fiches du personnel (matricule PER-…, fonction : Directeur, "
            "Enseignant, Caissier, Comptable, etc.).",
            styles["Body"],
        )
    )
    story.append(Paragraph("8.2 Contrats", styles["H2"]))
    story.append(
        Paragraph(
            "Associez un contrat (CDI, CDD, Prestataire, Stage) avec salaire de base, statut "
            "(Actif / Suspendu / Terminé). Les contrats actifs servent à la génération des paies.",
            styles["Body"],
        )
    )
    story.append(Paragraph("8.3 Congés &amp; Absences", styles["H2"]))
    story.append(
        Paragraph(
            "Enregistrez les demandes (annuel, maladie, etc.), puis <b>Approuver</b> ou <b>Rejeter</b>.",
            styles["Body"],
        )
    )
    story.append(Paragraph("8.4 Présences &amp; Pointage", styles["H2"]))
    story.append(
        Paragraph(
            "Pointer le personnel : Présent, Absent ou Retard.",
            styles["Body"],
        )
    )
    story.append(Paragraph("8.5 Paie &amp; Rémunération", styles["H2"]))
    story.append(
        bullets(
            [
                "Générer les paies pour un mois / une année",
                "Consulter le bulletin de paie (salaire de base, primes, déductions, net à payer)",
                "Confirmer le paiement depuis GRH ou depuis Finances → Payer le personnel",
            ],
            styles,
        )
    )

    # ========== 9 ==========
    story.append(Paragraph("9. Portail enseignant", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Accessible via <b>Mon espace</b> pour les professeurs. Menus typiques : Mes classes, "
            "Cours en ligne, Messages, Présences, Travaux.",
            styles["Body"],
        )
    )
    story.append(
        bullets(
            [
                "<b>Mes classes</b> — classes dont vous êtes titulaire ou affecté",
                "<b>Travaux cotés</b> — créer des travaux (TJ / examen) et saisir les notes (verrouillage après saisie)",
                "<b>Présences</b> — faire l'appel de la classe et consulter le récapitulatif",
                "<b>Bulletins scolaires</b> — consultation par classe / élève",
                "<b>Cours en ligne</b> — publier des chapitres et leçons (Digital School Learning)",
                "<b>Messages</b> — échanger avec les parents",
            ],
            styles,
        )
    )

    # ========== 10 ==========
    story.append(Paragraph("10. Portail parent", styles["H1"]))
    story.append(hr())
    story.append(
        Paragraph(
            "Après connexion avec le matricule tuteur, le parent accède à :",
            styles["Body"],
        )
    )
    story.append(
        bullets(
            [
                "<b>Mes enfants</b> — liste des enfants liés à son compte",
                "Suivi par enfant : présences, notes, frais dus",
                "<b>Annonces</b> — communications de la direction",
                "<b>Messages</b> — échange avec les enseignants titulaires",
            ],
            styles,
        )
    )

    # ========== 11 ==========
    story.append(Paragraph("11. Portail élève", styles["H1"]))
    story.append(hr())
    story.append(
        bullets(
            [
                "<b>Mon espace / Ma scolarité</b> — informations scolaires, notes",
                "<b>Étudier en ligne</b> — accès aux cours publiés par les enseignants",
            ],
            styles,
        )
    )

    # ========== 12 ==========
    story.append(Paragraph("12. Procédures métier pas à pas", styles["H1"]))
    story.append(hr())

    story.append(Paragraph("12.1 Inscrire un nouvel élève", styles["H2"]))
    for i, step in enumerate(
        [
            "Vérifier que l'année scolaire et les classes sont paramétrées.",
            "Inscriptions → Enregistrer un parent / tuteur.",
            "Inscriptions → Fiches Élèves → créer l'élève et le lier au tuteur.",
            "Inscriptions → Inscrire un élève (classe + année, type d'inscription).",
            "Communiquer les matricules (TUT / ELV) pour la création des comptes portail.",
        ],
        1,
    ):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))

    story.append(Paragraph("12.2 Encaisser les frais scolaires", styles["H2"]))
    for i, step in enumerate(
        [
            "Finances → Types de frais / Frais scolaires : paramétrer les barèmes.",
            "Se connecter en tant que caissier.",
            "Paiements → Encaisser : choisir l'élève, le frais, le montant et le mode.",
            "Valider puis imprimer le reçu.",
            "Contrôler l'encaissement sur le tableau de bord Finances (entrées du jour).",
        ],
        1,
    ):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))

    story.append(Paragraph("12.3 Payer les salaires du mois", styles["H2"]))
    for i, step in enumerate(
        [
            "GRH → Contrats : s'assurer que les contrats actifs ont un salaire.",
            "GRH → Paie &amp; Rémunération → Générer les paies (mois / année).",
            "Finances → Payer le personnel (ou confirmation depuis GRH).",
            "Payer fiche par fiche ou en lot.",
            "Vérifier le total des dépenses du mois sur le dashboard Finances.",
        ],
        1,
    ):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))

    story.append(Paragraph("12.4 Saisir les notes d'une période", styles["H2"]))
    for i, step in enumerate(
        [
            "Pédagogie → Périodes bulletin : activer la période en cours.",
            "Enseignant : Mon espace → Travaux → créer un travail (TJ ou examen).",
            "Saisir les notes des élèves (elles peuvent être verrouillées ensuite).",
            "Consulter les bulletins par classe / élève.",
        ],
        1,
    ):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))

    story.append(Paragraph("12.5 Communiquer avec les parents", styles["H2"]))
    for i, step in enumerate(
        [
            "Direction → Communications parents → Nouvelle communication.",
            "Choisir la cible : un parent, une classe, une section ou toute l'école.",
            "Rédiger et publier.",
            "Les parents voient l'annonce dans leur portail.",
        ],
        1,
    ):
        story.append(Paragraph(f"<b>Étape {i}.</b> {step}", styles["Step"]))

    # ========== 13 ==========
    story.append(Paragraph("13. Conseils et bonnes pratiques", styles["H1"]))
    story.append(hr())
    story.append(
        bullets(
            [
                "Paramétrez d'abord l'année scolaire, les sections/classes et les matières avant les inscriptions massives.",
                "Créez toujours le tuteur avant l'élève, puis l'inscription.",
                "Utilisez un compte caissier dédié pour les encaissements (traçabilité).",
                "Vérifiez régulièrement le dashboard Finances (entrées / dépenses jour–semaine–mois).",
                "Générez les paies uniquement après validation des contrats et du pointage du mois.",
                "Ne partagez pas vos identifiants ; déconnectez-vous sur les postes communs.",
                "Les devises CDF et USD coexistent : contrôlez toujours la devise affichée.",
                "Pour le support, contactez l'administrateur de votre établissement Digital School.",
            ],
            styles,
        )
    )

    # ========== 14 ==========
    story.append(Paragraph("14. Glossaire", styles["H1"]))
    story.append(hr())
    story.append(
        info_table(
            [
                ["Terme", "Définition"],
                ["Matricule", "Identifiant unique (ELV, TUT, PER) attribué par l'école"],
                ["Minerval", "Frais de scolarité périodiques"],
                ["HOADA", "Comptabilité d'entreprise (référentiel OHADA / SYSCOHADA)"],
                ["TJ", "Travaux journaliers (évaluation continue)"],
                ["EXAM.", "Note d'examen de période"],
                ["Bulletin RDC", "Bulletin scolaire conforme aux pratiques MEPST / MINEDU-NC"],
                ["CTEB", "Cycle Terminal de l'Éducation de Base"],
                ["Reçu", "Justificatif d'encaissement (numéro REC-…)"],
                ["Net à payer", "Salaire après primes et déductions"],
                ["Période en cours", "Trimestre/semestre actif pour la saisie pédagogique"],
            ],
            styles,
            col_widths=[4 * cm, W - 4 * cm],
        )
    )

    story.append(Spacer(1, 1.2 * cm))
    story.append(hr())
    story.append(
        Paragraph(
            "— Fin du manuel —<br/><br/>"
            "<b>Digital School</b> · Manuel d'utilisation · Version 1.0 · Août 2026<br/>"
            "Ce document décrit les fonctionnalités disponibles dans l'application. "
            "Certaines options peuvent varier selon la configuration de votre établissement.",
            styles["CoverSub"],
        )
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2.2 * cm,
        title="Manuel d'utilisation — Digital School",
        author="Digital School",
        subject="Guide utilisateur complet",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF généré : {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
