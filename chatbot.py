"""
chatbot.py
----------
Chatbot hors-ligne (aucune API, aucune clé) qui répond aux questions des
visiteurs sur les offres d'emploi et les entreprises IA de Marrakech, en
Darija (écriture latine), français ou anglais.

Il fonctionne par mots-clés + recherche dans les données du projet :
    - offres      : liste de dicts (id, titre, ville, source, description, lien)
    - entreprises : liste de dicts (nom, adresse, telephone, site_web,
                    google_maps, categorie, note, nombre_avis, email)

Utilisé par app_web.py via la route /api/chat.
"""

import re
import unicodedata
from urllib.parse import quote

import mailer
from villes_maroc import VILLES_COORDS


# ---------------------------------------------------------------- outils --

def norm(texte):
    """minuscules, sans accents, ponctuation -> espaces."""
    texte = unicodedata.normalize("NFKD", str(texte).lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texte).strip()


STOP = set(
    "le la les un une des de du d l a au aux en et ou pour sur dans par avec sans ce ces "
    "cet cette je tu il elle on nous vous ils elles me te se mon ma mes est sont y ai as "
    "qui que quoi quel quelle quels quelles si ne pas plus tres bien svp stp please the of "
    "in at is are to for and my i you do does can any there what which where how show give "
    "list kayn kayna kaynin wach dyal dial f fi li lli o w hna had hadi hada ana nta 3la "
    "3ndk 3ndi bghit bgha n9der ila daba 3tini goliya chi chno achno fin ch7al chhal combien "
    "comment kifach".split()
)

DARIJA = set(
    "chhal chal ch7al kifach kifash fin dyal dial khdma khedma lakhdma chirka charika chno "
    "achno wach bghit 3tini 3ndk 3ndi daba kayn kayna kaynin hna ahsan afdal chokran choukran "
    "salam mrhba marhba bzaf n9der nposti npostuli nposter wakha mzyan lqit ma3ndich 3la "
    "ila slm goliya".split()
)

CITY_ALIASES = {
    "casa": "Casablanca", "marrakesh": "Marrakech", "marrakch": "Marrakech",
    "kech": "Marrakech", "tanja": "Tanger", "tangier": "Tanger", "rbat": "Rabat",
    "fez": "Fès", "beni mellal": "Béni Mellal", "kenitra": "Kénitra",
}

GREET = {"salam", "slm", "bonjour", "salut", "hello", "hi", "hey", "ahlan", "mrhba",
         "marhba", "bonsoir", "salamu"}
THANKS = {"merci", "choukran", "chokran", "shukran", "thanks", "thx", "barakallah", "cool"}
OFFRE_W = {"offre", "offres", "emploi", "emplois", "job", "jobs", "khdma", "khedma",
           "lakhdma", "travail", "poste", "postes", "recrutement", "stage", "stages"}
ENT_W = {"entreprise", "entreprises", "societe", "societes", "chirka", "charika", "chorkat",
         "agence", "agences", "company", "companies", "startup", "startups", "boite"}
COUNT_W = {"chhal", "chal", "ch7al", "combien", "nombre", "many", "count", "total"}
BEST_W = {"meilleur", "meilleurs", "meilleure", "meilleures", "top", "ahsan", "afdal",
          "mieux", "best", "note", "notes", "rating", "populaire", "populaires"}
PHONE_W = {"telephone", "tel", "numero", "num", "phone", "appeler", "appel", "gsm",
           "whatsapp", "numro", "tlf"}
EMAIL_W = {"email", "mail", "mails", "gmail", "courriel"}
ADDR_W = {"adresse", "localisation", "map", "maps", "emplacement", "situe", "location",
          "address", "located", "fin"}
CONTACT_W = {"contact", "contacter", "joindre"}
APPLY_W = {"postuler", "postule", "candidater", "candidature", "apply", "nposti", "npostuli",
           "nposter", "tqdem", "t9dem", "candidatures"}
CV_W = {"cv", "curriculum", "resume"}
DASH_W = {"dashboard", "graphe", "graphes", "graphique", "graphiques", "statistique",
          "statistiques", "stats", "chart", "charts"}
HELP_W = {"aide", "help", "aider", "3awnni", "3awni"}

