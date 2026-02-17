import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getGpios, setGpioValue, setGpioPwm } from '../services/api';
import { useWebSocket, useWsStatus } from '../hooks/useWebSocket';

// Дебаунс для слайдера: не отправлять запрос на каждое движение мышью
function useDebounce(value, delay) {
    const [debounced, setDebounced] = useState(value);
    useEffect(() => {
        const t = setTimeout(() => setDebounced(value), delay);
        return () => clearTimeout(t);
    }, [value, delay]);
    return debounced;
}

// Виджет PWM-слайдера для одного пина
function PwmSlider({ gpio, onPwmChange }) {
    // Внутреннее состояние — проценты (0–100) для плавного UI
    const [pct, setPct] = useState(
        gpio.pwm_value !== null && gpio.pwm_value !== undefined
            ? Math.round(gpio.pwm_value * 100)
            : 0
    );
    const debouncedPct = useDebounce(pct, 80); // 80мс дебаунс
    const prevDebRef   = useRef(debouncedPct);

    // Когда WS приходит обновление от другого клиента — синхронизируем слайдер
    useEffect(() => {
        if (gpio.pwm_value !== null && gpio.pwm_value !== undefined) {
            const fromServer = Math.round(gpio.pwm_value * 100);
            if (Math.abs(fromServer - pct) > 2) setPct(fromServer);
        }
    }, [gpio.pwm_value]); // eslint-disable-line

    // Отправляем на сервер только когда дебаунс устаканился
    useEffect(() => {
        if (debouncedPct !== prevDebRef.current) {
            prevDebRef.current = debouncedPct;
            onPwmChange(gpio.gpio_number, debouncedPct / 100);
        }
    }, [debouncedPct]); // eslint-disable-line

    const color = pct === 0 ? '#6c757d' : pct < 30 ? '#198754' : pct < 70 ? '#ffc107' : '#dc3545';

    return (
        <div className="d-flex align-items-center gap-2" style={{ minWidth: 200 }}>
            <input
                type="range"
                className="form-range flex-grow-1"
                min={0} max={100} step={1}
                value={pct}
                onChange={(e) => setPct(parseInt(e.target.value))}
                style={{ accentColor: color }}
            />
            <span
                className="badge fw-bold"
                style={{ backgroundColor: color, minWidth: 48, fontSize: '0.9rem' }}
            >
                {pct}%
            </span>
            {/* Быстрые кнопки */}
            <div className="btn-group btn-group-sm">
                {[0, 25, 50, 75, 100].map((v) => (
                    <button
                        key={v}
                        className={`btn btn-outline-secondary py-0 px-1`}
                        style={{ fontSize: '0.7rem' }}
                        onClick={() => setPct(v)}
                    >{v}</button>
                ))}
            </div>
        </div>
    );
}

