/**
 * React-хук для подписки на WebSocket-события.
 *
 * Пример:
 *   const sensorData = useWebSocket('sensors', 'update', null);
 */

import { useState, useEffect, useRef } from 'react';
import { wsClient } from '../services/websocket';

export function useWebSocket(channel, event, initialValue = null) {
    const [data, setData] = useState(initialValue);
    const handlerRef = useRef(null);

    useEffect(() => {
        handlerRef.current = (payload) => setData(payload);
        wsClient.on(channel, event, handlerRef.current);
        return () => {
            wsClient.off(channel, event, handlerRef.current);
        };
    }, [channel, event]);

    return data;
}

/** Хук для WS-статуса соединения */
export function useWsStatus() {
    const [connected, setConnected] = useState(wsClient.isConnected);

    useEffect(() => {
        const onConnect = () => setConnected(true);
        const onDisconnect = () => setConnected(false);
        wsClient.on('system', 'connected', onConnect);
        wsClient.on('system', 'disconnected', onDisconnect);
        return () => {
            wsClient.off('system', 'connected', onConnect);
            wsClient.off('system', 'disconnected', onDisconnect);
        };
    }, []);

    return connected;
}
