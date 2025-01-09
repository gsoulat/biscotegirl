from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from backend.services.database import Database

app = FastAPI()
db = Database()

class ReservationCreate(BaseModel):
    user_id: int
    planning_id: int

@app.get("/api/users")
async def get_users():
    """Récupère la liste des utilisateurs"""
    return db.get_users()

@app.get("/api/planning")
async def get_planning():
    """Récupère la liste des activités disponibles"""
    return db.get_planning()

@app.post("/api/reservations")
async def create_reservation(reservation: ReservationCreate):
    """Crée une nouvelle réservation"""
    success = db.add_reservation(reservation.user_id, reservation.planning_id)
    if not success:
        raise HTTPException(status_code=400, detail="Erreur lors de la création de la réservation")
    return {"status": "success"}