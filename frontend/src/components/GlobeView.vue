<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { useEarthStore } from "@/stores/earth";
import type {
  Earthquake,
  LightningStrike,
  Satellite,
  Volcano,
  Wildfire,
} from "@/types";

// Disable Cesium Ion access warning (we don't use Ion assets)
(Cesium as any).Ion.defaultAccessToken = "";

// Color palette
const COLORS = {
  satellite: Cesium.Color.fromCssColorString("#22d3ee"),
  satelliteHi: Cesium.Color.fromCssColorString("#fde047"),
  satelliteStarlink: Cesium.Color.fromCssColorString("#94a3b8"),
  lightningPos: Cesium.Color.fromCssColorString("#f97316"),
  lightningNeg: Cesium.Color.fromCssColorString("#60a5fa"),
  earthquake: Cesium.Color.fromCssColorString("#ef4444"),
  earthquakeBig: Cesium.Color.fromCssColorString("#dc2626"),
  wildfire: Cesium.Color.fromCssColorString("#f59e0b"),
  volcanoErupt: Cesium.Color.fromCssColorString("#dc2626"),
  volcanoElev: Cesium.Color.fromCssColorString("#f59e0b"),
  volcanoNormal: Cesium.Color.fromCssColorString("#64748b"),
  orbit: Cesium.Color.fromCssColorString("#22d3ee").withAlpha(0.5),
};

const store = useEarthStore();
const container = ref<HTMLDivElement | null>(null);
let viewer: Cesium.Viewer | null = null;

// Persistent data sources we update incrementally
let satEntitySource: Cesium.CustomDataSource | null = null;
let lightningSource: Cesium.CustomDataSource | null = null;
let earthquakeSource: Cesium.CustomDataSource | null = null;
let wildfireSource: Cesium.CustomDataSource | null = null;
let volcanoSource: Cesium.CustomDataSource | null = null;
let orbitSource: Cesium.CustomDataSource | null = null;

let resizeObserver: ResizeObserver | null = null;
let animationHandle: number | null = null;

