// В dev-режиме proxy в package.json перенаправляет на localhost:8000
// В production Nginx проксирует /gpio, /devices, /sensors, /automations, /alerts -> api:8000

const BASE = '';

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function request(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
}

// ─── GPIO ────────────────────────────────────────────────────────────────────

export const getGpios = () => request(`${BASE}/gpio/`);
export const getAllPins = () => request(`${BASE}/gpio/all-pins`);
export const getGpioInfo = () => request(`${BASE}/gpio/info`);

export const setGpioValue = (pinNumber, value) =>
    request(`${BASE}/gpio/set-value`, {
        method: 'POST',
        body: JSON.stringify({ gpio_number: pinNumber, value }),
    });

export const setGpioFunction = (pinNumber, description, func) =>
    request(`${BASE}/gpio/set-function`, {
        method: 'POST',
        body: JSON.stringify({
            gpio_number: pinNumber,
            gpio_description: description,
            gpio_function: func,
        }),
    });

export const unassignGpio = (pinNumber) =>
    request(`${BASE}/gpio/${pinNumber}`, { method: 'DELETE' });

// value: 0.0 – 1.0 (или 0–100, бэкенд нормализует)
export const setGpioPwm = (pinNumber, value) =>
    request(`${BASE}/gpio/set-pwm`, {
        method: 'POST',
        body: JSON.stringify({ gpio_number: pinNumber, value }),
    });


// ─── Devices ─────────────────────────────────────────────────────────────────

export const getDevices = () => request(`${BASE}/devices/`);
export const getDevice = (id) => request(`${BASE}/devices/${id}`);

export const createDevice = (data) =>
    request(`${BASE}/devices/`, { method: 'POST', body: JSON.stringify(data) });

export const updateDevice = (id, data) =>
    request(`${BASE}/devices/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const deleteDevice = (id) =>
    request(`${BASE}/devices/${id}`, { method: 'DELETE' });

export const pollDeviceNow = (id) =>
    request(`${BASE}/devices/${id}/poll`, { method: 'POST' });

export const controlDevice = (id, command) =>
    request(`${BASE}/devices/${id}/control`, {
        method: 'POST',
        body: JSON.stringify(command),
    });

export const getDeviceHwInfo = (id) => request(`${BASE}/devices/${id}/info`);


// ─── Sensors ─────────────────────────────────────────────────────────────────

export const getLatestReadings = (deviceId) => {
    const q = deviceId !== undefined ? `?device_id=${deviceId}` : '';
    return request(`${BASE}/sensors/latest${q}`);
};

export const getSensorHistory = (deviceId, sensorType, hours = 24) =>
    request(`${BASE}/sensors/history?device_id=${deviceId}&sensor_type=${sensorType}&hours=${hours}`);

export const getSensorStats = (deviceId, sensorType, hours = 24) =>
    request(`${BASE}/sensors/stats?device_id=${deviceId}&sensor_type=${sensorType}&hours=${hours}`);


// ─── Automations ─────────────────────────────────────────────────────────────

export const getAutomations = () => request(`${BASE}/automations/`);

export const createAutomation = (data) =>
    request(`${BASE}/automations/`, { method: 'POST', body: JSON.stringify(data) });

export const updateAutomation = (id, data) =>
    request(`${BASE}/automations/${id}`, { method: 'PUT', body: JSON.stringify(data) });

export const deleteAutomation = (id) =>
    request(`${BASE}/automations/${id}`, { method: 'DELETE' });


// ─── Alerts ──────────────────────────────────────────────────────────────────

export const getAlerts = (unacknowledgedOnly = false) =>
    request(`${BASE}/alerts/?unacknowledged_only=${unacknowledgedOnly}`);

export const getAlertCounts = () => request(`${BASE}/alerts/count`);

export const acknowledgeAlert = (id) =>
    request(`${BASE}/alerts/${id}/acknowledge`, { method: 'POST' });

export const acknowledgeAll = () =>
    request(`${BASE}/alerts/acknowledge-all`, { method: 'POST' });
