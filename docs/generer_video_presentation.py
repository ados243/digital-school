"""
Génère une vidéo animée Digital School + NTT S.A.R.L.
avec maquettes d'écrans de l'application, Ken Burns, fades et overlays.

Usage :
    python docs/generer_video_presentation.py
"""

from __future__ import annotations

import asyncio
import math
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent
OUT_MP4 = OUT_DIR / "Video_Presentation_Digital_School.mp4"
LOGO = ROOT / "static" / "images" / "logo-ds.png"

W, H = 1280, 720
FPS = 24
VOICE = "fr-FR-DeniseNeural"

# Charte Digital School
PRIMARY = (0, 119, 197)
PRIMARY_LIGHT = (232, 244, 253)
BG_APP = (236, 238, 241)
BG_CARD = (255, 255, 255)
TEXT = (57, 58, 61)
MUTED = (141, 144, 150)
BORDER = (212, 215, 220)
DARK = (15, 23, 42)
WHITE = (255, 255, 255)
SIDEBAR_W = 180


def _font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _rr(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _paste_logo(img: Image.Image, xy=(24, 18), size=48):
    if not LOGO.is_file():
        return
    logo = Image.open(LOGO).convert("RGBA")
    logo.thumbnail((size, size))
    img.paste(logo, xy, logo)


def _shadow_card(base: Image.Image, box, radius=12):
    """Dessine une carte blanche avec ombre légère."""
    x0, y0, x1, y1 = box
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x0 + 3, y0 + 4, x1 + 3, y1 + 4], radius=radius, fill=(0, 0, 0, 35))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    out = Image.alpha_composite(base.convert("RGBA"), shadow)
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=BG_CARD + (255,))
    return out.convert("RGB"), ImageDraw.Draw(out.convert("RGB"))


# ─── UI mockups (vues application) ───────────────────────────────────────────


def ui_shell(active="Synthèse", page_title="Tableau de bord"):
    """Back-office Digital School : sidebar + topbar + zone contenu."""
    img = Image.new("RGB", (W, H), BG_APP)
    draw = ImageDraw.Draw(img)

    # Sidebar
    draw.rectangle([0, 0, SIDEBAR_W, H], fill=WHITE)
    draw.line([(SIDEBAR_W, 0), (SIDEBAR_W, H)], fill=BORDER, width=1)
    _paste_logo(img, (20, 22), 44)
    draw.text((76, 28), "Digital School", font=_font(22, True), fill=TEXT)
    draw.text((76, 54), "NTT S.A.R.L", font=_font(14), fill=PRIMARY)

    menu = [
        ("Inscriptions", ["Synthèse", "Élèves", "Inscriptions", "Classes"]),
        ("Finances", ["Synthèse", "Frais scolaires", "Paiements", "WhatsApp", "Comptabilité"]),
        ("Pédagogie", ["Synthèse", "Matières", "Périodes"]),
        ("GRH", ["Synthèse", "Personnel", "Paies"]),
    ]
    y = 100
    for section, items in menu:
        draw.text((24, y), section.upper(), font=_font(12, True), fill=MUTED)
        y += 28
        for item in items:
            selected = item == active or (section == active)
            if selected:
                _rr(draw, [12, y - 4, SIDEBAR_W - 12, y + 28], 8, PRIMARY_LIGHT)
            color = PRIMARY if selected else TEXT
            draw.text((28, y), item, font=_font(16, selected), fill=color)
            y += 36
        y += 10

    # Top content header
    draw.rectangle([SIDEBAR_W, 0, W, 72], fill=WHITE)
    draw.line([(SIDEBAR_W, 72), (W, 72)], fill=BORDER)
    draw.text((SIDEBAR_W + 32, 22), page_title, font=_font(26, True), fill=TEXT)
    _rr(draw, [W - 210, 18, W - 32, 54], 8, PRIMARY)
    draw.text((W - 175, 26), "Compte école", font=_font(15, True), fill=WHITE)

    return img


