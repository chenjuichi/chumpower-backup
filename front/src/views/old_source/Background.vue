<template>
  <div class="overflow-hidden" :style="backgroundStyle"></div>
</template>

<script setup>
import {ref, defineComponent, computed} from 'vue';
import { colors } from 'quasar';

//=== component name ==
defineComponent({
  name: 'Background'
});

const { lighten, textToRgb, rgbToHsv, hsvToRgb, rgbToHex} = colors;

//=== props ==
//const props = defineProps({
const props = defineProps({
  backgroundColor: {
    type: String,
    default: '#ff9258'
  },
  polygonColors: {
    type: Array,
    default: () => ['#ff5d05', '#cbe64e', '#40fff8', '#b14dff']
  },
  initialQuantity: {
    type: Number,
    default: 10
  },
  maxQuantity: {
    type: Number,
    default: 50
  },
  generationInterval: {
    type: Number,
    default: 500  // 500 毫秒
  }
});

//=== computed ===
const backgroundStyle = computed(() => {
  const lightenColor = lighten(props.backgroundColor, 10);
  const hsvColor = rgbToHsv(textToRgb(lightenColor));
  hsvColor.h +=10;
  const result = rgbToHex(hsvToRgb(hsvColor));

  return {
    background: linear-gradient('-10deg', '#77E4C8', '#478CCF')
  };
});
</script>

<style scoped>
.overflow-hidden {
  width: 100%;
  height: 100vh;
}
</style>