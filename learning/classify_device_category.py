"""
Ajoute et peuple la colonne device_category dans patterns.db.

Méthode : classification par règles (mots-clés dans le nom du dispositif +
indice du device_type PECAN/LATM = voie réglementaire numérique) plutôt que
par LLM en aveugle sur 112 noms de dispositifs médicaux dont beaucoup sont
ambigus sans contexte clinique. Chaque ligne reçoit aussi un `confidence`
('haute' si un signal clair a matché, 'a_valider' sinon) pour que rien ne
soit présenté comme certain sans l'être.

Catégories :
  DISPOSITIF_NUMERIQUE   - app, algorithme, télésurveillance, logiciel
  IMPLANT_ACTIF          - implanté + électronique (stimulateur, défibrillateur,
                            neurostim, cochléaire, pompe implantée)
  IMPLANT_PASSIF         - implanté, sans électronique (stent, valve, prothèse
                            articulaire, implant mammaire, treillis)
  DISPOSITIF_PORTE_EXTERNE - porté/externe non implanté (prothèse de membre,
                            orthèse, CPAP/ventilation, exosquelette)
  CONSOMMABLE            - pansement, produit à usage unique
  DIAGNOSTIC_EXTERNE     - dispositif de mesure/diagnostic externe
  A_CLASSIFIER           - aucun signal suffisant, à trancher manuellement

Usage : python3 classify_device_category.py
"""

import re
import sqlite3

import os
DB_PATH = os.environ.get(
    "EVIDENCEABLE_PATTERNS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "patterns.db"),
)

# Règles par mots-clés (regex insensible à la casse), évaluées dans l'ordre.
# Premier match = catégorie retenue, confidence='haute'.
RULES = [
    (r"télésurveillance|therapy|insomnie|connect\b|techcare|care\b(?!.*implant)", "DISPOSITIF_NUMERIQUE"),
    (r"pacemaker|defibrillat|neurostim|percept|sensight|activa|inceptiv|cochle|nucleus|nexa|control-?iq|confirm rx",
     "IMPLANT_ACTIF"),
    (r"valve|sapien|evolut|stent|xience|watchman|implant mammaire|^mentor$|prothèse articulaire|vitamys|pressfit|"
     r"ades|apta|trident|ifuse|mesh|treillis|sebbin|derivo|surpass|solitaire|penumbra|firehawk",
     "IMPLANT_PASSIF"),
    (r"vari-?flex|c-brace|myobock|talux|durawalk|exosquelette|scewo|orthèse|orthese|prothèse externe|d-sad|"
     r"aircurve|ventilat|cpap|zen-o",
     "DISPOSITIF_PORTE_EXTERNE"),
    (r"urgostart|urgofit|allevyn|pansement|surmatelas|nutramigen", "CONSOMMABLE"),
    (r"freestyle|optium|glucose|capteur de mesure", "DIAGNOSTIC_EXTERNE"),
]

COMPILED = [(re.compile(pat, re.IGNORECASE), cat) for pat, cat in RULES]

# Classifications ajoutées manuellement après recherche (avis HAS/CNEDiMTS
# trouvés en ligne) ou connaissance médicale directe des noms de dispositifs,
# pour les cas où le nom seul ne matchait aucune règle générique ci-dessus.
# confidence distingue la source pour rester traçable.
OVERRIDES = {
    # confirmé par recherche web (avis HAS/CNEDiMTS trouvé explicitement)
    "ALLURE RF": ("IMPLANT_ACTIF", "haute_recherche_web"),
    "AVEIR (CATHETER DE RECUPERATION)": ("DISPOSITIF_PORTE_EXTERNE", "haute_recherche_web"),
    "BROADWAY 8": ("DISPOSITIF_PORTE_EXTERNE", "haute_recherche_web"),
    "NEOVIS TOTAL MULTI": ("CONSOMMABLE", "haute_recherche_web"),
    "WALRUS": ("DISPOSITIF_PORTE_EXTERNE", "haute_recherche_web"),
    # connaissance médicale directe (dispositif reconnaissable sans ambiguïté)
    "DIZG DBM": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "ELUVIA": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "FRED X": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "GORE VIATORR TIPS": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "LAMBRE": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "YUKON CHROME PC": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "SPACEOAR VUE": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "SPYSCOPE DS": ("DISPOSITIF_PORTE_EXTERNE", "haute_connaissance_domaine"),
    "ENTERRA II": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "RESTORESENSOR SURESCAN MRI": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "ASSERT-IQ EL+": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "I-STOP": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "MACROPLASTIQUE": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "I-DIGITS": ("DISPOSITIF_PORTE_EXTERNE", "haute_connaissance_domaine"),
    "NARVAL CC": ("DISPOSITIF_PORTE_EXTERNE", "haute_connaissance_domaine"),
    "FORA 6 DUO et FORA 6": ("DIAGNOSTIC_EXTERNE", "haute_connaissance_domaine"),
    "HYLO DUAL PLUS": ("CONSOMMABLE", "haute_connaissance_domaine"),
    "RELAY NBS PRO": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "MPACT DM": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "IMPLANTS OSSEUX SUR MESURE 3DI EN PEEK": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "ALLOGREFFON VEINEUX SAPHÈNE +2/+8°C BIOPROTEC": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "ACCESS SOCKET TRANS FEMORAL": ("DISPOSITIF_PORTE_EXTERNE", "haute_connaissance_domaine"),
    "IMPELLA 5.0": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "INFINITY": ("IMPLANT_ACTIF", "moyenne_connaissance_domaine"),
    "INSPIRE IV": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "INSPIRE IV UAS": ("IMPLANT_ACTIF", "haute_connaissance_domaine"),
    "AZUR / AZUR CX": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    "NAVITOR": ("IMPLANT_PASSIF", "haute_connaissance_domaine"),
    # confiance moyenne : reconnaissance partielle, à confirmer si tu as un doute
    "RONDO 3": ("DISPOSITIF_PORTE_EXTERNE", "moyenne_connaissance_domaine"),
    "EMBOGOLD": ("IMPLANT_PASSIF", "moyenne_connaissance_domaine"),
    "DOMUS 4 AUTO": ("DISPOSITIF_PORTE_EXTERNE", "moyenne_connaissance_domaine"),
    "FLEX-SYMES": ("DISPOSITIF_PORTE_EXTERNE", "moyenne_connaissance_domaine"),
    "TRIAS 1C30-1": ("DISPOSITIF_PORTE_EXTERNE", "moyenne_connaissance_domaine"),
}


