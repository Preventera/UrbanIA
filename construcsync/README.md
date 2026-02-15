# ConstrucSync Municipal

**Orchestrateur de planification et coordination des chantiers municipaux**
Se positionne **EN AMONT** d'UrbanIA pour prévenir la coactivité plutôt que la détecter après coup.

## Position dans la chaîne

```
ConstrucSync (planification)  →  UrbanIA (surveillance)  →  NudgeAgent (alerte)
   AVANT le permis               PENDANT le chantier        TEMPS RÉEL
```

## 4 Agents

| Agent | Mission | Inputs |
|-------|---------|--------|
| **PermitOptimizerAgent** | Évalue chaque demande de permis, score de risque prédictif, recommandation approuver/reporter/conditionner | AGIR, CIFS, CNESST, SAAQ |
| **TerritoryPlannerAgent** | Carte de chaleur territoire, capacité par arrondissement, corridors stratégiques, saisonnalité | Permis actifs/planifiés, calendrier municipal |
| **ImpactSimulatorAgent** | Simulation "What-If" avec 3 scénarios (sans/avec/reporté), delta risque, incidents prédits | Score UrbanIA, flux piétons/cyclistes |
| **StakeholderSyncAgent** | Plan de coordination multi-parties prenantes, timeline, tâches, notifications multi-canal | Décision permis, conditions |

## Scoring

```
RiskScore = Coactivité × 0.30 + Vulnérables × 0.25 + Historique × 0.20 + Cascade × 0.15 + Saturation × 0.10
```

| Score | Sévérité | Recommandation |
|-------|----------|----------------|
| 0-30 | 🟢 Green | Approuver |
| 30-55 | 🟡 Yellow | Approuver avec suivi |
| 55-75 | 🟠 Orange | Conditionner |
| 75-100 | 🔴 Red | Reporter / Escalader HITL |

**⚠️ HITL obligatoire sur TOUTE décision de permis** — Charte AgenticX5

## Territoire Montréal

**19 arrondissements** avec capacité différenciée (3-15 chantiers simultanés max).

**10 corridors stratégiques protégés** :

| Corridor | Type | Priorité | Max simultanés |
|----------|------|----------|---------------|
| Sainte-Catherine | Piéton | 10/10 | 1 |
| REV Saint-Denis | Cyclable | 9/10 | 1 |
| René-Lévesque | Urgence | 10/10 | 1 |
| Berri / Station centrale | Transport | 10/10 | 1 |
| Canal Lachine | Cyclable | 8/10 | 1 |
| Notre-Dame | Urgence | 10/10 | 1 |

**4 saisons** avec contraintes spécifiques :
- Hiver (×1.3) : gel, déneigement, verglas
- Été (×1.15) : festivals, terrasses, tourisme
- Printemps (×1.1) : dégel, nids-de-poule
- Automne (×1.05) : rentrée scolaire

## Conditions de mitigation

Le système génère automatiquement des conditions de mitigation selon le risque :

- **Piétons** : Corridor sécurisé 1.5m, signaleur aux intersections
- **Cyclistes** : Déviation balisée, signalisation au sol
- **PMR** : Parcours accessible (pente 5%, largeur 1.5m)
- **Transport** : Notification STM 72h, relocalisation arrêts
- **Coactivité** : Réunion coordination hebdomadaire, coordonnateur dédié
- **Horaires** : Travaux bruyants 7h-19h, livraisons hors pointe

## API

```
POST /api/v1/permits/evaluate     → Évaluer une demande de permis
POST /api/v1/permits/simulate     → Simuler l'impact (3 scénarios)
GET  /api/v1/territory/snapshot   → État du territoire
GET  /api/v1/territory/corridors  → Corridors stratégiques
POST /api/v1/coordination/plan    → Plan de coordination
GET  /api/v1/seasonal             → Contraintes saisonnières
POST /api/v1/permits/query        → Requête RAG
GET  /api/v1/health               → Santé du service
```

## Tests

```bash
cd construcsync
python -m pytest tests/test_construcsync.py -v
# 35 passed
```

## Lien avec UrbanIA

Les données d'UrbanIA calibrent ConstrucSync :
- **54 403 lésions CNESST** → profils de risque par type de travaux
- **8 173 accidents SAAQ** → zones accidentogènes historiques
- **7 sources MTL temps réel** → état actuel du territoire

ConstrucSync utilise ces données pour évaluer chaque demande de permis **avant** l'émission, transformant le cycle de `détecter → alerter` en `prédire → prévenir → coordonner`.

## Conformité

- Charte AgenticX5 : HITL obligatoire, primauté de la vie
- ISO 45001 : Planification SST (Cl. 6.1, 8.1)
- Loi 25 / RGPD : Aucune donnée nominative dans le scoring
