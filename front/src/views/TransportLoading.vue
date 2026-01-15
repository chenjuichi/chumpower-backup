<template>
  <div class="wrap" :style="wrapStyle" aria-live="polite">
    <!-- width=0 時先不要渲染動畫，避免計算異常 -->
    <div
      v-if="safeWidth > 0"
      class="moving"
      :class="movingClass"
      :style="{ color: mainColor }"
    >
      <!-- 車體 SVG（Forklift / AGV） -->
      <img
        class="vehicle"
        :src="vehicleSrc"
        :style="{ width: vehicleSize + 'px', height: vehicleSize + 'px' }"
        alt="vehicle"
        draggable="false"
      />

      <!-- AGV 警示燈（可選） -->
      <span
        v-if="mode === 'agv'"
        class="beacon"
        :style="{ background: accentColor }"
      ></span>
    </div>

    <!-- 軌道 -->
    <div v-if="safeWidth > 0" class="track" :style="{ background: mainColor }"></div>

    <!-- 右側小文字（可選） -->
    <span v-if="safeWidth > 0 && showText" class="hint" :style="{ color: mainColor }">
      {{ textByStatus }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// ✅ 用你專案 assets 的路徑（請把 svg 放到 src/assets/）
import forkliftSvg from '@/assets/icon-forklift.svg?url'
// 如果你有 AGV 的 svg，再放一份；沒有就先沿用 forklift
// import agvSvg from '@/assets/icon-agv.svg?url'

const props = defineProps({
  mode: { type: String, default: 'forklift' },              // 'forklift' | 'agv'
  status: { type: String, default: 'sending' },             // 'idle' | 'sending' | 'success' | 'error'
  width: { type: Number, default: 220 },
  top: { type: Number, default: 30 },
  left: { type: Number, default: 0 },
  showText: { type: Boolean, default: true },

  // ✅ 新增：幾秒跑完一趟（越大越慢）
  durationSec: { type: Number, default: 6 },
})

const safeWidth = computed(() => Math.max(0, Number(props.width) || 0))

// 你放大後的車體尺寸
const vehicleSize = computed(() => 44)

// Forklift / AGV 的圖片來源
const vehicleSrc = computed(() => {
  if (props.mode === 'agv') {
    // 沒有 agv svg 時，先用 forklift 頂著
    return forkliftSvg
    // return agvSvg
  }
  return forkliftSvg
})

// ✅ 容器高度：車體 + padding
const wrapH = computed(() => vehicleSize.value + 16)

// ✅ 軌道離底部距離
const trackBottom = computed(() => 6)

// 顏色依狀態切換
const mainColor = computed(() => {
  switch (props.status) {
    case 'success': return '#2e7d32'
    case 'error':   return '#c62828'
    case 'idle':    return '#546e7a'
    case 'sending':
    default:        return '#1976d2'
  }
})

const accentColor = computed(() => {
  switch (props.status) {
    case 'error':   return '#ff5252'
    case 'success': return '#69f0ae'
    default:        return '#ffd54f'
  }
})

const textByStatus = computed(() => {
  if (props.status === 'success') return '已送出'
  if (props.status === 'error') return '送出失敗'
  if (props.mode === 'agv') return 'AGV 搬運中...'
  return '堆高機搬運中...'
})

const movingClass = computed(() => ({
  'moving-forklift': props.mode === 'forklift',
  'moving-agv': props.mode === 'agv',
  'state-success': props.status === 'success',
  'state-error': props.status === 'error',
  'state-idle': props.status === 'idle',
  'state-sending': props.status === 'sending',
}))

// ✅ duration 用 prop 控制（秒）
const safeDuration = computed(() => {
  const v = Number(props.durationSec)
  return Number.isFinite(v) ? Math.max(0.2, v) : 6
})

const wrapStyle = computed(() => ({
  position: 'relative',
  width: safeWidth.value + 'px',
  height: wrapH.value + 'px',
  top: props.top + 'px',
  left: props.left + 'px',

  '--wrap-h': `${wrapH.value}px`,
  '--track-bottom': `${trackBottom.value}px`,
  '--move-end': `${Math.max(0, safeWidth.value - 10)}px`,
  '--duration': `${safeDuration.value}s`,
}))
</script>

<style scoped>
.wrap{
  overflow: hidden;
  height: var(--wrap-h);
}

/* 軌道 */
.track{
  position:absolute;
  left:0;
  right:0;
  bottom: var(--track-bottom);
  height: 2px;
  opacity: .22;
}

/* 右側提示文字 */
.hint{
  position:absolute;
  right:0;
  top:-2px;
  font-size: 12px;
  opacity: .85;
  white-space: nowrap;
}

/* 移動容器 */
.moving{
  position:absolute;
  left:0;
  bottom: calc(var(--track-bottom) + 2px);
  width: 70px;
  height: 60px;

  animation-name: move-x;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  animation-duration: var(--duration);
}

/* 車體 */
.vehicle{
  position:absolute;
  left:0;
  bottom:0;
  user-select:none;
  pointer-events:none;
}

/* AGV 燈號 */
.beacon{
  position:absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  right: 10px;
  top: 2px;
  opacity: .9;
  animation: beacon-blink .55s ease-in-out infinite;
}

/* 成功/失敗停住（你要停住就保留） */
.state-error{
  animation: none;
}
.state-success{
  animation: none;
  transform: translateX(var(--move-end));
}

@keyframes move-x{
  0%   { transform: translateX(-90px); opacity: 0; }
  10%  { opacity: 1; }
  90%  { opacity: 1; }
  100% { transform: translateX(var(--move-end)); opacity: 0; }
}

@keyframes beacon-blink{
  0% { transform: scale(0.85); opacity: .25; }
  50%{ transform: scale(1.05); opacity: 1; }
  100%{ transform: scale(0.85); opacity: .25; }
}
</style>
