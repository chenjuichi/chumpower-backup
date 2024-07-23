<template>
  <div class="container" :class="{ 'sign-up-active': signUp }">
  <div class="overlay-container">
      <div class="overlay">
      <div class="overlay-left">
          <h2>
          <img :src="homeUrl" alt="Logo" style="height: 4vw; margin-bottom: 10px;">

          冷藏藥倉系統
          </h2>
          <button class="invert" id="signIn" @click="toggleSignUp">登入</button>
      </div>
      <div class="overlay-right">
          <h2>
          <img :src="homeUrl" alt="Logo" style="height: 4vw; margin-bottom: 10px;">
          冷藏藥倉系統
          </h2>
          <button class="invert" id="signUp" @click="toggleSignUp">註冊</button>
      </div>
      </div>
  </div>

  <div class="sign-up">
      <h3>註冊</h3>
      <v-form @submit.prevent="register">
      <v-text-field
          label="員工編號"
          prepend-icon="mdi-account"
          v-model="registerUser.empID"
          :rules="[rules.required, empIDRule]"
          required
      />
      <v-text-field
          label="員工姓名"
          prepend-icon="mdi-account-edit"
          v-model="registerUser.name"
          :rules="[rules.required, nameRule]"
          required
      />
      <v-select
          :items="departments"
          label="組別"
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
      <v-btn type="submit" color="primary">註冊</v-btn>
      </v-form>

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
      <v-btn type="submit" color="primary">登入</v-btn>
      </v-form>

      <p>Build 2024-03-27</p>
  </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineComponent } from 'vue';
import axios from 'axios';
import { myMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'LoginForm'
});

// === mix ==
const { initAxios } = myMixin();

const homeUrl = ref(require('../assets/china_header.png'))

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

const toggleSignUp = () => {
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

//#app {
//  background: #092525;
//}

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
    left: 50%;
    width: 50%;
    height: 100%;
    overflow: hidden;
    transition: transform 0.5s ease-in-out;
    z-index: 100;
  }

  .overlay {
    position: relative;
    left: -100%;
    height: 100%;
    width: 200%;
    background: linear-gradient(to bottom right, #7fd625, #009345);
    color: #fff;
    transform: translateX(0);
    transition: transform 0.5s ease-in-out;
  }

  @mixin overlays($property) {
    position: absolute;
    top: 0;
    display: flex;
    align-items: center;
    justify-content: space-around;
    flex-direction: column;
    padding: 70px 40px;
    /*width: calc(50% - 80px);*/
    width: calc(50% - 40px);
    height: calc(100% - 140px);
    text-align: center;
    transform: translateX($property);
    transition: transform 0.5s ease-in-out;
  }

  .overlay-left {
    @include overlays(-20%);
  }

  .overlay-right {
    @include overlays(0);
    right: 0;
  }
}

h2, h3 {
  margin: 0;
  font-family: "Noto Sans TC", "Microsoft Yahei", "微軟雅黑", sans-serif;
}

p {
  margin: 20px 0 30px;
}

a {
  color: #222;
  text-decoration: none;
  margin: 15px 0;
  font-size: 1rem;
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

button.invert {
  background-color: transparent;
  border-color: #fff;
}

div.sign-in, div.sign-up {
  position: absolute;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: space-around;
  flex-direction: column;
  padding: 90px 60px;
  /*width: calc(50% - 120px);*/
  width: calc(50% - 0px);
  /*height: calc(100% - 180px);*/
  height: calc(100% - 0px);
  text-align: center;
  background: linear-gradient(to bottom, #efefef, #ccc);
  transition: all 0.5s ease-in-out;

  div {
    font-size: 1rem;
  }


}

.sign-in {
  left: 0;
  z-index: 2;
}

.sign-up {
  left: 0;
  z-index: 1;
  opacity: 0;
}

.sign-up-active {
  .sign-in {
    transform: translateX(100%);
  }

  .sign-up {
    transform: translateX(100%);
    opacity: 1;
    z-index: 5;
    animation: show 0.5s;
  }

  .overlay-container {
    transform: translateX(-100%);
  }

  .overlay {
    transform: translateX(50%);
  }

  .overlay-left {
    transform: translateX(0);
  }

  .overlay-right {
    transform: translateX(20%);
  }
}

@keyframes show {
  0% {
    opacity: 0;
    z-index: 1;
  }
  49% {
    opacity: 0;
    z-index: 1;
  }
  50% {
    opacity: 1;
    z-index: 10;
  }
}

button.v-icon {
  /*background: yellow;*/
  padding-left: 10px;
  padding-right: 10px;
  height: 20px;
  width: 30px;
  border-style: none;
  background: linear-gradient(to bottom, #efefef, #ccc);
  margin-left: calc(100% + 50px);
}

.v-text-field {
  min-width: 17vw;;
}
/*
.text-teal input {
  color: #4dc0b5 !important;
}

.text-teal input::placeholder {
  color: red!important;
  opacity: 1;
}
*/
.text-teal .v-label {
  color: #909090;
  opacity: 1;
  font-size: 16px;
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
</style>

