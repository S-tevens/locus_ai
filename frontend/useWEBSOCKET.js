import { useEffect, useRef, useState } from "react";

// Connects to the backend's /ws feed and reconnects automatically if the
// backend restarts or the connection drops.
export function useWebSocket(url, onMessage) {
  const [connected, setConnected] = useState(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let socket;
    let retryTimer;
    let cancelled = false;

    function connect() {
      socket = new WebSocket(url);

      socket.onopen = () => setConnected(true);

      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          retryTimer = setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => socket.close();

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch {
          // ignore malformed frames
        }
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, [url]);

  return connected;
}
