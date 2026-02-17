import React, { useState, useEffect } from 'react';
import { getAutomations, createAutomation, updateAutomation, deleteAutomation } from '../services/api';
import { getDevices } from '../services/api';

const OPERATORS = ['>', '<', '>=', '<=', '==', '!='];
const SENSOR_TYPES = ['temperature', 'humidity', 'soil_moisture', 'co2', 'lux', 'pressure', 'voltage', 'current'];
const ACTION_TYPES = [
    { value: 'gpio', label: 'GPIO пин Raspberry Pi' },
    { value: 'device_control', label: 'ESP-устройство' },
];

function buildTriggerJson(trigger) {
    return JSON.stringify({
        device_id: parseInt(trigger.device_id),
        sensor: trigger.sensor,
        operator: trigger.operator,
        threshold: parseFloat(trigger.threshold),
    });
}

function buildActionJson(action) {
    if (action.type === 'gpio') {
        return JSON.stringify({
            type: 'gpio',
            target_id: parseInt(action.target_id),
            action: action.action,
        });
    }
    return JSON.stringify({
        type: 'device_control',
        target_id: parseInt(action.target_id),
        command: { [action.command_key]: parseInt(action.command_val) },
    });
}

const EMPTY_TRIGGER = { device_id: '', sensor: 'temperature', operator: '>', threshold: '25' };
const EMPTY_ACTION  = { type: 'gpio', target_id: '', action: 'on', command_key: 'relay1', command_val: '1' };

