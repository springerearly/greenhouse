import React, { useState, useEffect } from 'react';
import { getAlerts, acknowledgeAlert, acknowledgeAll } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const LEVEL_BADGE = {
    info:     'bg-info text-dark',
    warning:  'bg-warning text-dark',
    error:    'bg-danger',
    critical: 'bg-dark',
};

const LEVEL_ICON = {
    info: 'ℹ️', warning: '⚠️', error: '🔴', critical: '💀',
};

export default function AlertsPage() {
    const [alerts, setAlerts]           = useState([]);
    const [unackOnly, setUnackOnly]     = useState(false);
    const [loading, setLoading]         = useState(true);

    // Live алерты через WS
    const wsAlert = useWebSocket('alerts', 'new_alert', null);
    useEffect(() => {
        if (!wsAlert) return;
        setAlerts((prev) => [
            {
                id: wsAlert.id,
                device_id: wsAlert.device_id,
                level: wsAlert.level,
                message: wsAlert.message,
                acknowledged: false,
                created_at: wsAlert.created_at,
            },
            ...prev,
        ]);
    }, [wsAlert]);

    useEffect(() => { fetchAlerts(); }, [unackOnly]);

    async function fetchAlerts() {
        setLoading(true);
        try {
            setAlerts(await getAlerts(unackOnly));
        } finally { setLoading(false); }
    }

    async function handleAck(id) {
        await acknowledgeAlert(id);
        setAlerts((prev) =>
            prev.map((a) => (a.id === id ? { ...a, acknowledged: true } : a))
        );
    }

    async function handleAckAll() {
        await acknowledgeAll();
        setAlerts((prev) => prev.map((a) => ({ ...a, acknowledged: true })));
    }

    return (
        <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="mb-0">🔔 Алерты</h2>
                <div className="d-flex gap-2 align-items-center">
                    <div className="form-check mb-0">
                        <input className="form-check-input" type="checkbox" id="unack-only"
                            checked={unackOnly}
                            onChange={(e) => setUnackOnly(e.target.checked)}
                        />
                        <label className="form-check-label" htmlFor="unack-only">Только непрочитанные</label>
                    </div>
                    <button className="btn btn-sm btn-outline-secondary" onClick={handleAckAll}>
                        ✅ Прочитать все
                    </button>
                </div>
            </div>

            {loading && <div className="text-center"><div className="spinner-border" /></div>}

            {!loading && alerts.length === 0 && (
                <div className="alert alert-success">Нет алертов 🎉</div>
            )}

            <div className="list-group">
                {alerts.map((alert) => (
                    <div
                        key={alert.id}
                        className={`list-group-item list-group-item-action d-flex gap-3 align-items-start ${alert.acknowledged ? 'opacity-50' : ''}`}
                    >
                        <span className="fs-4">{LEVEL_ICON[alert.level] || 'ℹ️'}</span>
                        <div className="flex-grow-1">
                            <div className="d-flex gap-2 align-items-center">
                                <span className={`badge ${LEVEL_BADGE[alert.level] || 'bg-secondary'}`}>
                                    {alert.level}
                                </span>
                                {alert.device_id && (
                                    <span className="text-muted small">Устройство #{alert.device_id}</span>
                                )}
                                <span className="text-muted small ms-auto">
                                    {new Date(alert.created_at).toLocaleString('ru-RU')}
                                </span>
                            </div>
                            <div className="mt-1">{alert.message}</div>
                        </div>
                        {!alert.acknowledged && (
                            <button
                                className="btn btn-sm btn-outline-success flex-shrink-0"
                                onClick={() => handleAck(alert.id)}
                            >✓</button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
