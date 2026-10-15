"""
mailer.py
---------
Deux choses :
  1) Construire un lien Gmail "composer" : un clic ouvre Gmail dans le navigateur
     avec destinataire, objet et message déjà remplis (message de demande de stage en français).
  2) Envoyer le code de vérification de l'adresse email (SMTP, ex. compte Gmail + mot de passe d'application).
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def extract_email(text):
    """Première adresse email trouvée dans un texte (description d'offre), sinon ''."""
    if not text:
        return ""
    for m in EMAIL_RE.findall(str(text)):
        if not m.lower().endswith(_IMG_EXT):
            return m
    return ""


# ------------------------------------------------------------ Gmail ----

def gmail_compose(to="", subject="", body="", account=None):
    """Lien qui ouvre la fenêtre de rédaction Gmail (navigateur), message prérempli."""
    params = [("view", "cm"), ("fs", "1")]
    if to:
        params.append(("to", to))
    params += [("su", subject), ("body", body)]
    # Si l'utilisateur est connecté avec une adresse Gmail, on demande ce compte-là.
    if account and account.lower().endswith(("@gmail.com", "@googlemail.com")):
        params.append(("authuser", account))
    return "https://mail.google.com/mail/?" + "&".join(f"{k}={quote(str(v), safe='@')}" for k, v in params)


def message_stage(titre=None, entreprise=None, source=None, profil=None):
    """(objet, corps) d'une demande de stage, toujours en français."""
    p = profil or {}
    nom = (p.get("nom") or "").strip()
    formation = (p.get("formation") or "").strip().rstrip(".")
    cible = f"au sein de {entreprise}" if entreprise else "au sein de votre entreprise"

    if titre:
        objet = f"Demande de stage – {titre}"
        lien_offre = f", en lien avec votre annonce « {titre} »" + (f" publiée sur {source}" if source else "")
    else:
        objet = "Demande de stage – candidature spontanée"
        lien_offre = ""

    intro = f"Je me permets de vous contacter afin de solliciter un stage {cible}{lien_offre}."
    if formation:
        profil_ligne = f"Je suis actuellement {formation}."
    else:
        profil_ligne = ("Je suis à la recherche d'un stage dans le domaine de l'intelligence "
                        "artificielle et de l'analyse de données.")

    lignes = [
        "Bonjour Madame, Monsieur,", "",
        intro, "",
        profil_ligne,
        "Motivé(e) et sérieux(se), je souhaite mettre en pratique mes connaissances et acquérir "
        "une expérience concrète au sein de votre équipe. Vous trouverez mon CV en pièce jointe.", "",
        "Je reste disponible pour un entretien à votre convenance et vous remercie par avance "
        "pour l'attention portée à ma demande.", "",
        "Cordialement,",
    ]
    signature = [x for x in (nom, p.get("telephone"), p.get("ville")) if x]
    return objet, "\n".join(lignes + signature)


# -------------------------------------------------- code de vérification ----

def smtp_configured():
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def send_code(to, code, subject, text):
    """Envoie l'email contenant le code. Lève une exception si l'envoi échoue."""
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    pwd = os.environ["SMTP_PASSWORD"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_FROM", user)
    msg["To"] = to
    msg.set_content(text)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=15) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