def ui_dashboard() -> Image.Image:
    img = ui_shell("Synthèse", "Synthèse — Établissement")
    draw = ImageDraw.Draw(img)
    kpis = [
        ("Élèves", "248", PRIMARY),
        ("Classes", "12", (10, 102, 194)),
        ("Paiements du mois", "18 450 $", (5, 150, 105)),
        ("Présences", "94 %", (217, 119, 6)),
    ]
    x = SIDEBAR_W + 32
    for title, value, color in kpis:
        _rr(draw, [x, 100, x + 380, 220], 12, WHITE, BORDER)
        draw.text((x + 24, 118), title, font=_font(16), fill=MUTED)
        draw.text((x + 24, 150), value, font=_font(40, True), fill=color)
        x += 400

    # Table panel
    _rr(draw, [SIDEBAR_W + 32, 250, W - 32, H - 40], 12, WHITE, BORDER)
    draw.text((SIDEBAR_W + 52, 270), "Dernières inscriptions", font=_font(20, True), fill=TEXT)
    headers = ["Matricule", "Élève", "Classe", "Statut"]
    rows = [
        ("ELV-0042", "Amina K.", "6ème A", "Inscrit"),
        ("ELV-0043", "Joel M.", "5ème B", "Inscrit"),
        ("ELV-0044", "Grace N.", "Terminale", "Inscrit"),
        ("ELV-0045", "Patrick L.", "3ème C", "En attente"),
    ]
    hx = SIDEBAR_W + 52
    for h in headers:
        draw.text((hx, 320), h, font=_font(15, True), fill=MUTED)
        hx += 280
    draw.line([(SIDEBAR_W + 52, 350), (W - 52, 350)], fill=BORDER)
    y = 370
    for row in rows:
        hx = SIDEBAR_W + 52
        for cell in row:
            draw.text((hx, y), cell, font=_font(16), fill=TEXT)
            hx += 280
        y += 48
    return img


def ui_finances() -> Image.Image:
    img = ui_shell("Paiements", "Paiements élèves")
    draw = ImageDraw.Draw(img)
    _rr(draw, [SIDEBAR_W + 32, 100, W - 32, 200], 12, WHITE, BORDER)
    draw.text((SIDEBAR_W + 52, 120), "Encaissement du jour", font=_font(18, True), fill=TEXT)
    draw.text((SIDEBAR_W + 52, 155), "Minerval · USD / CDF · Reçu + WhatsApp parent", font=_font(16), fill=MUTED)
    _rr(draw, [W - 280, 130, W - 60, 175], 8, PRIMARY)
    draw.text((W - 250, 140), "+ Encaisser", font=_font(16, True), fill=WHITE)

    _rr(draw, [SIDEBAR_W + 32, 230, W - 32, H - 40], 12, WHITE, BORDER)
    cols = ["Date", "Élève", "Frais", "Montant", "Mode", "Statut"]
    data = [
        ("11/08/2026", "Amina K.", "Minerval", "120 USD", "Espèces", "Validé"),
        ("11/08/2026", "Joel M.", "Minerval", "340 000 CDF", "Mobile Money", "Validé"),
        ("10/08/2026", "Grace N.", "Inscription", "50 USD", "Virement", "Validé"),
    ]
    hx = SIDEBAR_W + 52
    widths = [160, 220, 200, 220, 220, 160]
    for h, w in zip(cols, widths):
        draw.text((hx, 255), h, font=_font(15, True), fill=MUTED)
        hx += w
    y = 310
    for row in data:
        hx = SIDEBAR_W + 52
        for cell, w in zip(row, widths):
            draw.text((hx, y), cell, font=_font(16), fill=TEXT)
            hx += w
        # badge
        _rr(draw, [W - 200, y - 4, W - 90, y + 28], 999, PRIMARY_LIGHT)
        draw.text((W - 175, y), "Validé", font=_font(14, True), fill=PRIMARY)
        y += 55
    return img


def ui_whatsapp() -> Image.Image:
    img = ui_shell("WhatsApp", "WhatsApp paiements")
    draw = ImageDraw.Draw(img)
    left, mid = SIDEBAR_W + 20, 740
    _rr(draw, [left, 90, mid, H - 24], 10, WHITE, BORDER)
    draw.text((left + 16, 108), "Configuration école", font=_font(16, True), fill=TEXT)
    fields = [("Fournisseur", "Meta Cloud API"), ("Modèle", "recu_paiement"), ("Langue", "fr"), ("Statut", "Actif")]
    y = 150
    for label, val in fields:
        draw.text((left + 16, y), label, font=_font(12), fill=MUTED)
        _rr(draw, [left + 16, y + 20, mid - 24, y + 52], 8, (250, 251, 252), BORDER)
        draw.text((left + 28, y + 28), val, font=_font(13), fill=TEXT)
        y += 72

    _rr(draw, [mid + 24, 100, W - 32, 620], 26, (30, 41, 59))
    _rr(draw, [mid + 42, 125, W - 50, 595], 18, (236, 253, 245))
    draw.text((mid + 70, 145), "Parent · WhatsApp", font=_font(14, True), fill=TEXT)
    _rr(draw, [mid + 70, 185, W - 80, 360], 12, WHITE)
    draw.multiline_text(
        (mid + 88, 205),
        "Digital School\nPaiement reçu ✓\nÉlève : Amina K.\nMinerval — 120 USD",
        font=_font(14), fill=TEXT, spacing=6,
    )
    return img


