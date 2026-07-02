"""Generate complete FIBROREM diagnostic PDF — based on real HAS/CNEDiMTS data."""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

from test_fibrorem_analysis import CLAIM, FIBREPIK_JSON, run

study, engine_out, comparison, repairs = run()

# ── palette ──────────────────────────────────────────────────────────────────
DARK_BLUE    = colors.HexColor("#1a3557")
MID_BLUE     = colors.HexColor("#2563eb")
LIGHT_BLUE   = colors.HexColor("#dbeafe")
ORANGE       = colors.HexColor("#ea580c")
ORANGE_LIGHT = colors.HexColor("#ffedd5")
GREEN        = colors.HexColor("#16a34a")
GREEN_LIGHT  = colors.HexColor("#dcfce7")
RED          = colors.HexColor("#dc2626")
RED_LIGHT    = colors.HexColor("#fee2e2")
GRAY         = colors.HexColor("#6b7280")
LIGHT_GRAY   = colors.HexColor("#f3f4f6")
BORDER_GRAY  = colors.HexColor("#e5e7eb")
DARK_RED     = colors.HexColor("#7f1d1d")
WHITE        = colors.white
W, H = A4

base = getSampleStyleSheet()
def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

styles = {
    "title":    S("title",  fontSize=22, textColor=WHITE,  leading=28, fontName="Helvetica-Bold"),
    "subtitle": S("sub",    fontSize=11, textColor=colors.HexColor("#bfdbfe"), leading=16),
    "meta":     S("meta",   fontSize=9,  textColor=colors.HexColor("#93c5fd"), leading=13),
    "h2":       S("h2",     fontSize=13, textColor=DARK_BLUE, leading=18, spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold"),
    "h3":       S("h3",     fontSize=10.5, textColor=DARK_BLUE, leading=15, spaceBefore=8, spaceAfter=3, fontName="Helvetica-Bold"),
    "body":     S("body",   fontSize=9.5, textColor=colors.HexColor("#1f2937"), leading=14, spaceAfter=4, alignment=TA_JUSTIFY),
    "body_sm":  S("bsm",    fontSize=8.5, textColor=colors.HexColor("#374151"), leading=13, spaceAfter=2),
    "label":    S("lbl",    fontSize=8,  textColor=GRAY, leading=11, spaceAfter=1, fontName="Helvetica-Bold"),
    "mono":     S("mono",   fontSize=8.5, textColor=colors.HexColor("#1e293b"), leading=13, fontName="Courier"),
    "footer":   S("footer", fontSize=7.5, textColor=GRAY, leading=11, alignment=TA_CENTER),
    "has_quote":S("hq",     fontSize=9.5, textColor=DARK_BLUE, leading=15, leftIndent=16, rightIndent=8,
                            spaceBefore=6, spaceAfter=6, alignment=TA_JUSTIFY, fontName="Helvetica-Oblique"),
    "red_bold": S("rb",     fontSize=9.5, textColor=RED, leading=14, fontName="Helvetica-Bold"),
    "verdict":  S("verd",   fontSize=16, textColor=RED, leading=20, fontName="Helvetica-Bold"),
}

out_path = "/home/olive/rwe-v5/fibrorem_diagnostic.pdf"
doc = SimpleDocTemplate(out_path, pagesize=A4,
    topMargin=0, bottomMargin=1.8*cm, leftMargin=2.2*cm, rightMargin=2.2*cm)

story = []

def colored_box(inner, bg, pad=6):
    return Table([[inner]], colWidths=[W - 4.4*cm],
        style=[("BACKGROUND",(0,0),(-1,-1),bg), ("TOPPADDING",(0,0),(-1,-1),pad),
               ("BOTTOMPADDING",(0,0),(-1,-1),pad), ("LEFTPADDING",(0,0),(-1,-1),pad+2),
               ("RIGHTPADDING",(0,0),(-1,-1),pad)])

def info_table(rows, col1=3.8*cm):
    return Table(rows, colWidths=[col1, W - 4.4*cm - col1 - 0.4*cm],
        style=[("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),9),
               ("TEXTCOLOR",(0,0),(0,-1),DARK_BLUE), ("BACKGROUND",(0,0),(0,-1),LIGHT_GRAY),
               ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY), ("TOPPADDING",(0,0),(-1,-1),7),
               ("BOTTOMPADDING",(0,0),(-1,-1),7), ("LEFTPADDING",(0,0),(-1,-1),8),
               ("RIGHTPADDING",(0,0),(-1,-1),8), ("VALIGN",(0,0),(-1,-1),"TOP")])

# ── HEADER ───────────────────────────────────────────────────────────────────
header_tbl = Table([[
    Table([
        [Paragraph("FIBROREM — REMEDEE LABS", styles["title"])],
        [Paragraph("Bracelet de neuromodulation par ondes millimétriques · Fibromyalgie modérée à sévère", styles["subtitle"])],
        [Spacer(1,6)],
        [Paragraph("Diagnostic épistémique · Basé sur l'avis CNEDiMTS du 11 mars 2025 · Étude FIBREPIK (NCT05058092)", styles["meta"])],
    ], colWidths=[W-4.4*cm],
       style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
]], colWidths=[W-4.4*cm],
    style=[("BACKGROUND",(0,0),(-1,-1),DARK_BLUE),("TOPPADDING",(0,0),(-1,-1),28),
           ("BOTTOMPADDING",(0,0),(-1,-1),24),("LEFTPADDING",(0,0),(-1,-1),24),
           ("RIGHTPADDING",(0,0),(-1,-1),24)])
story.append(header_tbl)
story.append(Spacer(1,14))

# ── VERDICT BAND ─────────────────────────────────────────────────────────────
verdict_inner = Table([[
    Table([
        [Paragraph("VERDICT CNEDiMTS (11 mars 2025)", styles["label"])],
        [Paragraph("SERVICE ATTENDU INSUFFISANT", styles["verdict"])],
        [Paragraph("Première demande LPPR — Refus d'inscription", S("vi", fontSize=9, textColor=RED, leading=13))],
    ], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]),
    Table([
        [Paragraph("Sévérité épistémique", styles["label"])],
        [Paragraph("ÉLEVÉE · 75/100", S("sv",fontSize=11,textColor=RED,fontName="Helvetica-Bold",leading=14))],
        [Paragraph("Moteur RWE-v5", S("sm",fontSize=8,textColor=GRAY,leading=11))],
    ], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
]], colWidths=[None, 4.5*cm],
   style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
          ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
          ("VALIGN",(0,0),(-1,-1),"MIDDLE")])
story.append(colored_box(verdict_inner, RED_LIGHT, pad=14))
story.append(Spacer(1,14))

# ── 1. CLAIM ─────────────────────────────────────────────────────────────────
story.append(Paragraph("1. Revendication du demandeur", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))
story.append(info_table([
    ["Fabricant",       "REMEDEE LABS (France)"],
    ["Dispositif",      "FIBROREM — Kit bracelet REM-3 + application mobile myRemedee"],
    ["Classe CE",       "Classe IIa — Notifié BSI (n°2797, Pays-Bas)"],
    ["Indication",      "Soulagement des symptômes de patients adultes atteints de fibromyalgie modérée à sévère (score FIQ ≥ 39)"],
    ["Comparateur",     "Prise en charge thérapeutique classique individualisée et pluridisciplinaire (éducation thérapeutique + activité physique adaptée)"],
    ["ASA revendiquée", "Niveau III — Amélioration modérée"],
    ["Mécanisme",       "Stimulation des récepteurs sensoriels du poignet interne (61,25 GHz, 0,02–0,05 W, profondeur 0,5 mm) → libération d'endorphines endogènes au niveau central"],
]))
story.append(Spacer(1,12))

# ── 2. ÉTUDE FIBREPIK ─────────────────────────────────────────────────────────
story.append(Paragraph("2. Étude principale — FIBREPIK (NCT05058092)", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

story.append(info_table([
    ["Type",          "RCT de supériorité · Prospective · Multicentrique · Ouverte"],
    ["Référence",     "Chipon et al., Trials 2022;23(1):740 · Rapport d'étude 22/11/2023"],
    ["Dispositif testé","Génération REM-2 (précédente) — équivalence technique revendiquée avec REM-3"],
    ["N randomisés",  "170 patients (86 accès différé / 84 accès immédiat) · 8 centres France"],
    ["Population",    "Fibromyalgie modérée à sévère (FIQ ≥ 39) · 96% femmes · âge médian 49 ans"],
    ["Comparateur",   "Prise en charge conventionnelle seule (sans bracelet ni accompagnement)"],
    ["Suivi",         "Critère primaire à 3 mois · Suivi total 9 mois"],
    ["Critère principal","Réduction FIQ cliniquement pertinente ≥ 14% entre J0 et 3 mois (auto-questionnaire)"],
    ["Résultat principal","55,1% vs 35,9% (p=0,021) — OR 0,701 [IC95% 0,14;0,955]"],
]))
story.append(Spacer(1,10))

# Tableau résultats FIQ
story.append(Paragraph("Résultats détaillés — Score FIQ :", styles["h3"]))
fiq_rows = [
    ["", "Accès différé (n=84)", "Accès immédiat (n=81)", "p"],
    ["Score FIQ à J0 (moy ± DS)", "69,8 ± 11,1", "69,3 ± 12,5", "—"],
    ["Score FIQ à 3 mois (moy ± DS)", "64,0 ± 15,5", "53,4 ± 16,9", "—"],
    ["Réduction ≥14% (critère principal)", "28/84 (35,9%)", "38/81 (55,1%)", "0,021"],
    ["Données manquantes", "6/84 (7,1%)", "12/84 (14,3%)", "—"],
]
fiq_tbl = Table(fiq_rows, colWidths=[5.5*cm, 3.8*cm, 3.8*cm, 2.2*cm],
    style=[
        ("BACKGROUND",(0,0),(-1,0),DARK_BLUE), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,1),(0,-1),DARK_BLUE), ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, LIGHT_GRAY]),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),
    ])
