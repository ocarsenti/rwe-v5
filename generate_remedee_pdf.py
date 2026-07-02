"""Generate a complete diagnostic PDF for Remedee case."""

import sys
sys.path.insert(0, "/home/olive/rwe-v5")

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import PageBreak

from gold_dataset import process_case, _case_remedee
from models import ClinicalClaim, Endpoint, EndpointNature, CausalRole
from engine import analyze

# ── palette ──────────────────────────────────────────────────────────────────
DARK_BLUE   = colors.HexColor("#1a3557")
MID_BLUE    = colors.HexColor("#2563eb")
LIGHT_BLUE  = colors.HexColor("#dbeafe")
ORANGE      = colors.HexColor("#ea580c")
ORANGE_LIGHT= colors.HexColor("#ffedd5")
GREEN       = colors.HexColor("#16a34a")
GREEN_LIGHT = colors.HexColor("#dcfce7")
RED         = colors.HexColor("#dc2626")
RED_LIGHT   = colors.HexColor("#fee2e2")
YELLOW      = colors.HexColor("#ca8a04")
YELLOW_LIGHT= colors.HexColor("#fef9c3")
GRAY        = colors.HexColor("#6b7280")
LIGHT_GRAY  = colors.HexColor("#f3f4f6")
BORDER_GRAY = colors.HexColor("#e5e7eb")
WHITE       = colors.white

W, H = A4

# ── styles ───────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    s = ParagraphStyle(name, parent=base[parent], **kw)
    return s

styles = {
    "title":      S("title",      fontSize=22, textColor=WHITE,       leading=28, spaceAfter=0, alignment=TA_LEFT, fontName="Helvetica-Bold"),
    "subtitle":   S("subtitle",   fontSize=11, textColor=colors.HexColor("#bfdbfe"), leading=16, spaceAfter=0, alignment=TA_LEFT),
    "meta":       S("meta",       fontSize=9,  textColor=colors.HexColor("#93c5fd"), leading=13, spaceAfter=0),
    "h2":         S("h2",         fontSize=13, textColor=DARK_BLUE,   leading=18, spaceBefore=14, spaceAfter=4, fontName="Helvetica-Bold"),
    "h3":         S("h3",         fontSize=10.5, textColor=DARK_BLUE, leading=15, spaceBefore=8,  spaceAfter=3, fontName="Helvetica-Bold"),
    "body":       S("body",       fontSize=9.5, textColor=colors.HexColor("#1f2937"), leading=14, spaceAfter=4, alignment=TA_JUSTIFY),
    "body_sm":    S("body_sm",    fontSize=8.5, textColor=colors.HexColor("#374151"), leading=13, spaceAfter=2),
    "label":      S("label",      fontSize=8,  textColor=GRAY,        leading=11, spaceAfter=1, fontName="Helvetica-Bold"),
    "badge_ok":   S("badge_ok",   fontSize=8.5, textColor=GREEN,      leading=12, fontName="Helvetica-Bold"),
    "badge_warn": S("badge_warn", fontSize=8.5, textColor=ORANGE,     leading=12, fontName="Helvetica-Bold"),
    "badge_bad":  S("badge_bad",  fontSize=8.5, textColor=RED,        leading=12, fontName="Helvetica-Bold"),
    "mono":       S("mono",       fontSize=8.5, textColor=colors.HexColor("#1e293b"), leading=13, fontName="Courier", spaceAfter=2),
    "footer":     S("footer",     fontSize=7.5, textColor=GRAY,       leading=11, alignment=TA_CENTER),
    "quote":      S("quote",      fontSize=9,   textColor=colors.HexColor("#374151"), leading=14, leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4, alignment=TA_JUSTIFY, fontName="Helvetica-Oblique"),
    "has_quote":  S("has_quote",  fontSize=9.5, textColor=DARK_BLUE,  leading=15, leftIndent=16, rightIndent=8, spaceBefore=6, spaceAfter=6, alignment=TA_JUSTIFY, fontName="Helvetica-Oblique"),
    "endpoint_name": S("ep_name", fontSize=9, textColor=colors.HexColor("#1e3a5f"), leading=13, fontName="Helvetica-Bold"),
    "chip_ok":    S("chip_ok",    fontSize=8, textColor=GREEN,        leading=11, fontName="Helvetica-Bold"),
    "chip_warn":  S("chip_warn",  fontSize=8, textColor=ORANGE,       leading=11, fontName="Helvetica-Bold"),
    "chip_bad":   S("chip_bad",   fontSize=8, textColor=RED,          leading=11, fontName="Helvetica-Bold"),
}

