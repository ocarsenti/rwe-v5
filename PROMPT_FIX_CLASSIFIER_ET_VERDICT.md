# Corrections à apporter — endpoint_classifier.py + logique de verdict

## Partie 1 — Corrections dans `endpoint_classifier.py`

1. Remplace tous les tests `marker in text` par un matching avec limite de mot (regex `\b`) pour éviter les faux positifs type "lab" dans "label".

2. La variable `is_hard_clinical` utilise `name_text` au lieu de `text` — uniformise pour qu'elle checke aussi la description comme les autres flags.

3. Dans `_match_nature`, documente en commentaire pourquoi INSTRUMENTED est prioritaire sur SUBJECTIVE et OBJECTIVE, ou revois la priorité si ce n'est pas justifié.

4. Ajoute une whitelist de surrogates validés connus (type HbA1c, LDL-C, pression artérielle) comme filet de sécurité en plus du flag `is_validated_surrogate`.

5. Vérifie si `DETECTION_BIAS` et `SURROGATE_RISK` peuvent se déclencher sur le même endpoint, et précise si c'est voulu ou s'il faut dédupliquer.

6. Fais retourner à `classify_endpoint` le marqueur exact qui a déclenché chaque nature et chaque flag, pour tracer la décision.

## Partie 2 — Changement de philosophie sur le verdict global

Objectif : l'outil doit repérer des problèmes méthodologiques, pas prédire la décision de la HAS.

7. Remplace le verdict ACCEPTABLE/REJECTED par un niveau de risque méthodologique FAIBLE/MODÉRÉ/ÉLEVÉ, pour ne pas donner l'impression de prédire la décision HAS.

8. Remplace le calcul du score composite d'`overall_verdict` par un comptage transparent du nombre de flags par sévérité, du type "3 CRITICAL, 2 HIGH, 1 MEDIUM", affiché tel quel sans agrégation opaque.

9. Dans l'affichage du rapport, mets la liste des `bias_flags` et des gaps en premier, et redescends le niveau de risque global en position secondaire, clairement labellisé comme tendance et non comme verdict.

10. Garde `run_cnedimts_comparison.py` et la comparaison aux avis HAS historiques comme outil de calibration interne du moteur, pas comme sortie affichée à l'utilisateur sur un nouveau dossier.
