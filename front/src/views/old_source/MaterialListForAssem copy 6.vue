<template>
<div :class="['page_contain', { 'no-footer': !showFooter }]" :style="containerStyle">
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
    {{ snackbar_info }}hello
    <template v-slot:actions>
      <v-btn color="#adadad" @click="snackbar = false">
        <v-icon dark>mdi-close-circle</v-icon>
      </v-btn>
    </template>
  </v-snackbar>

  <v-data-table
    :headers="headers"
    :items="materials"
    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
    :items-per-page-options="footerOptions"
    items-per-page="5"

    item-value="id"
    show-select
    :value="selectedItems"

    class="elevation-10 custom-table"
    items-per-page-text="每頁的資料筆數"
  >
    <!-- 自定義選擇框 -->
    <template v-slot:header.data-table-select>
      <span class="custom-header">送料</span>
    </template>

    <!-- 自定義每行的選擇框 -->
    <template v-slot:item.data-table-select="{ internalItem }">
      <v-checkbox-btn
        :model-value="isSelected(internalItem)"
        :disabled="!internalItem.raw.isTakeOk"
        color="primary"
        @update:model-value="toggleSelect(internalItem)"
        :class="{ 'blue-text': internalItem.raw.isTakeOk }"
      />
    </template>

    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="d-flex align-center pe-2" style="font-weight:700;">
          組裝區備料清單
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

          <!--客製化 匯入清單按鍵-->
          <v-btn
            :disabled="fileCount === 0"
            color="primary"
            variant="outlined"
            style="position: relative; right: 450px; top: 0px; font-weight: 700;"
            @click="readAllExcelFun"
          >
            <v-icon left color="green">mdi-microsoft-excel</v-icon>
            匯入清單
            <template v-if="fileCount > 0" v-slot:append>
              <v-badge color="info" :content="fileCount" inline />
            </template>
          </v-btn>

          <!--客製化 手推車/AGV切換按鍵-->
          <div class="button-container">
            <v-btn-toggle >
                <v-btn
                  variant="outlined"
                  :style="{
                    background: toggle_exclusive === 1 ? '#e67e22' : '#e7e9eb',
                    color: toggle_exclusive === 1 ? '#fff' : '#000',
                    fontWeight: '700'
                  }"
                  @click="setActive(1)"
                >
                  <v-icon right color="#003171">mdi-cart-outline</v-icon>
                  <span>手動推車</span>
                </v-btn>

                <v-btn
                  variant="outlined"
                  :style="{
                    background: toggle_exclusive === 2 ? '#27ae60' : '#e7e9eb',
                    color: toggle_exclusive === 2 ? '#fff' : '#000',
                    fontWeight: '700'
                  }"
                  @click="setActive(2)"
                >
                  <span>呼叫AGV</span>
                  <v-icon right color="#003171">mdi-truck-flatbed</v-icon>
                </v-btn>
            </v-btn-toggle>
          </div>

          <!--客製化flip button-->
          <!--
          <div class="flip_wrapper" v-show="!isBlinking">
            <div class="flip_btn" v-show="!isBlinking">

              <v-btn color="primary" :disable="!isBlinking" class="side default-side mt-n1 mr-15 mx-auto">
                <v-icon left>mdi-account-arrow-right-outline</v-icon>
                備料送出
              </v-btn>

              <v-btn color="primary" :disable="isBlinking" class="side hover-side mt-n1 mr-15 mx-auto" @click="callAGV">
                <v-icon left size="24px">mdi-check-circle-outline</v-icon>
                確定
              </v-btn>
            </div>
          </div>
          -->

          <!--客製化 備料送出按鍵-->
          <v-btn
            :disabled="isBlinking"
            color="primary"
            variant="outlined"
            style="position: relative; left: -100px; top: 0px; font-weight: 700;"
            @click="callAGV"
          >
            <v-icon left color="blue">mdi-account-arrow-right-outline</v-icon>
            備料送出
          </v-btn>

          <!-- 客製化黃綠燈 -->
          <div>
            <span
              :style="{
                display: 'inline-block',
                borderRadius: '50%',
                width: '25px',
                height: '25px',
                position: 'relative',
                top: '7px',
                left: '5px',

                opacity: isFlashLed && isVisible ? 1 : 0, // 根據 isFlashLed 和 isVisible 控制顯示
                transition: 'opacity 0.5s ease',          // 過渡效果
                background: background,                   // 背景顏色
                border: '1px solid black'                 // 黑色邊框
              }"
            />
          <!--
            <span style="margin-left: 10px; font-size: 14px;" :class="{ 'blinking': isBlinking }">
              {{order_num_on_agv_blink}}
            </span>
          -->
          </div>

          <v-dialog
            v-model="dialog"
            max-width="800px"
            @keydown.esc="handleEscClose"
            @click:outside="handleOutsideClick"
          >
            <v-card :style="{ maxHeight: boms.length > 5 ? '500px' : 'unset', overflowY: boms.length > 5 ? 'auto' : 'unset' }">
              <v-card-title class="text-h5 sticky-title" style="background-color: #1b4965; color: white;">
                備料資訊
                <v-fade-transition mode="out-in">
                  <v-btn
                    style="position: relative; right: -550px;"
                    color="success"
                    prepend-icon="mdi-check-circle-outline"
                    :disabled="enableDialogBtn"
                    text="確定"
                    class="text-none"
                    @click="updateItem"
                    variant="flat"
                    flat
                  />
                </v-fade-transition>
              </v-card-title>

              <v-card-text>
                <v-table class="inner" density="compact" fixed-header>
                  <thead style="color: black;">
                    <tr>
                      <th class="text-left">元件</th>
                      <th class="text-left">物料</th>
                      <th class="text-left">數量</th>
                      <th class="text-left">日期</th>
                      <th class="text-left">領料</th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr
                      v-for="(bom_item, index) in boms"
                      :key="bom_item.seq_num"
                      :style="{
                        backgroundColor: index % 2 === 0 ? '#ffffff' : '#edf2f4',
                      }"
                    >
                      <td>{{ bom_item.seq_num }}</td>
                      <td>
                        <div>
                          <div>{{ bom_item.material_num }}</div>
                          <div style="color: #33cccc; font-weight: 600">{{ bom_item.mtl_comment }}</div>
                        </div>
                      </td>
                      <td>
                        <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.qty }}</div>
                      </td>
                      <td>
                        <div>
                          <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.date }}</div>
                          <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.date_alarm }}</div>
                        </div>
                      </td>
                      <td>
                        <v-checkbox-btn v-model="bom_item.receive" :disabled="enableDialogBtn" />
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card-text>
            </v-card>
          </v-dialog>
        </v-card-title>
      </v-card>
    </template>

    <!-- 使用動態插槽來客製化 '需求數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
        <div>{{ column.title }}</div>
        <div style="font-size:12px; margin-top: 5px;">(建立日期)</div>
      </div>
    </template>

    <template v-slot:item.order_num="{ item }">
      <div>
        <div style="color: red;" v-if="item.isTakeOk && item.isLackMaterial != 99">{{ item.order_num }}</div> <!--檢料完成-->
        <div style="color: blue;" v-else-if="item.isTakeOk && item.isLackMaterial == 99">{{ item.order_num }}</div> <!--檢料完成-->
        <div v-else>{{ item.order_num }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px;">{{ item.process_num }}</div>-->
      </div>
    </template>

    <!--
    <template v-slot:item.material_num="{ item }">
      <div>
        <div>{{ item.material_num }}</div>
        <div :style="getStatusStyle(item.material_status)">{{ material_status[item.material_status] }}</div>
      </div>
    </template>
    -->

    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.date }}</div>
      </div>
    </template>

    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>-->
      </div>
    </template>

    <template v-slot:item.action="{ item }">
      <v-btn
        size="small"
        variant="tonal"
        style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"

        @click="toggleExpand(item)"
      >
        詳 情
        <v-icon color="orange-darken-4" end>mdi-open-in-new</v-icon>
      </v-btn>
    </template>

    <!-- 自訂 '送料數量' 輸入欄位 -->
    <template v-slot:item.delivery_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
        :model-value="item.delivery_qty"

          dense
          hide-details
          :id="`receiveQtyID-${item.id}`"
          @update:modelValue="(value) => {
            item.delivery_qty = value;
            checkReceiveQty(item);
          }"
          @update:focused="(focused) => checkTextEditField(focused, item)"
          @keyup.enter="updateItem2(item)"
          :disabled="item.input_disable"
        />
        <span
          v-show="item.tooltipVisible"
          style="position: absolute; left: -60px; top: 20; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 400; font-size: 10px !important;"
        >
          {{ delivery_qty_alarm }}
        </span>
      </div>
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