# ── data ─────────────────────────────────────────────────────────────────────
case_id, claim = _case_remedee()
gold = process_case(case_id, claim)
engine_out = analyze(claim)

# ── helpers ──────────────────────────────────────────────────────────────────
def colored_box(inner, bg, pad=6, radius=0):
    return Table([[inner]], colWidths=[W - 4.4*cm],
                 style=[
                     ("BACKGROUND",  (0,0), (-1,-1), bg),
                     ("ROUNDEDCORNERS", [4]),
                     ("TOPPADDING",  (0,0), (-1,-1), pad),
                     ("BOTTOMPADDING",(0,0),(-1,-1), pad),
                     ("LEFTPADDING", (0,0), (-1,-1), pad+2),
                     ("RIGHTPADDING",(0,0), (-1,-1), pad),
                 ])

def severity_color(score):
    if score >= 0.8: return RED
    if score >= 0.5: return ORANGE
    return GREEN

def severity_label(score):
    if score >= 0.8: return "ÉLEVÉE"
    if score >= 0.5: return "MODÉRÉE"
    return "FAIBLE"

def status_color(status):
    s = str(status)
    if "ACCEPTABLE_WITH" in s: return ORANGE
    if "INVALID" in s or "REJECT" in s: return RED
    if "ACCEPTABLE" in s: return GREEN
    return GRAY

def status_label(status):
    m = {
        "ACCEPTABLE_WITH_REDESIGN":  "ACCEPTABLE AVEC REFONTE",
        "INVALID_AS_PRIMARY_ENDPOINT_ONLY": "INVALIDE COMME CRITÈRE PRIMAIRE",
        "ACCEPTABLE_WITH_CONDITIONS":"ACCEPTABLE SOUS CONDITIONS",
        "ACCEPTABLE_PRIMARY_WITH_CONDITIONS":"ACCEPTABLE SOUS CONDITIONS",
        "REJECTED_UNLESS_EXTERNAL_VALIDATION":"REJETÉ SAUF VALIDATION EXTERNE",
        "ACCEPTABLE_SECONDARY_ONLY":"SECONDAIRE UNIQUEMENT",
    }
    k = str(status).replace("FinalRegulatoryStatus.", "")
    return m.get(k, k)

def ep_status_label(st):
    s = str(st).replace("EndpointStatus.", "")
    m = {
        "ACCEPTABLE_WITH_CONDITIONS":"Acceptable sous conditions",
        "INVALID_UNLESS_REDEFINED":  "Invalide — à redéfinir",
        "ACCEPTABLE":                "Acceptable",
        "REJECTED":                  "Rejeté",
    }
    return m.get(s, s)

def ep_status_style(st):
    s = str(st)
    if "ACCEPTABLE_WITH" in s: return styles["chip_warn"]
    if "INVALID" in s or "REJECT" in s: return styles["chip_bad"]
    return styles["chip_ok"]

def repair_type_label(t):
    m = {
        "UTILIZATION": "Utilisation / données admin.",
        "HARD_CLINICAL":"Critère clinique dur",
        "BIOMARKER":   "Biomarqueur",
        "SURVIVAL":    "Survie",
        "PROM":        "PROM",
    }
    return m.get(str(t).replace("RepairEndpointType.", ""), str(t))

def reg_label(r):
    m = {
        "PRIMARY_CANDIDATE":"Critère primaire candidat",
        "SECONDARY_ONLY":   "Critère secondaire",
        "EXPLORATORY":      "Exploratoire",
    }
    return m.get(str(r).replace("RegulatoryStrength.", ""), str(r))

# ── document builder ──────────────────────────────────────────────────────────
out_path = "/home/olive/rwe-v5/remedee_diagnostic.pdf"
doc = SimpleDocTemplate(
    out_path, pagesize=A4,
    topMargin=0, bottomMargin=1.8*cm,
    leftMargin=2.2*cm, rightMargin=2.2*cm
)

story = []

