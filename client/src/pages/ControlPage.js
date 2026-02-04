import React, { useState, useEffect } from 'react';
import { getGpios, setGpioValue } from '../services/api';

function ControlPage() {
    const [gpios, setGpios] = useState([]);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchGpios = async () => {
        try {
            setLoading(true);
            const data = await getGpios();
            setGpios(data);
            setError(null);
        } catch (err) {
            setError(err.message);
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchGpios();
        const interval = setInterval(fetchGpios, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, []);

    const handleToggle = async (pinNumber, currentValue) => {
        try {
            const newValue = currentValue === 1 ? 0 : 1;
            await setGpioValue(pinNumber, newValue);
            // Refresh the GPIO states immediately after toggle
            fetchGpios();
        } catch (err) {
            setError(err.message);
            console.error(err);
        }
    };

    if (loading && gpios.length === 0) {
        return <div>Loading GPIO states...</div>;
    }

    if (error) {
        return <div className="alert alert-danger">Error: {error}</div>;
    }

    return (
        <div>
            <h1>GPIO Control Panel</h1>
            <table className="table table-striped">
                <thead>
                    <tr>
                        <th>GPIO</th>
                        <th>Description</th>
                        <th>Function</th>
                        <th>State</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {gpios.map((gpio) => (
                        <tr key={gpio.gpio_number}>
                            <td>GPIO {gpio.gpio_number}</td>
                            <td>{gpio.gpio_description}</td>
                            <td>{gpio.gpio_function}</td>
                            <td>
                                {gpio.gpio_function === 'OUTPUT' ? (
                                    <span className={`badge ${gpio.value === 1 ? 'bg-success' : 'bg-secondary'}`}>
                                        {gpio.value === 1 ? 'ON' : 'OFF'}
                                    </span>
                                ) : (
                                    <span className="badge bg-light text-dark">{gpio.value}</span>
                                )}
                            </td>
                            <td>
                                {gpio.gpio_function === 'OUTPUT' && (
                                    <button 
                                        className={`btn ${gpio.value === 1 ? 'btn-danger' : 'btn-success'}`}
                                        onClick={() => handleToggle(gpio.gpio_number, gpio.value)}
                                    >
                                        Turn {gpio.value === 1 ? 'OFF' : 'ON'}
                                    </button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default ControlPage;