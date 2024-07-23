<template>
  <div class="container">
    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" location="top right" :timeout="snackbar_timeout" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn :color="snackbar_icon_color" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <div class="overlay-container">
      <!--跑馬燈效果-->
      <!--垂直滾動-->
      <!--<div style="position: relative; top: -220px; right: -240px; height: 50px; width: max-content">-->
        <!--<Vue3Marquee :pause-on-hover="true" :vertical="true">-->
      <!--水平滾動-->
      <div style="position: relative; top: -220px; right: -240px; width: 650px;">
        <Vue3Marquee :pause-on-hover="true">
          <template v-for="(word, index) in helloArray" :key="index">
            <span>{{ word }}</span>
            <span>&nbsp;&nbsp;&nbsp;</span> <!-- 間隔3個空白 -->
          </template>
        </Vue3Marquee>
      </div>
      <!--企業視覺圖像-->
      <img id="sourceImage" :src="imageSrc" alt="Logo" style="display: none;" />
      <canvas id="canvas" class="logo_img" />
      <p class="logo_text">{{ company_name }}</p>
      <!--<p class="logo_designer_text">{{ designer_name }}</p>-->
      <img :src="pmcLogoSrc" alt="PMC Logo" class="logo_designer_img" />
    </div>

    <!--登入-->
    <transition name="slide-in-left">
      <div v-if="!signUp" class="sign-in">
        <div @submit.prevent="userLogin" style="position: relative; top: -20px;">
          <!--
            @change='checkEmpty("loginEmpID")'
          -->
          <v-text-field
            label="工號"

            @update:focused ="listUsers"
            prepend-icon="mdi-account"
            v-model="loginUser.loginEmpID"
            :rules="[requiredRule, empIDRule]"
            ref="loginEmpIDInput"
            @keypress="handleKeyDown"
            @keydown.enter="focusPasswordInput"
            @keydown.tab.prevent="focusPasswordInput"
            id="loginEmpID"
            style="width: 100% !important; max-width: 183px !important;"
          />

          <v-text-field
            label="姓名"
            readonly
            prepend-icon="mdi-account-edit"
            v-model="loginUser.loginName"
            style="width: 100% !important; max-width: 183px !important;"
          />
          <!--
            @change='checkEmpty("loginPassword")'
          -->
          <v-text-field
            label="密碼"

            prepend-icon="mdi-lock"
            :append-icon="eyeShow ? 'mdi-eye-off' : 'mdi-eye'"
            :type="eyeShow ? 'password' : 'text'"
            @click:append="eyeShow = !eyeShow"
            v-model="loginUser.loginPassword"
            :rules="[requiredRule, passwordRule]"
            @keydown.enter="userLogin"
            @keydown.tab.prevent="handlePasswordTab"
            ref="passwordInput"
            class="password-field"
            style="width: 100% !important; max-width: 143px !important; transition: none;"
          />

          <v-btn ref="loginButton" type="submit" color="primary" class="btns" id="login" @click="userLogin">
            <i class="fa-solid fa-right-to-bracket fa-fade" style="color: #63E6BE;"></i>
            登入
          </v-btn>
        </div>
        <p class="mark_texts">員工註冊 <a href="#" @click.prevent="toggleSignUp">註冊</a></p>

        <!--<div v-if="openMenu" class="floating-menu-wrapper">-->
        <div v-if="false" class="floating-menu-wrapper">
          <v-menu>
            <template v-slot:activator="{ props }">
              <v-btn color="primary" variant="outlined" v-bind="props" style="width: 100px;" class="floating-menu-button">
                <v-icon icon="mdi-menu" start></v-icon>
                系統選單
              </v-btn>
            </template>
            <v-card>
              <v-card-text class="pa-6">
                <nav class="floating-menu">
                  <router-link :to="link1.to" class="floating-menu-link" :class="{ 'disabled-link': !link1.isEnabled }">
                    {{ link1.text }}
                  </router-link>
                  <router-link :to="link2.to" class="floating-menu-link" :class="{ 'disabled-link': !link2.isEnabled }">
                    {{ link2.text }}
                  </router-link>
                </nav>
              </v-card-text>
            </v-card>
          </v-menu>
        </div>
      </div>
    </transition>
    <!--註冊-->
    <transition name="slide-in-right">
      <div v-if="signUp" class="sign-up">
        <div style="position: relative; top: 0px;">
          <v-text-field
            label="工號"
            color="primary"
            prepend-icon="mdi-account"
            v-model="registerUser.empID"
            :rules="[requiredRule, empIDRule]"
            @blur="checkUsers"
            @keypress="handleKeyDown"
            ref="registerEmpIDInput"
            style="width: 100% !important; max-width: 183px !important;"
          />

          <v-text-field
            label="姓名"
            color="primary"
            prepend-icon="mdi-account-edit"
            v-model="registerUser.name"
            :rules="[requiredRule, nameRule]"
            style="width: 100% !important; max-width: 183px !important;"
          />

          <v-select
            :items="departments"
            label="部門"
            color="primary"
            prepend-icon="mdi-account-group"
            v-model="registerUser.dep"
            :rules="[requiredRule]"

            @update:menu="handleMenuUpdate"
            @update:modelValue="handleModelValueUpdate"

            style="width: 100% !important; max-width: 183px !important;"
          />

          <v-text-field
            label="密碼"
            color="primary"
            prepend-icon="mdi-lock"
            :append-icon="eyeShow1 ? 'mdi-eye-off' : 'mdi-eye'"
            :type="eyeShow1 ? 'password' : 'text'"
            @click:append="eyeShow1 = !eyeShow1"
            v-model="registerUser.password"
            :rules="[requiredRule, passwordRule]"
            ref="registerPasswordInput"
            style="width: 100% !important; max-width: 183px !important;"
          />

          <v-text-field
            label="確認密碼"
            color="primary"
            prepend-icon="mdi-account-check"
            :type="eyeShow1 ? 'password' : 'text'"
            v-model="registerUser.confirmPassword"
            :rules="[requiredRule, confirmPasswordRule]"
            @keydown.enter="register"
            @keydown.tab.prevent="handlePasswordConfirmTab"
            style="width: 100% !important; max-width: 183px !important;"
          />
          <v-btn ref="registerButton" type="submit" color="primary" class="btns" id="register" @click="register">
            <i class="fa-solid fa-user-plus fa-fade" style="color: #63E6BE;"></i>
            註冊
          </v-btn>
        </div>
        <p class="lg_mark_texts">員工登入 <a href="#" @click.prevent="toggleSignUp">登入</a></p>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, defineComponent, watch, onMounted, onBeforeMount, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { Vue3Marquee } from 'vue3-marquee';
