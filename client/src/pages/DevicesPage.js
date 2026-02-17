import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    getDevices, createDevice, updateDevice, deleteDevice, pollDeviceNow
} from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const DEVICE_TYPES = [
    { value: 'climate',   label: '🌡️ Климат-узел (DHT22, BMP280)' },
    { value: 'irrigation',label: '💧 Полив-узел (влажность почвы, клапан)' },
    { value: 'light',     label: '☀️ Свет-узел (BH1750, фитолампы)' },
    { value: 'co2',       label: '🌫️ CO₂-узел (MH-Z19B, вентиляция)' },
    { value: 'power',     label: '⚡ Питание-узел (INA226, счётчик энергии)' },
    { value: 'camera',    label: '📷 Камера-узел (ESP32-CAM)' },
];

const STATUS_BADGE = {
    online:  'bg-success',
    offline: 'bg-danger',
    unknown: 'bg-secondary',
};

const EMPTY_FORM = {
    name: '', device_type: 'climate', ip_address: '',
    port: 80, poll_interval: 5, description: '', enabled: true,
};

export default function DevicesPage() {
    const [devices, setDevices]       = useState([]);
    const [loading, setLoading]       = useState(true);
    const [showForm, setShowForm]     = useState(false);
    const [editDevice, setEditDevice] = useState(null);
    const [form, setForm]             = useState(EMPTY_FORM);
    const [error, setError]           = useState(null);
    const [polling, setPolling]       = useState(null);

    // WS: обновление статуса
    const wsStatus = useWebSocket('devices', 'status_change', null);
    useEffect(() => {
        if (!wsStatus) return;
        setDevices((prev) =>
            prev.map((d) =>
                d.id === wsStatus.device_id ? { ...d, status: wsStatus.status } : d
            )
        );
    }, [wsStatus]);

    useEffect(() => { fetchDevices(); }, []);

    async function fetchDevices() {
        try {
            setLoading(true);
            setDevices(await getDevices());
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
    }

    function openAdd() {
        setEditDevice(null);
        setForm(EMPTY_FORM);
        setShowForm(true);
        setError(null);
    }

    function openEdit(device) {
        setEditDevice(device);
        setForm({
            name: device.name, device_type: device.device_type,
            ip_address: device.ip_address, port: device.port,
            poll_interval: device.poll_interval,
            description: device.description || '', enabled: device.enabled,
        });
        setShowForm(true);
        setError(null);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setError(null);
        try {
            if (editDevice) {
                await updateDevice(editDevice.id, form);
            } else {
                await createDevice(form);
            }
            setShowForm(false);
            fetchDevices();
        } catch (e) { setError(e.message); }
    }

    async function handleDelete(id) {
        if (!window.confirm('Удалить устройство?')) return;
        try { await deleteDevice(id); fetchDevices(); }
        catch (e) { setError(e.message); }
    }

    async function handlePoll(id) {
        setPolling(id);
        try { await pollDeviceNow(id); fetchDevices(); }
        catch (e) { setError(e.message); }
        finally { setPolling(null); }
    }

    if (loading) return <div className="text-center mt-5"><div className="spinner-border" /></div>;

    return (
        <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="mb-0">📡 ESP-устройства</h2>
                <button className="btn btn-success" onClick={openAdd}>+ Добавить устройство</button>
            </div>

            {error && <div className="alert alert-danger alert-dismissible">
                {error}<button className="btn-close" onClick={() => setError(null)} />
            </div>}

            {/* Форма добавления / редактирования */}
            {showForm && (
                <div className="card mb-4 border-primary">
                    <div className="card-header bg-primary text-white">
                        {editDevice ? `Редактировать: ${editDevice.name}` : 'Новое устройство'}
                    </div>
                    <div className="card-body">
                        <form onSubmit={handleSubmit}>
                            <div className="row g-3">
                                <div className="col-md-6">
                                    <label className="form-label">Название</label>
                                    <input className="form-control" required
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    />
                                </div>
                                <div className="col-md-6">
                                    <label className="form-label">Тип устройства</label>
                                    <select className="form-select"
                                        value={form.device_type}
                                        onChange={(e) => setForm({ ...form, device_type: e.target.value })}
                                    >
                                        {DEVICE_TYPES.map((t) => (
                                            <option key={t.value} value={t.value}>{t.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-md-4">
                                    <label className="form-label">IP-адрес</label>
                                    <input className="form-control" required placeholder="192.168.1.100"
                                        value={form.ip_address}
                                        onChange={(e) => setForm({ ...form, ip_address: e.target.value })}
                                    />
                                </div>
                                <div className="col-md-2">
                                    <label className="form-label">Порт</label>
                                    <input className="form-control" type="number" min="1" max="65535"
                                        value={form.port}
                                        onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">Интервал опроса (сек)</label>
                                    <input className="form-control" type="number" min="1" max="3600"
                                        value={form.poll_interval}
                                        onChange={(e) => setForm({ ...form, poll_interval: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="col-md-3 d-flex align-items-end">
                                    <div className="form-check">
                                        <input className="form-check-input" type="checkbox" id="enabled"
                                            checked={form.enabled}
                                            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                                        />
                                        <label className="form-check-label" htmlFor="enabled">Включено</label>
                                    </div>
                                </div>
                                <div className="col-12">
                                    <label className="form-label">Описание</label>
                                    <input className="form-control" placeholder="Необязательно"
                                        value={form.description}
                                        onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="mt-3 d-flex gap-2">
                                <button type="submit" className="btn btn-primary">
                                    {editDevice ? 'Сохранить' : 'Добавить'}
                                </button>
                                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                                    Отмена
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Таблица устройств */}
            {devices.length === 0 ? (
                <div className="alert alert-info">Нет зарегистрированных устройств.</div>
            ) : (
                <div className="table-responsive">
                    <table className="table table-hover align-middle">
                        <thead className="table-light">
                            <tr>
                                <th>Статус</th>
                                <th>Название</th>
                                <th>Тип</th>
                                <th>IP : Порт</th>
                                <th>Интервал</th>
                                <th>Последний опрос</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            {devices.map((d) => (
                                <tr key={d.id}>
                                    <td>
                                        <span className={`badge ${STATUS_BADGE[d.status] || 'bg-secondary'}`}>
                                            {d.status}
                                        </span>
                                    </td>
                                    <td>
                                        <Link to={`/devices/${d.id}`} className="fw-bold text-decoration-none">
                                            {d.name}
                                        </Link>
                                        {d.description && (
                                            <div className="text-muted small">{d.description}</div>
                                        )}
                                    </td>
                                    <td>{DEVICE_TYPES.find((t) => t.value === d.device_type)?.label || d.device_type}</td>
                                    <td><code>{d.ip_address}:{d.port}</code></td>
                                    <td>{d.poll_interval}с</td>
                                    <td>
                                        <small className="text-muted">
                                            {d.last_seen
                                                ? new Date(d.last_seen).toLocaleString('ru-RU')
                                                : '—'}
                                        </small>
                                    </td>
                                    <td>
                                        <div className="d-flex gap-1">
                                            <button
                                                className="btn btn-sm btn-outline-info"
                                                onClick={() => handlePoll(d.id)}
                                                disabled={polling === d.id}
                                                title="Опросить сейчас"
                                            >
                                                {polling === d.id ? '⏳' : '🔄'}
                                            </button>
                                            <button
                                                className="btn btn-sm btn-outline-secondary"
                                                onClick={() => openEdit(d)}
                                                title="Редактировать"
                                            >✏️</button>
                                            <button
                                                className="btn btn-sm btn-outline-danger"
                                                onClick={() => handleDelete(d.id)}
                                                title="Удалить"
                                            >🗑️</button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
