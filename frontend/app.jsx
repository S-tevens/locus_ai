import { useEffect, useMemo, useState, useCallback } from "react";
import { useWebSocket } from "./useWebSocket.js";
import { WS_URL, HEALTH_URL, MAX_EVENTS } from "./config.js";
import ZoneMap from "./components/ZoneMap.jsx";
import EventFeed from "./components/EventFeed.jsx";
import StatBar from "./components/StatBar.jsx";
import Clock from "./components/Clock.jsx";

export default function App() {
  const [events, setEvents] = useState([]);
  const [zoneState, setZoneState] = useState({});
  const [health, setHealth] = useState(null);

  const handleMessage = useCallback((prediction) => {
    const enriched = { ...prediction, receivedAt: Date.now() };
    setEvents((prev) => [enriched, ...prev].slice(0, MAX_EVENTS));
    setZoneState((prev) => ({ ...prev, [prediction.zone_id]: enriched }));
  }, []);

  const connected = useWebSocket(WS_URL, handleMessage);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const res = await fetch(HEALTH_URL);
        const data = await res.json();
        if (!cancelled) setHealth(data);
      } catch {
        if (!cancelled) setHealth(null);
      }
    }
    poll();
    const id = setInterval(poll, 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const stats = useMemo(() => {
    const counts = { total: events.length, high: 0, medium: 0, low: 0 };
    for (const e of events) counts[e.risk_level] = (counts[e.risk_level] ?? 0) + 1;
    return counts;
  }, [events]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <h1>CityShield AI</h1>
          <span className="subtitle">Traffic &amp; Emergency Cyber Risk — Live Dashboard</span>
        </div>
        <Clock />
      </header>

      <main className="app-main">
        <section className="map-panel">
          <ZoneMap zoneState={zoneState} />
        </section>
        <section className="feed-panel">
          <EventFeed events={events} />
        </section>
      </main>

      <StatBar
        connected={connected}
        health={health}
        stats={stats}
        lastEventAt={events[0]?.receivedAt ?? null}
      />
    </div>
  );
}