import { routerLinks } from '../router/index.js';
import { myMixin } from '../mixins/common.js';
import { authModule, eventBus } from '../mixins/enentBus.js';

//=== component name ==
defineComponent({
  name: 'LoginForm'
});

// === mix ==
const { initAxios } = myMixin();

//=== data ===
const imageSrc = ref(require('../assets/pet4-rb.png')); //企業視覺圖像
const company_name = ref('銓寶工業股份有限公司')
//const designer_name = ref('財團法人精密機械研究發展中心設計')
const pmcLogoSrc = ref(require('../assets/pmc_logo.png')); // PMC logo 圖像

const snackbar = ref(false);
const snackbar_color = ref('red accent-2');
const snackbar_info = ref('');
const snackbar_icon_color = ref('#adadad');
const snackbar_timeout = ref(2000);

const isRegisterUserFocused = ref(false);
const isLoginUserFocused = ref(false);

const openMenu = ref(false);
const signUp = ref(false);
const departments = ref([]);
const temp_desserts = ref([]);
const foundDessert = ref(null);
const eyeShow = ref(true);
const eyeShow1 = ref(true);

const list_table_is_ok = ref(false);
const get_table_is_ok = ref(false);

const helloArray = ['公告欄: 測試...測試...', '部門A:', '訊息', , '部門B:', '訊息',, '部門C:', '訊息',]

const loginUser = reactive({
  loginEmpID:  '',
  loginName: '',
  loginPassword: ''
});

const registerUser = reactive({
  empID: '',
  name: '',
  dep: '',
  password: '',
  confirmPassword: '',
});

const link1 = reactive({
  text: 'Home',
  to: '/home',
  isEnabled: true,
});
const link2 = reactive ({
  text: 'About',
  to: '/about',
  isEnabled: false,
});
const emit = defineEmits(['setLinks']);

