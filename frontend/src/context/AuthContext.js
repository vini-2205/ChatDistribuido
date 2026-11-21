import React, { createContext, useState, useEffect, useCallback } from 'react';
import api, { ACCESS_KEY, REFRESH_KEY, setOnSessionExpired } from '../services/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem('user_data');
    setUser(null);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem(ACCESS_KEY);
    const userData = localStorage.getItem('user_data');
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setLoading(false);
  }, []);

  // Refresh token expirado ou inválido: encerra a sessão e avisa na tela de login
  useEffect(() => {
    setOnSessionExpired(() => {
      setSessionExpired(true);
      logout();
    });
  }, [logout]);

  const login = async (username, password) => {
    try {
      const { data } = await api.post('/auth/login/', { username, password });
      const userData = { id: data.id, username: data.username, nome: data.nome || data.username };

      localStorage.setItem(ACCESS_KEY, data.access);
      localStorage.setItem(REFRESH_KEY, data.refresh);
      localStorage.setItem('user_data', JSON.stringify(userData));

      setSessionExpired(false);
      setUser(userData);
      return { success: true };
    } catch (error) {
      return { success: false, message: 'Usuário ou senha inválidos' };
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, sessionExpired }}>
      {children}
    </AuthContext.Provider>
  );
};