export default function AutomationsPage() {
    const [automations, setAutomations] = useState([]);
    const [devices, setDevices]         = useState([]);
    const [showForm, setShowForm]       = useState(false);
    const [form, setForm]               = useState({
        name: '', description: '', cooldown_seconds: 60, enabled: true,
    });
    const [trigger, setTrigger]         = useState({ ...EMPTY_TRIGGER });
    const [action, setAction]           = useState({ ...EMPTY_ACTION });
    const [error, setError]             = useState(null);

    useEffect(() => {
        fetchAll();
    }, []);

    async function fetchAll() {
        const [autos, devs] = await Promise.all([getAutomations(), getDevices()]);
        setAutomations(autos);
        setDevices(devs);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setError(null);
        try {
            await createAutomation({
                ...form,
                trigger_json: buildTriggerJson(trigger),
                action_json: buildActionJson(action),
            });
            setShowForm(false);
            setForm({ name: '', description: '', cooldown_seconds: 60, enabled: true });
            setTrigger({ ...EMPTY_TRIGGER });
            setAction({ ...EMPTY_ACTION });
            fetchAll();
        } catch (e) { setError(e.message); }
    }

    async function toggleEnabled(auto) {
        await updateAutomation(auto.id, { enabled: !auto.enabled });
        fetchAll();
    }

    async function handleDelete(id) {
        if (!window.confirm('Удалить правило?')) return;
        await deleteAutomation(id);
        fetchAll();
    }

    function parseTrigger(json) {
        try { return JSON.parse(json); } catch { return {}; }
    }
    function parseAction(json) {
        try { return JSON.parse(json); } catch { return {}; }
    }
    function deviceName(id) {
        return devices.find((d) => d.id === id)?.name || `ID ${id}`;
    }
    function describeTrigger(t) {
        const d = parseTrigger(t.trigger_json);
        return `${deviceName(d.device_id)} · ${d.sensor} ${d.operator} ${d.threshold}`;
    }
    function describeAction(t) {
        const a = parseAction(t.action_json);
        if (a.type === 'gpio') return `GPIO ${a.target_id} → ${a.action}`;
        return `Устройство ${deviceName(a.target_id)} → ${JSON.stringify(a.command)}`;
    }

    return (
        <div>
            <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="mb-0">⚙️ Автоматизация</h2>
                <button className="btn btn-success" onClick={() => setShowForm(!showForm)}>
                    {showForm ? 'Скрыть форму' : '+ Новое правило'}
                </button>
            </div>

            {error && <div className="alert alert-danger alert-dismissible">
                {error}<button className="btn-close" onClick={() => setError(null)} />
            </div>}

            {/* Форма создания */}
            {showForm && (
                <div className="card mb-4 border-success">
                    <div className="card-header bg-success text-white">Новое правило автоматизации</div>
                    <div className="card-body">
                        <form onSubmit={handleSubmit}>
                            <div className="row g-3 mb-3">
                                <div className="col-md-6">
                                    <label className="form-label">Название правила</label>
                                    <input className="form-control" required
                                        value={form.name}
                                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                                        placeholder="Охлаждение при перегреве"
                                    />
                                </div>
                                <div className="col-md-3">
                                    <label className="form-label">Cooldown (сек)</label>
                                    <input className="form-control" type="number" min="10"
                                        value={form.cooldown_seconds}
                                        onChange={(e) => setForm({ ...form, cooldown_seconds: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div className="col-md-3 d-flex align-items-end">
                                    <div className="form-check">
                                        <input className="form-check-input" type="checkbox" id="auto-enabled"
                                            checked={form.enabled}
                                            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                                        />
                                        <label className="form-check-label" htmlFor="auto-enabled">Включено</label>
                                    </div>
                                </div>
                            </div>

                            {/* Условие (trigger) */}
                            <div className="card mb-3 border-warning">
                                <div className="card-header bg-warning text-dark">🔔 Условие (ЕСЛИ)</div>
                                <div className="card-body">
                                    <div className="row g-2">
                                        <div className="col-md-3">
                                            <label className="form-label">Устройство</label>
                                            <select className="form-select" required
                                                value={trigger.device_id}
                                                onChange={(e) => setTrigger({ ...trigger, device_id: e.target.value })}
                                            >
                                                <option value="">-- выберите --</option>
                                                {devices.map((d) => (
                                                    <option key={d.id} value={d.id}>{d.name}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-3">
                                            <label className="form-label">Сенсор</label>
                                            <select className="form-select"
                                                value={trigger.sensor}
                                                onChange={(e) => setTrigger({ ...trigger, sensor: e.target.value })}
                                            >
                                                {SENSOR_TYPES.map((s) => (
                                                    <option key={s} value={s}>{s}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-2">
                                            <label className="form-label">Оператор</label>
                                            <select className="form-select"
                                                value={trigger.operator}
                                                onChange={(e) => setTrigger({ ...trigger, operator: e.target.value })}
                                            >
                                                {OPERATORS.map((o) => (
                                                    <option key={o} value={o}>{o}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-4">
                                            <label className="form-label">Порог</label>
                                            <input className="form-control" type="number" step="0.1" required
                                                value={trigger.threshold}
                                                onChange={(e) => setTrigger({ ...trigger, threshold: e.target.value })}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Действие (action) */}
                            <div className="card mb-3 border-primary">
                                <div className="card-header bg-primary text-white">⚡ Действие (ТО)</div>
                                <div className="card-body">
                                    <div className="row g-2">
                                        <div className="col-md-3">
                                            <label className="form-label">Тип</label>
                                            <select className="form-select"
                                                value={action.type}
                                                onChange={(e) => setAction({ ...action, type: e.target.value })}
                                            >
                                                {ACTION_TYPES.map((t) => (
                                                    <option key={t.value} value={t.value}>{t.label}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-md-3">
                                            <label className="form-label">
                                                {action.type === 'gpio' ? 'GPIO пин' : 'Устройство'}
                                            </label>
                                            {action.type === 'gpio' ? (
                                                <input className="form-control" type="number" placeholder="17" required
                                                    value={action.target_id}
                                                    onChange={(e) => setAction({ ...action, target_id: e.target.value })}
                                                />
                                            ) : (
                                                <select className="form-select" required
                                                    value={action.target_id}
                                                    onChange={(e) => setAction({ ...action, target_id: e.target.value })}
                                                >
                                                    <option value="">-- выберите --</option>
                                                    {devices.map((d) => (
                                                        <option key={d.id} value={d.id}>{d.name}</option>
                                                    ))}
                                                </select>
                                            )}
                                        </div>
                                        {action.type === 'gpio' ? (
                                            <div className="col-md-3">
                                                <label className="form-label">Команда</label>
                                                <select className="form-select"
                                                    value={action.action}
                                                    onChange={(e) => setAction({ ...action, action: e.target.value })}
                                                >
                                                    <option value="on">on (включить)</option>
                                                    <option value="off">off (выключить)</option>
                                                </select>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="col-md-2">
                                                    <label className="form-label">Команда</label>
                                                    <input className="form-control" placeholder="relay1"
                                                        value={action.command_key}
                                                        onChange={(e) => setAction({ ...action, command_key: e.target.value })}
                                                    />
                                                </div>
                                                <div className="col-md-2">
                                                    <label className="form-label">Значение</label>
                                                    <input className="form-control" type="number"
                                                        value={action.command_val}
                                                        onChange={(e) => setAction({ ...action, command_val: e.target.value })}
                                                    />
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <button type="submit" className="btn btn-success">Сохранить правило</button>
                        </form>
                    </div>
                </div>
            )}

            {/* Список правил */}
            {automations.length === 0 ? (
                <div className="alert alert-info">Нет правил автоматизации.</div>
            ) : (
                <div className="table-responsive">
                    <table className="table table-hover align-middle">
                        <thead className="table-light">
                            <tr>
                                <th>Вкл</th>
                                <th>Название</th>
                                <th>Условие</th>
                                <th>Действие</th>
                                <th>Cooldown</th>
                                <th>Последний раз</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {automations.map((auto) => (
                                <tr key={auto.id} className={auto.enabled ? '' : 'table-secondary'}>
                                    <td>
                                        <div className="form-check form-switch">
                                            <input className="form-check-input" type="checkbox"
                                                checked={auto.enabled}
                                                onChange={() => toggleEnabled(auto)}
                                            />
                                        </div>
                                    </td>
                                    <td><strong>{auto.name}</strong></td>
                                    <td><code className="small">{describeTrigger(auto)}</code></td>
                                    <td><code className="small">{describeAction(auto)}</code></td>
                                    <td>{auto.cooldown_seconds}с</td>
                                    <td>
                                        <small className="text-muted">
                                            {auto.last_triggered
                                                ? new Date(auto.last_triggered).toLocaleString('ru-RU')
                                                : '—'}
                                        </small>
                                    </td>
                                    <td>
                                        <button className="btn btn-sm btn-outline-danger"
                                            onClick={() => handleDelete(auto.id)}>🗑️</button>
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
