<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";
import SatelliteDetail from "./details/SatelliteDetail.vue";
import EarthquakeDetail from "./details/EarthquakeDetail.vue";
import VolcanoDetail from "./details/VolcanoDetail.vue";

const emit = defineEmits<{ (e: "close"): void }>();

const store = useEarthStore();
const show = computed(
  () =>
    store.selectedSatellite || store.selectedEarthquake || store.selectedVolcano,
);
</script>

<template>
  <aside
    v-if="show"
    class="panel flex flex-col overflow-hidden"
    role="complementary"
    aria-label="Selected detail"
  >
    <div
      class="flex items-center justify-between px-3 py-1.5 border-b border-cyan-500/15 bg-space-900/60"
    >
      <span class="panel-title mb-0">DETAIL</span>
      <button
        class="text-slate-400 hover:text-slate-200 text-lg leading-none"
        aria-label="Close"
        @click="emit('close')"
      >
        ×
      </button>
    </div>
    <div class="flex-1 overflow-y-auto">
      <SatelliteDetail v-if="store.selectedSatellite" />
      <EarthquakeDetail v-else-if="store.selectedEarthquake" />
      <VolcanoDetail v-else-if="store.selectedVolcano" />
    </div>
  </aside>
</template>