story.append(fiq_tbl)
story.append(Spacer(1,12))

# ── 3. ANALYSE ÉPISTÉMIQUE ────────────────────────────────────────────────────
story.append(Paragraph("3. Analyse épistémique — moteur RWE-v5", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

bias_inner = Table([[
    Paragraph("Issue principale : SUBJECTIVE_ENDPOINT_BIAS + PERCEPTION_BIAS",
              S("bi",fontSize=10,textColor=RED,fontName="Helvetica-Bold",leading=14)),
    Paragraph("Score : 75/100 — ÉLEVÉE",
              S("bs",fontSize=10,textColor=RED,fontName="Helvetica-Bold",leading=14,alignment=TA_RIGHT)),
]], colWidths=[None, 3.5*cm],
   style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
          ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
story.append(colored_box(bias_inner, RED_LIGHT, pad=10))
story.append(Spacer(1,8))

story.append(Paragraph("Biais détectés :", styles["h3"]))
bias_rows = [["Biais", "Sévérité", "Description"],
    ["PERCEPTION_BIAS", "HIGH",
     "Tous les critères sont des auto-questionnaires patients (FIQ, EVA, PSQI, HAD). En l'absence d'aveugle ou de sham, les résultats ne peuvent être distingués d'un effet placebo / effet d'expectation."],
    ["CO-INTERVENTION_BIAS", "HIGH",
     "L'accompagnement personnalisé (coach) est fourni uniquement au groupe bracelet. Impossible d'isoler l'effet du bracelet de l'effet de l'accompagnement. Les coachs connaissent l'allocation → contamination du groupe contrôle impossible à mesurer."],
    ["MISSING_DATA_BIAS", "MEDIUM",
     "14,3% de données manquantes dans le groupe immédiat (12/84) vs 7,1% dans le groupe différé. L'analyse de sensibilité par imputation multiple (OR=0,478) n'est pas l'hypothèse du pire scénario (worst-case). Conclusion sur l'efficacité incertaine."],
    ["GENERATIONAL_GAP", "MEDIUM",
     "L'étude porte sur REM-2 (précédente génération). FIBROREM REM-3 fait l'objet de la demande. L'équivalence technique est revendiquée mais non démontrée cliniquement."],
    ["ANALYSIS_SET_BIAS", "MEDIUM",
     "L'analyse ne porte pas sur la population en ITT stricte (170 randomisés) mais sur 165 patients. Le protocole annonçait une analyse ITT."],
]
bias_tbl = Table(bias_rows, colWidths=[4.2*cm, 1.8*cm, W-4.4*cm-6.2*cm],
    style=[
        ("BACKGROUND",(0,0),(-1,0),DARK_BLUE), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,1),(0,-1),RED), ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
    ])
story.append(bias_tbl)
story.append(Spacer(1,12))

# ── 4. ANALYSE DES ENDPOINTS ──────────────────────────────────────────────────
story.append(Paragraph("4. Analyse des critères de jugement", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

ep_rows = [["Critère", "Nature", "Statut", "Problème principal"],
    ["Score FIQ à 3 mois\n(primaire)", "Subjectif\nPRO", "ACCEPTABLE\nSOUS CONDITIONS",
     "Auto-questionnaire complété avant consultation. Acceptable uniquement avec aveugle (sham) ou adjudication indépendante de la composante placebo."],
    ["EVA douleur\n(secondaire)", "Subjectif\nPRO", "ACCEPTABLE\nSOUS CONDITIONS",
     "Carnet de suivi patient auto-déclaré. Même vulnérabilité placebo que le FIQ. Valeur exploratoire uniquement sans sham."],
    ["Pittsburgh PSQI\n(secondaire)", "Subjectif\nPRO", "ACCEPTABLE\nSOUS CONDITIONS",
     "Questionnaire sommeil auto-rapporté. Critique secondaire — inflation du risque α non contrôlée."],
    ["HAD (anxiété/dép.)\n(secondaire)", "Subjectif\nPRO", "EXPLORATOIRE",
     "Critères secondaires multiples sans correction pour le risque α → valeur exploratoire uniquement."],
]
ep_tbl = Table(ep_rows, colWidths=[3.2*cm, 2*cm, 3*cm, W-4.4*cm-8.4*cm],
    style=[
        ("BACKGROUND",(0,0),(-1,0),DARK_BLUE), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,1),(0,-1),ORANGE), ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
    ])
story.append(ep_tbl)
story.append(Spacer(1,12))

# ── 5. PROBLÈMES CRITIQUES HAS ───────────────────────────────────────────────
story.append(Paragraph("5. Problèmes critiques identifiés par la CNEDiMTS", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

crit_rows = [["#", "Problème", "Impact"],
    ["1", "Analyse non ITT stricte\nLa population analysée (165/170) n'est pas celle annoncée au protocole (tous randomisés).",
     "Critique — invalide la conclusion de supériorité"],
    ["2", "Données manquantes non gérées en worst-case\nL'hypothèse du pire scénario (données manquantes = échecs) n'est pas testée.",
     "Critique — surévalue l'efficacité"],
    ["3", "Traitements médicamenteux à l'inclusion non fournis\nImpossible de vérifier la comparabilité des groupes sur les co-médications.",
     "Critique — biais de confusion majeur"],
    ["4", "Impact de l'accompagnement non évalué\nLe bras bracelet reçoit systématiquement un accompagnement personnalisé absent du bras contrôle.",
     "Critique — co-intervention non contrôlée"],
    ["5", "Effet placebo non exclu\nAucun bras sham (bracelet sans stimulation). Tous les endpoints sont subjectifs.",
     "Critique — interprétation clinique impossible"],
    ["6", "Étude sur génération précédente\nFIBREPIK utilise REM-2 ; la demande porte sur REM-3. Équivalence technique non démontrée cliniquement.",
     "Important — extrapolation non validée"],
]
crit_tbl = Table(crit_rows, colWidths=[0.7*cm, 9*cm, W-4.4*cm-9.9*cm],
    style=[
        ("BACKGROUND",(0,0),(-1,0),DARK_RED), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,1),(0,-1),MID_BLUE), ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,RED_LIGHT]),
        ("TEXTCOLOR",(2,1),(-1,-1),RED),
    ])
