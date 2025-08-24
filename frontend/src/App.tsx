import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Licitaciones from './pages/Licitaciones';
import Analytics from './pages/Analytics';
import LicitacionDetail from './pages/LicitacionDetail';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/licitaciones" element={<Licitaciones />} />
          <Route path="/licitaciones/:id" element={<LicitacionDetail />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;