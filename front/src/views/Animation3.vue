<template>
  <transition name="slide-down" @after-leave="navigateToRoute">
    <div class="header" v-if="showHeader">
      <nav class="nav">
        <div class="nav-logo">
          <!--<a href="#" class="nav-logo-link">INFINITY <span class="logo-color">SALON</span></a>-->
          <a href="#" class="nav-logo-link">
            <img :src="home_url" alt="INFINITY SALON" class="logo-image" />
          </a>
        </div>
        <div class="nav-menu">
          <ul class="nav-menu-container">
            <li><a href="#" class="nav-menu-link">在地製造</a></li>
            <li><a href="#" class="nav-menu-link">台灣精品</a></li>
            <li><a href="#" class="nav-menu-link">行銷全球</a></li>
            <li><a href="#" class="nav-menu-link">智慧工廠</a></li>
            <li><a href="#" class="nav-menu-link">世界專利</a></li>
            <!--<li><a href="#" class="nav-menu-link header-btn">Address</a></li>-->
          </ul>
        </div>
      </nav>

      <div class="header-content-container">
        <div class="left-container">
          <div class="header-text-container">
            <h1 class="header-main-heading">CHUMPOWER</h1>
            <h1 class="header-main-heading second-heading">銓寶工業</h1>
            <h2 class="header-sub-heading">專業精密夾頭、刀桿、主軸配件製造公司</h2>
            <p class="header-description">每年外銷25萬組以上精密鑽夾頭</p>
            <p class="header-description">客戶遍及全球五大洲</p>

            <div class="header-btn-container">
                <button class="header-btn btn-effect" @click="startTransition">
                  Booking
                </button>
              <!--
              <a href="#" class="header-btn btn-effect">Booking</a>
              <a href="#" class="header-btn">Gallery</a>
              -->
            </div>
          </div>
        </div>

        <div class="right-container">
          <div class="hero-image-container">
            <div class="overlay"></div>
            <img :src="imageSrc" class="hero-image">
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
  import { ref, onMounted } from 'vue'
  import { useRouter } from 'vue-router';
  import { gsap } from 'gsap'
  import logo from '../assets/logo.svg';

  const home_url = logo;     // 定義 home_url 變數，指向 SVG 圖像
  const imageSrc = ref(require('../assets/boss-chumpower.jpg')); //企業視覺圖像
  const showHeader = ref(true);

  const router = useRouter();

  //=== method ===
  const splitTextIntoLetters = (text) => {    // 字母分解邏輯，模擬 lettering.js 的效果
    return text.split("").map((letter, index) => `<span class="letter">${letter}</span>`).join("");
  }

  const startTransition = () => {   // 開始移除 header 並觸發轉場動畫
    showHeader.value = false;
  }

  const navigateToRoute = () => {
    const resolvedRoute = router.resolve({ name: "LoginRegister" });
    const path = resolvedRoute.href;
    router.replace({ path }); // 當 header 移除動畫結束後，進行路由導航
  }

  onMounted(() => {
    // GSAP 動畫替代 textillate 和 lettering
    const mainHeading1 = document.querySelector('.header-main-heading:first-child');
    const mainHeading2 = document.querySelector('.header-main-heading.second-heading');
    const subHeading = document.querySelector('.header-sub-heading');
    const description = document.querySelectorAll('.header-description');
    const heroImageContainer = document.querySelector('.hero-image-container');
    const heroImage = document.querySelector('.hero-image');
    const navItems = document.querySelectorAll('.nav-menu-link');

    // 使用 gsap 模擬效果
    gsap.from(mainHeading1, { opacity: 0, y: 50, duration: 2, ease: "expo.out" });
    gsap.from(mainHeading2, { opacity: 0, y: 50, duration: 2, ease: "expo.out", delay: 0.5 });
    gsap.from(subHeading, { opacity: 0, y: 50, duration: 2, ease: "expo.out", delay: 1 });
    gsap.from(description, { opacity: 0, y: 50, duration: 2, ease: "expo.out", delay: 1.5, stagger: 0.2 });

    // 按鈕動畫
    gsap.from(".header-btn", { opacity: 0, y: 50, duration: 2, ease: "expo.out", delay: 2.5 });

    // 導航列動畫
    gsap.from(navItems, { opacity: 0, y: 50, duration: 2, ease: "expo.out", stagger: 0.2 });

    // 圖像動畫
    gsap.to(heroImageContainer, { opacity: 1, duration: 2, ease: "expo.out", delay: 1 });
    gsap.from(heroImage, { x: 300, opacity: 0, duration: 2, ease: "expo.out", delay: 1 });
    gsap.to(heroImage, { x: 0, opacity: 1, duration: 2, ease: "expo.out", delay: 2 });
  });
