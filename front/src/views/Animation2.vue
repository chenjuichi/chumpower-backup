  <template>
    <div class="animation-page">
      <div class="box1 green">
        <div class="circle-container">
          <span class="char" style="transform: rotate(0deg) translate(36px) rotate(0deg)">完</span>
          <span class="char" style="transform: rotate(36deg) translate(36px) rotate(-36deg)">全</span>
          <span class="char" style="transform: rotate(72deg) translate(36px) rotate(-72deg)">台</span>
          <span class="char" style="transform: rotate(108deg) translate(36px) rotate(-108deg)">灣</span>
          <span class="char" style="transform: rotate(144deg) translate(36px) rotate(-144deg)">製</span>
          <span class="char" style="transform: rotate(180deg) translate(36px) rotate(-180deg)">造</span>
        </div>
      </div>
      <div class="box1 purple">
        <div class="circle-container">
          <span class="char" style="transform: rotate(0deg) translate(36px) rotate(0deg)">台</span>
          <span class="char" style="transform: rotate(60deg) translate(36px) rotate(-60deg)">灣</span>
          <span class="char" style="transform: rotate(120deg) translate(36px) rotate(-120deg)">精</span>
          <span class="char" style="transform: rotate(180deg) translate(36px) rotate(-180deg)">品</span>
        </div>
      </div>
      <div class="box1 orange">
        <div class="circle-container">
          <span class="char" style="transform: rotate(0deg) translate(36px) rotate(0deg)">行</span>
          <span class="char" style="transform: rotate(45deg) translate(36px) rotate(-45deg)">銷</span>
          <span class="char" style="transform: rotate(90deg) translate(36px) rotate(-90deg)">五</span>
          <span class="char" style="transform: rotate(135deg) translate(36px) rotate(-135deg)">大</span>
          <span class="char" style="transform: rotate(180deg) translate(36px) rotate(-180deg)">洲</span>
        </div>
      </div>
      <div class="box1 red">
        <div class="circle-container">
          <span class="char" style="transform: rotate(0deg) translate(36px) rotate(0deg)">智</span>
          <span class="char" style="transform: rotate(60deg) translate(36px) rotate(-60deg)">慧</span>
          <span class="char" style="transform: rotate(120deg) translate(36px) rotate(-120deg)">工</span>
          <span class="char" style="transform: rotate(180deg) translate(36px) rotate(-180deg)">廠</span>
        </div>
      </div>
      <div class="box1 yellow">
        <div class="circle-container">
          <span class="char" style="transform: rotate(0deg) translate(36px) rotate(0deg)">世</span>
          <span class="char" style="transform: rotate(60deg) translate(36px) rotate(-60deg)">界</span>
          <span class="char" style="transform: rotate(120deg) translate(36px) rotate(-120deg)">專</span>
          <span class="char" style="transform: rotate(180deg) translate(36px) rotate(-180deg)">利</span>
        </div>
      </div>
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
    gsap.to(".box1", {
      duration: 1,
      rotation: 360,
      opacity: 1,
      delay: 0.5,
      stagger: 0.2,
      ease: "sine.out",
      force3D: true
    });

    // 綁定 click 事件，並將元素儲存到 boxes 中
    boxes = document.querySelectorAll(".box1");
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
    gsap.to(".box1", {
      duration: 0.5,
      opacity: 0,
      y: -100,
      stagger: 0.1,
      ease: "back.in",
      onComplete: () => {
        console.log("Animation bye bye...");
        //router.replace({ name: 'LoginRegister' });
        const resolvedRoute = router.resolve({ name: 'LoginRegister' });
        const path = resolvedRoute.href;    // 取得解析後的 path
        router.replace({ path });           // 使用 path 來進行導航
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
  /*
  .animation-page {
    display: flex;
    align-items: center;
    justify-content: space-around;
    min-height: 100vh;
    font-family: "Signika Negative", sans-serif;
  }
  */
  .animation-page {
    display: flex;
    align-items: center;
    justify-content: space-around;
    min-height: 100vh;
    font-family: "Signika Negative", sans-serif;
    //background-image: url('../assets/C2018102900001_e-rm.png'); // 設置背景圖
    background-size: contain;       // 確保背景圖填滿視窗，並保持比例
    background-position: center;    // 背景圖居中
    background-repeat: no-repeat;   // 確保背景圖不重複
    background-attachment: fixed;   // 背景圖固定，不會隨滾動移動
    width: 100vw;                   // 設置寬度為視窗寬度
      position: relative;
  }

  h3 {
    position: fixed;
    top: 0;
    width: 100%;
    text-align: center;
  }
  /*
  .box {
    cursor: pointer;
    width: 100px;
    height: 100px;
    opacity: 0;
    background-size: cover;         // 確保背景圖適應 div 的大小
    background-position: center;    // 確保圖像居中
  }
  */

  .box1 {
    cursor: pointer;
    width: 100px;
    height: 100px;
    position: relative;    // 讓內容在 box 中定位
    display: flex;
    justify-content: center;
    align-items: center;
    background-size: cover;
    background-position: center;
      top: 210px;
  }

  .circle-container {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .char {
    position: absolute;
    transform-origin: center;
    font-size: 14px;
    font-weight: 500;
  }

  .green {
    //background-color: #28a745;
    background-image: url('../assets/com_adv_icon1m.png');  // 設置圖片路徑
    background-size: 100px 100px;                           // 調整圖片大小為 100x100 像素
  }

  .purple {
    //background-color: #6f42c1;
    background-image: url('../assets/com_adv_icon3m.png');  // 設置圖片路徑
    background-size: 100px 100px;                           // 調整圖片大小為 100x100 像素
  }

  .orange {
    //background-color: #fd7e14;
    background-image: url('../assets/com_adv_icon4m.png');  // 設置圖片路徑
    background-size: 100px 100px;                           // 調整圖片大小為 100x100 像素
  }

  .red {
    background-image: url('../assets/com_adv_icon5m.png');  // 設置圖片路徑
    background-size: 100px 100px;                           // 調整圖片大小為 100x100 像素
  }

  .yellow {
    background-image: url('../assets/com_adv_icon6m.png');  // 設置圖片路徑
    background-size: 100px 100px;                           // 調整圖片大小為 100x100 像素
  }
</style>
