<template>
    <footer class="footer">
      <p> © 銓寶工業 版權所有&nbsp;&nbsp;&nbsp; </p>
      <div class="logo-container">
        <img :src="home_url" alt="Home Logo" class="home-img-fluid home-logo" />
        <img :src="ce_logo_url" alt="CE Logo" class="ce-img-fluid ce-logo" />
      </div>
    </footer>
</template>

<script setup>
import { ref } from 'vue';
import { defineComponent } from 'vue';

import logo from '../assets/logo_en.svg';
import ce_logo from '../assets/certified-logo-ce.svg';

//=== component name ==
defineComponent({
  name: 'Footer'
});

//=== data ===
const home_url = logo;
const ce_logo_url = ce_logo;

</script>

  <style lang="scss" scoped>
  @import "../styles/variables.scss";

  .footer {
    background-color: $FOOTER_BG_COLOR;
    color: blue;
    text-align: center;
    height: 60px;
    width: 100%;

    position: fixed;
    bottom: 0;
    left: 0;
    z-index: 1000;
    display: flex;
    /*
    justify-content: space-between;
    align-items: center;
    width: 100%;
    */

    flex-direction: row;
    justify-content: center;
    align-items: center;
    padding: 10px 0;

    /*
    justify-content: center;
    align-items: center;
    line-height: 60px;
    */
  }

  .home-logo {
    /*align-self: flex-end;*/ /* 靠右 */
    align-content: center;
  }

  .ce-logo {
    /*align-self: flex-start;*/ /* 靠左 */
    align-content: center;
  }

  p {
    margin-top: 0;
    margin-bottom: 0;
  }

  .logo-container {
    display: flex;
    /* justify-content: space-between;*/ /* 水平均分 */
    align-items: center; /* 垂直置中 */
    width: 100%;
    max-width: 300px; /* 根據需要調整 */
  }

  .home-img-fluid {
    max-width: 80px;
    height: auto;
  }

  .ce-img-fluid {
    max-width: 50px;
    height: auto;
  }
</style>