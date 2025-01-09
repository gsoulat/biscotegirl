from datetime import datetime, timedelta
import time
from typing import List, Dict, Tuple, Optional
import tenacity
from loguru import logger
from playwright.sync_api import sync_playwright, TimeoutError
from app.config.config import Config
from app.services.database import Database
from app.services.discord_notifier import DiscordNotifier


class PlanningChecker:
    def __init__(self, logger, headless: bool = False):
        self.browser = None
        self.context = None
        self.page = None
        self.logger = logger
        self.headless = headless
        self.discord_notifier = DiscordNotifier(logger)
        self.db = Database(Config.DATABASE_PATH)
        self.error_count = 0
        self.max_consecutive_errors = 2
        self.last_error_notified = None

    def reset_error_count(self):
        """Réinitialise le compteur d'erreurs"""
        if self.error_count > 0:
            self.logger.info("✅ Réinitialisation du compteur d'erreurs")
            # Si on avait des erreurs et qu'on revient à la normale, on notifie
            if self.last_error_notified and Config.DISCORD_ENABLED:
                self.discord_notifier.send_notification_recovery()
        self.error_count = 0
        self.last_error_notified = None

    def handle_error(self, error: Exception) -> int:
        """Gère une erreur et retourne le délai avant la prochaine tentative"""
        self.error_count += 1
        self.logger.error(f"❌ Erreur #{self.error_count}: {str(error)}")

        retry_interval = (
            Config.ERROR_RETRY_INTERVAL
            if self.error_count >= self.max_consecutive_errors
            else Config.RETRY_INTERVAL
        )

        # Si c'est la première erreur ou si on passe en mode erreur, on notifie
        should_notify = (
                self.error_count == 1 or
                self.error_count == self.max_consecutive_errors
        )

        if should_notify and Config.DISCORD_ENABLED:
            # On évite de notifier deux fois la même erreur
            error_key = f"{type(error).__name__}:{str(error)}"
            if error_key != self.last_error_notified:
                self.discord_notifier.send_error_notification(
                    str(error),
                    self.error_count,
                    retry_interval
                )
                self.last_error_notified = error_key

        # Log spécial si on passe en mode erreur
        if self.error_count >= self.max_consecutive_errors:
            self.logger.warning(
                f"⚠️ {self.error_count} erreurs consécutives détectées. "
                f"Passage en mode récupération ({retry_interval}s)"
            )

        return retry_interval


    def should_check_planning(self) -> bool:
        """Vérifie si le planning doit être vérifié aujourd'hui"""
        now = datetime.now()
        # Vérifier si on est dans la plage horaire
        if not (Config.CHECK_START_TIME <= now.time() <= Config.CHECK_END_TIME):
            logger.info(f"⏰ Hors horaires ({Config.CHECK_START_TIME} - {Config.CHECK_END_TIME})")
            return False

        # Vérifier si le planning a déjà été vérifié aujourd'hui
        is_checked = self.db.get_today_check_status()
        if is_checked:
            logger.info("✅ Planning déjà vérifié aujourd'hui")
            # Calculer le temps restant jusqu'à demain 7h
            tomorrow = now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)
            wait_time = (tomorrow - now).total_seconds()
            logger.info(f"⏰ Reprise des vérifications demain à 7h (dans {wait_time / 3600:.1f} heures)")
            time.sleep(wait_time)
            return False

        return True

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(Config.RETRY_ATTEMPTS),
        wait=tenacity.wait_fixed(Config.RETRY_DELAY),
        retry=tenacity.retry_if_exception_type((TimeoutError, ConnectionError)),
        before_sleep=lambda retry_state: logger.info(
            f"Tentative {retry_state.attempt_number}/{Config.RETRY_ATTEMPTS}..."
        ),
    )
    def initialize_browser(self) -> None:
        try:
            logger.info("Démarrage de Playwright...")
            playwright = sync_playwright().start()

            logger.info(f"Lancement du navigateur (mode headless: {self.headless})")
            self.browser = playwright.chromium.launch(
                headless=self.headless,
                args=["--start-maximized", "--window-size=1920,1080"],
                slow_mo=50,
            )

            # Configuration de la locale en français
            self.context = self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="fr-FR",  # Force la locale en français
                timezone_id="Europe/Paris",  # Force le fuseau horaire
            )

            self.page = self.context.new_page()
            self.page.set_default_timeout(Config.PAGE_TIMEOUT)

            # Configuration des dialogues dès l'initialisation
            self.page.on("dialog", lambda dialog: self._handle_dialog(dialog))

            logger.info("Navigateur initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du navigateur: {str(e)}")
            raise

    def login(self, url: str, username: str, password: str) -> bool:
        """Se connecte au site avec gestion des erreurs"""
        try:
            logger.info(f"Accès à la page de connexion: {url}")
            self.page.goto(url)

            logger.info("Attente de chargement de la page...")
            self.page.wait_for_load_state("networkidle")

            logger.info("Recherche du champ email...")

            # Attente et remplissage des champs
            # Attente et remplissage du champ email
            email_input = self.page.wait_for_selector(
                Config.SELECTORS["email_input"],
                state="visible",
                timeout=Config.PAGE_TIMEOUT,
            )
            logger.info("Champ email trouvé, remplissage...")
            email_input.fill(username)

            logger.info("Recherche du champ mot de passe...")
            password_input = self.page.wait_for_selector(
                Config.SELECTORS["password_input"],
                state="visible",
                timeout=Config.PAGE_TIMEOUT,
            )
            logger.info("Champ mot de passe trouvé, remplissage...")
            password_input.fill(password)

            logger.info("clique sur le bouton login")
            # self.page.wait_for_timeout(1000)
            self.page.click(Config.SELECTORS["login_button"])
            self.page.click(Config.SELECTORS["ok_button"])
            logger.info("Connexion réussie")
            return True

        except TimeoutError as e:
            logger.error(f"Timeout lors de la connexion: {str(e)}")
            self.take_error_screenshot()
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la connexion: {str(e)}")
            self.take_error_screenshot()
            raise

    def navigate_to_page(self, url: str) -> bool:
        """Navigue vers une page donnée"""
        try:
            logger.info(f"Navigation vers : {url}")
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle")
            logger.info("Chargement de la page terminé")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la navigation : {str(e)}")
            self.take_error_screenshot("navigation_error")
            return False

    def select_month(self, target_date: datetime) -> None:
        try:
            self.page.click(Config.SELECTORS["month_picker"])
            target_month_fr = (
                f"{Config.MONTHS_FR[target_date.month]} {target_date.year}"
            )
            logger.info(f"Sélection du mois {target_month_fr}")

            self.page.click(Config.SELECTORS["month_option"].format(target_month_fr))
            self.page.click(Config.SELECTORS["ok_button_date"])
            self.page.wait_for_timeout(1000)
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du mois: {str(e)}")
            self.take_error_screenshot("month_selection_error")
            raise

    def select_date(self, target_date: datetime) -> bool:
        try:
            weekday_fr = Config.WEEKDAYS_FR[target_date.weekday()]
            logger.debug(f"Recherche du jour {target_date.day} ({weekday_fr})")

            self.page.wait_for_load_state("networkidle")

            date_xpath = f"//div[contains(@class, 'booking_x_day')][.//div[contains(@class, 'weekday') and contains(text(), '{weekday_fr}')]][.//div[contains(@class, 'val') and text()='{target_date.day}']]"

            if date_element := self.page.wait_for_selector(
                date_xpath, state="visible", timeout=5000
            ):
                date_element.click()
                logger.info(f"✅ Jour {target_date.day} sélectionné")
                self.page.wait_for_timeout(1000)
                return True

            logger.error(f"❌ Jour {target_date.day} non trouvé")
            return False

        except Exception as e:
            logger.error(f"❌ Erreur sélection de date: {str(e)}")
            self.take_error_screenshot("date_selection_error")
            return False

    def check_activities(self) -> Tuple[bool, List[Dict]]:
        try:
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_selector(
                "ion-list.htz_booking_list", state="visible", timeout=5000
            )

            planning_items = self.page.query_selector_all("ion-item.pl-evt")
            if not planning_items:
                logger.info("🔒 Planning non disponible")
                return False, []

            logger.info(
                f"🎯 Planning ouvert! ({len(planning_items)} activités trouvées)"
            )
            activities = []

            for item in planning_items:
                try:
                    activity = self._extract_activity_info(item)
                    if activity:
                        activities.append(activity)
                        self._log_activity(activity)
                except Exception as e:
                    logger.warning(f"❗ Erreur extraction activité: {str(e)}")
                    continue

            if activities:
                self._log_activities_stats(activities)

            return bool(activities), activities

        except Exception as e:
            logger.error(f"❌ Erreur vérification activités: {str(e)}")
            self.take_error_screenshot("activities_error")
            return False, []

    def _log_activity(self, activity: Dict) -> None:
        status = []
        if activity["is_booked"]:
            status.append("🎟️ [Réservé]")
        if activity["is_full"]:
            status.append("⛔ [Complet]")
        logger.info(
            f"    • {activity['start_time']} - {activity['activity']} "
            f"({activity['capacity']}) @ {activity['room']} {' '.join(status)}"
        )

    def _log_activities_stats(self, activities: List[Dict]) -> None:
        booked = sum(1 for a in activities if a["is_booked"])
        full = sum(1 for a in activities if a["is_full"])
        available = len(activities) - full
        logger.info(f"✅ Total: {len(activities)} activité(s)")
        logger.info(
            f"📊 Stats: {booked} réservé(s), {full} complet(s), {available} disponible(s)"
        )

    def _extract_activity_info(self, item) -> Optional[Dict]:
        start_time = item.query_selector(".pl-evt-start").inner_text()
        activity = item.query_selector(".pl-evt-label").inner_text()
        capacity = item.query_selector(".pl-evt-capacity").inner_text().strip()
        room = (
            item.query_selector(".pl-evt-room")
            .inner_text()
            .strip()
            .replace("@", "")
            .strip()
        )

        return {
            "start_time": start_time,
            "activity": activity,
            "capacity": capacity,
            "room": room,
            "is_full": "is-full"
            in (item.query_selector(".pl-evt-capacity").get_attribute("class") or ""),
            "is_booked": bool(item.query_selector(".pl-evt-status.booked")),
        }

    def _handle_dialog(self, dialog) -> None:
        try:
            message = dialog.message.lower()
            logger.info(f"Dialog: {message}")
            dialog.accept()
        except Exception as e:
            logger.error(f"Erreur dialog: {str(e)}")
            dialog.accept()

    def take_error_screenshot(self, prefix: str = "error") -> Optional[str]:
        try:
            if not self.page:
                return None

            path = (
                Config.LOGS_DIR
                / f"{prefix}_screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
            )
            self.page.screenshot(path=str(path))
            logger.info(f"Screenshot: {path}")
            return str(path)
        except Exception as e:
            logger.error(f"Erreur screenshot: {str(e)}")
            return None

    def cleanup(self) -> None:
        try:
            if hasattr(self, "page") and self.page:
                self.page.close()
            if hasattr(self, "context") and self.context:
                self.context.close()
            if hasattr(self, "browser") and self.browser:
                self.browser.close()
            logger.info("✨ Nettoyage terminé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {str(e)}")

    def periodic_check(self) -> None:
        while True:
            try:
                if not self.should_check_planning():
                    continue

                self.initialize_browser()
                if not self.login(Config.LOGIN_URL, Config.EMAIL, Config.PASSWORD):
                    wait_time = self.handle_error(Exception("Échec de connexion"))
                    time.sleep(wait_time)
                    continue

                self.navigate_to_page(Config.PLANNING_URL)
                target_date = datetime.now() + timedelta(days=Config.TARGET_DAY_OFFSET)
                logger.info(f"📅 Vérification pour le {target_date.strftime('%d/%m/%Y')}")

                try:
                    self.select_month(target_date)
                    if not self.select_date(target_date):
                        wait_time = self.handle_error(Exception("Impossible de sélectionner la date"))
                        time.sleep(wait_time)
                        continue
                except Exception as e:
                    wait_time = self.handle_error(e)
                    time.sleep(wait_time)
                    continue

                has_activities, activities = self.check_activities()
                if has_activities:
                    # Réinitialiser le compteur d'erreurs car tout s'est bien passé
                    self.reset_error_count()
                    # Marquer le planning comme vérifié
                    self.db.set_planning_checked()
                    if Config.DISCORD_ENABLED:
                        self.discord_notifier.send_notification(target_date, activities)
                else:
                    retry_interval = Config.RETRY_INTERVAL
                    logger.info(f"🔄 Nouvelle vérification dans {retry_interval} secondes")
                    time.sleep(retry_interval)

            except Exception as e:
                wait_time = self.handle_error(e)
                self.take_error_screenshot("periodic_check_error")
                time.sleep(wait_time)
            finally:
                self.cleanup()
