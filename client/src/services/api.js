// When running in development mode (npm start), the proxy in package.json will handle this.
// In production (Docker), Nginx will proxy requests starting with /gpio.
const API_BASE = '/gpio';

export const getGpios = async () => {
    const response = await fetch(`${API_BASE}/`);
    if (!response.ok) {
        throw new Error('Failed to fetch GPIOs');
    }
    return await response.json();
};

export const getAllPins = async () => {
    const response = await fetch(`${API_BASE}/all-pins`);
    if (!response.ok) {
        throw new Error('Failed to fetch all pins');
    }
    return await response.json();
};

export const setGpioValue = async (pinNumber, value) => {
    const response = await fetch(`${API_BASE}/set-value`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gpio_number: pinNumber, value: value }),
    });
    if (!response.ok) {
        throw new Error('Failed to set GPIO value');
    }
    return await response.json();
};

export const setGpioFunction = async (pinNumber, description, func) => {
    const response = await fetch(`${API_BASE}/set-function`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            gpio_number: pinNumber, 
            gpio_description: description,
            gpio_function: func 
        }),
    });
    if (!response.ok) {
        throw new Error('Failed to set GPIO function');
    }
    return await response.json();
};


export const unassignGpio = async (pinNumber) => {
    const response = await fetch(`${API_BASE}/${pinNumber}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        throw new Error('Failed to unassign GPIO');
    }
    return await response.json();
};