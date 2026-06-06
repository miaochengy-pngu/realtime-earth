<script setup lang="ts">
import { computed } from "vue";
import { useEarthStore } from "@/stores/earth";

const store = useEarthStore();
const s = computed(() => store.solar);

const kpColor = computed(() => {
  const kp = s.value?.kp_index ?? 0;
  if (kp >= 8) return "text-rose-300";
  if (kp >= 6) return "text-orange-300";
  if (kp >= 4) return "text-amber-300";
  return "text-emerald-300";
});

const auroraBar = computed(() => {
  const p = s.value?.aurora_probability_north ?? 0;
  return Math.round(p * 100);
});
</script>

<template>
  <div v-if="s" class="p-3 space-y-3">
    <!-- SDO image -->
    <div v-if="s.sdo_image_url" class="rounded-lg overflow-hidden border border-cyan-500/20 bg-black">
      <img
        :src="s.sdo_image_url + '?t=' + new Date(s.sdo_image_timestamp || s.timestamp).getTime()"
        alt="SDO solar image (HMI continuum)"
        class="w-full h-auto"
        loading="lazy"
      />
      <div class="px-2 py-1 text-[10px] text-slate-400 bg-space-900/60">
        SDO / HMI · NASA · refreshed on each push
      </div>
    </div>

    <!-- Kp + Storm -->
    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Kp index</span>
        <span class="stat-value" :class="kpColor">
          {{ s.kp_index?.toFixed(1) ?? "—" }}
        </span>
        <span class="text-[10px] text-slate-400">{{ s.kp_text || "—" }}</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Sunspot #</span>
        <span class="stat-value">{{ s.sunspot_number ?? "—" }}</span>
        <span class="text-[10px] text-slate-400">SILSO / SWPC</span>
      </div>
    </div>

    <!-- Aurora probability -->
    <div class="panel p-2">
      <div class="flex items-center justify-between mb-1">
        <span class="stat-label">Aurora probability (N)</span>
        <span class="text-[11px] font-mono text-cyan-200">
          {{ auroraBar }}%
        </span>
      </div>
      <div class="h-2 rounded-full bg-space-900 overflow-hidden">
        <div
          class="h-full transition-all duration-500"
          :class="auroraBar >= 60 ? 'bg-rose-400' : auroraBar >= 30 ? 'bg-amber-300' : 'bg-cyan-400'"
          :style="{ width: auroraBar + '%' }"
        />
      </div>
    </div>

    <div class="grid grid-cols-2 gap-2">
      <div class="stat panel p-2">
        <span class="stat-label">Solar wind</span>
        <span class="stat-value text-cyan-200">
          {{ s.solar_wind_speed_kms?.toFixed(0) ?? "—" }}
        </span>
        <span class="text-[10px] text-slate-400">km/s</span>
      </div>
      <div class="stat panel p-2">
        <span class="stat-label">Density</span>
        <span class="stat-value text-cyan-200">
          {{ s.solar_wind_density_pcm3?.toFixed(1) ?? "—" }}
        </span>
        <span class="text-[10px] text-slate-400">p/cm³</span>
      </div>
      <div class="stat panel p-2 col-span-2">
        <span class="stat-label">X-ray class</span>
        <span class="stat-value text-fuchsia-200">{{ s.xray_class ?? "—" }}</span>
        <span class="text-[10px] text-slate-400">GOES primary</span>
      </div>
    </div>

    <div class="text-[10px] text-slate-500 leading-relaxed">
      Data: NOAA
      <a
        href="https://www.swpc.noaa.gov/"
        target="_blank"
        rel="noopener"
        class="text-cyan-300/80 hover:text-cyan-200 underline"
        >Space Weather Prediction Center</a
      >
      + NASA
      <a
        href="https://sdo.gsfc.nasa.gov/"
        target="_blank"
        rel="noopener"
        class="text-cyan-300/80 hover:text-cyan-200 underline"
        >SDO</a
      >.
    </div>
  </div>
  <div v-else class="p-3 text-slate-500 text-xs loading-dots">Fetching solar data</div>
</template>
