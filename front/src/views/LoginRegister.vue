<template>
<div class="page_contain">
  <div class="wrapper" :class="{ active: isActive }">
      <!--<img id="sourceImage" :src="imageSrc" alt="Source Image">-->
      <canvas id="canvas" class="logo_img" />
    <h2 class="text-right">Welcome</h2>
    <div class="form-wrapper login">
      <form @submit.prevent="handleLogin">
        <h2>Login</h2>
        <div class="input-box">
          <input type="email" v-model="loginEmail" placeholder="Email" required>
        </div>
        <div class="input-box">
          <input type="password" v-model="loginPassword" placeholder="Password" required>
        </div>
        <button type="submit">Login</button>
        <div class="sign-link">
          <p>Don't have an account? <a href="#" @click.prevent="registerActive">Register</a></p>
        </div>
      </form>
    </div>
    <div class="form-wrapper register">
      <form @submit.prevent="handleRegister">
        <h2>Registration</h2>
        <div class="input-box">
          <input type="text" v-model="registerName" placeholder="Full Name" required>
        </div>
        <div class="input-box">
          <input type="email" v-model="registerEmail" placeholder="Email" required>
        </div>
        <div class="input-box">
          <input type="password" v-model="registerPassword" placeholder="Password" required>
        </div>
        <button type="submit">Register</button>
        <div class="sign-link">
          <p>Already have an account? <a href="#" @click.prevent="loginActive">Login</a></p>
        </div>
      </form>
    </div>
  </div>
  <img id="sourceImage" :src="imageSrc" alt="Source Image" style="display: none;">
</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

import pet from '../assets/pet4-rb.png';

const home_url = pet;
const isActive = ref(false)
const loginEmail = ref('')
const loginPassword = ref('')
const registerName = ref('')
const registerEmail = ref('')
const registerPassword = ref('')
const imageSrc = ref(require('../assets/pet4-rb.png'))


//const imageSrc = ref(null)
//imageSrc.value = require('../assets/pet4-rb.png');


//=== mounted ===
onMounted(() => {
  replaceImageColor();
});


const registerActive = () => {
  isActive.value = true
}

const loginActive = () => {
  isActive.value = false
}

const handleLogin = () => {
  console.log('Login', loginEmail.value, loginPassword.value)
}

const handleRegister = () => {
  console.log('Register', registerName.value, registerEmail.value, registerPassword.value)
}