KEYWORDS_OFFRES = [
    "data scientist", "data analyst", "data engineer", "machine learning", "deep learning",
    "nlp", "computer vision", "intelligence artificielle", "ingenieur", "developpeur",
    "stagiaire", "python", "ia", "ai",
]

CATEGORIES_SYN = {
    "ecole": ["enseignement", "ecole"], "ecoles": ["enseignement", "ecole"],
    "universite": ["universite"], "universites": ["universite"],
    "hotel": ["hotel"], "hotels": ["hotel"], "banque": ["banque"], "banques": ["banque"],
    "finance": ["banque"], "coworking": ["coworking"], "consultant": ["consultant"],
    "consulting": ["consultant"], "voyage": ["voyages"], "voyages": ["voyages"],
    "fabricant": ["fabricant"], "association": ["association", "organisme"],
}

GENERIC_NOMS = {"marrakech", "marrakesh", "maroc", "morocco", "agence", "agency", "group",
                "groupe", "services", "service", "centre", "center"}


# -------------------------------------------------------------- entités --

def detecter_ville(n):
    padded = f" {n} "
    for alias, ville in CITY_ALIASES.items():
        if f" {alias} " in padded:
            return ville
    for ville in VILLES_COORDS:
        if ville != "Non précisé" and f" {norm(ville)} " in padded:
            return ville
    return None


def detecter_categories(tokens):
    mots = []
    for t in tokens:
        mots += CATEGORIES_SYN.get(t, [])
    return mots


def trouver_entreprise(n, entreprises):
    padded = f" {n} "
    toks = set(n.split())
    meilleur, meilleur_score = None, 0
    for c in entreprises:
        cn = norm(c["nom"])
        if len(cn) >= 4 and f" {cn} " in padded:
            score = 10 + len(cn)
        else:
            distinctifs = [t for t in cn.split() if t not in GENERIC_NOMS and len(t) >= 3]
            if not distinctifs or not all(t in toks for t in distinctifs):
                continue
            if max(len(t) for t in distinctifs) < 4:
                continue
            score = len(distinctifs)
        if score > meilleur_score:
            meilleur, meilleur_score = c, score
    return meilleur


def mots_cles_offres(n, tokens):
    trouves = [k for k in KEYWORDS_OFFRES if f" {k} " in f" {n} "]
    if trouves:
        return trouves
    reste = [t for t in tokens if t not in STOP and len(t) >= 4
             and t not in OFFRE_W | ENT_W | COUNT_W | BEST_W | PHONE_W | EMAIL_W | ADDR_W
             | CONTACT_W | APPLY_W | CV_W | DASH_W | HELP_W | GREET | THANKS]
    return reste


# ---------------------------------------------------------- réponses ----

def _fmt_ent(c):
    note = f" ({c['note']}/5)" if c.get("note") else ""
    return f"• {c['nom']}{note}"


def mailto(c):
    """Lien Gmail (navigateur) avec un message de demande de stage prérempli, en français."""
    objet, corps = mailer.message_stage(entreprise=c.get("nom"))
    return mailer.gmail_compose(c.get("email") or "", objet, corps)


