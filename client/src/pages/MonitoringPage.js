import React, { useState, useEffect } from 'react';
import { getDevices, getSensorHistory } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const SENSOR_TYPES = [
    { key: 'temperature', label: 'Температура', unit: '°C', color: '#e74c3c' },
    { key: 'humidity',    label: 'Влажность',   unit: '%',  color: '#3498db' },
    { key: 'soil_moisture', label: 'Влажность почвы', unit: '%', color: '#27ae60' },
    { key: 'co2',         label: 'CO₂',          unit: 'ppm', color: '#8e44ad' },
    { key: 'lux',         label: 'Освещённость', unit: 'lux', color: '#f39c12' },
    { key: 'pressure',    label: 'Давление',     unit: 'hPa', color: '#16a085' },
];

/** Простой ASCII-подобный мини-график через SVG */
function SparkLine({ data, color = '#3498db', height = 50 }) {
    if (!data || data.length < 2) return <div className="text-muted small">Недостаточно данных</div>;

    const values = data.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const w = 300;
    const h = height;
    const pts = values.map((v, i) => {
        const x = (i / (values.length - 1)) * w;
        const y = h - ((v - min) / range) * h;
        return `${x},${y}`;
    });

    return (
        <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
            <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth="2" />
        </svg>
    );
}

export default function MonitoringPage() {
    const [devices, setDevices]       = useState([]);
    const [selectedDevice, setSelectedDevice] = useState(null);
    const [selectedSensor, setSelectedSensor] = useState('temperature');
    const [hours, setHours]           = useState(24);
    const [history, setHistory]       = useState(null);
    const [loading, setLoading]       = useState(false);
    const [liveValues, setLiveValues] = useState({});

    // Live обновления через WS
    const wsData = useWebSocket('sensors', 'update', null);
    useEffect(() => {
        if (!wsData) return;
        setLiveValues((prev) => ({
            ...prev,
            [wsData.device_id]: wsData.sensors,
        }));
    }, [wsData]);

    useEffect(() => {
        getDevices().then((devs) => {
            setDevices(devs);
            if (devs.length > 0) setSelectedDevice(devs[0].id);
        });
    }, []);

    useEffect(() => {
        if (selectedDevice && selectedSensor) fetchHistory();
    }, [selectedDevice, selectedSensor, hours]);

    async function fetchHistory() {
        setLoading(true);
        try {
            const h = await getSensorHistory(selectedDevice, selectedSensor, hours);
            setHistory(h);
        } catch (_) { setHistory(null); }
        finally { setLoading(false); }
    }

    const sensorMeta = SENSOR_TYPES.find((s) => s.key === selectedSensor);

    return (
        <div>
            <h2 className="mb-4">📈 Мониторинг сенсоров</h2>

            {/* Фильтры */}
            <div className="row g-3 mb-4">
                <div className="col-md-4">
                    <label className="form-label">Устройство</label>
                    <select className="form-select"
                        value={selectedDevice || ''}
                        onChange={(e) => setSelectedDevice(parseInt(e.target.value))}
                    >
                        {devices.map((d) => (
                            <option key={d.id} value={d.id}>{d.name}</option>
                        ))}
                    </select>
                </div>
                <div className="col-md-4">
                    <label className="form-label">Тип сенсора</label>
                    <select className="form-select"
                        value={selectedSensor}
                        onChange={(e) => setSelectedSensor(e.target.value)}
                    >
                        {SENSOR_TYPES.map((s) => (
                            <option key={s.key} value={s.key}>{s.label}</option>
                        ))}
                    </select>
                </div>
                <div className="col-md-4">
                    <label className="form-label">Период</label>
                    <select className="form-select"
                        value={hours}
                        onChange={(e) => setHours(parseInt(e.target.value))}
                    >
                        <option value={1}>1 час</option>
                        <option value={6}>6 часов</option>
                        <option value={24}>24 часа</option>
                        <option value={72}>3 дня</option>
                        <option value={168}>7 дней</option>
                    </select>
                </div>
            </div>

            {/* График */}
            <div className="card mb-4">
                <div className="card-header d-flex justify-content-between">
                    <span>
                        {sensorMeta?.label || selectedSensor}
                        {history && <span className="text-muted ms-2">({history.data.length} точек)</span>}
                    </span>
                    {history?.unit && <span className="badge bg-secondary">{history.unit}</span>}
                </div>
                <div className="card-body">
                    {loading && <div className="text-center"><div className="spinner-border" /></div>}
                    {!loading && history && history.data.length > 1 && (
                        <>
                            <SparkLine data={history.data} color={sensorMeta?.color} height={80} />
                            <div className="d-flex justify-content-between text-muted small mt-1">
                                <span>{new Date(history.data[0].timestamp).toLocaleString('ru-RU')}</span>
                                <span>{new Date(history.data[history.data.length - 1].timestamp).toLocaleString('ru-RU')}</span>
                            </div>
                        </>
                    )}
                    {!loading && (!history || history.data.length === 0) && (
                        <div className="text-muted text-center py-4">Нет данных за выбранный период</div>
                    )}
                </div>
            </div>

            {/* Live таблица всех устройств */}
            <h5>🔴 Текущие показания (live)</h5>
            <div className="table-responsive">
                <table className="table table-sm table-bordered">
                    <thead className="table-light">
                        <tr>
                            <th>Устройство</th>
                            {SENSOR_TYPES.map((s) => (
                                <th key={s.key}>{s.label}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {devices.map((d) => {
                            const vals = liveValues[d.id] || {};
                            return (
                                <tr key={d.id}>
                                    <td><strong>{d.name}</strong></td>
                                    {SENSOR_TYPES.map((s) => {
                                        const raw = vals[s.key];
                                        const val = raw !== undefined
                                            ? (typeof raw === 'object' ? raw.value : raw)
                                            : null;
                                        return (
                                            <td key={s.key} className="text-center">
                                                {val !== null
                                                    ? <span style={{ color: sensorMeta?.color }}>
                                                        {Number(val).toFixed(1)} {s.unit}
                                                      </span>
                                                    : <span className="text-muted">—</span>}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
