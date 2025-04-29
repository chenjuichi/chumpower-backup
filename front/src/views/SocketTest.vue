<template>
<div :class="['page_contain', { 'no-footer': !showFooter }]" :style="containerStyle" :key="componentKey">
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
    {{ snackbar_info }}
    <template v-slot:actions>
      <v-btn color="#adadad" @click="snackbar = false">
        <v-icon dark>mdi-close-circle</v-icon>
      </v-btn>
    </template>
  </v-snackbar>

  <v-row class="mt-10">
    <v-col cols="12" md="6" class="d-flex justify-center align-center">
      <v-card width=500>
        <v-card-title>WebSocket 連線測試</v-card-title>
        <v-card-text class="d-flex flex-column align-center">
          <!--寬500, 水平置中-->
          <div style="min-width:500px; max-width:500px; text-align:center; display:flex; flex-direction:column; align-items:center;">
            <v-text-field v-model="socketName" label="輸入 Socket 名稱" width=400 />
            <v-btn color="green" @click="sendMessage" >送出</v-btn>
          </div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" md="6" class="d-flex justify-center align-center">
      <v-card height=180 width=300 class="d-flex flex-column">
        <v-toolbar color="cyan-lighten-1" height=40>
          <v-toolbar-title>伺服器回傳訊息</v-toolbar-title>
        </v-toolbar>
        <v-list class="overflow-y-auto" style="flex: 1;">
          <v-list-item
            style="padding: 1px 4px;
            min-height:30px;"
            v-for="(msg, index) in messages"
            :key="index"
          >
            {{ msg }}
          </v-list-item>
        </v-list>
    </v-card>
    </v-col>
  </v-row>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount } from 'vue';

import { useRoute } from 'vue-router';

import { myMixin } from '../mixins/common.js';
import { socket_server_ip }  from '../mixins/crud.js';        //虛的socket_server_ip, 不會真的用到
import { useSocketio } from '../mixins/SocketioService.js';
import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

//=== component name ==
defineComponent({  name: 'SocketTest' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const socketName = ref('');
const messages = ref([]);
//const isConnected = ref(false);

const userId = 'user_chumpower';
const clientAppName = 'SocketTest';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);
const route = useRoute();
const currentUser = ref({});
const componentKey = ref(0)     // key值用於強制重新渲染
const pagination = reactive({   // 預設值, rows/per page
  itemsPerPage: 5,
  page: 1,
});

//=== watch ===

//=== computed ===
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0',
}));

const routeName = computed(() => route.name);

//=== mounted ===
onMounted(async () => {
  console.log("SocketTest.vue, mounted()...");

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  initialize();

  console.log('等待socket連線...');
  try {
    await setupSocketConnection();

    socket.value.on('station1_agv_start', async () => {
      console.log('接收 station1_agv_start 訊息');
      messages.value.push(`接收 station1_agv_start`);
    });

    socket.value.on('station2_agv_start', async () => {
      console.log('接收 station2_agv_start 訊息');
      messages.value.push(`接收 station2_agv_start`);
    });

    socket.value.on('station1_agv_begin', async () => {
      console.log('接收 station1_agv_begin 訊息');
      messages.value.push(`接收 station1_agv_begin`);
    })

    socket.value.on('station2_agv_begin', async () => {
      console.log('接收 station2_agv_begin 訊息');
      messages.value.push(`接收 station2_agv_begin`);
    })

    socket.value.on('station2_agv_end', async () => {
      console.log('接收 station2_agv_end 訊息');
      messages.value.push(`接收 station2_agv_end`);
    });

    socket.value.on('station3_agv_end', async () => {
      console.log('接收 station3_agv_end 訊息');
      messages.value.push(`接收 station3_agv_end`);
    });

    socket.value.on('station1_agv_ready', async () => {
      console.log('接收 station3_agv_ready 訊息');
      messages.value.push(`接收 station3_agv_ready`);
    });

    socket.value.on('station2_agv_ready', async () => {
      console.log('接收 station2_agv_ready 訊息');
      messages.value.push(`接收 station2_agv_ready`);
    });

    socket.value.on('kuka_server_not_ready', (data) => {
      let temp_msg= data?.message || 'kuka端伺服器未準備好';
      console.warn(temp_msg);
      showSnackbar(temp_msg, 'red accent-2');
    });

    // event :接收到的事件名稱（例如 'station2_agv_start', 'station3_agv_ready'）。
    //...args:事件所附帶的資料（可以是單一變數，也可以是多個參數）。
    socket.value.onAny((event, ...args) => {
      console.log(`接收 ${event}`, args);

      messages.value.push(`接收 ${event}`);
      /*
      if (event === 'station2_agv_start') {
        console.log('處理 station2_agv_start 事件');
      } else if (event === 'station2_agv_begin') {
        console.log('處理 station2_agv_begin 事件');
      } else {
        console.log(`未定義的事件: ${event}`, args);
      }
      */
    });

  } catch (error) {
    console.error('Socket連線失敗:', error);
    showSnackbar(`Socket連線失敗: ${error}`, 'red accent-2');
  }
}); //end of onMounted

//=== unmounted ===
onUnmounted(() => {

});

//=== created ===
onBeforeMount(() => {
  console.log("SocketTest.vue, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

  } catch (error) {
    console.error("Error during initialize():", error);

  }
};

const sendMessage = () => {
  console.log("sendMessage(), socketName:", socketName.value);

  let keyword_message = [
    'candidate', 'answer', 'offer', 'join', 'disconnect', 'error',
    'station1_call', 'station1_agv_ready','station1_agv_start', 'station1_agv_begin', 'station1_agv_end',
    'station2_call', 'station2_agv_ready','station2_agv_start', 'station2_agv_begin', 'station2_agv_end',
    'station3_call', 'station3_agv_ready','station3_agv_start', 'station3_agv_begin', 'station3_agv_end',
    'agv_reset',
  ];

  const subArr = keyword_message.indexOf(socketName.value);
  if (subArr != -1) {
    showSnackbar(`不可以使用本系統之關鍵字!`, 'red accent-2');
    return;
  }

  socket.value.emit(socketName.value);
  console.log(`發送: ${socketName.value}`)
  messages.value.push(`發送 ${socketName.value}`);
  socketName.value="";
};

const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

@import "../styles/variables.scss";

.page_contain {
  position: fixed;
  left: 0px !important;
  top: 60px !important;       // 確保在導航欄下方
  bottom: 60px !important;    // 確保在頁腳上方
  padding: 0px 10px;
  width: 100vw;               // 視窗寬度
  margin: 0;
  overflow-y: auto;           // 添加 scrollbar，防止內容溢出
  overflow-x: hidden;
}

.no-footer {
  margin-bottom: 0;           // 沒有頁腳時的底部邊距
}
</style>

