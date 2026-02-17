import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getAlertCounts } from '../services/api';
import { useWsStatus } from '../hooks/useWebSocket';
import { useWebSocket } from '../hooks/useWebSocket';

function Navbar() {
  const location = useLocation();
  const wsConnected = useWsStatus();
  const [alertCount, setAlertCount] = useState(0);

  // Обновляем счётчик при новом алерте через WS
  const newAlert = useWebSocket('alerts', 'new_alert', null);
  useEffect(() => {
    if (newAlert) setAlertCount((c) => c + 1);
  }, [newAlert]);

  useEffect(() => {
    getAlertCounts().then((c) => setAlertCount(c.total || 0)).catch(() => {});
  }, []);

  const isActive = (path) => location.pathname === path ? 'active' : '';

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-success">
      <div className="container-fluid">
        <Link className="navbar-brand fw-bold" to="/">
          🌿 Теплица
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
        >
          <span className="navbar-toggler-icon"></span>
        </button>
        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav me-auto">
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/')}`} to="/">📊 Dashboard</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/devices')}`} to="/devices">📡 Устройства</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/monitoring')}`} to="/monitoring">📈 Мониторинг</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/control')}`} to="/control">🔌 GPIO</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/settings')}`} to="/settings">⚙️ GPIO настройки</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/automations')}`} to="/automations">🤖 Автоматизация</Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/alerts')} position-relative`} to="/alerts">
                🔔 Алерты
                {alertCount > 0 && (
                  <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                    {alertCount > 99 ? '99+' : alertCount}
                  </span>
                )}
              </Link>
            </li>
            <li className="nav-item">
              <Link className={`nav-link ${isActive('/raspberry')}`} to="/raspberry">🍓 Raspberry Pi</Link>
            </li>
          </ul>
          {/* Индикатор WS */}
          <span
            className={`badge ${wsConnected ? 'bg-light text-success' : 'bg-danger'} ms-2`}
            title={wsConnected ? 'WebSocket подключён' : 'WebSocket отключён'}
          >
            {wsConnected ? '● Live' : '○ Offline'}
          </span>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
