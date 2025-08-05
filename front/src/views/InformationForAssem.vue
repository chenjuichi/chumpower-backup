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

  <v-row>
    <v-col cols="6" class="d-flex justify-center align-center pb-0">
      <span style="font-size:24px; font-weight:600; font-family: 'cwTeXYen', sans-serif;">組裝區在製品生產資訊</span>
    </v-col>
    <v-col cols="2" class="d-flex justify-end align-center pb-0">
      <v-btn
        @click="toggleHistory"
        :active="history"
        color="#c39898"
        variant="outlined"

      >
        <v-icon left color="#664343">mdi-history</v-icon>
        歷史紀錄
      </v-btn>
    </v-col>
    <v-col cols="4" class="d-flex justify-start align-center pb-0">
      <v-text-field
        v-model="search"
        label="搜尋"
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        hide-details
        single-line

        density="compact"
      />
    </v-col>
  </v-row>

  <v-row
    class="mt-0 mb-0 row-hidden"
    style="min-height: 48px; height: 48px; flex-wrap: nowrap; position:relative; top:25px; left:5px;"
  >
    <!--日期範圍-->
    <v-col cols="4" class="d-flex justify-end align-center pt-0 pb-0" style="position: relative; left:100px;">
      <Transition name="slide">
        <div v-if="showFields" style="min-width:290px; width:290px;">
          <v-dialog v-model="pick_date_dialog" width="auto">
            <template #activator="{ props }">
              <v-text-field
                v-bind="props"
                label="日期範圍"
                v-model="formattedDateRange"
                :value="formattedDateRange"
                readonly
                variant="underlined"
                density="compact"
                style="margin-top:20px;"
                placeholder="yyyy-mm-dd ~ yyyy-mm-dd"
                prepend-icon="mdi-calendar-check"
                clearable
                @click="pick_date_dialog = true"
                @click:clear="clearDates"
              />
            </template>

            <v-card>
              <v-card-text>
                <v-locale-provider locale="zhHant">
                  <v-date-picker
                    v-model="tempRange"
                    multiple
                    hide-actions
                    hide-header
                    title="選擇日期範圍"

                    :allowed-dates="() => true"
                  />
                </v-locale-provider>
              </v-card-text>
              <v-card-actions class="justify-end">
                <v-btn variant="text" color="grey" @click="onCancel">取消</v-btn>
                <v-btn variant="flat" color="primary" @click="onConfirm">確定</v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </div>
      </Transition>
    </v-col>

    <!--工單範圍-->
    <v-col cols="4" class="d-flex justify-end align-center pt-0 pb-0">
      <Transition name="slide">
        <div style="min-width:290px; width:290px;">
          <v-text-field
            v-if="showFields"
            label="工單範圍"
            variant="outlined"
            v-model="creditCardNumber"
            maxlength="25"
            inputmode="numeric"
            density="compact"
            prepend-icon="mdi-archive-check-outline"
            placeholder="xxxxxxxxxxxx-xxxxxxxxxxxx"
            @input="formatCreditCard"
            style="margin-top:20px; min-width:290px; width:290px;"
          />
        </div>
      </Transition>
    </v-col>

    <!--Excel按鍵-->
    <v-col cols="4" class="d-flex justify-start align-center pt-0 pb-0">
      <div class="flip_btn">
        <v-btn
          color="white"
          style="min-width: 90px; max-height: 34px; border-radius: 6px; border-width:1.5px; border-color:#64B5F6;"
          class="side default-side primary thin mt-1 mx-auto"
          :disable="isInformationEmpty"
          @mouseenter="showFields = true"
        >
          <v-icon left color="green" style="font-weight:700;">mdi-microsoft-excel</v-icon>
          <span style="color:black; font-weight:600;">Excel</span>
        </v-btn>
        <div class="side hover-side">
          <v-btn color="primary" style="position:relative; right:3px; width:60px;" class="mt-n1 mr-15 mx-auto" @click="showFields = false">
            <v-icon left size="24px">mdi-close-circle-outline</v-icon>
            取消
          </v-btn>
          <v-btn color="primary" style="position:relative; left:3px; width:60px;" class="mt-n1 mr-15 mx-auto" @click="exportToExcelFun">
            <v-icon left size="24px">mdi-check-circle-outline</v-icon>
            確定
          </v-btn>
        </div>
      </div>
    </v-col>
  </v-row>

  <v-data-table
    :headers="headers"
    :items="filteredInformations"
    :row-props="getRowProps"
    :search="search"
    :custom-filter="customFilter"
    item-value="order_num"
    class="outer custom-header"
    :style="tableStyle"
    style="min-height: 420px; height: auto;"
    :items-per-page-options="footerOptions"
    items-per-page="5"
    v-model:page="pagination.page"
  >
    <template v-slot:top>
      <v-card style="min-height:100px; overflow:visible; position:relative; top: -20px;">
        <v-card-title class="d-flex align-center pe-2 sticky-card-title" :max-width="dialogWidth" style="width: 100%; ">
          <v-row style="margin-left:3vw;">
            <v-col cols="9">
              <div style="display: flex; justify-content: center; gap: 45px; font-size: 20px; color: blue">
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span style="font-size: 16px;">{{ todayDate }}</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span>工單數</span>
                  <span style="position:relative; top:10px; font-size:30px;">{{ order_count }}</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span>備料送出</span>
                  <v-progress-circular
                    :model-value="progress_value2"
                    :rotate="360"
                    :size="70"
                    :width="8"
                    color="primary"
                  >
                    {{ prepare_count }}
                  </v-progress-circular>
                </div>

                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span>組裝送出</span>
                  <v-progress-circular
                    :model-value="progress_value3"
                    :rotate="360"
                    :size="70"
                    :width="8"
                    color="red"
                  >
                    {{ assemble_count }}
                  </v-progress-circular>
                </div>

                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span>入庫登記</span>
                  <v-progress-circular
                    :model-value="progress_value4"
                    :rotate="360"
                    :size="70"
                    :width="8"
                    color="pink"
                  >
                    {{ warehouse_count }}
                  </v-progress-circular>
                </div>
              </div>
            </v-col>
            <v-col cols="3" />
          </v-row>
          <div class="pa-4 text-center">
            <v-dialog v-model="process_dialog" max-width="1280px">
              <v-card :style="{ maxHeight: boms.length > 5 ? '500px' : 'unset', overflowY: boms.length > 5 ? 'auto' : 'unset' }">
                <v-card-title class="text-h5 sticky-title" style="background-color: #1b4965; color: white;">
                  裝配報工紀錄 -
                  <span style="font-size: 20px;">{{ current_order_num }}</span>
                  <v-fade-transition mode="out-in">
                    <v-btn
                      style="position: relative; right: -550px;"
                      color="success"
                      prepend-icon="mdi-check-circle-outline"

                      text="關閉"
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
                        <th class="text-left"></th>
                        <th class="text-left" style="width:240px;">備料/組裝</th>
                        <th class="text-left" style="width:110px; padding-left:0px; padding-right:0px;">開始時間</th>
                        <th class="text-left" style="width:110px; padding-left:0px; padding-right:0px;">結束時間</th>
                        <th class="text-left">領料數量</th>
                        <th class="text-left">實際耗時(分)</th>
                        <th class="text-left">實際工時(分)</th>
                        <th class="text-left">單件標工(分)</th>
                        <th class="text-left">人員註記</th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="(process_item, index) in processes"
                        :key="process_item.seq_num"
                        :style="{
                          backgroundColor: index % 2 === 0 ? '#ffffff' : '#edf2f4',
                        }"
                      >
                        <td>{{ process_item.seq_num }}</td>
                        <td style="width: 240px;">
                          {{ process_item.process_type }}
                          <span style="color:red">{{ process_item.normal_type }}</span>
                        </td>
                        <td style="width:110px; padding-left:0px; padding-right:0px;">{{ process_item.begin_time }}</td>
                        <td style="width:110px; padding-left:0px; padding-right:0px;">{{ process_item.end_time }}</td>
                        <!--<td>{{ process_item.total_delivery_qty }}</td>-->
                        <td>{{ process_item.process_work_time_qty }}</td>
                        <td>{{ process_item.period_time }}</td>
                        <td>{{ process_item.work_time }}</td>
                        <td>{{ process_item.single_std_time }}</td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-card-text>
              </v-card>
            </v-dialog>
          </div>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '現況進度' (show1_ok) 欄位的表頭 -->
    <template v-slot:header.show1_ok = "{ column }">
      <div
        style="line-height: 1;
        margin: 0; padding: 0;
        display: flex;
        cursor: pointer;
        position: relative; left: 8px;"
      >
        <span>{{ column.title }}</span>
      </div>
      <div
        style="color: #a6a6a6; font-size: 10px; font-weight: 600; text-align: center; line-height: 1; margin-left: -10px;"
      >
        組裝/雷射/檢驗
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: start;">
        <div style="margin-right: 20px;">
          {{ item.order_num }}
        </div>
      </div>
    </template>

    <!-- 自訂 '現況進度' 欄位 -->
    <template v-slot:item.show1_ok="{ item }">
      <div>
        <div style="font-weight:600;">{{ item.show1_ok }}</div>
        <div style="color: #1a1aff; font-size:12px;">{{ item.show2_ok}}</div>
      </div>
    </template>

    <!-- 自訂 '現況備註' 欄位 -->
    <template v-slot:item.show3_ok="{ item }">
      <div style="font-weight:600;">{{ item.show3_ok }}</div>
    </template>

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
        :disabled="!item.isTakeOk && item.whichStation == 1"
        size="small"
        variant="tonal"
        style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"

        @click="toggleExpand(item)"
      >
        詳 情
        <v-icon color="orange-darken-4" end>mdi-open-in-new</v-icon>
      </v-btn>
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
  <!--</v-row>-->
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount ,nextTick } from 'vue';

