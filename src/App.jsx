import React, { useContext } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { TransactionProvider, TransactionContext } from './context/TransactionContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Analysis from './pages/Analysis';
import Lending from './pages/Lending';
import BotTraining from './pages/BotTraining';
import Login from './pages/Login';
import Register from './pages/Register';
import Friends from './pages/Friends';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useContext(TransactionContext);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <BrowserRouter>
      <TransactionProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />

          <Route path="/analysis" element={
            <ProtectedRoute>
              <Analysis />
            </ProtectedRoute>
          } />

          <Route path="/lending" element={
            <ProtectedRoute>
              <Lending />
            </ProtectedRoute>
          } />

          <Route path="/bot-training" element={
            <ProtectedRoute>
              <BotTraining />
            </ProtectedRoute>
          } />
          
          <Route path="/friends" element={
            <ProtectedRoute>
              <Friends />
            </ProtectedRoute>
          } />
        </Routes>
      </TransactionProvider>
    </BrowserRouter>
  );
}

export default App;
