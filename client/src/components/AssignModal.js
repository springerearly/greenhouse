import React, { useState, useEffect } from 'react';
import { setGpioFunction } from '../services/api';

function AssignModal({ pin, show, onClose, onAssign }) {
    const [description, setDescription] = useState('');
    const [func, setFunc] = useState('OUTPUT');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (pin) {
            setDescription(pin.gpio_description || '');
            setFunc(pin.gpio_function || 'OUTPUT');
        }
    }, [pin]);

    if (!show || !pin) {
        return null;
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await setGpioFunction(pin.number, description, func);
            onAssign(); // This will trigger a data refresh in the parent
            onClose(); // Close the modal
        } catch (err) {
            setError(err.message);
        }
    };

    return (
        <div className="modal" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
            <div className="modal-dialog">
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Assign GPIO {pin.number}</h5>
                        <button type="button" className="btn-close" onClick={onClose}></button>
                    </div>
                    <div className="modal-body">
                        {error && <div className="alert alert-danger">{error}</div>}
                        <form onSubmit={handleSubmit}>
                            <div className="mb-3">
                                <label htmlFor="description" className="form-label">Description</label>
                                <input
                                    type="text"
                                    className="form-control"
                                    id="description"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="mb-3">
                                <label htmlFor="function" className="form-label">Function</label>
                                <select
                                    className="form-select"
                                    id="function"
                                    value={func}
                                    onChange={(e) => setFunc(e.target.value)}
                                >
                                    <option value="OUTPUT">OUTPUT</option>
                                    <option value="INPUT">INPUT</option>
                                </select>
                            </div>
                            <div className="modal-footer">
                                <button type="button" className="btn btn-secondary" onClick={onClose}>Close</button>
                                <button type="submit" className="btn btn-primary">Assign</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AssignModal;