import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
dayjs.extend(isSameOrBefore);             //啟用 plugin

import { useRoute } from 'vue-router';

import { myMixin } from '../mixins/common.js';

//import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { informations, boms, fileCount }  from '../mixins/crud.js';
import { order_count, prepare_count, assemble_count, warehouse_count, processes }  from '../mixins/crud.js';

import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';
import { apiOperationB } from '../mixins/crudB.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const countExcelFiles = apiOperation('get', '/countExcelFiles');
const listInformations = apiOperation('get', '/listInformations');
const listWorkingOrderStatus = apiOperation('get', '/listWorkingOrderStatus');

const getBoms = apiOperation('post', '/getBoms');
const updateBoms = apiOperation('post', '/updateBoms');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
//const createProcess = apiOperation('post', '/createProcess');
const getProcessesByOrderNum = apiOperation('post', '/getProcessesByOrderNum');

const exportToExcelForAssembleInformation = apiOperation('post', '/exportToExcelForAssembleInformation');

const downloadFile = apiOperationB('post', '/downloadXlsxFile');

//=== component name ==
defineComponent({ name: 'InformationForAssem' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
let intervalId = null;                    // 10秒, 倒數計時器
let intervalIdForProgressCircle = null;   // 5秒, 倒數計時器
const route = useRoute();                 // Initialize router

const showFields = ref(false);            // 用來控制是否顯示額外的excel btn欄位
const pick_date_dialog = ref(false);      // 控制 v-pick-date Dialog 顯示
const selectedRange = ref([])             // 最終選定日期範圍
const tempRange = ref([])                 // 選單中暫存日期範圍

const fromDateStart = ref("");
const fromDateValStart = ref([]);

const creditCardNumber = ref("");
const orderNumRange = ref(["", ""]);      // 用來儲存第一組與第二組的數字

const screenWidth = ref(window.innerWidth);
// 取得今日日期 (格式：YYYY/MM/DD)
const todayDate = ref(new Date().toISOString().split("T")[0].replace(/-/g, "/"));

const footerOptions = [
  { value: 5, title: '5' },
  //{ value: 10, title: '10' },
  //{ value: -1, title: '全部' }
];

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num' },
  { title: '現況進度', sortable: false, key: 'show1_ok', width:110 },
  { title: '現況備註', sortable: false, key: 'show3_ok', width:150 },
  { title: '交期', sortable: false, key: 'delivery_date', width:110 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:90 },
  { title: '現況數量', sortable: false, key: 'delivery_qty', width:90 },
  { title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '', sortable: false, key: 'action' },
];

//const localIp = 'localhost';
//const serverIp = process.env.VUE_SOCKET_SERVER_IP || '192.168.32.50';
//const userId = 'user_chumpower';
// 初始化Socket連接
//const { socket, setupSocketConnection } = useSocketio(localIp, userId);
//const localIP = ref('');
const from_agv_order_num = ref('');
const isBlinking = ref(false);          // 控制按鍵閃爍
const order_num_on_agv=ref('');

const search = ref('');

const history = ref(false);
const currentUser = ref({});

const current_order_num = ref('');

//const showExplore = ref(false);
//const showVirtualTable = ref(false);

const currentStartTime = ref(null);  // 記錄開始時間

const process_dialog = ref(false);

const pagination = reactive({
  itemsPerPage: 5, // 預設值, rows/per page
  page: 1,
});

const wakeLock = ref(null);           // 用於存儲 Wake Lock 物件
const isWakeLockActive = ref(false);  // 是否啟用螢幕鎖定

const selectedFile = ref(null); 						                // 儲存已選擇檔案的名稱
const topPath = ref('C:\\vue\\chumpower\\excel_export'); 	  // 初始路徑
const downloadFilePath = ref('');
const selectedFileName = ref('');						                // 用於追蹤目前選取的檔案名稱

//=== watch ===
setupGetBomsWatcher();

watch(tempRange, (newVal) => {
  console.log('目前選取型別與狀態：',
    newVal.map(d => ({
      value: d,
      type: typeof d,
      isDate: d instanceof Date
    }))
  );
  console.log('✅ 是否為 Date：', newVal.map(d => d instanceof Date));
})

watch(pick_date_dialog, (isOpen) => {
  if (isOpen) {
    if (selectedRange.value.length >= 2) {
      const sorted = [...selectedRange.value].sort((a, b) => new Date(a) - new Date(b))
      tempRange.value = generateDateRange(sorted[0], sorted[sorted.length - 1])
    } else {
      tempRange.value = [...selectedRange.value]
    }
  }
})

watch(
  () => informations.value || [],
  (newVal) => {
    console.log("Updated informations...", newVal);
  },
  { deep: true }
);

watch(fromDateValStart, (val) => {
  console.log("watch(), fromDateValStart:", fromDateValStart.value)

  if (!val || val.length === 0) {
    fromDateStart.value = [];
  } else {
    fromDateStart.value = val.map((date) => formatDate3(date));
  }
  console.log("watch: fromDateStart.value:", fromDateStart.value);
});

watch(selectedFile, (newVal) => {
  if (newVal) {
    console.log("📥 selectedFile 更新，現在下載檔案:", newVal);
    downloadFileFun();
  }
});

//=== computed ===
const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)',
  width: 'min(100%, 1500px)', // 讓表格最多1200px，但不超過螢幕
  minWidth: '700px',           // 避免過小
  maxWidth: '100%',            // 不超過父容器
  //width: '1050px',
  overflowY: 'hidden',
  overflowX: 'auto',
  position: 'relative',
  top: '50px',
  marginBottom: '5px',
}));

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