import { useRoute } from 'vue-router'; // Import useRouter

import { myMixin } from '../mixins/common.js';

import { useSocketio } from '../mixins/SocketioService.js';

//import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { materials, boms, socket_server_ip, fileCount }  from '../mixins/crud.js';

import { apiOperation, setupGetBomsWatcher}  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
const countExcelFiles = apiOperation('get', '/countExcelFiles');
const listMaterials = apiOperation('get', '/listMaterials');
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

const getBoms = apiOperation('post', '/getBoms');
const updateBoms = apiOperation('post', '/updateBoms');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const getMaterial = apiOperation('post', '/getMaterial');

//=== component name ==
defineComponent({
  name: 'MaterialListForAssem'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
  showFooter: Boolean
});

//=== data ===
const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const toggle_exclusive = ref(2); // 控制選擇的按鈕, 預設AGV

const isVisible = ref(true);             // 設定初始狀態為顯示
const isFlashLed = ref(false);           // 控制是否閃爍Led
let intervalIdForLed = null;
const background = ref('#ffff00');

let intervalId = null;              // 10分鐘, 倒數計時器
let debounceTimeout = null;

const deliveryQtyRefs = ref({});

const route = useRoute(); // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'id', width: '2px' },
  { title: '訂單編號', sortable: true, key: 'order_num' },
  { title: '物料編號', sortable: false, key: 'material_num'},
  { title: '需求數量', sortable: false, key: 'req_qty' },
  //{ title: '場域位置', sortable: false, key: 'location' },
  //{ title: '缺料註記', sortable: false, key: 'shortage_note' },
  { title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '備料內容', sortable: false, key: 'action' },
  //{ title: '待送料總數', sortable: false, key: 'total_delivery_qty' },
  { title: '應備料總數', sortable: false, key: 'total_delivery_qty' },
  //{ title: '實際送料數', sortable: false, key: 'delivery_qty' },
  { title: '已備料總數', sortable: false, key: 'delivery_qty' },
  //{ title: '組裝區', sortable: false, key: 'agv' },
];

const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)

const inputIDs = ref([]);

