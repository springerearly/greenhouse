import React, { useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import ControlPage from './pages/ControlPage';
import PortsSettingsPage from './pages/PortsSettingsPage';
import DevicesPage from './pages/DevicesPage';
import DeviceDetailPage from './pages/DeviceDetailPage';
import MonitoringPage from './pages/MonitoringPage';
import AutomationsPage from './pages/AutomationsPage';
import AlertsPage from './pages/AlertsPage';
import { wsClient } from './services/websocket';

function App() {
  useEffect(() => {
    // Устанавливаем WS-соединение при монтировании приложения
    wsClient.connect();
    wsClient.subscribe(['sensors', 'gpio', 'alerts', 'devices', 'system']);
    return () => wsClient.disconnect();
  }, []);

  return (
    <Router>
      <Navbar />
      <div className="container-fluid mt-4 px-4">
        <Routes>
          <Route path="/"              element={<DashboardPage />} />
          <Route path="/control"       element={<ControlPage />} />
          <Route path="/settings"      element={<PortsSettingsPage />} />
          <Route path="/devices"       element={<DevicesPage />} />
          <Route path="/devices/:id"   element={<DeviceDetailPage />} />
          <Route path="/monitoring"    element={<MonitoringPage />} />
          <Route path="/automations"   element={<AutomationsPage />} />
          <Route path="/alerts"        element={<AlertsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
