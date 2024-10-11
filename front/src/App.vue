<template>
  <div id="app">
    <Nav
      v-if="!hideNavAndFooter"
      :show-footer="showFooter"
      :navLinks="navLinks"
      @update:showFooter="updateShowFooter"
    />

    <div :class="{'content': !hideNavAndFooter,  'no-footer': !showFooter }">
      <router-view v-slot="{ Component, route }">
        <transition :name="route.meta.transitionName">
          <!--<component :is="Component" class="page" />-->
          <component :is="Component" />
        </transition>
      </router-view>
      <Sender />
    </div>
    <Footer v-if="!hideNavAndFooter" v-show="showFooter" />

  </div>
</template>

<script setup>
import { ref, watch, onBeforeMount, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { flatItems } from './mixins/MenuConstants.js';

import Animation from './views/Animation.vue';

import Nav from './views/Nav.vue';
import Footer from './views/Footer.vue';
//import LoginRegister from './views/LoginForm2.vue';
import Sender from './components/Sender.vue';
import eventBus from './mixins/enentBus.js';

const showFooter = ref(true);
const hideNavAndFooter = ref(false);    // 監聽路由變化來隱藏或顯示 Nav 和 Footer
//const showLoginForm = ref(true);        // 控制 LoginForm 顯示

const IDLE_TIMEOUT = 5 * 60 * 1000;     // 5 分鐘
let idleTimer = null;

let countdownTimer = null;              // 倒數計時器
const countdown = ref(IDLE_TIMEOUT);    // 初始倒數值

const route = useRoute();

// 定義 基本navLinks
//const generateDefaultNavLinks = () => {
//  return Array.from({ length: 26 }, (_, index) => ({
//    text: `Item ${index + 1}`,
//    to: `/path${index + 1}`,
//    isEnabled: index % 2 === 0    // 假設啟用每第二個项(偶數項)
//  }));
//};
//const navLinks = ref(generateDefaultNavLinks());  // 動態生成預設直(初始值)
const navLinks = ref([]);  // 初始值為空array
/*
const navLinks = ref([
  {
    text: 'Home',
    to: '/home',
    isEnabled: true   // 根據具體邏輯決定是否啟用
  },
  {
    text: 'About',
    to: '/about',
    isEnabled: false  // 根據具體邏輯決定是否啟用
  },
]);
*/


// 更新 showFooter
const updateShowFooter = (value) => {
  showFooter.value = value;
};

// 更新 navLinks
const updateNavLinks = (links) => {
  console.log("navLinks,links:", links)
  //showLoginForm.value = false; // 登入成功後隱藏 LoginForm
  navLinks.value = links;
};

const handleSetLinks = (links) => {
  console.log("Received links:", links);
  updateNavLinks(links);
};

// 設定timer
const resetIdleTimer = () => {
  clearTimeout(idleTimer);

  clearInterval(countdownTimer); // 清除舊的倒數計時器
  countdown.value = IDLE_TIMEOUT; // 重置倒數值

  idleTimer = setTimeout(() => {
    eventBus.emit('idleTimeout');
  }, IDLE_TIMEOUT);

  // 每秒更新倒數計時
  countdownTimer = setInterval(() => {
    countdown.value -= 1000;          // 每秒減少1000毫秒
    if (countdown.value <= 0) {
      clearInterval(countdownTimer);  // 停止倒數計時
    }
    const minutes = Math.floor(countdown.value / 60000);
    const seconds = Math.floor((countdown.value % 60000) / 1000);
    eventBus.emit('updateCountdown', {
      minutes: String(minutes).padStart(2, '0'),
      seconds: String(seconds).padStart(2, '0')
    });
  }, 1000);
};

// 起始timer
const handleUserActivity = () => {
  resetIdleTimer();
};

//const handleIdleTimeout = () => {
//  router.push({ name: 'LoginRegister' });
//};

const handleIdleTimeout = () => {
  eventBus.emit('triggerLogout');   // 觸發 'triggerLogout' 事件

  //router.replace({ name: 'LoginRegister' });  //啟動router

  /*
  const currentState = history.state;
  router.push({ name: 'LoginRegister' }).then(() => {
    // 保留現有的歷史狀態
    history.replaceState(currentState, '', router.resolve({ name: 'LoginRegister' }).href);
  }).catch(err => {
    if (err.name !== 'NavigationDuplicated') {
      throw err;
    }
  });
  */
};

watch(route, (newRoute) => {
  hideNavAndFooter.value = newRoute.meta.hideNavAndFooter || false;
});

//=== created ===
onBeforeMount(() => {
  console.log("App.vue, created()...");

});

//=== mounted ===
onMounted(() => {
  console.log("App.vue, mounted()...");

  eventBus.on('setLinks', handleSetLinks);

  // 初始化 navLinks
  //navLinks.value = generateDefaultNavLinks();
  navLinks.value = flatItems.value;
  console.log("navLinks:", navLinks.value);

  // 初始化計時器
  resetIdleTimer();

  // 監聽用戶活動
  window.addEventListener('mousemove', resetIdleTimer);
  window.addEventListener('keydown', resetIdleTimer);
  window.addEventListener('scroll', resetIdleTimer);
  /*
  // 監聽 idle 事件
  eventBus.on('idle', () => {
    isIdle.value = true;
  });

  // 監聽 active 事件
  eventBus.on('active', () => {
    isIdle.value = false;
  });
  */

  /*
  eventBus.on('idleTimeout', () => {
    // 在更改 URL 時, 保留現在的歷史狀態
    const currentState = history.state;
    router.push({ name: 'LoginRegister' }).catch(err => {
      if (err.name !== 'NavigationDuplicated') {
        throw err;
      }
    });
    //history.replaceState(currentState, '', router.resolve({ name: 'LoginRegister' }).href);
    // 保留現有的歷史狀態
    const newUrl = router.resolve({ name: 'LoginRegister' }).href;
    history.replaceState({ ...history.state }, '', newUrl);
  });
  */
  eventBus.on('idleTimeout', handleIdleTimeout);
});

onUnmounted(() => {
  if (idleTimer) {
    clearTimeout(idleTimer);
  }

  if (countdownTimer) {
    clearInterval(countdownTimer);
  }

  // 清除事件監聽器
  window.removeEventListener('mousemove', handleUserActivity);
  window.removeEventListener('keydown', handleUserActivity);
  window.removeEventListener('scroll', handleUserActivity);
});
</script>

<style lang="scss" scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  //height: 100%;
  overflow: hidden;
}