story.append(crit_tbl)
story.append(Spacer(1,12))

# ── 6. INTERPRÉTATION HAS ─────────────────────────────────────────────────────
story.append(Paragraph("6. Interprétation CNEDiMTS (verbatim)", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))

has_text = (
    "« Compte tenu du faible niveau de preuve des données fournies, l'intérêt de FIBROREM, bracelet de "
    "neuromodulation par émission d'ondes millimétriques associé à son application mobile, ne peut être "
    "établi, dans l'indication revendiquée. [...] La Commission encourage la réalisation d'études "
    "complémentaires, de bonne qualité méthodologique et prenant en compte à la fois les conditions réelles "
    "d'utilisation et l'évaluation d'un éventuel effet placebo. »"
)
story.append(colored_box(Paragraph(has_text, styles["has_quote"]), LIGHT_BLUE, pad=14))
story.append(Spacer(1,6))
story.append(Paragraph("Source : Avis CNEDiMTS du 11 mars 2025 — Service Attendu Insuffisant (verbatim).",
    S("src",fontSize=7.5,textColor=GRAY,leading=11,fontName="Helvetica-Oblique")))
story.append(Spacer(1,14))

# ── 7. DESIGN REQUIS ─────────────────────────────────────────────────────────
story.append(Paragraph("7. Design requis pour une future demande recevable", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

design_rows = [
    ["Dimension", "Exigence minimale", "Exigence optimale"],
    ["Design", "RCT en double aveugle", "RCT Sham-contrôlé (bracelet placebo identique)"],
    ["Aveugle", "Patient en aveugle du bras", "Patient + évaluateur en aveugle · coach commun aux deux bras"],
    ["Analyse", "ITT stricte (tous randomisés)", "ITT + analyse de sensibilité worst-case + LOCF"],
    ["Données manquantes", "MNAR avec worst-case testé", "Imputation multiple + analyse de sensibilité pré-spécifiée"],
    ["Critère primaire", "FIQ avec adjudication indépendante", "FIQ + co-primary objectif (ex : consommation antalgiques en mg/j)"],
    ["Co-médications", "Listées à l'inclusion + stratifiées", "Listées + stables pendant toute l'étude + analysées en sous-groupe"],
    ["Durée suivi", "6 mois minimum", "12 mois pour fibromyalgie chronique"],
    ["Dispositif évalué", "REM-3 directement", "REM-3 — pas d'extrapolation générationnelle"],
    ["Coaching", "Identique dans les deux bras", "Protocole coaching standardisé commun + aveugle des coachs sur l'allocation"],
]
design_tbl = Table(design_rows, colWidths=[3.5*cm, 5.5*cm, W-4.4*cm-9.2*cm],
    style=[
        ("BACKGROUND",(0,0),(-1,0),DARK_BLUE), ("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTNAME",(0,1),(0,-1),"Helvetica-Bold"),
        ("TEXTCOLOR",(0,1),(0,-1),DARK_BLUE), ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("GRID",(0,0),(-1,-1),0.5,BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1),7), ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT_GRAY]),
        ("TEXTCOLOR",(2,1),(-1,-1),GREEN),
    ])
