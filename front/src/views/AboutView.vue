<template>
  <div class="page">
    <h1>This is an about page</h1>
  </div>
</template>

<script setup>
import { ref, defineComponent, computed, onMounted, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import { myMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'AboutView'
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
  console.log("AboutView, mounted()...");

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
  console.log("a, created()...")

});
*/
</script>

<style scoped>
.page {
  padding: 20px;
}
</style>
