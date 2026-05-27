# HA-Linky-MyElectricalData
# MyElectricalData — Linky pour Home Assistant

Intégration personnalisée pour Home Assistant permettant de suivre la consommation électrique d'un compteur Linky via l'API [MyElectricalData](https://www.myelectricaldata.fr).

## Fonctionnalités

- Puissance instantanée (W) — mise à jour toutes les 30 minutes
- Consommation du jour en cours (kWh)
- Consommation de la veille (kWh)
- Consommation sur les 7 derniers jours (kWh)
- Puissance de pointe du jour (W)
- **Injection automatique de l'historique complet** dans le dashboard Énergie de HA (depuis janvier 2025)

## Prérequis

- Un compteur Linky
- Un compte sur [MyElectricalData](https://www.myelectricaldata.fr) avec le consentement accordé
- Votre numéro PDL (14 chiffres, visible sur votre facture d'électricité)
- Votre token d'accès MyElectricalData

## Installation

### Via HACS (recommandé)

1. Dans HACS → Intégrations → ⋮ → Dépôts personnalisés
2. Ajouter `https://github.com/hollowr/HA-Linky-MyElectricalData` en catégorie **Intégration**
3. Télécharger l'intégration
4. Redémarrer Home Assistant

### Installation manuelle

Copier le dossier `custom_components/myelectricaldata` dans le répertoire `config/custom_components/` de votre installation Home Assistant, puis redémarrer.

## Configuration

1. Aller dans **Paramètres → Appareils et services → Ajouter une intégration**
2. Rechercher **MyElectricalData**
3. Saisir votre numéro PDL et votre token d'accès

## Capteurs créés

| Entité | Description | Unité |
|--------|-------------|-------|
| `sensor.linky_energie_totale` | Énergie totale cumulée *(à utiliser dans le dashboard Énergie)* | kWh |
| `sensor.linky_puissance_actuelle` | Puissance instantanée | W |
| `sensor.linky_consommation_aujourd_hui` | Consommation du jour | kWh |
| `sensor.linky_consommation_hier` | Consommation de la veille | kWh |
| `sensor.linky_consommation_semaine` | Consommation sur 7 jours | kWh |
| `sensor.linky_puissance_max_aujourd_hui` | Puissance de pointe du jour | W |

## Dashboard Énergie

Pour afficher les données dans le dashboard Énergie de Home Assistant :

1. **Paramètres → Énergie → Réseau électrique → Ajouter consommation**
2. Sélectionner `sensor.linky_energie_totale`

L'historique complet (depuis janvier 2025) est injecté automatiquement au premier démarrage.

## Remarques

- Les données Linky ont un délai d'environ 24h — la consommation d'aujourd'hui sera visible demain
- Les données sont rafraîchies toutes les heures
- Aucune donnée n'est stockée localement — tout est récupéré en direct depuis l'API MyElectricalData
  
## Faites lui un Don pour son travail

## Licence

MIT
