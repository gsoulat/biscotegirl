from datetime import datetime, timedelta
import asyncio
import time
from typing import List, Dict, Tuple, Optional
import tenacity
from loguru import logger
from playwright.async_api import Playwright, async_playwright, TimeoutError
from backend.config.config import Config 
from backend.services.database import Database
from backend.services.discord_notifier import DiscordNotifier
from tqdm import tqdm


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
        self._playwright = None

    def reset_error_count(self):
        """Réinitialise le compteur d'erreurs"""
        if self.error_count > 0:
            self.logger.info("✅ Réinitialisation du compteur d'erreurs")
            if self.last_error_notified and Config.DISCORD_ENABLED:
                asyncio.create_task(self.discord_notifier.send_notification_recovery())
        self.error_count = 0
        self.last_error_notified = None

    async def handle_error(self, error: Exception) -> int:
        """Gère une erreur et retourne le délai avant la prochaine tentative"""
        self.error_count += 1
        self.logger.error(f"❌ Erreur #{self.error_count}: {str(error)}")

        retry_interval = (
            Config.ERROR_RETRY_INTERVAL
            if self.error_count >= self.max_consecutive_errors
            else Config.RETRY_INTERVAL
        )

        should_notify = (
                self.error_count == 1 or
                self.error_count == self.max_consecutive_errors
        )

        if should_notify and Config.DISCORD_ENABLED:
            error_key = f"{type(error).__name__}:{str(error)}"
            if error_key != self.last_error_notified:
                await self.discord_notifier.send_error_notification(
                    str(error),
                    self.error_count,
                    retry_interval
                )
                self.last_error_notified = error_key

        if self.error_count >= self.max_consecutive_errors:
            self.logger.warning(
                f"⚠️ {self.error_count} erreurs consécutives détectées. "
                f"Passage en mode récupération ({retry_interval}s)"
            )
            for _ in tqdm(range(retry_interval),
                         desc="⏳ Temps restant",
                         bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}s',
                         ncols=75):
                await asyncio.sleep(1)
        else:
            for _ in tqdm(range(retry_interval),
                         desc="⏳ Attente",
                         bar_format='{desc}: {n_fmt}/{total_fmt}s',
                         ncols=50):
                await asyncio.sleep(1)

        return retry_interval

    def should_check_planning(self) -> bool:
        """Vérifie si le planning doit être vérifié aujourd'hui"""
        now = datetime.now()
        is_checked = self.db.get_today_check_status()
        if is_checked:
            logger.info("✅ Planning déjà vérifié aujourd'hui")
            tomorrow = now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)
            wait_time = (tomorrow - now).total_seconds()
            logger.info(f"⏰ Reprise des vérifications demain à 7h (dans {wait_time / 3600:.1f} heures)")
            return False
        return True

    async def initialize_browser(self) -> None:
        """Initialize the browser with async Playwright"""
        try:
            logger.info("Démarrage de Playwright...")
            self._playwright = await async_playwright().start()

            logger.info(f"Lancement du navigateur (mode headless: {self.headless})")
            self.browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--start-maximized", "--window-size=1920,1080"],
                slow_mo=50,
            )

            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="fr-FR",
                timezone_id="Europe/Paris",
            )

            self.page = await self.context.new_page()
            self.page.set_default_timeout(Config.PAGE_TIMEOUT)
            self.page.on("dialog", lambda dialog: asyncio.create_task(self._handle_dialog(dialog)))

            logger.info("Navigateur initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du navigateur: {str(e)}")
            raise

    async def login(self, url: str, username: str, password: str) -> bool:
        """Se connecte au site avec gestion des erreurs"""
        try:
            logger.info(f"Accès à la page de connexion: {url}")
            await self.page.goto(url)

            logger.info("Attente de chargement de la page...")
            await self.page.wait_for_load_state("networkidle")

            logger.info("Recherche du champ email...")
            email_input = await self.page.wait_for_selector(
                Config.SELECTORS["email_input"],
                state="visible",
                timeout=Config.PAGE_TIMEOUT,
            )
            logger.info("Champ email trouvé, remplissage...")
            await email_input.fill(username)

            logger.info("Recherche du champ mot de passe...")
            password_input = await self.page.wait_for_selector(
                Config.SELECTORS["password_input"],
                state="visible",
                timeout=Config.PAGE_TIMEOUT,
            )
            logger.info("Champ mot de passe trouvé, remplissage...")
            await password_input.fill(password)

            logger.info("clique sur le bouton login")
            await self.page.click(Config.SELECTORS["login_button"])
            await self.page.click(Config.SELECTORS["ok_button"])
            logger.info("Connexion réussie")
            return True

        except TimeoutError as e:
            logger.error(f"Timeout lors de la connexion: {str(e)}")
            await self.take_error_screenshot()
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la connexion: {str(e)}")
            await self.take_error_screenshot()
            raise

    async def navigate_to_page(self, url: str) -> bool:
        """Navigue vers une page donnée"""
        try:
            logger.info(f"Navigation vers : {url}")
            await self.page.goto(url)
            await self.page.wait_for_load_state("networkidle")
            logger.info("Chargement de la page terminé")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la navigation : {str(e)}")
            await self.take_error_screenshot("navigation_error")
            return False

    async def select_month(self, target_date: datetime) -> None:
        """Sélectionne le mois dans le calendrier"""
        try:
            await self.page.click(Config.SELECTORS["month_picker"])
            target_month_fr = (
                f"{Config.MONTHS_FR[target_date.month]} {target_date.year}"
            )
            logger.info(f"Sélection du mois {target_month_fr}")

            await self.page.click(Config.SELECTORS["month_option"].format(target_month_fr))
            await self.page.click(Config.SELECTORS["ok_button_date"])
            await self.page.wait_for_timeout(1000)
        except Exception as e:
            logger.error(f"Erreur lors de la sélection du mois: {str(e)}")
            await self.take_error_screenshot("month_selection_error")
            raise

    async def select_date(self, target_date: datetime) -> bool:
        """Sélectionne la date dans le calendrier"""
        try:
            weekday_fr = Config.WEEKDAYS_FR[target_date.weekday()]
            logger.debug(f"Recherche du jour {target_date.day} ({weekday_fr})")

            await self.page.wait_for_load_state("networkidle")

            date_xpath = f"//div[contains(@class, 'booking_x_day')][.//div[contains(@class, 'weekday') and contains(text(), '{weekday_fr}')]][.//div[contains(@class, 'val') and text()='{target_date.day}']]"

            date_element = await self.page.wait_for_selector(
                date_xpath, state="visible", timeout=5000
            )
            if date_element:
                await date_element.click()
                logger.info(f"✅ Jour {target_date.day} sélectionné")
                await self.page.wait_for_timeout(1000)
                return True

            logger.error(f"❌ Jour {target_date.day} non trouvé")
            return False

        except Exception as e:
            logger.error(f"❌ Erreur sélection de date: {str(e)}")
            await self.take_error_screenshot("date_selection_error")
            return False

    async def check_activities(self) -> Tuple[bool, List[Dict]]:
        """Vérifie les activités disponibles"""
        try:
            await self.page.wait_for_load_state("networkidle")
            await self.page.wait_for_selector(
                "ion-list.htz_booking_list", state="visible", timeout=5000
            )

            planning_items = await self.page.query_selector_all("ion-item.pl-evt")
            if not planning_items:
                logger.info("🔒 Planning non disponible")
                return False, []

            logger.info(
                f"🎯 Planning ouvert! ({len(planning_items)} activités trouvées)"
            )
            activities = []
            current_date = datetime.now()

            for item in planning_items:
                try:
                    activity = await self._extract_activity_info(item)
                    if activity:
                        activity['weekday'] = self._convert_day_to_french(current_date)
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
            await self.take_error_screenshot("activities_error")
            return False, []

    async def _extract_activity_info(self, item) -> Optional[Dict]:
        """Extrait les informations d'une activité"""
        start_time = await item.query_selector(".pl-evt-start")
        start_time_text = await start_time.inner_text()

        activity = await item.query_selector(".pl-evt-label")
        activity_text = await activity.inner_text()

        capacity = await item.query_selector(".pl-evt-capacity")
        capacity_text = await capacity.inner_text()
        capacity_class = await capacity.get_attribute("class")

        room = await item.query_selector(".pl-evt-room")
        room_text = await room.inner_text()

        is_booked = await item.query_selector(".pl-evt-status.booked") is not None

        return {
            "start_time": start_time_text,
            "activity": activity_text,
            "capacity": capacity_text.strip(),
            "room": room_text.strip().replace("@", "").strip(),
            "is_full": "is-full" in (capacity_class or ""),
            "is_booked": is_booked,
        }

    async def _handle_dialog(self, dialog) -> None:
        """Gère les dialogues du navigateur"""
        try:
            message = dialog.message.lower()
            logger.info(f"Dialog: {message}")
            await dialog.accept()
        except Exception as e:
            logger.error(f"Erreur dialog: {str(e)}")
            await dialog.accept()

    async def take_error_screenshot(self, prefix: str = "error") -> Optional[str]:
        """Prend une capture d'écran en cas d'erreur"""
        try:
            if not self.page:
                return None

            path = (
                    Config.LOGS_DIR
                    / f"{prefix}_screenshot_{time.strftime('%Y%m%d-%H%M%S')}.png"
            )
            await self.page.screenshot(path=str(path))
            logger.info(f"Screenshot: {path}")
            return str(path)
        except Exception as e:
            logger.error(f"Erreur screenshot: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Nettoie les ressources du navigateur"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("✨ Nettoyage terminé")
        except Exception as e:
            logger.error(f"Erreur nettoyage: {str(e)}")

    @staticmethod
    def _convert_day_to_french(date_obj: datetime) -> str:
        """Convertit un jour en français"""
        weekday_map = {
            0: 'lundi',
            1: 'mardi',
            2: 'mercredi',
            3: 'jeudi',
            4: 'vendredi',
            5: 'samedi',
            6: 'dimanche'
        }

    def _log_activity(self, activity: Dict) -> None:
        """Log les détails d'une activité"""
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
        """Log les statistiques des activités"""
        booked = sum(1 for a in activities if a["is_booked"])
        full = sum(1 for a in activities if a["is_full"])
        available = len(activities) - full
        logger.info(f"✅ Total: {len(activities)} activité(s)")
        logger.info(
            f"📊 Stats: {booked} réservé(s), {full} complet(s), {available} disponible(s)"
        )

    async def periodic_check(self) -> None:
        """Vérifie périodiquement le planning"""
        while True:
            try:
                if not self.should_check_planning():
                    await asyncio.sleep(60)  # Attendre une minute avant de vérifier à nouveau
                    continue

                # Réinitialisation complète du navigateur à chaque itération
                await self.cleanup()
                self.browser = None
                self.context = None
                self.page = None

                # Initialiser une nouvelle instance du navigateur
                await self.initialize_browser()

                if not await self.login(Config.LOGIN_URL, Config.EMAIL, Config.PASSWORD):
                    wait_time = await self.handle_error(Exception("Échec de connexion"))
                    await asyncio.sleep(wait_time)
                    continue

                await self.navigate_to_page(Config.PLANNING_URL)
                target_date = datetime.now() + timedelta(days=Config.TARGET_DAY_OFFSET)
                logger.info(f"📅 Vérification pour le {target_date.strftime('%d/%m/%Y')}")

                try:
                    await self.select_month(target_date)
                    if not await self.select_date(target_date):
                        wait_time = await self.handle_error(Exception("Impossible de sélectionner la date"))
                        await asyncio.sleep(wait_time)
                        continue
                except Exception as e:
                    wait_time = await self.handle_error(e)
                    await asyncio.sleep(wait_time)
                    continue

                has_activities, activities = await self.check_activities()
                if has_activities:
                    self.reset_error_count()
                    self.db.set_planning_checked()
                    if Config.DISCORD_ENABLED:
                        await self.discord_notifier.send_notification(target_date, activities)
                else:
                    retry_interval = Config.RETRY_INTERVAL
                    logger.info(f"🔄 Nouvelle vérification dans {retry_interval} secondes")
                    for _ in tqdm(range(retry_interval),
                                  desc="⏳ Prochaine vérification",
                                  bar_format='{desc}: {n_fmt}/{total_fmt}s',
                                  ncols=50):
                        await asyncio.sleep(1)

            except Exception as e:
                wait_time = await self.handle_error(e)
                await self.take_error_screenshot("periodic_check_error")
                await asyncio.sleep(wait_time)
            finally:
                await self.cleanup()  # Toujours nettoyer à la fin