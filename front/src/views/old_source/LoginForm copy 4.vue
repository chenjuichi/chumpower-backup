<template>

  <div class="container" :class="{ 'sign-up-active': signUp }">
    <div class="overlay-container">
      <div class="overlay">
        <div class="overlay-content">
          <canvas id="canvas" class="logo_img" />
        </div>
      </div>
    </div>

    <div class="sign-in">
      <h3>登入</h3>
      <v-form @submit.prevent="userLogin">
        <v-text-field
          label="員工編號"
          prepend-icon="mdi-account"
          v-model="loginEmpID"
          :rules="[rules.required]"
        />
        <v-text-field
          label="密碼"
          prepend-icon="mdi-lock"
          :append-icon="eyeShow ? 'mdi-eye-off' : 'mdi-eye'"
          :type="eyeShow ? 'password' : 'text'"
          @click:append="eyeShow = !eyeShow"
          v-model="loginPassword"
          :rules="[rules.required]"
          @keyup.enter="userLogin"
        />
        <v-btn type="submit" color="primary" class="btns">登入</v-btn>
      </v-form>
      <!--<button class="switch-btn" @click="toggleSignUp">註冊s</button>-->
      <p style="color:#36558b">加入會員 <a href="#" @click.prevent="toggleSignUp">註冊</a></p>

    </div>

    <div class="sign-up">
      <h3>註冊</h3>
      <v-form @submit.prevent="register">
        <v-text-field
          label="工號"
          prepend-icon="mdi-account"
          v-model="registerUser.empID"
          :rules="[rules.required, empIDRule]"
          required

        />
        <v-text-field
          label="姓名"
          prepend-icon="mdi-account-edit"
          v-model="registerUser.name"
          :rules="[rules.required, nameRule]"
          required

        />
        <v-select
          :items="departments"
          label="部門"
          prepend-icon="mdi-account-group"
          v-model="registerUser.dep"
          :rules="[rules.required]"
          required

        />
        <v-text-field
          label="密碼"
          prepend-icon="mdi-lock"
          :append-icon="eyeShow1 ? 'mdi-eye-off' : 'mdi-eye'"
          :type="eyeShow1 ? 'password' : 'text'"
          @click:append="eyeShow1 = !eyeShow1"
          v-model="registerUser.password"
          :rules="[rules.required, passwordRule]"
          required

        />
        <v-text-field
          label="確認密碼"
          prepend-icon="mdi-account-check"
          :type="eyeShow1 ? 'password' : 'text'"
          v-model="registerUser.confirmPassword"
          :rules="[rules.required, confirmPasswordRule]"
          required

        />
        <v-btn type="submit" color="primary" class="btns">註冊</v-btn>
      </v-form>
      <p style="color:#36558b">會員登入 <a href="#" @click.prevent="toggleSignUp">登入</a></p>

    </div>
  </div>
  <img id="sourceImage" :src="imageSrc" alt="Logo"style="display: none;">

</template>

<script setup>
import { ref, defineComponent, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { myMixin } from '../../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'LoginForm'
});

// === mix ==
const { initAxios } = myMixin();

const imageSrc = ref(require('../assets/pet4-rb.png'))

const signUp = ref(false);
const loginEmpID = ref('');
const loginPassword = ref('');
const registerUser = ref({
  empID: '',
  name: '',
  dep: '',
  password: '',
  confirmPassword: '',
});
const departments = ref([]);
const eyeShow = ref(true);
const eyeShow1 = ref(true);
const tosterTitle = ref('Hello');
const tosterType = ref('error');
const tosterBody = ref('資料錯誤或空白, 請重新輸入...');
const tosterTimeout = ref(3);
const tosterOK = ref(false);
const tosterRegOK = ref(false);

let myIdField = null;

//=== mounted ===
onMounted(() => {
  replaceImageColor();

  myIdField = document.getElementById("loginEmpID");
  if (myIdField) {
    myIdField.addEventListener('keydown', handleKeydown);
  }
});

//=== unmounted ===
onUnmounted(() => {
  if (myIdField) {
    myIdField.removeEventListener('keydown', handleKeydown);
  }
});

const handleKeydown = (event) => {
  var caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when you press the keyboard CapsLock key
};

const toggleSignUp = () => {
  console.log("toggleSignUp()")

  signUp.value = !signUp.value;
};

const initialize = () => {
  axios.get('/listDepartments')
    .then(res => {
      departments.value = res.data.outputs.map(item => Object.values(item)[0]);
    })
    .catch(error => {
      console.error(error);
    });
};