//const localIp = 'localhost';
//const serverIp = process.env.VUE_SOCKET_SERVER_IP || '192.168.0.13';
//const serverIp = '192.168.0.13';
//const serverIp = process.env.VUE_SOCKET_SERVER_IP
const userId = 'user_chumpower';
//console.log("serverIp:", serverIp)
// 初始化Socket連接
//const { socket, setupSocketConnection } = useSocketio(localIp, userId);
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const delivery_qty_alarm = ref('');

//const localIP = ref('');
const from_agv_input_order_num = ref('');
const isBlinking = ref(false);          // 控制按鍵閃爍
const order_num_on_agv_blink=ref('');

const currentUser = ref({});
const permDialog = ref(false);
const enableDialogBtn = ref(false);
//const rightDialog = ref(false);
//const showExplore = ref(false);
//const showVirtualTable = ref(false);

const current_cell = ref(null);

const currentStartTime = ref(null);  // 記錄開始時間

const agv1StartTime = ref(null);
const agv1EndTime = ref(null);
const agv2StartTime = ref(null);
const agv2EndTime = ref(null);

const dialog = ref(false);

const selectedItem = ref(null); // 儲存當前點擊的記錄

const pagination = reactive({
  itemsPerPage: 5, // 預設值, rows/per page
  page: 1,
});

//=== watch ===
watch(currentUser, (newUser) => {
  if (newUser.perm < 1) {
    permDialog.value = true;
  }
});

setupGetBomsWatcher();

// 監視 boms 整個陣列
//watch(() => boms.value.map((bom_item) => bom_item.receive), (newValues) => {
//    console.log("watch(), newValues:", newValues)
//    if (newValues.includes(false)) {
//      selectedItem.show2_ok = false; // 如果有任一 receive 為 false
//    } else {
//      selectedItem.show2_ok = true; // 如果所有 receive 都為 true
//    }
//  },
//  {
//    deep: true,
//    immediate: true
//  } // 深度監視並立即執行
//);

// 監視 isFlashLed 的變化
//watch(isFlashLed, (newVal) => {
//  if (newVal) {
//    startFlashing();
//  } else {
//    stopFlashing();
//  }
///});

//=== computed ===
const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)',
  width: '1050px',
  overflowY: 'hidden',
  position: 'relative',
  top: '-30px',
  marginBottom: '5px',
}));

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  // 取得每個 v-text-field 的唯一 ID
  inputIDs.value.forEach((item) => {
    const myIdField = document.getElementById(`receiveQtyID-${item.id}`);
    myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  });

  fileCount.value = countExcelFiles();
  console.log("fileCount:", fileCount.value);

  intervalId = setInterval(countExcelFiles, 10 * 60 * 1000);  // 每 10 分鐘調用一次 API, 10分鐘=600000毫秒

  intervalIdForLed = setInterval(() => {
    isVisible.value = !isVisible.value;  // 每秒切換顯示狀態
  }, 500);

  //if (isFlashLed.value)
  //  startFlashing();
  // isBlinking 為 true, 若陣列是空的或陣列中所有項目的 isTakeOk 都是 false

  isBlinking.value = materials.value.length == 0 || materials.value.every(item => !item.isTakeOk || item.isTakeOk==item.isShow);

  /*
  console.log('取得本機ip...');
  try {
    localIP.value = await getLocalIP();
    console.error('本機ip:', localIP.value);
  } catch (err) {
    console.error(err);
  }
  */
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();

    socket.value.on('station1_agv_wait', async (data) => {   //注意, 已修改為async 函數
      console.log('AGV開始, 收到 station1_agv_wait 訊息, 工單:', data);

      const materialPayload0 = {
        order_num: data,
      };
      const response0 = await getMaterial(materialPayload0);

      if(response0) {
        console.log('工單 '+ data + ' 已檢料完成!');
        socket.value.emit('station1_order_ok');

        //from_agv_input_order_num.value = data;
        //order_num_on_agv_blink.value = "工單:" + data + "物料運送中...";
        //isBlinking.value = true; // 開始按鍵閃爍

        // 定義 materialPayload1
        const materialPayload1 = {
          order_num: from_agv_input_order_num.value, // 確保 my_material_orderNum 已定義
          record_name: 'show3_ok',
          record_data: 1    // 設為 1，等待agv
        };
        await updateMaterial(materialPayload1);
      } else {
        console.log('工單 '+ data + ' 還沒檢料完成!');
        socket.value.emit('station1_order_ng');
        order_num_on_agv_blink.value = '';
      }
    });

    socket.value.on('station1_agv_begin', async (data) => {
      console.log('AGV暫停, 收到 station1_agv_begin 訊息, 工單:', data);

      from_agv_input_order_num.value = data;
      order_num_on_agv_blink.value = "工單:" + data + "物料運送中...";

      // 記錄agv在站與站之間運行開始時間
      agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2StartTime.value);

      const materialPayload1 = {
        order_num: from_agv_input_order_num.value, // 確保 my_material_orderNum 已定義
        record_name: 'show3_ok',
        record_data: 2      // 設為 2，agv移動至組裝區中
      };
      await updateMaterial(materialPayload1);

      let agv1PeriodTime = calculatePeriodTime(agv1StartTime.value, agv1EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv1StartTime.value);
      let formattedEndTime = formatDateTime(agv1EndTime.value);
      console.log("Formatted AGV Start Time:", formattedStartTime);
      console.log("Formatted AGV End Time:", formattedEndTime);
      console.log("AGV Period time:", agv1PeriodTime);

      const processPayload = {
        begin_time: formattedStartTime,
        end_time: formattedEndTime,
        periodTime: agv1PeriodTime,
        user_id: 'AGV1',
        order_num: from_agv_input_order_num.value,
        process_type: 1,
      };
      await createProcess(processPayload);

      background.value='#10e810'
    })

    socket.value.on('station2_agv_end', async (data) => {
      console.log('AGV暫停, 收到 station2_agv_end 訊息, 工單:', data);

      let materialPayload1 = {
        order_num: data,
        show1_ok: 2,      //組裝站
        show2_ok: 3,      //未組裝
        show3_ok: 3,      //等待組裝中
        whichStation: 2,  //目標途程:組裝站
      };
      await updateMaterialRecord(materialPayload1);

      let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv2StartTime.value);
      let formattedEndTime = formatDateTime(agv2EndTime.vale);
      console.log("Formatted AGV Start Time:", formattedStartTime);
      console.log("Formatted AGV End Time:", formattedEndTime);
      console.log("AGV Period time:", agv2PeriodTime);

      let processPayload = {
        begin_time: formattedStartTime,
        end_time: formattedEndTime,
        periodTime: agv2PeriodTime,
        user_id: 'AGV2',
        order_num: from_agv_input_order_num.value,
        process_type: 2,
      };
      await createProcess(processPayload);

      materialPayload1 = {
        order_num: data,
        record_name: 'isShow',
        record_data: true
      };
      await updateMaterial(materialPayload1);

      //let myMaterial = materials.value.find(m => m.order_num == data);
      //myMaterial.isShow = true;
      //isBlinking.value = false;           // 停止工單運送字串閃爍
      //order_num_on_agv_blink.value = '';

      let myMaterialIndex = materials.value.findIndex(m => m.order_num == data);
      if (myMaterialIndex != -1) {
        materials.value[myMaterialIndex] = {
          ...materials.value[myMaterialIndex],
          isShow : true,
        };
        isBlinking.value = false;           // 停止工單運送字串閃爍
        order_num_on_agv_blink.value = '';
      }

      // 方法1: 重新賦值來觸發 Vue 的響應式系統
      //materials.value = [...materials.value];

      // 方法2: 手動重新獲取資料
      await listMaterials();

      //stopFlashing();
      isFlashLed.value = false;
    });

    socket.value.on('station1_agv_ready', async () => {
      console.log('AGV 已到達裝卸站, 收到 station1_agv_ready 訊息...');
      // 記錄等待ag到站結束時間
      agv1EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV End time:", agv1EndTime.value);
      //startFlashing();
      background.value='#ffff00'
      isFlashLed.value = true;
    });
  } catch (error) {
    console.error('Socket連線失敗:', error);
  }
});

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  clearInterval(intervalId);
  //clearInterval(intervalIdForLed);
  stopFlashing();
});

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

    // 使用 async/await 等待 API 請求完成，確保順序正確
    await listMaterials();

    await listSocketServerIP();
    console.log("initialize, socket_server_ip:", socket_server_ip.value)
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

