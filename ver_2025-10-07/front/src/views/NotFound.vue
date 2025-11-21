<template>
  <div class="not-found" :style="backgroundStyle">
    <!--<h1>Not Found!</h1>-->
    <p class="not-found-message">沒有這個網頁!</p>
  </div>
</template>

<script setup>
import { ref, defineComponent, onMounted, onUnmounted } from 'vue'

//=== component name ==
defineComponent({
  name: 'NotFound'
});

const imageSrc = ref(require('../assets/404NotFoundPage.png'));

// 背景style
const backgroundStyle = ref({
  backgroundImage: `url(${imageSrc.value})`,
  backgroundSize: 'cover',
  backgroundPosition: 'center',
});
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexfangsong.css');

body{
   font-family: 'cwTeXFangSong', serif;
}

.not-found {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  text-align: center;
}

.not-found h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
  color: #fff;
}

.not-found p {
  font-size: 1.5rem;
  color: #fff;
}

.not-found-message {
  font-family: 'cwTeXFangSong', serif;
  font-size: 1.5rem;
  color: #fff;
  left: 450px;
  top: 260px;
  position: relative;
}
</style>
