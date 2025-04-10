# backend/services/database.py
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from loguru import logger


class Database:
    def __init__(self, db_path: str = "database.sqlite"):
        self.db_path = Path(db_path)
        self.initialize_db()

    def execute(self, query: str, params: tuple = ()) -> None:
        """Exécute une requête SQL"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête SQL : {str(e)}")
            raise

    def initialize_db(self):
        """Initialise la base de données et crée les tables si elles n'existent pas"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Tables existantes
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS checking_days (
                        date TEXT PRIMARY KEY,
                        is_planning BOOLEAN NOT NULL DEFAULT 0
                    )
                """)

                # Création de la table users selon la nouvelle structure
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL,
                        discord_name TEXT NOT NULL
                    )
                """)

                # Création de la table planning
                cursor.execute("""
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

                # Création de la table reservations selon la nouvelle structure
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        day TEXT NOT NULL,
                        activity TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        UNIQUE(user_id, day, activity)
                    )
                """)

                conn.commit()
                logger.info("Base de données initialisée avec succès")
        except Exception as e:
            logger.error(
                f"Erreur lors de l'initialisation de la base de données: {str(e)}"
            )
            raise

    def get_users(self) -> List[Dict]:
        """Récupère tous les utilisateurs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, email, discord_name FROM users")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            return []

    def get_planning(self) -> List[Dict]:
        """Récupère toutes les activités du planning"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, weekday, start_time, activity, room, capacity, is_full
                    FROM planning 
                    ORDER BY weekday, start_time
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du planning: {str(e)}")
            return []

    def add_reservation(self, user_id: int, day: str, activity: str) -> bool:
        """Ajoute une réservation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO reservations (user_id, day, activity)
                    VALUES (?, ?, ?)
                """,
                    (user_id, day, activity),
                )
                conn.commit()
                logger.info(
                    f"Réservation ajoutée pour user_id={user_id}, day={day}, activity={activity}"
                )
                return True
        except sqlite3.IntegrityError:
            logger.error(
                f"Cette réservation existe déjà (user_id={user_id}, day={day}, activity={activity})"
            )
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la réservation: {str(e)}")
            return False

    def get_reservations(self, day: str) -> List[Dict]:
        """Récupère les réservations pour un jour donné"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT r.day, r.activity, u.email, u.password, u.discord_name, u.id as user_id
                    FROM reservations r
                    JOIN users u ON r.user_id = u.id
                    WHERE r.day = ?
                """,
                    (day,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des réservations: {str(e)}")
            return []

    def add_user(self, email: str, password: str, discord_name: str) -> int:
        """Ajoute un utilisateur et retourne son ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO users (email, password, discord_name) VALUES (?, ?, ?)",
                        (email, password, discord_name),
                    )
                    user_id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"Utilisateur ajouté avec l'ID: {user_id}")
                    return user_id
                except sqlite3.IntegrityError:
                    logger.info("L'utilisateur existe déjà. Récupération de l'ID...")
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        raise Exception("Impossible de trouver l'utilisateur")
        except Exception as e:
            logger.error(
                f"Erreur lors de l'ajout/récupération de l'utilisateur: {str(e)}"
            )
            raise

    def get_today_check_status(self) -> bool:
        """Récupère le statut de vérification pour aujourd'hui"""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT is_planning FROM checking_days WHERE date = ? AND is_planning = 1",
                    (today,),
                )
                result = cursor.fetchone()

                if not result:
                    # Si pas d'entrée pour aujourd'hui ou is_planning = 0, on crée/met à jour l'entrée
                    cursor.execute(
                        """
                        INSERT INTO checking_days (date, is_planning) 
                        VALUES (?, ?) 
                        ON CONFLICT(date) DO UPDATE SET is_planning = ?
                        """,
                        (today, False, False),
                    )
                    conn.commit()
                    return False

                return bool(result[0])
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
            return False

    def get_today_planning_status(self) -> bool:
        """Récupère le status du planning pour aujourd'hui"""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT is_planning FROM checking_days WHERE date = ?", (today,)
                )
                result = cursor.fetchone()

                if not result:
                    cursor.execute(
                        "INSERT INTO checking_days (date, is_planning) VALUES (?, ?)",
                        (today, False),
                    )
                    conn.commit()
                    return False

            return bool(result[0])
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
            return False

    def set_planning_checked(self) -> None:
        """Marque le planning comme vérifié pour aujourd'hui"""
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO checking_days (date, is_planning) 
                    VALUES (?, ?) 
                    ON CONFLICT(date) DO UPDATE SET is_planning = ?
                    """,
                    (today, True, True),
                )
                conn.commit()
                logger.info("Status de vérification mis à jour")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
