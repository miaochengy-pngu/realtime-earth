<script setup lang="ts">
import { computed, ref } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
type Tab = "earthquakes" | "wildfires" | "volcanoes";
const tab = ref<Tab>("earthquakes");
const minMag = ref(2.5);

const eqFiltered = computed(() =>
  store.earthquakes.filter((e) => e.mag >= minMag.value).slice(0, 50),
);

const eqStats = computed(() => {
  const last24 = store.earthquakes.filter(
    (e) => Date.now() - new Date(e.time).getTime() < 24 * 3600 * 1000,
  );
  return {
    last24: last24.length,
    maxMag24: last24.reduce((m, e) => Math.max(m, e.mag), 0),
    tsunami: last24.filter((e) => e.tsunami).length,
  };
});

const bigFires = computed(() =>
  store.wildfires
    .filter((f) => f.frp_mw > 100 && f.confidence !== "low")
    .sort((a, b) => b.frp_mw - a.frp_mw)
    .slice(0, 30),
);

const fireStats = computed(() => ({
  total: store.wildfires.length,
  high: store.wildfires.filter((f) => f.confidence === "high").length,
  totalFrp: store.wildfires.reduce((s, f) => s + f.frp_mw, 0),
}));

const erupting = computed(() =>
  store.volcanoes
    .filter((v) => v.activity_level === "erupting")
    .sort((a, b) => a.name.localeCompare(b.name)),
);
const elevated = computed(() =>
  store.volcanoes
    .filter((v) => v.activity_level === "elevated")
    .sort((a, b) => a.name.localeCompare(b.name)),
);

