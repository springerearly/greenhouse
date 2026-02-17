/**
 * WebSocket singleton-клиент.
 *
 * Использование:
 *   import { wsClient } from './services/websocket';
 *
 *   wsClient.subscribe(['sensors', 'alerts']);
 *   wsClient.on('sensors', 'update', (data) => console.log(data));
 *   wsClient.off('sensors', 'update', handler);
 */

const WS_URL =
    process.env.NODE_ENV === 'development'
        ? 'ws://localhost:8000/ws'
        : `ws://${window.location.host}/ws`;

const RECONNECT_DELAY_MS = 3000;

class WebSocketClient {
    constructor() {
        this._ws = null;
        this._channels = [];
        // handlers: { 'channel:event': Set<fn> }
        this._handlers = {};
        this._reconnectTimer = null;
        this._intentionalClose = false;
    }

    connect() {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) return;
        this._intentionalClose = false;
        this._ws = new WebSocket(WS_URL);

        this._ws.onopen = () => {
            console.log('[WS] Connected');
            if (this._channels.length > 0) {
                this._send({ type: 'subscribe', channels: this._channels });
            }
            this._emit('system', 'connected', {});
        };

        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._emit(msg.channel, msg.event, msg.data);
            } catch (e) {
                console.error('[WS] Parse error', e);
            }
        };

        this._ws.onerror = (err) => {
            console.error('[WS] Error', err);
        };

        this._ws.onclose = () => {
            console.log('[WS] Disconnected');
            this._emit('system', 'disconnected', {});
            if (!this._intentionalClose) {
                this._reconnectTimer = setTimeout(
                    () => this.connect(),
                    RECONNECT_DELAY_MS
                );
            }
        };
    }

    disconnect() {
        this._intentionalClose = true;
        clearTimeout(this._reconnectTimer);
        if (this._ws) {
            this._ws.close();
            this._ws = null;
        }
    }

    subscribe(channels) {
        this._channels = channels;
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            this._send({ type: 'subscribe', channels });
        }
    }

    /** Подписаться на событие конкретного канала. */
    on(channel, event, handler) {
        const key = `${channel}:${event}`;
        if (!this._handlers[key]) this._handlers[key] = new Set();
        this._handlers[key].add(handler);
    }

    /** Отписаться от события. */
    off(channel, event, handler) {
        const key = `${channel}:${event}`;
        if (this._handlers[key]) this._handlers[key].delete(handler);
    }

    ping() {
        this._send({ type: 'ping' });
    }

    _send(obj) {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
            this._ws.send(JSON.stringify(obj));
        }
    }

    _emit(channel, event, data) {
        const key = `${channel}:${event}`;
        if (this._handlers[key]) {
            this._handlers[key].forEach((fn) => fn(data));
        }
        // Также вызываем универсальные слушатели '*:event' и 'channel:*'
        const star1 = `*:${event}`;
        const star2 = `${channel}:*`;
        [star1, star2].forEach((k) => {
            if (this._handlers[k]) {
                this._handlers[k].forEach((fn) => fn({ channel, event, data }));
            }
        });
    }

    get isConnected() {
        return this._ws && this._ws.readyState === WebSocket.OPEN;
    }
}

export const wsClient = new WebSocketClient();