const replaceImageColor = () => {
  console.log("replaceImageColor()...");

  const sourceImage = document.getElementById('sourceImage');
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  /*
  sourceImage.onload = function() {
    canvas.width = sourceImage.width;
    canvas.height = sourceImage.height;
    ctx.drawImage(sourceImage, 0, 0);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    const OLD_COLOR = '#ffffff';
    const NEW_COLOR = '#54880e';

    //const oldColor = { r: 2, g: 100, b: 206 }; // #0264ce
    //const newColor = { r: 90, g: 150, b: 204 }; // #5a96cc
    // 解析舊颜色和新颜色
    const oldColor = {
      r: parseInt(OLD_COLOR.substr(1, 2), 16),
      g: parseInt(OLD_COLOR.substr(3, 2), 16),
      b: parseInt(OLD_COLOR.substr(5, 2), 16)
    };

    const newColor = {
      r: parseInt(NEW_COLOR.substr(1, 2), 16),
      g: parseInt(NEW_COLOR.substr(3, 2), 16),
      b: parseInt(NEW_COLOR.substr(5, 2), 16)
    };

    for (let i = 0; i < data.length; i += 4) {
      if (data[i] === oldColor.r && data[i + 1] === oldColor.g && data[i + 2] === oldColor.b) {
        data[i] = newColor.r;
        data[i + 1] = newColor.g;
        data[i + 2] = newColor.b;
      }
    }



    //將圖像資料放回畫布上
    ctx.putImageData(imageData, 0, 0);
  };
  */
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
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional');

.page_contain {
  position: fixed;
  left: 0px;

  padding: 60px 0px 0px;
  width: 100vw;           // 視窗寬度
  margin: 0;
}

.wrapper {
    position: relative;
    width: 800px;
    height: 100vh;
    background: linear-gradient(90deg, #54880e, #f2f2f2);
    border-radius: 50px;
    box-shadow: 0 0 60px rgba(0, 0, 0, .3);
    padding: 60px;
    display: flex;
    align-items: center;
    overflow: hidden;
    margin-left: auto;
    margin-right: auto;
    margin-top: 5px;
}

.wrapper .text-right {
    position: absolute;
    top: 20px;
    right: 180px;
    color: #f2f2f2;
    text-shadow: 0 0 20px rgba(0, 0, 0, .3);
    font-size: 50px;
    user-select: none;
    font-family: 'Parisienne', cursive;
}

.wrapper .text-right::before {
    content: 'Back';
    position: absolute;
    top: 60px;
    right: -50px;
}

.wrapper img {
    position: absolute;
    right: -240px;
    bottom: 120px;
    width: 50%;
    //transform: rotate(260deg);
}

canvas {
  max-width: 100%;
  max-height: 100%;
}

.logo_container {
  position: relative;
  width: 52%;                 //佔總寬度的52%
  padding-top: 52%;
  //height: auto;             //可以設為明確的高度，或者百分比的高度
  display: flex;
  align-items: center;
  justify-content: center;    //水平和垂直居中
  overflow: hidden;           //防止溢出
}

.logo_container img {
  position: absolute;
  right: -40px;
  bottom: -60px;
  width: 60%;

  //top: 50%;
  //left: 50%;
  //width:100%;

  height: auto;             // 保持寬高比例
  transform: translate(-50%, -50%);
  object-fit: cover;
  object-position: center;
}

.logo_img {
  position: absolute;
  right: -240px;
  bottom: -60px;
  width: 60%;

  //top: 50%;
  //left: 50%;
  //width: 100%;

  height: auto;
  transform: translate(-50%, -50%);
  object-fit: cover;
  object-position: center;
}

.form-wrapper {
    z-index: 2;
}

.wrapper .form-wrapper.login {
    transition: .7s ease-in-out;
    transition-delay: .7s;
}
.wrapper.active .form-wrapper.login {
    transition-delay: 0s;
    transform: translateX(-400px);
}
.wrapper .form-wrapper.register {
    position: absolute;
    margin-top: 15px;
    transform: translateX(-400px);
    transition: .7s ease-in-out;
}
.wrapper.active .form-wrapper.register {
    transition-delay: .7s;
    transform: translateX(0);
}
h2 {
    font-size: 2em;
    text-align: center;
    color: #f2f2f2;
}
.input-box {
    position: relative;
    width: 320px;
    margin: 30px 0;
}
.input-box input {
    width: 100%;
    height: 50px;
    background: transparent;
    border: 2px solid #f2f2f2;
    outline: none;
    border-radius: 40px;
    font-size: 1em;
    color: #f2f2f2;
    padding: 0 20px 0 40px;
}
.input-box input::placeholder {
    color: rgba(255, 255, 255, .3);
}
.input-box .icon {
    position: absolute;
    left: 15px;
    color: #f2f2f2;
    font-size: 1.2em;
    line-height: 55px;
}
.forgot-pass {
    margin: -15px 0 15px 15px;
}
.forgot-pass a {
    color: #f2f2f2;
    font-size: .9em;
    text-decoration: none;
}
.forgot-pass a:hover {
    text-decoration: underline;
}
button {
    width: 100%;
    height: 45px;
    background: #f2f2f2;
    border: none;
    outline: none;
    border-radius: 40px;
    cursor: pointer;
    font-size: 1em;
    color: #54880e;
    font-weight: 500;
}
.sign-link {
    font-size: .9em;
    text-align: center;
    margin: 25px 0;
}
.sign-link p {
    color: #f2f2f2;
}
.sign-link p a {
    color: #f2f2f2;
    text-decoration: none;
    font-weight: 600;
}
.sign-link p a:hover {
    text-decoration: underline;
}
</style>
