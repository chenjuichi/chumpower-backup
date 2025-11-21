<template>
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" :timeout="snackbar_timeout" :color="snackbar_color">
    {{ snackbar_info }}
    <template v-slot:actions>
      <v-btn :color="snackbar_icon_color" @click="snackbar = false">
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

      <div class="collapse navbar-collapse" id="navbarNav">
        <!-- 左側 -->
        <ul class="navbar-nav">
        <!--
          <li class="nav-item" v-if="navLinks.link1.isEnabled">
            <router-link class="nav-link my-nav-link-text" to="/home">Home</router-link>
          </li>
          <li class="nav-item" v-if="navLinks.link2.isEnabled">
            <router-link class="nav-link my-nav-link-text" to="/about">About</router-link>
          </li>
        -->

          <li class="nav-item">
            <router-link :to="navLinks.link1.to" class="nav-link my-nav-link-text" :class="{ 'disabled-link': !navLinks.link1.isEnabled }">
              <!-- {{ navLinks.link1.text || 'router link 尚未命名' }} -->
              Home
            </router-link>
          </li>

          <li class="nav-item dropdown" @mouseenter="showDropdown('product_info')" @mouseleave="hideDropdown('product_info')">
            <span class="nav-link my-nav-link-text">在製品生產資訊<i class="fas fa-angle-down" style="position: relative; left: 5px;"></i></span>
            <div class="dropdown-menu" :class="{ show: dropdownOpen.product_info }">
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/a">1.加工區</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/c">2.組裝區</router-link>
            </div>
          </li>



          <li class="nav-item">
            <router-link :to="navLinks.link2.to" class="nav-link my-nav-link-text" :class="{ 'disabled-link': !navLinks.link2.isEnabled }">
              <!-- {{ navLinks.link2.text || 'router link 尚未命名' }} -->
              About
            </router-link>
          </li>

          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/a">Item a</router-link>
          </li>

          <li class="nav-item dropdown" @mouseenter="showDropdown('b')" @mouseleave="hideDropdown('b')">
            <!--<router-link class="nav-link my-nav-link-text" to="/b">Item b <i class="fas fa-angle-down"></i></router-link>-->
            <span class="nav-link my-nav-link-text">Item b <i class="fas fa-angle-down"></i></span>
            <div class="dropdown-menu" :class="{ show: dropdownOpen.b }">
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/a">SubItem A</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/c">SubItem B</router-link>
            </div>
          </li>

          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/c">Item c</router-link>
          </li>
        <!--
          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/d">MyTable</router-link>
          </li>
        -->

          <li class="nav-item dropdown" @mouseenter="showDropdown('data_maintin')" @mouseleave="hideDropdown('data_maintin')">
            <span class="nav-link my-nav-link-text">資料維護<i class="fas fa-angle-down" style="position: relative; left: 5px;"></i></span>
            <div class="dropdown-menu" :class="{ show: dropdownOpen.data_maintin }">
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/a">1.機台資訊</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/c">2.站別資訊</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/a">3.加工區異常原因</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/c">4.組裝區異常原因</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/a">5.人員資訊</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/d">MyTable</router-link>
            </div>
          </li>

        </ul>

        <!--checkbox-->
        <v-checkbox v-model="localShowFooter" label="Show Footer" class="ml-auto" style="position: relative; right: 80px;" />

        <!-- 右側 -->
        <ul class="nav justify-content-end" style="position: relative; right: 70px;">
          <li class="nav-item dropdown" @mouseenter="showDropdown('user')" @mouseleave="hideDropdown('user')">
            <div class="nav-link my-nav-link-text">
              <em>{{ currentUser ? currentUser.name : '使用者' }}</em><i class="fas fa-angle-down" style="position: relative; left: 5px;" />
            </div>
            <div class="dropdown-menu" :class="{ show: dropdownOpen.user }">
              <div class="dropdown-item my-dropdown-item" @click="logout">登出</div>
              <div class="dropdown-item my-dropdown-item" @click="passwordDialog">修改密碼</div>
              <div class="dropdown-item my-dropdown-item" @click="functionB">功能B</div>
              <div class="dropdown-item my-dropdown-item" @click="functionC">功能C</div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </nav>

  <ChangePassword :dialog="openDialog" @update:dialog="updateDialog"></ChangePassword>
</template>

<script setup>
import { ref, watch, computed, defineComponent, onBeforeMount, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { useRoute, useRouter } from 'vue-router'; // Import useRouter
//import logo from '../assets/BBC-Line-Logo_Blue.png';
import logo from '../assets/logo.svg';
import VCheckbox from '../VCheckbox.vue';
import ChangePassword from '../changePassword.vue';
import { myMixin } from '../../mixins/common.js';

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
const snackbar_icon_color = ref('#adadad');
const snackbar_timeout = ref(2000);

const openDialog = ref(false);
const home_url = logo;
const localShowFooter = ref(props.showFooter);
const dropdownOpen = ref({ b: false, user: false, data_maintain: false, product_info: false });
const currentUser = ref(null);
const router = useRouter(); // Initialize router
const route = useRoute(); // Initialize router

//=== method ===
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
@import "../styles/variables.scss";
.navbar {
  background: $NAVBAR_COLOR !important;
  padding-top: 0px;
  padding-bottom: 0px;
}
</style>