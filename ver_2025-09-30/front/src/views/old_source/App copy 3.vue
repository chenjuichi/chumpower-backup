<template>
  <div id="app">
    <Nav v-if="!hideNavAndFooter" :show-footer="showFooter" @update:showFooter="updateShowFooter" />
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
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Nav from '../Nav.vue';
import Footer from '../Footer.vue';
//import LoginForm from './views/LoginForm.vue';
import Sender from '../../components/Sender.vue';
import eventBus from '../../mixins/enentBus.js';

const showFooter = ref(true);
const hideNavAndFooter = ref(false);    // 監聽路由變化來隱藏或顯示 Nav 和 Footer

const IDLE_TIMEOUT = 5 * 60 * 1000;     // 5 分鐘
let idleTimer = null;

const route = useRoute();
const router = useRouter();

// 更新 showFooter
const updateShowFooter = (value) => {
  showFooter.value = value;
};

const resetIdleTimer = () => {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(() => {
    eventBus.emit('idleTimeout');
  }, IDLE_TIMEOUT);
};

const handleUserActivity = () => {
  resetIdleTimer();
};

const handleIdleTimeout = () => {
  router.push({ name: 'LoginRegister' });
};

watch(route, (newRoute) => {
  hideNavAndFooter.value = newRoute.meta.hideNavAndFooter || false;
});

onMounted(() => {
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

  eventBus.on('idleTimeout', () => {
    // 在更改 URL 時, 保留現在的歷史狀態
    const currentState = history.state;
    router.push({ name: 'LoginRegister' }).catch(err => {
      if (err.name !== 'NavigationDuplicated') {
        throw err;
      }
    });
    history.replaceState(currentState, '', router.resolve({ name: 'LoginRegister' }).href);
  });

});

onUnmounted(() => {
  if (idleTimer) {
    clearTimeout(idleTimer);
  }
  // 清除事件監聽器
  window.removeEventListener('mousemove', handleUserActivity);
  window.removeEventListener('keydown', handleUserActivity);
  window.removeEventListener('scroll', handleUserActivity);
  //clearTimeout(idleTimer);
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
  overflow: hidden;
}

.content {
  flex: 1;
  margin-top: 60px;     // 確保內容不被固定導航欄遮擋，根據導航欄的高度調整這個值
  margin-bottom: 60px;  // 確保內容不被固定頁尾遮擋，根據頁尾的高度調整這個值
  padding: 20px;
  box-sizing: border-box;
  overflow: auto;
  position: relative;
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
