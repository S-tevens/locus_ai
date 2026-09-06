export const BACKEND_HOST = "127.0.0.1:8000";
export const WS_URL = `ws://${BACKEND_HOST}/ws`;
export const HEALTH_URL = `http://${BACKEND_HOST}/health`;

// Schematic (non-geographic) layout: each zone is a quadrant on a simple
// grid, not a real map. Bounds are [[y1, x1], [y2, x2]] for Leaflet's
// CRS.Simple, where the CSV's `zone_id` values are the keys.
export const ZONES = {
  downtown: { bounds: [[100, 0], [200, 100]], label: "Downtown" },
  hospital_zone: { bounds: [[100, 100], [200, 200]], label: "Hospital Zone" },
  residential: { bounds: [[0, 0], [100, 100]], label: "Residential" },
  arterial_road: { bounds: [[0, 100], [100, 200]], label: "Arterial Road" },
};

export const RISK_COLORS = {
  low: "#3fb950",
  medium: "#d29922",
  high: "#f85149",
  unknown: "#6e7681",
};

export const MAX_EVENTS = 200;
