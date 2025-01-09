import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';

// Création d'une instance Axios avec la configuration de base
const api = axios.create({
  baseURL: 'http://localhost:8000'  // URL de votre backend
});

const ReservationInterface = () => {
  const [users, setUsers] = useState([]);
  const [planning, setPlanning] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedActivity, setSelectedActivity] = useState('');
  const [message, setMessage] = useState(null);

  useEffect(() => {
    // Fonction pour charger les données
    const fetchData = async () => {
      try {
        // Chargement parallèle des utilisateurs et du planning
        const [usersResponse, planningResponse] = await Promise.all([
          api.get('/api/users'),
          api.get('/api/planning')
        ]);

        setUsers(usersResponse.data);
        setPlanning(planningResponse.data);
      } catch (error) {
        console.error('Erreur lors du chargement des données:', error);
        setMessage({
          type: 'error',
          text: 'Erreur lors du chargement des données: ' + error.response?.data?.detail || error.message
        });
      }
    };

    fetchData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedUser || !selectedActivity) {
      setMessage({
        type: 'error',
        text: 'Veuillez sélectionner un utilisateur et une activité'
      });
      return;
    }

    try {
      const response = await api.post('/api/reservations', {
        user_id: selectedUser,
        planning_id: selectedActivity
      });

      setMessage({
        type: 'success',
        text: 'Réservation ajoutée avec succès !'
      });

      // Reset des sélections
      setSelectedUser('');
      setSelectedActivity('');

    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Erreur lors de la réservation: ' +
          (error.response?.data?.detail || error.message)
      });
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto mt-8">
      <CardHeader>
        <CardTitle>Nouvelle réservation</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Sélection de l'utilisateur */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Utilisateur
            </label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="">Sélectionner un utilisateur</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.pseudo}
                </option>
              ))}
            </select>
          </div>

          {/* Sélection de l'activité */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Activité
            </label>
            <select
              value={selectedActivity}
              onChange={(e) => setSelectedActivity(e.target.value)}
              className="w-full p-2 border rounded-md"
            >
              <option value="">Sélectionner une activité</option>
              {planning.map(activity => (
                <option key={activity.id} value={activity.id}>
                  {activity.weekday} - {activity.start_time} - {activity.activity} ({activity.room})
                </option>
              ))}
            </select>
          </div>

          {/* Message de confirmation/erreur */}
          {message && (
            <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
              <AlertDescription>
                {message.text}
              </AlertDescription>
            </Alert>
          )}

          {/* Bouton de soumission */}
          <button
            type="submit"
            className="w-full bg-blue-500 text-white p-2 rounded-md hover:bg-blue-600 transition-colors"
          >
            Ajouter la réservation
          </button>
        </form>
      </CardContent>
    </Card>
  );
};

export default ReservationInterface;