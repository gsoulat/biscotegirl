import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Alert, AlertDescription } from './ui/alert';

const api = axios.create({
  baseURL: 'http://localhost:8000'
});

const ReservationInterface = () => {
  const [users, setUsers] = useState([]);
  const [planning, setPlanning] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedDay, setSelectedDay] = useState('');
  const [selectedActivity, setSelectedActivity] = useState('');
  const [message, setMessage] = useState(null);

  // Log des données du planning
  useEffect(() => {
    console.log('Planning mis à jour:', planning);
  }, [planning]);

  // Calcul des jours uniques à partir du planning
  const uniqueDays = [...new Set(planning.map(item => item.weekday))].sort((a, b) => {
    const daysOrder = { 'lundi': 1, 'mardi': 2, 'mercredi': 3, 'jeudi': 4, 'vendredi': 5, 'samedi': 6, 'dimanche': 7 };
    return daysOrder[a] - daysOrder[b];
  });
  console.log('Jours uniques trouvés:', uniqueDays);

  // Filtrer les activités en fonction du jour sélectionné
  const filteredActivities = selectedDay
    ? planning.filter(activity => {
        console.log('Vérification activité:', {
          jour_activite: activity.weekday,
          jour_selectionne: selectedDay,
          correspond: activity.weekday === selectedDay
        });
        return activity.weekday === selectedDay;
      })
    : [];
  console.log('Activités filtrées pour', selectedDay, ':', filteredActivities);

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log('Début du chargement des données...');
        const [usersResponse, planningResponse] = await Promise.all([
          api.get('/api/users'),
          api.get('/api/planning')
        ]);

        console.log('Réponse users:', usersResponse.data);
        console.log('Réponse planning:', planningResponse.data);

        setUsers(usersResponse.data);
        setPlanning(planningResponse.data);
      } catch (error) {
        console.error('Erreur détaillée:', {
          message: error.message,
          response: error.response,
          status: error.response?.status
        });
        setMessage({
          type: 'error',
          text: 'Erreur lors du chargement des données: ' + error.response?.data?.detail || error.message
        });
      }
    };

    fetchData();
  }, []);

  // Log lors du changement de jour sélectionné
  useEffect(() => {
    console.log('Jour sélectionné changé:', selectedDay);
    setSelectedActivity('');
  }, [selectedDay]);

  // Log lors de la sélection d'une activité
  useEffect(() => {
    console.log('Activité sélectionnée:', selectedActivity);
  }, [selectedActivity]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log('Soumission du formulaire:', { selectedUser, selectedDay, selectedActivity });

    if (!selectedUser || !selectedActivity) {
      setMessage({
        type: 'error',
        text: 'Veuillez sélectionner un utilisateur et une activité'
      });
      return;
    }

    try {
      console.log('Envoi de la requête de réservation...');
      const response = await api.post('/api/reservations', {
        user_id: selectedUser,
        planning_id: selectedActivity
      });
      console.log('Réponse de la réservation:', response.data);

      setMessage({
        type: 'success',
        text: 'Réservation ajoutée avec succès !'
      });

      setSelectedUser('');
      setSelectedDay('');
      setSelectedActivity('');

    } catch (error) {
      console.error('Erreur lors de la réservation:', error);
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
              onChange={(e) => {
                console.log('Sélection utilisateur:', e.target.value);
                setSelectedUser(e.target.value);
              }}
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

          {/* Sélection du jour */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Jour
            </label>
            <select
              value={selectedDay}
              onChange={(e) => {
                console.log('Sélection jour:', e.target.value);
                setSelectedDay(e.target.value);
              }}
              className="w-full p-2 border rounded-md"
            >
              <option value="">Sélectionner un jour</option>
              {uniqueDays.map(day => (
                <option key={day} value={day}>
                  {day.charAt(0).toUpperCase() + day.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Sélection de l'activité */}
          {selectedDay && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Activité
              </label>
              <select
                value={selectedActivity}
                onChange={(e) => {
                  console.log('Sélection activité:', e.target.value);
                  setSelectedActivity(e.target.value);
                }}
                className="w-full p-2 border rounded-md"
              >
                <option value="">Sélectionner une activité</option>
                {filteredActivities.map(activity => (
                  <option key={activity.id} value={activity.id}>
                    {activity.start_time} - {activity.activity} ({activity.room})
                  </option>
                ))}
              </select>
            </div>
          )}

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