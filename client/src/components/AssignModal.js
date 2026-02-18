import React, { useState, useEffect } from 'react';
import { setGpioFunction } from '../services/api';

// BCM-номера пинов с аппаратным PWM (lgpio на Pi OS Bookworm)
const HW_PWM_PINS = new Set([12, 13, 18, 19]);

const FUNCTION_INFO = {
    OUTPUT: {
        label:  '⬆ OUTPUT — цифровой выход',
        badge:  'bg-primary',
        hint:   'Управляемый цифровой выход: HIGH (1) или LOW (0). Используйте для реле, светодиодов, транзисторных ключей.',
    },
    INPUT: {
        label:  '⬇ INPUT — цифровой вход',
        badge:  'bg-info text-dark',
        hint:   'Читает уровень сигнала (0/1). Изменения приходят в реальном времени через WebSocket. Внутренний pull-up включён.',
    },
    PWM: {
        label:  '〜 PWM — широтно-импульсная модуляция',
        badge:  'bg-warning text-dark',
        hint:   'Аппаратный ШИМ-выход, скважность 0–100%. Управляйте яркостью, скоростью мотора, мощностью нагрева.',
        hintDisabled: 'Доступно только на GPIO 12, 13, 18 и 19 (аппаратный PWM).',
    },
};

function AssignModal({ pin, show, onClose, onAssign }) {
    const [description, setDescription] = useState('');
    const [func, setFunc]               = useState('OUTPUT');
    const [error, setError]             = useState(null);
    const [loading, setLoading]         = useState(false);

    // Поддерживает ли пин аппаратный PWM (из данных бэкенда или fallback по номеру)
    const isHwPwm = pin
        ? (pin.supports_hw_pwm ?? HW_PWM_PINS.has(pin.number))
        : false;

    useEffect(() => {
        if (pin) {
            setDescription(pin.gpio_description || '');
            // Если у пина сохранён PWM но он не поддерживает аппаратный — сбрасываем на OUTPUT
            const savedFunc = pin.gpio_function || 'OUTPUT';
            if (savedFunc === 'PWM' && !isHwPwm) {
                setFunc('OUTPUT');
            } else {
                setFunc(savedFunc);
            }
            setError(null);
        }
    }, [pin, isHwPwm]);

    if (!show || !pin) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        try {
            await setGpioFunction(pin.number, description, func);
            onAssign();
            onClose();
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            className="modal d-block"
            style={{ backgroundColor: 'rgba(0,0,0,0.55)' }}
            onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
        >
            <div className="modal-dialog modal-dialog-centered">
                <div className="modal-content shadow-lg">

                    <div className="modal-header bg-success text-white">
                        <h5 className="modal-title">
                            Назначить GPIO {pin.number}
                            {isHwPwm && (
                                <span className="badge bg-warning text-dark ms-2" title="Поддерживает аппаратный PWM">
                                    〜 HW PWM
                                </span>
                            )}
                        </h5>
                        <button type="button" className="btn-close btn-close-white" onClick={onClose} />
                    </div>

                    <div className="modal-body">
                        {error && (
                            <div className="alert alert-danger py-2">{error}</div>
                        )}

                        <form onSubmit={handleSubmit} id="assignForm">
                            {/* Описание */}
                            <div className="mb-3">
                                <label className="form-label fw-semibold">Описание</label>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Например: Вентилятор зоны A"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    required
                                    autoFocus
                                />
                            </div>

                            {/* Режим */}
                            <div className="mb-3">
                                <label className="form-label fw-semibold">Режим пина</label>
                                <div className="d-flex flex-column gap-2">
                                    {Object.entries(FUNCTION_INFO).map(([key, meta]) => {
                                        const isPwmOption = key === 'PWM';
                                        const disabled = isPwmOption && !isHwPwm;

                                        return (
                                            <label
                                                key={key}
                                                className={`d-flex align-items-start gap-2 p-2 rounded border ${
                                                    disabled
                                                        ? 'border-light bg-light opacity-50'
                                                        : func === key
                                                            ? 'border-success bg-light'
                                                            : 'border-light'
                                                }`}
                                                style={{ cursor: disabled ? 'not-allowed' : 'pointer' }}
                                                title={disabled ? 'Аппаратный PWM доступен только на GPIO 12, 13, 18, 19' : undefined}
                                            >
                                                <input
                                                    type="radio"
                                                    name="func"
                                                    value={key}
                                                    checked={func === key}
                                                    onChange={() => !disabled && setFunc(key)}
                                                    disabled={disabled}
                                                    className="mt-1"
                                                />
                                                <div>
                                                    <span className={`badge ${meta.badge} mb-1`}>
                                                        {meta.label}
                                                    </span>
                                                    <div className="text-muted small">
                                                        {disabled ? meta.hintDisabled : meta.hint}
                                                    </div>
                                                </div>
                                            </label>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Подсказка по аппаратному PWM */}
                            {func === 'PWM' && isHwPwm && (
                                <div className="alert alert-success py-2 small">
                                    <strong>✅ Аппаратный PWM</strong> — GPIO {pin.number} поддерживает
                                    аппаратный ШИМ с минимальным джиттером (lgpio, Pi OS Bookworm).
                                </div>
                            )}
                        </form>
                    </div>

                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={onClose}>
                            Отмена
                        </button>
                        <button
                            type="submit"
                            form="assignForm"
                            className="btn btn-success"
                            disabled={loading}
                        >
                            {loading ? (
                                <><span className="spinner-border spinner-border-sm me-1" />Сохранение…</>
                            ) : (
                                'Назначить'
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AssignModal;
