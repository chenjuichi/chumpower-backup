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
					@click="toggleIcons"
					style="display: flex; justify-content: center; align-items: center; background: #000; color: #fff; border-radius: 50%; height: 36px; width: 36px;"
				>
					<i class="fa-solid fa-bars fa-fade"	style="color: #fff;	background: #000;	font-size: 18px; transform: translateY(1px);"	/>
        </button>

        <!-- 彈出圖示 -->
        <div class="icon-group" :class="{ active: state.iconsVisible }">
          <button v-for="(icon, index) in icons" :key="index" :class="['icon', icon.color]" @click="toggleIcons">
            <i :class="icon.class" style="font-size: 18px;	transform: translateY(1px);" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, defineComponent } from "vue";
import interact from "interactjs";

//=== component name ===
defineComponent({
  name: "FloatingIcon",
});

//=== watch ===
watch(localShowFooter, (newValue) => {
  console.log("FloatIcon.vue, watch(),", newValue)

  emit('update:showFooter', newValue);
});


//=== props ==
const props = defineProps({
  showFooter: Boolean,
});

//=== data ===
const localShowFooter = ref(props.showFooter);
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

//=== mounted ===
onMounted(() => {
  initDraggable();
});

//=== methods ===
/*
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
      state.item.x += e.dx;
      state.item.y += e.dy;
    },
  });
};
*/
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

// 切換圖示顯示
//const toggleIcons = () => {
//  state.iconsVisible = !state.iconsVisible;
//};

//==

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

/*
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
      state.item.x += e.dx;
      state.item.y += e.dy;
    },
    onend: () => {
      // 放開滑鼠後確保彈出圖示不受影響
      if (!state.iconsVisible) {
        // 如果圖示本來就是隱藏的，不做任何改變
        state.iconsVisible = false;
      }
    }
  });
};
*/
// 切換圖示顯示（僅按下按鈕時觸發）
const toggleIcons = () => {
  state.iconsVisible = !state.iconsVisible;
};

//==
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
