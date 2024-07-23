<template>
  <div class="page_contain">
    <h1>This is B Page</h1>
    <p>Welcome to the B Page.</p>
  </div>
</template>

<script setup>
import { ref, defineComponent, computed, onMounted, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import { myMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'b'
});

// === mix ==
const { initAxios } = myMixin();

//=== data ===
const currentUser = ref(null);
const route = useRoute();

//=== computed ===
const routeName = computed(() => route.name);

//=== mounted ===
onMounted(() => {
  console.log("b, mounted()...");

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;

  console.log("currentUser:", currentUser.value);
});

//=== unmounted ===
/*
onUnmounted(() => {
  console.log("LoginForm, onUnmounted()...")

});
*/
/*
//=== created ===
onBeforeMount(() => {
  console.log("b, created()...")

});
*/
</script>

<style lang="scss" scoped>
.page_contain {
  position: fixed;
  left: 0px;

  padding: 60px 0px 0px;
  width: 100vw;           // 視窗寬度
  margin: 0;
}
</style>