// 啟動閃爍效果
//const startFlashing = () => {
//  console.log("startFlashing()...")
//
//  isFlashLed.value = true;
//  intervalIdForLed = setInterval(() => {
//    isVisible.value = !isVisible.value; // 每秒切換顯示狀態
//  }, 500);
//}

// 停止閃爍效果
const stopFlashing = () => {
  console.log("stopFlashing()...")

  clearInterval(intervalIdForLed);
  isVisible.value = true;               // 重設為顯示
  isFlashLed.value = false;
}
/*
const getStatusStyle = (status) =>{
  const colorMap = {
    0: '#ff4000',
    1: '#0040ff',
    2: '#669999',
    3: '#ffbf00',
  };

  return {
    color: colorMap[status],
    fontWeight: '600',
    fontSize: '12px',
  };
};
*/
const setActive = (value) => {
  toggle_exclusive.value = value; // 設置當前活動按鈕
}

const checkReceiveQty = (item) => {
    console.log("checkReceiveQty,", item);

    const total = Number(item.delivery_qty) + Number(item.total_delivery_qty);
    const temp = Number(item.req_qty)
    if (total > temp) {
      delivery_qty_alarm.value = '送料數量超過需求數量!';
      item.tooltipVisible = true;       // 顯示 Tooltip
      setTimeout(() => {
        item.tooltipVisible = false;    // 2秒後隱藏 Tooltip
        //item.delivery_qty = '';         // 清空輸入欄位
      }, 2000);
      console.error('送料數量超過需求數量');
    } else {
      item.tooltipVisible = false;
      delivery_qty_alarm.value = ''; // 清除警告
    }
};

const handleKeyDown = (event) => {
  const inputChar = event.key;

  const caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when CapsLock is on

  // 允許左右方向鍵、backspace 和 delete 鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }

  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
    event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
  }

  // 偵測是否按下 Enter 鍵
  if (event.key === 'Enter' || event.keyCode === 13) {
    console.log('Return key pressed');
    // 如果需要，這裡可以執行其他操作，或進行額外的驗證
    //checkReceiveQty(event.target.item);  // 檢查接收數量的驗證
  }
};

const isSelected = (item) => {
  console.log("isSelected(), item.columns.id", item.raw, item.columns.id); // 查看 item.columns 是否包含 id
  return selectedItems.value.includes(item.columns.id); // 根據 columns.id 檢查是否被選中
};

