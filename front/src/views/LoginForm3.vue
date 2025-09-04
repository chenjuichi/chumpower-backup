<template>
<div class="background-container" >
  <div class="container">
    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn color="#adadad" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <div class="overlay-container">
      <!--企業視覺圖像-->
      <p class="logo_text">{{ company_name }}</p>
      <img :src="pmcLogoSrc" alt="PMC Logo" class="logo_designer_img" />
    </div>

    <!--登入-->
      <div v-if="!signUp" class="sign-in">
        <div @submit.prevent="userLogin" style="position: relative; top: -20px;">
          <v-text-field
            label="工號"
            @update:focused ="setupListUsers"
            prepend-icon="mdi-account"
            v-model="loginUser.loginEmpID"
            :rules="[requiredRule, empIDRule]"
            ref="loginEmpIDInput"
            @keypress="handleKeyDown"
            @keydown.enter="focusPasswordInput"
            @keydown.tab.prevent="focusPasswordInput"
            id="loginEmpID"
            style="width:15rem; min-width:15rem; position:relative; left:0em;"
          />

          <v-text-field
            label="姓名"
            readonly
            prepend-icon="mdi-account-edit"
            v-model="loginUser.loginName"
            style="width:15rem; min-width:15rem; position:relative; left:0em;"
          />

          <v-text-field
            label="密碼"
            prepend-icon="mdi-lock"
            :append-icon="eyeShow ? 'mdi-eye-off' : 'mdi-eye'"
            :type="eyeShow ? 'password' : 'text'"
            @click:append="eyeShow = !eyeShow"
            v-model="loginUser.loginPassword"
            :rules="[requiredRule, passwordRule]"
            @keydown="handleCapsLock"
            @keydown.enter="userLogin"
            @keydown.tab.prevent="handlePasswordTab"
            ref="passwordInput"
            class="password-field"
            style="width:15rem; min-width:15rem; position:relative; left:0em; transition:none;"
          />

          <v-btn ref="loginButton" type="submit" color="primary" class="btns" id="login" @click="userLogin">
            <i class="fa-solid fa-right-to-bracket fa-fade" style="color: #63E6BE;"></i>
            登入
          </v-btn>

          <v-icon
            dark
            :style="{
              position: 'relative',
              top: '5px',
              left: '20px',
              opacity: caps ? 1 : 0,
              transition: 'opacity 0.5s ease',
            }"
          >
            mdi-caps-lock
          </v-icon>
        </div>
        <span style="position:relative; top:150px; font-weight:300; font-size: 12px;">
          {{ 'Build 2025-09-03' }}
        </span>
      </div>
  </div>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, watch, onBeforeMount, onMounted, onUnmounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';

import { routerLinks } from '../router/index.js';
import { myMixin } from '../mixins/common.js';

import { useClientIdentifier } from '../mixins/useClientIdentifier.js';

import { useSocketio } from '../mixins/SocketioService.js';
import { socket_server_ip }  from '../mixins/crud.js';

import { empPermMapping, roleMappings, flatItems } from '../mixins/MenuConstants.js';

import eventBus from '../mixins/enentBus.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

//import { departments }  from '../mixins/crud.js';
import { loginUser, loginEmpIDInput }  from '../mixins/crud.js';
import { temp_desserts2 }  from '../mixins/crud.js';

import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listUsers2 = apiOperation('get', '/listUsers2');
const register = apiOperation('post', '/register');
const login = apiOperation('post', '/login');
const reLogin = apiOperation('post', '/reLogin');

//=== component name ==
defineComponent({ name: 'LoginForm3' });

// === mix ==
const { initAxios } = myMixin();

//=== data ===
const imageSrc = ref(require('../assets/20250708-chumpower-login.png')); //企業視覺圖像

const company_name = ref('銓寶工業股份有限公司')
//const designer_name = ref('財團法人精密機械研究發展中心設計')
const pmcLogoSrc = ref(require('../assets/pmc_logo.png')); // PMC logo 圖像