def repondre(message, offres, entreprises):
    """Retourne {"reply": str, "links": [{"label", "url"}]}."""
    n = norm(message)
    tokens = n.split()
    tset = set(tokens)
    darija = bool(tset & DARIJA)

    def L(fr, da):
        return da if darija else fr

    def out(texte, links=None):
        return {"reply": texte, "links": links or []}

    if not tokens:
        return out(L("Écris-moi ta question", "Kteb liya soual dyalek"))

    ville = detecter_ville(n)
    ent = trouver_entreprise(n, entreprises)

    # 1) infos sur une entreprise précise ---------------------------------
    if ent:
        links = []
        lignes = [f"{ent['nom']}"]
        if ent.get("categorie"):
            lignes.append(f"Catégorie : {ent['categorie']}")
        if ent.get("adresse"):
            lignes.append(f"Adresse : {ent['adresse']}")
        if ent.get("telephone"):
            lignes.append(f"Tél : {ent['telephone']}")
        if ent.get("note"):
            avis = f" ({int(ent['nombre_avis'])} avis)" if ent.get("nombre_avis") else ""
            lignes.append(f"Note : {ent['note']}/5{avis}")
        if tset & EMAIL_W:
            if ent.get("email"):
                lignes.append(f"Email : {ent['email']}")
            else:
                lignes.append(L(
                    "Je n'ai pas d'email pour cette entreprise dans les données. "
                    "Le bouton ci-dessous ouvre un email prêt à envoyer (tu ajoutes l'adresse).",
                    "Ma3ndich l'email dyalha f data. L'bouton lta7t kay7ell email wajed, "
                    "ghi zid l'adresse."))
        if ent.get("google_maps"):
            links.append({"label": "Localisation", "url": ent["google_maps"]})
        if ent.get("site_web"):
            links.append({"label": "Site web", "url": ent["site_web"]})
        links.append({"label": "Contacter par email", "url": mailto(ent)})
        return out("\n".join(lignes), links)

    # 2) politesse ---------------------------------------------------------
    if tset & THANKS and len(tokens) <= 4:
        return out(L("Avec plaisir !", "Bla jmil !"))
    if tset & GREET and len(tokens) <= 3:
        return out(L("Bonjour Je peux t'aider à chercher des offres, des entreprises à "
                     "Marrakech, ou t'expliquer comment postuler. Pose ta question !",
                     "Salam N9der n3awnek tl9a l'offres, les entreprises f Marrakech, "
                     "wla nchrah lik kifach tposti. Soul !"))

    # 3) actions : postuler / CV / dashboard / aide ---------------------------
    if tset & APPLY_W or "marquer" in tset or "marque" in tset:
        return out(L(
            "Pour postuler :\n"
            "1. Offres : « Postuler » ouvre l'annonce d'origine pour envoyer ton CV.\n"
            "2. Entreprises : « Postuler » ouvre leur site (candidature spontanée) et "
            "« Contacter par email » prépare un email.\n"
            "3. Clique « Marquer comme postulé » pour suivre tes candidatures.\n"
            "Pas encore de CV ? Génère-le dans l'onglet CV.",
            "Bach tposti :\n"
            "1. F l'offres : « Postuler » kay7ell l'annonce l'asliya bach t'sifet CV.\n"
            "2. F l'entreprises : « Postuler » kay7ell site dyalhom (candidature spontanée) o "
            "« Contacter par email » kaydir lik email wajed.\n"
            "3. Clicki « Marquer comme postulé » bach tb9a t'tab3 l'candidatures dyalek.\n"
            "Ma3ndekch CV ? Sayeb-o f onglet CV."),
            [{"label": "Générer mon CV", "url": "/cv"}])
    if tset & CV_W:
        return out(L("Tu peux générer ton CV en PDF gratuitement :",
                     "T9der tsayb CV dyalek PDF b blach :"),
                   [{"label": "Générer mon CV", "url": "/cv"}])
    if tset & DASH_W:
        return out(L("Les graphes et statistiques sont dans le Dashboard :",
                     "L'graphes o l'statistiques kaynin f Dashboard :"),
                   [{"label": "Dashboard", "url": "/dashboard"}])
    if tset & HELP_W or n in {"aide", "help", "menu"}:
        return out(L("Je peux répondre à : « combien d'offres à Rabat ? », « offres data "
                     "scientist », « entreprises à Marrakech », « meilleures entreprises », "
                     "« téléphone de <nom entreprise> », « comment postuler ? ».",
                     "N9der njawb 3la : « chhal mn offre f Rabat ? », « offres data scientist », "
                     "« entreprises f Marrakech », « ahsan les entreprises », "
                     "« telephone dyal <smiya dyal chirka> », « kifach nposti ? »."))

    # 4) meilleures entreprises --------------------------------------------
    if tset & BEST_W and (tset & ENT_W or not tset & OFFRE_W):
        candidates = [c for c in entreprises if c.get("note") and (c.get("nombre_avis") or 0) >= 10]
        candidates.sort(key=lambda c: (-c["note"], -(c.get("nombre_avis") or 0)))
        if not candidates:
            return out(L("Pas assez de notes dans les données.", "Ma3ndich bzaf notes f data."))
        lignes = [_fmt_ent(c) + f" ({int(c['nombre_avis'])} avis)" for c in candidates[:5]]
        return out(L("Les mieux notées à Marrakech (10 avis minimum) :\n",
                     "L'ahsan notes f Marrakech (3la l'a9al 10 avis) :\n") + "\n".join(lignes),
                   [{"label": "Voir toutes les entreprises", "url": "/entreprises?tri=note"}])

    # 5) entreprises ---------------------------------------------------------
    if tset & ENT_W or (detecter_categories(tokens) and not tset & OFFRE_W):
        liste = entreprises
        cats = detecter_categories(tokens)
        if cats:
            liste = [c for c in liste if any(m in norm(c.get("categorie", "")) for m in cats)]
        if ville and ville != "Marrakech":
            return out(L(f"Mes données d'entreprises couvrent seulement Marrakech, pas {ville}. "
                         "Pour les offres à " + ville + ", demande « offres " + ville + " ».",
                         f"Data dyal l'entreprises ghi f Marrakech, machi {ville}. "
                         f"L'offres f {ville} soul : « offres {ville} »."))
        liste = sorted(liste, key=lambda c: -(c.get("note") or 0))
        if not liste:
            return out(L("Je n'ai trouvé aucune entreprise pour ça.", "Ma lqit ta chirka."))
        lignes = [_fmt_ent(c) for c in liste[:5]]
        suite = f"\n… +{len(liste) - 5}" if len(liste) > 5 else ""
        q = f"?q={quote(cats[0])}" if cats else ""
        return out(L(f"{len(liste)} entreprise(s) à Marrakech :\n", f"{len(liste)} chirka f Marrakech :\n")
                   + "\n".join(lignes) + suite,
                   [{"label": "Voir les entreprises", "url": "/entreprises" + q}])

    # 6) offres ---------------------------------------------------------------
    if tset & OFFRE_W or ville or (tset & COUNT_W) or mots_cles_offres(n, tokens):
        liste = offres
        if ville:
            liste = [o for o in liste if o["ville"] == ville]
        mots = mots_cles_offres(n, tokens)
        if mots:
            def match(o):
                texte = norm(o["titre"] + " " + o["description"])
                return all(f" {m} " in f" {texte} " or m in texte for m in mots)
            liste = [o for o in liste if match(o)]

        if (tset & COUNT_W) and not liste:
            return out(L("Aucune offre trouvée pour ces critères.", "Ma lqit ta offre b had l'critères."))
        if not liste:
            if tset & OFFRE_W or ville:
                return out(L("Je n'ai trouvé aucune offre pour ça. Essaie une autre ville ou un autre mot-clé.",
                             "Ma lqit ta offre. Jarreb ville okhra wla mot-clé akhor."))
            return out(L("Je n'ai pas compris Tape « aide » pour voir ce que je sais faire.",
                         "Ma fhemtch Kteb « aide » bach tchof chno n9der ndir."))
        qs = []
        if ville:
            qs.append(f"ville={quote(ville)}")
        if mots:
            qs.append(f"q={quote(' '.join(mots))}")
        lien_liste = "/?" + "&".join(qs) if qs else "/"
        ou = f" à {ville}" if ville else ""
        ou_d = f" f {ville}" if ville else ""
        if tset & COUNT_W:
            return out(L(f"Il y a {len(liste)} offre(s){ou}.", f"Kayn {len(liste)} offre{ou_d}."),
                       [{"label": "Voir les offres", "url": lien_liste}])
        lignes = [f"• {o['titre']} ({o['ville']})" for o in liste[:5]]
        suite = f"\n… +{len(liste) - 5}" if len(liste) > 5 else ""
        liens = [{"label": f"{o['titre'][:35]}", "url": f"/offre/{o['id']}"} for o in liste[:3]]
        liens.append({"label": "Toutes les offres", "url": lien_liste})
        return out(L(f"{len(liste)} offre(s){ou} :\n", f"{len(liste)} offre{ou_d} :\n")
                   + "\n".join(lignes) + suite, liens)

    # 7) infos générales ---------------------------------------------------------
    return out(L("Je n'ai pas compris Tape « aide » pour voir ce que je sais faire.",
                 "Ma fhemtch Kteb « aide » bach tchof chno n9der ndir."))
