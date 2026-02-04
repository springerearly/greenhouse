const API_URL = 'http://localhost:8000'; // This will be proxied by React dev server in development

// In production, the Nginx container will handle the proxying.
// We can use a relative URL.
const getApiUrl = () => {
    return process.env.NODE_ENV === 'development'
      ? API_URL
      : '';
  };

export const getGpios = async () => {
    const response = await fetch(`${getApiUrl()}/gpio/`);
    if (!response.ok) {
        throw new Error('Failed to fetch GPIOs');
    }
    return await response.json();
};

export const getAllPins = async () => {
    const response = await fetch(`${getApiUrl()}/gpio/all-pins`);
    if (!response.ok) {
        throw new Error('Failed to fetch all pins');
    }
    return await response.json();
};

export const setGpioValue = async (pinNumber, value) => {
    const response = await fetch(`${getApiUrl()}/gpio/set-value`, {
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
    const response = await fetch(`${getApiUrl()}/gpio/set-function`, {
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
    const response = await fetch(`${getApiUrl()}/gpio/${pinNumber}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        throw new Error('Failed to unassign GPIO');
    }
    return await response.json();
};
