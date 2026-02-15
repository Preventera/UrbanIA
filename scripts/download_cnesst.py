"""
Téléchargement des CSV CNESST depuis Données Québec
Source: donneesquebec.ca/recherche/dataset/lesions-professionnelles
"""

import os
import sys
import urllib.request

# URLs des fichiers CSV CNESST (à mettre à jour si les URLs changent)
CNESST_URLS = {
    # Les URLs exactes doivent être vérifiées sur donneesquebec.ca
    # car elles changent à chaque publication
    # Format: "lesions-YYYY.csv" → URL donneesquebec.ca
}

DATA_DIR = os.environ.get("CNESST_DATA_DIR", "./data/cnesst")


def download_all():
    """Télécharge tous les CSV CNESST disponibles."""
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=" * 60)
    print("📥 Téléchargement des données CNESST")
    print("Source: donneesquebec.ca")
    print("=" * 60)

    if not CNESST_URLS:
        print(
            "\n⚠️  Les URLs de téléchargement doivent être configurées.\n"
            "    1. Aller sur donneesquebec.ca/recherche/dataset/lesions-professionnelles\n"
            "    2. Copier les URLs des CSV (2016 à 2022)\n"
            "    3. Les ajouter dans CNESST_URLS dans ce script\n"
            "\n    Alternativement, télécharger manuellement les CSV et les placer dans:\n"
            f"    {os.path.abspath(DATA_DIR)}/\n"
        )
        return

    for filename, url in CNESST_URLS.items():
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            print(f"  ⏭️  {filename} existe déjà")
            continue

        print(f"  📥 {filename}...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, filepath)
            size_mb = os.path.getsize(filepath) / 1024 / 1024
            print(f"✅ ({size_mb:.1f} Mo)")
        except Exception as e:
            print(f"❌ {e}")

    print("\n✅ Terminé")


if __name__ == "__main__":
    download_all()
