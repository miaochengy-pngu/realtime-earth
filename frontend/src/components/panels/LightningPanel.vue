<script setup lang="ts">
import { computed, ref } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const windowMin = ref(10);

const stats = computed(() => {
  const cutoff = Date.now() - windowMin.value * 60 * 1000;
  const recent = store.lightning.filter((s) => new Date(s.time).getTime() >= cutoff);
  const pos = recent.filter((s) => s.polarity === "positive").length;
  const neg = recent.filter((s) => s.polarity === "negative").length;
  const max = recent.reduce((m, s) => Math.max(m, s.amplitude_ka || 0), 0);
  return {
    total: recent.length,
    pos,
    neg,
    perMin: recent.length / Math.max(windowMin.value, 1),
    maxAmp: max,
  };
});

const latest = computed(() =>
  store.lightning
    .slice()
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 50),
);
</script>

<template>
  <div class="p-3 space-y-3">
    <div>
      <div class="panel-title">Live window</div>
      <div class="grid grid-cols-3 gap-2">
        <button
          v-for="m in [5, 10, 30, 60]"
          :key="m"
          @click="windowMin = m"
          :class="[
            'px-2 py-1 text-[11px] rounded',
            windowMin === m
              ? 'bg-cyan-500/20 text-cyan-200 border border-cyan-400/30'
              : 'bg-space-900/60 text-slate-400 border border-transparent',
          ]"
        >
          {{ m }}m
        </button>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Strikes</span>
        <span class="stat-value">{{ stats.total.toLocaleString() }}</span>
        <span class="text-[10px] text-slate-400">
          {{ stats.perMin.toFixed(1) }}/min
        </span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Pos / Neg</span>
        <span class="stat-value text-orange-300">
          {{ stats.pos }}<span class="text-slate-500 mx-1">/</span
          ><span class="text-cyan-300">{{ stats.neg }}</span>
        </span>
        <span class="text-[10px] text-slate-400">ratio</span>
      </div>
      <div class="stat panel p-2 col-span-2">
        <span class="stat-label">Peak amplitude</span>
        <span class="stat-value">{{ stats.maxAmp.toFixed(1) }} kA</span>
        <span class="text-[10px] text-slate-400">in last {{ windowMin }} min</span>
      </div>
    </div>

    <div>
      <div class="panel-title">Latest 50</div>
      <div class="max-h-72 overflow-y-auto text-[11px] font-mono">
        <div
          v-for="s in latest"
          :key="s.id"
          class="flex items-center justify-between py-0.5 px-1.5 hover:bg-cyan-500/5 rounded"
        >
          <span class="text-slate-400 w-16">
            {{ new Date(s.time).toLocaleTimeString() }}
          </span>
          <span
            :class="s.polarity === 'positive' ? 'text-orange-300' : 'text-cyan-300'"
            class="w-3"
          >
            {{ s.polarity === "positive" ? "+" : s.polarity === "negative" ? "−" : "·" }}
          </span>
          <span class="text-slate-200 w-12 text-right">
            {{ s.amplitude_ka?.toFixed(1) ?? "—" }}
          </span>
          <span class="text-slate-500 w-20 text-right uppercase">{{ s.region }}</span>
          <span class="text-slate-500 w-24 text-right">
            {{ s.lat.toFixed(1) }}, {{ s.lon.toFixed(1) }}
          </span>
        </div>
      </div>
    </div>

    <div class="text-[10px] text-slate-500 leading-relaxed">
      Data courtesy of the
      <a
        href="https://www.blitzortung.org/"
        target="_blank"
        rel="noopener"
        class="text-cyan-300/80 hover:text-cyan-200 underline"
        >Blitzortung</a
      >
      community detection network.
    </div>
  </div>
</template>
