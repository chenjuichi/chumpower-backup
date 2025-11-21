<template>
  <div class="color-picker-container">

      <Chrome
				:modelValue="localColorValue"
				@update:modelValue="updateColorValue"
				class="custom-chrome-picker"
			/>

  </div>
</template>

<script setup>
import { ref, watch, defineComponent } from "vue";
import { Chrome } from "@ckpack/vue-color";

//=== component name ===
defineComponent({
  name: "ColorPicker",
});

//=== props ==
//const props = defineProps({
//	colorValue: String,
//});
const props = defineProps({
  colorValue: {
    type: String,
    default: "#FFFFFF", // 提供默認值，避免 undefined
  },
});

//=== emits ==
const emit = defineEmits(['update:colorValue']);

//=== data ===
const localColorValue = ref(props.colorValue);


//=== watch ===
watch(() => props.colorValue, (newValue) => {
	if (newValue) {
      localColorValue.value = newValue; // 同步傳入值
    }
  },
  { immediate: true }
);

//=== methods ===
const updateColorValue = (newColor) => {
  localColorValue.value = newColor; // 更新本地顏色
  emit('update:colorValue', newColor); // 通知父層更新
  console.log('Updated colorValue:', newColor);
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