onMounted(() => {
  if (!container.value) return;

  // Default to Cesium's bundled NaturalEarthII tiles — zero network, no keys.
  // (The previous build used OpenStreetMap which is unreachable in mainland CN
  // and causes the globe to render with no imagery at all.)
  let baseLayer: Cesium.ImageryLayer;
  try {
    const tms = new Cesium.TileMapServiceImageryProvider({
      url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
    });
    baseLayer = new Cesium.ImageryLayer(tms);
  } catch (e) {
    // Last-ditch: a single dark blue tile so we at least see *something*.
    baseLayer = new Cesium.ImageryLayer(
      new Cesium.SingleTileImageryProvider({
        url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII/0/0/0.jpg"),
        rectangle: Cesium.Rectangle.MAX_VALUE,
      }),
    );
  }

  try {
    viewer = new Cesium.Viewer(container.value, {
      baseLayer,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      timeline: false,
      animation: false,
      fullscreenButton: false,
      navigationHelpButton: false,
      selectionIndicator: true,
      infoBox: false,
      shouldAnimate: true,
      contextOptions: {
        // WebGL 1 first — works on more browsers/GPUs. Cesium will internally
        // upgrade to WebGL 2 where available.
        requestWebgl1: true,
        webgl: { alpha: true, antialias: true, preserveDrawingBuffer: true },
      } as any,
    });
  } catch (e: any) {
    showOverlay(`Cesium Viewer failed to initialize: ${e?.message ?? e}`);
    return;
  }

  // Atmosphere & sky settings
  const scene = viewer.scene;
  scene.skyAtmosphere.show = true;
  scene.fog.enabled = false;
  scene.globe.enableLighting = false;
  scene.globe.showGroundAtmosphere = true;
  scene.backgroundColor = Cesium.Color.fromCssColorString("#050a18");
  (scene.skyBox as any).show = true;

  // Surface WebGL context loss so the user knows what happened instead of a
  // silent black canvas.
  const canvas = scene.canvas as HTMLCanvasElement;
  canvas.addEventListener("webglcontextlost", (ev) => {
    ev.preventDefault();
    showOverlay("WebGL context lost. Reload the page or restart the browser.");
  });
  const gl = (canvas.getContext("webgl2") ?? canvas.getContext("webgl")) as
    | WebGLRenderingContext
    | WebGL2RenderingContext
    | null;
  if (gl) {
    const dbg = (gl.getExtension("WEBGL_debug_renderer_info") as any) ?? null;
    const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "n/a";
    const vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : "n/a";
    console.info("[Realtime Earth] WebGL ready:", { vendor, renderer });
  } else {
    showOverlay(
      "WebGL is not available in this browser. Enable hardware acceleration " +
        "(chrome://settings/system → Use graphics acceleration when available) " +
        "and reload.",
    );
  }

  // Initial camera: nice oblique view of the Earth
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(105, 25, 22000000),
    duration: 0,
  });

  // Data sources
  satEntitySource = new Cesium.CustomDataSource("satellites");
  orbitSource = new Cesium.CustomDataSource("orbits");
  lightningSource = new Cesium.CustomDataSource("lightning");
  earthquakeSource = new Cesium.CustomDataSource("earthquakes");
  wildfireSource = new Cesium.CustomDataSource("wildfires");
  volcanoSource = new Cesium.CustomDataSource("volcanoes");

  viewer.dataSources.add(satEntitySource);
  viewer.dataSources.add(orbitSource);
  viewer.dataSources.add(lightningSource);
  viewer.dataSources.add(earthquakeSource);
  viewer.dataSources.add(wildfireSource);
  viewer.dataSources.add(volcanoSource);

  // Click → select
  const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas);
  handler.setInputAction((click: Cesium.ScreenSpaceEventHandler.MouseOverEvent) => {
    const picked = scene.pick(click.position);
    if (Cesium.defined(picked) && picked.id) {
      const eid = (picked.id as any).re_id;
      const ecat = (picked.id as any).re_category;
      if (!eid) return;
      if (ecat === "satellite") store.selectedSatelliteId = eid;
      else if (ecat === "earthquake") store.selectedEarthquakeId = eid;
      else if (ecat === "wildfire") store.selectedWildfireId = eid;
      else if (ecat === "volcano") store.selectedVolcanoId = eid;
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  // Resize handling
  resizeObserver = new ResizeObserver(() => {
    if (viewer) viewer.resize();
  });
  resizeObserver.observe(container.value);

  // Animation loop for orbit tracking
  const tick = () => {
    if (store.layers.satellites) updateOrbitEnds();
    animationHandle = requestAnimationFrame(tick);
  };
  tick();

  // Initial render
  renderAll();
});

onBeforeUnmount(() => {
  if (animationHandle !== null) cancelAnimationFrame(animationHandle);
  if (resizeObserver) resizeObserver.disconnect();
  if (viewer) viewer.destroy();
});

// ---- Reactive updates -----------------------------------------------------

watch(
  () => [
    store.satellites,
    store.lightning,
    store.earthquakes,
    store.wildfires,
    store.volcanoes,
    store.layers.satellites,
    store.layers.lightning,
    store.layers.earthquakes,
    store.layers.wildfires,
    store.layers.volcanoes,
    store.layers.satellitesOrbit,
  ],
  () => renderAll(),
  { deep: false },
);

function renderAll() {
  if (!viewer) return;
  renderSatellites();
  renderLightning();
  renderEarthquakes();
  renderWildfires();
  renderVolcanoes();
}

function renderSatellites() {
  if (!satEntitySource || !orbitSource) return;
  satEntitySource.entities.removeAll();
  orbitSource.entities.removeAll();
  if (!store.layers.satellites) return;

  for (const sat of store.satellites) {
    if (!sat.position) continue;
    const isStarlink = sat.category === "starlink";
    const color = isStarlink
      ? COLORS.satelliteStarlink
      : sat.category === "hubble" || sat.category === "webb"
        ? COLORS.satelliteHi
        : COLORS.satellite;

    const pos = Cesium.Cartesian3.fromDegrees(
      sat.position.lon,
      sat.position.lat,
      sat.position.alt_km * 1000,
    );
    const size = isStarlink ? 4 : sat.category === "stations" ? 9 : 7;
    const isHeadliner = ["ISS", "TIANGONG", "HUBBLE", "JAMES WEBB"].some((h) =>
      sat.name.toUpperCase().includes(h),
    );

    const entity = satEntitySource.entities.add({
      position: pos,
      point: {
        pixelSize: isHeadliner ? size + 3 : size,
        color,
        outlineColor: Cesium.Color.WHITE.withAlpha(0.4),
        outlineWidth: 1,
      },
      label: store.layers.satellitesLabels
        ? {
            text: sat.name,
            font: "11px ui-monospace, monospace",
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 2,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, -16),
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString("#0b1220").withAlpha(0.7),
            scale: 0.8,
            translucencyByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 5.0e7, 0.0),
          }
        : undefined,
    });
    (entity as any).re_id = sat.id;
    (entity as any).re_category = "satellite";

    // Orbit track: simple 90-minute ground track from current position
    if (store.layers.satellitesOrbit && !isStarlink) {
      orbitSource.entities.add(buildOrbitEntity(sat));
    }
  }
}

