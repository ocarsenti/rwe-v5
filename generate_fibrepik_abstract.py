"""Generate FIBREPIK study abstract PDF — input document for RWE-v5 diagnostic.
All table cells use Paragraph objects to prevent truncation.
"""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

W, H = A4
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

DARK     = colors.HexColor("#1a3557")
MID_BLUE = colors.HexColor("#2563eb")
LIGHT_BG = colors.HexColor("#f0f4f8")
BORDER   = colors.HexColor("#cbd5e1")
GRAY     = colors.HexColor("#64748b")
WHITE    = colors.white

sN  = S("n",  fontSize=9,   textColor=colors.HexColor("#1e293b"), leading=14)
sNJ = S("nj", fontSize=9,   textColor=colors.HexColor("#1e293b"), leading=14, alignment=TA_JUSTIFY)
sSm = S("sm", fontSize=8.5, textColor=colors.HexColor("#334155"), leading=13)
sLb = S("lb", fontSize=9,   textColor=DARK, leading=14, fontName="Helvetica-Bold")
sCe = S("ce", fontSize=9,   textColor=colors.HexColor("#1e293b"), leading=14, alignment=TA_CENTER)

COL1 = 4.2*cm
COL2 = W - 4.4*cm - COL1 - 0.4*cm

def p(txt, style=None):
    return Paragraph(txt, style or sN)

def row(label, content, style=None):
    return [p(label, sLb), p(content, style or sN)]

