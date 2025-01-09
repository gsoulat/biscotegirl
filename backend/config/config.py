from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv(override=True)


class Config:
    # Paths de base
    BASE_DIR = Path(__file__).parent.parent.parent
    LOGS_DIR = BASE_DIR / "logs"

    # Credentials HeitzFit
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")

    # URLs
    BASE_URL = os.getenv("BASE_URL", "https://app.heitzfit.com")
    CENTER_ID = os.getenv("CENTER_ID", "4831")
    PLANNING_URL = f"{BASE_URL}/#/planning/browse"
    LOGIN_URL = f"{BASE_URL}/?center={CENTER_ID}"

    # Planning check configuration
    TARGET_DAY_OFFSET = int(os.getenv("TARGET_DAY_OFFSET", "6"))
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))

    # Check times
    CHECK_START_TIME = datetime.strptime(
        os.getenv("CHECK_START_TIME", "07:00"), "%H:%M"
    ).time()
    CHECK_END_TIME = datetime.strptime(
        os.getenv("CHECK_END_TIME", "21:00"), "%H:%M"
    ).time()

    # OpenWeatherMap configuration
    WHEATER_API = os.getenv("WHEATER_API")
    WEATHER_CITY = os.getenv("WEATHER_CITY", "Valenciennes")

    # Discord configuration
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "true").lower() == "true"
    BISCOTEGIRL_AVATAR_URL = os.getenv(
        "BISCOTEGIRL_AVATAR_URL",
        "./images/biscotegirl.jpeg",
    )

    # Browser configuration
    PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "60000"))
    RETRY_ATTEMPTS = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))

    # Database configuration
    DATABASE_PATH = str(BASE_DIR / "database.sqlite")
    RETRY_INTERVAL = int(os.getenv("RETRY_INTERVAL", "30"))
    ERROR_RETRY_INTERVAL = int(os.getenv("ERROR_RETRY_INTERVAL", "300"))

    # Selectors
    SELECTORS = {
        # Login form
        "email_input": "input[type='email']",
        "password_input": "input[type='password']",
        "login_button": "span:has-text('CONNEXION')",
        # Navigation elements
        "ok_button": "text=OK",
        "alert_ok_button": "button.alert-button-role-success",
        # Success verification elements
        "success_elements": ["text=Planning", "text=Mon Club", "text=Mes réservations"],
        # Planning navigation
        "month_picker": ".booking-month-picker",
        "ok_button_date": "//ion-alert//button[contains(.,'OK')]",
        "month_option": "//button[contains(@class, 'alert-radio-button') and contains(., '{}')]",
    }

    # Mapping des mois en français
    MONTHS_FR = {
        1: "janvier",
        2: "février",
        3: "mars",
        4: "avril",
        5: "mai",
        6: "juin",
        7: "juillet",
        8: "août",
        9: "septembre",
        10: "octobre",
        11: "novembre",
        12: "décembre",
    }

    # Mapping des jours de la semaine en français
    WEEKDAYS_FR = {
        0: "lun.",
        1: "mar.",
        2: "mer.",
        3: "jeu.",
        4: "ven.",
        5: "sam.",
        6: "dim.",
    }

    # Création des répertoires nécessaires
    @classmethod
    def create_directories(cls):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Validation de la configuration
    @classmethod
    def validate(cls):
        """Valide la configuration requise"""
        required_vars = ["EMAIL", "PASSWORD", "DISCORD_WEBHOOK_URL"]
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(
                f"Variables d'environnement manquantes: {', '.join(missing_vars)}"
            )

    # Initialisation
    @classmethod
    def initialize(cls):
        """Initialise la configuration"""
        cls.create_directories()
        cls.validate()


# Initialisation automatique lors de l'import
Config.initialize()
