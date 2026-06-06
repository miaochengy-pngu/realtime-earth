<script setup lang="ts">
import { onMounted, computed, watch } from "vue";
import GlobeView from "@/components/GlobeView.vue";
import TopBar from "@/components/TopBar.vue";
import Sidebar from "@/components/Sidebar.vue";
import StatusBar from "@/components/StatusBar.vue";
import DetailPanel from "@/components/DetailPanel.vue";
import { useEarthWebSocket } from "@/composables/useEarthWebSocket";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
useEarthWebSocket();

const selectedAnything = computed(
  () =>
    store.selectedSatelliteId ||
    store.selectedEarthquakeId ||
    store.selectedWildfireId ||
    store.selectedVolcanoId,
);

function clearSelection() {
  store.selectedSatelliteId = null;
  store.selectedEarthquakeId = null;
  store.selectedWildfireId = null;
  store.selectedVolcanoId = null;
}

// Keyboard shortcuts
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") clearSelection();
  if (e.key === "?" || (e.shiftKey && e.key === "/")) {
    const ev = new CustomEvent("re:toggle-help");
    window.dispatchEvent(ev);
  }
}

onMounted(() => {
  window.addEventListener("keydown", onKey);
});
</script>

<template>
  <div class="relative h-screen w-screen overflow-hidden bg-space-950 text-slate-100">
    <GlobeView class="absolute inset-0" />

    <TopBar class="absolute top-0 left-0 right-0 z-30" />

    <Sidebar class="absolute top-16 left-3 bottom-10 z-20 w-80 max-w-[90vw]" />

    <DetailPanel
      v-if="selectedAnything"
      class="absolute top-16 right-3 bottom-10 z-20 w-96 max-w-[90vw]"
      @close="clearSelection"
    />

    <StatusBar class="absolute bottom-0 left-0 right-0 z-30" />
  </div>
</template>
