<template>
  <div class="color-picker-container">
	<!--
      <Chrome
				v-model="localColorValue"
				@update:colorValue="updateColorValue"
				class="custom-chrome-picker"
			/>
	-->
	<!--
			<Chrome
				v-model:color="localColorValue"
				@update:color="updateColorValue"
				class="custom-chrome-picker"
			/>
	-->
			<Chrome
				:color="localColorValue"
				@update:color="updateColorValue"
				class="custom-chrome-picker"
			/>

  </div>
</template>

<script setup>
import { ref, watch, defineComponent, onMounted, onBeforeMount } from "vue";
import { Chrome } from "@ckpack/vue-color";

//=== component name ===
defineComponent({
  name: "ColorPicker",
});

//=== props ==
const props = defineProps({
	colorValue: String,
});

//=== emits ==
const emit = defineEmits(['update:colorValue']);

//=== data ===
//const localColorValue = ref(props.colorValue);
const localColorValue = ref({
  hex: props.colorValue || '#FFFFFF', // 預設值，避免未傳入時出錯
  hsl: { h: 0, s: 0, l: 1 }, // 初始 HSL 值
  rgb: { r: 255, g: 255, b: 255 } // 初始 RGB 值
});

//=== watch ===
//watch(() => props.colorValue, (newValue) => {
//    localColorValue.value = newValue;
//  }
//);
const parseColor = (hex) => {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const hsl = { h: 0, s: 0, l: 0 }; // 假設 HSL 計算邏輯簡化
  return { hex, rgb: { r, g, b }, hsl };
};

watch(() => props.colorValue, (newValue) => {
    if (newValue) {
      localColorValue.value = parseColor(newValue);
    }
  },
  { immediate: true }
);

//=== created ===
onBeforeMount(() => {
  console.log("ColorPicker, created()...");

});

//=== mounted ===
onMounted(() => {
  console.log("ColorPicker, mounted()...");

});

//=== methods ===
/*
const updateColorValue = (newColor) => {
  localColorValue.value = newColor; // 更新本地顏色
  emit('update:colorValue', localColorValue.value.hex); // 通知父層更新
  console.log('Updated colorValue:', localColorValue.value.hex);
};
*/
//const updateColorValue = (newColor) => {
//  console.log("updateColorValue()...");
//
//  localColorValue.value = newColor; // 更新本地顏色
//  emit('update:colorValue', newColor); // 通知父層更新
//  console.log('Updated colorValue:', newColor);
//};
/*
const updateColorValue = (newColor) => {
  console.log("updateColorValue()...");

  try {
    localColorValue.value = newColor; // 更新本地顏色
    emit('update:colorValue', newColor.hex); // 通知父層更新
    console.log('Updated colorValue:', newColor.hex);
  } catch (error) {
    console.error('Error updating color value:', error);
  }
};
*/
const updateColorValue = (newColor) => {
  localColorValue.value = newColor; // 更新本地顏色
  emit('update:colorValue', newColor.hex); // 通知父層更新 HEX 值
};

</script>

<style lang="scss" scoped>
.color-picker-container {
  //padding: 10px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 5px;
  width: 200px;
}
/*
.custom-chrome-picker .chrome-picker {
  position: relative;
}

.custom-chrome-picker .chrome-picker div[class*="vc-saturation-pointer"] {
  transform: translate(-50px, 50px); 	// 向左移50px，向下移50px
}
*/
//div.vc-saturation-pointer {
//	top: 10%;
//	left: 80%;
//}

//.vc-chrome-saturation-wrap .vc-saturation-pointer {
  //transform: translate(-50px, 50px); /* 向左移50px，向下移50px */
//	top: 10%;
//	left: 80%;

//}
</style>