story.append(design_tbl)
story.append(Spacer(1,14))

# ── 8. OPPORTUNITÉ — MESSAGE POSITIF ─────────────────────────────────────────
story.append(Paragraph("8. Opportunité — pourquoi les résultats sont encourageants", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

opp_inner = Table([
    [Paragraph("Points positifs issus de FIBREPIK :", S("pp",fontSize=9.5,textColor=DARK_BLUE,fontName="Helvetica-Bold",leading=13))],
    [Paragraph(
        "• Le signal d'efficacité est réel et statistiquement significatif (p=0,021) — "
        "55% de répondeurs vs 36% dans le bras contrôle.\n"
        "• La fibromyalgie est une pathologie sans traitement médicamenteux remboursé — "
        "besoin médical non couvert fort.\n"
        "• Le statut FDA Breakthrough Device (2022) indique un potentiel reconnu.\n"
        "• Les événements indésirables sont non graves et gérables (3,3% en surveillance marché).\n"
        "• La Commission elle-même encourage explicitement la réalisation d'études complémentaires.",
        S("opp",fontSize=9,textColor=colors.HexColor("#1e3a5f"),leading=14,spaceAfter=0)
    )],
], style=[("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
          ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
story.append(colored_box(opp_inner, GREEN_LIGHT, pad=12))
story.append(Spacer(1,6))
story.append(Paragraph(
    "Le refus HAS n'est pas un refus définitif sur l'efficacité du dispositif. "
    "C'est un refus sur la qualité de la démonstration. Avec une étude sham-contrôlée en double aveugle, "
    "les mêmes résultats deviendraient potentiellement acceptables.",
    styles["body"]))
story.append(Spacer(1,14))

# ── FOOTER ───────────────────────────────────────────────────────────────────
story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=8, spaceAfter=6))
story.append(Paragraph(
    "Rapport généré par RWE-v5 · Moteur épistémique causal HAS/CNEDiMTS · Juin 2026  |  "
    "Basé sur l'avis CNEDiMTS du 11 mars 2025 (données publiques)  |  Confidentiel",
    styles["footer"]))

doc.build(story)
print(f"PDF généré : {out_path}")
