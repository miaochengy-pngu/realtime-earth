<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const eq = computed(() => store.selectedEarthquake);

const magClass = computed(() => {
  if (!eq.value) return "";
  const m = eq.value.mag;
  if (m >= 8) return "Great";
  if (m >= 7) return "Major";
  if (m >= 6) return "Strong";
  if (m >= 5) return "Moderate";
  if (m >= 4) return "Light";
  if (m >= 3) return "Minor";
  return "Micro";
});
</script>

<template>
  <div v-if="eq" class="p-3 space-y-3">
    <div>
      <div class="text-[10px] uppercase tracking-wider text-rose-300/80">
        Earthquake · {{ magClass }}
      </div>
      <div class="text-base font-semibold text-slate-100 leading-tight">
        M {{ eq.mag.toFixed(1) }} — {{ eq.place }}
      </div>
      <div class="text-[11px] text-slate-500 font-mono mt-0.5">
        {{ new Date(eq.time).toLocaleString() }}
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Depth</span>
        <span class="stat-value">{{ eq.depth_km.toFixed(1) }}</span>
        <span class="text-[10px] text-slate-400">km</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Felt</span>
        <span class="stat-value">{{ eq.felt ?? "—" }}</span>
        <span class="text-[10px] text-slate-400">reports</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Tsunami</span>
        <span :class="['stat-value', eq.tsunami ? 'text-rose-300' : 'text-slate-200']">
          {{ eq.tsunami ? "YES" : "no" }}
        </span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Alert</span>
        <span class="stat-value uppercase text-[10px]">
          {{ eq.alert ?? "—" }}
        </span>
      </div>
    </div>

    <a
      :href="eq.url"
      target="_blank"
      rel="noopener"
      class="block text-center px-3 py-2 rounded bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-200 text-xs font-medium border border-cyan-400/30"
    >
      View on USGS ↗
    </a>

    <div class="text-[10px] text-slate-500">
      ID: <span class="font-mono">{{ eq.id }}</span> · event_type: {{ eq.event_type }}
    </div>
  </div>
</template>
