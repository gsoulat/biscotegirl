# BiscoteGirl 💪

Un bot de réservation fitness automatisé avec notifications Discord enrichies pour HeitzFit.

## 📝 Description

BiscoteGirl est un système automatisé qui vous permet de :
- Surveiller l'ouverture des plannings de cours sur HeitzFit
- Recevoir des notifications Discord lorsque les cours deviennent disponibles
- Réserver automatiquement vos cours préférés
- Obtenir des informations supplémentaires comme la météo pour le jour de vos cours

## 🌟 Fonctionnalités

- **Surveillance automatique des plannings** : Vérifie régulièrement l'ouverture des plannings pour les jours à venir
- **Notifications Discord** : Envoi de messages détaillés avec les cours disponibles
- **Réservation automatique** : Configuration possible pour réserver automatiquement vos cours préférés
- **Multi-utilisateurs** : Gestion de plusieurs comptes utilisateurs
- **Informations météo** : Affichage des conditions météorologiques pour le jour des cours
- **Persistance des données** : Stockage des informations dans une base de données SQLite
- **Interface API** : Endpoints FastAPI pour l'intégration avec d'autres services

## 🚀 Installation

### Prérequis

- Python 3.12+
- Poetry (gestionnaire de dépendances)
- Un compte HeitzFit
- Un webhook Discord (pour les notifications)

### Installation des dépendances

```bash
# Cloner le dépôt
git clone https://github.com/votre-nom/biscotegirl.git
cd biscotegirl

# Installation des dépendances avec Poetry
poetry install

# Installation des navigateurs pour Playwright
poetry run playwright install chromium
```

### Configuration

1. Créer un fichier `.env` à la racine du projet avec les variables suivantes :

```env
# Credentials HeitzFit
EMAIL=votre_email@example.com
PASSWORD=votre_mot_de_passe

# URLs
BASE_URL=https://app.heitzfit.com
CENTER_ID=4831

# Planning configuration
TARGET_DAY_OFFSET=6
CHECK_INTERVAL=20
CHECK_START_TIME=07:00
CHECK_END_TIME=21:00

# Weather API (optionnel)
WHEATER_API=votre_cle_api_weather
WEATHER_CITY=Valenciennes

# Discord configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/votre_webhook_url
DISCORD_ENABLED=true
BISCOTEGIRL_AVATAR_URL=./images/biscotegirl.jpeg

# Browser configuration
PAGE_TIMEOUT=60000
RETRY_ATTEMPTS=3
RETRY_DELAY=5
RETRY_INTERVAL=30
ERROR_RETRY_INTERVAL=300
```

2. Initialiser la base de données:

```bash
poetry run python -c "from backend.services.database import Database; db = Database('./database.sqlite'); db.initialize_db()"
```

## 🔧 Utilisation

### Démarrer le bot en mode surveillance

```bash
poetry run python -m backend.main
```

### Démarrer le bot en mode scraping (pour remplir la base de données)

```bash
poetry run python -m backend.main --scraping
```

### Démarrer l'API

```bash
poetry run python -m backend.server
```

### Ajouter des réservations automatiques

Pour ajouter des réservations automatiques, vous devez d'abord ajouter un utilisateur puis configurer les réservations souhaitées :

```python
# Exemple d'utilisation via l'API ou en Python direct
from backend.services.database import Database

db = Database('./database.sqlite')

# Ajouter un utilisateur
user_id = db.add_user(
    email="utilisateur@example.com",
    password="mot_de_passe",
    discord_name="Nom Discord"
)

# Ajouter une réservation (jour de la semaine en français)
db.add_reservation(
    user_id=user_id,
    day="lundi",  # lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche
    activity="BOXING"  # Nom exact de l'activité comme affiché sur HeitzFit
)
```

## 📊 Structure du projet

```
BiscoteGirl/
├── backend/
│   ├── api/                # Endpoints FastAPI
│   ├── config/             # Configuration du projet
│   ├── services/           # Services principaux
│   │   ├── database.py     # Gestion de la base de données
│   │   ├── discord_notifier.py  # Notifications Discord
│   │   ├── planning_checker.py  # Vérification du planning
│   │   └── scraping_service.py  # Service de scraping
│   ├── utils/              # Utilitaires
│   │   └── logger.py       # Configuration du logger
│   ├── __init__.py
│   ├── main.py             # Point d'entrée principal
│   └── server.py           # Serveur FastAPI
├── logs/                   # Logs du système
├── .env                    # Variables d'environnement
├── pyproject.toml          # Configuration Poetry
└── ruff.toml               # Configuration linter
```

## 🔍 Fonctionnement technique

Le système utilise Playwright pour automatiser la navigation sur le site HeitzFit. Il se connecte avec vos identifiants, navigue jusqu'au planning des cours pour la date cible (par défaut J+6) et vérifie si des cours sont disponibles.

Si des cours sont détectés, il envoie une notification Discord avec les détails des cours disponibles, y compris les informations météo pour le jour concerné.

Le système peut également réserver automatiquement des cours en fonction des préférences configurées dans la base de données.

## 📝 Logs

Les logs sont stockés dans le dossier `logs/`. Ils contiennent des informations détaillées sur les opérations effectuées, les erreurs rencontrées et les actions entreprises.

## 🛠 Dépannage

### Screenshots d'erreur

En cas d'erreur, le système prend automatiquement des captures d'écran qui sont stockées dans le dossier `logs/`. Ces captures peuvent aider à diagnostiquer les problèmes.

### Erreurs fréquentes

- **Timeout lors de la connexion** : Vérifiez vos identifiants et votre connexion internet
- **Erreur lors de la sélection de date** : Le format de date peut avoir changé sur HeitzFit
- **Webhook Discord non configuré** : Vérifiez l'URL du webhook dans le fichier .env

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou à soumettre une pull request.

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).

## 🙏 Remerciements

- [HeitzFit](https://app.heitzfit.com) pour leur service de réservation de cours de fitness
- [Discord](https://discord.com/) pour leur API de webhooks
- [Playwright](https://playwright.dev/) pour l'automatisation de navigateur
- [FastAPI](https://fastapi.tiangolo.com/) pour l'API REST
- [Loguru](https://github.com/Delgan/loguru) pour la gestion des logs