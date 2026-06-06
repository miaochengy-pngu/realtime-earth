<script setup lang="ts">
import { computed, ref } from "vue";
import { useEarthStore } from "@/stores/earth";
import type { SatelliteCategory } from "@/types";

const store = useEarthStore();

const filter = ref<"all" | SatelliteCategory>("all");
const search = ref("");

const filtered = computed(() => {
  let sats = store.satellites;
  if (filter.value !== "all") sats = sats.filter((s) => s.category === filter.value);
  if (search.value) {
    const q = search.value.toLowerCase();
    sats = sats.filter((s) => s.name.toLowerCase().includes(q));
  }
  return sats
    .slice()
    .sort((a, b) => {
      const ha = ["ISS", "TIANGONG", "HUBBLE", "JAMES WEBB"].some((h) =>
        a.name.toUpperCase().includes(h),
      )
        ? 0
        : 1;
      const hb = ["ISS", "TIANGONG", "HUBBLE", "JAMES WEBB"].some((h) =>
        b.name.toUpperCase().includes(h),
      )
        ? 0
        : 1;
      return ha - hb;
    });
});

const counts = computed(() => {
  const out: Record<string, number> = { all: store.satellites.length };
  for (const s of store.satellites) {
    out[s.category] = (out[s.category] || 0) + 1;
  }
  return out;
});

function select(id: string) {
  store.selectedSatelliteId = id;
}
</script>

<template>
  <div class="p-3 space-y-3">
    <div class="space-y-1.5">
      <input
        v-model="search"
        type="text"
        placeholder="Search by name…"
        class="w-full bg-space-900/80 border border-cyan-500/20 rounded px-2.5 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/50"
      />
      <div class="flex flex-wrap gap-1">
        <button
          v-for="(c, key) in counts"
          :key="key"
          @click="filter = key as any"
          :class="[
            'text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider',
            filter === key
              ? 'bg-cyan-500/20 text-cyan-200'
              : 'bg-space-900/60 text-slate-400 hover:text-slate-200',
          ]"
        >
          {{ key }} · {{ c }}
        </button>
      </div>
    </div>

    <div>
      <div class="panel-title">Headliners</div>
      <ul class="space-y-1">
        <li
          v-for="sat in store.prominentSatellites"
          :key="sat.id"
          class="px-2 py-1.5 rounded bg-space-900/60 hover:bg-cyan-500/10 cursor-pointer transition-colors border border-transparent hover:border-cyan-400/30"
          @click="select(sat.id)"
        >
          <div class="flex items-center justify-between">
            <div class="text-xs font-medium text-slate-100">
              {{ sat.name }}
            </div>
            <span
              :class="[
                'text-[9px] uppercase px-1.5 py-0.5 rounded',
                sat.category === 'hubble' || sat.category === 'webb'
                  ? 'bg-fuchsia-500/15 text-fuchsia-300'
                  : 'bg-cyan-500/15 text-cyan-300',
              ]"
            >
              {{ sat.category }}
            </span>
          </div>
          <div
            v-if="sat.position"
            class="mt-0.5 text-[10px] text-slate-400 font-mono"
          >
            {{ sat.position.lat.toFixed(2) }}°, {{ sat.position.lon.toFixed(2) }}° ·
            {{ sat.position.alt_km.toFixed(0) }} km · {{ sat.position.velocity_kms.toFixed(2) }} km/s
          </div>
        </li>
      </ul>
    </div>

    <div v-if="filter !== 'all' || search">
      <div class="panel-title">
        {{ filter === "all" ? "Search" : filter }} ({{ filtered.length }})
      </div>
      <ul class="space-y-0.5 max-h-72 overflow-y-auto">
        <li
          v-for="sat in filtered.slice(0, 200)"
          :key="sat.id"
          @click="select(sat.id)"
          class="px-2 py-1 rounded text-[11px] text-slate-300 hover:bg-cyan-500/10 cursor-pointer truncate"
        >
          {{ sat.name }}
        </li>
      </ul>
    </div>
  </div>
</template>