const toggleSelect = (item) => {
  console.log("toggleSelect(), item.columns.id", item.raw, item.columns.id); // 查看 item.columns 是否包含 id
  const index = selectedItems.value.indexOf(item.columns.id);
  if (index === -1) {
    selectedItems.value.push(item.columns.id); // 若未選中，則添加 columns.id
  } else {
    selectedItems.value.splice(index, 1); // 若已選中，則移除 columns.id
  }
};

const handleEscClose = async () => {
  console.log("Dialog closed via ESC key, item:", selectedItem.value);

  // 記錄當前途程狀態
  let payload = {
    order_num: selectedItem.value.order_num,
    record_name: 'show2_ok',
    record_data: 0                //未備料
  };
  await updateMaterial(payload);
  //updateMaterial(payload).then(data => {
  //  !data && showSnackbar(data.message, 'red accent-2');
  //});

  dialog.value = false;
};

const handleOutsideClick = async () => {
  console.log("Dialog closed by clicking outside, item:", selectedItem.value);

  // 記錄當前途程狀態
  let payload = {
    order_num: selectedItem.value.order_num,
    record_name: 'show2_ok',
    record_data: 0                //未備料
  };
  await updateMaterial(payload);
  //updateMaterial(payload).then(data => {
  //  !data && showSnackbar(data.message, 'red accent-2');
  //});

  dialog.value = false;
};

// 開啟對話框並傳遞點擊的資料
//const openDialog = (item) => {
//  console.log("openDialog(), item:", item);
//
//  selectedItem.value = item;  // 儲存當前選中的行資料
//  dialog.value = true;        // 開啟對話框
//};

/*
const getServerIP = async () => {   // 定義一個異步函數來請求socket伺服器 IP
  try {
    const response = await axios.get('http://localhost:6500/server-ip'); // 請求伺服器 IP
    serverIP.value = response.data.ip;
  } catch (error) {
    console.error('無法獲取伺服器 IP:', error);
    serverIP.value = '無法獲取伺服器 IP';
  }
};
*/
const toggleExpand = async (item) => {
  console.log("toggleExpand(),", item.order_num);

  enableDialogBtn.value = item.isTakeOk && !item.isShow;

  let payload = {
    order_num: item.order_num,
  };
  await getBoms(payload);
  current_cell.value = item.delivery_qty
  selectedItem.value = item;
  console.log("toggleExpand, selectedItem.value", selectedItem.value)
  //Object.assign(selectedItem.value, item);

  // 1.記錄當前開始備料時間
  currentStartTime.value = new Date();  // 使用 Date 來記錄當時時間
  console.log("Start time:", currentStartTime.value);

  // 2.記錄當前途程狀態
  payload = {
    id: item.id,
    //order_num: item.order_num,
    record_name: 'show2_ok',
    record_data: 1                //備料中
  };
  await updateMaterial(payload);

  payload = {
    id: item.id,
    //order_num: item.order_num,
    record_name: 'shortage_note',
    record_data: ''
  };
  await updateMaterial(payload);

  //updateMaterial(payload).then(data => {
  //  !data && showSnackbar(data.message, 'red accent-2');
  //});

  dialog.value = true;
};


const checkTextEditField = (focused, item) => {
  if (!focused) { // 當失去焦點時
    console.log("checkTextEditField(): 失去焦點");

    // 當失去焦點時，檢查是否需要保留更新值
    if (current_cell.value !== null) {
      item.delivery_qty = current_cell.value;
    }
    //item.delivery_qty = current_cell.value;

    //if (item.receive_qty.trim().length == 0)
    //  item.receive_qty =0;        // 強迫輸入值為0

    // 檢查 item.pickBegin 是否為空陣列
    /*
    if (item.pickBegin.length == 0) {
      item.receive_qty = 0; // 若為空陣列，設置 item.receive_qty 為 0
    } else {
      item.receive_qty = item.pickBegin[item.pickBegin.length - 1]; // 若不是空陣列，將最後一筆值 assign 給 item.receive_qty
    }
    */
  } else {
    console.log("checkTextEditField(): 獲得焦點");

    current_cell.value = item.delivery_qty; // 儲存當前值
  }
};

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  // 檢查是否輸入了空白或 0
  if (!item.delivery_qty || Number(item.delivery_qty) === 0) {
    console.log("item.delivery_qty:", item.delivery_qty)
    delivery_qty_alarm.value = '送料數量不可為空白或0!'
    item.tooltipVisible = true;     // 顯示 Tooltip 提示
    setTimeout(() => {
      item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.delivery_qty = '';        // 清空輸入欄位
    }, 2000);
    console.error('送料數量不可為空白或0!');
    return;
  }

  let payload = {};

  // 記錄當前送料數量
  payload = {
    id: item.id,
    record_name: 'delivery_qty',
    record_data: Number(item.delivery_qty),
  };
  await updateMaterial(payload);

  // 記錄當前已送料總數量
  let total = Number(item.delivery_qty) + Number(item.total_delivery_qty);
  payload = {
    id: item.id,
    record_name: 'total_delivery_qty',
    record_data: total,
  };
  await updateMaterial(payload);
  item.total_delivery_qty = total.toString().trim()

  let temp1 = Number(item.total_delivery_qty)
  let temp2 = Number(item.req_qty)
  console.log("temp2 == temp1",temp2, temp1)
  // 確認 已送料總數量=需求數量
  if (temp2 == temp1) {
    // 記錄當前紀錄, 不能再輸入
    payload = {
      id: item.id,
      record_name: 'input_disable',
      record_data: true,
    };
    await updateMaterial(payload);
    item.input_disable = true;
  }

};

