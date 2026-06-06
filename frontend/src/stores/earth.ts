/**
 * Pinia store that holds the latest snapshot of every data source
 * and the WebSocket connection state. The WS composable feeds it,
 * the components read it reactively.
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type {
  Earthquake,
  HealthResponse,
  LightningStrike,
  Satellite,
  SolarSnapshot,
  SourceStatus,
  Volcano,
  Wildfire,
  WSMessage,
} from "@/types";

export const useEarthStore = defineStore("earth", () => {
  // ---- connection state ----
  const wsConnected = ref(false);
  const wsLastMessage = ref<number | null>(null);
  const uptime = ref(0);
  const version = ref("");

  // ---- source snapshots ----
  const sources = ref<Record<string, SourceStatus>>({});
  const counts = ref<Record<string, number>>({});

  // ---- data layers ----
  const satellites = ref<Satellite[]>([]);
  const lightning = ref<LightningStrike[]>([]);
  const earthquakes = ref<Earthquake[]>([]);
  const wildfires = ref<Wildfire[]>([]);
  const volcanoes = ref<Volcano[]>([]);
  const solar = ref<SolarSnapshot | null>(null);

  // ---- UI layer toggles (user-facing) ----
  const layers = ref({
    satellites: true,
    satellitesOrbit: true,
    satellitesLabels: false,
    lightning: true,
    lightningLabels: false,
    earthquakes: true,
    wildfires: true,
    volcanoes: true,
    solar: true,
  });

  const selectedSatelliteId = ref<string | null>(null);
  const selectedEarthquakeId = ref<string | null>(null);
  const selectedWildfireId = ref<string | null>(null);
  const selectedVolcanoId = ref<string | null>(null);

  // ---- derived ----
  const selectedSatellite = computed(() =>
    satellites.value.find((s) => s.id === selectedSatelliteId.value) ?? null,
  );
  const selectedEarthquake = computed(() =>
    earthquakes.value.find((e) => e.id === selectedEarthquakeId.value) ?? null,
  );
  const selectedVolcano = computed(() =>
    volcanoes.value.find((v) => v.id === selectedVolcanoId.value) ?? null,
  );

  const prominentSatellites = computed(() => {
    const headliners = ["ISS", "TIANGONG", "HUBBLE", "JAMES WEBB"];
    return satellites.value.filter((s) =>
      headliners.some((h) => s.name.toUpperCase().includes(h)),
    );
  });

  const recentLightningCount = computed(() => {
    const cutoff = Date.now() - 5 * 60 * 1000;
    return lightning.value.filter((s) => new Date(s.time).getTime() >= cutoff).length;
  });

  const bigEarthquakes = computed(() =>
    earthquakes.value.filter((e) => e.mag >= 4.5).slice(0, 20),
  );

  const eruptingVolcanoes = computed(() =>
    volcanoes.value.filter((v) => v.activity_level === "erupting"),
  );

  // ---- WS ingestion ----
  function ingest(msg: WSMessage) {
    wsLastMessage.value = Date.now();
    switch (msg.topic) {
      case "meta":
        if (msg.data) {
          const data = msg.data as {
            status: Record<string, SourceStatus>;
            counts: Record<string, number>;
          };
          sources.value = data.status;
          counts.value = data.counts;
        }
        break;
      case "lightning":
        lightning.value = (msg.data as LightningStrike[]) ?? [];
        break;
      case "satellites":
        satellites.value = (msg.data as Satellite[]) ?? [];
        break;
      case "earth":
        if (msg.data) {
          const data = msg.data as {
            earthquakes: Earthquake[];
            wildfires: Wildfire[];
            volcanoes: Volcano[];
          };
          if (data.earthquakes) earthquakes.value = data.earthquakes;
          if (data.wildfires) wildfires.value = data.wildfires;
          if (data.volcanoes) volcanoes.value = data.volcanoes;
        }
        break;
      case "solar":
        solar.value = (msg.data as SolarSnapshot) ?? null;
        break;
    }
  }

  // ---- initial REST bootstrap (so the page is never empty) ----
  async function bootstrap() {
    try {
      const apiBase =
        typeof __API_BASE__ !== "undefined" ? __API_BASE__ : "/api";
      const r = await fetch(`${apiBase}/meta`);
      if (r.ok) {
        const data = await r.json();
        sources.value = data.status || {};
        counts.value = data.counts || {};
      }
      const h = await fetch(`${apiBase}/../healthz`);
      if (h.ok) {
        const data = (await h.json()) as HealthResponse;
        uptime.value = data.uptime_seconds;
        version.value = data.version;
        sources.value = data.sources;
        counts.value = data.counts;
      }
    } catch (err) {
      console.warn("[earth] bootstrap failed", err);
    }
  }

  function toggleLayer(name: keyof typeof layers.value) {
    layers.value[name] = !layers.value[name];
  }

  return {
    // state
    wsConnected,
    wsLastMessage,
    uptime,
    version,
    sources,
    counts,
    satellites,
    lightning,
    earthquakes,
    wildfires,
    volcanoes,
    solar,
    layers,
    selectedSatelliteId,
    selectedEarthquakeId,
    selectedWildfireId,
    selectedVolcanoId,
    // derived
    selectedSatellite,
    selectedEarthquake,
    selectedVolcano,
    prominentSatellites,
    recentLightningCount,
    bigEarthquakes,
    eruptingVolcanoes,
    // actions
    ingest,
    bootstrap,
    toggleLayer,
  };
});
