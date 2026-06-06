<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const uptime = computed(() => {
  const s = store.uptime;
  if (!s) return "—";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
});
</script>

<template>
  <header
    class="flex items-center gap-3 px-4 py-2.5 bg-gradient-to-b from-space-900/95 to-space-900/80 backdrop-blur border-b border-cyan-500/15"
  >
    <div class="flex items-center gap-2.5">
      <div
        class="h-7 w-7 rounded-full bg-gradient-to-br from-cyan-400 to-blue-700 shadow-glow"
      />
      <div>
        <div class="text-sm font-semibold tracking-wide text-slate-100">
          Realtime Earth
        </div>
        <div class="text-[10px] text-slate-400 -mt-0.5">
          Live atlas of public data · v{{ store.version || "0.1" }}
        </div>
      </div>
    </div>

    <div class="flex-1" />

    <div class="flex items-center gap-2 text-[11px]">
      <span class="text-slate-400">UPTIME</span>
      <span class="font-mono text-slate-200">{{ uptime }}</span>
    </div>

    <div class="flex items-center gap-2 text-[11px]">
      <span
        :class="store.wsConnected ? 'bg-emerald-400' : 'bg-rose-400'"
        class="h-2 w-2 rounded-full animate-pulse"
      />
      <span class="text-slate-300">
        {{ store.wsConnected ? "STREAMING" : "OFFLINE" }}
      </span>
    </div>
  </header>
</template>
