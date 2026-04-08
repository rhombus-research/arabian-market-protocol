import { useSimulationStore } from '../store/simulationStore';
import type { TickEvent } from '../types/simulation';

// Module-level singleton — survives component unmounts/remounts
let ws: WebSocket | null = null;

function connect(sessionId: string) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/simulation/${sessionId}`);

  ws.onopen = () => {
    useSimulationStore.getState().setRunning(true);
  };

  ws.onmessage = (evt) => {
    const data = JSON.parse(evt.data);
    if (data.type === 'complete') {
      useSimulationStore.getState().setRunning(false);
      return;
    }
    useSimulationStore.getState().pushTick(data as TickEvent);
  };

  ws.onclose = () => {
    useSimulationStore.getState().setRunning(false);
    ws = null;
  };

  ws.onerror = () => {
    useSimulationStore.getState().setRunning(false);
  };
}

function send(action: string, params?: Record<string, unknown>) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action, ...params }));
  }
}

function disconnect() {
  if (ws) {
    ws.close();
    ws = null;
  }
}

export function useSimulationWs() {
  return { connect, send, disconnect };
}
