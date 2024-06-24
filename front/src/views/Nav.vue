<template>
  <nav class="navbar navbar-expand-lg navbar-light bg-light fixed-top">
    <div class="container-fluid">
      <div class="navbar-brand">
        <img :src="home_url" alt="Logo" style="height: 4vw;">
      </div>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav">
          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/">Home</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/about">About</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/a">Item a</router-link>
          </li>

          <li class="nav-item dropdown" @mouseenter="showDropdown('b')" @mouseleave="hideDropdown('b')">
            <router-link class="nav-link my-nav-link-text" to="/b">Item b <i class="fas fa-angle-down"></i></router-link>
            <div class="dropdown-menu" :class="{ show: dropdownOpen.b }">
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/b/a">SubItem A</router-link>
              <router-link class="dropdown-item my-dropdown-item style='padding-left:20px !important;'" to="/b/b">SubItem B</router-link>
            </div>
          </li>

          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/c">Item c</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link my-nav-link-text" to="/d">MyTable</router-link>
          </li>
        </ul>
        <v-checkbox
          v-model="localShowFooter"
          label="Show Footer"
          class="ml-auto"
        ></v-checkbox>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, watch, defineComponent } from 'vue';
//import logo from '../assets/BBC-Line-Logo_Blue.png';
import logo from '../assets/logo.svg';
import VCheckbox from './VCheckbox.vue';

//=== component name ==
defineComponent({
  name: 'Nav'
});

//=== props ==
const props = defineProps({
  showFooter: Boolean
});

//=== emits ==
const emit = defineEmits(['update:showFooter']);

//=== data ===
const home_url = logo;
const localShowFooter = ref(props.showFooter);
const dropdownOpen = ref({ b: false });

//=== method ===
const showDropdown = (item) => {
  dropdownOpen.value[item] = true;
};

const hideDropdown = (item) => {
  dropdownOpen.value[item] = false;
};

//const toggleUnderline = (underline) => {
//  const brand = document.querySelector('.navbar-brand');
//  console.log("brand:", brand)
//  if (brand) {
//    brand.style.textDecoration = underline ? 'underline' : 'none';
//  }
//};

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