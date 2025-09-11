<template>
  <span
    v-if="show"
    style="font-size:18px; margin-left:10px; margin-right:10px; color:yellow;"
  >
    {{ displayTime }}
  </span>
</template>

<script setup>
import { ref, watch, onUnmounted, defineComponent, defineExpose, defineProps, defineEmits } from "vue";

//=== component name ==
defineComponent({
  name: 'TimerDisplay'
});

const props = defineProps({
  autoStart: { type: Boolean, default: false },
  isPaused: { type: Boolean, default: true },
  show: { type: Boolean, default: true },
});
//const emit = defineEmits(["update:time", "pause", "resume", "update:modelValue", 'update:isPaused']);
const emit = defineEmits(["update:time", "pause", "resume", 'update:isPaused']);

const displayTime = ref("00:00:00");
//const isPaused = ref(props.modelValue);
const paused = ref(props.isPaused);

let startTime = null;
let elapsed = 0;
let intervalId = null;

function format(ms) {
  const totalSec = Math.floor(ms / 1000);
  const h = String(Math.floor(totalSec / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
  const s = String(totalSec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function start() {
  if (intervalId) return;
  startTime = Date.now();
  intervalId = setInterval(update, 1000);
  paused.value = false;
  //emit("update:modelValue", false);
  emit("update:isPaused", false);

  emit("resume", elapsed);
  update();
}

function pause() {
  if (paused.value) return;
  paused.value = true;

  // 只在有有效計時時才累加
  if (intervalId && startTime) {
    elapsed += Date.now() - startTime;
  }

  clearInterval(intervalId);
  intervalId = null;
  startTime = null;
  //elapsed += Date.now() - startTime;
  //emit("update:modelValue", true);
  emit("update:isPaused", true);
  emit("pause", elapsed);
  // 停下來也刷新一次
  displayTime.value = format(elapsed);
  emit("update:time", elapsed);
}

function resume() {
  if (!paused.value) return;
  paused.value = false;
  startTime = Date.now();
  intervalId = setInterval(update, 1000);
  //emit("update:modelValue", false);
  emit("'update:isPaused'", false);

  emit("resume", elapsed);
  update();
}

function reset() {
  clearInterval(intervalId);
  intervalId = null;
  startTime = null;
  elapsed = 0;
  paused.value = true;
  displayTime.value = "00:00:00";
  //emit("update:modelValue", true);
  emit("update:isPaused", true);
  emit("update:time", 0);
}

function update() {
  const now = Date.now();
  //const total = elapsed + (now - startTime);
  const total = elapsed + (startTime ? (now - startTime) : 0);
  displayTime.value = format(total);
  emit("update:time", total);
}

/**
 * ✅ 外部可設定秒數（從後端還原時用）
 * @param {number} seconds
 */
function setElapsedTime(seconds) {
  //elapsed = seconds * 1000;  // 換算成毫秒
  elapsed = Math.max(0, Number(seconds) || 0) * 1000;
  // 若正在跑，從現在重新起算
  if (!paused.value && intervalId) startTime = Date.now();
  update();
  //displayTime.value = format(elapsed);
  //emit("update:time", elapsed);
}

/**
 * ✅ 一次設定時間與狀態（從後端還原）
 * @param {number} seconds - 已累積秒數
 * @param {boolean} paused - 是否暫停
 */
function setState(seconds, paused) {
  setElapsedTime(seconds);

  if (paused) {
    pause();  // 確保停止
  } else {
    resume(); // 繼續跑
  }
}

function getElapsedMs() {
  // 目前累積的毫秒 +（如果正在跑）本段已經過的毫秒
  /*
  if (intervalId && startTime) {
    return elapsed + (Date.now() - startTime);
  }
  return elapsed;
  */
  const now = Date.now();
  return elapsed + (startTime ? (now - startTime) : 0);
}

// 父層變更 v-model:isPaused 時，同步處理
watch(
  () => props.isPaused,
  (val) => {
    if (val === paused.value) return;
    val ? pause() : resume();
  }
);

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});

//if (props.autoStart) start();
// 若要一掛上就跑（且一開始不是暫停）
if (props.autoStart && !props.isPaused) start();

defineExpose({ start, pause, resume, reset, setElapsedTime, setState, getElapsedMs });
</script>