from datetime import datetime
from typing import List, Dict
import aiohttp
from loguru import logger
from backend.config.config import Config

class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_weather(self, city: str = "Valenciennes") -> Dict:
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={self.api_key}&q={city}&lang=fr"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    return {
                        "temperature": round(data["current"]["temp_c"]),
                        "description": data["current"]["condition"]["text"],
                        "humidity": data["current"]["humidity"],
                    }
        except Exception:
            return {
                "temperature": None,
                "description": "Non disponible",
                "humidity": None,
            }

class DiscordNotifier:
    def __init__(self, logger: logger):
        self.logger = logger
        self.webhook_url = Config.DISCORD_WEBHOOK_URL
        self.weather_service = WeatherService(Config.WHEATER_API)

    async def format_planning_message(
        self, target_date: datetime, activities: List[Dict]
    ) -> str:
        """Formate le message avec toutes les informations"""
        weather = await self.weather_service.get_weather(Config.WEATHER_CITY)

        message = [
            "🏋️ **PLANNING SPORT DISPONIBLE !** 🎉",
            f"\n📅 Planning ouvert pour le {target_date.strftime('%d/%m/%Y')}",
            f"\n🌤️ **Météo du jour à {Config.WEATHER_CITY}:**",
            f"• Température: {weather['temperature']}°C",
            f"• Conditions: {weather['description']}",
            f"• Humidité: {weather['humidity']}%",
            "\n📋 **Activités disponibles:**",
        ]

        sorted_activities = sorted(activities, key=lambda x: x["start_time"])

        for activity in sorted_activities:
            status = []
            if activity.get("is_booked"):
                status.append("🎟️ [Réservé]")
            if activity.get("is_full"):
                status.append("⛔ [Complet]")
            status_str = " ".join(status)

            message.append(
                f"• {activity['start_time']} - {activity['activity']} "
                f"({activity['capacity']}) @ {activity['room']} {status_str}"
            )

        available = sum(1 for a in activities if not a.get("is_full"))
        message.extend(
            [
                "\n📊 **Résumé:**",
                f"• {len(activities)} cours au total",
                f"• {available} cours disponibles",
                f"• {sum(1 for a in activities if a.get('is_full'))} cours complets",
                f"• {sum(1 for a in activities if a.get('is_booked'))} cours déjà réservés",
                "\n-------------------",
                "Réservez vite vos places ! 🎟️",
            ]
        )

        return "\n".join(message)

    async def send_error_notification(self, error_msg: str, error_count: int, next_retry: int) -> None:
        """Envoie une notification d'erreur à Discord"""
        try:
            self.logger.info("Préparation de la notification d'erreur Discord...")

            message = [
                "⚠️ **ATTENTION - PROBLÈME TECHNIQUE** ⚠️",
                "\n🔧 **Le système de vérification rencontre des difficultés:**",
                f"• Erreur #{error_count}: {error_msg}",
                f"• Prochaine tentative dans {next_retry} secondes",
                "\n⚡ Le système continue de fonctionner mais il est conseillé de:",
                "• Vérifier manuellement vos réservations sur le site",
                "• Ne pas vous fier uniquement aux notifications",
                "\n-------------------",
                "Le système vous tiendra informé dès qu'il sera rétabli 🛠️"
            ]

            payload = {
                "content": "\n".join(message),
                "username": "BiscoteGirl",
                "avatar_url": Config.BISCOTEGIRL_AVATAR_URL
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info("✅ Notification d'erreur Discord envoyée avec succès")
                    else:
                        self.logger.error(
                            f"❌ Erreur lors de l'envoi de la notification d'erreur ({response.status}): {await response.text()}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'envoi de la notification d'erreur: {str(e)}")
            self.logger.exception("Détails de l'erreur:")

    async def send_notification(self, target_date: datetime, activities: List[Dict]) -> None:
        """Envoie la notification enrichie à Discord"""
        try:
            self.logger.info("Préparation de la notification Discord...")
            message = await self.format_planning_message(target_date, activities)

            if not message:
                self.logger.error("Message formatté vide")
                return

            self.logger.debug(
                f"Message formatté : {message[:200]}..."
            )

            if not self.webhook_url:
                self.logger.error("URL du webhook Discord non configurée")
                return

            self.logger.debug(f"Utilisation du webhook: {self.webhook_url[:20]}...")

            payload = {
                "content": message,
                "username": "BiscoteGirl",
                "avatar_url": Config.BISCOTEGIRL_AVATAR_URL
            }

            self.logger.info("Envoi de la requête à Discord...")
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info("✅ Notification Discord envoyée avec succès")
                    else:
                        self.logger.error(
                            f"❌ Erreur lors de l'envoi ({response.status}): {await response.text()}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'envoi de la notification: {str(e)}")
            self.logger.exception("Détails de l'erreur:")

    async def send_notification_recovery(self) -> None:
        """Envoie une notification quand le système est rétabli"""
        try:
            self.logger.info("Préparation de la notification de récupération Discord...")

            message = [
                "✅ **SYSTÈME RÉTABLI** ✅",
                "\n🛠️ **Le système de vérification fonctionne à nouveau:**",
                "• Les erreurs ont été résolues",
                "• Les vérifications reprennent normalement",
                "\n-------------------",
                "Le système continue son travail normalement 🚀"
            ]

            payload = {
                "content": "\n".join(message),
                "username": "BiscoteGirl",
                "avatar_url": Config.BISCOTEGIRL_AVATAR_URL
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info("✅ Notification de récupération Discord envoyée avec succès")
                    else:
                        self.logger.error(
                            f"❌ Erreur lors de l'envoi de la notification de récupération ({response.status}): {await response.text()}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'envoi de la notification de récupération: {str(e)}")
            self.logger.exception("Détails de l'erreur:")