import sqlite3
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import List, Dict


class Database:
    def __init__(self, db_path: str = "database.sqlite"):
        self.db_path = Path(db_path)
        self.initialize_db()

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

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        id_discord TEXT NOT NULL UNIQUE,
                        pseudo TEXT NOT NULL,
                        login TEXT NOT NULL,
                        password TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

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

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reservations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        planning_id INTEGER NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (planning_id) REFERENCES planning(id),
                        UNIQUE(user_id, planning_id)
                    )
                """)
                conn.commit()
                logger.info("Base de données initialisée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
            raise

    def get_users(self) -> List[Dict]:
        """Récupère tous les utilisateurs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, pseudo FROM users ORDER BY pseudo")
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
                    SELECT id, weekday, start_time, activity, room
                    FROM planning 
                    WHERE is_full = FALSE
                    ORDER BY 
                        CASE weekday 
                            WHEN 'lundi' THEN 1
                            WHEN 'mardi' THEN 2
                            WHEN 'mercredi' THEN 3
                            WHEN 'jeudi' THEN 4
                            WHEN 'vendredi' THEN 5
                            WHEN 'samedi' THEN 6
                            WHEN 'dimanche' THEN 7
                        END,
                        start_time
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du planning: {str(e)}")
            return []

    def add_reservation(self, user_id: int, planning_id: int) -> bool:
        """Ajoute une réservation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reservations (user_id, planning_id)
                    VALUES (?, ?)
                """, (user_id, planning_id))
                conn.commit()
                logger.info(f"Réservation ajoutée pour user_id={user_id}, planning_id={planning_id}")
                return True
        except sqlite3.IntegrityError:
            logger.error("Cette réservation existe déjà")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la réservation: {str(e)}")
            return False