const isRegisterUserFocused = ref(false);
const isLoginUserFocused = ref(false);

const signUp = ref(false);
const foundDessert = ref(null);
const eyeShow = ref(true);
const eyeShow1 = ref(true);
const popStateHandler = ref(null);

const caps =ref(false);

const initialSelection = Array(26).fill(0).map((_, i) => (roleMappings['員工'].includes(i + 1) ? 1 : 0));

const registerUser = reactive({
  empID: '',
  name: '',
  dep: '',
  password: '',
  confirmPassword: '',
});
const reactiveLinks = reactive(flatItems.value);

const emit = defineEmits(['setLinks']);

const registerEmpIDInput = ref(null);

const passwordInput = ref(null);
const loginButton = ref(null);
const registerButton = ref(null);
const registerPasswordInput = ref(null);

let myIdField = null;
let loginEmpID_max_length = 8;

const router = useRouter();

const showBackWarning = ref(true);

const isOnline = ref(navigator.onLine);

const screenSizeInInches = ref(null);

// 初始化Socket連接
const userId = 'user_chumpower';
const clientAppName = 'LoginForm3';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);

const { localIP, userAgent, uuid } = useClientIdentifier()

const backgroundStyle = ref({
  backgroundImage: `url('../assets/20250708-chumpower-login.png')`,
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'center',
  backgroundSize: `${window.innerWidth}px ${window.innerHeight}px`,
  width: '100vw',
  height: '100vh',
});

//=== mounted ===
onMounted(async () => {
  console.log("LoginForm, onMounted()...")

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);
  //+++

  // 禁用 BackButton 功能
  //disableBackButton();
  // 阻止直接後退
  window.history.pushState(null, null, document.URL); //呼叫到瀏覽器原生的 history 物件
  //history.pushState(null, null, document.URL)
  window.addEventListener('popstate', handlePopState)

  document.addEventListener('keydown', allowBackspaceInInputs);

  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);

  window.addEventListener('resize', updateBackgroundSize);

  myIdField = document.getElementById("loginEmpID");
  //if (myIdField) {
  //  myIdField.addEventListener('keydown', handleKeyDown);
  //}
  myIdField && (myIdField.addEventListener('keydown', handleKeyDown));

  loginEmpIDInput.value.focus();   // 元件掛載時聚焦在工號欄位

  console.log("routerLinks:",routerLinks);
  //在組件掛載後, 執行一次聚焦
  if (loginEmpIDInput.value) {
    loginEmpIDInput.value.focus()
  }

  //處理socket連線
  console.log('等待socket連線...');

  try {
    await setupSocketConnection();
    console.log('Socket連線ok...');
  } catch (error) {
    console.error('Socket連線失敗:', error);
  }
});

//=== unmounted ===
// 在組件卸載時移除事件監聽器
onUnmounted(() => {
  document.removeEventListener('keydown', allowBackspaceInInputs);

  window.removeEventListener('popstate', handlePopState);

  window.removeEventListener('online', updateOnlineStatus);
  window.removeEventListener('offline', updateOnlineStatus);

  window.removeEventListener('resize', updateBackgroundSize);
});

//=== destroyed ===
onBeforeUnmount(() => {
  console.log("LoginForm, destroyed()...")

  // 恢復 BackButton 功能
  if (popStateHandler.value) {
    enableBackButton();
    document.removeEventListener('keydown', allowBackspaceInInputs);

    //window.removeEventListener('popstate', popStateHandler.value);
    popStateHandler.value = null;
  }

  //
  //if (myIdField) {
  //  myIdField.removeEventListener('keydown', handleKeyDown);
  //}
  myIdField && (myIdField.removeEventListener('keydown', handleKeyDown));
});

//=== watch ===
//setupListUsersWatcher();

// 監視 loginEmpID
watch(() => loginUser.loginEmpID,
  (newVal) => {
    if (newVal === '') {
      loginUser.loginName = ''
    }
  }
)