const loginEmpIDInput = ref(null);
const registerEmpIDInput = ref(null);

const passwordInput = ref(null);
const loginButton = ref(null);
const registerButton = ref(null);
const registerPasswordInput = ref(null);
/*
const user_data = reactive({
  dep: '',
  empID: '',
  isOnline: false,
  name: '',
  password: '',
  perm: 3,
  perm_name: 'member',
  setting_items_per_page: 10,
  setting_lastRoutingName: '',
  setting_message: '',
  setting_routingPriv: '',
});
*/
let myIdField = null;
let loginEmpID_max_length = 5;

const router = useRouter();

//=== mounted ===
onMounted(() => {
  console.log("LoginForm, onMounted()...")

  replaceImageColor();  //處理企業圖像

  myIdField = document.getElementById("loginEmpID");
  if (myIdField) {
    myIdField.addEventListener('keydown', handleKeyDown);
  }

  loginEmpIDInput.value.focus();   // 元件掛載時聚焦在工號欄位

  console.log("routerLinks:",routerLinks);
});
//=== destroyed ===
onBeforeUnmount(() => {
  console.log("LoginForm, destroyed()...")

  if (myIdField) {
    myIdField.removeEventListener('keydown', handleKeyDown);
  }
});


//=== watch ===
watch(list_table_is_ok, (val) => {
  if (val) {
    temp_desserts.value.sort((a, b) => a.emp_id - b.emp_id);  //升冪排序
    foundDessert.value = temp_desserts.value.find(dessert => dessert.emp_id === loginUser.loginEmpID);
    if (foundDessert.value) {
      loginUser.loginName = foundDessert.value.emp_name;
    } else {
      if (loginUser.loginEmpID !='') {
        snackbar_info.value = '錯誤, 找不到工號' + loginUser.loginEmpID + '!';
        snackbar.value = true;
      }
      loginEmpIDInput.value.focus();
    }
    list_table_is_ok.value = false;
  }
});
/*
watch(get_table_is_ok, (val) => {
  if (val) {
    user_data = temp_user_data;
    console.log("login user:",user_data);
    signInUser(user_data);
    get_table_is_ok.value = false;
  }
});
*/
//=== computed ===
/*
const foundDessert = computed(() => {

});
*/
//=== mounted ===
onMounted(() => {
   console.log("LoginForm, mounted()...");
});

//=== unmounted ===
/*
onUnmounted(() => {
  console.log("LoginForm, onUnmounted()...")

});
*/

//=== created ===
onBeforeMount(() => {
  console.log("LoginForm, created()...")

  initAxios();
  initialize();
});

//=== method ===
const initialize = () => {
  console.log("initialize()...")

  listDepartments();
};

const listDepartments = () => {
  console.log("listDepartments()...")

  const path = '/listDepartments';
  axios.get(path)
  .then((res) => {
    departments.value=[...res.data.departments];
  })
  .catch((error) => {
    console.error(error);
    snackbar_info.value = '錯誤! API連線問題...';
    snackbar.value = true;
  });
};

const listUsers = (focused) => {
  if (!focused) { // 當失去焦點時
    console.log("listUsers()...");

    isLoginUserFocused.value=false;

    list_table_is_ok.value = false;
    const path = '/listUsers';
    axios.get(path)
    .then((res) => {
      temp_desserts.value = res.data.users;
      console.log("GET ok, total records:", res.data.users.length);
      list_table_is_ok.value = true;
    })
    .catch((error) => {
      console.error(error);
      snackbar_info.value = '錯誤! API連線問題...';
      snackbar.value = true;
    });
  } else {
    isLoginUserFocused.value=true
  }
};

const checkUsers = () => {
  console.log("checkUser(), not focused");

  isRegisterUserFocused.value=true;
  foundDessert.value = temp_desserts.value.find(dessert => dessert.emp_id === loginUser.loginEmpID);
  if (foundDessert.value) {
    if (registerUser.empID !='') {
      snackbar_info.value = '錯誤, 工號' + registerUser.empID + '重複!';
      snackbar.value = true;
    }
    registerEmpIDInput.value.focus();
  }

};

const focusPasswordInput = (event) => {
  event.preventDefault();
  passwordInput.value.focus();
};

