"""
villes_maroc.py
----------------
Coordonnées approximatives (latitude, longitude) des principales villes
marocaines. Utilisé pour afficher les offres sur une carte (app.py) et
pour les graphes de visualisation.py.
"""

VILLES_COORDS = {
    "Casablanca": (33.5731, -7.5898),
    "Rabat": (34.0209, -6.8417),
    "Marrakech": (31.6295, -7.9811),
    "Fès": (34.0331, -5.0003),
    "Tanger": (35.7595, -5.8340),
    "Agadir": (30.4278, -9.5981),
    "Kénitra": (34.2610, -6.5802),
    "Meknès": (33.8935, -5.5473),
    "Oujda": (34.6867, -1.9114),
    "Tétouan": (35.5785, -5.3684),
    "Salé": (34.0531, -6.7985),
    "Mohammedia": (33.6866, -7.3830),
    "El Jadida": (33.2549, -8.5089),
    "Nador": (35.1688, -2.9335),
    "Béni Mellal": (32.3373, -6.3498),
    "Safi": (32.2994, -9.2372),
    "Non précisé": (31.7917, -7.0926),  # centre du Maroc, fallback
}


def get_coords(ville):
    return VILLES_COORDS.get(ville, VILLES_COORDS["Non précisé"])