const dialogWidth = computed(() => (screenWidth.value > 1200 ? '1400px' : '80vw'));

order_count, prepare_count, assemble_count, warehouse_count
const progress_value1 = computed(() => order_count.value);
const progress_value2 = computed(() => order_count.value !=0 ? (prepare_count.value / order_count.value)* 100 : 0 );
const progress_value3 = computed(() => order_count.value !=0 ? (assemble_count.value / order_count.value)* 100 : 0 );
const progress_value4 = computed(() => order_count.value !=0 ? (warehouse_count.value / order_count.value)* 100 : 0 );

// 顯示格式：yyyy-mm-dd ~ yyyy-mm-dd
const formattedDateRange = computed(() => {
  const list = selectedRange.value
  if (list.length === 0) return ''
  const sorted = [...list].sort((a, b) => new Date(a) - new Date(b))
  const start = dayjs(sorted[0]).format('YYYY-MM-DD')
  const end = dayjs(sorted[sorted.length - 1]).format('YYYY-MM-DD')
  return start === end ? start : `${start} ~ ${end}`
})

const isInformationEmpty = computed(() => {
  return informations.value.length === 0;
});

// 計算屬性 - 過濾符合條件的資訊
const filteredInformations = computed(() => {
  return informations.value
  .filter(item => {
    const isWithinDateRange = checkDateInRange(item.delivery_date);
    const isWithinOrderRange = checkOrderInRange(item.order_num);
    return isWithinDateRange && isWithinOrderRange;
  });
});