//const focusRegisterPassword = async (focused) => {
const focusRegisterPassword = (focused) => {
  if (!focused) { // 當失去焦點時
    //await nextTick();
    registerPasswordInput.value.focus();
  }
};

const handleMenuUpdate = (menuState) => {
  console.log('Menu state updated:', menuState);
  if (!menuState) { // 當菜單關閉，focus到密碼欄位
    focusRegisterPassword();
  }
};

const handleModelValueUpdate = (newValue) => {
  console.log('Model value updated:', newValue);
  registerUser.dep = newValue;
};
/*
const focusLoginButton = (event) => {
  event.preventDefault();
  if (event.shiftKey) {
    passwordInput.value.focus();
  } else {
    loginButton.value.$el.focus();
  }
};
*/
const handlePasswordConfirmTab = (event) => {
  event.preventDefault();
  if (event.shiftKey) {
    registerEmpIDInput.value.focus();
  } else {
    registerButton.value.$el.focus();
  }
};

const handlePasswordTab = (event) => {
  event.preventDefault();
  if (event.shiftKey) {
    loginEmpIDInput.value.focus();
  } else {
    loginButton.value.$el.focus();
  }
};

const handleKeyDown = (event) => {
  const inputChar = event.key;

  const caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when you press the keyboard CapsLock key

  // 允許左右方向鍵、backspace和delete鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }

  const inputValue = event.target.value || ''; // 确保 inputValue 是字符串

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar) || inputValue.length >= loginEmpID_max_length) {
    event.preventDefault();
  }
};

const toggleSignUp = () => {
  console.log("toggleSignUp()")

  isRegisterUserFocused.value=false;
  isLoginUserFocused.value=false;

  signUp.value = !signUp.value;
};

const replaceImageColor = () => {
  console.log("replaceImageColor()...");

  const sourceImage = document.getElementById('sourceImage');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');

  ctx.canvas.willReadFrequently = true;   //啟動 willReadFrequently 優化

  sourceImage.onload = function() {
    canvas.width = sourceImage.width;
    canvas.height = sourceImage.height;

    ctx.drawImage(sourceImage, 0, 0);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];

        // If the pixel is white, make it transparent
        if (r > 240 && g > 240 && b > 240) {
            data[i + 3] = 0; // Alpha channel
        }
    }

    ctx.putImageData(imageData, 0, 0);
  };

  // 觸發圖片加載
  sourceImage.src = imageSrc.value;
}

const register = () => {
  if (
    !registerUser.empID ||
    !registerUser.name ||
    !registerUser.dep ||
    !registerUser.password ||
    !registerUser.confirmPassword
  ) {
    snackbar_info.value = '所有欄位都需要填!';
    snackbar_color.value = 'yellow lighten-5';
    snackbar.value = true;
    return;
  }

  if (registerUser.password !== registerUser.confirmPassword) {
    snackbar_info.value = '密碼與確認密碼不相符合!';
    snackbar_color.value = 'yellow lighten-5';
    snackbar.value = true;
    return;
  }

  const payload = {
    emp_id: registerUser.empID,
    emp_name: registerUser.name,
    dep_name: registerUser.dep,
    password: registerUser.password,
  };
  axios.post('/register', payload)
    .then(res => {
      if (res.data.status) {

        resetRegisterForm();
        toggleSignUp();

      }
    })
    .catch(err => {
      console.error(err);
      snackbar_info.value = '錯誤! API連線問題...';
      snackbar.value = true;
    });
};

const resetRegisterForm = () => {
  registerUser.empID = '';
  registerUser.name = '';
  registerUser.dep = '';
  registerUser.password = '';
  registerUser.confirmPassword = '';
};

const menu_1 = () => {
  router.push('/home');
}

const menu_2 = () => {
  router.push('/about');
}

const userLogin = () => {
  console.log("userLogin()...");

  const payload = {
    empID: loginUser.loginEmpID,
    password: loginUser.loginPassword,
  };

  //get_table_is_ok.value = false;

  const path = '/login';
  axios.post(path, payload)
    .then(res => {
      if (res.data.status) {
        //user_data = res.data.user;
        console.log("login user:",res.data.user);
        signInUser(res.data.user);
        //get_table_is_ok.value = true;
      } else {
        snackbar_info.value = res.data.message;
        snackbar.value = true;
      }
    })
    .catch(err => {
      console.error(err);
      snackbar_info.value = '錯誤! API連線問題...';
      snackbar.value = true;
    });
};