def ui_visio() -> Image.Image:
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    _rr(draw, [20, 16, W - 20, 78], 10, WHITE)
    draw.text((36, 26), "Révision fractions — séance live", font=_font(16, True), fill=TEXT)
    draw.text((36, 50), "Mathématiques · 6ème A · Visio + Questions", font=_font(12), fill=MUTED)
    _rr(draw, [W - 260, 28, W - 150, 64], 8, PRIMARY)
    draw.text((W - 248, 36), "Ouvrir visio", font=_font(12, True), fill=WHITE)
    _rr(draw, [W - 135, 28, W - 40, 64], 8, (226, 232, 240))
    draw.text((W - 115, 36), "Quitter", font=_font(12, True), fill=TEXT)

    _rr(draw, [20, 95, 800, H - 20], 12, (30, 41, 59))
    draw.ellipse([300, 230, 500, 430], fill=PRIMARY)
    draw.text((350, 305), "LIVE", font=_font(28, True), fill=WHITE)
    draw.text((260, 470), "Salle de visioconférence Jitsi", font=_font(14), fill=(148, 163, 184))

    _rr(draw, [830, 95, W - 20, H - 20], 12, WHITE)
    draw.text((855, 115), "Questions", font=_font(16, True), fill=TEXT)
    _rr(draw, [1140, 115, 1175, 142], 999, PRIMARY)
    draw.text((1150, 118), "2", font=_font(12, True), fill=WHITE)
    qs = [
        ("Amina K.", "Comment simplifier 12/18 ?", False),
        ("Joel M.", "Peut-on revoir les exemples ?", True),
    ]
    y = 160
    for author, q, answered in qs:
        _rr(draw, [850, y, W - 40, y + 95], 10, PRIMARY_LIGHT if not answered else (248, 250, 252), BORDER)
        draw.text((870, y + 12), author, font=_font(12, True), fill=PRIMARY)
        draw.text((870, y + 36), q, font=_font(13), fill=TEXT)
        draw.text((870, y + 64), "Répondue" if answered else "Ouverte", font=_font(11), fill=MUTED)
        y += 110
    _rr(draw, [850, H - 100, W - 40, H - 40], 10, (250, 251, 252), BORDER)
    draw.text((870, H - 78), "Posez votre question…", font=_font(13), fill=MUTED)
    return img


def ui_portal_enseignant() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_APP)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 54], fill=WHITE)
    _paste_logo(img, (16, 6), 38)
    draw.text((64, 14), "Digital School — Mon espace", font=_font(15, True), fill=TEXT)
    for i, label in enumerate(["Mes classes", "Cours en ligne", "Messages", "Travaux"]):
        x = 500 + i * 165
        _rr(draw, [x, 10, x + 145, 42], 8, PRIMARY_LIGHT if i == 0 else (246, 247, 249))
        draw.text((x + 14, 16), label, font=_font(11, True), fill=PRIMARY if i == 0 else TEXT)
    draw.text((32, 78), "Mes classes", font=_font(26, True), fill=TEXT)
    draw.text((32, 112), "Pilotez vos classes, notes, présences et cours en visio.", font=_font(14), fill=MUTED)
    classes = [("6ème A", "32 élèves", "Titulaire"), ("5ème B", "28 élèves", "Cours"), ("3ème C", "30 élèves", "Cours")]
    x = 32
    cw = 380
    for name, meta, badge in classes:
        _rr(draw, [x, 160, x + cw, 400], 12, WHITE, BORDER)
        draw.text((x + 20, 185), name, font=_font(22, True), fill=TEXT)
        draw.text((x + 20, 225), meta, font=_font(14), fill=MUTED)
        _rr(draw, [x + 20, 280, x + 140, 312], 999, PRIMARY_LIGHT)
        draw.text((x + 38, 286), badge, font=_font(12, True), fill=PRIMARY)
        draw.text((x + 20, 345), "Ouvrir la classe →", font=_font(13, True), fill=PRIMARY)
        x += cw + 20
    return img


