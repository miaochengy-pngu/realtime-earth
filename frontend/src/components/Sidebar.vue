<script setup lang="ts">
import { computed, ref } from "vue";
import { useEarthStore } from "@/stores/earth";
import LightningPanel from "./panels/LightningPanel.vue";
import SatellitePanel from "./panels/SatellitePanel.vue";
import EarthPanel from "./panels/EarthPanel.vue";
import SolarPanel from "./panels/SolarPanel.vue";
import LayersPanel from "./panels/LayersPanel.vue";

const store = useEarthStore();
type Tab = "satellites" | "lightning" | "earth" | "solar" | "layers";
const tab = ref<Tab>("satellites");

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "satellites", label: "Spacefleet", icon: "🛰️" },
  { id: "lightning", label: "Lightning", icon: "⚡" },
  { id: "earth", label: "Earth Skin", icon: "🌋" },
  { id: "solar", label: "Sun & Aurora", icon: "☀️" },
  { id: "layers", label: "Layers", icon: "🗺️" },
];
</script>

<template>
  <aside
    class="flex flex-col panel overflow-hidden"
    role="complementary"
    aria-label="Data panels"
  >
    <nav
      class="flex items-center gap-1 px-2 py-1.5 border-b border-cyan-500/15 bg-space-900/50 overflow-x-auto"
    >
      <button
        v-for="t in tabs"
        :key="t.id"
        :class="[
          'flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-colors whitespace-nowrap',
          tab === t.id
            ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-400/30'
            : 'text-slate-400 hover:text-slate-200 border border-transparent',
        ]"
        @click="tab = t.id"
      >
        <span>{{ t.icon }}</span>
        <span>{{ t.label }}</span>
      </button>
    </nav>

    <div class="flex-1 overflow-y-auto">
      <SatellitePanel v-if="tab === 'satellites'" />
      <LightningPanel v-else-if="tab === 'lightning'" />
      <EarthPanel v-else-if="tab === 'earth'" />
      <SolarPanel v-else-if="tab === 'solar'" />
      <LayersPanel v-else-if="tab === 'layers'" />
    </div>
  </aside>
</template>