.content {
  flex: 1;
  margin-top: 60px;     // 確保內容不被固定導航欄遮擋，根據導航欄的高度調整這個值
  margin-bottom: 60px;  // 確保內容不被固定頁尾遮擋，根據頁尾的高度調整這個值
  //padding: 20px;
  padding: 0;
  box-sizing: border-box;
  position: relative;
  overflow: auto;
  //overflow: hidden;
}

a {
  font-weight: bold;
  color: #2c3e50;
  text-decoration: none;
  margin-right: 1em;
}

a:hover,
a.router-link-active {
  border-bottom: 2px solid #3498db;
}

.no-footer {
  margin-bottom: 0; // 沒有頁腳時的底部邊距
}

.page {
  width: 100%;
  position: absolute;
  top: 0;
  left: 0;
}

.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 1s linear; /* 將過渡動畫的緩動函數改為 linear */
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(100%);
}

.slide-left-enter-to,
.slide-left-leave-from {
  transform: translateX(0%);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(-100%);
}

.slide-right-enter-to,
.slide-right-leave-from {
  transform: translateX(0%);
}

body {
  overflow: hidden; /* 禁用 body 的 scrollbar */
}

/* 如果你還需要內部容器具有滾動功能，可以單獨設置 */
.scrollable-container {
  overflow-y: auto; /* 允許垂直滾動 */
  overflow-x: auto; /* 允許水平滾動 */
}

body::-webkit-scrollbar {
  width: 0px !important;               /* width of the entire scrollbar */
}
</style>
