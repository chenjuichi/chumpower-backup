<template>
    <div class="animation-page">
      <div class="box green">一站式服務</div>
      <div class="box purple"></div>
      <div class="box orange"></div>
      <div class="box purple"></div>
      <div class="box green"></div>
      <h3>歡迎光臨...</h3>
    </div>
  </template>

  <script setup>
  import { ref, defineComponent, onMounted, onUnmounted } from 'vue';
  import { gsap } from 'gsap';
  import { useRouter } from 'vue-router';

  //=== data ===
  const imageSrc = ref(require('../assets/com_adv_icon1_tw_pic-rmv.png')); //企業視覺圖像
  let boxes = []; // 用來儲存所有綁定的元素

  const router = useRouter();

  //=== component name ==
  defineComponent({
    name: 'Animation'
  });

  //=== mounted ===
  onMounted(() => {
    console.log("Animation, mounted()...");

    // 動畫效果
    gsap.to(".box", {
      duration: 1,
      rotation: 360,
      opacity: 1,
      delay: 0.5,
      stagger: 0.2,
      ease: "sine.out",
      force3D: true
    });

    // 綁定 click 事件，並將元素儲存到 boxes 中
    boxes = document.querySelectorAll(".box");
    boxes.forEach((box) => {
      box.addEventListener("click", handleClick);
    });
    /*
    // 點擊 box 時的動畫效果
    document.querySelectorAll(".box").forEach((box) => {
      box.addEventListener("click", () => {
        console.log("Box clicked!"); // 確認點擊事件被觸發
        gsap.to(".box", {
          duration: 0.5,
          opacity: 0,
          y: -100,
          stagger: 0.1,
          ease: "back.in",
          onComplete: () => {
            // 動畫完成後跳轉到 App.vue
            console.log("Animation bye bye...")
            router.replace({ name: 'LoginRegister' });
          }
        });
      });
    });
    */
  });

  //=== method ===
  const handleClick = () => {     // 點擊事件處理函數
    console.log("Box clicked!"); // 確認點擊事件被觸發
    gsap.to(".box", {
      duration: 0.5,
      opacity: 0,
      y: -100,
      stagger: 0.1,
      ease: "back.in",
      onComplete: () => {
        console.log("Animation bye bye...");
        router.replace({ name: 'LoginRegister' });
      }
    });
  };

  // 清理綁定的事件
  onUnmounted(() => {
    console.log("Animation unmounted, cleaning up events...");
    boxes.forEach((box) => {
      box.removeEventListener("click", handleClick); // 移除 click 事件
    });
  });

  </script>

  <style lang="scss" scoped>
  @import url("https://fonts.googleapis.com/css2?family=Signika+Negative:wght@400;600&display=swap");

  .animation-page {
    display: flex;
    align-items: center;
    justify-content: space-around;
    min-height: 100vh;
    font-family: "Signika Negative", sans-serif;
  }

  h3 {
    position: fixed;
    top: 0;
    width: 100%;
    text-align: center;
  }

  .box {
    cursor: pointer;
    width: 100px;
    height: 100px;
    opacity: 0;
    background-size: cover;         // 確保背景圖適應 div 的大小
    background-position: center;    // 確保圖像居中
  }

  .green {
    background-color: #28a745;
  }

  .purple {
    background-color: #6f42c1;
  }

  .orange {
    background-color: #fd7e14;
  }
  </style>
