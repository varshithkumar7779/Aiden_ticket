import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Home.css';

// Base URL for API calls
const API_BASE_URL = 'http://localhost:8000';

function Home() {
  const [tickets, setTickets] = useState([]);
  const [employers, setEmployers] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newTicket, setNewTicket] = useState({
    user_id: '',
    title: '',
    description: ''
  });
  const [selectedTicket, setSelectedTicket] = useState(null);

  // Fetch tickets and employers on component mount
  useEffect(() => {
    fetchTickets();
    fetchEmployers();
  }, []);

  const fetchTickets = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/tickets`);
      setTickets(response.data);
    } catch (error) {
      console.error('Error fetching tickets:', error);
    }
  };

  const fetchEmployers = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/employers`);
      setEmployers(response.data);
    } catch (error) {
      console.error('Error fetching employers:', error);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API_BASE_URL}/tickets-with-triage`, newTicket);
      setTickets([...tickets, response.data.ticket]);
      setNewTicket({ user_id: '', title: '', description: '' });
      setShowCreateForm(false);
      alert('Ticket created and triaged successfully!');
    } catch (error) {
      console.error('Error creating ticket:', error);
      alert('Error creating ticket. Please try again.');
    }
  };

  const handleTriageTicket = async (ticketId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/tickets/${ticketId}/triage`);
      // Update the ticket in the list
      setTickets(tickets.map(ticket => 
        ticket.id === ticketId ? { ...ticket, ...response.data } : ticket
      ));
      alert('Ticket triaged successfully!');
    } catch (error) {
      console.error('Error triaging ticket:', error);
      alert('Error triaging ticket. Please try again.');
    }
  };

  const getPriorityBadgeClass = (priority) => {
    switch (priority) {
      case 'P0': return 'badge urgent';
      case 'P1': return 'badge high';
      case 'P2': return 'badge medium';
      case 'P3': return 'badge low';
      default: return 'badge unknown';
    }
  };

  const getEmployerName = (employerId) => {
    const employer = employers.find(emp => emp.id === employerId);
    return employer ? employer.name : 'Unassigned';
  };

  return (
    <div className="App">
      <header className="App-headers">
        <h1>Helpdesk Ticket System</h1>
        <p>AI-powered ticket triaging and assignment</p>
      </header>

      <div className="container">
        <div className="action-bar">
          <button 
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? 'Cancel' : 'Create New Ticket'}
          </button>
        </div>

        {showCreateForm && (
          <div className="create-form">
            <h2>Create New Ticket</h2>
            <form onSubmit={handleCreateTicket}>
              <div className="form-group">
                <label>User ID:</label>
                <input
                  type="text"
                  value={newTicket.user_id}
                  onChange={(e) => setNewTicket({...newTicket, user_id: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Title:</label>
                <input
                  type="text"
                  value={newTicket.title}
                  onChange={(e) => setNewTicket({...newTicket, title: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description:</label>
                <textarea
                  value={newTicket.description}
                  onChange={(e) => setNewTicket({...newTicket, description: e.target.value})}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Submit Ticket</button>
            </form>
          </div>
        )}

        <div className="tickets-section">
          <h2>Tickets</h2>
          {tickets.length === 0 ? (
            <p>No tickets found. Create one to get started.</p>
          ) : (
            <div className="tickets-grid">
              {tickets.map(ticket => (
                <div key={ticket.id} className="ticket-card">
                  <div className="ticket-header">
                    <h3>{ticket.title}</h3>
                    <span className={getPriorityBadgeClass(ticket.priority)}>
                      {ticket.priority || 'Not Triaged'}
                    </span>
                  </div>
                  <div className="ticket-body">
                    <p><strong>User:</strong> {ticket.user_id}</p>
                    <p><strong>Description:</strong> {ticket.description}</p>
                    <p><strong>Status:</strong> {ticket.status}</p>
                    {ticket.priority_score && (
                      <p><strong>Priority Score:</strong> {ticket.priority_score.toFixed(1)}/100</p>
                    )}
                    {ticket.assignee && (
                      <p><strong>Assignee:</strong> {getEmployerName(ticket.assignee)}</p>
                    )}
                    {ticket.first_reply && (
                      <div className="first-reply">
                        <strong>First Reply:</strong>
                        <p>{ticket.first_reply}</p>
                      </div>
                    )}
                    <p><strong>Created:</strong> {new Date(ticket.created_at).toLocaleString()}</p>
                  </div>
                  <div className="ticket-actions">
                    {!ticket.priority && (
                      <button 
                        className="btn btn-secondary"
                        onClick={() => handleTriageTicket(ticket.id)}
                      >
                        Run Triage
                      </button>
                    )}
                    <button 
                      className="btn btn-info"
                      onClick={() => setSelectedTicket(ticket)}
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedTicket && (
          <div className="modal">
            <div className="modal-content">
              <span className="close" onClick={() => setSelectedTicket(null)}>&times;</span>
              <h2>Ticket Details</h2>
              <div className="ticket-details">
                <p><strong>ID:</strong> {selectedTicket.id}</p>
                <p><strong>Title:</strong> {selectedTicket.title}</p>
                <p><strong>User ID:</strong> {selectedTicket.user_id}</p>
                <p><strong>Description:</strong> {selectedTicket.description}</p>
                <p><strong>Status:</strong> {selectedTicket.status}</p>
                <p><strong>Priority:</strong> {selectedTicket.priority || 'Not set'}</p>
                {selectedTicket.priority_score && (
                  <p><strong>Priority Score:</strong> {selectedTicket.priority_score.toFixed(1)}/100</p>
                )}
                {selectedTicket.rationale && (
                  <p><strong>Rationale:</strong> {selectedTicket.rationale}</p>
                )}
                {selectedTicket.assignee && (
                  <p><strong>Assignee:</strong> {getEmployerName(selectedTicket.assignee)}</p>
                )}
                {selectedTicket.assignee_reason && (
                  <p><strong>Assignee Reason:</strong> {selectedTicket.assignee_reason}</p>
                )}
                {selectedTicket.first_reply && (
                  <div>
                    <strong>First Reply:</strong>
                    <p>{selectedTicket.first_reply}</p>
                  </div>
                )}
                <p><strong>Created:</strong> {new Date(selectedTicket.created_at).toLocaleString()}</p>
                <p><strong>Updated:</strong> {new Date(selectedTicket.updated_at).toLocaleString()}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;