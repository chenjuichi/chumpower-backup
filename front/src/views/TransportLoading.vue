<template>
  <div class="wrap" :style="wrapStyle" aria-live="polite">
    <!-- 依 mode 切動畫主體 -->
    <div
      class="moving"
      :class="movingClass"
      :style="{ color: mainColor }"
    >
      <!-- 貨物 / 料箱（在前面） -->
      <v-icon class="cargo" :size="cargoSize">
        {{ cargoIcon }}
      </v-icon>

      <!-- 交通工具 icon（在後面） -->
      <v-icon class="vehicle" :size="vehicleSize">
        {{ vehicleIcon }}
      </v-icon>

      <!-- 警示燈（AGV 特有，可選） -->
      <span v-if="mode === 'agv'" class="beacon" :style="{ background: accentColor }"></span>
    </div>

    <!-- 軌道 -->
    <div class="track" :style="{ background: mainColor }"></div>

    <!-- 右側小文字（可選） -->
    <span v-if="showText" class="hint" :style="{ color: mainColor }">
      {{ textByStatus }}
    </span>
  </div>
</template>

<script setup>
import { ref, defineComponent, defineProps, computed, watch, onMounted, onBeforeUnmount, onUnmounted, onBeforeMount, onDeactivated } from 'vue';

//=== component name ==
defineComponent({
  name: 'TransportLoading'
});

const props = defineProps({
  /** 'forklift' | 'agv' */
  mode: { type: String, default: 'forklift' },

  /** 'idle' | 'sending' | 'success' | 'error' */
  status: { type: String, default: 'sending' },

  /** 位置/尺寸 */
  width: { type: Number, default: 220 },
  top: { type: Number, default: 30 },
  left: { type: Number, default: 180 },

  // 是否顯示文字提示
  showText: { type: Boolean, default: true },
})


// icon 選擇（你也可以改成更符合你現場的 mdi）
const vehicleIcon = computed(() => (props.mode === 'agv' ? 'mdi-robot-industrial' : 'mdi-forklift'))
const cargoIcon = computed(() => (props.mode === 'agv' ? 'mdi-package-variant-closed' : 'mdi-package-variant'))

const vehicleSize = computed(() => (props.mode === 'agv' ? 22 : 22))
const cargoSize = computed(() => 18)

// 顏色依狀態切換（可依你喜好改色名/色碼）
const mainColor = computed(() => {
  switch (props.status) {
    case 'success': return '#2e7d32' // 綠
    case 'error':   return '#c62828' // 紅
    case 'idle':    return '#546e7a' // 灰藍
    case 'sending':
    default:        return '#1976d2' // 藍
  }
})

// 強調色（AGV 燈號用）
const accentColor = computed(() => {
  switch (props.status) {
    case 'error':   return '#ff5252'
    case 'success': return '#69f0ae'
    default:        return '#ffd54f'
  }
})

// 文字依狀態
const textByStatus = computed(() => {
  if (props.status === 'success') return '已送出'
  if (props.status === 'error') return '送出失敗'
  if (props.mode === 'agv') return 'AGV 搬運中...'
  return '堆高機搬運中...'
})

// 動畫 class
const movingClass = computed(() => ({
  'moving-forklift': props.mode === 'forklift',
  'moving-agv': props.mode === 'agv',
  'state-success': props.status === 'success',
  'state-error': props.status === 'error',
  'state-idle': props.status === 'idle',
  'state-sending': props.status === 'sending',
}))

const wrapStyle = computed(() => ({
  position: 'relative',
  width: props.width + 'px',
  height: wrapH.value + 'px',
  top: props.top + 'px',
  left: props.left + 'px',

  '--move-end': `${props.width - 10}px`,            // 動畫終點 = width - 一點緩衝
  '--wrap-h': `${wrapH.value}px`,
  '--track-bottom': `${trackBottom.value}px`,
}))

// ✅ 容器高度：用最大 icon + padding
const wrapH = computed(() => Math.max(vehicleSize.value, cargoSize.value) + 14)

// ✅ 軌道高度位置：在底部再往上幾 px
const trackBottom = computed(() => 6) // 離底部的距離
</script>

<style lang="scss" scoped>
.wrap {
  overflow: hidden;
  height: var(--wrap-h);    // ✅ 自動高度
}

// ✅ 軌道永遠在底部附近
.track {
  position: absolute;
  left: 0;
  right: 0;
  bottom: var(--track-bottom);
  height: 2px;
  opacity: 0.22;
}

// ✅ 移動群組：用 bottom 對齊，避免 icon 放大後切到
.moving {
  position: absolute;
  left: 0;
  bottom: calc(var(--track-bottom) + 2px); 	// ✅ 貼著軌道上方
  display: flex;
  align-items: flex-end;   	// ✅ icon 底部對齊
  gap: 8px;
  animation: move-x 2.6s linear infinite;
  animation-duration: calc(var(--move-end) / 140 * 1s);
}

// 右側提示文字
.hint{
  position:absolute;
  right: 0;
  top: -2px;
  font-size: 12px;
  opacity: .85;
  white-space: nowrap;
}

// 貨物微晃
.cargo{
  animation: cargo-bounce .6s ease-in-out infinite alternate;
}

// 車體微震
.vehicle{
  animation: vehicle-bump .4s linear infinite;
}

/* AGV 警示燈 */
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

// Forklift：較快一點
.moving-forklift{
  animation-duration: 1.45s;
}

// AGV：稍慢一點 + 更平穩
.moving-agv{
  animation-duration: 1.85s;
}
.moving-agv .vehicle{
  animation: none; 	// AGV 更穩：不抖
}

/* success / error：如果想「停住」*/
.state-error{
    animation: none;
}

.state-success{
  animation: none;
  transform: translateX(var(--move-end));
}

// 由左到右（translateX 的終點和 width 配合）, 預設 width=220

@keyframes move-x{
  0%   { transform: translateX(-70px); opacity: 0; }
  10%  { opacity: 1; }
  90%  { opacity: 1; }
  100% { transform: translateX(var(--move-end)); opacity: 0; }
}

@keyframes cargo-bounce{
  from { transform: translateY(2px); }
  to   { transform: translateY(0); }
}

@keyframes vehicle-bump{
  0% { transform: translateY(0); }
  50%{ transform: translateY(1px); }
  100%{ transform: translateY(0); }
}

@keyframes beacon-blink{
  0% { transform: scale(0.85); opacity: .25; }
  50%{ transform: scale(1.05); opacity: 1; }
  100%{ transform: scale(0.85); opacity: .25; }
}
</style>