//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  console.log("裝置像素比 (DPR):", window.devicePixelRatio);

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  //fileCount.value = countExcelFiles();
  //console.log("fileCount:", fileCount.value);

  intervalId = setInterval(listInformationsFun, 10 * 1000);  // 每 10秒鐘調用一次 API
  intervalIdForProgressCircle = setInterval(listWorkingOrderStatusFun, 5 * 1000);  // 每 5秒鐘調用一次 API

  //window.addEventListener('resize', () => {
  //  screenWidth.value = window.innerWidth;
  //});
  window.addEventListener('resize', updateScreenWidth);
  updateScreenWidth(); // 確保初始時執行一次

  document.addEventListener("visibilitychange", handleVisibilityChange);

  /*
  console.log('取得本機ip...');
  try {
    localIP.value = await getLocalIP();
    console.error('本機ip:', localIP.value);
  } catch (err) {
    console.error(err);
  }
  */
  /*
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

        from_agv_order_num.value = data;
        order_num_on_agv.value = "工單:" + data + "物料運送中...";
        //isBlinking.value = true; // 開始按鍵閃爍

        // 定義 materialPayload1
        const materialPayload1 = {
          order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
          record_name: 'show3_ok',
          record_data: 1 // 設為 2，表示備料完成
        };
        await updateMaterial(materialPayload1);
      } else {
        console.log('工單 '+ data + ' 還沒檢料完成!');
        socket.value.emit('station1_order_ng');
        order_num_on_agv.value = '';
      }
    });

    socket.value.on('station1_agv_begin', async () => {
      console.log('AGV暫停, 收到 station1_agv_begin 訊息');

      const materialPayload1 = {
        order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
        record_name: 'show3_ok',
        record_data: 2 // 設為 2，表示備料完成
      };
      await updateMaterial(materialPayload1);
    })

    socket.value.on('station1_agv_end', async () => {
      console.log('AGV暫停, 收到 station1_agv_end 訊息');

      const materialPayload1 = {
        order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
        show1_ok: 2,
        show2_ok: 20, // 設為 2，表示備料完成
        show3_ok: 2,
        whichStation: 2,
      };
      await updateMaterialRecord(materialPayload1);

      isBlinking.value = false; // 停止按鍵閃爍
      order_num_on_agv.value = '';
    });
  } catch (error) {
    console.error('Socket連接失敗:', error);
  }
  */
});

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  clearInterval(intervalId);

  clearInterval(intervalIdForProgressCircle);

  window.removeEventListener('resize', updateScreenWidth);
});

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...", currentUser.value)

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

