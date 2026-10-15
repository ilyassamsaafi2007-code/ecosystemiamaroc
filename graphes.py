"""
graphes.py
----------
Fonctions qui construisent les figures matplotlib/seaborn à partir des
données nettoyées. Chaque fonction retourne un objet Figure (ne
sauvegarde rien elle-même) — utilisé par :
    - visualisation.py (CLI) : sauvegarde chaque figure en PNG
    - app.py (Dashboard Streamlit) : affiche chaque figure avec st.pyplot
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from villes_maroc import get_coords

sns.set_theme(style="whitegrid")


def fig_bar_villes(df):
    fig, ax = plt.subplots(figsize=(9, 5))
    df["ville"].value_counts().plot(kind="bar", color="#2E86AB", ax=ax)
    ax.set_title("Nombre d'offres IA par ville")
    ax.set_xlabel("Ville")
    ax.set_ylabel("Nombre d'offres")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


def fig_pie_sources(df):
    fig, ax = plt.subplots(figsize=(6, 6))
    df["source"].value_counts().plot(
        kind="pie", autopct="%1.1f%%", startangle=90,
        colors=["#2E86AB", "#F26419", "#6A4C93"], ax=ax
    )
    ax.set_title("Répartition des offres par source")
    ax.set_ylabel("")
    fig.tight_layout()
    return fig


def fig_hist_longueur(df):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(df["longueur_description"].dropna(), bins=25, color="#6A4C93")
    ax.set_title("Distribution de la longueur des descriptions")
    ax.set_xlabel("Longueur (nombre de caractères)")
    ax.set_ylabel("Fréquence")
    fig.tight_layout()
    return fig


def fig_boxplot_longueur(df):
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=df, x="ville", y="longueur_description", ax=ax)
    ax.set_title("Longueur des descriptions par ville")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


def fig_heatmap_ville_source(df):
    table = pd.crosstab(df["ville"], df["source"])
    fig, ax = plt.subplots(figsize=(7, 8))
    sns.heatmap(table, annot=True, fmt="d", cmap="YlGnBu", ax=ax)
    ax.set_title("Nombre d'offres par ville et par source")
    fig.tight_layout()
    return fig


def fig_scatter_villes(df):
    df = df.copy()
    coords = df["ville"].apply(get_coords)
    df["latitude"] = coords.apply(lambda c: c[0])
    df["longitude"] = coords.apply(lambda c: c[1])

    fig, ax = plt.subplots(figsize=(8, 8))
    for source, sous_df in df.groupby("source"):
        ax.scatter(sous_df["longitude"], sous_df["latitude"], label=source, alpha=0.6, s=60)
    ax.set_title("Localisation des offres IA (par ville)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(title="Source")
    fig.tight_layout()
    return fig


def fig_bar_categories_entreprises(df_entreprises):
    fig, ax = plt.subplots(figsize=(9, 5))
    df_entreprises["categorie"].value_counts().head(15).plot(kind="bar", color="#F26419", ax=ax)
    ax.set_title("Entreprises IA à Marrakech par catégorie")
    ax.set_xlabel("Catégorie")
    ax.set_ylabel("Nombre d'entreprises")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig
