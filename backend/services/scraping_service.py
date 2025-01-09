from datetime import datetime, timedelta
import time
from typing import List, Dict
from loguru import logger
from app.config.config import Config
from app.services.planning_checker import PlanningChecker
from app.services.database import Database


class ScrapingService(PlanningChecker):
    def __init__(self, logger, headless: bool = True):
        super().__init__(logger, headless)
        self.db = Database(Config.DATABASE_PATH)

    def setup_database(self):
        """Crée les tables nécessaires si elles n'existent pas"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_discord TEXT NOT NULL UNIQUE,
                pseudo TEXT NOT NULL,
                login TEXT NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS planning (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekday TEXT NOT NULL,
                start_time TEXT NOT NULL,
                activity TEXT NOT NULL,
                room TEXT NOT NULL,
                capacity TEXT,
                is_full BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def save_activities(self, weekday: str, activities: List[Dict]) -> None:
        """Sauvegarde les activités dans la base de données"""
        for activity in activities:
            self.db.execute("""
                INSERT INTO planning (weekday, start_time, activity, room, capacity, is_full)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                weekday,
                activity['start_time'],
                activity['activity'],
                activity['room'],
                activity['capacity'],
                activity['is_full']
            ))

    def scrape_planning(self) -> None:
        """Scrape le planning pour les 7 prochains jours"""
        try:
            self.setup_database()
            self.initialize_browser()

            if not self.login(Config.LOGIN_URL, Config.EMAIL, Config.PASSWORD):
                logger.error("Échec de la connexion")
                return

            self.navigate_to_page(Config.PLANNING_URL)

            # Vérifier le planning pour les 7 prochains jours
            for day_offset in range(Config.TARGET_DAY_OFFSET + 1):
                target_date = datetime.now() + timedelta(days=day_offset)
                logger.info(f"📅 Scraping du planning pour le {target_date.strftime('%d/%m/%Y')}")

                try:
                    self.select_month(target_date)
                    if not self.select_date(target_date):
                        logger.error(f"Impossible de sélectionner la date {target_date}")
                        continue

                    has_activities, activities = self.check_activities()
                    if has_activities:
                        weekday = target_date.strftime("%A").lower()  # jour en français
                        self.save_activities(weekday, activities)
                        logger.info(f"✅ Planning sauvegardé pour {weekday}")

                    time.sleep(2)  # Petit délai entre chaque jour

                except Exception as e:
                    logger.error(f"Erreur lors du scraping pour {target_date}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Erreur lors du scraping: {str(e)}")
            self.take_error_screenshot("scraping_error")
        finally:
            self.cleanup()