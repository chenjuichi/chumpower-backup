<template>
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn color="#adadad" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>


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
          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(0)"
            @mouseleave="onLeave(0)"
          >
            <button class="dropbtnk" :disabled="navLinks.link1.isEnabled">
              <div :class="{'button-content': isSegment }">
                <span :class="{'button-title': isSegment }">{{navLinks.link1.text}}</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[0] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <router-link
                :to="navLinks.link2.isEnabled ? '/a' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks.link2.text }}
              </router-link>
              <router-link
                :to="navLinks.link3.isEnabled ? '/b' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                {{ navLinks.link3.text }}
              </router-link>
              <router-link
                :to="navLinks.link4.isEnabled ? '/c' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks.link4.text }}
              </router-link>
              <router-link
                to="/c"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link2.isEnabled}]"
                :to="navLinks.link5.isEnabled ? '/d' : '#'"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              {{ navLinks.link5.text }}
              </router-link>
            </div>
          </li>

          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(1)"
            @mouseleave="onLeave(1)"
          >
              <button class="dropbtnk">
                <div :class="{'button-content': isSegment }">
                  <span :class="{'button-title': isSegment }">備料清單</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[1] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <router-link
                :to="navLinks.link1.isEnabled ? '/e' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link2.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                1.加工區
              </router-link>
              <router-link
                to="/c"
                :to="navLinks.link2.isEnabled ? '/f' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                2.組裝區
              </router-link>
            </div>
          </li>

          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(2)"
            @mouseleave="onLeave(2)"
          >
              <button class="dropbtnk">
                <div :class="{'button-content': isSegment }">
                  <span :class="{'button-title': isSegment }">組裝生產</span>
                  <span class="icon-container">
                    <i :class="['fas', hoveredItems[2] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
                  </span>
                </div>
              </button>
            <div class="dropdown-contentk">
              <router-link
                :to="navLinks.link1.isEnabled ? '/g1' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link2.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                1.領料生產報工
              </router-link>
              <router-link
                to="/c"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                :to="navLinks.link2.isEnabled ? '/g2' : '#'"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                2.完成生產報工
              </router-link>
              <router-link
                to="/c"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                :to="navLinks.link2.isEnabled ? '/g3' : '#'"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                3.異常填報
              </router-link>
            </div>
          </li>

          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/c">
              成品入庫
            </router-link>
          </li>

          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(4)"
            @mouseleave="onLeave(4)"
          >
            <button class="dropbtnk">
              <div :class="{'button-content': isSegment }">
                <span :class="{'button-title': isSegment }">加工生產</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[4] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <router-link
                :to="navLinks.link1.isEnabled ? '/h1' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link2.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                1.領料生產報工
              </router-link>
              <router-link
                to="/c"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                :to="navLinks.link2.isEnabled ? '/h2' : '#'"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                2.完成生產報工
              </router-link>
              <router-link
                to="/c"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                :to="navLinks.link2.isEnabled ? '/h3' : '#'"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
                3.異常填報
              </router-link>
            </div>
          </li>

          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(5)"
            @mouseleave="onLeave(5)"
          >
            <button class="dropbtnk">
              <div :class="{'button-content': isSegment }">
                <span :class="{'button-title': isSegment }">系統設定</span>
                <span class="icon-container">
                  <i :class="['fas', hoveredItems[5] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
                </span>
              </div>
            </button>
            <div class="dropdown-contentk">
              <router-link
                :to="navLinks.link1.isEnabled ? '/j1' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              1.機台資料維護
              </router-link>

              <router-link
                :to="navLinks.link1.isEnabled ? '/j2' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              2.組裝站資料維護
              </router-link>

              <router-link
                :to="navLinks.link1.isEnabled ? '/j3' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              3.加工異常原因維護
              </router-link>

              <router-link
                :to="navLinks.link1.isEnabled ? '/j4' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              4.組裝異常原因維護
              </router-link>

              <router-link
                :to="navLinks.link1.isEnabled ? '/employer' : '#'"
                :class="['dropdown-item', 'my-dropdown-item', {'disabled-linkk': !navLinks.link1.isEnabled}]"
                @click.prevent="!openMenuItem && $event.stopPropagation()"
              >
              5.人員資料維護
              </router-link>
            </div>
          </li>

          <li
            class="nav-item dropdown dropdownk"
            @mouseenter="onHover(6)"
            @mouseleave="onLeave(6)"
          >
            <button class="dropbtnk">
              <em>{{ currentUser ? currentUser.name : '使用者' }}</em>
              <span class="icon-container">
                <i :class="['fas', hoveredItems[6] ? 'fa-angle-right' : 'fa-angle-down', {'button-icon' : isSegment}]" />
              </span>
            </button>
            <div class="dropdown-contentk">
              <div class="dropdown-item my-dropdown-item" @click="logout">登出</div>
              <div class="dropdown-item my-dropdown-item" @click="passwordDialog">修改密碼</div>
              <div class="dropdown-item my-dropdown-item" @click="functionB">功能B</div>
              <div class="dropdown-item my-dropdown-item" @click="functionC">功能C</div>
            </div>
          </li>
        </ul>

        <!--checkbox-->
        <v-checkbox v-model="localShowFooter" label="Show Footer" class="ml-auto" style="position: relative; right: 180px;" />
      </div>
    </div>
  </nav>

  <ChangePassword :dialog="openDialog" @update:dialog="updateDialog"></ChangePassword>
