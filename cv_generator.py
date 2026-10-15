"""
cv_generator.py
----------------
Génère un CV en PDF (une page, sobre) à partir d'un dictionnaire
d'informations saisies par l'utilisateur dans l'application Streamlit.

Utilisation :
    from cv_generator import generer_cv_pdf
    pdf_bytes = generer_cv_pdf(infos)
"""

from fpdf import FPDF

BLEU = (46, 134, 171)   # #2E86AB, couleur d'accent du projet
GRIS_FONCE = (50, 50, 50)

# La police intégrée "helvetica" de fpdf2 ne supporte que le Latin-1.
# Les guillemets/apostrophes "intelligents" (’ “ ”), tirets longs (— –),
# points de suspension (…) etc. (souvent collés depuis Word) plantent sinon
# avec FPDFUnicodeEncodingException. On les remplace par leurs équivalents
# ASCII, puis on filtre tout caractère encore non supporté en sécurité.
_REMPLACEMENTS = {
    "\u2019": "'", "\u2018": "'",      # ’ ‘
    "\u201c": '"', "\u201d": '"',      # “ ”
    "\u2013": "-", "\u2014": "-",      # – —
    "\u2026": "...",                   # …
    "\u00a0": " ",                     # espace insécable
}


def _nettoyer_texte(texte):
    if texte is None:
        return ""
    texte = str(texte)
    for caractere, remplacement in _REMPLACEMENTS.items():
        texte = texte.replace(caractere, remplacement)
    # filet de sécurité : tout caractère encore hors Latin-1 est retiré
    return texte.encode("latin-1", errors="replace").decode("latin-1")


class CV(FPDF):
    def header(self):
        pass

    def footer(self):
        pass


def _section_titre(pdf, titre):
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 8, titre.upper(), ln=True)
    pdf.set_draw_color(*BLEU)
    pdf.set_line_width(0.5)
    y = pdf.get_y()
    pdf.line(pdf.get_x(), y, pdf.get_x() + 190, y)
    pdf.ln(3)
    pdf.set_text_color(*GRIS_FONCE)


def generer_cv_pdf(infos: dict) -> bytes:
    """
    infos attend les clés :
        nom, prenom, poste_recherche, email, telephone, ville,
        formation, experiences, competences, langues, a_propos
    (chaînes de caractères ; les champs vides sont simplement ignorés)
    """
    infos = {cle: _nettoyer_texte(valeur) for cle, valeur in infos.items()}

    pdf = CV(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # ---- En-tête ----
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*BLEU)
    nom_complet = f"{infos.get('prenom', '')} {infos.get('nom', '')}".strip()
    pdf.cell(0, 12, nom_complet or "Nom Prénom", ln=True)

    if infos.get("poste_recherche"):
        pdf.set_font("Helvetica", "", 13)
        pdf.set_text_color(*GRIS_FONCE)
        pdf.cell(0, 8, infos["poste_recherche"], ln=True)

    # ---- Contact ----
    pdf.set_font("Helvetica", "", 10)
    contact_parts = [
        p for p in [
            infos.get("email"), infos.get("telephone"), infos.get("ville")
        ] if p
    ]
    if contact_parts:
        pdf.cell(0, 6, "  |  ".join(contact_parts), ln=True)

    # ---- À propos ----
    if infos.get("a_propos"):
        _section_titre(pdf, "À propos")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, infos["a_propos"])

    # ---- Formation ----
    if infos.get("formation"):
        _section_titre(pdf, "Formation")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, infos["formation"])

    # ---- Expériences ----
    if infos.get("experiences"):
        _section_titre(pdf, "Expériences")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, infos["experiences"])

    # ---- Compétences ----
    if infos.get("competences"):
        _section_titre(pdf, "Compétences")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, infos["competences"])

    # ---- Langues ----
    if infos.get("langues"):
        _section_titre(pdf, "Langues")
        pdf.set_font("Helvetica", "", 10.5)
        pdf.multi_cell(0, 5.5, infos["langues"])

    return bytes(pdf.output())