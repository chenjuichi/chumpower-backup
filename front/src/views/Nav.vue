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
        <ul class="navbar-nav my-left-nav" style="font-weight: 700;">
          <!--item1-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(0)"
            @mouseleave="onLeave(0)"
          >
            <button class="dropbtnk" :disabled="localNavLinks[0].isEnabled">
              <div :class="{'button-content': localNavLinks[0].isSegment }">
                <!--item1, menu 1-->
                <span :class="{'button-title': localNavLinks[0].isSegment }">{{ localNavLinks[0].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[0] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[0].isSegment }]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 2-->
            <!--
              <router-link
                :to="localNavLinks[1].isEnabled ? localNavLinks[1].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[1].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[1].text }}
              </router-link>
            -->
              <!--menu 3-->
              <router-link
                :to="localNavLinks[2].isEnabled ? localNavLinks[2].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[2].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[2].text }}
              </router-link>
              <!--menu 4-->
              <router-link
                :to="localNavLinks[3].isEnabled ? localNavLinks[3].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[3].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ localNavLinks[3].text }}
              </router-link>
              <!--menu 5-->
            <!--
              <router-link
                :to="localNavLinks[4].isEnabled ? localNavLinks[4].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[4].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ localNavLinks[4].text }}
              </router-link>
            -->
            </div>
          </li>
          <!--item2-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(1)"
            @mouseleave="onLeave(1)"
          >
              <button class="dropbtnk" :disabled="localNavLinks[5].isEnabled">
                <div :class="{'button-content': localNavLinks[5].isSegment }">
                  <!--item2, menu 6-->
                  <span :class="{'button-title': localNavLinks[5].isSegment }">{{ localNavLinks[5].text }}</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[1] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[5].isSegment }]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <!--menu 7-->
              <router-link
                :to="localNavLinks[6].isEnabled ? localNavLinks[6].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[6].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[6].text }}
              </router-link>
              <!--menu 8-->
              <router-link
                :to="localNavLinks[7].isEnabled ? localNavLinks[7].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[7].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[7].text }}
              </router-link>
            </div>
          </li>
          <!--item3-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(2)"
            @mouseleave="onLeave(2)"
          >
              <button class="dropbtnk" :disabled="localNavLinks[8].isEnabled">
                <div :class="{'button-content': localNavLinks[8].isSegment }">
                  <!--item3, menu 9-->
                  <span :class="{'button-title': localNavLinks[8].isSegment }">{{ localNavLinks[8].text }}</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[2] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[8].isSegment}]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <!--menu 10-->
              <router-link
                :to="localNavLinks[9].isEnabled ? localNavLinks[9].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[9].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[9].text }}

                <v-badge color="info" :content="begin_count" inline v-show="begin_count != 0"  />
              </router-link>
              <!--menu 11-->
              <router-link
                :to="localNavLinks[10].isEnabled ? localNavLinks[10].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', { 'disabled-linkk': !localNavLinks[10].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[10].text }}

                <v-badge color="info" :content="end_count" inline v-show="end_count != 0" />
              </router-link>
              <!--menu 12-->
              <router-link
                :to="localNavLinks[11].isEnabled ? localNavLinks[11].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[11].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[11].text }}
              </router-link>
            </div>
          </li>
          <!--item4-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(3)"
            @mouseleave="onLeave(3)"
          >
            <button class="dropbtnk" :disabled="localNavLinks[12].isEnabled">
              <div :class="{'button-content': localNavLinks[12].isSegment }">
                <!--item4, menu 13-->
                <span :class="{'button-title': localNavLinks[12].isSegment }">{{ localNavLinks[12].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[3] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[12].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 14-->
              <router-link
                :to="localNavLinks[13].isEnabled ? localNavLinks[13].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[13].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ localNavLinks[13].text }}
              </router-link>
              <!--menu 15-->
            <!--
              <router-link
                :to="localNavLinks[14].isEnabled ? localNavLinks[14].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[14].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ localNavLinks[14].text }}
              </router-link>
            -->
              <!--menu 16-->
            <!--
              <router-link
                :to="localNavLinks[15].isEnabled ? localNavLinks[15].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[15].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[15].text }}
              </router-link>
            -->
            </div>
          </li>
          <!--item5-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(4)"
            @mouseleave="onLeave(4)"
          >
            <button class="dropbtnk" :disabled="localNavLinks[16].isEnabled">
              <div :class="{'button-content': localNavLinks[16].isSegment }">
                <!--item5, menu 17-->
                <span :class="{'button-title': localNavLinks[16].isSegment }">{{ localNavLinks[16].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[4] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[16].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 18-->
              <router-link
                :to="localNavLinks[17].isEnabled ? localNavLinks[17].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[17].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[17].text }}
              </router-link>
              <!--menu 19-->
              <router-link
                :to="localNavLinks[18].isEnabled ? localNavLinks[18].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[18].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[18].text }}
              </router-link>
              <!--menu 20-->
              <router-link
                :to="localNavLinks[19].isEnabled ? localNavLinks[19].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[19].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[19].text }}
              </router-link>
            </div>
          </li>
          <!--item6-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(5)"
            @mouseleave="onLeave(5)"
          >
            <button class="dropbtnk" :disabled="localNavLinks[20].isEnabled">
              <div :class="{'button-content': localNavLinks[20].isSegment }">
                <!--item6, menu 21-->
                <span :class="{'button-title': localNavLinks[20].isSegment }">{{ localNavLinks[20].text }}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[5] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : localNavLinks[20].isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <!--menu 22-->
              <router-link
                :to="localNavLinks[21].isEnabled ? localNavLinks[21].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[21].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[21].text }}
              </router-link>
              <!--menu 23-->
              <router-link
                :to="localNavLinks[22].isEnabled ? localNavLinks[22].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[22].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[22].text }}
              </router-link>
              <!--menu 24-->
              <router-link
                :to="localNavLinks[23].isEnabled ? localNavLinks[23].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[23].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[23].text }}
              </router-link>
              <!--menu 25-->
              <router-link
                :to="localNavLinks[24].isEnabled ? localNavLinks[24].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[24].isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[24].text }}
              </router-link>
              <!--menu 26-->
              <router-link
                :to="localNavLinks[25].isEnabled ? localNavLinks[25].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[25].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[25].text }}
              </router-link>

              <!--menu 27-->
              <router-link
                :to="localNavLinks[26].isEnabled ? localNavLinks[26].to : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !localNavLinks[26].isEnabled }]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ localNavLinks[26].text }}
              </router-link>

            </div>
          </li>
          <!--item7-->
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(6)"
            @mouseleave="onLeave(6)"
            style="left: 125px;"
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
              <div class="dropdown-item my-dropdown-item" @click="browserDialog">表單貼條碼</div>
              <div class="dropdown-item my-dropdown-item" @click="functionC">功能C</div>
            </div>
          </li>
          <!--item8-->
          <li class="nav-item" style="position: relative; left: 125px; font-size: 13px; margin-right: 0px;">
            <span style="background: #1976d2; color: white; font-weight: 400; font-size: 16px;">
              剩餘時間: {{ countdown.minutes }}:{{ countdown.seconds }}
            </span>
          </li>
        </ul>



        <!--checkbox-->
      <!--
        <v-checkbox
          v-model="localShowFooter"
          label="Show Footer"
          class="ml-auto"
          style="position: relative; right: 200px;"
        />
      -->
      <!--
        <v-checkbox
          v-model="localShowFooter"
          v-model:modelValue="localShowFooter"
  				@update:modelValue="updateShowFooter"

          label="Show Footer"
          class="ml-auto"
          style="position: relative; right: 200px;"
        />
      -->
      </div>
    </div>
  </nav>

  <ChangePassword :dialog="openDialog" @update:dialog="updateDialog" />
  <BrowseDirectory :pdf="openPdfDialog" @update:pdf="updatePdfDialog" />
</template>

<script setup>
import { ref, reactive, watch, watchEffect, computed, defineComponent, onBeforeMount, onMounted, onBeforeUnmount, onUnmounted } from 'vue';
//import { useRoute, useRouter } from 'vue-router'; // Import useRouter
import { useRouter } from 'vue-router'; // Import useRouter
//import logo from '../assets/BBC-Line-Logo_Blue.png';
import logo from '../assets/logo.svg';

//import VCheckbox from './VCheckbox.vue';
import ChangePassword from './changePassword.vue';
import BrowseDirectory from './BrowseDirectory.vue';

import { empPermMapping, roleMappings, flatItems } from '../mixins/MenuConstants.js';

import eventBus from '../mixins/enentBus.js';

import { myMixin } from '../mixins/common.js';

import { begin_count, end_count }  from '../mixins/crud.js';

import { apiOperation, }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');

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
  //navBarColor: String,
  navBarColor: {
    type: String,
    default: "#f9f9f9", // 提供默認值，避免 undefined
  },

  navLinks: {
    type: Array,
    required: true,
    default: () => []
  },
});

const localNavLinks = ref([...props.navLinks]);

//=== emits ==
const emit = defineEmits(['update:showFooter']);

//=== data ===
const isSegment = ref(false);
const openDialog = ref(false);
const openPdfDialog = ref(false);

let intervalId = null;                        // 間格10秒, 倒數計時器

const home_url = logo;
const localShowFooter = ref(props.showFooter);
const bgColor = ref('');
//const dropdownOpen = ref({ b: false, user: false, data_maintain: false, product_info: false });

const hoveredItems = reactive({});
//const dropdownContent = reactive({
//  product_info: null,
//})
const currentUser = ref(null);
const popStateHandler = ref(null);

const initialSelection = Array(26).fill(0).map((_, i) => (roleMappings['員工'].includes(i + 1) ? 1 : 0));

const countdown = ref({
  minutes: '00',
  seconds: '00'
});

const router = useRouter(); // Initialize router
//const route = useRoute(); // Initialize router

//=== mounted ===
onMounted(() => {
  console.log("nav, mounted():",props.navLinks);

  // 自動追蹤callBack裡的響應式數據, bgColor.value
  watchEffect(() => (bgColor.value = props.navBarColor));

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

  intervalId = setInterval(listWaitForAssembleFun, 10 * 1000);  // 每 10秒鐘調用一次 API
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
  clearInterval(intervalId);    // 清除計時器（當元件卸載時）
});

//=== created ===
onBeforeMount(() => {
  console.log("nav.vue, created(), props.navLinks:", props.navLinks);
  console.log("nav.vue, created(), localNavLinks:", localNavLinks.value);

  if (props.navLinks.length != 0) {
    localStorage.setItem('navLinks', JSON.stringify(props.navLinks));
  } else {
    let temp_navLinks = JSON.parse(localStorage.getItem("navLinks"));
    if (temp_navLinks)
      localNavLinks.value = temp_navLinks;
  }

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("nav.vue, created(), current user:", currentUser.value);
  //
  if (currentUser.value) {
    let default_routingPriv = initialSelection.join(',');
    let routingPriv_string = (currentUser.value.setting_routingPriv == '') ? default_routingPriv : currentUser.value.setting_routingPriv;
    let routingPriv_array = routingPriv_string.split(',').map(value => value === '1');
    console.log("routingPriv_array:", routingPriv_array);

    // 使用 routingPriv_array 的值更新 reactiveLinks 中每個物件的 isEnabled 屬性
    localNavLinks.value.forEach((link, index) => {
      if (index < routingPriv_array.length) {
        link.isEnabled = routingPriv_array[index];
      }
    });
    console.log("localNavLinks:", localNavLinks.value);
  }
  //
  initAxios();
  initialize();
});

//=== computed ===

//=== watch ===
watch(localShowFooter, (newValue) => {
  console.log("Nav.vue, watch(),", newValue)
  localShowFooter.value = newValue;           // 2024-11-26 add

  emit('update:showFooter', newValue);
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

    await listWaitForAssembleFun();
    //console.log("begin_count, end_count:", begin_count, end_count);
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const listWaitForAssembleFun = async () => {
  await listWaitForAssemble();
}

const onHover = (index) => {
  hoveredItems[index] = true;
  console.log("onHover:", index, hoveredItems[index]);
  console.log("begin_count, end_count:", begin_count.value, end_count.value);
};

const onLeave = (index) => {
  hoveredItems[index] = false;
  console.log("onLeave:", index, hoveredItems[index]);
};

const passwordDialog = () => {
  openDialog.value=true;
};
const browserDialog = () => {
  console.log("browserDialog()...")
  openPdfDialog.value=true;
  console.log("openPdfDialog:", openPdfDialog.value)
};

const updateDialog = (newVal) => {
  openDialog.value = newVal;
};

const updatePdfDialog = (newVal) => {
  openPdfDialog.value = newVal;
};

const updateShowFooter = (newColor) => {
  localShowFooter.value = newColor; 							// 更新本地顏色
  emit('update:showFooter', newColor); 	          // 通知父層更新
  console.log('Updated showFooter:', newColor);
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
  //status && (setAuthenticated(isAuthenticated), removelocalStorage(), router.replace({ name: 'LoginRegister' }));
  updateSetting(payload)
  .finally(() => {
    setAuthenticated(isAuthenticated);
    removelocalStorage();
    //router.replace({ name: 'LoginRegister' });
    const resolvedRoute = router.resolve({ name: 'LoginRegister' });
    const path = resolvedRoute.href;  // 取得解析後的 path
    router.replace({ path });         // 使用 path 來進行導航
  });
  /*
  updateSetting(payload).then(status => {
    console.log("updateSetting status:", status);
    if (status) {
      setAuthenticated(isAuthenticated);
      removelocalStorage();
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
const removelocalStorage = () => {
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
  //background: $NAVBAR_COLOR !important;
  background: v-bind(bgColor) !important;
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