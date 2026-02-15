"""
Téléchargement des CSV SAAQ depuis Données Québec
Ou copie depuis AgenticX5-SafeFleet-Hub/data/saaq/
"""

import os
import shutil

SAAQ_DATA_DIR = os.environ.get("SAAQ_DATA_DIR", "./data/saaq")
SAFEFLEET_SAAQ = "../AgenticX5-SafeFleet-Hub/AgenticX5-SafeFleet-Hub/data/saaq/raw/"

def copy_from_safefleet():
    """Copie les CSV depuis le repo SafeFleet-Hub s'il existe."""
    os.makedirs(SAAQ_DATA_DIR, exist_ok=True)
    
    if os.path.exists(SAFEFLEET_SAAQ):
        print(f"📂 SafeFleet-Hub trouvé: {SAFEFLEET_SAAQ}")
        for f in os.listdir(SAFEFLEET_SAAQ):
            if f.endswith(".csv"):
                src = os.path.join(SAFEFLEET_SAAQ, f)
                dst = os.path.join(SAAQ_DATA_DIR, f)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    print(f"  ✅ Copié: {f}")
                else:
                    print(f"  ⏭️  Existe: {f}")
    else:
        print(
            "\n⚠️  Placer manuellement les CSV SAAQ dans:\n"
            f"    {os.path.abspath(SAAQ_DATA_DIR)}/\n"
            "    Fichiers: rapports-accident-2020.csv, -2021.csv, -2022.csv\n"
        )

if __name__ == "__main__":
    copy_from_safefleet()
