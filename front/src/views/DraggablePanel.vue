<template>
	<div
		class="draggable-panel"
		:style="panelStyle"
		@mousedown="startDrag"
		@dblclick="togglePanelFlag"
	>
		<slot />
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
	initX: { type: Number, default: 100 },
	initY: { type: Number, default: 100 },
	isDraggable: { type: Boolean, default: true },
})

//const x = ref(props.initX);
//const y = ref(props.initY);
const x = ref(0);
const y = ref(0);
const dragging = ref(false);
const offsetX = ref(0);
const offsetY = ref(0);
const panel_flag = ref(false);

// 監聽 props 的變化，更新 x 和 y
watch(() => props.initX, (val) => x.value = val)
watch(() => props.initY, (val) => y.value = val)
/*
watch(() => props.initX, (newVal) => {
  x.value = newVal
  console.log("x.value:",x.value)
})

watch(() => props.initY, (newVal) => {
  y.value = newVal
  console.log("y.value:",y.value)
})
*/
// 計算 panel 的 style
const panelStyle = computed(() => ({
	position: 'absolute',
	top: `${y.value}px`,
	left: `${x.value}px`,
	//cursor: props.isDraggable ? 'move' : 'default',
	cursor: props.isDraggable && panel_flag.value ? 'move' : 'default',
	//border: panel_flag.value ? '2px solid blue' : '2px solid transparent',
	//cursor: panel_flag.value ? 'move' : 'default',
	//zIndex: panel_flag.value ? 9999 : 1,
	//background: '#fff',
	//padding: '10px',
	//boxShadow: '0 2px 8px rgba(0,0,0,0.2)'

}))

// 初始化初始座標（重要）
onMounted(() => {
	console.log("DraggablePanel.vue, mounted()...");

  x.value = props.initX
  y.value = props.initY
})

// 切換 panel_flag，僅當 isDraggable 為 true 時才有效
const togglePanelFlag = () => {
	console.log("DraggablePanel.vue, togglePanelFlag()...");

	if (!props.isDraggable) return;
	panel_flag.value = !panel_flag.value
}

// 開始拖曳
const startDrag = (e) => {
	//if (!panel_flag.value) return;
	if (!props.isDraggable || !panel_flag.value) return;
	dragging.value = true
	offsetX.value = e.clientX - x.value
	offsetY.value = e.clientY - y.value
	document.addEventListener('mousemove', onDrag)
	document.addEventListener('mouseup', stopDrag)
}

// 拖曳進行中
const onDrag = (e) => {
	if (!dragging.value) return;
	x.value = e.clientX - offsetX.value;
	y.value = e.clientY - offsetY.value;

}

// 拖曳結束
const stopDrag = () => {
	dragging.value = false
	document.removeEventListener('mousemove', onDrag)
	document.removeEventListener('mouseup', stopDrag)
}
</script>

<style lang="scss" scoped>
.draggable-panel {
	user-select: none;
}
</style>