const updateItem = async () => {              //編輯 bom, material及process後端table資料
  console.log("updateItem(),", boms.value);

  let my_material_orderNum = boms.value[0].order_num;

  let endTime = new Date();                                               // 記錄當前結束時間
  let periodTime = calculatePeriodTime(currentStartTime.value, endTime);  // 計算時間間隔
  let formattedStartTime = formatDateTime(currentStartTime.value);
  let formattedEndTime = formatDateTime(endTime);

  // 使用 .some() 檢查是否有任何 `receive` 為 false 的項目，若有則將 `take_out` 設為 false
  let take_out = !boms.value.some(bom => !bom.receive);
  console.log("take_out:", take_out);

  // 1. 更新 boms 資料
  let response0 = await updateBoms(boms.value);
  if (!response0) {
    showSnackbar(response0.message, 'red accent-2');
    dialog.value = false;
    return;
  }

  let materialPayload = {}

  //if (take_out) {                 // 該筆訂單檢料完成
    materialPayload = {           // 更新 materials 資料
      id: selectedItem.value.id,
      record_name: 'delivery_qty',
      record_data: selectedItem.value.req_qty
    };
    await updateMaterial(materialPayload);

    materialPayload = {           // 更新 materials 資料
      id: selectedItem.value.id,
      record_name: 'input_disable',
      record_data: false
    };
    await updateMaterial(materialPayload);

    selectedItem.value.input_disable = false;
    selectedItem.value.delivery_qty = selectedItem.value.req_qty;
  //}

  if (!take_out) {                    // 該筆訂單檢料未完成, 缺料
    materialPayload = {               // 更新 materials 資料，shortage_note = '(缺料)'
      order_num: my_material_orderNum,
      record_name: 'shortage_note',
      record_data: '(缺料)'
    };
    await updateMaterial(materialPayload);
    selectedItem.value.shortage_note = '(缺料)';

    materialPayload = {               // 2. 更新 materials 資料，isLackMaterial = 1
      order_num: my_material_orderNum,
      record_name: 'isLackMaterial',
      record_data: 1          //缺料
    };
    await updateMaterial(materialPayload);
    selectedItem.value.isLackMaterial = false;
  }

  materialPayload = {                       // 2. 更新 materials 資料，isTakeOk = true
    order_num: my_material_orderNum,
    record_name: 'isTakeOk',
    record_data: true
  };
  await updateMaterial(materialPayload);
  selectedItem.value.isTakeOk = true;


  if (take_out) {                     // 該筆訂單檢料完成
    materialPayload = {               // 2. 更新 materials 資料，show2_ok = 2
      order_num: my_material_orderNum,
      record_name: 'show2_ok',
      record_data: 2                  // 設為 2，表示備料完成
    };
    await updateMaterial(materialPayload);
    //const response1 = await updateMaterial(materialPayload1);
    //if (!response1) {
    //  showSnackbar(response1.message, 'red accent-2');
    //  dialog.value = false;
    //  return;
    //}
    //materialPayload = {
    //   order_num: my_material_orderNum,
    //   record_name: 'isShow',
    //   record_data: true
    // };
    //await updateMaterial(materialPayload);

    //let myMaterial = materials.value.find(m => m.order_num == my_material_orderNum);
    //myMaterial.isTakeOk =true;

    //materialPayload = {        // 2. 更新 materials 資料，isTakeOk = true
    //  order_num: my_material_orderNum,
    //  record_name: 'isTakeOk',
    //  record_data: true
    //};
    //await updateMaterial(materialPayload);

    //materialPayload = {         // 2. 更新 materials 資料，isTakeOk = true
    //  order_num: my_material_orderNum,
    //  record_name: 'isShow',    // disable button
    //  record_data: true
    //};
    //await updateMaterial(materialPayload);

    //let matchResult = materials.value.find(x => x.id == selectedItem.value.id);
    //console.log("matchResult:", matchResult)
    //if (matchResult) {
    //  matchResult.isTakeOk = true;
    //  isBlinking.value = materials.value.some((item) => !item.isTakeOk);
    //}

    //const response11 = await updateMaterial(materialPayload11);
    //if (!response11) {
    //  showSnackbar(response11.message, 'red accent-2');
    //  dialog.value = false;
    //  return;
    //}

    //let myMaterial = materials.value.find(m => m.order_num == my_material_orderNum);
    let myMaterialIndex = materials.value.findIndex(m => m.order_num === my_material_orderNum);

    if (myMaterialIndex != -1) {
      materials.value[myMaterialIndex] = {
        ...materials.value[myMaterialIndex],
        isTakeOk: true,
        show2_ok: 2,
        //isShow: true
      };
      //isBlinking.value = materials.value.some((item) => !item.isTakeOk);
      isBlinking.value = materials.value.every((item) => !item.isTakeOk);
    }

    console.log("Formatted Start Time:", formattedStartTime);
    console.log("Formatted End Time:", formattedEndTime);
    console.log("Period time:", periodTime);
    let processPayload = {
      begin_time: formattedStartTime,
      end_time: formattedEndTime,
      periodTime: periodTime,
      user_id: currentUser.value.empID,
      order_num: my_material_orderNum,
      process_type: 1,
    };
    await createProcess(processPayload);

    await listMaterials();
  }

  dialog.value = false;
};