function timeAgo(iso: string) {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function selectEq(id: string) {
  store.selectedEarthquakeId = id;
}
function selectVolcano(id: string) {
  store.selectedVolcanoId = id;
}
</script>

<template>
  <div class="p-3 space-y-3">
    <div class="flex items-center gap-1">
      <button
        v-for="t in ['earthquakes', 'wildfires', 'volcanoes'] as Tab[]"
        :key="t"
        @click="tab = t"
        :class="[
          'px-2.5 py-1 rounded text-[11px] font-medium uppercase tracking-wider',
          tab === t
            ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400/30'
            : 'bg-space-900/60 text-slate-400 border border-transparent',
        ]"
      >
        {{ t }}
      </button>
    </div>

    <!-- Earthquakes -->
    <div v-if="tab === 'earthquakes'" class="space-y-3">
      <div class="grid grid-cols-3 gap-2">
        <div class="stat panel p-2">
          <span class="stat-label">Last 24h</span>
          <span class="stat-value">{{ eqStats.last24 }}</span>
        </div>
        <div class="stat panel p-2">
          <span class="stat-label">Max M</span>
          <span class="stat-value text-rose-300">{{ eqStats.maxMag24.toFixed(1) }}</span>
        </div>
        <div class="stat panel p-2">
          <span class="stat-label">Tsunami</span>
          <span class="stat-value">{{ eqStats.tsunami }}</span>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-[10px] text-slate-400 uppercase">Min M</span>
        <input
          v-model.number="minMag"
          type="range"
          min="0"
          max="8"
          step="0.1"
          class="flex-1 accent-cyan-400"
        />
        <span class="text-[11px] font-mono text-slate-200 w-8 text-right">
          {{ minMag.toFixed(1) }}
        </span>
      </div>

      <div>
        <div class="panel-title">Recent ({{ eqFiltered.length }})</div>
        <div class="max-h-72 overflow-y-auto space-y-0.5">
          <button
            v-for="eq in eqFiltered"
            :key="eq.id"
            @click="selectEq(eq.id)"
            class="w-full text-left px-2 py-1.5 rounded hover:bg-cyan-500/10 transition-colors flex items-center gap-2"
          >
            <span
              :class="[
                'inline-flex items-center justify-center w-9 h-9 rounded font-mono font-semibold text-[11px] flex-shrink-0',
                eq.mag >= 6
                  ? 'bg-rose-500/20 text-rose-200 border border-rose-400/30'
                  : eq.mag >= 4.5
                    ? 'bg-orange-500/15 text-orange-200 border border-orange-400/30'
                    : 'bg-slate-700/50 text-slate-200 border border-slate-600/30',
              ]"
            >
              {{ eq.mag.toFixed(1) }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-[11px] text-slate-100 truncate">{{ eq.place }}</div>
              <div class="text-[10px] text-slate-500 font-mono">
                {{ timeAgo(eq.time) }} · {{ eq.depth_km.toFixed(0) }} km
                <span v-if="eq.tsunami" class="text-rose-300 ml-1">⚠ TSUNAMI</span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Wildfires -->
    <div v-else-if="tab === 'wildfires'" class="space-y-3">
      <div class="grid grid-cols-3 gap-2">
        <div class="stat panel p-2">
          <span class="stat-label">Tracked</span>
          <span class="stat-value">{{ fireStats.total.toLocaleString() }}</span>
        </div>
        <div class="stat panel p-2">
          <span class="stat-label">High conf.</span>
          <span class="stat-value text-amber-300">{{ fireStats.high }}</span>
        </div>
        <div class="stat panel p-2">
          <span class="stat-label">Total FRP</span>
          <span class="stat-value">{{ (fireStats.totalFrp / 1000).toFixed(1) }} GW</span>
        </div>
      </div>

      <div>
        <div class="panel-title">Hottest fires (FRP &gt; 100 MW)</div>
        <div class="max-h-72 overflow-y-auto space-y-0.5 text-[11px]">
          <div
            v-for="f in bigFires"
            :key="f.id"
            class="flex items-center justify-between px-2 py-1 rounded hover:bg-amber-500/10"
          >
            <span class="font-mono text-slate-300 w-16"
              >{{ f.acq_date }} {{ f.acq_time }}</span
            >
            <span
              :class="[
                'w-14 text-right font-mono',
                f.confidence === 'high' ? 'text-amber-200' : 'text-slate-300',
              ]"
              >{{ f.frp_mw.toFixed(0) }} MW</span
            >
            <span class="text-slate-500 w-12 text-right">{{ f.satellite }}</span>
            <span class="text-slate-400 w-24 text-right">
              {{ f.lat.toFixed(1) }}, {{ f.lon.toFixed(1) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Volcanoes -->
    <div v-else class="space-y-3">
      <div class="grid grid-cols-2 gap-2">
        <div class="stat panel p-2">
          <span class="stat-label">🌋 Erupting</span>
          <span class="stat-value text-rose-300">{{ erupting.length }}</span>
        </div>
        <div class="stat panel p-2">
          <span class="stat-label">🔶 Elevated</span>
          <span class="stat-value text-amber-300">{{ elevated.length }}</span>
        </div>
      </div>

      <div v-if="erupting.length">
        <div class="panel-title">Erupting now</div>
        <div class="space-y-0.5">
          <button
            v-for="v in erupting"
            :key="v.id"
            @click="selectVolcano(v.id)"
            class="w-full text-left px-2 py-1 rounded hover:bg-rose-500/10 text-[11px] flex items-center justify-between"
          >
            <span class="text-rose-100">🌋 {{ v.name }}</span>
            <span class="text-slate-500">{{ v.country }}</span>
          </button>
        </div>
      </div>

      <div v-if="elevated.length">
        <div class="panel-title">Elevated</div>
        <div class="space-y-0.5">
          <button
            v-for="v in elevated"
            :key="v.id"
            @click="selectVolcano(v.id)"
            class="w-full text-left px-2 py-1 rounded hover:bg-amber-500/10 text-[11px] flex items-center justify-between"
          >
            <span class="text-amber-100">🔶 {{ v.name }}</span>
            <span class="text-slate-500">{{ v.country }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