const replaceImageColor = () => {
  console.log("replaceImageColor()...");

  const sourceImage = document.getElementById('sourceImage');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');

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
  const payload = {
    emp_id: registerUser.empID,
    emp_name: registerUser.name,
    password: registerUser.password,
    dep: registerUser.dep,
  };
  axios.post('/register', payload)
    .then(res => {
      if (res.data.status) {
        tosterRegOK.value = false;
        resetRegisterForm();
        toggleSignUp();
      } else {
        tosterRegOK.value = true;
      }
    })
    .catch(err => {
      console.error(err);
    });
};

const resetRegisterForm = () => {
  registerUser.empID = '';
  registerUser.name = '';
  registerUser.dep = '';
  registerUser.password = '';
  registerUser.confirmPassword = '';
};

const userLogin = () => {
  const payload = {
    empID: loginEmpID.value,
    password: loginPassword.value,
  };
  axios.post('/login', payload)
    .then(res => {
      if (res.data.status) {
        tosterOK.value = false;
        signInUser(res.data.user);
      } else {
        tosterOK.value = true;
      }
    })
    .catch(err => {
      console.error(err);
    });
};

const signInUser = (user) => {
  router.push('/navbar');
  localStorage.setItem('loginedUser', JSON.stringify(user));
  localStorage.setItem('Authenticated', true);
};

const rules = {
  required: value => !!value || 'Required.',
};

const empIDRule = value => /[0-9]{4}$/.test(value) || '員工編號資料格式錯誤!';
const nameRule = value => value.length <= 10 || '資料格式錯誤或資料長度太長!';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{8,12}$/.test(value) || '資料格式或資料長度錯誤!';
const confirmPasswordRule = value => value === registerUser.password || '密碼不相同!';

onMounted(initialize);
</script>

<style lang="scss" scoped>
@import url(
  'https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);

.page {
  display: flex;
  justify-content: center;
  align-items: center;
}

.container {
  position: relative;
  width: 768px;
  height: 480px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2), 0 10px 10px rgba(0, 0, 0, 0.2);
  background: linear-gradient(to bottom, #efefef, #ccc);
  margin-top: 10vh;

  .overlay-container {
    position: absolute;
    top: 0;
    right: 0;
    width: 50%;
    height: 100%;
    overflow: hidden;
    //background: linear-gradient(to bottom right, #7fd625, #009345);
    background: linear-gradient(90deg, #54880e, #f2f2f2);

    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    padding: 20px;
  }

  .logo_img {
    position: relative;
    right: -170px;
    bottom: -150px;
    width: 110%;

    height: auto;
    transform: translate(-50%, -50%);
    object-fit: cover;
    object-position: center;
  }

  .overlay-content {
    text-align: center;

    .logo {
      height: 4vw;
      margin-bottom: 10px;
    }

    h2 {
      margin: 0;
      font-family: "Noto Sans TC", "Microsoft Yahei", "微軟雅黑", sans-serif;
    }
  }
}

.sign-in, .sign-up {
  position: absolute;
  top: 0;
  left: 0;
  width: 50%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(to bottom, #efefef, #ccc);
  transition: transform 0.5s ease-in-out;
}

.sign-in {
  z-index: 2;
}

.sign-up {
  transform: translateX(-100%);
  z-index: 1;
}

.sign-up-active .sign-in {
  transform: translateX(100%);
}

.sign-up-active .sign-up {
  transform: translateX(0);
  z-index: 2;
}

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

.switch-btn {
  background-color: transparent;
  border-color: #009345;
  color: #009345;
  margin-top: 20px;
}

.v-text-field, .v-select {
  min-width: 17vw;
}

.v-messages__message {
  color: #FF5c4E;
  font-size: 12px;
}

small.msgErr {
  font-size: 80%;
  color: red;
  margin-top: -20px;
}

small.clickLgnErr {
  font-size: 100%;
  color: red;
  margin-top: -60px;
  animation: blinker 0.5s linear infinite;
}

small.clickRegErr {
  font-size: 100%;
  color: red;
  margin-top: -40px;
  animation: blinker 0.5s linear infinite;
}

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
    background-color: #445f8c;
    border-radius: 0.615rem;
    -webkit-border-radius: 0.615rem;
    -moz-border-radius: 0.615rem;
    -ms-border-radius: 0.615rem;
    -o-border-radius: 0.615rem;
    border: 0rem;
    margin-top: 1.538rem;
    padding: 0rem 1.538rem;

}

:deep(.v-input--density-default .v-field--variant-filled) {
  --v-input-control-height: 20px;
  --v-field-padding-top: 0px;
  --v-field-padding-bottom: 0px;
}
</style>