const signInUser = (user) => {
  console.log("signInUser(),", user);
  //router.push('/home');
  /*
  if (link1.isEnabled && link2.isEnabled) {
    router.push(link1.to);
  } else if (link1.isEnabled) {
    router.push(link1.to);
  } else if (link2.isEnabled) {
    router.push(link2.to);
  }
  */
  emit('setLinks', { link1, link2 }); // 使用 emit 發送資料

  removeLoginUser();

  localStorage.setItem('loginedUser', JSON.stringify(user));  //使用者登入資料
  //let isAuthenticated = 'true'; // 確保初始值為字串 'true'
  //localStorage.setItem('Authenticated', isAuthenticated);

  authModule.isAuthenticated = true; // 登入成功, 更新驗證狀態為 true

  // 發布登入成功事件
  eventBus.emit('userLoggedIn', authModule.isAuthenticated);
  // route to component
  let router_name = (user.setting_lastRoutingName=='') ? 'Main': user.setting_lastRoutingName;
  console.log("router_name:", router_name);
  router.push({ name: router_name });
  //const currentState = history.state;
  //router.push({ name: router_name }).then(() => {
  //  // 保留現有的歷史狀態
  //  history.replaceState(currentState, '', router.resolve({ name: router_name }).href);
  //}).catch(err => {
  //  if (err.name !== 'NavigationDuplicated') {
  //    throw err;
  //  }
  //});
};

const removeLoginUser = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
};

//const rules = {
//  required: value => !!value || 'Required.',
//};

const checkEmpty = (field) => {
  console.log("checkEmpty(),", field, loginUser[field]);

  if (loginUser.loginEmpID !== '' && loginUser.loginPassword !== '')
    openMenu.value=true;
  else
    openMenu.value=false;
};

const requiredRule = value => !!value || '欄位必須輸入資料...';
const empIDRule = value => /^[0-9]{4,5}$/.test(value) || '工號必須是4或5位數字!';  // ^ 和 $ 分別表示字符串的開始和結束, [0-9] 表示數字, {4,5} 4到5位數

const nameRule = value => value.length <= 10 || '資料長度太長!';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';
const confirmPasswordRule = value => value === registerUser.password || '密碼不相同!';

//onMounted(initialize);
</script>

<style lang="scss" scoped>
@import url(
  'https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);
@import "../styles/variables.scss";

.container {
  position: relative;
  width: 768px;
  height: 480px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2), 0 10px 10px rgba(0, 0, 0, 0.2); //區塊陰影
  background: linear-gradient(to left, $SYSTEM_BACKGROUND_COLOR, #f2f2f2);                     //漸層顏色
  margin-top: 10vh;
}

.overlay-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  padding: 20px;
  background: none;
}

.sign-in, .sign-up {
  position: absolute;
  top: 0;
  left: -60px;
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  //background: rgba(255, 255, 255, 0.8);
  background: transparent;
  transition: transform 0.5s ease-in-out;
  z-index: 2;
  border: none;
  box-shadow: none;
}
.sign-in {
  z-index: 2;
}
.sign-up {
  z-index: 1;
}

.floating-menu-wrapper {
  position: relative;
    right: -180px;
    top: -274px;
}
.floating-menu-button {
  width: 100px;
}
.floating-menu {
  background: #f9f9f9;
  padding: 5px;
  width: 130px;
  z-index: 100;
  position: fixed;
  top: 0px;
  right: -12px;
  border-radius: 5px;
}
.floating-menu .floating-menu-link {
  font-size: 0.9em;
  margin: 0 0.5em;
  transition: color 0.3s, background-color 0.3s;
  padding-top: 10px;
  padding-bottom: 10px;
  height: 40px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  white-space: nowrap;
  overflow: hidden;
  text-decoration: none;
  //color: inherit;
  font-weight: bolder;
}
.floating-menu .floating-menu-link:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #01d1b7;
}

/*
.disabled-link {
  color: rgba(0, 0, 0, 0.2);  // 灰色並且透明度淡
  pointer-events: none;           // 禁用點擊事件
  cursor: not-allowed;            // 禁用指針顯示
  //font-weight: 400;
}
*/

