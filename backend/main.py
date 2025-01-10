import argparse
import asyncio
import time
from datetime import timedelta
from loguru import logger
from backend.services.planning_checker import PlanningChecker
from backend.services.scraping_service import ScrapingService


def parse_args():
    parser = argparse.ArgumentParser(description="Planning Checker pour HeitzFit")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Masquer le navigateur (mode headless)"
    )
    parser.add_argument(
        "--scraping",
        action="store_true",
        help="Mode scraping pour sauvegarder le planning dans la base de données"
    )
    return parser.parse_args()


def format_duration(seconds: float) -> str:
    """Formate la durée en format lisible"""
    duration = timedelta(seconds=seconds)
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    milliseconds = duration.microseconds // 1000

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    if milliseconds > 0:
        parts.append(f"{milliseconds}ms")

    return " ".join(parts)


async def async_main():
    start_time = time.time()
    args = parse_args()

    try:
        if args.scraping:
            logger.info("Mode scraping activé - Démarrage du scraping du planning...")
            scraper = ScrapingService(logger, headless=args.headless)
            await scraper.scrape_planning()
        else:
            logger.info("Mode normal - Démarrage de la vérification du planning...")
            checker = PlanningChecker(logger, headless=args.headless)
            await checker.periodic_check()

    except KeyboardInterrupt:
        logger.info("Arrêt manuel du programme")
    except Exception as e:
        logger.error(f"Erreur critique: {str(e)}")
    finally:
        execution_time = time.time() - start_time
        logger.info(f"Temps d'exécution total: {format_duration(execution_time)}")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()