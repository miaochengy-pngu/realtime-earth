<script setup lang="ts">
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();

const layerDefs = [
  {
    key: "satellites",
    label: "Satellites",
    desc: "All tracked orbital objects",
    color: "text-cyan-300",
  },
  {
    key: "satellitesOrbit",
    label: "Orbit tracks",
    desc: "Ground track polyline (headliners only)",
    color: "text-cyan-300",
  },
  {
    key: "satellitesLabels",
    label: "Satellite names",
    desc: "Show name labels next to points",
    color: "text-cyan-300",
  },
  {
    key: "lightning",
    label: "Lightning",
    desc: "Last hour of strikes (Blitzortung)",
    color: "text-orange-300",
  },
  {
    key: "earthquakes",
    label: "Earthquakes",
    desc: "USGS events, point size = magnitude",
    color: "text-rose-300",
  },
  {
    key: "wildfires",
    label: "Active fires",
    desc: "NASA FIRMS thermal anomalies",
    color: "text-amber-300",
  },
  {
    key: "volcanoes",
    label: "Volcanoes",
    desc: "GVP, color by activity level",
    color: "text-rose-300",
  },
] as const;
</script>

<template>
  <div class="p-3 space-y-2">
    <div class="panel-title">Visible layers</div>
    <ul class="space-y-1">
      <li
        v-for="layer in layerDefs"
        :key="layer.key"
        class="flex items-start gap-2 px-2 py-1.5 rounded hover:bg-cyan-500/5 cursor-pointer"
        @click="store.toggleLayer(layer.key as any)"
      >
        <input
          type="checkbox"
          :checked="(store.layers as any)[layer.key]"
          class="mt-0.5 accent-cyan-400"
          @click.stop="store.toggleLayer(layer.key as any)"
        />
        <div class="flex-1 min-w-0">
          <div class="text-[12px] font-medium" :class="layer.color">
            {{ layer.label }}
          </div>
          <div class="text-[10px] text-slate-500">{{ layer.desc }}</div>
        </div>
      </li>
    </ul>

    <div class="border-t border-cyan-500/15 my-2" />

    <div class="text-[10px] text-slate-500 leading-relaxed space-y-1.5">
      <p>
        <kbd class="px-1 py-0.5 bg-space-900 rounded text-[10px]">Esc</kbd> clear
        selection · click a point on the globe for details.
      </p>
      <p>
        Drag to rotate the globe · scroll to zoom · right-drag to tilt.
      </p>
    </div>
  </div>
</template>
