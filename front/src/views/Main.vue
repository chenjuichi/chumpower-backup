<template>
  <div class="main-background">
    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn color="#adadad" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <img id="sourceImage" :src="imageSrc" alt="Background Image" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';


//=== data ===
const route = useRoute();

const currentUser = ref({});

const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

//const imageSrc = ref(require('../assets/main_background_img.png'))
//const imageSrc = ref(require('../assets/20250630-chumpower-main.png'))
const imageSrc = ref(require('../assets/20250708-chumpower-main.png'))

const showBackWarning = ref(true);


//=== computed ===
const routeName = computed(() => route.name);

//=== mounted ===
onMounted(() => {
  console.log("Main.vue, mounted()...");

  updateContentStyles('hidden', '0');

  // 阻止直接後退
  window.history.pushState(null, null, document.URL);
  //history.pushState(null, null, document.URL)
  window.addEventListener('popstate', handlePopState)

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  //userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
});

//=== unmounted ===
onUnmounted(() => {
  updateContentStyles('auto', '20px');

  window.removeEventListener('popstate', handlePopState);

});

//=== method ===
/*
const updateContentOverflow = (overflowValue) => {
  const contentElement = document.querySelector('.content');
  if (contentElement) {
    contentElement.style.overflow = overflowValue;
  }
};
*/
const updateContentStyles = (overflowValue, paddingValue) => {
  const contentElement = document.querySelector('.content');
  if (contentElement) {
    contentElement.style.overflow = overflowValue;
    contentElement.style.padding = paddingValue;
  }
};
/*
const handlePopState = () => {
  // 重新添加歷史紀錄以阻止實際後退
  history.pushState(null, null, document.URL)

  // 只在第一次顯示警告
  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面内的導航按鍵', 'red accent-2');
    showBackWarning.value = false
  }
}
*/
const handlePopState = () => {
  //// ✅ 正確方式：保留 Vue Router 的 state
  ////history.pushState(history.state, '', document.URL)
  ////history.replaceState(history.state, '', document.URL);
  //window.history.pushState(history.state, '', document.URL)

  // 重新 push 一次，但保留原狀態
  window.history.pushState({ ...history.state }, '', document.URL);


  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

</script>

<style lang="scss" scoped>
  //html, body {
  //  height: 100%;
  //  margin: 0;
  //  overflow: hidden; /* 禁用scroll bar */
  //}

  .main-background {
    display: flex;
    justify-content: center;
    align-items: center;
    height: calc(100vh - 120px); /* 調整高度以考慮 Nav 和 Footer 的高度 */
    margin-top: 60px;
    margin-bottom: 60px;
  }

  .main-background img {
    width: 100%;
    height: 150%;
    object-fit: cover;
  }
  </style>
