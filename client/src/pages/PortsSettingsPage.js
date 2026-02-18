import React, { useState, useEffect, useCallback } from 'react';
import { getAllPins, getGpios, unassignGpio } from '../services/api';
import AssignModal from '../components/AssignModal';

// BCM-номера пинов с аппаратным PWM
const HW_PWM_PINS = new Set([12, 13, 18, 19]);

function FuncBadge({ func }) {
    if (!func) return <span className="text-muted">—</span>;
    const map = {
        OUTPUT: <span className="badge bg-primary">⬆ OUTPUT</span>,
        INPUT:  <span className="badge bg-info text-dark">⬇ INPUT</span>,
        PWM:    <span className="badge bg-warning text-dark">〜 PWM</span>,
    };
    return map[func] ?? <span className="badge bg-secondary">{func}</span>;
}

function PwmBadge({ pin }) {
    const hw = pin.supports_hw_pwm ?? HW_PWM_PINS.has(pin.number);
    if (!hw) return <span className="text-muted small">—</span>;
    return (
        <span className="badge bg-warning text-dark" title="Аппаратный PWM (lgpio)">
            〜 HW
        </span>
    );
}

function PortsSettingsPage() {
    const [allPins, setAllPins]           = useState([]);
    const [assignedGpios, setAssignedGpios] = useState(new Map());
    const [error, setError]               = useState(null);
    const [loading, setLoading]           = useState(true);
    const [showModal, setShowModal]       = useState(false);
    const [selectedPin, setSelectedPin]   = useState(null);

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const [pins, gpios] = await Promise.all([getAllPins(), getGpios()]);
            setAllPins(pins);
            setAssignedGpios(new Map(gpios.map(g => [g.gpio_number, g])));
            setError(null);
        } catch (err) {
            setError(err.message);
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleUnassign = async (pinNumber) => {
        if (window.confirm(`Снять назначение с GPIO ${pinNumber}?`)) {
            try {
                await unassignGpio(pinNumber);
                fetchData();
            } catch (err) {
                setError(err.message);
            }
        }
    };

    const handleOpenAssignModal = (pin) => {
        setSelectedPin(pin);
        setShowModal(true);
    };

    const handleCloseModal = () => {
        setShowModal(false);
        setSelectedPin(null);
    };

    return (
        <div>
            {/* Заголовок */}
            <div className="d-flex align-items-center justify-content-between mb-4">
                <h2 className="mb-0">⚙️ Настройки GPIO</h2>
                <button
                    className="btn btn-outline-success btn-sm"
                    onClick={fetchData}
                    disabled={loading}
                >
                    {loading
                        ? <span className="spinner-border spinner-border-sm" />
                        : '🔄 Обновить'}
                </button>
            </div>

            {error && (
                <div className="alert alert-danger">❌ Ошибка: {error}</div>
            )}

            {loading ? (
                <div className="text-center py-5">
                    <div className="spinner-border text-success" />
                    <div className="mt-2 text-muted">Загрузка пинов…</div>
                </div>
            ) : (
                <div className="card shadow-sm">
                    <div className="card-body p-0">
                        <table className="table table-hover table-sm mb-0">
                            <thead className="table-dark">
                                <tr>
                                    <th style={{ width: 100 }}>Пин</th>
                                    <th style={{ width: 80 }}>PWM</th>
                                    <th style={{ width: 120 }}>Статус</th>
                                    <th style={{ width: 110 }}>Режим</th>
                                    <th>Описание</th>
                                    <th style={{ width: 130 }} className="text-end">Действие</th>
                                </tr>
                            </thead>
                            <tbody>
                                {allPins.map(pin => {
                                    const gpio = assignedGpios.get(pin.number);
                                    const pinWithData = gpio
                                        ? { ...pin, gpio_description: gpio.gpio_description, gpio_function: gpio.gpio_function }
                                        : pin;
                                    const isHwPwm = pin.supports_hw_pwm ?? HW_PWM_PINS.has(pin.number);

                                    return (
                                        <tr key={pin.number} className={isHwPwm ? 'table-warning' : undefined}>
                                            <td className="fw-semibold font-monospace">
                                                GPIO {pin.number}
                                            </td>
                                            <td>
                                                <PwmBadge pin={pin} />
                                            </td>
                                            <td>
                                                {gpio
                                                    ? <span className="badge bg-success">✅ Назначен</span>
                                                    : <span className="badge bg-secondary">Свободен</span>}
                                            </td>
                                            <td>
                                                {gpio ? <FuncBadge func={gpio.gpio_function} /> : <span className="text-muted small">—</span>}
                                            </td>
                                            <td className="text-truncate" style={{ maxWidth: 240 }}>
                                                {gpio
                                                    ? <span>{gpio.gpio_description}</span>
                                                    : <span className="text-muted small fst-italic">не назначено</span>}
                                            </td>
                                            <td className="text-end">
                                                {gpio ? (
                                                    <div className="btn-group btn-group-sm">
                                                        <button
                                                            className="btn btn-outline-success"
                                                            onClick={() => handleOpenAssignModal(pinWithData)}
                                                            title="Изменить"
                                                        >
                                                            ✏️
                                                        </button>
                                                        <button
                                                            className="btn btn-outline-danger"
                                                            onClick={() => handleUnassign(pin.number)}
                                                            title="Снять назначение"
                                                        >
                                                            ✕
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <button
                                                        className="btn btn-success btn-sm"
                                                        onClick={() => handleOpenAssignModal(pinWithData)}
                                                    >
                                                        + Назначить
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Легенда */}
            {!loading && (
                <div className="mt-3 d-flex flex-wrap gap-3 text-muted small">
                    <span>
                        <span className="badge bg-warning text-dark me-1">〜 HW</span>
                        Аппаратный PWM (GPIO 12, 13, 18, 19)
                    </span>
                    <span>
                        <span className="badge bg-primary me-1">⬆ OUTPUT</span>
                        Цифровой выход
                    </span>
                    <span>
                        <span className="badge bg-info text-dark me-1">⬇ INPUT</span>
                        Цифровой вход
                    </span>
                    <span>
                        <span className="badge bg-warning text-dark me-1">〜 PWM</span>
                        ШИМ-выход
                    </span>
                </div>
            )}

            <AssignModal
                pin={selectedPin}
                show={showModal}
                onClose={handleCloseModal}
                onAssign={fetchData}
            />
        </div>
    );
}

export default PortsSettingsPage;
