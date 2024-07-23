<template>
  <div class="main-background">
    <img id="sourceImage" :src="imageSrc" alt="Background Image" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const imageSrc = ref(require('../assets/main_background_img.png'))
/*
const updateContentOverflow = (overflowValue) => {
  const contentElement = document.querySelector('.content');
  if (contentElement) {
    contentElement.style.overflow = overflowValue;
  }
};
*/
const updateContentStyles = (overflowValue, paddingValue) => {
  const contentElement = document.querySelector('.content');
  if (contentElement) {
    contentElement.style.overflow = overflowValue;
    contentElement.style.padding = paddingValue;
  }
};

onMounted(() => {
  updateContentStyles('hidden', '0');
});

onUnmounted(() => {
  updateContentStyles('auto', '20px');
});

</script>

<style lang="scss" scoped>
  //html, body {
  //  height: 100%;
  //  margin: 0;
  //  overflow: hidden; /* 禁用scroll bar */
  //}

  .main-background {
    display: flex;
    justify-content: center;
    align-items: center;
    height: calc(100vh - 120px); /* 調整高度以考慮 Nav 和 Footer 的高度 */
    margin-top: 60px;
    margin-bottom: 60px;
  }

  .main-background img {
    width: 100%;
    height: 150%;
    object-fit: cover;
  }
  </style>