onBeforeUnmount(() => {
  // 卸載時釋放鎖定
  releaseWakeLock();
  document.removeEventListener("visibilitychange", handleVisibilityChange);
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...")

    await listInformations();

    await listWorkingOrderStatus();
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

// 檢查 item.delivery_date 是否落在 fromDateValStart 範圍內
const checkDateInRange = (date) => {
  if (!fromDateValStart.value.length) return true; // 沒選日期 -> 全部顯示

  const formattedDates = fromDateValStart.value.map(d => formatDate3(d));
  const minDate = formattedDates[0];
  const maxDate = formattedDates[formattedDates.length - 1];

  return date >= minDate && date <= maxDate;
};

// 檢查 item.order_num 是否落在 orderNumRange 內
const checkOrderInRange = (orderNum) => {
  if (!orderNumRange.value[0] && !orderNumRange.value[1]) return true; // 沒輸入範圍 -> 全部顯示

  const minOrder = orderNumRange.value[0];
  const maxOrder = orderNumRange.value[1] || minOrder; // 若只輸入一組，則上下限相同
  return orderNum >= minOrder && orderNum <= maxOrder;
};


const exportToExcelFun = async () => {
  console.log('InformationForAssem.vue, exportToExcelFun()...');

  //const obj = {
  //  order_num: '訂單編號',
  //  comment: '說明',
  //  delivery_date: '交期',
  //  req_qty: '訂單數量',
  //  delivery_qty: '現況數量',
  //};

  // 先取得 data table 內的 filteredInformations
  let filteredData = filteredInformations.value;
  console.log("1. filteredData: ", filteredData);

  // 再手動應用 customFilter()
  if (search.value) {
    filteredData = filteredData.filter(item => customFilter(search.value, item));
  }
  console.log("2. filteredData: ", filteredData);

  // 確保欄位名稱與 obj 一致
  let updatedData = filteredData.map(item => ({
    order_num: item.order_num ?? '',
    comment: item.comment ?? '',
    delivery_date: item.delivery_date ?? '',
    req_qty: item.req_qty ?? '',
    delivery_qty: item.delivery_qty ?? '',

  }));
  console.log("3. updatedData: ", updatedData);

  //let object_Desserts = [obj, ...updatedData];
  //console.log("4. object_Desserts: ", object_Desserts);

  let payload = {
    blocks: updatedData,
    //blocks: object_Desserts,
    //count: object_Desserts.length,
    name: currentUser.value.name,
  };

  try {
    const export_file_data = await exportToExcelForAssembleInformation(payload);
    console.log("export_file_dat:", export_file_data);

    if (export_file_data.status) {
      selectedFile.value = export_file_data.file_name;
      downloadFilePath.value = export_file_data.message;
      console.log("✅ 更新後的 selectedFile:", selectedFile.value); // 確保它不是 null

      //let temp_message = `庫存記錄(${export_file_data.message})轉檔完成!`;
      let temp_message = '轉檔完成!';
      showSnackbar(temp_message, '#008184');
    } else {
      showSnackbar(excel_file_data.message, 'red accent-2');
    }
  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("存檔錯誤!", 'red accent-2');
  }
  showFields.value = false;
};

const downloadFileFun = async () => {
	console.log("downloadFileFun()...", downloadFilePath.value)

	const payload = {
    filepath: downloadFilePath.value,
	};

	try {
		const response = await downloadFile(payload);

		console.log("response:", response);                   // 檢查是否為 Blob
		console.log("Response headers:", response.headers);   // 檢查headers

		selectedFileName.value = null;

		if (response.data instanceof Blob) {
			const fileName = response.headers['X-File-Name'] || response.headers['x-file-name'] || `${selectedFile.value}`;
      console.log('下載的檔案名稱:', fileName);

			// 建立下載鏈接並觸發下載
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      //link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
			return true; 													// 成功下載
    }
  } catch (error) {
    showSnackbar('下載檔案錯誤！', 'red accent-2');
    console.error('下載檔案錯誤:', error);
  }
};

const listInformationsFun = async () => {
  await listInformations();
};

const listWorkingOrderStatusFun = async () => {
  await listWorkingOrderStatus();
};

const customFilter = (value, search, item) => {
  //const customFilter = (search, item) => {
    if (!search) return true;
  search = search.toLowerCase();

  return Object.values(item).some(val =>
    String(val).toLowerCase().includes(search)
  );
};

const toggleHistory = async () => {
  history.value = !history.value;
  await getInformationsByHistoryFun();
};

const getInformationsByHistoryFun = async () => {
  let payload = {
    history_flag: history.value,
  };
  await getInformationsByHistory(payload);
}

// 監聽視窗變化
const updateScreenWidth = () => {
  screenWidth.value = window.innerWidth;
};

const getRowProps = (item, index) => {
  // 偶數列與奇數列高度不同
  const backgroundColor = item.index % 2 === 0 ? '#ffffff' : '#edf2f4';

  return {
    style: {
      backgroundColor,
    },
  };
};

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

// 請求螢幕鎖定
const requestWakeLock = async () => {
  try {
    if ("wakeLock" in navigator) {
      wakeLock.value = await navigator.wakeLock.request("screen");
      isWakeLockActive.value = true;
      console.log("✅ 螢幕鎖定成功");

      // 監聽鎖定被釋放的情況
      wakeLock.value.addEventListener("release", () => {
        isWakeLockActive.value = false;
        console.log("⚠️ 螢幕鎖定已解除");
      });
    } else {
      console.warn("❌ 你的瀏覽器不支援 Wake Lock API");
    }
  } catch (err) {
    console.error("❌ 無法鎖定螢幕:", err);
  }
};

// 釋放螢幕鎖定
const releaseWakeLock = async () => {
  if (wakeLock.value) {
    await wakeLock.value.release();
    wakeLock.value = null;
    isWakeLockActive.value = false;
    console.log("🔓 螢幕鎖定已釋放");
  }
};

// 當網頁可見性變化時，確保鎖定不會被打斷
const handleVisibilityChange = () => {
  if (document.visibilityState === "visible" && isWakeLockActive.value) {
    requestWakeLock();
  }
};
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

  current_order_num.value = item.order_num;
  let payload = {
    order_num: item.order_num,
  };
  await getProcessesByOrderNum(payload);
  console.log("processes:", processes.value);

  process_dialog.value = true;
};

const updateItem = async () => {              //編輯 bom, material及process後端table資料
  console.log("updateItem()...");
  /*
  let my_material_orderNum = boms.value[0].order_num;

  let endTime = new Date();                                               // 記錄當前結束時間
  let periodTime = calculatePeriodTime(currentStartTime.value, endTime);  // 計算時間間隔
  // 將 currentStartTime, endTime 轉換為字串格式 yyyy-mm-dd hh:mm:ss
  let formattedStartTime = formatDateTime(currentStartTime.value);
  let formattedEndTime = formatDateTime(endTime);

  // 使用 .some() 檢查是否有任何 `receive` 為 false 的項目，若有則將 `take_out` 設為 false
  let take_out = !boms.value.some(bom => !bom.receive);

  // 1. 更新 boms 資料
  const response0 = await updateBoms(boms.value);
  if (!response0) {
    showSnackbar(response0.message, 'red accent-2');
    dialog.value = false;
    return;
  }

  if (take_out) {                     // 該筆訂單檢料完成
    const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
      order_num: my_material_orderNum,
      record_name: 'show2_ok',
      record_data: 2                  // 設為 2，表示備料完成
    };
    await updateMaterial(materialPayload1);
    //const response1 = await updateMaterial(materialPayload1);
    //if (!response1) {
    //  showSnackbar(response1.message, 'red accent-2');
    //  dialog.value = false;
    //  return;
    //}

    const materialPayload11 = {        // 2. 更新 materials 資料，isTakeOk = true
      order_num: my_material_orderNum,
      record_name: 'isTakeOk',
      record_data: true
    };
    await updateMaterial(materialPayload11);
    //const response11 = await updateMaterial(materialPayload11);
    //if (!response11) {
    //  showSnackbar(response11.message, 'red accent-2');
    //  dialog.value = false;
    //  return;
    //}

    let myMaterial = materials.value.find(m => m.order_num == my_material_orderNum);
    myMaterial.isTakeOk = true;    // 更新該項目的 isTakeOk 為 true
    myMaterial.show2_ok = 2;  // 更新 bom_agv_status

    console.log("Formatted Start Time:", formattedStartTime);
    console.log("Formatted End Time:", formattedEndTime);
    console.log("Period time:", periodTime);

    // 4. 新增 後端 process的相應項目
    const processPayload = {
      begin_time: formattedStartTime,
      end_time: formattedEndTime,
      periodTime: periodTime,
      user_id: currentUser.value.empID,
      order_num: my_material_orderNum,
      process_type: 1,
      //process_status: 2,
    };

    const response3 = await createProcess(processPayload);
    if (!response3) {
      showSnackbar(response3.message, 'red accent-2');
      dialog.value = false;
      return;
    }

    listMaterials();
  }
  */
  process_dialog.value = false;
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

//const callAGV = async () => {
//  console.log("callAGV()...")
  /*
  const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
    order_num: my_material_orderNum,
    record_name: 'show3_ok',
    record_data: 1                  // 設為 2，表示備料完成
  };

  await updateMaterial(materialPayload1);
  */
//  isBlinking.value = true; // 開始按鍵閃爍
//  socket.value.emit('station1_call');
//};
//
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
const formatDate3 = (date) => {

  if (!date) return null;
  const localDate = new Date(date);
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset()); // 修正時區
  //return localDate.toISOString().split("T")[0]; // yyyy-mm-dd
  const isoDate = localDate.toISOString().split("T")[0]; // yyyy-mm-dd

  const [year, month, day] = isoDate.split("-");
  //console.log("formatDate3: ", `${year}-${month}-${day}`)
  return `${year}-${month}-${day}`;
};


const formatCreditCard = () => {
  // 移除所有 "-"，確保格式統一
  let realNumber = creditCardNumber.value.replace(/-/g, "");

  // 只保留最多 24 位數 (兩組 12 位數)
  realNumber = realNumber.slice(0, 24);

  // 每 12 位數加上 "-"
  let dashedNumber = realNumber.match(/.{1,12}/g);
  creditCardNumber.value = dashedNumber ? dashedNumber.join("-") : realNumber;

  // 儲存第一組與第二組數字
  orderNumRange.value = dashedNumber || ["", ""];
};


const clearDates = () => {
  selectedRange.value = []
  tempRange.value = []
}

// 點「確定」按鈕
const onConfirm = () => {
  const rawDates = tempRange.value.map(d => dayjs(d))
  if (rawDates.length === 1) {
    selectedRange.value = [rawDates[0].toDate()]
  } else if (rawDates.length >= 2) {
    const sorted = rawDates.sort((a, b) => a.unix() - b.unix())
    selectedRange.value = generateDateRange(sorted[0], sorted[sorted.length - 1])
  }
  pick_date_dialog.value = false
}

// 點「取消」按鈕
const onCancel = () => {
  console.log('❌ 取消選擇');

  if (selectedRange.value.length >= 1) {
    const [start, end] = selectedRange.value.length === 1
      ? [selectedRange.value[0], selectedRange.value[0]]
      : [selectedRange.value[0], selectedRange.value[1]]

    tempRange.value = generateDateRange(start, end)
  } else {
    tempRange.value = []
  }
  pick_date_dialog.value = false
}

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
:deep(.v-table.outer .v-table__wrapper) {
  overflow-y: hidden;
  max-height: 320px;
}

//:deep(.v-data-table-footer__items-per-page) {
//  display: none;
//}

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

//:deep(.v-card .v-data-table-footer) {
//  padding-top: 0px;
//  padding-bottom: 0px;
//}

:deep(.v-card .v-data-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.v-card .v-data-table thead th) {
  background-color: white;  // 確保標題背景與卡片一致
  z-index: 2;                 // 提高z-index以確保標題在其他內容之上
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

//.table-container {
//  position: relative; /* 讓 sticky 定位相對於這個元素 */
//  max-height: 440px; /* 設定合適的高度來產生滾動條 */
//  overflow-y: auto; /* 允許垂直滾動 */
//}

.red-text {
  color: red;
}

//:deep(.v-input__control) {
//left: 150px;
//position: relative;
//width: 250px;
//}

:deep(.v-field__field) {
  min-height : 20px;
  height: 34px;
}

:deep(.v-progress-circular__content) {
  font-size: 25px;
}

//:deep(.v-data-table-footer__info) {
//min-height : 30px;
//height: 40px;
//}

.custom-header theader th {
  background-color: #85aef2; /* 自訂背景顏色 */
}

.blinking {
  animation: blink-animation 1s steps(5, start) infinite;
}

@keyframes blink-animation {
  to {
    visibility: hidden;
  }
}

// 預設 left: 180px
.search-field {
  position: relative;
  top: -20px;
  left: 180px;
  min-height: 10px;
  height: 10px;
}

// 小螢幕 調整 left
@media (max-width: 1600px) {
  .search-field {
    left: 140px;
  }
}

// 大螢幕 調整 left
@media (min-width: 1920px) {
  .search-field {
    left: 220px;
  }
}

//===

.slide-enter-from
{
  transform: translateX(-100%);
}

.slide-leave-to {
  transform: translateX(100%);
}

//===過場特效

.flip_btn {
  position: relative;
  top: -5px;
  left: 30px;
  height: 20px;
  width: 130px;
  transform-style: preserve-3d;
  transition: transform 500ms ease-in-out;
  transform: translateZ(-20px);
}

.flip_btn:hover {
  transform: rotateX(-90deg) translateY(20px);
}

.side {
  position: absolute;
  backface-visibility: hidden;
  width: 130px;
  //width: 100%;
  height: 100%;
  display: flex;
}

.default-side {
  transform: translateZ(20px);
}

.hover-side {
  transform: rotateX(90deg) translateZ(20px);
}

</style>
