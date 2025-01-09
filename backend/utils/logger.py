from pathlib import Path
from loguru import logger
import sys


def setup_logger(name: str = "FitnessBot", debug: bool = False) -> logger:
    """Configure et retourne un logger"""
    # Création du dossier logs s'il n'existe pas
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Suppression des handlers par défaut
    logger.remove()

    # Ajout du handler pour la console
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Niveau de log basé sur le mode debug
    log_level = "DEBUG" if debug else "INFO"

    # Handler console
    logger.add(sys.stdout, format=log_format, level=log_level, colorize=True)

    # Handler fichier
    logger.add(
        "logs/fitness_bot.log",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        format=log_format,
        level=log_level,
        encoding="utf-8",
    )

    return logger.bind(name=name)