# ── HEADER BAND ──────────────────────────────────────────────────────────────
header_data = [[
    Table([
        [Paragraph("REMEDEE LABS", styles["title"])],
        [Paragraph("Bracelet de neurostimulation par ondes millimétriques", styles["subtitle"])],
        [Spacer(1, 6)],
        [Paragraph("Diagnostic épistémique · Évaluation HAS/CNEDiMTS · Juin 2026", styles["meta"])],
    ], colWidths=[W - 4.4*cm],
       style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
]]
header_tbl = Table(header_data, colWidths=[W - 4.4*cm],
    style=[
        ("BACKGROUND", (0,0),(-1,-1), DARK_BLUE),
        ("TOPPADDING", (0,0),(-1,-1), 28),
        ("BOTTOMPADDING",(0,0),(-1,-1), 24),
        ("LEFTPADDING", (0,0),(-1,-1), 24),
        ("RIGHTPADDING",(0,0),(-1,-1), 24),
    ])
story.append(header_tbl)
story.append(Spacer(1, 14))

# ── SUMMARY VERDICT ──────────────────────────────────────────────────────────
score = gold.issue_detection.severity_score
sc = severity_color(score)
final_status = gold.final_regulatory_status

verdict_inner = Table([
    [Paragraph("VERDICT RÉGLEMENTAIRE", styles["label"]), ""],
    [Paragraph(status_label(final_status), ParagraphStyle("verd", fontSize=16,
        textColor=status_color(final_status), fontName="Helvetica-Bold", leading=20)),
     Table([
         [Paragraph("Sévérité", styles["label"])],
         [Paragraph(f"{int(score*100)}/100  —  {severity_label(score)}",
                    ParagraphStyle("sev", fontSize=11, textColor=sc, fontName="Helvetica-Bold", leading=14))],
     ], style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
               ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
    ],
], colWidths=[None, 5*cm],
   style=[("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
          ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
          ("VALIGN",(0,0),(-1,-1),"MIDDLE")])

story.append(colored_box(verdict_inner, LIGHT_BLUE, pad=14))
story.append(Spacer(1, 14))

# ── SECTION 1 : CLAIM ─────────────────────────────────────────────────────────
story.append(Paragraph("1. Analyse du claim clinique", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

claim_rows = [
    ["Dispositif", gold.device_context.name],
    ["Domaine",    gold.device_context.domain],
    ["Type",       gold.device_context.intervention_type],
    ["Claim",      claim.text],
]
claim_tbl = Table(claim_rows, colWidths=[3.5*cm, W - 4.4*cm - 3.5*cm - 0.4*cm],
    style=[
        ("FONTNAME",  (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0),(-1,-1), 9),
        ("TEXTCOLOR", (0,0),(0,-1), DARK_BLUE),
        ("TEXTCOLOR", (1,0),(1,-1), colors.HexColor("#111827")),
        ("BACKGROUND",(0,0),(0,-1), LIGHT_GRAY),
        ("BACKGROUND",(1,0),(1,-1), WHITE),
        ("GRID",      (0,0),(-1,-1), 0.5, BORDER_GRAY),
        ("TOPPADDING",(0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",    (0,0),(-1,-1), "TOP"),
    ])
story.append(claim_tbl)
story.append(Spacer(1, 12))

# ── SECTION 2 : GRAPHE CAUSAL ─────────────────────────────────────────────────
story.append(Paragraph("2. Graphe causal", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

cg = gold.causal_graph
story.append(Paragraph(cg.summary, styles["body"]))

if cg.measurement_influence_paths:
    story.append(Spacer(1, 4))
    story.append(Paragraph("Chemins d'influence mesurée :", styles["h3"]))
    for path in cg.measurement_influence_paths:
        story.append(Paragraph(f"→  {path}", styles["mono"]))

if cg.mediators:
    story.append(Spacer(1, 4))
    story.append(Paragraph("Médiateurs identifiés :", styles["h3"]))
    for m in cg.mediators:
        story.append(Paragraph(f"•  {m}", styles["body_sm"]))
else:
    story.append(Paragraph("Aucun médiateur biologique explicitement documenté dans les données disponibles. "
                            "La chaîne causale reste à valider (endorphine → douleur).", styles["body_sm"]))

story.append(Spacer(1, 12))

# ── SECTION 3 : BIAIS ─────────────────────────────────────────────────────────
story.append(Paragraph("3. Détection des biais", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

issue = gold.issue_detection
bias_color = severity_color(issue.severity_score)
bias_bg = {RED: RED_LIGHT, ORANGE: ORANGE_LIGHT, GREEN: GREEN_LIGHT}[bias_color]

bias_inner = Table([
    [Paragraph(f"Issue principale : {str(issue.primary_issue_type).replace('IssueType.','').replace('_',' ')}",
               ParagraphStyle("bi", fontSize=10, textColor=bias_color, fontName="Helvetica-Bold", leading=14)),
     Paragraph(f"Score : {int(issue.severity_score*100)}/100",
               ParagraphStyle("bs", fontSize=10, textColor=bias_color, fontName="Helvetica-Bold", leading=14, alignment=TA_RIGHT))],
], colWidths=[None, 3*cm],
   style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
          ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])
story.append(colored_box(bias_inner, bias_bg, pad=10))
story.append(Spacer(1, 8))

# Engine bias flags
if engine_out.bias_flags:
    bf_rows = [["Biais", "Sévérité", "Description"]]
    for bf in engine_out.bias_flags:
        sev_str = str(bf.severity)
        if "HIGH" in sev_str: sev_c = RED
        elif "MEDIUM" in sev_str: sev_c = ORANGE
        else: sev_c = GREEN
        bf_rows.append([
            Paragraph(str(bf.flag.value).replace("_"," "), ParagraphStyle("bfn", fontSize=8.5, fontName="Helvetica-Bold", textColor=sev_c, leading=12)),
            Paragraph(sev_str.split(".")[-1], ParagraphStyle("bfs", fontSize=8.5, textColor=sev_c, leading=12)),
            Paragraph(str(bf.detail)[:160] if bf.detail else "—", styles["body_sm"]),
        ])
    bf_tbl = Table(bf_rows, colWidths=[3.5*cm, 2*cm, W - 4.4*cm - 5.7*cm],
        style=[
            ("BACKGROUND", (0,0),(-1,0), DARK_BLUE),
            ("TEXTCOLOR",  (0,0),(-1,0), WHITE),
            ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0),(-1,-1), 8.5),
            ("GRID",       (0,0),(-1,-1), 0.5, BORDER_GRAY),
            ("TOPPADDING", (0,0),(-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING",(0,0),(-1,-1), 7),
            ("RIGHTPADDING",(0,0),(-1,-1), 7),
            ("VALIGN",     (0,0),(-1,-1), "TOP"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GRAY]),
        ])
    story.append(bf_tbl)
else:
    story.append(Paragraph("Aucun biais critique détecté par l'engine.", styles["body_sm"]))

story.append(Spacer(1, 14))

# ── SECTION 4 : ENDPOINTS ─────────────────────────────────────────────────────
story.append(Paragraph("4. Analyse des critères de jugement", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

for i, ep_analysis in enumerate(gold.endpoint_analyses):
    oe = ep_analysis.original_endpoint
    ep_bg = ORANGE_LIGHT if "ACCEPTABLE_WITH" in str(oe.status) else RED_LIGHT if "INVALID" in str(oe.status) or "REJECT" in str(oe.status) else GREEN_LIGHT

    ep_header = Table([
        [Paragraph(oe.name, styles["endpoint_name"]),
         Paragraph(ep_status_label(oe.status), ep_status_style(oe.status))],
    ], colWidths=[None, 5.5*cm],
       style=[("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
              ("VALIGN",(0,0),(-1,-1),"MIDDLE")])

    ep_inner = Table([
        [ep_header],
        [Paragraph(oe.failure_mode, styles["body_sm"])],
    ], style=[("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2),
              ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)])

    story.append(colored_box(ep_inner, ep_bg, pad=10))
    story.append(Spacer(1, 6))

    if ep_analysis.repair_endpoints:
        story.append(Paragraph("Critères de remplacement recommandés :", styles["h3"]))
        rep_rows = [["Critère proposé", "Type", "Robustesse", "Positionnement"]]
        for r in ep_analysis.repair_endpoints:
            rob = r.robustness_score
            rob_c = GREEN if rob >= 0.75 else ORANGE if rob >= 0.5 else RED
            rep_rows.append([
                Paragraph(r.endpoint_name, styles["body_sm"]),
                Paragraph(repair_type_label(r.type), styles["body_sm"]),
                Paragraph(f"{int(rob*100)}%",
                          ParagraphStyle("rob", fontSize=8.5, textColor=rob_c, fontName="Helvetica-Bold", leading=12)),
                Paragraph(reg_label(r.regulatory_strength), styles["body_sm"]),
            ])
        rep_tbl = Table(rep_rows,
            colWidths=[6.5*cm, 3.5*cm, 1.8*cm, W - 4.4*cm - 12*cm],
            style=[
                ("BACKGROUND", (0,0),(-1,0), DARK_BLUE),
                ("TEXTCOLOR",  (0,0),(-1,0), WHITE),
                ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0),(-1,-1), 8.5),
                ("GRID",       (0,0),(-1,-1), 0.5, BORDER_GRAY),
                ("TOPPADDING", (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("LEFTPADDING",(0,0),(-1,-1), 7),
                ("RIGHTPADDING",(0,0),(-1,-1), 7),
                ("VALIGN",     (0,0),(-1,-1), "TOP"),
                ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GRAY]),
            ])
        story.append(rep_tbl)

    if i < len(gold.endpoint_analyses) - 1:
        story.append(Spacer(1, 10))

story.append(Spacer(1, 14))

# ── SECTION 5 : CHEMINS RÉGLEMENTAIRES ───────────────────────────────────────
story.append(Paragraph("5. Chemins réglementaires acceptables", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

for j, rc in enumerate(gold.regulatory_conditions):
    label_txt = f"Chemin {j+1} — {str(rc.design_type_required).replace('DesignTypeRequired.','').replace('_','-')}"
    path_rows = [
        ["Aveugle requis",               "Oui" if rc.blinding_required else "Non"],
        ["Adjudication indépendante",     "Oui" if rc.independent_adjudication_required else "Non"],
        ["Source externe requise",        "Oui" if rc.external_data_source_required else "Non"],
        ["Repositionnement critère",      rc.endpoint_repositioning],
        ["Design requis",                 str(rc.design_type_required).replace("DesignTypeRequired.", "").replace("_", "-")],
        ["Seuil biais acceptable",        str(rc.acceptable_bias_threshold).replace("BiasThreshold.","").upper()],
    ]
    path_tbl = Table(path_rows, colWidths=[6*cm, W - 4.4*cm - 6.2*cm],
        style=[
            ("FONTNAME",  (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTSIZE",  (0,0),(-1,-1), 8.5),
            ("TEXTCOLOR", (0,0),(0,-1), DARK_BLUE),
            ("GRID",      (0,0),(-1,-1), 0.5, BORDER_GRAY),
            ("TOPPADDING",(0,0),(-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING",(0,0),(-1,-1), 8),
            ("RIGHTPADDING",(0,0),(-1,-1), 8),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [LIGHT_GRAY, WHITE]),
        ])

    path_group = [
        Paragraph(label_txt, styles["h3"]),
        path_tbl,
        Spacer(1, 8),
    ]
    story.append(KeepTogether(path_group))

story.append(Spacer(1, 6))

# ── SECTION 6 : INTERPRÉTATION HAS ──────────────────────────────────────────
story.append(Paragraph("6. Interprétation HAS/CNEDiMTS simulée", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=8))

has_inner = Table([
    [Paragraph("« " + gold.has_interpretation + " »", styles["has_quote"])],
], style=[
    ("BACKGROUND",  (0,0),(-1,-1), LIGHT_BLUE),
    ("LEFTBORDERPADDING", (0,0),(-1,-1), 0),
    ("TOPPADDING",  (0,0),(-1,-1), 14),
    ("BOTTOMPADDING",(0,0),(-1,-1), 14),
    ("LEFTPADDING", (0,0),(-1,-1), 16),
    ("RIGHTPADDING",(0,0),(-1,-1), 12),
])
story.append(has_inner)
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Cette interprétation est générée par le moteur épistémique RWE-v5 sur la base "
    "de la logique décisionnelle CNEDiMTS reconstituée. Elle est indicative et non "
    "opposable à une commission réelle.",
    ParagraphStyle("disc", fontSize=7.5, textColor=GRAY, leading=11, fontName="Helvetica-Oblique")
))
story.append(Spacer(1, 14))

# ── SECTION 7 : RECOMMANDATIONS ACTIONNABLES ─────────────────────────────────
story.append(Paragraph("7. Recommandations actionnables", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

reco_rows = [
    ["#", "Action", "Impact", "Effort"],
    ["1", "Ajouter un critère co-primaire objectif\n(consommation d'antalgiques en mg morphine-équivalent/jour, "
          "mesuré sur 12 semaines via carnet de prescription)", "Critique — débloque le critère primaire", "Faible"],
    ["2", "Passer à un design en double aveugle avec sham\n(stimulation placebo identique visuellement)",
          "Critique — élimine PERCEPTION_BIAS", "Moyen"],
    ["3", "Documenter le médiateur biologique\n(béta-endorphines sériques à T+2h et T+4h)",
          "Important — valide la chaîne causale", "Faible"],
    ["4", "Repositionner EVA en critère secondaire\n(non plus primaire)",
          "Important — réduit le risque réglementaire", "Immédiat"],
    ["5", "Ajouter un critère de ressources de santé\n(hospitalisations via données Ameli à 12 mois)",
          "Bonus — renforce acceptabilité HAS", "Moyen"],
]
reco_tbl = Table(reco_rows, colWidths=[0.8*cm, 7.5*cm, 4*cm, 2.5*cm],
    style=[
        ("BACKGROUND", (0,0),(-1,0), DARK_BLUE),
        ("TEXTCOLOR",  (0,0),(-1,0), WHITE),
        ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTNAME",   (0,1),(0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (0,1),(0,-1), MID_BLUE),
        ("FONTSIZE",   (0,0),(-1,-1), 8.5),
        ("GRID",       (0,0),(-1,-1), 0.5, BORDER_GRAY),
        ("TOPPADDING", (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 7),
        ("RIGHTPADDING",(0,0),(-1,-1), 7),
        ("VALIGN",     (0,0),(-1,-1), "TOP"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GRAY]),
    ])
story.append(reco_tbl)
story.append(Spacer(1, 14))

# ── SECTION 8 : COMPARAISON AVEC ODYSIGHT ────────────────────────────────────
story.append(Paragraph("8. Positionnement vs cas de référence (Odysight)", styles["h2"]))
story.append(HRFlowable(width="100%", thickness=1, color=BORDER_GRAY, spaceAfter=6))

comp_rows = [
    ["Dimension",         "Odysight",              "Remedee"],
    ["Statut final",      "INVALIDE (primaire)",    "ACCEPTABLE AVEC REFONTE"],
    ["Sévérité",          "90/100  (ÉLEVÉE)",       "60/100  (MODÉRÉE)"],
    ["Issue principale",  "Circularité mesure",     "Biais endpoint subjectif"],
    ["Design requis",     "PRAGMATIC RCT",          "SHAM-RCT ou Pragmatic RCT"],
    ["Critère primaire",  "À remplacer (circulaire)","Acceptable sous conditions d'aveugle"],
    ["Réparabilité",      "Partielle (redesign lourd)","Bonne (modifications ciblées)"],
]
comp_tbl = Table(comp_rows, colWidths=[4.2*cm, 5.8*cm, 5.3*cm],
    style=[
        ("BACKGROUND", (0,0),(-1,0), DARK_BLUE),
        ("TEXTCOLOR",  (0,0),(-1,0), WHITE),
        ("FONTNAME",   (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTNAME",   (0,1),(0,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (0,1),(0,-1), DARK_BLUE),
        ("FONTSIZE",   (0,0),(-1,-1), 8.5),
        ("GRID",       (0,0),(-1,-1), 0.5, BORDER_GRAY),
        ("TOPPADDING", (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",(0,0),(-1,-1), 8),
        ("RIGHTPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_GRAY]),
        ("TEXTCOLOR",  (1,2),(1,2), RED),
        ("TEXTCOLOR",  (2,2),(2,2), ORANGE),
        ("TEXTCOLOR",  (1,1),(1,1), RED),
        ("TEXTCOLOR",  (2,1),(2,1), ORANGE),
    ])
story.append(comp_tbl)
story.append(Spacer(1, 14))

# ── FOOTER ───────────────────────────────────────────────────────────────────
story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GRAY, spaceBefore=8, spaceAfter=6))
story.append(Paragraph(
    "Rapport généré par RWE-v5 · Moteur épistémique causal HAS/CNEDiMTS · Juin 2026  |  "
    "Confidentiel — usage interne uniquement",
    styles["footer"]
))

# ── BUILD ─────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"PDF généré : {out_path}")
