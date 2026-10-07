import { API_BASE_URL } from '../config/api';

const API_URL = `${API_BASE_URL}/api`;

function getHeaders() {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  };
}

export interface DatabaseConfig {
  db_name?: string;
  name?: string;
  db_type: 'postgresql' | 'mysql' | 'sqlite' | 'mongodb' | string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  database?: string;
  connection_string?: string;
  description?: string;
}

export const databaseConnectionsAPI = {

  // Get all connections for the user
  async listConnections() {
    const response = await fetch(`${API_URL}/connections/list`, {
      headers: getHeaders()
    });
    return response.json();
  },

  // Get a specific connection
  async getConnection(connectionId: string | number) {
    const response = await fetch(`${API_URL}/connections/${connectionId}`, {
      headers: getHeaders()
    });
    return response.json();
  },

  // Get tables for a connection
  async getTables(connectionId: string | number) {
    const response = await fetch(`${API_URL}/connections/${connectionId}/tables`, {
      method: 'POST',
      headers: getHeaders()
    });
    return response.json();
  },

  // Delete a connection
  async deleteConnection(connectionId: string | number) {
    const response = await fetch(`${API_URL}/connections/${connectionId}`, {
      method: 'DELETE',
      headers: getHeaders()
    });
    return response.json();
  },

  // Retest a connection
  async retestConnection(connectionId: string | number) {
    const response = await fetch(`${API_URL}/connections/${connectionId}/retest`, {
      method: 'POST',
      headers: getHeaders()
    });
    return response.json();
  }
};

export default databaseConnectionsAPI;