//=== computed ===

//=== mounted ===

//=== unmounted ===

//=== created ===
onBeforeMount(() => {
  console.log("LoginForm, created()...")

  initAxios();
  initialize();
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

    // 使用 async/await 等待 API 請求完成，確保順序正確
    //await listMarquees();      // 最後加載廣告牌資料
    //await listDepartments();   // 再加載部門資料

    await listUsers2();         // 先加載使用者資料
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const updateBackgroundSize = () => {
  backgroundStyle.value.backgroundSize = `${window.innerWidth}px ${window.innerHeight}px`;
};

const handlePopState = () => {
  // ✅ 正確方式：保留 Vue Router 的 state
  //history.pushState(history.state, '', document.URL)
  window.history.pushState(history.state, '', document.URL)

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
};

const updateOnlineStatus = () => {
  isOnline.value = navigator.onLine
  if (!isOnline.value) {
    showSnackbar('⚠️ 網路連線中斷，請檢查您的網路狀態', 'yellow lighten-5');

  } else {
    console.log('✅ 網路恢復正常')
  }
}

const setupListUsers = (focused) => {
  if (!focused) { // 當失去焦點時
    console.log("setupListUsers()...");

    isLoginUserFocused.value=false;

    //if (loginUser.loginEmpID.length == 7) {   // 在工號為7位數時, 則前方自動補0成為8位數
    loginUser.loginEmpID = loginUser.loginEmpID.trim();
    if (loginUser.loginEmpID.length < 8 && loginUser.loginEmpID.length != 0) {   // 在工號為7位數時, 則前方自動補0成為8位數
        loginUser.loginEmpID = loginUser.loginEmpID.padStart(8, '0');
    }

    foundDessert.value = temp_desserts2.value.find(dessert => dessert.emp_id === loginUser.loginEmpID);
    //console.log("foundDessert:",foundDessert.value);
    if (foundDessert.value) {
      loginUser.loginName = foundDessert.value.emp_name;
    } else {
        //console.log("step, not found...", loginUser.loginEmpID);
      if (loginUser.loginEmpID !== '') {
        let temp_info = snackbar_info.value = '錯誤, 找不到工號' + loginUser.loginEmpID + '!';
        showSnackbar(temp_info, 'red accent-2');

        loginUser.loginEmpID = '';
      }
      loginEmpIDInput.value.focus();
    }
  } else {
    isLoginUserFocused.value = true;
  }
};

const checkUsers = (focused) => {
  if (!focused) { // 當失去焦點時
    console.log("checkUser()...");

    isRegisterUserFocused.value=false;
    foundDessert.value = temp_desserts2.value.find(dessert => dessert.emp_id === registerUser.empID);
    console.log("foundDessert:",foundDessert.value);
    if (foundDessert.value) {
      console.log("step, found...", registerUser.empID);
      if (registerUser.empID !='') {
        let temp_info = snackbar_info.value = '錯誤, 工號' + registerUser.empID + '重複!';
        showSnackbar(temp_info, 'red accent-2');

        registerUser.empID = '';
      }
      registerEmpIDInput.value.focus();
    }
  } else {
    isRegisterUserFocused.value=true;
  }
};

const focusPasswordInput = (event) => {
  event.preventDefault();
  passwordInput.value.focus();
};

const focusRegisterPassword = (focused) => {
  //if (!focused) { // 當失去焦點時
  //  registerPasswordInput.value.focus();
  //}
  !focused && (registerPasswordInput.value.focus());  // 當失去焦點時
};

const handleMenuUpdate = (menuState) => {
  console.log('handleMenuUpdate(),', menuState);
  //if (!menuState) { // 當菜單關閉，focus到密碼欄位
  //  focusRegisterPassword();
  //}
  !menuState && (focusRegisterPassword());  //當菜單關閉，focus到密碼欄位
};

const handleModelValueUpdate = (newValue) => {
  console.log('handleModelValueUpdate(),', newValue);

  registerUser.dep = newValue;
};

const handlePasswordConfirmTab = (event) => {
  event.preventDefault();
  //if (event.shiftKey) {
  //  registerEmpIDInput.value.focus();
  //} else {
  //  registerButton.value.$el.focus();
  //}
  event.shiftKey ? registerEmpIDInput.value.focus() : registerButton.value.$el.focus();
};

const handlePasswordTab = (event) => {
  event.preventDefault();
  //if (event.shiftKey) {
  //  loginEmpIDInput.value.focus();
  //} else {
  //  loginButton.value.$el.focus();
  //}
  event.shiftKey ? loginEmpIDInput.value.focus() : loginButton.value.$el.focus();
};


const handleCapsLock = (event) => {
  caps.value = event.getModifierState && event.getModifierState('CapsLock');
  //console.log("CapsLock is: ", caps.value);
};

const handleKeyDown = (event) => {
  //console.log("handleKeyDown()...", event.getModifierState('CapsLock'))
  const inputChar = event.key;

  caps.value = event.getModifierState && event.getModifierState('CapsLock');
  //const caps = event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps.value); // true when you press the keyboard CapsLock key

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

const togglePanel = () => {
  console.log("togglePanel()")

  isRegisterUserFocused.value=false;
  isLoginUserFocused.value=false;

  signUp.value = !signUp.value;
};

const userLogin = async () => {
  console.log("userLogin()...");

  let payload = {
    empID: loginUser.loginEmpID,
    password: loginUser.loginPassword,

    local_ip: localIP.value,     // ✅ 傳入後端
    user_agent: userAgent.value, // ✅ 若需後端記錄
    device_id: uuid.value        // ✅ 可作裝置識別
  };

  const data = await reLogin(payload);
  console.log("data:",data);
  //data.status ? signInUser(data.user) : showSnackbar(data.message, 'red accent-2');
  if (data.status === true) {
    if (data.forceLogoutRequired) {
      socket.value.emit('triggerLogout', { empID: data.user.empID });
      console.log("送出 triggerLogout 強迫登出訊息...", data.user.empID);
    }

    signInUser(data.user)
    console.log("登入成功...", data.user.empID);
  } else {
    console.log("帳號不存在、密碼錯誤...");
    showSnackbar(data.message, 'red accent-2')
  }
};

const signInUser = (user) => {
  console.log("signInUser(),", user);
  //待確認0519
  //let router_name = (user.setting_lastRoutingName == '') ? 'Main': user.setting_lastRoutingName;
  let router_name = 'Main';
  console.log("router_name:", router_name);
  let default_routingPriv = initialSelection.join(',');
  let routingPriv_string = (user.setting_routingPriv == '') ? default_routingPriv : user.setting_routingPriv;
  //let routingPriv_array = routingPriv_string.split(',').map(Number);
  let routingPriv_array = routingPriv_string.split(',').map(value => value === '1');
  console.log("routingPriv_array:", routingPriv_array);

  // 使用 routingPriv_array 的值更新 reactiveLinks 中每個物件的 isEnabled 屬性
  reactiveLinks.forEach((link, index) => {
    if (index < routingPriv_array.length) {
      link.isEnabled = routingPriv_array[index];
    }
  });

  eventBus.emit('setLinks', reactiveLinks);
  removelocalStorage();         //清除 localStorage內的值

  Object.assign(loginUser, {    //清除 登入資料
    loginEmpID: '',
    loginName: '',
    loginPassword: ''
  });

  localStorage.setItem('loginedUser', JSON.stringify(user));  //重新設定使用者登入資料於localStorage
  sessionStorage.setItem('auth_user', JSON.stringify(user));
  let isAuthenticated = 'true'; // 確保初始值為字串 'true'
  localStorage.setItem('Authenticated', isAuthenticated);

  //router.replace({ name: router_name });  //啟動router
  const resolvedRoute = router.resolve({ name: router_name });
  const path = resolvedRoute.href;    // 取得解析後的 path
  router.replace({ path });           // 使用 path 來進行導航
};

const removelocalStorage = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
  if (localStorage.getItem('selectedItems')) {
    localStorage.removeItem('selectedItems');
  }
};
/*
const validateFields = () => {
  if (['empID', 'name', 'dep', 'password', 'confirmPassword'].some(field => !registerUser[field])) {
    showSnackbar('所有欄位都需要填!', 'yellow lighten-5');
    return;
  }

  if (registerUser.password !== registerUser.confirmPassword) {
    showSnackbar('密碼與確認密碼不相符合!', 'yellow lighten-5');
    return;
  }
};
*/
const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const requiredRule = value => !!value || '必須輸入資料...';
const empIDRule = value => /^[0-9]{7,8}$/.test(value) || '必須是7或8位數字!';  // ^ 和 $ 分別表示字符串的開始和結束, [0-9] 表示數字, {4,5} 4到5位數
//const nameRule = value => value.length <= 10 || '資料長度太長!';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';
//const confirmPasswordRule = value => value === registerUser.password || '密碼不相同!';

const reverseEmpPermMapping = Object.fromEntries(
  Object.entries(empPermMapping).map(([key, value]) => [value, key])
);

//const getEmpPermKey = (permText) => {
//  return reverseEmpPermMapping[permText] || '未知';
//};

//const disableBackButton = () => {
//  window.history.pushState(null, '', window.location.href);
//
//  popStateHandler.value = (event) => {
//    window.history.pushState(null, '', window.location.href);
//  };
//
//  window.addEventListener('popstate', popStateHandler.value);
//};

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

/*
const getLocalIP = () => {
  return new Promise((resolve, reject) => {
    const pc = new RTCPeerConnection({
      iceServers: []
    });

    pc.createDataChannel('');

    pc.createOffer()
      .then(offer => pc.setLocalDescription(offer))
      .catch(reject);

    pc.onicecandidate = (event) => {
      if (!event || !event.candidate) return;

      const candidate = event.candidate.candidate;
      const ipRegex = /([0-9]{1,3}(\.[0-9]{1,3}){3})/;
      const ipMatch = candidate.match(ipRegex);
      if (ipMatch) {
        resolve(ipMatch[1]); // 回傳第一個符合的 IP
        pc.close();
      }
    };
  });
};
*/
</script>

<style lang="scss" scoped>
@import url(
  'https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);
@import "../styles/variables.scss";

html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  height: 100%;
}

.container {
  //z-index: 3;         // 確保內容在背景上方
  //max-width: 100%;
  //max-height: 100%;
  //overflow: hidden;
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;   // 防止內容溢出
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

.sign-in {
  position: absolute;
  top: 0;
  left: 20px;
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

.v-text-field, .v-select {
  min-width: 17vw;
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
  font-weight: 800;
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

:deep(.v-btn) {
  min-width: 0;
}

:deep(span.v-btn__content) {
  font-size: 14px;
}

:deep(.v-input__details) {
  position: relative;
  right: 25px !important;
  width: 270px !important;
}
/*
.background-container {
  width: 100vw;
  height: 100vh;
  background-image: url('../assets/20250708-chumpower-login.png');
  background-size: cover;                         // 讓背景覆蓋整個視窗
  //background-position: center + 150px;
  background-position: center calc(50% - 40px);
  background-repeat: no-repeat;                   // 不重複圖片
  overflow: hidden;                               // 防止滾動
  display: flex;
  align-items: center;
  justify-content: center;
}
*/

.background-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-image: url('../assets/20250708-chumpower-login-3.png');
  background-position: center;
  //background-position: center calc(50% - 30px);
  background-repeat: no-repeat;
  background-attachment: fixed;
  //background-size: cover;
  background-size:auto 100%;    // height covering the whole page height
  overflow: hidden;
}
</style>
