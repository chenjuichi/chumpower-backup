<template>
  <div :class="['page_contain', { 'no-footer': !showFooter }]" :style="containerStyle">
    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn color="#adadad" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <v-row align="center" justify="center" v-if="currentUser.perm >= 1">
      <v-card flat class="card-container">

        <h1>Welcome</h1>
        <p>This is Page a</p>

      </v-card>
    </v-row>
  </div>
</template>

<script setup>
import { ref, defineComponent, computed, onMounted, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import { myMixin } from '../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

//=== component name ==
defineComponent({
  name: 'a'
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
  console.log("a, mounted()...");

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

<style lang="scss" scoped>
.page_contain {
  position: fixed;
  left: 0px;

  padding: 60px 0px 0px;
  width: 100vw;             // 視窗寬度
  margin: 0;
}
</style>