/*
h3 {
  margin: 0;
  font-family: "Noto Sans TC", "Microsoft Yahei", "微軟雅黑", sans-serif;
}

button {
  border-radius: 20px;
  border: 1px solid #009345;
  background-color: #009345;
  color: #fff;
  font-size: 1rem;
  font-weight: bold;
  padding: 10px 40px;
  margin-top: 10px;
  letter-spacing: 1px;
  text-transform: uppercase;
  cursor: pointer;
  transition: transform 0.1s ease-in;

  &:active {
    transform: scale(0.9);
  }

  &:focus {
    outline: none;
  }
}
*/
.v-text-field,
.v-select {
  min-width: 17vw;
}

.block_ticker {
  font-size: 14px;
  border-block: 1px solid red;
  padding-block: 8px;
  display: flex;
  gap: 2rem
}

.block_ticker ul {
  list-style: none;
  font-size: 12px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap:2rem;
}

.mark_texts {
  margin-top: -10px;
  margin-bottom: 1rem;
  font-size: 12px;
  color:#36558b;
}

.lg_mark_texts {
  margin-top: 10px;
  margin-bottom: 1rem;
  font-size: 12px;
  color:#36558b;
}

.mark_texts > a {
  margin-top: 1rem;
}

.lg_mark_texts > a {
  margin-top: 1rem;
}

.logo_img {
  position: absolute;
  right: 0px;
  top: 60px;
  width: 75%;
  height: auto;
  object-fit: cover;
  object-position: center;
}

.logo_text, .logo_designer_text {
  position: absolute;   // 以 absolute 更精確地控制位置
  bottom: -18px;        // 顯示在容器底部
  font-size: 12px;
  font-weight: 700;
  opacity: 0.5;
  color: #000;
  //background: rgba(255, 255, 255, 0.7);   // 添加背景以便更清晰地看到文字
  padding: 5px;
}
.logo_text {
  left: 400px;       // 顯示在容器左邊
}
.logo_designer_text {
  left: 560px;      // 顯示在容器左邊
}

.logo_designer_img {
  position: absolute;   // 以 absolute 更精確地控制位置
  bottom: 2px;          // 顯示在容器底部
  left: 610px;
  max-width: 120px;     // 根據需要調整
  height: auto;
}

//.logo_text {
  //position: relative;
  //top: 250px;
  //font-size: 12px;
  //right: 60px;
  //border: 1px solid red;
  //max-width: 100%;
  //overflow: visible;
//}

//.logo_designer_text {
  //position: relative;
  //top: 250px;
  //font-size: 12px;
  //right: 0px;
  //color: blue;
  //font-weight: 700;
  //opacity: 0.5;
  //border: 1px solid green;
  //max-width: 100%;
  //overflow: visible;
//}

@keyframes blinker {
  50% {
    opacity: 0;
  }
}

.btns {
  width: auto;
  height: 3.077rem;
  font-size: 1.154rem;
  color: #FFF;
  font-weight: bold;
  text-align: center;
  background-color: #8BB5D6;
  border-radius: 0.615rem;
  border: none;
  //margin-top: 1.538rem;
  margin-top: 10px !important;
  padding: 0rem 1.538rem;
  transition: border 0.05s ease;
}

.btns:hover {
  border: 1.5px solid white;
}

button#login {
  width: 80px;
}

button#register {
  width: 90px;
}

:deep(.v-input--density-default .v-field--variant-filled) {
  --v-input-control-height: 20px;
  --v-field-padding-top: 0px;
  --v-field-padding-bottom: 0px;
}

:deep(.v-messages__message) {
  color:#36558b !important;
}

/* turn off min-width for all buttons */
:deep(.v-btn) {
  min-width: 0;
}

:deep(span.v-btn__content) {
  font-size: 14px;
}

//.password-field .v-input__details {
:deep(.v-input__details) {
  position: relative;
  right: 25px !important;
  width: 270px !important;
}

.slide-in-left-enter-active,
.slide-in-left-leave-active {
  transition: all 0.5s ease;
}

.slide-in-left-enter,
.slide-in-left-leave-to {
  transform: translateX(100%);
}

.slide-in-right-enter-active,
.slide-in-right-leave-active {
  transition: all 0.5s ease;
}

.slide-in-right-enter,
.slide-in-right-leave-to {
  transform: translateX(-100%);
}
</style>
