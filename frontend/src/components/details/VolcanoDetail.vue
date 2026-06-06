<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const v = computed(() => store.selectedVolcano);

const levelColor = computed(() => {
  switch (v.value?.activity_level) {
    case "erupting":
      return "text-rose-300 border-rose-400/30 bg-rose-500/15";
    case "elevated":
      return "text-amber-300 border-amber-400/30 bg-amber-500/15";
    default:
      return "text-slate-300 border-slate-400/30 bg-slate-700/30";
  }
});
</script>

<template>
  <div v-if="v" class="p-3 space-y-3">
    <div>
      <div
        class="inline-block text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border"
        :class="levelColor"
      >
        {{ v.activity_level }}
      </div>
      <div class="text-lg font-semibold text-slate-100 leading-tight mt-1">
        🌋 {{ v.name }}
      </div>
      <div class="text-[11px] text-slate-500 mt-0.5">
        {{ v.country || v.region }}
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Elevation</span>
        <span class="stat-value">{{ v.elevation_m }}</span>
        <span class="text-[10px] text-slate-400">m</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Last known</span>
        <span class="stat-value">{{ v.last_known_eruption ?? "—" }}</span>
        <span class="text-[10px] text-slate-400">eruption</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Latitude</span>
        <span class="stat-value">{{ v.lat.toFixed(2) }}°</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Longitude</span>
        <span class="stat-value">{{ v.lon.toFixed(2) }}°</span>
      </div>
    </div>

    <a
      :href="`https://volcano.si.edu/volcano.cfm?vn=${encodeURIComponent(v.id)}`"
      target="_blank"
      rel="noopener"
      class="block text-center px-3 py-2 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-200 text-xs font-medium border border-cyan-400/30"
    >
      View on Smithsonian GVP ↗
    </a>

    <div class="text-[10px] text-slate-500">
      Data: Smithsonian Global Volcanism Program
    </div>
  </div>
</template>
