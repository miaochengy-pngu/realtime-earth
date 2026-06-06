// TypeScript mirror of the backend's Pydantic models.
// Keep this in sync with backend/app/models/schemas.py.

export type SatelliteCategory =
  | "stations"
  | "starlink"
  | "hubble"
  | "webb"
  | "scientific"
  | "weather"
  | "amateur"
  | "other";

export interface SatellitePosition {
  lat: number;
  lon: number;
  alt_km: number;
  velocity_kms: number;
}

export interface Satellite {
  id: string;
  name: string;
  category: SatelliteCategory;
  line1: string;
  line2: string;
  epoch: string;
  intl_designator?: string | null;
  launched?: string | null;
  position: SatellitePosition | null;
}

export interface LightningStrike {
  id: string;
  time: string;
  lat: number;
  lon: number;
  alt_km: number;
  polarity: "positive" | "negative" | "unknown";
  amplitude_ka: number | null;
  strike_type: "cg" | "cc" | "ic" | "unknown";
  region: string | null;
}

export interface Earthquake {
  id: string;
  mag: number;
  place: string;
  time: string;
  lat: number;
  lon: number;
  depth_km: number;
  url: string;
  event_type: string;
  tsunami: boolean;
  felt: number | null;
  alert: "green" | "yellow" | "orange" | "red" | null;
  significance?: number | null;
  mmi?: number | null;
}

export interface Wildfire {
  id: string;
  lat: number;
  lon: number;
  brightness_k: number;
  scan_km: number;
  track_km: number;
  acq_date: string;
  acq_time: string;
  acq_datetime: string;
  satellite: string;
  instrument: string;
  confidence: "low" | "nominal" | "high";
  frp_mw: number;
  daynight: "D" | "N";
  bright_ti4?: number | null;
  bright_ti5?: number | null;
}

export interface Volcano {
  id: string;
  name: string;
  country: string;
  region: string;
  lat: number;
  lon: number;
  elevation_m: number;
  activity_level: "unknown" | "normal" | "elevated" | "erupting";
  last_known_eruption: string | null;
  last_update: string | null;
  vei?: number | null;
}

export interface SolarSnapshot {
  timestamp: string;
  kp_index: number | null;
  kp_text: string | null;
  solar_wind_speed_kms: number | null;
  solar_wind_density_pcm3: number | null;
  sunspot_number: number | null;
  xray_class: string | null;
  aurora_probability_north: number | null;
  aurora_probability_south: number | null;
  sdo_image_url: string | null;
  sdo_image_timestamp: string | null;
}

export interface SourceStatus {
  ok: boolean;
  error: string | null;
  items: number;
  last_updated: string | null;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  uptime_seconds: number;
  sources: Record<string, SourceStatus>;
  counts: Record<string, number>;
}

export type WSTopic =
  | "hello"
  | "subscribed"
  | "meta"
  | "lightning"
  | "satellites"
  | "earth"
  | "solar";

export interface WSMessage<T = unknown> {
  topic: WSTopic;
  t?: number;
  subs?: string[];
  data?: T;
}