// Виджет INPUT-пина с мигающим индикатором
function InputIndicator({ value }) {
    const isHigh = value === 1;
    return (
        <div className="d-flex align-items-center gap-2">
            <span
                style={{
                    display: 'inline-block',
                    width: 14, height: 14,
                    borderRadius: '50%',
                    backgroundColor: isHigh ? '#198754' : '#6c757d',
                    boxShadow: isHigh ? '0 0 6px 2px #19875488' : 'none',
                    transition: 'background-color 0.1s, box-shadow 0.1s',
                }}
            />
            <span className={`badge ${isHigh ? 'bg-success' : 'bg-secondary'}`}>
                {isHigh ? 'HIGH (1)' : 'LOW (0)'}
            </span>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────

function ControlPage() {
    const [gpios, setGpios]     = useState([]);
    const [error, setError]     = useState(null);
    const [loading, setLoading] = useState(true);
    const wsConnected           = useWsStatus();

    // Live обновления состояния GPIO через WebSocket
    const wsEvent = useWebSocket('gpio', 'state_change', null);

    // При WS-событии обновляем только нужный пин, не перезагружаем весь список
    useEffect(() => {
        if (!wsEvent) return;
        setGpios((prev) =>
            prev.map((g) => {
                if (g.gpio_number !== wsEvent.pin) return g;
                if (wsEvent.function === 'PWM') {
                    return { ...g, pwm_value: wsEvent.value, value: wsEvent.value };
                }
                return { ...g, value: wsEvent.value };
            })
        );
    }, [wsEvent]);

    const fetchGpios = useCallback(async () => {
        try {
            const data = await getGpios();
            setGpios(data);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Первичная загрузка; WS заменяет polling — интервал убираем
    useEffect(() => {
        fetchGpios();
    }, [fetchGpios]);

    const handleToggle = async (pinNumber, currentValue) => {
        try {
            await setGpioValue(pinNumber, currentValue === 1 ? 0 : 1);
            // WS пуш придёт сам; для надёжности тоже обновим локально
        } catch (err) {
            setError(err.message);
        }
    };

    const handlePwm = async (pinNumber, value) => {
        try {
            await setGpioPwm(pinNumber, value);
        } catch (err) {
            setError(err.message);
        }
    };

    if (loading) {
        return (
            <div className="text-center mt-5">
                <div className="spinner-border text-success" />
                <div className="mt-2 text-muted">Загрузка состояния GPIO…</div>
            </div>
        );
    }

    return (
        <div>
            {/* Шапка */}
            <div className="d-flex align-items-center justify-content-between mb-3">
                <h2 className="mb-0">🔌 GPIO Панель управления</h2>
                <div className="d-flex align-items-center gap-2">
                    <span
                        className={`badge ${wsConnected ? 'bg-success' : 'bg-warning text-dark'}`}
                        title={wsConnected ? 'Live обновления активны' : 'Нет WS — нажмите Обновить'}
                    >
                        {wsConnected ? '● Live' : '○ Polling'}
                    </span>
                    <button className="btn btn-sm btn-outline-secondary" onClick={fetchGpios}>
                        🔄 Обновить
                    </button>
                </div>
            </div>

            {error && (
                <div className="alert alert-danger alert-dismissible">
                    {error}
                    <button className="btn-close" onClick={() => setError(null)} />
                </div>
            )}

            {gpios.length === 0 ? (
                <div className="alert alert-info">
                    Нет настроенных GPIO.
                    Перейдите в <a href="/settings">GPIO Настройки</a> чтобы назначить пины.
                </div>
            ) : (
                <div className="table-responsive">
                    <table className="table table-hover align-middle">
                        <thead className="table-light">
                            <tr>
                                <th style={{ width: 100 }}>Пин</th>
                                <th>Описание</th>
                                <th style={{ width: 110 }}>Режим</th>
                                <th style={{ width: 180 }}>Состояние</th>
                                <th>Управление</th>
                            </tr>
                        </thead>
                        <tbody>
                            {gpios.map((gpio) => (
                                <tr key={gpio.gpio_number}>

                                    {/* Пин */}
                                    <td>
                                        <span className="badge bg-dark fs-6">
                                            GPIO {gpio.gpio_number}
                                        </span>
                                    </td>

                                    {/* Описание */}
                                    <td>{gpio.gpio_description}</td>

                                    {/* Режим */}
                                    <td>
                                        {gpio.gpio_function === 'INPUT' && (
                                            <span className="badge bg-info text-dark">⬇ INPUT</span>
                                        )}
                                        {gpio.gpio_function === 'OUTPUT' && (
                                            <span className="badge bg-primary">⬆ OUTPUT</span>
                                        )}
                                        {gpio.gpio_function === 'PWM' && (
                                            <span className="badge bg-warning text-dark">〜 PWM</span>
                                        )}
                                    </td>

                                    {/* Состояние */}
                                    <td>
                                        {gpio.gpio_function === 'INPUT' && (
                                            <InputIndicator value={gpio.value} />
                                        )}
                                        {gpio.gpio_function === 'OUTPUT' && (
                                            <span
                                                className={`badge ${gpio.value === 1 ? 'bg-success' : 'bg-secondary'}`}
                                                style={{ fontSize: '0.95rem' }}
                                            >
                                                {gpio.value === 1 ? 'ON' : 'OFF'}
                                            </span>
                                        )}
                                        {gpio.gpio_function === 'PWM' && (
                                            <span className="text-muted small">
                                                {gpio.pwm_value !== null && gpio.pwm_value !== undefined
                                                    ? `${Math.round(gpio.pwm_value * 100)}%`
                                                    : '—'}
                                            </span>
                                        )}
                                    </td>

                                    {/* Управление */}
                                    <td>
                                        {gpio.gpio_function === 'INPUT' && (
                                            <span className="text-muted small fst-italic">
                                                Только чтение
                                            </span>
                                        )}

                                        {gpio.gpio_function === 'OUTPUT' && (
                                            <button
                                                className={`btn btn-sm ${gpio.value === 1 ? 'btn-danger' : 'btn-success'}`}
                                                onClick={() => handleToggle(gpio.gpio_number, gpio.value)}
                                            >
                                                {gpio.value === 1 ? '■ Выкл' : '▶ Вкл'}
                                            </button>
                                        )}

                                        {gpio.gpio_function === 'PWM' && (
                                            <PwmSlider
                                                gpio={gpio}
                                                onPwmChange={handlePwm}
                                            />
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Легенда */}
            <div className="mt-3 d-flex gap-3 text-muted small">
                <span><span className="badge bg-info text-dark">⬇ INPUT</span> — цифровой вход, live через WebSocket</span>
                <span><span className="badge bg-primary">⬆ OUTPUT</span> — цифровой выход</span>
                <span><span className="badge bg-warning text-dark">〜 PWM</span> — ШИМ 0–100%</span>
            </div>
        </div>
    );
}

export default ControlPage;
