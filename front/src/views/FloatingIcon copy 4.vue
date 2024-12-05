<template>
  <div class="is-flex is-justify-content-center is-align-items-center">
    <div class="options box container">
      <button :class="['button is-info', { 'is-light': !state.isEnabled }]" @click="toggleDraggable">
        Drag is {{ state.isEnabled ? "enabled" : "disabled" }}
      </button>
      <button :class="['button is-info', { 'is-light': !state.isRestricted }]" @click="toggleRestriction">
        Dropzone zone restriction is {{ state.isRestricted ? "enabled" : "disabled" }}
      </button>
    </div>

    <div class="box container dropzone">
      <!-- 主按鈕與彈出圖示容器 -->
      <div class="icon-container" :style="getContainerStyle">
				<!-- 主按鈕 -->
				<button
					class="button is-primary draggable main-icon"
					:style="{
						display: 'flex',
						justifyContent: 'center',
						alignItems: 'center',
						background: '#000',
						color: '#fff',
						borderRadius: '50%',
						height: '36px',
						width: '36px',
						cursor: state.iconsVisible ? 'pointer' : 'move',
					}"
					@click="handleMainButtonClick"
					@mouseover="mhandleMouseOver"
					@mouseleave="mhandleMouseLeave"
				>
					<i
						class="fa-solid fa-bars fa-fade"
						style="color: #fff; background: #000; font-size: 18px; transform: translateY(1px);"
					/>
				</button>

				<!-- 彈出圖示 -->
				<div class="icon-group" :class="{ active: state.iconsVisible }">
					<button
						v-for="(icon, index) in icons"
						:key="index"
						:class="['icon', icon.color]"
						@click.stop="handleIconClick(icon.class)"
					>
						<i
							:class="icon.class"
							style="font-size: 18px; transform: translateY(1px);"
						/>
					</button>
				</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref,reactive, computed, onMounted, watch, defineComponent } from "vue";
import interact from "interactjs";

import eventBus from '../mixins/enentBus.js';

//=== component name ===
defineComponent({
  name: "FloatingIcon",
});

//=== props ==
const props = defineProps({
  showFooter: Boolean,		// 父組件傳遞的初始值
});

//=== emits ==
const emit = defineEmits(['update:showFooter']);

//=== data ===
const localShowFooter = ref(props.showFooter);
const cursorStyle = ref("default");
const state = reactive({
  isEnabled: true,
  isRestricted: true,
  item: {
    x: 0,
    y: 0,
  },
  iconsVisible: false, // 控制圖示顯示的狀態
});

// 彈出圖示的資料
const icons = [
  { class: "fa-solid fa-laptop", color: "red" },
  { class: "fa-solid fa-palette", color: "green" },
];

//=== computed ===
// 主按鈕與彈出圖示容器的實時位置
const getContainerStyle = computed(() => {
  return `transform: translate(${state.item.x}px, ${state.item.y}px)`;
});

watch(() => props.showFooter, (newValue) => {
  localShowFooter.value = newValue; // 同步父層變更到 localShowFooter
});

//=== mounted ===
onMounted(() => {
  initDraggable();
});

//=== methods ===
const mhandleMouseOver = () => {
	console.log("cursor state:",state.iconsVisible)
	cursorStyle.value = "default"; // 滑鼠懸停時不顯示手形
};

const mhandleMouseLeave = () => {
	console.log("cursor state:",state.iconsVisible)
	cursorStyle.value = "default"; // 離開按鈕時可保持樣式
};

const handleMainButtonClick = (event) => {
  console.log('click main button');
  if (state.iconsVisible) {
    // 如果彈出圖示已顯示，隱藏圖示
    state.iconsVisible = false;
  } else {
    // 如果彈出圖示未顯示，滑出圖示
    state.iconsVisible = true;
  }
};

const handleIconClick = (iconClass) => {
  console.log('click icon button');

  if (iconClass === 'fa-solid fa-laptop' && state.iconsVisible) {
    // 切換 localShowFooter 的值
    localShowFooter.value = !localShowFooter.value;
    emit('update:showFooter', localShowFooter.value);
    console.log('Toggled showFooter:', localShowFooter.value);
  }
};

const toggleDraggable = () => {
  if (state.isEnabled) {
    interact(".draggable").unset();
  } else {
    initDraggable();
  }
  state.isEnabled = !state.isEnabled;
};

const toggleRestriction = () => {
  state.isRestricted = !state.isRestricted;
  interact(".draggable").unset();
  initDraggable();
};

const initDraggable = () => {
  let restriction = null;
  if (state.isRestricted) {
    restriction = {
      restriction: ".dropzone",
      elementRect: { top: 0, left: 0, bottom: 1, right: 1 },
    };
  }

  interact(".draggable").draggable({
    restrict: restriction,
    onmove: (e) => {
      // 更新拖曳位置
      state.item.x += e.dx;
      state.item.y += e.dy;
    },
    onend: (e) => {
      // 拖曳結束時，不改變圖示顯示狀態
      console.log("Drag ended at:", state.item.x, state.item.y);
    },
  });
};

// 切換圖示顯示（僅按下按鈕時觸發）
const toggleIcons = () => {
  state.iconsVisible = !state.iconsVisible;
};
</script>

<style lang="scss" scoped>
.options {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  margin: auto !important;
  z-index: 10;
}

.dragzone,
.dropzone {
  height: 50vh;
}

.draggable {
  touch-action: none;
  user-select: none;
}

.icon-container {
  position: absolute;
}

.main-icon {
  z-index: 2;
}
/*
.icon-group {
  position: absolute;
  top: 100%; 				// 主按鈕下方
  left: 0;
  display: flex;
  gap: 0.5rem; 			// 圖示間距
  transition: opacity 0.3s ease; 	// 只使用 opacity 的過渡
  opacity: 0;
}

// 滑出時顯示
.icon-group.active {
  opacity: 1;
}
*/

.icon-group {
  position: absolute;
  top: 30%; 			// 主按鈕下方
  left: 0;
  display: flex;
  gap: 0.2rem; 		// 圖示間距
  transform: translateX(0);
  transition: transform 0.3s ease, opacity 0.3s ease;
  opacity: 0;
}

// 滑出時顯示
.icon-group.active {
  opacity: 1;
  transform: translateX(-100%);
}

.icon {
  width: 3rem;
  height: 3rem;
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  background-color: gray;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  transition: background-color 0.3s;
}

.icon.red {
  background-color: #FF5C5C;
	color: #000;
	border-radius: 50%;
	height: 36px;
	width: 36px;
	display: flex;
	justify-content: center;
	align-items: center;
}

.icon.green {
  background-color: #5CD1FF;
	color: #000;
	border-radius: 50%;
	height: 36px;
	width: 36px;
	display: flex;
	justify-content: center;
	align-items: center;
}
</style>