def ui_portal_parent() -> Image.Image:
    img = Image.new("RGB", (W, H), BG_APP)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 54], fill=WHITE)
    _paste_logo(img, (16, 6), 38)
    draw.text((64, 14), "Espace Parent", font=_font(15, True), fill=TEXT)
    draw.text((32, 80), "Mes enfants", font=_font(26, True), fill=TEXT)
    kids = [("Amina K.", "6ème A", "Soldes à jour", "Présence 96 %"), ("Joel M.", "5ème B", "Reste 40 USD", "Présence 91 %")]
    x = 32
    cw = 580
    for name, classe, finance, presence in kids:
        _rr(draw, [x, 130, x + cw, 460], 12, WHITE, BORDER)
        draw.ellipse([x + 24, 170, x + 104, 250], fill=PRIMARY_LIGHT)
        draw.text((x + 48, 195), name[0], font=_font(24, True), fill=PRIMARY)
        draw.text((x + 130, 175), name, font=_font(20, True), fill=TEXT)
        draw.text((x + 130, 210), classe, font=_font(14), fill=MUTED)
        draw.text((x + 130, 265), finance, font=_font(16, True), fill=PRIMARY)
        draw.text((x + 130, 300), presence, font=_font(14), fill=TEXT)
        draw.text((x + 130, 360), "Notes · Présences · Frais · Messages", font=_font(13), fill=MUTED)
        x += cw + 24
    return img


