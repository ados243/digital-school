#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Génère le kit client Digital School (PDF) : documents commerciaux,
contractuels, formulaires d'onboarding, facturation et après-vente.

Usage :
    python docs/generer_kit_client_pdf.py
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
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
from reportlab.pdfgen import canvas as pdfcanvas

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "kit-client"
LOGO_NTT = ROOT / "assets" / "logo-ntt.png"
LOGO_DS = ROOT / "assets" / "logo-ds.png"

pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", r"C:\Windows\Fonts\ariali.ttf"))

NAVY = colors.HexColor("#0F172A")
BLUE = colors.HexColor("#0077C5")
LIGHT = colors.HexColor("#F8FAFC")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#166534")
GREEN_BG = colors.HexColor("#DCFCE7")
AMBER = colors.HexColor("#B45309")
WHITE = colors.white

PRICE = 20
PRICE_DUP = 10
EXTRA_TRAINING = 50
REF_PROP = "PROP-DS-2026-001"
YEAR = "2026 / 2027"

EDITEUR = "NTT S.A.R.L — NTOBO'S TECHNOLOGY"
ADRESSE = "12, avenue Avenir, Q. Basoko, C. Ngaliema, Kinshasa, RDC"
EMAIL = "Adoscongo@gmail.com"
TEL = "WhatsApp / téléphone : à indiquer à la remise"

BANQUES = [
    ("UBA RDC", "030320004374", "NTOBO'S TECHNOLOGY"),
    ("EQUITY BCDC", "00011150722200037532797", "NTOBO'S TECHNOLOGY SARL"),
    ("ECOBANK RDC", "35900000801", "NTOBO'S TECHNOLOGY SARL"),
]


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="DocTitle", fontName="Arial-Bold", fontSize=18, leading=22, textColor=NAVY, alignment=TA_CENTER, spaceAfter=4))
    s.add(ParagraphStyle(name="DocSub", fontName="Arial", fontSize=10.5, leading=14, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8))
    s.add(ParagraphStyle(name="H1", fontName="Arial-Bold", fontSize=13, leading=17, textColor=NAVY, spaceBefore=12, spaceAfter=6))
    s.add(ParagraphStyle(name="H2", fontName="Arial-Bold", fontSize=11, leading=14, textColor=BLUE, spaceBefore=10, spaceAfter=4))
    s.add(ParagraphStyle(name="Body", fontName="Arial", fontSize=10, leading=13.5, alignment=TA_JUSTIFY, spaceAfter=6, textColor=NAVY))
    s.add(ParagraphStyle(name="Left", fontName="Arial", fontSize=10, leading=13.5, alignment=TA_LEFT, spaceAfter=6, textColor=NAVY))
    s.add(ParagraphStyle(name="Small", fontName="Arial", fontSize=8.5, leading=11.5, textColor=MUTED, spaceAfter=4))
    s.add(ParagraphStyle(name="SmallCenter", fontName="Arial-Italic", fontSize=8, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=6))
    s.add(ParagraphStyle(name="BulletBody", fontName="Arial", fontSize=10, leading=13, textColor=NAVY, leftIndent=2, spaceAfter=1))
    s.add(ParagraphStyle(name="Cell", fontName="Arial", fontSize=8.5, leading=11.5, textColor=NAVY))
    s.add(ParagraphStyle(name="CellH", fontName="Arial-Bold", fontSize=8.5, leading=11.5, textColor=WHITE))
    s.add(ParagraphStyle(name="Label", fontName="Arial-Bold", fontSize=9, leading=12, textColor=WHITE))
    s.add(ParagraphStyle(name="Field", fontName="Arial", fontSize=9.5, leading=13, textColor=NAVY))
    s.add(ParagraphStyle(name="LetterHead", fontName="Arial", fontSize=10, leading=14, alignment=TA_RIGHT, textColor=NAVY, spaceAfter=10))
    s.add(ParagraphStyle(name="Banner", fontName="Arial-Bold", fontSize=12, leading=16, textColor=WHITE, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="BannerSub", fontName="Arial", fontSize=9.5, leading=13, textColor=WHITE, alignment=TA_CENTER))
    s.add(ParagraphStyle(name="CenterBold", fontName="Arial-Bold", fontSize=11, leading=14, alignment=TA_CENTER, textColor=NAVY, spaceAfter=6))
    s.add(ParagraphStyle(name="Sign", fontName="Arial", fontSize=9.5, leading=13, textColor=NAVY))
    return s


S = styles()


def P(text, style="Body"):
    return Paragraph(text, S[style])


def hr():
    return HRFlowable(width="100%", thickness=0.7, color=LINE, spaceBefore=2, spaceAfter=8)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(i, S["BulletBody"]), leftIndent=10, bulletColor=BLUE) for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=14,
        bulletFontName="Arial",
        bulletFontSize=9,
        spaceBefore=1,
        spaceAfter=8,
    )


