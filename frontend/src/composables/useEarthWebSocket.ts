/**
 * WebSocket composable — auto-reconnects with exponential backoff.
 * Use in App.vue (or a top-level layout) to keep one connection alive
 * for the whole session.
 */

import { ref, onMounted, onBeforeUnmount } from "vue";
import { useEarthStore } from "@/stores/earth";
import type { WSMessage } from "@/types";

const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;
const PING_INTERVAL_MS = 25000;

export function useEarthWebSocket() {
  const store = useEarthStore();
  const socket = ref<WebSocket | null>(null);
  const reconnectAttempt = ref(0);
  const reconnectTimer = ref<number | null>(null);
  const pingTimer = ref<number | null>(null);

  function wsUrl(): string {
    const base =
      typeof __WS_BASE__ !== "undefined" ? __WS_BASE__ : "/ws";
    if (base.startsWith("ws")) return base;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}${base}`;
  }

  function connect() {
    const url = wsUrl();
    console.log("[ws] connecting to", url);
    const s = new WebSocket(url);
    socket.value = s;

    s.onopen = () => {
      console.log("[ws] connected");
      store.wsConnected = true;
      reconnectAttempt.value = 0;
      // Subscribe to all topics
      s.send(JSON.stringify({ subscribe: ["*"] }));
      // Periodic ping to keep the connection alive
      if (pingTimer.value !== null) {
        clearInterval(pingTimer.value);
      }
      pingTimer.value = window.setInterval(() => {
        if (s.readyState === WebSocket.OPEN) {
          s.send(JSON.stringify({ type: "ping", t: Date.now() }));
        }
      }, PING_INTERVAL_MS);
    };

    s.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data);
        store.ingest(msg);
      } catch (err) {
        console.warn("[ws] bad message", err);
      }
    };

    s.onerror = () => {
      console.warn("[ws] error");
    };

    s.onclose = () => {
      console.log("[ws] closed, will reconnect");
      store.wsConnected = false;
      socket.value = null;
      if (pingTimer.value !== null) {
        clearInterval(pingTimer.value);
        pingTimer.value = null;
      }
      scheduleReconnect();
    };
  }

  function scheduleReconnect() {
    if (reconnectTimer.value !== null) {
      clearTimeout(reconnectTimer.value);
    }
    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(1.6, reconnectAttempt.value),
      RECONNECT_MAX_MS,
    );
    reconnectAttempt.value += 1;
    console.log(`[ws] reconnect in ${Math.round(delay)}ms (attempt ${reconnectAttempt.value})`);
    reconnectTimer.value = window.setTimeout(connect, delay);
  }

  function disconnect() {
    if (reconnectTimer.value !== null) {
      clearTimeout(reconnectTimer.value);
      reconnectTimer.value = null;
    }
    if (pingTimer.value !== null) {
      clearInterval(pingTimer.value);
      pingTimer.value = null;
    }
    if (socket.value) {
      socket.value.close();
      socket.value = null;
    }
  }

  onMounted(() => {
    connect();
    store.bootstrap();
  });

  onBeforeUnmount(disconnect);

  return { socket, reconnectAttempt, disconnect };
}
