import React, { useState, useEffect, useCallback } from 'react';
import { getGpioInfo } from '../services/api';

// Человекочитаемые названия полей
const FIELD_LABELS = {
    model:        { label: 'Модель',         icon: '🖥️' },
    revision:     { label: 'Ревизия платы',  icon: '🔖' },
    pcb_revision: { label: 'PCB ревизия',    icon: '🔩' },
    ram:          { label: 'ОЗУ',            icon: '💾' },
    processor:    { label: 'Процессор',      icon: '⚙️' },
    manufacturer: { label: 'Производитель',  icon: '🏭' },
};

// Системная информация через /proc (запрашивается отдельно через API)
function InfoRow({ icon, label, value, mono = false }) {
    return (
        <tr>
            <td className="text-muted" style={{ width: '40%' }}>
                <span className="me-1">{icon}</span>{label}
            </td>
            <td className={mono ? 'font-monospace' : ''}>
                {value ?? <span className="text-muted fst-italic">нет данных</span>}
            </td>
        </tr>
    );
}

function StatusBadge({ value }) {
    if (value === 'MOCK') {
        return <span className="badge bg-secondary">Mock (не Pi)</span>;
    }
    return <span className="badge bg-success">Raspberry Pi</span>;
}

export default function RaspberryInfoPage() {
    const [info, setInfo]       = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError]     = useState(null);
    const [sysInfo, setSysInfo] = useState(null);
    const [sysLoading, setSysLoading] = useState(true);

    const fetchInfo = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getGpioInfo();
            setInfo(data);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Дополнительная системная информация через /gpio/sysinfo
    const fetchSysInfo = useCallback(async () => {
        setSysLoading(true);
        try {
            const res = await fetch('/gpio/sysinfo');
            if (res.ok) setSysInfo(await res.json());
        } catch (_) {}
        finally { setSysLoading(false); }
    }, []);

    useEffect(() => {
        fetchInfo();
        fetchSysInfo();
    }, [fetchInfo, fetchSysInfo]);

    const isMock = info?.revision === 'MOCK';

    return (
        <div>
            <div className="d-flex align-items-center justify-content-between mb-4">
                <h2 className="mb-0">🍓 Raspberry Pi — информация</h2>
                <button
                    className="btn btn-outline-success btn-sm"
                    onClick={() => { fetchInfo(); fetchSysInfo(); }}
                    disabled={loading}
                >
                    {loading ? <span className="spinner-border spinner-border-sm" /> : '🔄 Обновить'}
                </button>
            </div>

            {error && (
                <div className="alert alert-danger">
                    ❌ Ошибка загрузки: {error}
                </div>
            )}

            <div className="row g-4">

                {/* ── Карточка платы ─────────────────────────────────── */}
                <div className="col-lg-6">
                    <div className="card h-100 shadow-sm">
                        <div className="card-header bg-danger text-white fw-semibold">
                            🖥️ Информация о плате
                        </div>
                        <div className="card-body p-0">
                            {loading ? (
                                <div className="text-center p-4">
                                    <div className="spinner-border text-danger" />
                                </div>
                            ) : (
                                <table className="table table-sm table-hover mb-0">
                                    <tbody>
                                        <tr>
                                            <td className="text-muted" style={{ width: '40%' }}>
                                                <span className="me-1">📟</span>Тип устройства
                                            </td>
                                            <td><StatusBadge value={info?.revision} /></td>
                                        </tr>
                                        {Object.entries(FIELD_LABELS).map(([key, meta]) => (
                                            <InfoRow
                                                key={key}
                                                icon={meta.icon}
                                                label={meta.label}
                                                value={info?.[key]}
                                                mono={key === 'revision' || key === 'pcb_revision'}
                                            />
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </div>

                {/* ── Системная информация ───────────────────────────── */}
                <div className="col-lg-6">
                    <div className="card h-100 shadow-sm">
                        <div className="card-header bg-primary text-white fw-semibold">
                            📊 Системная информация
                        </div>
                        <div className="card-body p-0">
                            {sysLoading ? (
                                <div className="text-center p-4">
                                    <div className="spinner-border text-primary" />
                                </div>
                            ) : sysInfo ? (
                                <table className="table table-sm table-hover mb-0">
                                    <tbody>
                                        <InfoRow icon="🌡️" label="Температура CPU"
                                            value={sysInfo.cpu_temp != null
                                                ? <span className={`fw-bold ${sysInfo.cpu_temp > 70 ? 'text-danger' : sysInfo.cpu_temp > 55 ? 'text-warning' : 'text-success'}`}>
                                                    {sysInfo.cpu_temp.toFixed(1)} °C
                                                </span>
                                                : null}
                                        />
                                        <InfoRow icon="⚡" label="Напряжение CPU"
                                            value={sysInfo.cpu_voltage != null ? `${sysInfo.cpu_voltage} В` : null}
                                        />
                                        <InfoRow icon="🕐" label="Uptime"
                                            value={sysInfo.uptime}
                                        />
                                        <InfoRow icon="💻" label="Загрузка CPU"
                                            value={sysInfo.cpu_usage != null
                                                ? <div>
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="progress flex-grow-1" style={{ height: 8 }}>
                                                            <div
                                                                className={`progress-bar ${sysInfo.cpu_usage > 80 ? 'bg-danger' : sysInfo.cpu_usage > 50 ? 'bg-warning' : 'bg-success'}`}
                                                                style={{ width: `${sysInfo.cpu_usage}%` }}
                                                            />
                                                        </div>
                                                        <span className="small fw-bold">{sysInfo.cpu_usage.toFixed(1)}%</span>
                                                    </div>
                                                </div>
                                                : null}
                                        />
                                        <InfoRow icon="💾" label="ОЗУ использовано"
                                            value={sysInfo.ram_used != null
                                                ? <div>
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="progress flex-grow-1" style={{ height: 8 }}>
                                                            <div
                                                                className={`progress-bar ${sysInfo.ram_percent > 85 ? 'bg-danger' : sysInfo.ram_percent > 60 ? 'bg-warning' : 'bg-info'}`}
                                                                style={{ width: `${sysInfo.ram_percent}%` }}
                                                            />
                                                        </div>
                                                        <span className="small fw-bold">{sysInfo.ram_percent?.toFixed(0)}%</span>
                                                    </div>
                                                    <div className="text-muted small mt-1">
                                                        {sysInfo.ram_used} / {sysInfo.ram_total}
                                                    </div>
                                                </div>
                                                : null}
                                        />
                                        <InfoRow icon="💿" label="Диск /"
                                            value={sysInfo.disk_used != null
                                                ? <div>
                                                    <div className="d-flex align-items-center gap-2">
                                                        <div className="progress flex-grow-1" style={{ height: 8 }}>
                                                            <div
                                                                className={`progress-bar ${sysInfo.disk_percent > 90 ? 'bg-danger' : sysInfo.disk_percent > 70 ? 'bg-warning' : 'bg-success'}`}
                                                                style={{ width: `${sysInfo.disk_percent}%` }}
                                                            />
                                                        </div>
                                                        <span className="small fw-bold">{sysInfo.disk_percent?.toFixed(0)}%</span>
                                                    </div>
                                                    <div className="text-muted small mt-1">
                                                        {sysInfo.disk_used} / {sysInfo.disk_total}
                                                    </div>
                                                </div>
                                                : null}
                                        />
                                        <InfoRow icon="🌐" label="IP адреса"
                                            value={sysInfo.ip_addresses?.join(', ')}
                                            mono
                                        />
                                        <InfoRow icon="🔧" label="Ядро ОС"
                                            value={sysInfo.kernel}
                                            mono
                                        />
                                        <InfoRow icon="🐧" label="ОС"
                                            value={sysInfo.os_name}
                                        />
                                    </tbody>
                                </table>
                            ) : (
                                <div className="text-center p-4 text-muted">
                                    <div className="fs-1">📊</div>
                                    <div>Системная информация недоступна</div>
                                    <div className="small mt-1">Эндпоинт /gpio/sysinfo не отвечает</div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* ── GPIO PWM пины ──────────────────────────────────── */}
                {!loading && (
                    <div className="col-12">
                        <div className="card shadow-sm">
                            <div className="card-header bg-warning text-dark fw-semibold">
                                〜 Аппаратные PWM пины
                            </div>
                            <div className="card-body">
                                {isMock ? (
                                    <div className="text-muted fst-italic">
                                        Запущено в режиме эмуляции — данные о пинах недоступны.
                                    </div>
                                ) : (
                                    <>
                                        <p className="text-muted small mb-3">
                                            Эти пины поддерживают аппаратный ШИМ с минимальным джиттером.
                                            Для активации аппаратного PWM установите <code>pigpio</code> и
                                            раскомментируйте <code>PiGPIOFactory</code> в <code>gpio.py</code>.
                                        </p>
                                        <div className="d-flex flex-wrap gap-2">
                                            {(info?.hw_pwm_pins || []).map((pin) => (
                                                <div key={pin} className="text-center">
                                                    <div
                                                        className="badge bg-warning text-dark fs-6 px-3 py-2"
                                                        style={{ minWidth: 70 }}
                                                    >
                                                        GPIO {pin}
                                                    </div>
                                                    <div className="text-muted small mt-1">
                                                        {pin === 12 && 'PWM0 / пин 32'}
                                                        {pin === 13 && 'PWM1 / пин 33'}
                                                        {pin === 18 && 'PWM0 / пин 12'}
                                                        {pin === 19 && 'PWM1 / пин 35'}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Mock-предупреждение ────────────────────────────── */}
                {!loading && isMock && (
                    <div className="col-12">
                        <div className="alert alert-warning d-flex align-items-start gap-2 mb-0">
                            <span className="fs-4">⚠️</span>
                            <div>
                                <strong>Режим эмуляции</strong> — бэкенд запущен не на Raspberry Pi
                                (или gpiozero не смог определить плату).
                                GPIO управление работает через mock-классы.
                                На реальном Pi эта страница покажет полную информацию о плате.
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
}
