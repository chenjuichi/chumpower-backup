  <template>
    <div class="container" @click="imageClicked">
      <div class="content">
        <!--<h1>Testing this out</h1>-->
      </div>

      <div class="img"></div>
    </div>
  </template>

  <script setup>
  import { ref, defineComponent, onMounted, onUnmounted } from 'vue';
  import { gsap } from 'gsap';
  import { useRouter } from 'vue-router';

  const isClickable = ref(false);
  const router = useRouter();

  //=== component name ==
  defineComponent({
    name: 'Animation'
  });

  //=== mounted ===
  onMounted(() => {
    console.log("Animation, mounted()...");

    // 動畫效果
    const tl = gsap.timeline({
      paused:true,
      onComplete: () => {
        console.log("Clip path animation done, image is now clickable...");
        isClickable.value = true; // 動畫完成後，圖片可以點擊
      },
    });

    const container = document.querySelector('.container');

    // 使用正確的變數名稱 tl
    tl.to(container, {
      clipPath: 'polygon(7% 7%, 93% 7%, 93% 93%, 7% 93%)',
      duration: 1,
    });
    //tl.to(container, {clipPath: 'polygon(93% 7%, 93% 7%, 93% 93%, 93% 93%)'});

    container.addEventListener("mouseover", () => {
      tl.play();  // 使用 tl 而非 t1
    });
  });

  // 按鈕點擊事件處理函數
  const handleClick = () => {
    console.log("Image clicked!");

    gsap.to(".img", {
      duration: 0.5,
      opacity: 0,
      y: -100,
      stagger: 0.1,
      ease: "back.in",
      onComplete: () => {
        console.log("Animation bye bye...");

        // 進行路由導航
        const resolvedRoute = router.resolve({ name: "LoginRegister" });
        const path = resolvedRoute.href;
        router.replace({ path });
      },
    });
  };

  // 圖片點擊邏輯
  const imageClicked = () => {
    console.log("Image clicked function called,", isClickable.value);
    //console.log("imageClicked(), ", isClickable.value)

    if (isClickable.value) {
      handleClick(); // 只有動畫完成後才允許點擊
    } else {
      console.log("Image not clickable yet...");
    }
  };
  </script>

  <style lang="scss" scoped>
  @import url("https://fonts.googleapis.com/css2?family=Signika+Negative:wght@400;600&display=swap");

  // 全局樣式調整
  //body:hover .container {
  //  clip-path: polygon(7% 7%, 93% 7%, 93% 93%, 7% 93%);
  //}

  .container {
    //width: calc(100vw - 0px);
    width: 100vw;           // 設定寬度填滿整個視窗或父容器
    max-width: 1249px;     // 如果要限制容器的最大寬度
    height: 100vh;
    //margin: 0 auto;        // 讓 container 在視窗中水平置中
    margin: 0;
    padding: 0;            // 移除任何內間距

    position: absolute;
    clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
    transition: clip-path 1s;

    .img {
      background: url('../assets/boss-chumpower.jpg');
      background-size: cover;
      background-position: center;  // 確保背景圖居中
      width: 100%;          // 寬度設定為 container 的 100%
      height: 100vh;
      cursor: pointer;
      opacity: 1; // 確保圖片可見
    }

    .content {
      position: absolute;
      z-index: 1;
      display: grid;
      place-items: center;
      height: 100vh;
      width: 100%;          // 設定 content 寬度與 container 一致
      //max-width: 1140px;    // 保持與 container 一樣的最大寬度
      //margin: 0 auto;       // content 水平置中
      margin: 0;
      padding: 0;           // 移除任何內間距

      h1 {
        font-size: 4rem;
        position: absolute;
      }
    }
  }
  </style>