</script>

<style lang="scss" scoped>
  @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;600;700;800&display=swap');
  @import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

  * {
    padding: 0;
    margin: 0;
    box-sizing: border-box;
    text-decoration: none;
    list-style: none;
  }

  body {
    font-family: 'Poppins', sans-serif;
    background: rgb(241, 224, 216);
    color: #333;
    overflow: hidden;
  }

  .logo-image {
    width: 150px;
    height: auto;
  }

  .header {
    display: flex;
    flex-direction: column;
    padding: 0 100px;
  }

  .nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.2rem 0;
    z-index: 2;
  }

  .nav-logo-link {
    font-size: 1.9rem;
    font-weight: 700;
    color: #000;
  }

  .logo-color {
    color: #99573D;
  }

  .nav-menu-container {
    display: flex;
    flex-direction: row;
    transform: translateX(-130px);
  }

  .nav-menu-link {
    margin-right: 2rem;
    font-size: 1.1rem;
    font-weight: 700;
    color: #000;
    font-family: '微軟正黑體', 'cwTeXYen', sans-serif;
  }

  .header-content-container {
    display: flex;
    justify-content: space-between;
    width: 100%;
  }

  .left-container {
    width: 40%;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 100px);
    justify-content: center;
  }

  .right-container {
    width: 60%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .header-main-heading {
    font-size: 2.5rem;
    font-weight: 700;
    //color: #000;
    color:#31349f
  }

  .second-heading {
    color: #46C4B2;
  }

  .header-sub-heading {
    font-size: 1.4rem;
    font-weight: 700;
    color: #555;
    margin-top: 20px;
  }

  .header-description {
    font-size: 1rem;
    font-weight: 700;
    color: #888;
    margin-top: 10px;
  }

  .header-btn-container {
    display: flex;
    margin-top: 20px;

    justify-content: center;   // 水平置中
    align-items: center;       // 垂直置中
  }

  .header-btn {
    padding: 0.6rem 2rem;
    font-weight: 600;
    color: black;
    background: #46c4b2;
    border: 2px solid #46c4b2;
    border-radius: 5px;
    margin-right: 8px;
  }

  .btn-effect {
    color: #46c4b2;
    background: transparent;
  }

  .header-btn:hover {
    background: #46c4b2;
    color: #fff;
  }

  .hero-image-container {
    position: absolute;
    width: 100%;
    height: 80vh;
    background: #99573D;
    opacity: 0;

    display: flex;                //垂直置中對齊
    justify-content: center;      //
    align-items: center;          //
  }

  .hero-image {
    height: 70vh;
    width: auto;
    border-radius: 6px;
    opacity: 0;
    transition: transform 0.3s ease;
  }

  .overlay {
    position: absolute;
    right: 0;
    width: 0;
    height: 80vh;
    background: white;
    animation: overlayAnimation 2s cubic-bezier(0.2, 1, 0.25, 1) forwards;
    animation-delay: 1s;
  }

  @keyframes overlayAnimation {
    0% {
      right: 0;
      width: 0;
    }
    100% {
      right: 0;
      width: 60%;
    }
  }

  .slide-down-leave-active {
    transition: transform 0.5s ease;
  }

  .slide-down-leave-to {
    transform: translateY(100%); /* 向下移出視窗 */
  }
  </style>
