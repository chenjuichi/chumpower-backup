<template>

  <nav class="navbar navbar-expand-lg navbar-light bg-light fixed-top">
    <div class="container-fluid">
      <!--圖示-->
      <div class="navbar-brand"><img :src="home_url" alt="Logo" style="height: 4vw;"></div>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="collapse navbar-collapse" id="navbarNav" style="font-family: 'cwTeXYen', sans-serif;">
        <!-- 選單 -->
        <ul class="navbar-nav my-left-nav">
          <!--item1-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(0)"
            @mouseleave="onLeave(0)"
          >
            <button class="dropbtnk" :disabled="navLinks[0].isEnabled">
              <div :class="{'button-content': navLinks[0].isSegment }">
                <!--item1, menu 1-->
                <span :class="{'button-title': navLinks[0].isSegment }">{{ navLinks[0].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[0] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[0].isSegment }]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 2-->
              <router-link
                :to="navLinks[1].isEnabled ? navLinks[1].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[1].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[1].text }}
              </router-link>
              <!--menu 3-->
              <router-link
                :to="navLinks[2].isEnabled ? navLinks[2].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[2].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[2].text }}
              </router-link>
              <!--menu 4-->
              <router-link
                :to="navLinks[3].isEnabled ? navLinks[3].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[3].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[3].text }}
              </router-link>
              <!--menu 5-->
              <router-link
                :to="navLinks[4].isEnabled ? navLinks[4].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[4].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[4].text }}
              </router-link>
            </div>
          </li>
          <!--item2-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(1)"
            @mouseleave="onLeave(1)"
          >
              <button class="dropbtnk" :disabled="navLinks[5].isEnabled">
                <div :class="{'button-content': navLinks[5].isSegment }">
                  <!--item2, menu 6-->
                  <span :class="{'button-title': navLinks[5].isSegment }">{{ navLinks[5].text }}</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[1] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[5].isSegment }]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <!--menu 7-->
              <router-link
                :to="navLinks[6].isEnabled ? navLinks[6].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[6].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[6].text }}
              </router-link>
              <!--menu 8-->
              <router-link
                :to="navLinks[7].isEnabled ? navLinks[7].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[7].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[7].text }}
              </router-link>
            </div>
          </li>
          <!--item3-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(2)"
            @mouseleave="onLeave(2)"
          >
              <button class="dropbtnk" :disabled="navLinks[8].isEnabled">
                <div :class="{'button-content': navLinks[8].isSegment }">
                  <!--item3, menu 9-->
                  <span :class="{'button-title': navLinks[8].isSegment }">{{ navLinks[8].text }}</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[2] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[8].isSegment}]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <!--menu 10-->
              <router-link
                :to="navLinks[9].isEnabled ? navLinks[9].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[9].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[9].text }}
              </router-link>
              <!--menu 11-->
              <router-link
                :to="navLinks[10].isEnabled ? navLinks[10].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', { 'disabled-linkk': !navLinks[10].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[10].text }}
              </router-link>
              <!--menu 12-->
              <router-link
                :to="navLinks[11].isEnabled ? navLinks[11].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[11].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[11].text }}
              </router-link>
            </div>
          </li>
          <!--item4-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(3)"
            @mouseleave="onLeave(3)"
          >
            <button class="dropbtnk" :disabled="navLinks[12].isEnabled">
              <div :class="{'button-content': navLinks[12].isSegment }">
                <!--item4, menu 13-->
                <span :class="{'button-title': navLinks[12].isSegment }">{{ navLinks[12].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[3] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[12].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 14-->
              <router-link
                :to="navLinks[13].isEnabled ? navLinks[13].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[13].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[13].text }}
              </router-link>
              <!--menu 15-->
              <router-link
                :to="navLinks[14].isEnabled ? navLinks[14].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[14].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks[14].text }}
              </router-link>
              <!--menu 16-->
              <router-link
                :to="navLinks[15].isEnabled ? navLinks[15].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[15].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[15].text }}
              </router-link>
            </div>
          </li>
          <!--item5-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(4)"
            @mouseleave="onLeave(4)"
          >
            <button class="dropbtnk" :disabled="navLinks[16].isEnabled">
              <div :class="{'button-content': navLinks[16].isSegment }">
                <!--item5, menu 17-->
                <span :class="{'button-title': navLinks[16].isSegment }">{{ navLinks[16].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[4] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[16].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 18-->
              <router-link
                :to="navLinks[17].isEnabled ? navLinks[17].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[17].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[17].text }}
              </router-link>
              <!--menu 19-->
              <router-link
                :to="navLinks[18].isEnabled ? navLinks[18].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[18].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[18].text }}
              </router-link>
              <!--menu 20-->
              <router-link
                :to="navLinks[19].isEnabled ? navLinks[19].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[19].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[19].text }}
              </router-link>
            </div>
          </li>
          <!--item6-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(5)"
            @mouseleave="onLeave(5)"
          >
            <button class="dropbtnk" :disabled="navLinks[20].isEnabled">
              <div :class="{'button-content': navLinks[20].isSegment }">
                <!--item6, menu 21-->
                <span :class="{'button-title': navLinks[20].isSegment }">{{ navLinks[20].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[5] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : navLinks[20].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 22-->
              <router-link
                :to="navLinks[21].isEnabled ? navLinks[21].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[21].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[21].text }}
              </router-link>
              <!--menu 23-->
              <router-link
                :to="navLinks[22].isEnabled ? navLinks[22].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[22].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[22].text }}
              </router-link>
              <!--menu 24-->
              <router-link
                :to="navLinks[23].isEnabled ? navLinks[23].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[23].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[23].text }}
              </router-link>
              <!--menu 25-->
              <router-link
                :to="navLinks[24].isEnabled ? navLinks[24].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[24].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[24].text }}
              </router-link>
              <!--menu 26-->
              <router-link
                :to="navLinks[25].isEnabled ? navLinks[25].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks[25].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks[25].text }}
              </router-link>
            </div>
          </li>
          <!--item7-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(6)"
            @mouseleave="onLeave(6)"
            style="left: 200px;"
          >
            <button class="dropbtnk">
              <em>{{ currentUser ? currentUser.name : '使用者' }}</em>
              <span class="icon-container">
                <i :class="['fas', hoveredItems[6] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment }]" />
              </span>
            </button>
            <div class="dropdown-contentk">
              <div class="dropdown-item my-dropdown-item" @click="logout">登出</div>
              <div class="dropdown-item my-dropdown-item" @click="passwordDialog">修改密碼</div>
              <div class="dropdown-item my-dropdown-item" @click="functionB">功能B</div>
              <div class="dropdown-item my-dropdown-item" @click="functionC">功能C</div>
            </div>
          </li>
          <!--item8-->
          <li class="nav-item" style="position: relative; left: 190px; font-size: 13px;">
            <span>剩餘時間: {{ countdown.minutes }}:{{ countdown.seconds }}</span>
          </li>
        </ul>

        <!--checkbox-->
        <v-checkbox v-model="localShowFooter" label="Show Footer" class="ml-auto" style="position: relative; right: 200px;" />
      </div>
    </div>
  </nav>

  <ChangePassword :dialog="openDialog" @update:dialog="updateDialog"></ChangePassword>
</template>

<script setup>
import { ref, reactive, watch, defineComponent, onBeforeMount, onMounted, onBeforeUnmount, onUnmounted } from 'vue';
//import { useRoute, useRouter } from 'vue-router'; // Import useRouter
import { useRouter } from 'vue-router'; // Import useRouter
//import logo from '../assets/BBC-Line-Logo_Blue.png';
import logo from '../assets/logo.svg';
import VCheckbox from './VCheckbox.vue';
import ChangePassword from './changePassword.vue';
import eventBus from '../mixins/enentBus.js';

import { myMixin } from '../mixins/common.js';

import { apiOperation, }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const updateSetting = apiOperation('post', '/updateSetting');

//=== component name ==
defineComponent({
  name: 'Nav'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ==
const props = defineProps({
  showFooter: Boolean,

  //navLinks: {
  //  type: Object,
  //  required: true,
  //  default: () => ({})
  //},

  navLinks: {
    type: Array,
    required: true,
    default: () => []
  },
});

//=== emits ==
const emit = defineEmits(['update:showFooter']);

//=== data ===
const isSegment = ref(false);
const openDialog = ref(false);
const home_url = logo;
const localShowFooter = ref(props.showFooter);
//const dropdownOpen = ref({ b: false, user: false, data_maintain: false, product_info: false });

const hoveredItems = reactive({});
//const dropdownContent = reactive({
//  product_info: null,
//})
const currentUser = ref(null);
const popStateHandler = ref(null);

const countdown = ref({
  minutes: '00',
  seconds: '00'
});

const router = useRouter(); // Initialize router
//const route = useRoute(); // Initialize router

//=== mounted ===
onMounted(() => {
  console.log("nav, mounted():",props.navLinks);

  // 禁用 BackButton 功能
  disableBackButton();
  document.addEventListener('keydown', allowBackspaceInInputs);
  /*
  window.history.pushState(null, '', window.location.href);
  popStateHandler.value = (event) => {
    event.preventDefault();
    window.history.pushState(null, '', window.location.href);
  };
  window.addEventListener('popstate', popStateHandler.value);
  */
  //
  hoveredItems[0]=false;
  hoveredItems[1]=false;
  hoveredItems[2]=false;
  hoveredItems[3]=false;
  hoveredItems[4]=false;
  hoveredItems[5]=false;
  hoveredItems[6]=false;
  //
  eventBus.on('triggerLogout', logout);
  //
  eventBus.on('updateCountdown', updateCountdown);
});

onBeforeUnmount(() => {
  // 恢復 BackButton 功能
  if (popStateHandler.value) {
    enableBackButton();
    document.removeEventListener('keydown', allowBackspaceInInputs);

    //window.removeEventListener('popstate', popStateHandler.value);
    popStateHandler.value = null;
  }
  //
  eventBus.off('triggerLogout', logout);
  //
  eventBus.off('updateCountdown', updateCountdown);
});

//=== unmounted ===
onUnmounted(() => {
  //enableBackButton();
});

//=== created ===
onBeforeMount(() => {
  let user = localStorage.getItem("loginedUser");
  console.log("1. nav, created(), user:", user);
  currentUser.value = user ? JSON.parse(user) : null;
  //currentUser.value = JSON.parse(localStorage.getItem("loginedUser"));
  console.log("2. nav, created(), current user:", currentUser.value);

  initAxios();
});

//=== computed ===


//=== watch ===
watch(localShowFooter, (newValue) => {
  console.log("Nav.vue, watch(),", newValue)

  emit('update:showFooter', newValue);
});

//=== method ===
const onHover = (index) => {
  hoveredItems[index] = true;
  console.log("onHover:", index, hoveredItems[index]);
};

const onLeave = (index) => {
  hoveredItems[index] = false;
  console.log("onLeave:", index, hoveredItems[index]);
};

const passwordDialog = () => {
  openDialog.value=true;
};

const updateDialog = (newVal) => {
  openDialog.value = newVal;
};
// 測試用
const functionB = () => {
  alert("功能B");
};
// 測試用
const functionC = () => {
  alert("功能C");
};

const updateCountdown = (time) => {
  countdown.value = time;
};

// 登出功能(儲存user操作資料)
const logout = () => {
  console.log("logout...");

  const userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("userData:", userData)
  let payload= {
    itemsPerPage: 0,        //0: itemsPerPage不必update, else要update
    seeIsOk: userData.setting_isSee,
    lastRoutingName: userData.setting_lastRoutingName,
    empID: userData.empID,
  };
  let isAuthenticated = false;
  //status && (setAuthenticated(isAuthenticated), removeLocalStorage(), router.replace({ name: 'LoginRegister' }));
  updateSetting(payload)
  .finally(() => {
    setAuthenticated(isAuthenticated);
    removeLocalStorage();
    router.replace({ name: 'LoginRegister' });
  });
  /*
  updateSetting(payload).then(status => {
    console.log("updateSetting status:", status);
    if (status) {
      setAuthenticated(isAuthenticated);
      removeLocalStorage();
      console.log("Redirecting to LoginRegister...");
      router.replace({ name: 'LoginRegister' });
    }
  }).catch(error => {
    console.error("Error during logout:", error);
  });
  */
  //router.replace({ name: 'LoginRegister' });  //啟動router
  //if (router.currentRoute.value.path !== '/') {
  //  router.push('/');
  //}
};

// 清除localStorage內容
const removeLocalStorage = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
};

// 設定localStorage內容
const setAuthenticated = (isLogin) => {
  localStorage.setItem('Authenticated', isLogin)
};

//
const disableBackButton = () => {
  window.history.pushState(null, '', window.location.href);

  popStateHandler.value = (event) => {
    window.history.pushState(null, '', window.location.href);
  };

  window.addEventListener('popstate', popStateHandler.value);
};

const enableBackButton = () => {
  window.removeEventListener('popstate', popStateHandler.value);
};

const allowBackspaceInInputs = (event) => {
  const target = event.target;
  const isInputElement = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

  if (event.key === 'Backspace' && !isInputElement) {
    event.preventDefault();
  }
};
//
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');
@import "../styles/variables.scss";

.navbar {
  background: $NAVBAR_COLOR !important;
  padding-top: 0px;
  padding-bottom: 0px;
}

.navbar-nav .nav-item {
  margin-right: 20px;                   // 設置每個 nav-item 之間的間距
}

.navbar-nav .nav-item:first-child {     // 第1個nav-item設置左側間距
  margin-left: 40px;
}

.navbar-nav .nav-item:last-child {
  left: 210px;                          // 最後1個 nav-item設置右側距離
}

// 確保左側和右側的nav使用相同的對齊方式
.my-left-nav .dropdownk .dropdown-contentk {
  top: 130%;                            // 確保dropdown內容在nav-item下方, 由100%修改為130%
  margin-top: 0;                        // 根據需要調整
  padding: 0;                           // 根據需要調整
}

// 將所有dropdown內容的垂直位置設置為一致
.my-left-nav .dropdown-contentk {
  top: calc(100% + 10px);             // 根據需要調整10px，確保垂直對齊
  margin-top: 10px;
}

// for the Dropdown Button
.dropbtnk {
  border: none;
  cursor: pointer;
  position: relative;
  display: inline-block;
  top: 8px;
  font-size: 16px;
  font-weight: 700;
  transition: color 0.3s;
  color:rgba(0,0,0,0.65);
  text-decoration: none;            // 取消所有 nav-link 的下劃線

  position: relative;               // 確保dropdown內容相對於父級定位
}

// Dropdown Content (Hidden by Default)
.dropdown-contentk {
  display: none;
  position: absolute;               // 絕對定位dropdown內容
  background-color: #f9f9f9;
  min-width: 160px;
  box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
  z-index: 1;
}

// Links inside the dropdown
.dropdown-contentk a {
  color: black;
  padding: 12px 16px;
  text-decoration: none;
  display: block;
}

// Change color of dropdown links on hover
.dropdown-contentk a:hover, .dropdown-contentk div:hover {
  font-size: 16px;
  font-weight: 700;
  //color: blue;
  color: #01d1b7;
}

// Show the dropdown menu on hover
.dropdownk:hover .dropdown-contentk {
  display: block;
}

// Change the background color of the dropdown button when the dropdown content is shown
.dropdown:hover .dropbtnk {
  color: #01d1b7;
}

li a:hover, .dropdownk:hover .dropbtnk {
  color: #01d1b7;
}

li.dropdownk {
  display: inline-block;
}

.disabled-linkk {
  pointer-events: none;
  color: gray !important;
  font-size: 16px;
  //font-weight: 700;
  opacity: 0.6;             // 調整透明度使其更淡
}

.button-content {
  display: flex;
  flex-direction: column;     // 垂直排列
  //align-items: center;      // 水平居中對齊
  align-items: flex-start;    // 文字靠左對齊
  max-width: 60px;            // 最大寬度
}

.icon-container {
  width: 20px;                // 根據圖標的實際大小調整
  display: inline-block;
  text-align: center;         // 居中對齊圖標
}

.button-title {
  //font-size: 14px;          // 調整文字大小
  line-height: 1.2;           // 調整行高以控制行間距

  //text-align: center;         // 文字居中對齊
  text-align: left;           // 文字靠左對齊
  max-width: 100%;            // 讓文字內容不超過按鈕的寬度
  white-space: normal;        // 允許文字換行
  overflow: hidden;           // 隱藏溢出的文字
  text-overflow: ellipsis;    // 超出部分用省略號表示
}

.button-icon {
  position: relative;
  margin-top: -20px;
  left: 43px;
}
</style>