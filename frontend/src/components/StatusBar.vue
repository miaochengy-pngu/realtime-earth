<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();

const sources = computed(() =>
  Object.entries(store.sources).map(([name, s]) => ({
    name,
    ...s,
  })),
);

const formatTime = (iso: string | null) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString();
  } catch {
    return iso;
  }
};
</script>

<template>
  <footer
    class="flex items-center gap-3 px-3 py-1.5 bg-space-900/95 border-t border-cyan-500/15 text-[10px] text-slate-400"
  >
    <span class="font-semibold text-slate-300">SOURCES</span>
    <div class="flex items-center gap-3 overflow-x-auto flex-1">
      <div
        v-for="s in sources"
        :key="s.name"
        class="flex items-center gap-1.5 whitespace-nowrap"
        :title="s.error || s.name"
      >
        <span
          :class="s.ok ? 'bg-emerald-400' : 'bg-rose-400'"
          class="h-1.5 w-1.5 rounded-full"
        />
        <span class="uppercase tracking-wider">{{ s.name }}</span>
        <span class="font-mono text-slate-200">{{ s.items }}</span>
        <span class="text-slate-500">·</span>
        <span class="font-mono">{{ formatTime(s.last_updated) }}</span>
      </div>
    </div>
    <div class="text-slate-500 hidden md:block">
      ⚡ {{ store.recentLightningCount }} strikes / 5min · 🌋
      {{ store.eruptingVolcanoes.length }} erupting
    </div>
  </footer>
</template>