const calculatePeriodTime = (start, end) => {     // 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
  const diffMs = end - start;                     // 差異時間（毫秒）
  const diffSeconds = Math.floor(diffMs / 1000);  // 轉換為秒

  const hours = Math.floor(diffSeconds / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);
  const seconds = diffSeconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

const formatDateTime = (date) => {
  if (!date || !(date instanceof Date)) {
    console.error("Invalid date passed to formatDateTime:", date);
    return 'Invalid Date';
  }

  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');  // 月份是從0開始的，所以加1
  const dd = String(date.getDate()).padStart(2, '0');
  const hh = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  const ss = String(date.getSeconds()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
};

const formatTime = (time) => {                            // 格式化時間為 hh:mm:ss
  const hours = String(time.getHours()).padStart(2, '0');
  const minutes = String(time.getMinutes()).padStart(2, '0');
  const seconds = String(time.getSeconds()).padStart(2, '0');

  return `${hours}:${minutes}:${seconds}`;
};

const callAGV = async () => {
  console.log("callAGV()...")

  if (selectedItems.value.length == 0) {
    showSnackbar("請選擇出料的工單!", 'orange-darken-2');
    return;
  }

  /*
  const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
    order_num: my_material_orderNum,
    record_name: 'show3_ok',
    record_data: 1                  // 設為 2，表示備料完成
  };

  await updateMaterial(materialPayload1);
  */
  isBlinking.value = true;
  socket.value.emit('station1_call');
  // 記錄等待agv到站開始時間
  agv1StartTime.value = new Date();  // 使用 Date 來記錄當時時間
  console.log("AGV Start time:", agv1StartTime.value);
};

/*
const readAllExcelFun = () => {
  console.log("readAllExcelFun()...");

  if (fileCount.value == 0) {
    console.warn("No files available for import.");
    return;
  }

  readAllExcelFiles().then(data => {
    console.log("data:", data);

    if (data.status) {
      fileCount.value = 0;
      listMaterials();
    } else {
      showSnackbar(data.message, 'red accent-2');
    }
    //data.status ? listMaterials() : showSnackbar(data.message, 'red accent-2');
  });
};
*/
const readAllExcelFun = async () => {
  console.log("readAllExcelFun()...");

  if (fileCount.value === 0) {
    console.warn("No files available for import.");
    return;
  }

  try {
    // 等待 readAllExcelFiles 完成
    const data = await readAllExcelFiles();
    console.log("data:", data);

    if (data.status) {
      fileCount.value = 0;
      await deleteAssemblesWithNegativeGoodQty();
      listMaterials();
    } else {
      showSnackbar(data.message, 'red accent-2');
    }
  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("An error occurred.", 'red accent-2');
  }
};

/*
// 獲取本機 IP 的函數
const getLocalIP = async () => {
  try {
    const rtc = new RTCPeerConnection({ iceServers: [] });
    rtc.createDataChannel(''); // 創建一個數據通道以避免錯誤
    const offer = await rtc.createOffer();
    await rtc.setLocalDescription(offer);

    return new Promise((resolve, reject) => {
      rtc.onicecandidate = (ice) => {
        if (ice && ice.candidate && ice.candidate.candidate) {
          const ipMatch = ice.candidate.candidate.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
          if (ipMatch) {
            for (let i = 0; i < ipMatch.length; i++) {
              console.log("local ip:",ipMatch[i])
            }
            //resolve(ipMatch[1]); // 返回找到的 IP 地址
            const ip = ipMatch[0];
            // 檢查 IP 是否為無線網卡的 IP 地址
            // 假設無線網卡的 IP 是 192.168.*.* 或 10.*.*.*
            //if (ip.startsWith('192.168.') || ip.startsWith('10.')) {
            //if (ip.startsWith('192.168.')) {
                resolve(ip); // 返回找到的無線 IP 地址
            //}
          }
        }
      };

      // 超時處理
      setTimeout(() => {
        reject('無法獲取 IP 地址');
      }, 1000);
    });
  } catch (err) {
    console.error('獲取本機 IP 時出現錯誤:', err);
    error.value = '無法獲取本機 IP';
  }
};
*/

const showSnackbar = (message, color) => {
  if (debounceTimeout) {
    clearTimeout(debounceTimeout);
  }

  debounceTimeout = setTimeout(() => {
    snackbar_info.value = message;
    snackbar_color.value = color;
    snackbar.value = true;
  }, 100); // 防止短時間內重複觸發
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
  overflow-y: auto;           // 添加scrollbar，防止內容溢出
  overflow-x:hidden;
}

.table_border_radius {
  border-radius: 0px 0px 10px;
}

.card_container {
    // width: 100%;
    // max-width: 400px;
    // max-height: 251px;
    // height: 54vw;
  padding: 20px;
}

:deep(.v-overlay__content) {
    //overflow: hidden !important;
  overflow-y: hidden !important;
  top: 20px !important;
  border-radius: 40px;
}

.card-no-padding .v-card {
  margin: 0 !important;
  padding: 0 !important;
}

:deep(.v-card-text .card_container) {
  padding: 0px;
}

.no-rounded-icon-btn .v-btn__icon {
  border-radius: 0 !important;
}

.v-input--custom-text-input-density .v-field--variant-underlined {
  --v-input-control-height: 30px; //change here
  --v-field-padding-top: 0px;
  --v-field-padding-bottom: 0px;
}

.elevation-1.table_border_radius {
  overflow-y: hidden;
}

:deep(.v-messages .v-messages__message) {
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
  max-width: none;
  //width: auto;
  //position: absolute;
  //left: 0;
  //right: 0;
  width: 200px;
}

//:deep(.v-table.outer .v-table__wrapper) {
//  overflow-y: hidden;
//  max-height: 320px;
//}

:deep(.v-data-table-footer__items-per-page) {
  display: none;
}

:deep(.v-table .v-table__wrapper table thead tr th) {
  height: 46px;
  line-height: 46px;
}

.sticky-card-title {
  //position: -webkit-sticky;
  //position: sticky;
  //top: 50; // 固定在容器顶部
  z-index: 10; // 保证标题在内容上方显示
  background: white; // 避免内容滚动时标题被遮盖
  top: 10px;
  position: relative;
  font-size: 24px;
  font-weight: 600;
  font-family: 'cwTeXYen', sans-serif;
}

.card-container {
  height: 440px;    // 设置明确的高度以允许滚动
  //overflow: auto; // 确保容器可以滚动
  overflow-y: hidden;
}

:deep(.v-data-table-footer) {
  position: relative;
  top: -20px;
}

:deep(.v-overlay__content) {
  border-radius: 0px !important;
  max-height: 320px !important;
  overflow-y: auto !important;

  --v-scrollbar-offset: 0px !important;
  border-radius: 5px !important;
}

:deep(.v-card .v-data-table-footer) {
  padding-top: 0px;
  padding-bottom: 0px;
}

:deep(.v-card .v-data-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.v-card .v-data-table thead th) {
  background-color: white;              // 確保標題背景與卡片一致
  z-index: 2;                               // 提高z-index以確保標題在其他內容之上
}

.sticky-title {
  position: sticky;
  top: 0px;
  background-color: white;
  z-index: 10;
  //padding-top: 10px;
  //padding-bottom: 10px;
}

.v-table.inner thead.sticky-thead tr.inner_header th {
  position: sticky;
  top: 0px;
  background-color: white;
  z-index: 9;
}

.table-container {
  position: relative;         // 讓 sticky 定位相對於這個元素
  max-height: 440px;          // 設定產生滾動條的高度
  overflow-y: auto;           // 允許垂直滾動
}

.red-text {
  color: red;
}

.custom-table {
  border-radius: 0 0 20px 20px;
}

.custom-table theader th {
  background-color: #85aef2;    // 自訂背景顏色
}

.blinking {
  animation: blink-animation 1s steps(5, start) infinite;
}

@keyframes blink-animation {
  to {
    visibility: hidden;
  }
}


.light {
  display: inline-block;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  //margin-bottom: 8px;
  //opacity: 0.2;
  //transition: opacity 0.2s;
  position: relative;
}

.light span {
  transition: opacity 0.2s;
  color: #fff;
  font-size: 24px;
  position: absolute;
  right: 0;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  text-align: center;
  opacity: 0;
  visibility: hidden;
}
.light.active span {
  opacity: 1;
  visibility: visible;
}
.active {
  opacity: 1;
}

.yellow {
  background: #ffff00;
/*
background-color: #ffff00;
width: 32px;
height: 32px;
border-radius: 50%;
*/
}
.green {
  background: green;
}

:deep(.v-data-table-footer) {
  margin-bottom: -10px;
}

.no-footer {
  margin-bottom: 0;           // 沒有頁腳時的底部邊距
}

:deep(.custom-table .v-table__wrapper > table > thead > tr > th.v-data-table__th) {
  background-color: #85aef2;      // 自訂背景顏色
}

:deep(.custom-table th:nth-child(2)), /* 隱藏標題欄 */
:deep(.custom-table td:nth-child(2)) { /* 隱藏數據欄 */
  display: none
}

:deep(.custom-table thead th:nth-child(1)) {
  padding-left: 16px !important;
}

:deep(.custom-table thead th:nth-child(3)) {
  padding-left: 32px !important;
}

:deep(.custom-table thead th:nth-child(4)) {
  padding-left: 40px !important;
}

:deep(.custom-table thead th:nth-child(5)) {
  padding-left: 32px !important;
}
// 資料表
:deep(.custom-table thead th:nth-child(7)) {
  padding-left: 40px !important;
}

// 選擇框
:deep(span.custom-header) {
  display: block;
  width: 80px;      // 設定最小寬度
}

// 輸入欄位 <v-text-field />
:deep(input[type="text"]) {
  min-height: 20px;
  height:20px;
  opacity: 1;
  padding: 0px;
  text-align: center;
  color: red;
  min-width:60px;
  width:60px;
}

:deep(.v-btn-group--density-default.v-btn-group) {
  min-height: 36px;
  height: 36px;
  left: -10px;
  position: relative;
}

//.flip_wrapper {
//  perspective: 800px;
//}

//.flip_btn {
//  position: relative;
//  top: 3px;
//  right: 100px;
//  height: 36px;
//  width: 100px;
//  transform-style: preserve-3d;
//  transition: transform 500ms ease-in-out;
//  transform: translateZ(-20px);
//}

//.flip_btn:hover {
//    transform: rotateX(-90deg) translateY(20px);
//}

//.side {
//  position: absolute;
//  backface-visibility: hidden;
//  width: 100%;
//  height: 100%;
//  display: flex;
//}

//.default-side {
//  transform: translateZ(20px);
//}

//.hover-side {
//  transform: rotateX(90deg) translateZ(20px) translateY(-3px);  // 向上移動 3px;
//}

// 客製化 手推車/AGV切換按鍵
.button-container {
  position: relative;
  width: fit-content;     // 可調整寬度以適應按鈕

  right: 100px;
  top: 0px;
}

.blue-text {
  color: #0d47a1; /* 設置字體顏色為藍色 */
  font-weight: 700;
}
</style>
