import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getDevices, getLatestReadings, getAlertCounts } from '../services/api';
import { useWebSocket, useWsStatus } from '../hooks/useWebSocket';

const SENSOR_ICONS = {
    temperature: '🌡️',
    humidity: '💧',
    soil_moisture: '🌱',
    co2: '🌫️',
    lux: '☀️',
    pressure: '🔵',
    voltage: '⚡',
    current: '⚡',
    power: '⚡',
};

const DEVICE_TYPE_LABELS = {
    climate: '🌡️ Климат',
    irrigation: '💧 Полив',
    light: '☀️ Свет',
    co2: '🌫️ CO₂',
    power: '⚡ Питание',
    camera: '📷 Камера',
};

const STATUS_BADGE = {
    online: 'bg-success',
    offline: 'bg-danger',
    unknown: 'bg-secondary',
};

export default function DashboardPage() {
    const [devices, setDevices] = useState([]);
    const [readings, setReadings] = useState({});
    const [alertCounts, setAlertCounts] = useState({ total: 0 });
    const [loading, setLoading] = useState(true);
    const wsConnected = useWsStatus();

    // Живые данные сенсоров через WS
    const wsData = useWebSocket('sensors', 'update', null);
    const wsDeviceStatus = useWebSocket('devices', 'status_change', null);

    useEffect(() => {
        fetchAll();
    }, []);

    // Обновляем данные сенсоров при WS-событии
    useEffect(() => {
        if (!wsData) return;
        setReadings((prev) => ({
            ...prev,
            [wsData.device_id]: wsData.sensors,
        }));
    }, [wsData]);

    // Обновляем статус устройства при WS-событии
    useEffect(() => {
        if (!wsDeviceStatus) return;
        setDevices((prev) =>
            prev.map((d) =>
                d.id === wsDeviceStatus.device_id
                    ? { ...d, status: wsDeviceStatus.status }
                    : d
            )
        );
    }, [wsDeviceStatus]);

    async function fetchAll() {
        try {
            const [devs, counts] = await Promise.all([
                getDevices(),
                getAlertCounts(),
            ]);
            setDevices(devs);
            setAlertCounts(counts);

            // Загружаем последние показания для каждого устройства
            const readingsMap = {};
            await Promise.all(
                devs.map(async (d) => {
                    try {
                        const r = await getLatestReadings(d.id);
                        const map = {};
                        r.forEach((row) => {
                            map[row.sensor_type] = { value: row.value, unit: row.unit };
                        });
                        readingsMap[d.id] = map;
                    } catch (_) {}
                })
            );
            setReadings(readingsMap);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    if (loading) return <div className="text-center mt-5"><div className="spinner-border" /></div>;

    const onlineCount = devices.filter((d) => d.status === 'online').length;
    const offlineCount = devices.filter((d) => d.status === 'offline').length;

    return (
        <div>
            <div className="d-flex align-items-center justify-content-between mb-4">
                <h2 className="mb-0">🌿 Dashboard</h2>
                <span className={`badge ${wsConnected ? 'bg-success' : 'bg-danger'}`}>
                    {wsConnected ? '● Live' : '○ Offline'}
                </span>
            </div>

            {/* Статистика */}
            <div className="row g-3 mb-4">
                <div className="col-6 col-md-3">
                    <div className="card text-center border-success">
                        <div className="card-body">
                            <div className="fs-1 fw-bold text-success">{onlineCount}</div>
                            <div className="text-muted small">Устройств онлайн</div>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card text-center border-danger">
                        <div className="card-body">
                            <div className="fs-1 fw-bold text-danger">{offlineCount}</div>
                            <div className="text-muted small">Устройств офлайн</div>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card text-center border-warning">
                        <div className="card-body">
                            <div className="fs-1 fw-bold text-warning">{alertCounts.total || 0}</div>
                            <div className="text-muted small">Непрочитанных алертов</div>
                        </div>
                    </div>
                </div>
                <div className="col-6 col-md-3">
                    <div className="card text-center border-primary">
                        <div className="card-body">
                            <div className="fs-1 fw-bold text-primary">{devices.length}</div>
                            <div className="text-muted small">Всего устройств</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Карточки устройств */}
            {devices.length === 0 ? (
                <div className="alert alert-info">
                    Устройства не добавлены.{' '}
                    <Link to="/devices">Добавьте первое устройство</Link>
                </div>
            ) : (
                <div className="row g-3">
                    {devices.map((device) => {
                        const devReadings = readings[device.id] || {};
                        return (
                            <div className="col-md-6 col-lg-4" key={device.id}>
                                <div className="card h-100">
                                    <div className="card-header d-flex justify-content-between align-items-center">
                                        <span>
                                            {DEVICE_TYPE_LABELS[device.device_type] || device.device_type}{' '}
                                            <strong>{device.name}</strong>
                                        </span>
                                        <span className={`badge ${STATUS_BADGE[device.status] || 'bg-secondary'}`}>
                                            {device.status}
                                        </span>
                                    </div>
                                    <div className="card-body">
                                        <div className="text-muted small mb-2">{device.ip_address}</div>
                                        {Object.entries(devReadings).length === 0 ? (
                                            <div className="text-muted small">Нет данных</div>
                                        ) : (
                                            <div className="row g-2">
                                                {Object.entries(devReadings).map(([stype, payload]) => (
                                                    <div className="col-6" key={stype}>
                                                        <div className="bg-light rounded p-2 text-center">
                                                            <div className="fs-5">
                                                                {SENSOR_ICONS[stype] || '📊'}
                                                            </div>
                                                            <div className="fw-bold">
                                                                {typeof payload === 'object'
                                                                    ? `${payload.value} ${payload.unit || ''}`
                                                                    : payload}
                                                            </div>
                                                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                                                                {stype}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <div className="card-footer">
                                        <Link
                                            to={`/devices/${device.id}`}
                                            className="btn btn-sm btn-outline-primary w-100"
                                        >
                                            Подробнее →
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
