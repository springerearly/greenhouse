import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    getDevice, getSensorHistory, getSensorStats, controlDevice, pollDeviceNow
} from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const SENSOR_ICONS = {
    temperature: '🌡️', humidity: '💧', soil_moisture: '🌱',
    co2: '🌫️', lux: '☀️', pressure: '🔵', voltage: '⚡',
    current: '⚡', power: '⚡',
};

const RELAY_LABELS = ['relay1', 'relay2', 'relay3', 'relay4'];

export default function DeviceDetailPage() {
    const { id } = useParams();
    const deviceId = parseInt(id);

    const [device, setDevice]   = useState(null);
    const [stats, setStats]     = useState({});
    const [history, setHistory] = useState({});
    const [relays, setRelays]   = useState({});
    const [pwm, setPwm]         = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError]     = useState(null);
    const [polling, setPolling] = useState(false);

    // Live данные через WS
    const wsData = useWebSocket('sensors', 'update', null);

    useEffect(() => {
        fetchDevice();
    }, [deviceId]);

    // Обновляем данные при WS-событии от этого устройства
    useEffect(() => {
        if (!wsData || wsData.device_id !== deviceId) return;
        // Обновляем текущие показания в device.latest_readings
        setDevice((prev) => {
            if (!prev) return prev;
            const updated = { ...prev, latest_readings: {} };
            Object.entries(wsData.sensors).forEach(([k, v]) => {
                updated.latest_readings[k] = typeof v === 'object' ? v : { value: v, unit: null };
            });
            return updated;
        });
        // Обновляем состояния реле
        if (wsData.actuators) {
            const newRelays = {};
            RELAY_LABELS.forEach((r) => {
                if (wsData.actuators[r] !== undefined) newRelays[r] = wsData.actuators[r];
            });
            setRelays((prev) => ({ ...prev, ...newRelays }));
            if (wsData.actuators.pwm !== undefined) setPwm(wsData.actuators.pwm);
        }
    }, [wsData, deviceId]);

    async function fetchDevice() {
        try {
            setLoading(true);
            const d = await getDevice(deviceId);
            setDevice(d);
            // Начальные состояния реле (если есть)
            const initialRelays = {};
            RELAY_LABELS.forEach((r) => { initialRelays[r] = 0; });
            setRelays(initialRelays);
            // Загружаем статистику для каждого типа сенсора
            fetchStats(d);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
    }

    async function fetchStats(d) {
        const sensorTypes = Object.keys(d.latest_readings || {});
        const statsMap = {};
        await Promise.all(
            sensorTypes.map(async (st) => {
                try {
                    statsMap[st] = await getSensorStats(deviceId, st, 24);
                } catch (_) {}
            })
        );
        setStats(statsMap);
    }

    async function handleRelay(relay, value) {
        try {
            await controlDevice(deviceId, { [relay]: value });
            setRelays((prev) => ({ ...prev, [relay]: value }));
        } catch (e) { setError(e.message); }
    }

    async function handlePwm(value) {
        try {
            await controlDevice(deviceId, { pwm: value });
            setPwm(value);
        } catch (e) { setError(e.message); }
    }

    async function handlePoll() {
        setPolling(true);
        try { await pollDeviceNow(deviceId); await fetchDevice(); }
        catch (e) { setError(e.message); }
        finally { setPolling(false); }
    }

    if (loading) return <div className="text-center mt-5"><div className="spinner-border" /></div>;
    if (error) return <div className="alert alert-danger">{error}</div>;
    if (!device) return <div className="alert alert-warning">Устройство не найдено</div>;

    const readings = device.latest_readings || {};

    return (
        <div>
            {/* Хлебные крошки */}
            <nav aria-label="breadcrumb">
                <ol className="breadcrumb">
                    <li className="breadcrumb-item"><Link to="/devices">Устройства</Link></li>
                    <li className="breadcrumb-item active">{device.name}</li>
                </ol>
            </nav>

            {/* Шапка */}
            <div className="d-flex align-items-center gap-3 mb-4">
                <div>
                    <h2 className="mb-0">{device.name}</h2>
                    <small className="text-muted">
                        {device.device_type} · {device.ip_address}:{device.port}
                    </small>
                </div>
                <span className={`badge fs-6 ${device.status === 'online' ? 'bg-success' : 'bg-danger'}`}>
                    {device.status}
                </span>
                <button className="btn btn-outline-info ms-auto" onClick={handlePoll} disabled={polling}>
                    {polling ? '⏳ Опрашиваем...' : '🔄 Опросить'}
                </button>
            </div>

            <div className="row g-4">
                {/* Текущие показания */}
                <div className="col-lg-7">
                    <div className="card">
                        <div className="card-header">📊 Текущие показания</div>
                        <div className="card-body">
                            {Object.keys(readings).length === 0 ? (
                                <div className="text-muted">Нет данных</div>
                            ) : (
                                <div className="row g-3">
                                    {Object.entries(readings).map(([st, payload]) => {
                                        const val = typeof payload === 'object' ? payload.value : payload;
                                        const unit = typeof payload === 'object' ? payload.unit : null;
                                        const s = stats[st];
                                        return (
                                            <div className="col-6 col-xl-4" key={st}>
                                                <div className="card bg-light h-100">
                                                    <div className="card-body text-center p-3">
                                                        <div className="fs-2">{SENSOR_ICONS[st] || '📊'}</div>
                                                        <div className="fs-4 fw-bold">
                                                            {val !== null && val !== undefined
                                                                ? `${Number(val).toFixed(1)} ${unit || ''}`
                                                                : '—'}
                                                        </div>
                                                        <div className="text-muted small">{st}</div>
                                                        {s && (
                                                            <div className="text-muted" style={{ fontSize: '0.7rem' }}>
                                                                min {s.min} · avg {s.avg} · max {s.max}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Управление */}
                <div className="col-lg-5">
                    <div className="card">
                        <div className="card-header">🎛️ Управление</div>
                        <div className="card-body">
                            {/* Реле */}
                            <div className="mb-3">
                                <div className="fw-semibold mb-2">Реле</div>
                                <div className="d-flex flex-wrap gap-2">
                                    {RELAY_LABELS.map((relay) => (
                                        <div key={relay} className="d-flex align-items-center gap-1">
                                            <span className="text-muted small">{relay}</span>
                                            <div className="btn-group btn-group-sm">
                                                <button
                                                    className={`btn ${relays[relay] === 1 ? 'btn-success' : 'btn-outline-success'}`}
                                                    onClick={() => handleRelay(relay, 1)}
                                                >ON</button>
                                                <button
                                                    className={`btn ${relays[relay] === 0 ? 'btn-danger' : 'btn-outline-danger'}`}
                                                    onClick={() => handleRelay(relay, 0)}
                                                >OFF</button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* PWM */}
                            <div>
                                <div className="fw-semibold mb-2">PWM: {pwm}</div>
                                <input
                                    type="range" className="form-range"
                                    min="0" max="255" step="1"
                                    value={pwm}
                                    onChange={(e) => setPwm(parseInt(e.target.value))}
                                    onMouseUp={() => handlePwm(pwm)}
                                    onTouchEnd={() => handlePwm(pwm)}
                                />
                                <div className="d-flex justify-content-between text-muted small">
                                    <span>0</span><span>128</span><span>255</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Метаданные */}
                    <div className="card mt-3">
                        <div className="card-header">ℹ️ Информация</div>
                        <div className="card-body">
                            <table className="table table-sm mb-0">
                                <tbody>
                                    <tr><th>MAC</th><td>{device.mac_address || '—'}</td></tr>
                                    <tr><th>Прошивка</th><td>{device.firmware_version || '—'}</td></tr>
                                    <tr><th>Интервал</th><td>{device.poll_interval}с</td></tr>
                                    <tr><th>Последний опрос</th><td>
                                        {device.last_seen ? new Date(device.last_seen).toLocaleString('ru-RU') : '—'}
                                    </td></tr>
                                    <tr><th>Добавлен</th><td>
                                        {new Date(device.created_at).toLocaleDateString('ru-RU')}
                                    </td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