def info_table(rows_data):
    tbl = Table(rows_data, colWidths=[COL1, COL2])
    tbl.setStyle([
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("BACKGROUND",    (0,0),(0,-1),  LIGHT_BG),
        ("GRID",          (0,0),(-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ])
    return tbl

out_path = "/home/olive/rwe-v5/fibrepik_abstract.pdf"
doc = SimpleDocTemplate(out_path, pagesize=A4,
    topMargin=2*cm, bottomMargin=1.8*cm, leftMargin=2.2*cm, rightMargin=2.2*cm)

story = []

# ── TITRE ─────────────────────────────────────────────────────────────────────
story.append(Paragraph(
    "A drug-free solution for improving the quality of life of fibromyalgia patients (FIBREPIK): "
    "a multicenter, randomized, controlled effectiveness trial",
    S("ti", fontSize=15, textColor=DARK, leading=21, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(Paragraph(
    "Chipon E., Bosson J., Minier L., Dumolard A., Vilotitch A., Crouzier D., et al.",
    S("au", fontSize=9, textColor=GRAY, leading=13, spaceAfter=2)))

story.append(Paragraph(
    "Trials. 2022;23(1):740. doi:10.1186/s13063-022-06693-z  ·  "
    "ClinicalTrials.gov: NCT05058092  ·  Rapport d'étude daté du 22/11/2023",
    S("jo", fontSize=8.5, textColor=MID_BLUE, leading=12, spaceAfter=10,
      fontName="Helvetica-Oblique")))

story.append(HRFlowable(width="100%", thickness=1.5, color=DARK, spaceAfter=12))

# ── REVENDICATION ─────────────────────────────────────────────────────────────
story.append(Paragraph("Revendication du fabricant (Remedee Labs)",
    S("h2", fontSize=11, textColor=DARK, leading=16, fontName="Helvetica-Bold",
      spaceBefore=6, spaceAfter=6)))

story.append(Table([[
    Paragraph(
        "Le bracelet FIBROREM utilise la neuromodulation par émission d'ondes millimétriques "
        "(61,25 GHz) pour libérer des endorphines endogènes au niveau central, soulageant les "
        "symptômes de patients adultes atteints de fibromyalgie modérée à sévère "
        "(score FIQ ≥ 39) en comparaison à la prise en charge thérapeutique classique "
        "individualisée et pluridisciplinaire (éducation thérapeutique + activité physique adaptée).",
        S("cl", fontSize=9.5, textColor=DARK, leading=15, alignment=TA_JUSTIFY,
          fontName="Helvetica-Oblique"))
]], colWidths=[W - 4.4*cm],
    style=[
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT_BG),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("BOX",           (0,0),(-1,-1), 1.2, DARK),
    ]))
story.append(Spacer(1, 12))

# ── DESIGN ────────────────────────────────────────────────────────────────────
story.append(Paragraph("Design de l'étude",
    S("h2", fontSize=11, textColor=DARK, leading=16, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(info_table([
    row("Type",
        "Étude de supériorité, prospective, multicentrique, contrôlée, randomisée, en ouvert "
        "(l'évaluateur est indépendant mais les accompagnants connaissent l'allocation de traitement)."),
    row("Objectif",
        "Montrer la supériorité du bracelet FIBROREM (génération REM-2) associé à son application "
        "mobile et à un accompagnement personnalisé, en complément de la prise en charge "
        "conventionnelle, par rapport à la prise en charge conventionnelle seule, sur la réduction "
        "du score FIQ à 3 mois de suivi."),
    row("Bras de traitement",
        "Groupe accès immédiat (n=84) : prise en charge conventionnelle + bracelet + accompagnement dès J0. "
        "Groupe accès différé (n=86) : prise en charge conventionnelle seule jusqu'à M3, puis accès au bracelet + accompagnement."),
    row("Randomisation",
        "Ratio 1:1. Réalisée par les accompagnants (coachs) de chaque centre — les coachs ne sont "
        "pas en aveugle de l'allocation."),
    row("Centres",
        "8 centres en France : Grenoble, Valenciennes, Suresnes, Paris, Rouen, Mornant, Montpellier, "
        "Villeurbanne. 7 hôpitaux (6 publics + 1 privé) + 1 cabinet libéral de neurologie."),
    row("Période",
        "Inclusions : novembre 2021 – avril 2022. Dernier suivi : fin mars 2023. "
        "Durée totale de la recherche : 21 mois."),
    row("Dispositif évalué",
        "Bracelet REMEDEE génération REM-2 (61,25 GHz, puissance transmise 0,02–0,05 W, "
        "surface d'exposition 2,5 cm², profondeur de pénétration estimée 0,5 mm) + "
        "application mobile FIBREPIK V1.0."),
    row("Accompagnement personnalisé",
        "Réalisé par des assistants de recherche clinique, psychologues ou infirmiers de chaque "
        "centre (« coach »), préalablement formés par un neuropsychologue de Remedee Labs. "
        "Étapes : formation patient à J0 (ou M3 pour le groupe différé), appels téléphoniques "
        "standardisés à J7, M1, M2, entretien avant consultation médicale à M3."),
]))
story.append(Spacer(1, 12))

# ── POPULATION ────────────────────────────────────────────────────────────────
story.append(Paragraph("Population",
    S("h2", fontSize=11, textColor=DARK, leading=16, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(info_table([
    row("Critères d'inclusion",
        "Adulte ≥ 18 ans · Diagnostic clinique de fibromyalgie confirmé selon les critères "
        "du Collège Américain de Rhumatologie (ACR 2016) · Score FIQ ≥ 39 à l'inclusion "
        "(formes modérées à sévères) · Possession d'un smartphone compatible (iOS ou Android) "
        "et acceptation de l'installation de l'application FIBREPIK."),
    row("Critères d'exclusion",
        "Épisode dépressif caractérisé selon DSM-5 · Modification substantielle de traitement "
        "dans les 3 mois précédant l'inclusion ou prévue · Pathologie inflammatoire chronique "
        "associée (PR, spondylarthrite, lupus…) · Pathologie dermatologique au niveau des "
        "poignets (dermatose suintante, hypersudation, lésion non cicatrisée) · Implant "
        "chirurgical, tatouage ou piercing au niveau des deux poignets."),
    row("Effectif randomisé",
        "170 patients au total : 84 dans le groupe accès immédiat, 86 dans le groupe accès différé."),
    row("Caractéristiques",
        "Âge médian : 49 ans (écart interquartile 42–54). Sexe féminin : 95,3% (162/170). "
        "Fibromyalgie sévère (FIQ ≥ 59) : 82% des patients. Score de douleur médian : 7/10. "
        "Statut professionnel varié (actifs 38%, invalides 20%, arrêts maladie 14%)."),
    row("Traitements à l'inclusion",
        "Non détaillés dans le rapport d'étude — liste des médicaments et classes "
        "thérapeutiques non fournie."),
]))
story.append(Spacer(1, 12))

# ── CRITÈRES DE JUGEMENT ──────────────────────────────────────────────────────
story.append(Paragraph("Critères de jugement",
    S("h2", fontSize=11, textColor=DARK, leading=16, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(info_table([
    row("Critère principal",
        "Réduction cliniquement pertinente du score FIQ ≥ 14% entre J0 et 3 mois de suivi. "
        "Le score FIQ (Fibromyalgia Impact Questionnaire) est un auto-questionnaire complété "
        "par le patient avant la consultation médicale. Seuil de pertinence clinique de 14% "
        "établi sur la base d'une publication préexistante."),
    row("Calcul du nombre de sujets",
        "Hypothèses : 50% de répondeurs dans le groupe accès immédiat vs 25% dans le groupe "
        "différé. Risque α = 5%, puissance = 90%, attrition estimée = 10%. "
        "Résultat : 85 patients par bras, soit 170 patients au total."),
    row("Critères secondaires",
        "Évolutions entre J0 et 3 mois (questionnaires décrits en annexe du protocole) :\n"
        "· Qualité du sommeil : Pittsburgh Sleep Quality Index (PSQI)\n"
        "· Douleur moyenne hebdomadaire : EVA 11 points (carnet de suivi 7 jours consécutifs "
        "à M1, M2 et M3)\n"
        "· Anxiété et dépression : questionnaire HAD\n"
        "· Fatigue : questionnaire IMF-20\n"
        "· Consommation d'antalgiques, d'antidépresseurs et de somnifères (classe, dose, "
        "nombre de prises — auto et hétéro-prescription)\n"
        "· Consommation de soins en lien avec la fibromyalgie (actes, consultations)\n"
        "· Patient Global Impression of Change (PGIC)\n"
        "Note : les critères secondaires sont multiples sans correction pour l'inflation du risque α."),
    row("Analyse statistique",
        "Analyse en intention de traiter (ITT) annoncée au protocole. Analyse de sensibilité "
        "par imputation multiple prévue en cas de données manquantes."),
]))
story.append(Spacer(1, 12))

# ── RÉSULTATS ─────────────────────────────────────────────────────────────────
story.append(Paragraph("Résultats",
    S("h2", fontSize=11, textColor=DARK, leading=16, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(Paragraph("Critère de jugement principal — Score FIQ :",
    S("h3", fontSize=9.5, textColor=DARK, leading=14, fontName="Helvetica-Bold", spaceAfter=4)))

res_rows = [
    [p("", sLb), p("Accès différé (n=84)", sLb), p("Accès immédiat (n=81)", sLb), p("Statistique", sLb)],
    [p("Score FIQ à J0 (moyenne ± DS)"), p("69,8 ± 11,1", sCe), p("69,3 ± 12,5", sCe), p("Groupes comparables", sCe)],
    [p("Score FIQ à 3 mois (moyenne ± DS)"), p("64,0 ± 15,5", sCe), p("53,4 ± 16,9", sCe), p("—", sCe)],
    [p("Réduction FIQ ≥ 14%\n(critère principal, analyse per-protocol)"),
     p("28/84\n(35,9%)", sCe), p("38/81\n(55,1%)", sCe),
     p("p = 0,021\nOR = 0,701\nIC95% [0,14 ; 0,955]", sCe)],
    [p("Analyse de sensibilité\n(imputation multiple)"),
     p("—", sCe), p("—", sCe),
     p("OR = 0,478\nIC95% [0,25 ; 0,92]", sCe)],
    [p("Données manquantes"), p("6/84 (7,1%)", sCe), p("12/84 (14,3%)", sCe), p("—", sCe)],
]
res_tbl = Table(res_rows, colWidths=[5.2*cm, 2.8*cm, 2.8*cm, W-4.4*cm-11*cm])
res_tbl.setStyle([
    ("BACKGROUND",    (0,0),(-1,0),  DARK),
    ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
    ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
    ("FONTNAME",      (0,1),(0,-1),  "Helvetica-Bold"),
    ("TEXTCOLOR",     (0,1),(0,-1),  DARK),
    ("FONTSIZE",      (0,0),(-1,-1), 8.5),
    ("GRID",          (0,0),(-1,-1), 0.5, BORDER),
    ("TOPPADDING",    (0,0),(-1,-1), 7),
    ("BOTTOMPADDING", (0,0),(-1,-1), 7),
    ("LEFTPADDING",   (0,0),(-1,-1), 7),
    ("RIGHTPADDING",  (0,0),(-1,-1), 7),
    ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BG]),
])
story.append(res_tbl)
story.append(Spacer(1, 10))

story.append(Paragraph("Événements indésirables :",
    S("h3", fontSize=9.5, textColor=DARK, leading=14, fontName="Helvetica-Bold", spaceAfter=4)))

story.append(info_table([
    row("EI non graves liés au bracelet",
        "51 patients avec au moins 1 EI non grave recensé dans l'étude FIBREPIK. "
        "Occurrences : sensations de chaleur (17,8%), douleurs locales (17,8%), "
        "paresthésies / sensations de lourdeur (14,5%), céphalées (14,5%), "
        "somnolence / fatigue (9,6%), vertiges (6,5%), nausées (4,8%), "
        "bouffées de chaleur (4,8%), autres (acouphènes, agitation, inconfort, "
        "réaction dermatologique, sensation d'électricité, troubles de la motricité)."),
    row("EI graves",
        "3 événements indésirables graves non liés au bracelet : "
        "2 hospitalisations pour dépression, 1 intoxication médicamenteuse volontaire."),
    row("Données de surveillance du marché",
        "Période 2021–2024 (commercialisation version bien-être). Taux d'incidence "
        "d'EI non graves imputables au bracelet : 3,3%. Occurrences : sensations de "
        "chaleur (n=116, dont 93 résolues), somnolence (n=30, dont 19 résolues), "
        "réactions dermatologiques (n=25, dont 16 résolues), sensations de brûlures "
        "liées à un problème technique (n=3)."),
    row("Matériovigilance",
        "Aucune donnée disponible — le bracelet n'était pas commercialisé en version "
        "dispositif médical au moment de l'étude."),
]))
story.append(Spacer(1, 14))

# ── FOOTER ────────────────────────────────────────────────────────────────────
story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=6))
story.append(Paragraph(
    "FIBREPIK · NCT05058092 · Chipon et al., Trials 2022  ·  "
    "Document préparé pour analyse RWE-v5 · Juin 2026  ·  "
    "Source : dossier Remedee Labs soumis à la CNEDiMTS (données publiques HAS)",
    S("fo", fontSize=7.5, textColor=GRAY, leading=11, alignment=TA_CENTER)))

doc.build(story)
print(f"PDF généré : {out_path}")
