<template>
  <div class="is-flex is-justify-content-center is-align-items-center">
		<!--
    <div class="options box container">
      <button :class="['button is-info', { 'is-light': !state.isEnabled }]" @click="toggleDraggable">
        Drag is {{ state.isEnabled ? "enabled" : "disabled" }}
      </button>
      <button :class="['button is-info', { 'is-light': !state.isRestricted }]" @click="toggleRestriction">
        Dropzone zone restriction is {{ state.isRestricted ? "enabled" : "disabled" }}
      </button>
    </div>
		-->
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
						background: '#3664d9',
						color: '#fff',
						borderRadius: '50%',
						height: '36px',
						width: '36px',
					}"
					@click="handleMainButtonClick"
					@mouseover="mhandleMouseOver"
					@mouseleave="mhandleMouseLeave"
				>
					<i
						class="fa-solid fa-bars fa-fade"
						style="color: #fff; background: #3664d9; font-size: 18px; transform: translateY(1px);"
					/>
				</button>

				<!-- 彈出圖示 -->
				<div class="icon-group" :class="{ active: state.iconsVisible }">
					<button
						v-for="(icon, index) in icons"
						:key="index"
						:class="['icon', icon.color]"
						@click="handleIconClick(icon.class)"
					>
						<i
							:class="icon.class"
							style="font-size: 18px; transform: translateY(1px);"
						/>
					</button>
				</div>

				<!-- ColorPicker -->
				<ColorPicker
					v-if="showColorPicker"
					v-model:colorValue="localNavBarColor"
  				@update:colorValue="updateNavBarColor"
					@close="showColorPicker = false"
					style="position: relative; top: 5px; right: 30px;"
				/>


      </div>
    </div>
  </div>

  <!--WebRTC-->
  <WebRTC
    v-if="showWebRTC"
    class="webrtc-container"
    @close="showWebRTC = false"
    :targetRouteName=routeName
  />
</template>

<script setup>
import { ref,reactive, computed, onMounted, watch, defineComponent } from "vue";
import { useRoute } from 'vue-router'; // Import useRouter
import interact from "interactjs";

import ColorPicker from './ColorPicker.vue';
import WebRTC from './WebRTC.vue';

//import eventBus from '../mixins/enentBus.js';

//=== component name ===
defineComponent({
  name: "FloatingIcon",
});

//=== props ==
const props = defineProps({
  showFooter: Boolean,

	navBarColor: String,
});

//=== emits ==
const emit = defineEmits(['update:showFooter', 'update:navBarColor']);

//=== data ===
const showColorPicker = ref(false);
const showWebRTC = ref(false);

const localShowFooter = ref(props.showFooter);

const localNavBarColor = ref(props.navBarColor);
const state = reactive({
  isEnabled: true,
  isRestricted: false,
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
  { class: "fa-solid fa-camera", color: "yellow" },
];

const route = useRoute();               // Initialize router

//=== computed ===
// 主按鈕與彈出圖示容器的實時位置
const getContainerStyle = computed(() => {
  return `transform: translate(${state.item.x}px, ${state.item.y}px)`;
});

const routeName = computed(() => route.name);

watch(() => props.showFooter, (newValue) => {
  localShowFooter.value = newValue; // 同步父層變更到 localShowFooter
});

//=== mounted ===
onMounted(() => {
  initDraggable();
});

//=== methods ===
const updateNavBarColor = (newColor) => {
  localNavBarColor.value = newColor; 										// 更新本地顏色
  emit('update:navBarColor', newColor); 	// 通知父層更新
  console.log('Updated navBarColor:', newColor);
};

const mhandleMouseOver = () => {
	console.log("cursor state:",state.iconsVisible)
	//cursorStyle.value = "default"; // 滑鼠懸停時不顯示手形
};

const mhandleMouseLeave = () => {
	console.log("cursor state:",state.iconsVisible)
	//cursorStyle.value = "default"; // 離開按鈕時可保持樣式
};

const handleMainButtonClick = (event) => {
  console.log('click main button');
  if (state.iconsVisible) {
    state.iconsVisible = false;				// 如果彈出圖示已顯示，隱藏圖示
		showColorPicker.value = false;
    showWebRTC.value = false;
  } else {
    state.iconsVisible = true;				// 如果彈出圖示未顯示，滑出圖示
  }
};

const handleIconClick = (iconClass) => {
  console.log('click icon button');

  if (iconClass === 'fa-solid fa-laptop' && state.iconsVisible) {
    localShowFooter.value = !localShowFooter.value;							// 切換 localShowFooter 的值
    emit('update:showFooter', localShowFooter.value);
    //console.log('Toggled showFooter:', localShowFooter.value);
  }

	if (iconClass === 'fa-solid fa-palette' && state.iconsVisible) {
		showColorPicker.value = !showColorPicker.value;
	}

	if (iconClass === 'fa-solid fa-camera' && state.iconsVisible) {
		showWebRTC.value = !showWebRTC.value;
	}
};
/*
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
*/
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

//.dragzone,
//.dropzone {
//  height: 50vh;
//}

.dropzone {
  height: 90vh;
	//width: 20px;
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
	top: 1px;
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
  background-color: #00E676;
	color: #000;
	border-radius: 50%;
	height: 36px;
	width: 36px;
	display: flex;
	justify-content: center;
	align-items: center;
}

.icon.yellow {
  background-color: #FFF176;
	color: #000;
	border-radius: 50%;
	height: 36px;
	width: 36px;
	display: flex;
	justify-content: center;
	align-items: center;
}

.webrtc-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1000; /* 確保它顯示在最上層 */
  background: white;
  box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.2);
  padding: 20px;
  border-radius: 8px;
}

</style>