</template>

<script setup>
import { ref, reactive, watch, computed, defineComponent, onBeforeMount, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router'; // Import useRouter
//import logo from '../assets/BBC-Line-Logo_Blue.png';
import logo from '../assets/logo.svg';
import VCheckbox from './VCheckbox.vue';
import ChangePassword from './changePassword.vue';
import { myMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'Nav'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ==
const props = defineProps({
  showFooter: Boolean,

  navLinks: {
    type: Object,
    required: true,
    default: () => ({})
  },
});

//=== emits ==
const emit = defineEmits(['update:showFooter']);

//=== data ===
const snackbar = ref(false);
const snackbar_color = ref('red accent-2');
const snackbar_info = ref('');

const isHovered = ref(false);
const isSegment = ref(false);
const openDialog = ref(false);
const home_url = logo;
const localShowFooter = ref(props.showFooter);
const dropdownOpen = ref({ b: false, user: false, data_maintain: false, product_info: false });

const hoveredItems = reactive({});
const dropdownContent = reactive({
  product_info: null,
})
const currentUser = ref(null);
const router = useRouter(); // Initialize router
const route = useRoute(); // Initialize router

//=== method ===
const onHover = (index) => {
  //console.log("onHover:", index, hoveredItems[index]);
  hoveredItems[index] = true;
  console.log("onHover:", index, hoveredItems[index]);
};

const onLeave = (index) => {
  hoveredItems[index] = false;
  console.log("onLeave:", index, hoveredItems[index]);
};

const showDropdownk = () => {
  if (dropdownContent.product_info) {
    dropdownContent.product_info.style.display = 'block';
  }
};

const hideDropdownk = () => {
  if (dropdownContent.product_info) {
    dropdownContent.product_info.style.display = 'none';
  }
};

const showDropdown = (item) => {
  dropdownOpen.value[item] = true;
};

const hideDropdown = (item) => {
  dropdownOpen.value[item] = false;
};

const disableBackButton = () => {
  window.history.pushState(null, "", window.location.href);
  window.onpopstate = handlePopState;
};

const handlePopState = () => {
  window.history.pushState(null, "", window.location.href);
};

const enableBackButton = () => {
  window.onpopstate = null;
};

const passwordDialog = () => {
  //console.log("before openDialog:", openDialog.value)
  openDialog.value=true;
  //console.log("after openDialog:", openDialog.value)
};

const updateDialog = (newVal) => {
  openDialog.value = newVal;
};

const functionB = () => {
  alert("功能B");
};

const functionC = () => {
  alert("功能C");
};

const logout = () => {
  console.log("logout...");

  updateSetting();
  const isAuthenticated=false;
  setAuthenticated(isAuthenticated);
  removeLoginUser();

  if (router.currentRoute.value.path !== '/') {
    router.push('/');
  }
};

const updateSetting = () => {
  console.log("updateSetting()...")
  //console.log("updateSetting(),", routeName)

  const userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("userData:", userData)
  let path='/updateSetting';
  let payload= {
    items_per_page: userData.setting_items_per_page,
    see_is_ok: userData.setting_isSee,
    lastRoutingName: userData.setting_lastRoutingName,
    empID: userData.empID,
  };

  axios.post(path, payload)
  .then(res => {
      console.log("update user's setting:", res.data.status);
  })
  .catch(err => {
      console.error(err);
      snackbar_info.value = '錯誤! API連線問題...';
      snackbar.value = true;
  });
};

const removeLoginUser = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
};

const setAuthenticated = (isLogin) => {
  localStorage.setItem('Authenticated', isLogin)
};

//=== mounted ===
onMounted(() => {
  disableBackButton();
  console.log("nav, mounted():",props.navLinks);

  hoveredItems[0]=false;
  hoveredItems[1]=false;
  hoveredItems[2]=false;
  hoveredItems[3]=false;
  hoveredItems[4]=false;
  hoveredItems[5]=false;
  hoveredItems[6]=false;

});

//=== unmounted ===
onUnmounted(() => {
  enableBackButton();
});

//=== created ===
onBeforeMount(() => {
  const user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  //currentUser.value = JSON.parse(localStorage.getItem("loginedUser"));
  console.log("nav, created(), current user:", currentUser.value);

  initAxios();
});

//=== computed ===
//const routeName = computed(() => route.name);

//=== watch ===
watch(localShowFooter, (newValue) => {
  console.log("Nav.vue, watch(),", newValue)

  emit('update:showFooter', newValue);
});
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
  top: 100%;        // 確保dropdown內容在nav-item下方
  margin-top: 0;    // 根據需要調整
  padding: 0;       // 根據需要調整
}

// 將所有dropdown內容的垂直位置設置為一致
.my-left-nav .dropdown-contentk {
  top: calc(100% + 10px);             // 根據需要調整10px，確保垂直對齊
  margin-top: 10px;
}


// Style The Dropdown Button
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