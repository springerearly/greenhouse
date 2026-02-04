import React, { useState, useEffect } from 'react';
import { getAllPins, getGpios, unassignGpio } from '../services/api';
import AssignModal from '../components/AssignModal';

function PortsSettingsPage() {
    const [allPins, setAllPins] = useState([]);
    const [assignedGpios, setAssignedGpios] = useState(new Map());
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [selectedPin, setSelectedPin] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [pins, gpios] = await Promise.all([getAllPins(), getGpios()]);
            setAllPins(pins);
            
            const gpioMap = new Map(gpios.map(g => [g.gpio_number, g]));
            setAssignedGpios(gpioMap);

            setError(null);
        } catch (err) {
            setError(err.message);
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleUnassign = async (pinNumber) => {
        if (window.confirm(`Are you sure you want to unassign GPIO ${pinNumber}?`)) {
            try {
                await unassignGpio(pinNumber);
                fetchData(); // Refresh data
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

    const handleAssign = () => {
        fetchData(); // Refresh data after assignment
    }

    if (loading) {
        return <div>Loading pin information...</div>;
    }

    if (error) {
        return <div className="alert alert-danger">Error: {error}</div>;
    }

    return (
        <div>
            <h1>Ports Settings</h1>
            <table className="table">
                <thead>
                    <tr>
                        <th>Pin</th>
                        <th>Status</th>
                        <th>Description</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {allPins.map(pin => {
                        const assignedGpio = assignedGpios.get(pin.number);
                        const pinWithData = { ...pin, ...assignedGpio };

                        return (
                            <tr key={pin.number}>
                                <td>GPIO {pin.number}</td>
                                <td>
                                    {assignedGpio ? (
                                        <span className="badge bg-success">Assigned</span>
                                    ) : (
                                        <span className="badge bg-secondary">Not Assigned</span>
                                    )}
                                </td>
                                <td>{assignedGpio ? assignedGpio.gpio_description : '-'}</td>
                                <td>
                                    {assignedGpio ? (
                                        <button className="btn btn-danger btn-sm" onClick={() => handleUnassign(pin.number)}>
                                            Unassign
                                        </button>
                                    ) : (
                                        <button className="btn btn-primary btn-sm" onClick={() => handleOpenAssignModal(pinWithData)}>
                                            Assign
                                        </button>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
            
            <AssignModal 
                pin={selectedPin}
                show={showModal}
                onClose={handleCloseModal}
                onAssign={handleAssign}
            />
        </div>
    );
}

export default PortsSettingsPage;
