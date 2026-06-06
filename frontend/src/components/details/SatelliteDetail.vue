<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const sat = computed(() => store.selectedSatellite);

const suborbitalSpeed = computed(() => {
  if (!sat.value?.position) return null;
  return sat.value.position.velocity_kms;
});

const orbitMinutes = computed(() => {
  if (!sat.value?.position) return null;
  // Rough orbital period from altitude (km) using v^2 = GM/r
  const alt = sat.value.position.alt_km;
  const r = alt + 6371;
  const mu = 398600.4418; // km^3/s^2
  const v = Math.sqrt(mu / r);
  const period = (2 * Math.PI * r) / v; // seconds
  return Math.round(period / 60);
});

const subPoint = computed(() => {
  if (!sat.value?.position) return null;
  return {
    lat: sat.value.position.lat,
    lon: sat.value.position.lon,
  };
});
</script>

<template>
  <div v-if="sat" class="p-3 space-y-3">
    <div>
      <div class="text-[10px] uppercase tracking-wider text-cyan-300/80">
        {{ sat.category }}
      </div>
      <div class="text-lg font-semibold text-slate-100 leading-tight">
        {{ sat.name }}
      </div>
      <div class="text-[11px] text-slate-500 font-mono mt-0.5">
        NORAD {{ sat.id }}<span v-if="sat.intl_designator"> · {{ sat.intl_designator }}</span>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Latitude</span>
        <span class="stat-value">{{ sat.position?.lat.toFixed(2) }}°</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Longitude</span>
        <span class="stat-value">{{ sat.position?.lon.toFixed(2) }}°</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Altitude</span>
        <span class="stat-value">{{ sat.position?.alt_km.toFixed(0) }}</span>
        <span class="text-[10px] text-slate-400">km</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Speed</span>
        <span class="stat-value">{{ suborbitalSpeed?.toFixed(2) }}</span>
        <span class="text-[10px] text-slate-400">km/s</span>
      </div>
      <div v-if="orbitMinutes" class="stat panel p-2 col-span-2">
        <span class="stat-label">Orbital period (approx)</span>
        <span class="stat-value">{{ orbitMinutes }} min</span>
      </div>
    </div>

    <details class="text-[10px] text-slate-500">
      <summary class="cursor-pointer text-slate-300">TLE (epoch {{ new Date(sat.epoch).toLocaleString() }})</summary>
      <pre class="mt-1 p-2 bg-space-900/80 rounded text-[10px] font-mono text-slate-300 overflow-x-auto whitespace-pre">{{ sat.line1 }}
{{ sat.line2 }}</pre>
    </details>
  </div>
</template>