function buildOrbitEntity(sat: Satellite): Cesium.Entity {
  const positions: Cesium.Cartesian3[] = [];
  if (!sat.position) {
    return new Cesium.Entity({ position: Cesium.Cartesian3.fromDegrees(0, 0) });
  }
  const { lat, lon, alt_km } = sat.position;
  // 90 minutes is typical for LEO; we draw ±45 min as a polyline
  const minutes = 90;
  const steps = 90;
  const alt = alt_km * 1000;
  // Crude approximation: Earth rotates 0.25°/min, satellite moves ~4°/min in track
  // We use a simple circular ground-track shift for visualisation purposes
  for (let i = -steps / 2; i <= steps / 2; i++) {
    const t = (i / steps) * minutes;
    const trackAngle = (t / minutes) * 360; // 360° per orbit
    const earthRotation = (t / minutes) * 360 * 0.065; // 0.065 = 1/15.4
    const lat_t =
      lat * Math.cos((trackAngle * Math.PI) / 180) -
      30 * Math.sin((trackAngle * Math.PI) / 180) * Math.cos((lat * Math.PI) / 180);
    const lon_t = lon + trackAngle - earthRotation;
    positions.push(
      Cesium.Cartesian3.fromDegrees(
        ((lon_t + 540) % 360) - 180,
        Math.max(-85, Math.min(85, lat_t)),
        alt,
      ),
    );
  }
  return new Cesium.Entity({
    polyline: {
      positions,
      width: 1.2,
      material: COLORS.orbit,
      arcType: Cesium.ArcType.NONE,
    },
  });
}

function updateOrbitEnds() {
  // Could animate — keeping it simple for now
}

function renderLightning() {
  if (!lightningSource) return;
  lightningSource.entities.removeAll();
  if (!store.layers.lightning) return;

  // Limit to most recent 2000 strikes to keep render snappy
  const strikes = store.lightning.slice(-2000);
  for (const s of strikes) {
    const color =
      s.polarity === "positive" ? COLORS.lightningPos : COLORS.lightningNeg;
    const entity = lightningSource.entities.add({
      position: Cesium.Cartesian3.fromDegrees(s.lon, s.lat, s.alt_km * 1000),
      point: {
        pixelSize: 4,
        color: color.withAlpha(0.85),
        outlineColor: color.withAlpha(0.4),
        outlineWidth: 1,
      },
    });
    (entity as any).re_id = s.id;
    (entity as any).re_category = "lightning";
  }
}

