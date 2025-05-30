<template>
  <div
    class="led-draggable-panel"
    :style="{ zIndex: zIndex }"
    @mousedown="startDrag"
    @dblclick="toggleDrag"
  >
	<!--
    <p class="status">
      拖曳模式：
      <span :class="{ active: dragFlag }">{{ dragFlag ? 'ON' : 'OFF' }}</span>
    </p>
	-->
		<!-- 閃爍速度滑桿 -->
	<!--
		<div style="margin-bottom: 12px;">
		<v-slider
      v-model="alarm"
      :min="0.1"
      :max="2"
      :step="0.1"
      append-icon="mdi-alarm"
      label="閃爍速度"
      hide-details
			track-color="green"
    ></v-slider>
		<div style="text-align: center; font-size: 13px;">目前速度：{{ alarm.toFixed(1) }} 秒</div>
    </div>
	-->
		 <!-- 燈號顯示 -->
    <div class="led-container">
      <div v-for="led in activeLeds" :key="led.color" class="led-item">
        <div
          :class="{
            [`led-${led.color}`]: led.isActive,
            'led-off': !led.isActive
          }"
					:style="led.isActive ? { animationDuration: `${alarm}s` } : {}"
        ></div>
        <div class="led-label">{{ led.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, computed, onBeforeUnmount, watch, onMounted } from 'vue'

const props = defineProps({
  activeColor: String,
  zIndex: {
    type: Number,
    default: 1000
  }
})

//=== data ===
const dragFlag = ref(false)
const position = ref({ x: 100, y: 100 })
const isDragging = ref(false)
const offset = ref({ x: 0, y: 0 })

const alarm = ref(0.5) // 初始閃爍速度（秒）

// 每顆燈號對應顏色與名稱
const leds = [
  { color: 'green', 			label: '區域閒置' },
  { color: 'yellow', 			label: '物料進站' },
  { color: 'red', 				label: '等待運輸' },
  { color: 'blue', 				label: '機器人進站' },
  { color: 'SeaGreen', 		label: '物料出站' },
  { color: 'DarkOrange', 	label: '物料送達' },
]

//=== computed ===
const activeLeds = computed(() =>
  leds.map(led => ({
    ...led,
    isActive: led.color === props.activeColor
  }))
)
/*
// 動態更新 blink 動畫速度
watch(alarm, (newVal) => {
  const panel = document.querySelector('.led-draggable-panel')
  if (panel) {
    panel.style.setProperty('--blink-duration', `${newVal}s`)
  }
})

onMounted(() => {
  const panel = document.querySelector('.led-draggable-panel')
  if (panel) {
    panel.style.setProperty('--blink-duration', `${alarm.value}s`)
  }
})
*/

//=== method ===
const toggleDrag = () => {
  dragFlag.value = !dragFlag.value
}

const startDrag = (e) => {
  if (!dragFlag.value) return;

  isDragging.value = true;
  offset.value = {
    x: e.clientX - position.value.x,
    y: e.clientY - position.value.y,
  }
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
}

const onDrag = (e) => {
  if (isDragging.value) {
    position.value = {
      x: e.clientX - offset.value.x,
      y: e.clientY - offset.value.y,
    }
  }
}

const stopDrag = () => {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
}

onBeforeUnmount(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
})
</script>

<style lang="scss" scoped>
.led-draggable-panel {
  position: fixed;
  padding: 3px;
  border: 2px solid #ccc;
  background: white;
  border-radius: 8px;
  cursor: move;
  user-select: none;
  width: 420px;
	/*--blink-duration: 0.5s;*/
}

.status {
  font-size: 12px;
  margin-bottom: 8px;
  text-align: center;
}
.status .active {
  color: green;
  font-weight: bold;
}

:deep(.v-label ) {
  font-size: 12px;
}

.led-container {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
}

.led-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0px;
  width: 60px;
}

.led-label {
  margin-top: 4px;
  font-size: 11px;
	font-weight: 600;
  text-align: center;
  white-space: nowrap;
	overflow: hidden;
  text-overflow: ellipsis;
}

.led-off {
  width: 24px;
  height: 24px;
  background: #888;
  border-radius: 50%;
}

.led-green {
  width: 24px;
  height: 24px;
	color: #0f0;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
  //box-shadow: rgba(0, 0, 0, 0.2) 0 -1px 7px 1px, inset currentColor 0 -1px 9px,
  //  rgba(255, 0, 0, 0.5) 0 2px 12px;

	/*
  background-color: #0f0;
  box-shadow: 0 0 10px #0f0;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

.led-yellow {
  width: 24px;
  height: 24px;
	//color: #808002;
	color: #FDD835;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
  //box-shadow: rgba(0, 0, 0, 0.2) 0 -1px 7px 1px, inset currentColor 0 -1px 9px,
  //  rgba(255, 0, 0, 0.5) 0 2px 12px;
	/*
  background-color: #ff0;
	box-shadow: 0 0 10px #ff0;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

.led-red {
  width: 24px;
  height: 24px;
	color: #f00;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
	/*
  background-color: #f00;
  box-shadow: 0 0 10px #f00;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

.led-blue {
  width: 24px;
  height: 24px;
	color: #00f;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
	/*
  background-color: #00f;
  box-shadow: 0 0 10px #00f;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

.led-SeaGreen {
  width: 24px;
  height: 24px;
	color: #2e8b57;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
	/*
  background-color: #2e8b57;
  box-shadow: 0 0 10px #2e8b57;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

.led-DarkOrange {
  width: 24px;
  height: 24px;
	color: #ff9800;
  background-color: currentColor;
  box-shadow: 0 0 10px currentColor;
	/*
  background-color: #ff8c00;
  box-shadow: 0 0 10px #ff8c00;
	*/
  border-radius: 50%;
	animation-name: blink;
	animation-iteration-count: infinite;
	animation-timing-function: ease-in-out;
	/*
	animation: blinkRed var(--blink-duration) infinite;
  box-shadow: 0 0 10px currentColor;
	*/
}

@keyframes blink {
/*@keyframes blinkRed {*/
  0%, 100% {
    opacity: 1;
    transform: scale(1);
    box-shadow: 0 0 12px currentColor;
  }
	50% {
    opacity: 0.4;
		transform: scale(0.7);
    box-shadow: 0 0 2px currentColor;
  }
	/*
  50% {
    background-color: #fff;
  }
	*/
}

</style>