def title_card(title: str, subtitle: str, bullets: list[str] | None = None) -> Image.Image:
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(DARK[0] * (1 - t) + 20 * t)
        g = int(DARK[1] * (1 - t) + 50 * t)
        b = int(DARK[2] * (1 - t) + 90 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    draw.rectangle([0, 0, 16, H], fill=PRIMARY)
    _paste_logo(img, (70, 60), 90)
    draw.text((180, 75), "Digital School", font=_font(28, True), fill=WHITE)
    draw.text((180, 115), "Conçu par NTT S.A.R.L", font=_font(18), fill=PRIMARY)

    y = 280
    draw.text((80, y), title, font=_font(64, True), fill=WHITE)
    y += 90
    if subtitle:
        for line in _wrap_simple(subtitle, 42):
            draw.text((80, y), line, font=_font(32), fill=(186, 198, 214))
            y += 48
    if bullets:
        y += 30
        for b in bullets:
            draw.text((100, y), "▸  " + b, font=_font(28), fill=(226, 232, 240))
            y += 52

    draw.rectangle([0, H - 64, W, H], fill=(8, 15, 30))
    draw.text((80, H - 42), "NTT S.A.R.L  ·  Digital School", font=_font(20), fill=(148, 163, 184))
    return img


def _wrap_simple(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


def compose_overlay(ui: Image.Image, label: str) -> Image.Image:
    """UI + bandeau titre animable."""
    base = ui.copy().resize((W, H), Image.BILINEAR)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([0, H - 100, W, H], fill=(15, 23, 42, 215))
    d.text((40, H - 75), label, font=_font(22, True), fill=WHITE + (255,))
    d.text((40, H - 42), "Vue application Digital School", font=_font(14), fill=(148, 163, 184, 255))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


# ─── Animations ──────────────────────────────────────────────────────────────


def ease_in_out(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * min(1.0, max(0.0, t)))


def ken_burns_frames(img: Image.Image, duration: float, zoom_end: float = 1.08, pan=(0.03, 0.02)):
    """Génère des frames avec zoom/pan progressif (écriture streaming)."""
    n = max(1, int(duration * FPS))
    src = img.convert("RGB").resize((W, H), Image.BILINEAR)
    sw, sh = src.size
    for i in range(n):
        t = ease_in_out(i / max(1, n - 1))
        zoom = 1.0 + (zoom_end - 1.0) * t
        cw, ch = max(2, int(W / zoom)), max(2, int(H / zoom))
        # force even dims for yuv420
        cw -= cw % 2
        ch -= ch % 2
        cx = sw // 2 + int(pan[0] * sw * (t - 0.5) * 2)
        cy = sh // 2 + int(pan[1] * sh * (t - 0.5) * 2)
        x0 = max(0, min(sw - cw, cx - cw // 2))
        y0 = max(0, min(sh - ch, cy - ch // 2))
        crop = src.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
        yield np.asarray(crop)


def fade_transition(a: np.ndarray, b: np.ndarray, frames: int = 8):
    for i in range(frames):
        t = ease_in_out((i + 1) / frames)
        yield (a.astype(np.float32) * (1 - t) + b.astype(np.float32) * t).astype(np.uint8)


def slide_in_frames(img: Image.Image, duration: float = 0.4, direction="left"):
    n = max(1, int(duration * FPS))
    base = np.asarray(img.convert("RGB").resize((W, H), Image.BILINEAR))
    for i in range(n):
        t = ease_in_out((i + 1) / n)
        canvas = np.full_like(base, np.array(DARK, dtype=np.uint8))
        if direction == "left":
            offset = int((1 - t) * W)
            if offset < W:
                canvas[:, offset:] = base[:, : W - offset]
        else:
            offset = int((1 - t) * H)
            if offset < H:
                canvas[offset:, :] = base[: H - offset, :]
        yield canvas


# ─── Audio / montage ─────────────────────────────────────────────────────────


async def synthesize(text: str, path: Path) -> None:
    await edge_tts.Communicate(text, VOICE).save(str(path))


def audio_duration(path: Path) -> float:
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr or "")
    if m:
        h, m_, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
        return h * 3600 + m_ * 60 + s
    return max(4.0, path.stat().st_size / 3500)


def mux(video: Path, audios: list[Path], out: Path, tmp: Path):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    lst = tmp / "a.txt"
    lines = []
    for a in audios:
        p = str(a).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{p}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    voice = tmp / "voice.mp3"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(voice)], check=True, capture_output=True)
    subprocess.run(
        [ff, "-y", "-i", str(video), "-i", str(voice), "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out)],
        check=True,
        capture_output=True,
    )


SCENES = [
    {
        "kind": "title",
        "title": "NTT S.A.R.L",
        "subtitle": "Startup technologique — conceptrice de Digital School",
        "bullets": [
            "Solutions numériques concrètes",
            "Produit phare : Digital School",
            "Pour les écoles d’aujourd’hui",
        ],
        "vo": (
            "NTT S.A.R.L est une startup technologique qui conçoit des solutions numériques "
            "pour les organisations. Notre produit phare pour l’éducation : Digital School."
        ),
        "zoom": 1.08,
    },
    {
        "kind": "title",
        "title": "Le défi des écoles",
        "subtitle": "Des outils dispersés freinent la gestion",
        "bullets": ["Cahiers et Excel", "Paiements peu tracés", "Parents mal informés"],
        "vo": (
            "Dans beaucoup d’écoles, inscriptions, paiements, notes et communication parents "
            "sont encore dispersés. Résultat : perte de temps, litiges, manque de visibilité."
        ),
        "zoom": 1.1,
    },
    {
        "kind": "ui",
        "builder": ui_dashboard,
        "label": "Vue application — Synthèse établissement",
        "vo": (
            "Digital School regroupe toute la gestion scolaire dans une plateforme unique, "
            "multi-écoles, avec un tableau de bord clair pour la direction."
        ),
        "zoom": 1.14,
        "pan": (0.05, 0.03),
    },
    {
        "kind": "ui",
        "builder": ui_dashboard,
        "label": "Inscriptions & classes — effectifs sous contrôle",
        "vo": (
            "Vous organisez vos classes, créez les fiches élèves et parents, "
            "et inscrivez pour l’année scolaire en cours. Les matricules sont générés automatiquement."
        ),
        "zoom": 1.18,
        "pan": (-0.04, 0.05),
    },
    {
        "kind": "ui",
        "builder": ui_finances,
        "label": "Finances — encaissements Minerval CDF / USD",
        "vo": (
            "Côté finances : barèmes de frais, encaissements multi-devises CDF et USD, "
            "reçus, et suivi des paiements élèves."
        ),
        "zoom": 1.12,
        "pan": (0.03, -0.02),
    },
    {
        "kind": "ui",
        "builder": ui_whatsapp,
        "label": "WhatsApp — notification automatique aux parents",
        "vo": (
            "À chaque paiement validé, le parent peut recevoir une notification WhatsApp "
            "avec les informations du reçu. Plus de transparence, moins de litiges."
        ),
        "zoom": 1.15,
        "pan": (0.06, 0.02),
    },
    {
        "kind": "ui",
        "builder": ui_portal_enseignant,
        "label": "Portail enseignant — classes, notes, cours",
        "vo": (
            "Les enseignants pilotent leurs classes, travaux, notes et présences "
            "depuis un espace dédié, simple et rapide."
        ),
        "zoom": 1.1,
        "pan": (-0.03, 0.04),
    },
    {
        "kind": "ui",
        "builder": ui_visio,
        "label": "Cours en visioconférence + questions en direct",
        "vo": (
            "Les cours se dispensent aussi à distance : visioconférence intégrée, "
            "les élèves rejoignent depuis leur portail, et posent des questions en direct."
        ),
        "zoom": 1.16,
        "pan": (0.02, 0.05),
    },
    {
        "kind": "ui",
        "builder": ui_portal_parent,
        "label": "Portail parent — suivi enfants, frais, présence",
        "vo": (
            "Les parents suivent leurs enfants : notes, présences, situation des frais, "
            "annonces et messagerie avec l’école."
        ),
        "zoom": 1.12,
        "pan": (0.04, -0.03),
    },
    {
        "kind": "title",
        "title": "Digital School",
        "subtitle": "Conçu par NTT S.A.R.L — Demandez une démonstration",
        "bullets": ["Inscriptions · Finances · Pédagogie", "Visio · Portails · GRH", "Une plateforme pour votre école"],
        "vo": (
            "Digital School, conçu par NTT S.A.R.L. "
            "Demandez une démonstration pour votre établissement."
        ),
        "zoom": 1.06,
    },
]


async def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        audio_dir = tmp / "audio"
        audio_dir.mkdir()

        print("1/4 — Voix off…")
        audios = []
        durations = []
        for i, scene in enumerate(SCENES):
            ap = audio_dir / f"{i:02d}.mp3"
            await synthesize(scene["vo"], ap)
            audios.append(ap)
            dur = max(4.5, audio_duration(ap) + 0.45)
            durations.append(dur)
            print(f"   • scène {i + 1}/{len(SCENES)} — {dur:.1f}s")

        print("2/4 — Rendu slides + UI…")
        images = []
        for scene in SCENES:
            if scene["kind"] == "title":
                images.append(title_card(scene["title"], scene["subtitle"], scene.get("bullets")))
            else:
                ui = scene["builder"]()
                images.append(compose_overlay(ui, scene["label"]))

        print("3/4 — Animations (Ken Burns, fades, slide-in)…")
        silent = tmp / "silent.mp4"
        writer = imageio.get_writer(
            str(silent), fps=FPS, codec="libx264", quality=7, pixelformat="yuv420p", macro_block_size=1
        )
        prev_last = None
        try:
            for idx, (img, dur, scene) in enumerate(zip(images, durations, SCENES)):
                img = img.resize((W, H), Image.BILINEAR)
                intro_frames = list(slide_in_frames(img, 0.35, "left" if idx % 2 == 0 else "up"))
                if prev_last is not None and intro_frames:
                    for fr in fade_transition(prev_last, intro_frames[-1], frames=8):
                        writer.append_data(fr)
                for fr in intro_frames:
                    writer.append_data(fr)

                last = intro_frames[-1] if intro_frames else np.asarray(img)
                for fr in ken_burns_frames(
                    img,
                    max(0.8, dur - 0.35),
                    zoom_end=min(1.12, scene.get("zoom", 1.08)),
                    pan=scene.get("pan", (0.03, 0.02)),
                ):
                    writer.append_data(fr)
                    last = fr
                prev_last = last
                print(f"   • anim scène {idx + 1} OK")
        finally:
            writer.close()

        print("4/4 — Mux audio…")
        target = OUT_MP4
        try:
            mux(silent, audios, target, tmp)
        except Exception:
            target = OUT_DIR / "Video_Presentation_Digital_School_Animee.mp4"
            mux(silent, audios, target, tmp)

        total = sum(durations)
        print(f"Vidéo générée : {target}")
        print(f"Durée estimée : {total:.0f} s (~{total/60:.1f} min)")
        return target


if __name__ == "__main__":
    asyncio.run(build())