function renderEarthquakes() {
  if (!earthquakeSource) return;
  earthquakeSource.entities.removeAll();
  if (!store.layers.earthquakes) return;

  for (const eq of store.earthquakes) {
    if (eq.mag < 2.5 && eq.depth_km < 50) continue; // skip noisy tiny ones
    const size = Math.min(28, Math.max(4, eq.mag * 3));
    const color = eq.mag >= 6 ? COLORS.earthquakeBig : COLORS.earthquake;
    const entity = earthquakeSource.entities.add({
      position: Cesium.Cartesian3.fromDegrees(eq.lon, eq.lat, 0),
      point: {
        pixelSize: size,
        color: color.withAlpha(0.75),
        outlineColor: Cesium.Color.WHITE.withAlpha(0.6),
        outlineWidth: 1,
      },
    });
    (entity as any).re_id = eq.id;
    (entity as any).re_category = "earthquake";
  }
}

function renderWildfires() {
  if (!wildfireSource) return;
  wildfireSource.entities.removeAll();
  if (!store.layers.wildfires) return;

  // Limit: only show high+nominal confidence to keep render fast
  const fires = store.wildfires
    .filter((f) => f.confidence !== "low")
    .slice(0, 4000);
  for (const f of fires) {
    const size = Math.min(8, Math.max(2, Math.log10(f.frp_mw + 1) * 2.5));
    const entity = wildfireSource.entities.add({
      position: Cesium.Cartesian3.fromDegrees(f.lon, f.lat, 0),
      point: {
        pixelSize: size,
        color: COLORS.wildfire.withAlpha(0.85),
        outlineColor: Cesium.Color.fromCssColorString("#fbbf24").withAlpha(0.4),
        outlineWidth: 0.5,
      },
    });
    (entity as any).re_id = f.id;
    (entity as any).re_category = "wildfire";
  }
}

function renderVolcanoes() {
  if (!volcanoSource) return;
  volcanoSource.entities.removeAll();
  if (!store.layers.volcanoes) return;

  for (const v of store.volcanoes) {
    const color =
      v.activity_level === "erupting"
        ? COLORS.volcanoErupt
        : v.activity_level === "elevated"
          ? COLORS.volcanoElev
          : COLORS.volcanoNormal;
    const pos = Cesium.Cartesian3.fromDegrees(v.lon, v.lat, v.elevation_m || 0);
    const entity = volcanoSource.entities.add({
      position: pos,
      point: {
        pixelSize: v.activity_level === "erupting" ? 12 : 8,
        color,
        outlineColor: Cesium.Color.WHITE.withAlpha(0.6),
        outlineWidth: 1,
      },
      cylinder: {
        length: Math.max(50000, v.elevation_m * 1.5),
        topRadius: 0,
        bottomRadius: 6000,
        material: color.withAlpha(0.4),
        outline: false,
      },
    });
    (entity as any).re_id = v.id;
    (entity as any).re_category = "volcano";
  }
}

// ---- Public actions -------------------------------------------------------

function flyTo(lon: number, lat: number, altKm = 5000) {
  if (!viewer) return;
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(lon, lat, altKm * 1000),
    duration: 1.5,
  });
}

function showOverlay(msg: string) {
  if (!container.value) return;
  const div = document.createElement("div");
  div.style.cssText = [
    "position:absolute",
    "inset:16px",
    "z-index:50",
    "display:flex",
    "align-items:center",
    "justify-content:center",
    "padding:24px",
    "border-radius:12px",
    "background:rgba(11,18,32,0.85)",
    "color:#fda4af",
    "font:13px ui-monospace,monospace",
    "line-height:1.6",
    "border:1px solid #ef4444",
    "text-align:center",
    "pointer-events:auto",
  ].join(";");
  div.textContent = msg;
  container.value.appendChild(div);
  console.error("[Realtime Earth]", msg);
}

defineExpose({ flyTo });
</script>

<template>
  <div ref="container" class="relative h-full w-full">
    <!-- Cesium injects its canvas here. An absolute overlay sits on top so we
         can surface WebGL / context errors instead of leaving a black hole. -->
  </div>
</template>