def banner(title, subtitle=None, fill=BLUE):
    rows = [[P(title, "Banner")]]
    if subtitle:
        rows.append([P(subtitle, "BannerSub")])
    t = Table(rows, colWidths=[17 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("TOPPADDING", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return t


def highlight(title, body, fill=GREEN_BG):
    data = [[P(f"<b>{title}</b><br/>{body}", "Left")]]
    t = Table(data, colWidths=[17 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.6, GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def kv_table(rows, w_label=5.5, w_value=11.5):
    data = []
    for i, (k, v) in enumerate(rows):
        data.append([P(k, "Label"), P(v or " ", "Field")])
    t = Table(data, colWidths=[w_label * cm, w_value * cm])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (1, 0), (1, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
    ]
    for i in range(len(rows)):
        style.append(("BACKGROUND", (0, i), (0, i), NAVY if i % 2 == 0 else BLUE))
    t.setStyle(TableStyle(style))
    return t


def data_table(header, rows, col_widths=None):
    data = [[P(h, "CellH") for h in header]]
    for row in rows:
        data.append([P(str(c), "Cell") for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def blank_table(header, n_rows, col_widths=None):
    empty = [[" "] * len(header) for _ in range(n_rows)]
    return data_table(header, empty, col_widths)


def sign_block(left="Pour l'établissement", right="Pour NTT S.A.R.L"):
    body = "Nom :<br/>Fonction :<br/>Date : ____ / ____ / 20____<br/><br/>Signature et cachet :"
    t = Table(
        [
            [P(left, "Label"), P(right, "Label")],
            [P(body, "Sign"), P(body, "Sign")],
        ],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 1), (-1, 1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), ( -1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("TOPPADDING", (0, 1), (-1, 1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 36),
            ]
        )
    )
    return t


def spacer(h=0.25):
    return Spacer(1, h * cm)


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, **kwargs):
        self._kit_title = kwargs.pop("kit_title", "Digital School")
        self._kit_ref = kwargs.pop("kit_ref", "")
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_chrome(n)
            super().showPage()
        super().save()

    def _draw_chrome(self, page_count):
        w, h = A4
        page = self._pageNumber
        if LOGO_NTT.is_file():
            self.drawImage(str(LOGO_NTT), 2 * cm, h - 2.35 * cm, width=1.7 * cm, height=1.7 * cm, mask="auto", preserveAspectRatio=True, anchor="c")
        if LOGO_DS.is_file():
            self.drawImage(str(LOGO_DS), w - 3.7 * cm, h - 2.35 * cm, width=1.7 * cm, height=1.7 * cm, mask="auto", preserveAspectRatio=True, anchor="c")
        self.setFillColor(NAVY)
        self.setFont("Arial-Bold", 9)
        self.drawCentredString(w / 2, h - 1.15 * cm, EDITEUR)
        self.setFillColor(BLUE)
        self.setFont("Arial", 8)
        self.drawCentredString(w / 2, h - 1.55 * cm, f"{self._kit_title}   ·   {self._kit_ref}".strip(" ·"))
        self.setStrokeColor(BLUE)
        self.setLineWidth(1.4)
        self.line(2 * cm, h - 2.55 * cm, w - 2 * cm, h - 2.55 * cm)
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.55 * cm, w - 2 * cm, 1.55 * cm)
        self.setFillColor(MUTED)
        self.setFont("Arial", 7.5)
        self.drawString(2 * cm, 1.15 * cm, f"{ADRESSE}")
        self.drawRightString(w - 2 * cm, 1.15 * cm, f"{EMAIL}   ·   Page {page}/{page_count}")


def build_pdf(filename, title, ref, story, confidential=True):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    note = P(
        "Modèle NTT S.A.R.L — à personnaliser (nom d'école, effectif, dates, montants). "
        + ("Document confidentiel, usage commercial." if confidential else "Document opérationnel destiné à l'établissement."),
        "SmallCenter",
    )
    flow = [spacer(0.15), note, spacer(0.1)] + story

    def factory(filename_unused, **kwargs):
        kwargs.pop("ident", None)
        return NumberedCanvas(filename_unused, kit_title=title, kit_ref=ref, **kwargs)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.9 * cm,
        bottomMargin=2.0 * cm,
        title=f"{title} — {ref}",
        author=EDITEUR,
    )
    doc.build(flow, canvasmaker=factory)
    return path


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def doc_sommaire():
    story = [
        banner("KIT CLIENT DIGITAL SCHOOL", "Dossier complet à remettre ou à faire signer par l'établissement"),
        spacer(0.3),
        P("Ce kit regroupe les documents manquants du cycle commercial NTT S.A.R.L. "
          "La proposition financière, le cahier des charges et le manuel d'utilisation existent déjà dans le dossier docs/."),
        P("1. Avant-vente", "H1"),
        data_table(
            ["Fichier", "Usage"],
            [
                ["01_Lettre_Proposition_Partenariat.pdf", "Premier contact direction / promoteur"],
                ["02_Plaquette_Commerciale.pdf", "Présentation courte de l'offre (2 pages)"],
                ["03_Presentation_Direction.pdf", "Support de rendez-vous (diapos PDF)"],
            ],
            [9.5 * cm, 7.5 * cm],
        ),
        P("2. Signature", "H1"),
        data_table(
            ["Fichier", "Usage"],
            [
                ["04_Bon_de_Commande.pdf", "Commande ferme des cartes"],
                ["05_Devis_Proforma.pdf", "Devis avant facture"],
                ["06_Contrat_de_Service.pdf", "Convention annuelle"],
                ["07_Conditions_Generales_Vente.pdf", "CGV applicables"],
                ["08_Annexe_Donnees_Personnelles.pdf", "Photos et dossiers élèves"],
            ],
            [9.5 * cm, 7.5 * cm],
        ),
        P("3. L'école fournit", "H1"),
        data_table(
            ["Fichier", "Usage"],
            [
                ["09_Fiche_Etablissement.pdf", "Identité de l'école"],
                ["10_Modele_Liste_Eleves.pdf", "Production des cartes"],
                ["11_Modele_Bareme_Frais.pdf", "Paramétrage Finances"],
                ["12_Modele_Liste_Personnel.pdf", "Création des comptes"],
                ["13_Autorisation_Usage_Photos.pdf", "Droit d'utiliser les photos"],
            ],
            [9.5 * cm, 7.5 * cm],
        ),
        P("4. Mise en service", "H1"),
        data_table(
            ["Fichier", "Usage"],
            [
                ["14_Facture_Modele.pdf", "Note de débit NTT"],
                ["15_Recu_Paiement.pdf", "Acompte, solde ou paiement intégral"],
                ["16_Bon_Livraison_Cartes.pdf", "Remise physique des cartes"],
                ["17_PV_Mise_en_Service.pdf", "Go-live signé"],
                ["18_Fiche_Identifiants.pdf", "URL et comptes"],
                ["19_Guide_Demarrage.pdf", "Première semaine d'usage"],
                ["20_Attestation_Formation.pdf", "Preuve de formation"],
                ["21_Feuille_Emargement_Formation.pdf", "Présence aux sessions"],
            ],
            [9.5 * cm, 7.5 * cm],
        ),
        P("5. Après le go-live", "H1"),
        data_table(
            ["Fichier", "Usage"],
            [
                ["22_Formulaire_Commande_Complementaire.pdf", "Nouveaux élèves (20 USD)"],
                ["23_Formulaire_Duplicata.pdf", "Carte perdue / abîmée (10 USD)"],
                ["24_Fiche_Incident_Support.pdf", "Ticket e-mail / WhatsApp"],
                ["25_Proposition_Renouvellement.pdf", "Année scolaire suivante"],
                ["26_Relance_Impaye.pdf", "Solde non réglé"],
            ],
            [9.5 * cm, 7.5 * cm],
        ),
        spacer(0.3),
        highlight(
            "Offre commerciale de référence",
            f"{PRICE} USD par carte d'élève et par année scolaire. Duplicata : {PRICE_DUP} USD. "
            f"Acompte 50 % à la commande (paiement intégral si moins de 100 cartes). "
            f"Référence proposition : {REF_PROP}.",
        ),
    ]
    return story


def doc_lettre():
    return [
        P("Kinshasa, le ____ / ____ / 20____", "LetterHead"),
        P("<b>Objet :</b> Proposition de partenariat — plateforme Digital School", "Left"),
        P("<b>Réf. :</b> " + REF_PROP, "Left"),
        spacer(0.15),
        P("Madame la Directrice, Monsieur le Directeur, Monsieur le Promoteur,"),
        P(
            "NTT S.A.R.L (NTOBO'S TECHNOLOGY), basée à Ngaliema, Kinshasa, édite <b>Digital School</b>, "
            "une plateforme de gestion scolaire conçue pour les établissements de la République démocratique du Congo : "
            "inscriptions, minerval multi-devises CDF/USD, bulletins, présences, portails parents et enseignants, "
            "GRH et comptabilité OHADA."
        ),
        P(
            "Beaucoup d'écoles perdent encore du temps entre cahiers d'appel, fichiers Excel de caisse, "
            "messages WhatsApp non tracés et bulletins reconstitués à la main. Digital School rassemble ces opérations "
            "dans une seule source de vérité, utilisable dès le lundi matin par la direction, la caisse et les enseignants."
        ),
        P("Le principe commercial est volontairement simple :", "H2"),
        bullets(
            [
                f"<b>Pas de licence logicielle, pas d'abonnement mensuel.</b>",
                f"L'école commande une <b>carte d'élève à {PRICE} USD</b> (année scolaire).",
                "Cette carte ouvre le droit d'utiliser <b>tous les modules</b> pour cet élève.",
                "Comptes direction, caisse, enseignants et parents : <b>illimités et inclus</b>.",
                f"Si l'établissement répercute les {PRICE} USD aux parents au titre de la carte scolaire, "
                "<b>le coût net pour l'école peut être de 0 USD</b>.",
            ]
        ),
        P(
            "Sont inclus : mise en service, hébergement et sauvegardes pendant l'année couverte, "
            "deux sessions de formation (direction/caisse puis enseignants), et le support e-mail / WhatsApp."
        ),
        P(
            "Vous trouverez ci-joint la proposition financière, le bon de commande et, sur demande, "
            "une démonstration sur site ou à distance. Nous restons à votre disposition pour adapter "
            "l'effectif et planifier la production des cartes avant la rentrée."
        ),
        P("Nous vous prions d'agréer, Madame, Monsieur, l'expression de notre considération distinguée."),
        spacer(0.4),
        P(f"<b>{EDITEUR}</b>", "Left"),
        P(ADRESSE, "Left"),
        P(f"E-mail : {EMAIL}", "Left"),
        P(TEL, "Left"),
        spacer(0.3),
        P("Pièces jointes : proposition financière · bon de commande · plaquette · contrat de service.", "Small"),
    ]


def doc_plaquette():
    return [
        banner("DIGITAL SCHOOL", "La gestion scolaire, de l'inscription à la caisse — une carte, tous les modules"),
        spacer(0.25),
        P("Pour qui ?", "H1"),
        P("Écoles privées, publiques et conventionnées en RDC. Direction, trésorerie, enseignants, parents et élèves."),
        P("Ce que l'école obtient", "H1"),
        data_table(
            ["Module", "Résultat concret"],
            [
                ["Inscriptions", "Élèves, tuteurs, classes, sections, capacité des salles"],
                ["Finances", "Frais, encaissements CDF/USD, reçus, WhatsApp, OHADA"],
                ["Pédagogie", "Notes, travaux, bulletins modèle RDC, présences, cours en ligne"],
                ["GRH &amp; paie", "Personnel, contrats, congés, pointage, fiches de paie"],
                ["Portails", "Espaces direction, caisse, enseignant, parent, élève"],
            ],
            [4.5 * cm, 12.5 * cm],
        ),
        spacer(0.2),
        highlight(
            f"Tarif unique : {PRICE} USD / élève / année",
            f"1 carte = 1 élève = 1 année scolaire. Pas de frais d'installation. "
            f"Duplicata : {PRICE_DUP} USD. Formation initiale : 2 sessions incluses.",
        ),
        P("Comment ça se passe", "H1"),
        data_table(
            ["Étape", "Délai"],
            [
                ["Accord et bon de commande signé", "Jour J"],
                ["Création de l'école et des comptes", "48 h"],
                ["Liste des élèves + photos", "Selon l'école"],
                ["Production et livraison des cartes", "7 à 15 jours ouvrés"],
                ["Formation direction / caisse puis enseignants", "Dans les 15 jours"],
            ],
            [12 * cm, 5 * cm],
        ),
        P("Paiement", "H1"),
        bullets(
            [
                "Devise : USD. Acompte 50 % à la commande, solde à la livraison (intégral si moins de 100 cartes).",
                "Virement UBA / EQUITY BCDC / ECOBANK, Mobile Money ou espèces contre reçu.",
                f"Contact : {EMAIL} — {ADRESSE}",
            ]
        ),
    ]


def doc_presentation():
    slides = [
        (
            "Le problème sur le terrain",
            [
                "Cahiers d'appel, Excel de caisse, WhatsApp informel.",
                "Files à la caisse, relances parents au cas par cas.",
                "Bulletins reconstitués à la main, doubles saisies.",
                "Pas de vision unique pour le promoteur.",
            ],
        ),
        (
            "La réponse : Digital School",
            [
                "ERP scolaire édité à Kinshasa par NTT S.A.R.L.",
                "Une source de vérité : inscriptions, caisse, notes, GRH.",
                "Pensé pour la RDC : CDF/USD, bulletins nationaux, WhatsApp.",
                "Utilisable par la direction, la caisse, les enseignants et les parents.",
            ],
        ),
        (
            "Les modules inclus",
            [
                "Inscriptions et dossiers élèves / tuteurs.",
                "Finances : barèmes, encaissements, reçus, OHADA.",
                "Pédagogie : notes, présences, bulletins, cours en ligne.",
                "GRH : contrats, congés, pointage, paie.",
                "Portails et messagerie interne.",
            ],
        ),
        (
            "L'offre commerciale",
            [
                f"{PRICE} USD par carte d'élève, par année scolaire.",
                "Pas de licence, pas d'abonnement mensuel caché.",
                "Tous les modules ouverts dès la première commande.",
                f"Coût net possible pour l'école : 0 USD si répercuté aux parents.",
                f"Duplicata {PRICE_DUP} USD · formation extra {EXTRA_TRAINING} USD / session.",
            ],
        ),
        (
            "Exemple — 400 élèves",
            [
                f"400 × {PRICE} USD = 8 000 USD pour l'année.",
                "Licence, hébergement, comptes illimités : 0 USD de plus.",
                "2 sessions de formation incluses.",
                "Si facturé comme carte scolaire aux parents : coût net école = 0.",
            ],
        ),
        (
            "Prochaine étape",
            [
                "Démonstration (30 à 45 minutes).",
                "Signature du bon de commande + contrat.",
                "Transmission de la liste élèves et du logo.",
                "Production des cartes et mise en service.",
            ],
        ),
    ]
    story = [
        banner("RENDEZ-VOUS DIRECTION", "Support de présentation Digital School — NTT S.A.R.L"),
        spacer(0.2),
        P("Document à projeter ou à laisser après le rendez-vous. Une page = un message."),
    ]
    for i, (title, items) in enumerate(slides, 1):
        if i > 1:
            story.append(PageBreak())
        story.extend(
            [
                banner(f"{i}  /  {len(slides)}", title),
                spacer(0.4),
                bullets(items),
                spacer(0.4),
                P(f"Réf. {REF_PROP}  ·  {PRICE} USD / carte / année  ·  {EMAIL}", "SmallCenter"),
            ]
        )
    return story


def doc_bon_commande():
    return [
        banner("BON DE COMMANDE", f"Digital School — cartes d'élève · réf. {REF_PROP}"),
        spacer(0.2),
        P("À compléter, signer, cacheter et renvoyer à NTT S.A.R.L. Un devis / facture conforme sera adressé sous 48 heures."),
        kv_table(
            [
                ("Nom de l'établissement", ""),
                ("Ville / commune", ""),
                ("Promoteur / directeur", ""),
                ("Téléphone", ""),
                ("E-mail", ""),
                ("Année scolaire", YEAR),
                ("Nombre de cartes", f"________  élèves  ×  {PRICE} USD"),
                ("Montant cartes (USD)", "________"),
                ("Duplicatas", f"________  ×  {PRICE_DUP} USD  =  ________"),
                ("Montant général (USD)", "________"),
                ("Mode de paiement", "Virement  /  Mobile Money  /  Espèces"),
                ("Banque de virement", "UBA RDC  /  EQUITY BCDC  /  ECOBANK RDC"),
            ]
        ),
        spacer(0.25),
        P(
            f"Je soussigné(e), dûment habilité(e) à engager l'établissement, accepte la proposition financière "
            f"Digital School (réf. {REF_PROP}) et commande le nombre de cartes indiqué ci-dessus. "
            "L'engagement naît à la signature du présent bon et au versement de l'acompte (ou du paiement intégral "
            "si la commande est inférieure à 100 cartes)."
        ),
        spacer(0.2),
        sign_block(),
        spacer(0.2),
        P("Joindre : fiche établissement, liste des élèves, preuve de paiement de l'acompte.", "Small"),
    ]


def doc_devis():
    return [
        banner("DEVIS / FACTURE PRO FORMA", "Non contractuel tant que le bon de commande n'est pas signé"),
        spacer(0.15),
        kv_table(
            [
                ("Émetteur", EDITEUR),
                ("Adresse", ADRESSE),
                ("E-mail", EMAIL),
                ("N° devis", "DEV-DS-2026-____"),
                ("Date", "____ / ____ / 20____"),
                ("Validité", "90 jours"),
                ("Client", "[Nom de l'établissement]"),
                ("Année scolaire", YEAR),
                ("Réf. offre", REF_PROP),
            ]
        ),
        P("Prestations", "H1"),
        data_table(
            ["Désignation", "Qté", "P.U. USD", "Montant USD"],
            [
                [f"Carte d'élève Digital School — droit d'usage {YEAR}", "________", str(PRICE), "________"],
                ["Duplicata de carte (le cas échéant)", "________", str(PRICE_DUP), "________"],
                ["Formation supplémentaire sur site (au-delà des 2 sessions)", "________", str(EXTRA_TRAINING), "________"],
                ["Total HT / TTC (USD)", "", "", "________"],
            ],
            [8.5 * cm, 2.5 * cm, 3 * cm, 3 * cm],
        ),
        P("Inclus sans ligne supplémentaire : mise en service, hébergement et sauvegardes de l'année, "
          "comptes illimités, 2 sessions de formation, support de base e-mail / WhatsApp.", "Small"),
        P("Exemple de lecture (400 élèves, sans duplicata) : 400 × 20 = 8 000 USD.", "Small"),
        P("Conditions de règlement", "H1"),
        bullets(
            [
                "Acompte 50 % à la commande ferme, solde à la livraison des cartes.",
                "Commande inférieure à 100 cartes : paiement intégral à la commande.",
                "Moyens : virement, Mobile Money (M-Pesa, Airtel Money, Orange Money), espèces contre reçu.",
            ]
        ),
        P("Comptes de virement", "H2"),
        data_table(["Banque", "N° de compte", "Intitulé"], BANQUES, [4 * cm, 7.5 * cm, 5.5 * cm]),
        spacer(0.25),
        sign_block("Bon pour accord — l'établissement", "NTT S.A.R.L"),
    ]


def doc_contrat():
    arts = [
        ("Article 1 — Objet",
         "Le présent contrat a pour objet la fourniture par NTT S.A.R.L de cartes d'élève nominatives et "
         "l'ouverture du droit d'utiliser la plateforme Digital School (inscriptions, finances, pédagogie, GRH, portails) "
         "pour l'année scolaire indiquée, au profit de l'établissement client."),
        ("Article 2 — Documents contractuels",
         f"Font partie du contrat : le bon de commande signé, les CGV, l'annexe données personnelles, "
         f"et la proposition financière {REF_PROP}. En cas de contradiction, le contrat prévaut sur la proposition, "
         "puis les CGV, puis le bon de commande pour les quantités et montants."),
        ("Article 3 — Prestations incluses",
         "Sont inclus : production des cartes commandées ; création du compte établissement ; "
         "hébergement, sauvegardes et mises à jour pendant l'année couverte ; comptes utilisateurs illimités ; "
         "deux sessions de formation (direction/caisse et enseignants) ; support de base e-mail / WhatsApp."),
        ("Article 4 — Prestations hors forfait",
         f"Duplicata : {PRICE_DUP} USD. Cartes complémentaires : {PRICE} USD. Formation supplémentaire : "
         f"{EXTRA_TRAINING} USD / session. Import de données historiques et développements spécifiques : sur devis. "
         "Le matériel informatique et la connexion internet restent à la charge de l'établissement."),
        ("Article 5 — Prix et paiement",
         f"Le prix est de {PRICE} USD par carte et par année scolaire. Devise : USD. "
         "Acompte de 50 % à la commande, solde à la livraison. Paiement intégral si moins de 100 cartes. "
         "Toute somme due produit, après mise en demeure restée sans effet quinze (15) jours, "
         "un droit pour NTT de suspendre l'accès à la plateforme jusqu'à régularisation."),
        ("Article 6 — Durée",
         "Le contrat est conclu pour l'année scolaire correspondant aux cartes commandées. "
         "Il se renouvelle par une nouvelle commande selon l'effectif réel. "
         "Les données de l'école sont conservées ; on ne recommence pas de zéro."),
        ("Article 7 — Obligations de l'établissement",
         "L'école commande une carte pour chaque élève utilisant la plateforme ; transmet une liste exacte "
         "et des photos exploitables ; désigne un interlocuteur ; fait suivre le personnel aux formations ; "
         "n'utilise Digital School que pour son établissement ; n'extrait pas le logiciel ni ne le reverse."),
        ("Article 8 — Obligations de NTT",
         "NTT s'engage à maintenir la plateforme disponible pendant l'année couverte, hors maintenance planifiée "
         "et cas de force majeure ; à produire les cartes sous 7 à 15 jours ouvrés après liste complète et acompte ; "
         "à traiter les données élèves uniquement pour l'exécution du contrat."),
        ("Article 9 — Propriété",
         "Digital School, ses codes, marques et documentations restent la propriété exclusive de NTT S.A.R.L. "
         "L'école bénéficie d'un droit d'usage non exclusif, non cessible, limité à l'année payée. "
         "Les données élèves, notes, paiements et documents de l'école restent la propriété de l'établissement."),
        ("Article 10 — Données personnelles",
         "Le traitement des photos et dossiers est précisé en annexe. NTT n'utilise pas ces données à des fins "
         "de prospection tierce. L'école garantit disposer des bases légales nécessaires vis-à-vis des parents."),
        ("Article 11 — Non-remboursement",
         "Un élève qui quitte l'établissement en cours d'année n'ouvre pas droit à remboursement : "
         "la carte a été produite et le droit d'usage ouvert pour l'année."),
        ("Article 12 — Résiliation",
         "Chaque partie peut résilier en cas de manquement grave non réparé sous 15 jours après mise en demeure écrite. "
         "Les sommes correspondant aux cartes déjà produites restent acquises à NTT."),
        ("Article 13 — Responsabilité",
         "NTT n'est pas responsable des saisies erronées de l'école, des pannes du matériel ou de l'accès internet "
         "de l'établissement, ni des décisions pédagogiques ou financières prises par la direction. "
         "La responsabilité de NTT est limitée, par année, au montant effectivement encaissé au titre du présent contrat."),
        ("Article 14 — Droit applicable",
         "Le présent contrat est soumis au droit de la République démocratique du Congo et aux Actes uniformes OHADA. "
         "Tout litige non résolu à l'amiable relève des juridictions compétentes de Kinshasa."),
        ("Article 15 — Intégralité",
         "Le présent document et ses annexes constituent l'intégralité de l'accord. "
         "Toute modification se fait par avenant écrit signé des deux parties."),
    ]
    story = [
        banner("CONTRAT DE SERVICE", "Fourniture de cartes d'élève et accès à Digital School"),
        spacer(0.15),
        P("Entre les soussignés :"),
        kv_table(
            [
                ("Prestataire", f"{EDITEUR}, {ADRESSE}, e-mail {EMAIL} (ci-après « NTT »)"),
                ("Client", "[Nom de l'établissement], adresse : ____________________ (ci-après « l'Établissement »)"),
                ("Année scolaire", YEAR),
                ("Effectif commandé", "________ cartes"),
                ("Montant", f"________ USD  (________ × {PRICE} USD)"),
                ("N° contrat", "CTR-DS-2026-____"),
            ]
        ),
        spacer(0.15),
        P("Il a été convenu ce qui suit."),
    ]
    for title, body in arts:
        story.append(P(title, "H2"))
        story.append(P(body))
    story.extend([spacer(0.25), sign_block("L'Établissement", "NTT S.A.R.L"), spacer(0.15),
                  P("Fait à Kinshasa, en deux exemplaires originaux.", "SmallCenter")])
    return story


def doc_cgv():
    return [
        banner("CONDITIONS GÉNÉRALES DE VENTE", "Digital School — NTT S.A.R.L"),
        P("Applicables à toute commande de cartes Digital School et à l'accès à la plateforme, "
          "sauf avenant écrit. Version août 2026."),
        P("1. Offre et acceptation", "H1"),
        P(f"L'offre {REF_PROP} est valable 90 jours. Un bon de commande signé et l'acompte valent acceptation. "
          "La proposition commerciale n'est pas une facture."),
        P("2. Tarifs", "H1"),
        bullets(
            [
                f"Carte d'élève : {PRICE} USD / élève / année scolaire.",
                f"Duplicata : {PRICE_DUP} USD.",
                f"Commande minimale conseillée : 30 cartes (en dessous : devis spécifique).",
                f"Formation supplémentaire : {EXTRA_TRAINING} USD / session.",
                "Import historique et développements : sur devis.",
            ]
        ),
        P("3. Commande et production", "H1"),
        P("La production des cartes commence après réception du bon signé, de la liste élèves (et photos) "
          "et de l'acompte. Délai indicatif : 7 à 15 jours ouvrés. Les nouveaux élèves en cours d'année "
          "font l'objet d'une commande complémentaire au tarif plein, sans prorata mensuel."),
        P("4. Paiement", "H1"),
        P("USD. Acompte 50 %, solde à la livraison ; paiement intégral sous 100 cartes. "
          "Virement (UBA, EQUITY BCDC, ECOBANK), Mobile Money ou espèces contre reçu NTT. "
          "Toute commande doit rappeler le nom de l'école et la référence de l'offre."),
        P("5. Accès à la plateforme", "H1"),
        P("L'accès est ouvert pour l'année des cartes commandées. Comptes illimités inclus. "
          "NTT peut suspendre l'accès en cas d'impayé après mise en demeure. "
          "Les identifiants sont personnels ; l'école est responsable de leur usage."),
        P("6. Support et formation", "H1"),
        P("Deux sessions initiales incluses. Support de base e-mail / WhatsApp pendant l'année. "
          "Le support ne couvre pas la formation continue du personnel nouvellement recruté, "
          "ni les incidents liés au réseau ou au matériel de l'école."),
        P("7. Données et photos", "H1"),
        P("Les listes et photos restent la propriété de l'établissement. NTT les utilise uniquement "
          "pour produire les cartes et alimenter Digital School. Voir l'annexe données personnelles."),
        P("8. Garantie et disponibilité", "H1"),
        P("NTT s'efforce d'assurer un service continu. Des maintenances peuvent être planifiées. "
          "Force majeure : coupures générales, faits de guerre, catastrophes, défaillance majeure d'un hébergeur."),
        P("9. Non-remboursement", "H1"),
        P("Pas de remboursement en cas de départ d'élève, de carte déjà produite, ou de résiliation "
          "après lancement de la fabrication."),
        P("10. Propriété intellectuelle", "H1"),
        P("Interdiction de copier, revendre, sous-licencier ou décompiler la plateforme. "
          "Le droit d'usage cesse à la fin de l'année non renouvelée, sous réserve de restitution des données à l'école."),
        P("11. Droit applicable", "H1"),
        P("Droit congolais et OHADA. Litiges : juridictions de Kinshasa, après tentative de règlement amiable."),
        spacer(0.3),
        sign_block("Lu et approuvé — l'établissement", "NTT S.A.R.L"),
    ]


def doc_annexe_donnees():
    return [
        banner("ANNEXE — DONNÉES PERSONNELLES", "Photos, listes d'élèves et dossiers Digital School"),
        P("Annexe au contrat de service Digital School. Loi n° 20/017 du 26 juin 2020 relative aux "
          "télécommunications et aux technologies de l'information en RDC, et principes OHADA de bonne foi."),
        P("1. Finalités", "H1"),
        bullets(
            [
                "Produire les cartes nominatives (identité, classe, photo, QR).",
                "Créer et tenir le dossier élève dans Digital School.",
                "Permettre la caisse, les bulletins, les présences et le portail parent.",
                "Assurer le support et la sécurité de la plateforme.",
            ]
        ),
        P("2. Données concernées", "H1"),
        P("Identité de l'élève et du tuteur, classe, matricule, photo, coordonnées, historiques de paiement "
          "et données pédagogiques saisies par l'école. Pas de donnée de santé sauf si l'école la saisit de sa propre initiative."),
        P("3. Rôles", "H1"),
        P("<b>L'établissement</b> est responsable de la collecte auprès des parents et de l'exactitude des listes. "
          "<b>NTT</b> traite les données pour le compte de l'école, uniquement pour exécuter le contrat. "
          "NTT ne revend pas les fichiers élèves."),
        P("4. Conservation", "H1"),
        P("Pendant la relation contractuelle et les années scolaires suivantes si l'école renouvelle. "
          "En cas d'arrêt définitif, NTT restitue un export (selon format disponible) puis supprime ou archive "
          "selon un délai de 90 jours, sauf obligation légale de conservation."),
        P("5. Sécurité", "H1"),
        P("Accès par comptes nominatifs et rôles. Sauvegardes. L'école s'interdit de partager le mot de passe administrateur."),
        P("6. Photos", "H1"),
        P("Les photos servent à la carte et au dossier. L'école obtient l'accord des tuteurs (formulaire 13 du kit). "
          "Une photo illisible peut retarder la carte ; un duplicata pourra être facturé si réimpression après livraison."),
        P("7. Droits des personnes", "H1"),
        P("Toute demande d'accès, rectification ou opposition d'un parent est adressée d'abord à l'école. "
          "NTT coopère dans un délai raisonnable sur demande écrite de la direction."),
        spacer(0.25),
        sign_block(),
    ]


def doc_fiche_etablissement():
    return [
        banner("FICHE ÉTABLISSEMENT", "À remplir par la direction — préalable à la mise en service"),
        P("Identité", "H1"),
        kv_table(
            [
                ("Nom officiel de l'école", ""),
                ("Sigle", ""),
                ("Type", "Privée  /  Publique  /  Conventionnée"),
                ("N° agrément / SECOPE (si applicable)", ""),
                ("Adresse complète", ""),
                ("Commune / ville", ""),
                ("Téléphone standard", ""),
                ("E-mail officiel", ""),
                ("Logo (fichier PNG/JPG)", "Joindre par e-mail"),
            ]
        ),
        P("Direction et interlocuteurs", "H1"),
        kv_table(
            [
                ("Promoteur", "Nom, tél., e-mail"),
                ("Chef d'établissement", "Nom, tél., e-mail"),
                ("Responsable caisse", "Nom, tél., e-mail"),
                ("Responsable pédagogique", "Nom, tél., e-mail"),
                ("Interlocuteur Digital School", "Nom, tél., e-mail"),
            ]
        ),
        P("Paramètres de démarrage", "H1"),
        kv_table(
            [
                ("Année scolaire", YEAR),
                ("Date de rentrée", "____ / ____ / 20____"),
                ("Effectif estimé", "________ élèves"),
                ("Sections / cycles", "Maternelle / Primaire / Secondaire / …"),
                ("Devises utilisées", "CDF  /  USD  /  les deux"),
                ("WhatsApp de l'école", ""),
            ]
        ),
        spacer(0.3),
        sign_block("Cachet de l'école", "Réception NTT"),
    ]


def doc_liste_eleves():
    return [
        banner("MODÈLE — LISTE DES ÉLÈVES", "Fichier de production des cartes (photocopier si besoin)"),
        P("Une ligne = une carte. Photo : fichier nommé Matricule_Nom.jpg, ou photo collée / jointe. "
          "Joindre aussi un tableur Excel si disponible (mêmes colonnes)."),
        kv_table(
            [
                ("Établissement", ""),
                ("Année scolaire", YEAR),
                ("Classe / section concernée", "________  ou  « toutes »"),
                ("Nombre de lignes de cette feuille", "________"),
            ]
        ),
        spacer(0.15),
        blank_table(
            ["N°", "Matricule", "Nom", "Post-nom", "Prénom", "Sexe", "Classe", "Photo OK"],
            18,
            [1.2 * cm, 2.2 * cm, 2.6 * cm, 2.4 * cm, 2.4 * cm, 1.2 * cm, 2.4 * cm, 2.6 * cm],
        ),
        spacer(0.2),
        P("Certification : la présente liste correspond aux élèves pour lesquels une carte Digital School est commandée.", "Small"),
        sign_block("Direction / secrétariat", "NTT — reçu le"),
    ]


def doc_bareme():
    return [
        banner("MODÈLE — BARÈME DES FRAIS", "Paramétrage du module Finances"),
        kv_table([("Établissement", ""), ("Année scolaire", YEAR), ("Taux CDF / USD du jour (indicatif)", "1 USD = ________ CDF")]),
        P("Saisir les frais que la caisse devra encaisser (inscription, minerval, transport, cantine, carte, etc.).", "Small"),
        blank_table(
            ["Libellé du frais", "Section / classe", "Montant", "Devise", "Échéance", "Obligatoire"],
            12,
            [4 * cm, 3.2 * cm, 2.2 * cm, 2 * cm, 2.8 * cm, 2.8 * cm],
        ),
        spacer(0.25),
        sign_block("Trésorerie de l'école", "Paramétré par NTT le"),
    ]


def doc_personnel():
    return [
        banner("MODÈLE — LISTE DU PERSONNEL", "Création des comptes Digital School"),
        P("Indiquer le rôle souhaité : Direction, Caisse, Enseignant, RH, Parent (le parent est en général créé via le dossier élève)."),
        kv_table([("Établissement", ""), ("Année scolaire", YEAR)]),
        blank_table(
            ["Nom et post-nom", "Fonction", "Téléphone", "E-mail", "Rôle DS", "Classe (ens.)"],
            14,
            [3.6 * cm, 2.6 * cm, 2.6 * cm, 3.2 * cm, 2.4 * cm, 2.6 * cm],
        ),
        spacer(0.25),
        sign_block("Direction", "Comptes créés par NTT le"),
    ]


def doc_autorisation_photos():
    return [
        banner("AUTORISATION D'USAGE DES PHOTOS", "Cartes d'élève et dossiers Digital School"),
        P("Document signé par l'établissement, qui confirme disposer de l'accord des tuteurs "
          "(ou s'engage à l'obtenir) pour l'usage des photos dans le cadre strict du contrat."),
        kv_table(
            [
                ("Établissement", ""),
                ("Année scolaire", YEAR),
                ("Nombre approximatif de photos transmises", "________"),
            ]
        ),
        P("L'établissement autorise NTT S.A.R.L à :", "H2"),
        bullets(
            [
                "Imprimer la photo sur la carte nominative de l'élève.",
                "Associer la photo au dossier dans Digital School (consultation selon les rôles).",
                "Conserver le fichier le temps du contrat et des renouvellements.",
            ]
        ),
        P("NTT s'interdit tout usage publicitaire externe sans accord écrit. "
          "Les photos ne sont pas vendues. Un tuteur peut demander le retrait via la direction de l'école."),
        spacer(0.3),
        P("Option recommandée côté école : faire signer un accord parent lors de l'inscription "
          "(mention « photo carte scolaire et dossier numérique »)."),
        spacer(0.3),
        sign_block("Le chef d'établissement", "NTT S.A.R.L"),
    ]


def doc_facture():
    return [
        banner("FACTURE / NOTE DE DÉBIT", "NTT S.A.R.L — à émettre après commande ferme"),
        kv_table(
            [
                ("Émetteur", EDITEUR),
                ("Adresse", ADRESSE),
                ("E-mail", EMAIL),
                ("RCCM / ID. NAT / NIF", "[à compléter par NTT]"),
                ("N° facture", "FACT-DS-2026-____"),
                ("Date", "____ / ____ / 20____"),
                ("Client", "[Nom de l'établissement]"),
                ("Bon de commande", "BC-DS-2026-____"),
                ("Année scolaire", YEAR),
            ]
        ),
        P("Détail", "H1"),
        data_table(
            ["Désignation", "Qté", "P.U. USD", "Montant USD"],
            [
                [f"Cartes Digital School — droit d'usage {YEAR}", "________", str(PRICE), "________"],
                ["Duplicatas", "________", str(PRICE_DUP), "________"],
                ["Autres (préciser)", "________", "________", "________"],
                ["Total dû (USD)", "", "", "________"],
                ["Acompte déjà reçu", "", "", "________"],
                ["Net à payer", "", "", "________"],
            ],
            [8.5 * cm, 2.5 * cm, 3 * cm, 3 * cm],
        ),
        P("Échéance : acompte à la commande · solde à la livraison des cartes.", "Small"),
        P("Comptes", "H2"),
        data_table(["Banque", "N° de compte", "Intitulé"], BANQUES, [4 * cm, 7.5 * cm, 5.5 * cm]),
        P("Libellé de virement : nom de l'école + n° facture.", "Small"),
        spacer(0.2),
        sign_block("Reçu par l'établissement", "NTT S.A.R.L — cachet"),
    ]


def doc_recu():
    return [
        banner("REÇU DE PAIEMENT", "Acompte · solde · paiement intégral · Mobile Money · espèces"),
        kv_table(
            [
                ("N° reçu", "REC-DS-2026-____"),
                ("Date", "____ / ____ / 20____"),
                ("Établissement", ""),
                ("Facture / devis lié", ""),
                ("Nature", "Acompte 50 %  /  Solde  /  Paiement intégral  /  Duplicata  /  Complément"),
                ("Montant reçu (USD)", "________"),
                ("Montant en lettres", "________________________________"),
                ("Mode", "Virement  /  M-Pesa  /  Airtel Money  /  Orange Money  /  Espèces"),
                ("Référence (bordereau, tel, n° trans.)", ""),
                ("Banque (si virement)", "UBA  /  EQUITY  /  ECOBANK"),
            ]
        ),
        spacer(0.2),
        P("NTT S.A.R.L reconnaît avoir reçu la somme indiquée. Ce reçu ne vaut pas quitus de la commande "
          "tant que le solde éventuel n'est pas réglé et les cartes non livrées."),
        spacer(0.35),
        sign_block("Payeur (école)", "Caissier / NTT S.A.R.L"),
    ]


def doc_livraison():
    return [
        banner("BON DE LIVRAISON — CARTES D'ÉLÈVE", "Remise contradictoire"),
        kv_table(
            [
                ("N° BL", "BL-DS-2026-____"),
                ("Date de remise", "____ / ____ / 20____"),
                ("Établissement", ""),
                ("Année scolaire", YEAR),
                ("Lieu de remise", "Siège école  /  Siège NTT  /  Autre : ________"),
                ("Cartes commandées", "________"),
                ("Cartes remises ce jour", "________"),
                ("Cartes en attente (photos manquantes, etc.)", "________"),
                ("Lots / classes", ""),
            ]
        ),
        P("Contrôle à la réception", "H1"),
        data_table(
            ["Point", "OK", "Réserve"],
            [
                ["Quantité conforme au bon de commande (hors attente)", "☐", "☐  ________"],
                ["Noms / classes lisibles", "☐", "☐  ________"],
                ["Photos présentes et exploitables", "☐", "☐  ________"],
                ["QR / code visuel imprimé", "☐", "☐  ________"],
                ["Logo et année scolaire corrects", "☐", "☐  ________"],
            ],
            [9 * cm, 3 * cm, 5 * cm],
        ),
        P("Observations : ______________________________________________________________"),
        spacer(0.25),
        sign_block("Réception école — nom et cachet", "Remis par NTT"),
    ]


def doc_pv():
    return [
        banner("PROCÈS-VERBAL DE MISE EN SERVICE", "Go-live Digital School"),
        kv_table(
            [
                ("Établissement", ""),
                ("Date de mise en service", "____ / ____ / 20____"),
                ("URL de connexion", "https://________________"),
                ("Année scolaire paramétrée", YEAR),
                ("Interlocuteur école", ""),
                ("Interlocuteur NTT", ""),
            ]
        ),
        P("Checklist", "H1"),
        data_table(
            ["Opération", "Fait", "Commentaire"],
            [
                ["Compte établissement créé", "☐", ""],
                ["Comptes direction et caisse remis", "☐", ""],
                ["Année, sections, classes", "☐", ""],
                ["Barème des frais saisi", "☐", ""],
                ["Élèves importés / saisis (échantillon ou lot)", "☐", ""],
                ["Cartes livrées ou en cours", "☐", ""],
                ["Formation direction / caisse", "☐", ""],
                ["Formation enseignants (planifiée ou faite)", "☐", ""],
                ["Support (e-mail / WhatsApp) expliqué", "☐", ""],
            ],
            [8 * cm, 2.2 * cm, 6.8 * cm],
        ),
        P("Réserves éventuelles : ______________________________________________________"),
        P("En l'absence de réserve, l'établissement reconnaît pouvoir utiliser Digital School pour l'année en cours."),
        spacer(0.25),
        sign_block(),
    ]


def doc_identifiants():
    return [
        banner("FICHE DES IDENTIFIANTS", "Document confidentiel — ne pas photocopier inutilement"),
        kv_table(
            [
                ("Établissement", ""),
                ("URL", "https://________________"),
                ("Date de remise", "____ / ____ / 20____"),
                ("Remis à (nom)", ""),
            ]
        ),
        P("Comptes initiaux (mots de passe à changer à la première connexion)", "H1"),
        blank_table(
            ["Rôle", "Identifiant / e-mail", "Mot de passe temporaire", "Remis (visa)"],
            8,
            [3.5 * cm, 5 * cm, 5 * cm, 3.5 * cm],
        ),
        spacer(0.2),
        bullets(
            [
                "Changez les mots de passe dès la première connexion.",
                "Ne partagez pas le compte administrateur.",
                "En cas de perte : écrire à " + EMAIL + " depuis l'e-mail officiel de l'école.",
                "NTT ne redemande jamais un mot de passe par WhatsApp non officiel.",
            ]
        ),
        spacer(0.25),
        sign_block("Réception école", "Remise NTT"),
    ]


def doc_guide():
    return [
        banner("GUIDE DE DÉMARRAGE", "Première semaine avec Digital School"),
        P("Ce guide complète le manuel d'utilisation. Objectif : que la caisse et le secrétariat tournent en 5 jours."),
        P("Jour 1 — Connexion et rôles", "H1"),
        bullets(
            [
                "Ouvrir l'URL, se connecter, changer le mot de passe.",
                "Vérifier les comptes direction et caisse.",
                "Parcourir le tableau de bord sans saisir de vrai paiement test sur la caisse réelle.",
            ]
        ),
        P("Jour 2 — Structure de l'école", "H1"),
        bullets(
            [
                "Contrôler l'année scolaire, les sections, les classes et les capacités.",
                "Vérifier que les élèves livrés (ou un échantillon) apparaissent dans Inscriptions.",
                "Corriger les homonymes et matricules avant d'imprimer quoi que ce soit.",
            ]
        ),
        P("Jour 3 — Caisse", "H1"),
        bullets(
            [
                "Saisir ou valider le barème des frais (montant, devise CDF ou USD, échéance).",
                "Enregistrer un premier encaissement réel uniquement si le caissier est formé.",
                "Imprimer un reçu et le comparer au talon papier habituel.",
                "Vérifier le taux de change du jour si vous encaissez les deux devises.",
            ]
        ),
        P("Jour 4 — Enseignants", "H1"),
        bullets(
            [
                "Créer ou activer les comptes enseignants.",
                "Affecter les matières / classes.",
                "Montrer : appel, saisie d'une note, consultation du portail.",
            ]
        ),
        P("Jour 5 — Parents et communication", "H1"),
        bullets(
            [
                "Tester une annonce de classe et, si configuré, une notification WhatsApp.",
                "Expliquer au secrétariat comment un parent se connecte.",
                "Noter les questions ouvertes sur la fiche incident.",
            ]
        ),
        P("À ne pas faire la première semaine", "H1"),
        bullets(
            [
                "Générer toutes les paies avant d'avoir validé les contrats.",
                "Importer un Excel douteux sans copie de contrôle.",
                "Laisser un stagiaire sur le compte administrateur.",
            ]
        ),
        P(f"Support : {EMAIL} — rappeler le nom de l'école. Manuel complet : docs/Manuel_Utilisation_Digital_School.pdf.", "Small"),
    ]


def doc_attestation():
    return [
        Spacer(1, 1.2 * cm),
        banner("ATTESTATION DE FORMATION", "Digital School — NTT S.A.R.L"),
        spacer(0.5),
        P("Je soussigné(e), représentant NTT S.A.R.L, atteste que :", "CenterBold"),
        spacer(0.2),
        kv_table(
            [
                ("Établissement", ""),
                ("Session", "Direction / caisse    /    Enseignants    /    Autre : ________"),
                ("Date", "____ / ____ / 20____"),
                ("Lieu", "Sur site  /  Distancial  /  Siège NTT"),
                ("Durée", "________ heures"),
                ("Nombre de participants", "________  (voir émargement)"),
                ("Intervenant NTT", ""),
            ]
        ),
        spacer(0.3),
        P("La session a porté sur l'usage de Digital School correspondant au public formé "
          "(connexion, rôles, inscriptions et/ou caisse et/ou pédagogie). "
          "Cette attestation ne dispense pas de la seconde session prévue au contrat, si elle n'a pas encore eu lieu."),
        spacer(0.5),
        sign_block("Cachet de l'établissement", "Formateur — NTT S.A.R.L"),
    ]


def doc_emargement():
    return [
        banner("FEUILLE D'ÉMARGEMENT", "Formation Digital School"),
        kv_table(
            [
                ("Établissement", ""),
                ("Session", "Direction-caisse  /  Enseignants"),
                ("Date et heure", "____ / ____ / 20____    de ____ h à ____ h"),
                ("Formateur", ""),
            ]
        ),
        spacer(0.15),
        blank_table(
            ["N°", "Nom", "Fonction", "Téléphone", "Signature matin", "Signature soir"],
            16,
            [1.2 * cm, 3.6 * cm, 3 * cm, 3 * cm, 3.1 * cm, 3.1 * cm],
        ),
        spacer(0.2),
        sign_block("Visa direction", "Visa formateur NTT"),
    ]


def doc_complementaire():
    return [
        banner("COMMANDE COMPLÉMENTAIRE", f"Nouveaux élèves en cours d'année — {PRICE} USD / carte"),
        P("Pas de prorata mensuel. Tarif plein de l'année en cours. Joindre la liste et les photos."),
        kv_table(
            [
                ("Établissement", ""),
                ("Année scolaire", YEAR),
                ("N° commande initiale", ""),
                ("Nombre de nouvelles cartes", f"________  ×  {PRICE} USD"),
                ("Montant (USD)", "________"),
                ("Motif", "Inscription tardive  /  Transfert  /  Autre"),
            ]
        ),
        spacer(0.15),
        blank_table(
            ["Nom", "Post-nom", "Prénom", "Classe", "Photo"],
            8,
            [3.4 * cm, 3.4 * cm, 3.4 * cm, 3.4 * cm, 3.4 * cm],
        ),
        spacer(0.25),
        sign_block("Commande école", "Acceptation NTT"),
    ]


def doc_duplicata():
    return [
        banner("DEMANDE DE DUPLICATA", f"Carte perdue, volée ou détériorée — {PRICE_DUP} USD"),
        kv_table(
            [
                ("Établissement", ""),
                ("Élève (nom complet)", ""),
                ("Matricule / classe", ""),
                ("Motif", "Perte  /  Vol  /  Détérioration  /  Erreur d'impression"),
                ("N° de la carte d'origine (si connu)", ""),
                ("Tarif", f"{PRICE_DUP} USD"),
                ("Mode de paiement", "Virement  /  Mobile Money  /  Espèces"),
            ]
        ),
        P("L'ancienne carte, si retrouvée, doit être détruite ou restituée. "
          "Le duplicata ne crée pas un second droit d'usage : il remplace le support physique."),
        spacer(0.3),
        sign_block("Tuteur / école", "NTT — duplicata lancé le"),
    ]


def doc_incident():
    return [
        banner("FICHE INCIDENT / SUPPORT", "E-mail ou WhatsApp — rappeler le nom de l'école"),
        kv_table(
            [
                ("N° (NTT)", "INC-DS-2026-____"),
                ("Date / heure", "____ / ____ / 20____    ____ h ____"),
                ("Établissement", ""),
                ("Demandeur", "Nom, rôle, téléphone"),
                ("Canal", "E-mail  /  WhatsApp  /  Sur site"),
                ("Urgence", "Bloquant caisse  /  Bloquant cours  /  Gênant  /  Demande"),
                ("Module", "Inscriptions  /  Finances  /  Pédagogie  /  GRH  /  Portail  /  Cartes  /  Accès"),
            ]
        ),
        P("Description (faits, message d'erreur, élève concerné) :", "H2"),
        P("________________________________________________________________"),
        P("________________________________________________________________"),
        P("________________________________________________________________"),
        P("________________________________________________________________"),
        P("Traitement NTT", "H1"),
        kv_table(
            [
                ("Pris en charge par", ""),
                ("Cause probable", ""),
                ("Action menée", ""),
                ("Statut", "Ouvert  /  En cours  /  Résolu  /  Reporté"),
                ("Date de clôture", "____ / ____ / 20____"),
            ]
        ),
        spacer(0.25),
        sign_block("Demandeur", "Support NTT"),
        P(f"Adresse de support : {EMAIL}", "SmallCenter"),
    ]


def doc_renouvellement():
    return [
        banner("PROPOSITION DE RENOUVELLEMENT", f"Année scolaire suivante — {PRICE} USD / carte"),
        P("Les données de l'école (dossiers, paiements, notes) sont conservées. Il s'agit d'une nouvelle commande de cartes, pas d'une réinstallation."),
        kv_table(
            [
                ("Établissement", ""),
                ("Année qui se termine", YEAR),
                ("Année à commander", "20____ / 20____"),
                ("Effectif prévu", "________ élèves"),
                ("Montant estimé", f"________ × {PRICE} = ________ USD"),
                ("Date limite souhaitée (avant rentrée)", "____ / ____ / 20____"),
            ]
        ),
        P("À confirmer", "H1"),
        bullets(
            [
                "Liste actualisée des élèves et photos de la nouvelle année.",
                "Bon de commande signé et acompte selon les CGV en vigueur.",
                "Mise à jour éventuelle du barème des frais et de l'organigramme.",
            ]
        ),
        P("Conditions : celles du contrat et des CGV en vigueur à la date du nouveau bon de commande. "
          f"Tarif de référence actuel : {PRICE} USD / carte (sous réserve d'une nouvelle grille communiquée par écrit)."),
        spacer(0.25),
        sign_block("Intention de renouveler — école", "Offre NTT"),
    ]


def doc_relance():
    return [
        banner("RELANCE D'IMPAIÉ", "Solde ou acompte Digital School"),
        P("Kinshasa, le ____ / ____ / 20____", "LetterHead"),
        P("<b>Objet :</b> Relance — facture Digital School n° FACT-DS-2026-____", "Left"),
        P("Madame, Monsieur,"),
        P(
            "Sauf erreur ou omission de notre part, le règlement suivant demeure impayé. "
            "Nous vous remercions de procéder au virement ou de nous adresser la preuve de paiement."
        ),
        kv_table(
            [
                ("Établissement", ""),
                ("N° facture / reçu", ""),
                ("Date d'échéance", "____ / ____ / 20____"),
                ("Montant dû (USD)", "________"),
                ("Déjà reçu", "________"),
                ("Reste à payer", "________"),
                ("Nature", "Acompte  /  Solde livraison  /  Duplicatas  /  Complément"),
            ]
        ),
        P("Comptes NTT", "H2"),
        data_table(["Banque", "N° de compte", "Intitulé"], BANQUES, [4 * cm, 7.5 * cm, 5.5 * cm]),
        spacer(0.15),
        P(
            "Conformément au contrat, l'accès à Digital School peut être suspendu quinze (15) jours "
            "après la présente relance si le solde n'est pas régularisé. "
            "Les cartes déjà produites restent dues."
        ),
        P("Nous restons ouverts à un échéancier écrit en cas de difficulté temporaire."),
        P("Veuillez agréer, Madame, Monsieur, l'expression de nos salutations distinguées."),
        spacer(0.3),
        P(f"<b>{EDITEUR}</b><br/>{EMAIL}<br/>{ADRESSE}", "Left"),
        spacer(0.2),
        sign_block("Accusé de réception école", "NTT S.A.R.L"),
    ]


DOCS = [
    ("00_Sommaire_Kit_Client.pdf", "Sommaire du kit client", "KIT-DS-2026", doc_sommaire),
    ("01_Lettre_Proposition_Partenariat.pdf", "Lettre de proposition", REF_PROP, doc_lettre),
    ("02_Plaquette_Commerciale.pdf", "Plaquette commerciale", "PLA-DS-2026", doc_plaquette),
    ("03_Presentation_Direction.pdf", "Présentation direction", "PRES-DS-2026", doc_presentation),
    ("04_Bon_de_Commande.pdf", "Bon de commande", "BC-DS-2026", doc_bon_commande),
    ("05_Devis_Proforma.pdf", "Devis / pro forma", "DEV-DS-2026", doc_devis),
    ("06_Contrat_de_Service.pdf", "Contrat de service", "CTR-DS-2026", doc_contrat),
    ("07_Conditions_Generales_Vente.pdf", "Conditions générales de vente", "CGV-DS-2026", doc_cgv),
    ("08_Annexe_Donnees_Personnelles.pdf", "Annexe données personnelles", "ANN-DP-2026", doc_annexe_donnees),
    ("09_Fiche_Etablissement.pdf", "Fiche établissement", "FIC-ETAB-2026", doc_fiche_etablissement),
    ("10_Modele_Liste_Eleves.pdf", "Liste des élèves", "LST-ELV-2026", doc_liste_eleves),
    ("11_Modele_Bareme_Frais.pdf", "Barème des frais", "BAR-FRAIS-2026", doc_bareme),
    ("12_Modele_Liste_Personnel.pdf", "Liste du personnel", "LST-PERS-2026", doc_personnel),
    ("13_Autorisation_Usage_Photos.pdf", "Autorisation photos", "AUT-PHOTO-2026", doc_autorisation_photos),
    ("14_Facture_Modele.pdf", "Facture / note de débit", "FACT-DS-2026", doc_facture),
    ("15_Recu_Paiement.pdf", "Reçu de paiement", "REC-DS-2026", doc_recu),
    ("16_Bon_Livraison_Cartes.pdf", "Bon de livraison", "BL-DS-2026", doc_livraison),
    ("17_PV_Mise_en_Service.pdf", "PV de mise en service", "PV-MS-2026", doc_pv),
    ("18_Fiche_Identifiants.pdf", "Fiche identifiants", "ID-DS-2026", doc_identifiants),
    ("19_Guide_Demarrage.pdf", "Guide de démarrage", "GD-DS-2026", doc_guide),
    ("20_Attestation_Formation.pdf", "Attestation de formation", "ATT-FORM-2026", doc_attestation),
    ("21_Feuille_Emargement_Formation.pdf", "Feuille d'émargement", "EMARG-2026", doc_emargement),
    ("22_Formulaire_Commande_Complementaire.pdf", "Commande complémentaire", "BC-COMPL-2026", doc_complementaire),
    ("23_Formulaire_Duplicata.pdf", "Demande de duplicata", "DUP-DS-2026", doc_duplicata),
    ("24_Fiche_Incident_Support.pdf", "Fiche incident support", "INC-DS-2026", doc_incident),
    ("25_Proposition_Renouvellement.pdf", "Renouvellement", "REN-DS-2026", doc_renouvellement),
    ("26_Relance_Impaye.pdf", "Relance impayé", "REL-DS-2026", doc_relance),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = []
    for filename, title, ref, fn in DOCS:
        path = build_pdf(filename, title, ref, fn())
        ok.append(path.name)
        print(f"OK  {path}")
    print(f"\n{len(ok)} PDF générés dans {OUT_DIR}")


if __name__ == "__main__":
    main()