def classify(device_name: str, device_type: str | None) -> tuple[str, str]:
    name = device_name or ""

    if name in OVERRIDES:
        return OVERRIDES[name]

    for pattern, category in COMPILED:
        if pattern.search(name):
            return category, "haute"

    # Fallback : la voie réglementaire numérique (PECAN/LATM) est un bon proxy
    # quand le nom seul ne suffit pas.
    if device_type in ("PECAN", "LATM"):
        return "DISPOSITIF_NUMERIQUE", "moyenne_proxy_device_type"

    return "A_CLASSIFIER", "aucun_signal"


def main():
    conn = sqlite3.connect(DB_PATH)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(dossiers)")}
    if "device_category" not in existing_cols:
        conn.execute("ALTER TABLE dossiers ADD COLUMN device_category TEXT")
    if "device_category_confidence" not in existing_cols:
        conn.execute("ALTER TABLE dossiers ADD COLUMN device_category_confidence TEXT")

    rows = conn.execute(
        "SELECT id, device_name, device_type FROM dossiers WHERE source != 'verifie_manuellement'"
    ).fetchall()
    counts = {}
    # Compter aussi les lignes déjà vérifiées manuellement, sans les reclasser
    for cat, in conn.execute(
        "SELECT device_category FROM dossiers WHERE source='verifie_manuellement'"
    ):
        counts[cat] = counts.get(cat, 0) + 1
    for dossier_id, device_name, device_type in rows:
        category, confidence = classify(device_name, device_type)
        counts[category] = counts.get(category, 0) + 1
        conn.execute(
            "UPDATE dossiers SET device_category=?, device_category_confidence=? WHERE id=?",
            (category, confidence, dossier_id),
        )
    conn.commit()

    # Propagation : si un même device_name a déjà une catégorie fiable
    # ('haute') dans une autre source, la réutiliser pour les lignes
    # A_CLASSIFIER de même nom plutôt que de les laisser sans info.
    known = dict(
        conn.execute(
            "SELECT device_name, device_category FROM dossiers "
            "WHERE device_category_confidence='haute'"
        ).fetchall()
    )
    propagated = 0
    for dossier_id, device_name, _ in rows:
        if device_name in known:
            cur_cat = conn.execute(
                "SELECT device_category FROM dossiers WHERE id=?", (dossier_id,)
            ).fetchone()[0]
            if cur_cat == "A_CLASSIFIER":
                conn.execute(
                    "UPDATE dossiers SET device_category=?, device_category_confidence=? WHERE id=?",
                    (known[device_name], "propagee_meme_dispositif_autre_source", dossier_id),
                )
                counts["A_CLASSIFIER"] -= 1
                counts[known[device_name]] = counts.get(known[device_name], 0) + 1
                propagated += 1
    conn.commit()
    print(f"Propagées depuis une autre source (même nom de dispositif) : {propagated}\n")

    print("Répartition par catégorie :")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:28s} {n}")
    print(f"\nTotal dossiers : {sum(counts.values())}")
    print(f"À valider manuellement (A_CLASSIFIER) : {counts.get('A_CLASSIFIER', 0)}")
    conn.close()


if __name__ == "__main__":
    main()
