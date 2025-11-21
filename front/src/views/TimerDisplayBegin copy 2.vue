<script setup>
import { ref, defineComponent, computed, watch, onMounted, onBeforeUnmount } from 'vue'

//=== component name ==
defineComponent({ name: 'TimerDisplayBegin' });

/**
 * Props
 * - autoStart: 掛載後若 isPaused=false 且 show=true，是否自動開始
 * - isPaused: 由父層控制是否暫停（支援 v-model:isPaused）
 * - show: 顯示/隱藏，隱藏時會自動 stop
 * - fontSize: 顯示字體大小
 */
const props = defineProps({
  autoStart: { type: Boolean, default: false },
  isPaused:  { type: Boolean, default: true },
  show:      { type: Boolean, default: true },
  fontSize:  { type: [Number, String], default: 18 },

  displayMs:  { type: Number, default: null },
  initialMs:  { type: Number, default: 0 },   // 初始毫秒
})

/**
 * Emits
 * - update:time: 每次 tick 時回傳累積毫秒（ms）
 * - update:isPaused: 供 v-model:isPaused 雙向綁定
 */
const emit = defineEmits(['update:time', 'update:isPaused'])

/* ----- 內部狀態 ----- */
const elapsedMs = ref(0)     // 目前累積的毫秒
//const elapsedMs = ref(props.initialMs || 0)
let intervalId = null        // setInterval handler

/* ----- 轉字串顯示（HH:MM:SS）----- */
const hhmmss = computed(() => {
  const sec = Math.floor((elapsedMs.value || 0) / 1000)
  const h = String(Math.floor(sec / 3600)).padStart(2, '0')
  const m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0')
  const s = String(sec % 60).padStart(2, '0')
  return `${h}:${m}:${s}`
})

const shownMs = computed(() => props.displayMs ?? elapsedMs.value)

/* ----- 核心：開始/停止/暫停/恢復/重置 ----- */
function _tick() {
  // 有凍結值就不要再累加或對外 emit
  if (props.displayMs !== null) return

  elapsedMs.value += 1000
  emit('update:time', elapsedMs.value)
  console.log('TimerDisplayBegin.vue, [TD] tick', elapsedMs.value)
}

function start() {
  // 僅當可見且非暫停時才啟動
  if (!props.show) return
  if (intervalId) return
  if (props.isPaused) return
  console.log('[TD] start')
  intervalId = setInterval(_tick, 1000)
}

function stop() {
  if (intervalId) {
    console.log('[TD] stop')
    clearInterval(intervalId)
    intervalId = null
  }
}

function pause() {
  stop()
  emit('update:isPaused', true)
}

function resume() {
  start()
  emit('update:isPaused', false)
}

function reset() {
  stop()
  elapsedMs.value = 0
  emit('update:time', 0)
}

/**
 * setState：由父層 (hook) 用於還原狀態
 * @param {number} seconds - 從後端帶回的有效秒數
 * @param {boolean} paused - 是否暫停
 */
function setState(seconds, paused) {
  const sec = Number(seconds) || 0
  elapsedMs.value = sec * 1000
  emit('update:time', elapsedMs.value)
  if (paused) stop()
  else start()
}

/** setElapsedTime：毫秒版，提供相容 API */
function setElapsedTime(ms) {
  const v = Number(ms) || 0
  elapsedMs.value = v
  emit('update:time', elapsedMs.value)
}

/** 讓父層/Hook 讀回目前毫秒數 */
function getElapsedMs() {
  return elapsedMs.value || 0
}

/* ----- 父層變更 isPaused/ show 的反應 ----- */
/*
watch(
  () => props.isPaused,
  (val) => {

    if (val) stop()
    else start()
  },
  { immediate: true }
)
*/
watch(() => props.isPaused, (paused, old) => {
  console.log('[TD] isPaused changed', old, '→', paused)
  if (!!paused) stop()
  else start()
}, { immediate: true })

watch(() => props.show, (v) => {
  if (!v) stop()
    else if (!props.isPaused) start()
})

watch(() => props.displayMs, (v) => {
  if (v !== null) {
    // 進入凍結 → 停止內部加總
    stop()
  } else {
    // 解除凍結 → 若未暫停且顯示中，恢復 interval
    if (!props.isPaused && props.show) start()
  }
})

watch(() => props.initialMs, (ms) => {
  if (props.displayMs === null && typeof ms === 'number') {
    elapsedMs.value = ms
  }
})

/* ----- 掛載/卸載行為 ----- */
onMounted(() => {
  // 測試timer
  console.log('%c[TD] mounted', 'color:#2962FF')
  //

  elapsedMs.value = props.initialMs || 0

  if (props.autoStart && !props.isPaused && props.show) {
    start()
  }
})

onBeforeUnmount(() => {
  stop()
})

/* ----- 對外暴露給 hook 呼叫（非常重要）----- */
//defineExpose({
//  start, stop, pause, resume, reset,
//  setState, setElapsedTime, getElapsedMs,
//})

defineExpose({
  //start, stop, pause: stop, resume: start, reset,
  //setState, setElapsedTime, getElapsedMs
  start, stop, pause, stop, resume, start, reset,
  setState, setElapsedTime, getElapsedMs,
})
</script>

<template>
  <span
    :style="{
      fontSize: typeof fontSize === 'number' ? `${fontSize}px` : String(fontSize),
      fontVariantNumeric: 'tabular-nums',
      display: 'inline-block',
      minWidth: '88px',
      textAlign: 'right'
    }"
  >
    {{ show ? hhmmss : ''  }}
  </span>
</template>
