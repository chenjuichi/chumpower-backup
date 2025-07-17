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

  <DraggablePanel :initX="panelX" :initY="panelY" :isDraggable="true">
    <LedLights :activeColor="activeColor" />
  </DraggablePanel>

  <!-- data table -->
  <v-data-table
    :headers="headers"
    :items="warehouses"
    :row-props="getRowProps"
    :search="search"
    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"

    item-value="id"
    show-select
    :value="selectedItems"

    class="elevation-10 custom-table"
    :items-per-page-options="footerOptions"
    items-per-page="5"
    v-model:page="pagination.page"
    items-per-page-text="每頁的資料筆數"
  >

    <!-- 客製化 '選擇框' 欄位表頭 -->
    <template v-slot:header.data-table-select>
      <span class="custom-header">入庫</span>
    </template>

    <!-- 自定義每行的選擇框 -->
    <template v-slot:item.data-table-select="{ internalItem }">
      <v-checkbox-btn
        :model-value="isSelected(internalItem)"
        :disabled="internalItem.raw.allOk_qty == 0 || internalItem.raw.isTakeOk"
        color="primary"
        @update:model-value="toggleSelect(internalItem)"
        :class="{ 'blue-text': internalItem.raw.isTakeOk }"
      />
    </template>

    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="d-flex align-center pe-2" style="font-weight:700; height:86px;">
          <v-row>
            <v-col cols="12" md="2">
              成品區入庫資訊
            </v-col>

            <!--客製化 歷史紀錄按鍵-->
            <v-col cols="12" md="2">
              <v-btn
                @click="toggleHistory"
                :active="history"
                color="#c39898"
                variant="outlined"
                style="position: relative; top: 0px; font-weight: 700;"
              >
                <v-icon left color="#664343">mdi-history</v-icon>
                歷史紀錄
              </v-btn>
            </v-col>

            <!--客製化 入庫登記按鍵-->
            <v-col cols="12" md="2">
              <v-btn
                :disabled="c_isBlinking"
                color="primary"
                variant="outlined"
                style="position: relative; right: 75px; top: 0px; font-weight: 700;"
                @click="callAGV"
              >
                <v-icon left color="blue">mdi-view-grid-plus-outline</v-icon>
                <span>入庫登記</span>
              </v-btn>
            </v-col>

            <!--客製化 搜尋輸入框-->
            <v-col cols="12" md="2">
              <v-text-field
                v-model="search"
                label="搜尋"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                hide-details
                single-line
                style="position: relative; top: 10px; right:120px;"

              />
            </v-col>

             <!-- 客製化barcode輸入 -->
            <v-col cols="12" md="4">
              <v-text-field
                v-model="bar_code"
                :value="bar_code"
                ref="barcodeInput"
                @keyup.enter="handleBarCode"
                hide-details="auto"
                prepend-icon="mdi-barcode"
                style="min-width:200px; width:200px; position: relative; top: 35px;"
                class="align-center"
                density="compact"
              />
            </v-col>
          </v-row>

          <!-- 成品區來料異常備註 -->
          <div class="pa-4 text-center">
            <v-dialog v-model="abnormalDialog" max-width="500">
              <!--取消最大高度限制，讓卡片內容可以顯示完整-->
              <!--消自動捲軸，完全依內容高度決定是否超出-->
              <v-card :style="{ maxHeight: 'unset', overflowY: 'unset' }">
                <v-card-title class="text-h6 sticky-title text-center" style="background-color: #1b4965; color: white;">
                  成品區來料異常備註
                </v-card-title>

                <v-card-text>
                  <!-- 若 Incoming1_Abnormal 為 true，顯示第1與第2行 -->
                  <template v-if="abnormalDialog_display">
                    <v-row style="margin-bottom: 4px;" dense justify="center">
                      <v-col cols="4" class="pa-0">訂單編號</v-col>
                      <v-col cols="4" class="pa-0">來料數量</v-col>
                      <v-col cols="4" class="pa-0">實際數量</v-col>
                    </v-row>
                    <v-row dense>
                      <v-col cols="4" class="pa-0">{{ abnormalDialog_order_num }}</v-col>
                      <v-col cols="4" class="pa-0">{{ abnormalDialog_delivery_qty }}</v-col>
                      <v-col cols="4" class="pa-0">
                        <v-text-field
                          v-model="abnormalDialog_new_must_receive_qty"
                          variant="underlined"
                          style="max-width: 60px;"
                        />
                      </v-col>
                    </v-row>
                  </template>
                  <!-- 顯示第3行 -->
                  <template v-else>
                    <v-row style="margin-bottom: 4px;" dense justify="center">
                      {{ abnormalDialog_message }}
                    </v-row>
                  </template>
                </v-card-text>

                <v-card-actions class="justify-center">
                  <v-btn
                    color="success"
                    prepend-icon="mdi-content-save"

                    text="確定"
                    class="text-none"
                    @click="createAbnormalFun"
                    variant="flat"
                  />
                  <v-btn
                    color="error"
                    prepend-icon="mdi-close"
                    text="取消"
                    class="text-none"
                    @click="abnormalDialog = false"
                    variant="flat"
                  />
                </v-card-actions>
              </v-card>
            </v-dialog>
          </div>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '需求數量' (req_qty) 欄位表頭 -->
  <!--
    <template v-slot:header.req_qty="{ column }">
      <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
        <div>{{ column.title }}</div>
        <div style="font-size:12px; margin-top: 5px;">(交貨日期)</div>
      </div>
    </template>
  -->
    <!-- 客製化 '需求數量' (req_qty) 欄位的表頭 2025-06-13 modify, 改順序 -->
<!--
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div>需求</div>
        <div>數量</div>
      </div>
    </template>
  -->
    <!-- 客製化 '到庫數量' (delivery_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
  <!--
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div>到庫</div>
        <div>數量</div>
      </div>
    </template>
  -->

    <!-- 客製化 '應入庫數量' (must_allOk_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
  <!--
    <template v-slot:header.must_allOk_qty="{ column }">
      <div style="text-align: center;">
        <div>應入庫</div>
        <div>數量</div>
      </div>
    </template>
  -->

    <!-- 客製化 '入庫數量' (allOk_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
  <!--
    <template v-slot:header.allOk_qty="{ column }">
      <div style="text-align: center;">
        <div>入庫</div>
        <div>數量</div>
      </div>
    </template>
  -->
    <!-- 自訂 '訂單編號' 欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: center;">
        <!-- Order Info -->
        <div style="color: red; margin-right: 2px;" v-if="item.isTakeOk && item.isLackMaterial != 99">
          {{ item.order_num }}&nbsp;&nbsp;
          <span style="font-weight: 700; font-size: 16px;">缺料</span>
        </div> <!--檢料完成-->
        <div style="color: blue; margin-right: 20px;" v-else-if="item.isTakeOk && item.isLackMaterial == 99">
          {{ item.order_num }}
        </div> <!--檢料完成-->
        <div style="margin-right: 20px;" v-else>
          {{ item.order_num }}
        </div>
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

    <!-- 自訂 '需求數量' (req_qty) 欄位 -->
  <!-- 2025-06-13 mark, 改順序
    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.date }}</div>
      </div>
    </template>
  -->
    <!-- 自訂 '說明' 欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>-->
      </div>
    </template>

    <!-- 自訂 '詳情' 按鍵 -->
    <!--
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
    -->
    <!-- 自訂 '到庫數量' 輸入欄位 -->
  <!-- 2025-06-13 mark, 改順序
    <template v-slot:item.delivery_qty="{ item }">
      <div>{{ item.delivery_qty }}</div>
    </template>
  -->
    <!-- 自訂 應入庫數量 欄位資料欄位 -->
    <template v-slot:item.must_allOk_qty="{ item }">
      <div style="display: flex; align-items: center;">
        <v-icon
          style="transition: opacity 0.3s ease, visibility 0.3s ease;  margin-left: -10px;"
          :style="{ opacity: (currentUser.perm == 1 || currentUser.perm == 2)  ? 1 : 0, visibility: (currentUser.perm == 1 || currentUser.perm == 2) ? 'visible' : 'hidden' }"
          @click="addAbnormalInMaterial(item)"
          size="16"
          class="mr-2"
          :color="item.Incoming2_Abnormal ? 'light-blue lighten-3':'red lighten-4'"
        >
          mdi-bell-plus
        </v-icon>
        <span style="margin-left: 15px;">
          {{ item.must_allOk_qty }}
        </span>
      </div>
    </template>

    <!-- 自訂 '入庫數量' 輸入欄位 -->
    <template v-slot:item.allOk_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
          v-model="item.allOk_qty"
          dense
          hide-details
          style="max-width: 60px; text-align: center; z-index: 1;"
          :id="`allOkQtyID-${item.id}`"
          @keydown="handleKeyDown"
          @update:modelValue="checkQtyField(item)"
          @update:focused="(focused) => checkTextEditField(focused, item)"
          @keyup.enter="updateItem2(item)"
          :disabled="selectedItems.includes(item.id) || item.isTakeOk"
          :style="{
            '--input-text-color': (item.isError || item.allOk_qty!=0) ? 'red' : 'black'  // 動態設置 CSS 變數
          }"
        />
        <span
          v-show="item.tooltipVisible"
          style=" position: absolute;
                  left: 20px;
                  top: -15px;
                  z-index: 2;
                  background-color: transparent;
                  padding: 0;
                  min-width: 120px;
                  white-space: nowrap;
                  color:red;
                  text-align: left;
                  font-weight: 600;
                  font-size: 12px;"
        >
          {{ delivery_qty_alarm }}
        </span>
      </div>
    <!--
      <div v-show="item.isTakeOk" style=" position: relative; left: -20px; top: -5px; font-weight: 400; font-size: 10px;">
        入庫日期
      </div>
    -->
    </template>

    <!-- 自訂 data table 在沒有資料時, 畫面的顯示資訊 -->
    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';

import draggable from 'vuedraggable'
import { useRoute } from 'vue-router';

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { desserts2 }  from '../mixins/crud.js';
import { materials, warehouses, boms, currentBoms, currentAGV, material_copy_id ,socket_server_ip, fileCount }  from '../mixins/crud.js';
//import { setupListUsersWatcher }  from '../mixins/crud.js';
import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
const countExcelFiles = apiOperation('get', '/countExcelFiles');
//const listWarehouseForAssemble = apiOperation('get', '/listWarehouseForAssemble');
const listUsers2 = apiOperation('get', '/listUsers2');
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

const getBoms = apiOperation('post', '/getBoms');
const getAGV = apiOperation('post', '/getAGV');
//const updateBoms = apiOperation('post', '/updateBoms');
const updateMaterial = apiOperation('post', '/updateMaterial');
const copyMaterial = apiOperation('post', '/copyMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const updateAGV = apiOperation('post', '/updateAGV');
const modifyExcelFiles = apiOperation('post', '/modifyExcelFiles');
const updateModifyMaterialAndBoms = apiOperation('post', '/updateModifyMaterialAndBoms');
const getWarehouseForAssembleByHistory = apiOperation('post', '/getWarehouseForAssembleByHistory');

//=== component name ==
defineComponent({ name: 'WarehouseForAssemble' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const panelX = ref(810);
const panelY = ref(11);
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

const screenSizeInInches = ref(null);

const bar_code = ref('');
const barcodeInput = ref(null);

const toggle_exclusive = ref(2);              // 控制選擇的按鈕, 預設AGV

const editDialogBtnDisable = ref(true);

const isVisible = ref(true);                  // 設定初始狀態為顯示
const isFlashLed = ref(false);                // 控制紅黃綠燈是否閃爍
let intervalIdForLed = null;
const background = ref('#ffff00');
const isCallAGV = ref(false);                 // 確認是否已經按了callAGV按鍵, true:已經按鍵了, 不能重複按鍵
const showMenu = ref(false);                  // 控制員工選單顯示

const fromDateMenu = ref(false);              // 日期menu 打開/關閉

const selectedEmployee = ref(null);

const selectedId = ref(0);
const selectedOrderNum = ref(null);
const selectedReqQty = ref(null);
const selectedDate = ref(null);

const fromDateVal = ref('');

const placeholderTextForEmployee = ref('請選擇員工');
const placeholderTextForOrderNum = ref('請選擇工單');
const inputSelectEmployee = ref(null);
const inputSelectOrderNum = ref(null);

let intervalId = null;                        // 10分鐘, 倒數計時器

const route = useRoute();                     // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'id', width: 0, class: 'hidden-column' },
  { title: '訂單編號', sortable: true, key: 'order_num', width:150 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:110 },               // 2025-06-13 modify, 改順序
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:300 },  // 2025-06-13 modify, 改順序
  { title: '交期', align: 'start', sortable: false, key: 'date', width:110 },     // 2025-06-13 add, 改順序
  { title: '到庫數量', sortable: false, key: 'delivery_qty', width:110 },          // 2025-06-13 modify, 改順序
  { title: '應入庫數量', sortable: false, key: 'must_allOk_qty', width:110 },      // 2025-06-13 add, 改順序
  { title: '入庫數量', sortable: false, key: 'allOk_qty', width:110 },             // 2025-06-13 modify, 改順序
];

const search = ref('');

const history = ref(false);

//const modify_boms = ref([]);
//const modify_file_name = ref('');

const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)
//const inputValueForItems = ref([]); // 儲存輸入的值

const inputIDs = ref([]);

//const localIp = 'localhost';
//const serverIp = process.env.VUE_SOCKET_SERVER_IP || '192.168.0.13';
//const serverIp = '192.168.0.13';
//const serverIp = process.env.VUE_SOCKET_SERVER_IP
const userId = 'user_chumpower';
const clientAppName = 'WarehouseForAssemble';

//console.log("serverIp:", serverIp)
// 初始化Socket連接
//const { socket, setupSocketConnection } = useSocketio(localIp, userId);
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);

const delivery_qty_alarm = ref('');

//const localIP = ref('');
//const from_agv_input_order_num = ref('');
const isBlinking = ref(false);          // 控制按鍵閃爍
//const order_num_on_agv_blink=ref('');

const currentUser = ref({});
const componentKey = ref(0)       // key 值用於強制重新渲染

const editDialog = ref(false);
const enableDialogBtn = ref(false);

const current_cell = ref(null);

const currentStartTime = ref(null);   // 記錄開始時間

const agv1StartTime = ref(null);      //等待agv計時開始
const agv1EndTime = ref(null);
const agv2StartTime = ref(null);      //運行agv計時開始
const agv2EndTime = ref(null);

const dialog = ref(false);

const selectedItem = ref(null); // 儲存當前點擊的記錄

const pagination = reactive({
  itemsPerPage: 5, // 預設值, rows/per page
  page: 1
});

// 定義 facet 列表
//const allFacets = ref(['Facet 2', 'Facet 3', 'Facet 5']);
//const userFacets = ref(['Facet 1', 'Facet 4']);

const abnormalDialogBtnDisable = ref(true);
const abnormalDialog = ref(false);
const abnormalDialog_order_num = ref('');
const abnormalDialog_delivery_qty = ref('');
const abnormalDialog_must_receive_qty = ref('');
const abnormalDialog_new_must_receive_qty = ref('');
const abnormalDialog_message = ref('');
const abnormalDialog_display = ref(true);

const abnormalDialog_record = ref(null);

//=== watch ===
setupGetBomsWatcher();

//setupListUsersWatcher();

// 監視 selectedItems 的變化，並將其儲存到 localStorage
watch(selectedItems, (newItems) => {
  console.log("watch(), newItems:", newItems)
  localStorage.setItem('selectedItems', JSON.stringify(newItems));
  },
  { deep: true }
);

// 監視 history 的變化，並將其儲存到 localStorage
watch(history, (newItems) => {
  console.log("watch(), newItems:", newItems)
  localStorage.setItem('history', JSON.stringify(newItems));
  },
  { deep: true }
);

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

//=== computed ===
const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
const formatWeekday = computed(() => {
return (day) => {
  console.log('day:', day); // 調試輸出
  return weekdays[day];
};
});

const formattedDesserts = computed(() =>
desserts2.value.map(emp => ({
  ...emp,
  display: `${emp.emp_id} ${emp.emp_name}`,
}))
);

const c_isBlinking = computed(() => selectedItems.value.length === 0);

const containerStyle = computed(() => ({
bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

// 顯示格式化日期
const formattedDate = computed(() => {
return fromDateVal.value ? fromDateVal.value.toISOString().split('T')[0] : ''; // 自動格式化
});

//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  //const dpiEstimate = 96 * dpi;
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);

  if (screenSizeInInches.value != null) {
    panelX.value = screenSizeInInches.value > 20 ? 1290 : 810;
    panelY.value = screenSizeInInches.value > 20 ? 11 : 11;
  }
  //+++

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  intervalId = setInterval(getWarehouseForAssembleByHistoryFun, 10 * 1000);  // 每 10秒鐘調用一次 API

  // 設定紅黃綠燈閃爍週期
  intervalIdForLed = setInterval(() => {
    isVisible.value = !isVisible.value;  // 每0.5秒切換顯示狀態
  }, 500);

  isBlinking.value = selectedItems.value.length == 0 ? true:false;

  // 從 localStorage 中恢復 selectedItems
  let savedItems = localStorage.getItem('selectedItems');
  if (savedItems) {
    selectedItems.value = JSON.parse(savedItems);
  }

  // 從 localStorage 中恢復 history
  savedItems = localStorage.getItem('history');
  if (savedItems) {
    history.value = JSON.parse(savedItems);
  }

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }


  //處理socket連線
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();

    socket.value.on('station3_loading_ready', async(data) => {
      //const num = parseInt(data.message, 10);

      activeColor.value='yellow';  // 物料進站

      //if ([1, 2, 3].includes(num)) {
      //  const temp_msg = `物料已經進入第${num}號裝卸站!`;
      //  console.warn(temp_msg);
      //  //activeColor.value='yello';  // 物料進站
      //  //showSnackbar(temp_msg, 'yellow lighten-5');
      //} else {
      //  console.error('接收到不合法的裝卸站號碼:', data.message);
      //}
    });

    socket.value.on('station3_agv_begin', async () => {
      activeColor.value='SeaGreen';     // 物料出站
    })

    socket.value.on('station1_agv_end', async (data) => {
      activeColor.value='DarkOrange';   // 物料送達組裝區
    })

    socket.value.on('station3_agv_ready', async () => {
      activeColor.value='blue';         // 機器人進入成品區
    })

    /*
    if (!savedItems) {
      console.log('送出 agv_reset 指令');
      socket.value.emit('agv_reset');
    }
    */

    /*
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
    */
    /*
    socket.value.on('station1_agv_start', async () => {
      console.log('AGV 運行任務開始，press Start按鍵, 收到 station1_agv_start 訊息');

      let payload = {};
      // 依據每個 item 的 id 進行資料更新
      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);
        payload = {
          id: item,
          record_name: 'show3_ok',
          record_data: 16,          // agv start
        };
        //await updateMaterial(materialPayload1);
        try {
          await updateMaterial(payload);
          console.log(`資料更新成功，id: ${item}`);
        } catch (error) {
          console.error(`資料更新失敗，id: ${item}`, error);
        }
      });
    });

    socket.value.on('station1_agv_begin', async () => {
      console.log('AGV暫停, 收到 station1_agv_begin 訊息');

      let payload = {};
      // 記錄agv在站與站之間運行開始時間
      agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2StartTime.value);

      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        payload = {
          id: item,
          record_name: 'show3_ok',
          record_data: 2      // 設為 2，agv移動至組裝區中
        };
        try {
          await updateMaterial(payload);
          console.log(`資料更新成功，id: ${item}`);
        } catch (error) {
          console.error(`資料更新失敗，id: ${item}`, error);
        }
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 2,      // 行走中
        station:  2,    // 行走至組裝區
      };
      await updateAGV(payload);

      background.value='#10e810'
    })

    socket.value.on('station2_agv_end', async () => {
      console.log('收到 station2_agv_end 訊息, AGV已到達組裝區!');

      // 記錄agv在站與站之間運行結束時間
      agv2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2EndTime.value);

      let payload = {};

      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);
        payload = {
          id: item,
          show1_ok: 2,      //組裝站
          show2_ok: 3,      //未組裝
          show3_ok: 3,      //等待組裝中
          whichStation: 2,  //目標途程:組裝站
        };
        await updateMaterialRecord(payload);
      });
      console.log('agv_end 處理步驟1...');

      let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv2StartTime.value);
      let formattedEndTime = formatDateTime(agv2EndTime.value);
      console.log("AGV 運行 Start Time:", formattedStartTime);
      console.log("AGV 運行 End Time:", formattedEndTime);
      console.log("AGV 運行 Period time:", agv2PeriodTime);

      //let payload1 = {};
      //let payload2 = {};
      //let payload_new = {};

      console.log('agv_end 處理步驟2...');
      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        let myMaterial = materials.value.find(m => m.id == item);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv2PeriodTime,
          user_id: 'AGV1-2',                        //在備料區('AGV1'), 呼叫AGV的運行時間('-2'), 即簡稱AGV1-2
          order_num: myMaterial.order_num,
          id: myMaterial.id,                        //2025-02-24 add
          process_type: 2,                          //在組裝區
        };
        await createProcess(payload);
        console.log('步驟2-1...');

        //紀錄該筆的agv送料數量
        payload = {
          id: item,
          record_name: 'delivery_qty',
          record_data: myMaterial.delivery_qty
        };
        await updateMaterial(payload);
        console.log('步驟2-2...');

        //紀錄該筆的agv送料狀態
        payload = {
          id: item,
          record_name: 'isShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-3...');

        if (Number(myMaterial.allOk_qty) != Number(myMaterial.req_qty)) { // 1張工單多批次運送, 訂單數量與入庫數量不同
          console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

          let tempDelivery = myMaterial.req_qty - myMaterial.allOk_qty;

          payload = {
            copy_id: myMaterial.id,
            //total_delivery_qty: tempDelivery,
            assemble_qty: tempDelivery,
            show2_ok: 2,
            shortage_note: '',
          }
          await copyMaterial(payload);
          console.log('步驟2-4...');
        }
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 1,      // 準備中
        station:  2,    // 已在組裝區
      };
      await updateAGV(payload);
      console.log('agv_end 處理步驟3...');

      // 插入延遲 3 秒
      await delay(3000);

      isFlashLed.value = false;     //黃綠燈熄滅

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }

      history.value = false;
      if (localStorage.getItem('history')) {
        localStorage.removeItem('history');
      }

      //待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    });

    socket.value.on('station2_agv_ready', async () => {
      console.log('AGV 已在組裝區裝卸站, 收到 station2_agv_ready 訊息...');

    });

    socket.value.on('station1_agv_ready', async () => {
      console.log('AGV 已在備料區裝卸站, 收到 station1_agv_ready 訊息...');
      // 記錄等待agv到站結束時間
      agv1EndTime.value = new Date();
      console.log("AGV End time:", agv1EndTime.value);

      let agv1PeriodTime = calculatePeriodTime(agv1StartTime.value, agv1EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv1StartTime.value);
      let formattedEndTime = formatDateTime(agv1EndTime.value);
      console.log("AGV 等待 Start Time:", formattedStartTime);
      console.log("AGV 等待 End Time:", formattedEndTime);
      console.log("AGV 等待 Period time:", agv1PeriodTime);

      let payload = {};
      // 記錄備料區途程資料, 等待agv時間
      selectedItems.value.forEach(async (item) => {
        let myMaterial = materials.value.find(m => m.id == item);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv1PeriodTime,
          user_id: 'AGV1-1',                        //在備料區('AGV1'), 呼叫AGV的等待時間('-1'), 即簡稱AGV1-1
          order_num: myMaterial.order_num,
          id: myMaterial.id,                        //2025-02-24 add
          process_type: 1,                          //在備料區
        };
        await createProcess(payload);
      });
      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 0,
        station:  1,
      };
      await updateAGV(payload);

      //startFlashing();
      background.value='#ffff00'
      isFlashLed.value = true;
    });
    */
    //socket.value.on('agv_ack', async () => {
    //  console.log('收到 agv_ack 回應');
    //});
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
    //await listWarehouseForAssemble();
    await getWarehouseForAssembleByHistoryFun();

    await listUsers2();

    //await listSocketServerIP();
    //console.log("initialize, socket_server_ip:", socket_server_ip.value)
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const handleBarCode = () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)
  let myBarcode = materials_and_assembles_by_user.value.find(m => m.order_num == bar_code.value);

  // 在這裡做條碼比對、查詢、上傳等邏輯
  if (myBarcode) {
    console.log('找到條碼對應項目:', myBarcode.id);

    // focus到對應項目的欄位
    focusItemField(myBarcode);
  } else {
    showSnackbar('找不到對應條碼資料！', 'red accent-2');
    console.warn('找不到對應條碼資料!')
  }
}

const toggleHistory = async () => {
  history.value = !history.value;
  await getWarehouseForAssembleByHistoryFun();
};

const getWarehouseForAssembleByHistoryFun = async () => {
  let payload = {
    history_flag: history.value,
  };
  await getWarehouseForAssembleByHistory(payload);
}

const getRowProps = (item, index) => {
// 偶數列與奇數列高度不同
const backgroundColor = item.index % 2 === 0 ? '#ffffff' : '#edf2f4';

return {
  style: {
    backgroundColor,
  },
};
};

const handleDateChange = (newDate) => {
  if (newDate instanceof Date) {
    // 調整為本地時區日期
    const localDate = new Date(newDate.getTime() - newDate.getTimezoneOffset() * 60000);
    fromDateVal.value = localDate;
    formattedDate.value = localDate.toISOString().split('T')[0]; // 格式化為 YYYY-MM-DD

    editDialogBtnDisable.value = false;
  }
  fromDateMenu.value = false;
};

const parseDate = (formatted, format) => {
  const parts = formatted.split('/');
  switch (format) {
    case 'MM/DD/YYYY':
      return { month: parts[0], day: parts[1], year: parts[2] };
    case 'DD/MM/YYYY':
      return { day: parts[0], month: parts[1], year: parts[2] };
    case 'YYYY/MM/DD':
      return { year: parts[0], month: parts[1], day: parts[2] };
    default:
      throw new Error('Unsupported date format');
  }
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 根據輸入搜尋工單編號
const handleOrderNumSearch = () => {
console.log("handleOrderNumSearch()...");

let selected = materials.value.find(mat => mat.order_num === selectedOrderNum.value);
if (selected) {
  selectedOrderNum.value = `${selected.order_num}`;
  console.log("已更新選中工單: ", selectedOrderNum.value);

  inputSelectOrderNum.value = placeholderTextForOrderNum.value;
} else {
  selectedOrderNum.value = ''; // 清空值，防止未選擇時顯示錯誤內容
}

// 確保 placeholder 保持靜態文字
placeholderTextForOrderNum.value = "請選擇工單";
};

// 根據輸入搜尋員工編號
const handleEmployeeSearch = () => {
console.log("handleEmployeeSearch()...");

let selected = desserts2.value.find(emp => emp.emp_id.replace(/^0+/, '') === selectedEmployee.value);
if (selected) {
  selectedEmployee.value = `${selected.emp_id} ${selected.emp_name}`;
  console.log("已更新選中員工: ", selectedEmployee.value);

  inputSelectEmployee.value = placeholderTextForEmployee.value;
} else {
  selectedEmployee.value = ''; // 清空值，防止未選擇時顯示錯誤內容
}

// 確保 placeholder 保持靜態文字
placeholderTextForEmployee.value = "請選擇員工";
};

const updateEmployeeFieldFromSelect = () => {
console.log("更新 TextField: ", inputSelectEmployee.value);
const selected = desserts2.value.find(emp => emp.emp_id === inputSelectEmployee.value);
if (selected) {
  selectedEmployee.value = `${selected.emp_id} ${selected.emp_name}`;
  console.log("已更新選中員工: ", selectedEmployee.value);

  inputSelectEmployee.value = placeholderTextForEmployee.value;
} else {
  selectedEmployee.value = ''; // 清空值，防止未選擇時顯示錯誤內容
}

  // 確保 placeholder 保持靜態文字
  placeholderTextForEmployee.value = "請選擇員工";
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

const setActive = (value) => {
  toggle_exclusive.value = value; // 設置當前活動按鈕
  if (toggle_exclusive.value == 1)
    showMenu.value = true;
  else
    showMenu.value = false;
}

const checkQtyField = (item) => {
  console.log("checkQtyField,", item);

  // 將輸入值轉換為數字，並確保是有效的數字，否則設為 0
  //const deliveryQty = Number(item.delivery_qty) || 0;   //到庫數量
  const deliveryQty = Number(item.must_allOk_qty);      //應入庫數量
  const totalQty = Number(item.allOk_qty) || 0;         //入庫數量
  console.log("deliveryQty , totalQty:", deliveryQty, totalQty)

  if (deliveryQty < totalQty) {       // 檢查是否超過到庫數量
    delivery_qty_alarm.value = '入庫數量超過應入庫數量!';

    item.tooltipVisible = true;       // 顯示 Tooltip
    setTimeout(() => {
      item.tooltipVisible = false;    // 2秒後隱藏 Tooltip
      item.allOk_qty = 0;
    }, 2000);

  } else {
    item.tooltipVisible = false;
    delivery_qty_alarm.value = '';    // 清除警告
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

  // 如果按下的鍵不是數字，阻止輸入
  if (!/^\d$/.test(inputChar)) {
    event.preventDefault();  // 阻止非數字輸入
    return;
  }

  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入, 2025-07-02 modify
  if (inputValue.length > 5 && inputValue < 10000) {
    event.preventDefault();
    return;
  }

  /*
  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 使用正規化運算式檢查是否為數字且長度不超過3
  //if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
  if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
    event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
    return;   // 確保阻止後執行中止
  }
  */
  // 偵測是否按下 Enter 鍵
  if (event.key === 'Enter' || event.keyCode === 13) {
    console.log('Return key pressed');
    // 如果需要，這裡可以執行其他操作，或進行額外的驗證
  }

  editDialogBtnDisable.value = false;
};

const isSelected = (item) => {
  //console.log("isSelected(), item.columns.id", item.raw, item.columns.id); // 查看 item.columns 是否包含 id
  // 安全檢查，確保 item 和 item.columns 存在
  if (!item || !item.columns || typeof item.columns.id === 'undefined') {
    return false; // 預設未被選中
  }

  return selectedItems.value.includes(item.columns.id); // 根據 columns.id 檢查是否被選中
};

const toggleSelect = (item) => {
  const index = selectedItems.value.indexOf(item.columns.id);
  if (index === -1) {
    selectedItems.value.push(item.columns.id); // 若未選中，則添加 columns.id
  } else {
    selectedItems.value.splice(index, 1);     // 若已選中，則移除 columns.id
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

const editOrderNum = async (item) => {
  console.log("editOrderNum(),", item);

  selectedId.value = item.id;
  selectedOrderNum.value = item.order_num;
  selectedReqQty.value = item.req_qty;
  selectedDate.value = item.date;

  fromDateVal.value = new Date(selectedDate.value)
  console.log("fromDateVal:", fromDateVal.value);

  let payload = {
    id: item.id,
  };
  await getBoms(payload);
  console.log("currentBoms:",currentBoms.value)
  //modify_boms.value = [...currentBoms.value];
  //console.log("boms, modify_boms:", currentBoms.value, modify_boms.value)

  editDialogBtnDisable.value = true;

  editDialog.value = true;
}
/*
const toggleExpand = async (item) => {
  console.log("toggleExpand(),", item.order_num);

  enableDialogBtn.value = item.isTakeOk && !item.isShow;    //備料完成(按確定鍵) && AGV還沒送出

  let payload = {};

  payload = {
    //order_num: item.order_num,
    id: item.id,
  };
  await getBoms(payload);
  current_cell.value = item.delivery_qty
  selectedItem.value = item;
  //console.log("toggleExpand, selectedItem.value", selectedItem.value)

  // 記錄當前開始備料時間
  currentStartTime.value = new Date();  // 使用 Date 來記錄當時時間
  console.log("Start time:", currentStartTime.value, item, item.id);

  // 記錄當前途程狀態
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

  dialog.value = true;
};
*/
const checkTextEditField = (focused, item) => {
  if (!focused) {
    console.log("checkTextEditField(): 失去焦點");
  } else {
    console.log("checkTextEditField(): 獲得焦點");
  }
};

const addAbnormalInMaterial = (item) => {
  console.log("addAbnormalInMaterial(),", item);

  abnormalDialog_record.value = warehouses.value.find(m => m.id == item.id);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_delivery_qty.value = item.delivery_qty;
  abnormalDialog_new_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_display.value = item.Incoming2_Abnormal;

  abnormalDialog.value = true;
}

const createAbnormalFun = async () => {
  console.log("createAbnormalFun()...");

  if (abnormalDialog_new_must_receive_qty.value != abnormalDialog_must_receive_qty.value) {
    let temp_str = '(' + abnormalDialog_delivery_qty.value + abnormalDialog_new_must_receive_qty.value + ')'
    abnormalDialog_message.value = '組裝區來料數量不對! '+ temp_str;
    let payload = {}
    try {
      //payload = {
      //  assemble_id: item.assemble_id,
      //  cause_message: ['備料區來料數量不對'],
      //  cause_user: currentUser.value.empID,
      //};
      //await updateAssembleAlarmMessage(payload);
      console.log("abnormalDialog_record.order_num:", abnormalDialog_record.value.order_num)
      payload = {
        order_num: abnormalDialog_record.value.order_num,
        record_name: 'Incoming2_Abnormal',
        record_data: abnormalDialog_message.value,
      };
      await updateMaterial(payload);
      abnormalDialog_record.value.Incoming2_Abnormal=false;

      // targetIndex為目前table data record 的 index
      const targetIndex = warehouses.value.findIndex(
        (kk) => kk.id === item.id
      );

      if (targetIndex !== -1) {
        // 用 Vue 的方式確保觸發響應式更新
        warehouses.value[targetIndex] = {
          ...warehouses.value[targetIndex],
          Incoming2_Abnormal: false,
        };
      }

      console.log('更新成功...');
    } catch (error) {
      console.error('更新失敗:', error.response?.data?.message || error.message);
    }
  }
  abnormalDialog.value = false;
}

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  let allOk_qty = 0;
  // 檢查是否輸入了空白或 0
  if (!item.allOk_qty || Number(item.allOk_qty) === 0) {
    allOk_qty = Number(item.delivery_qty) || 0;
  } else {
    allOk_qty = Number(item.allOk_qty) || 0;
  }

  let payload = {};

  // 記錄當前入庫數量
  payload = {
    id: item.id,
    record_name: 'allOk_qty',
    record_data: allOk_qty,
  };
  await updateMaterial(payload);
  item.allOk_qty = allOk_qty

  payload = {
    id: item.id,
    record_name: 'show2_ok',
    record_data: 11      // 設為 11，入庫進行中
  };
  await updateMaterial(payload);

  payload = {
    id: item.id,
    record_name: 'show3_ok',
    record_data: 12      // 設為 12，入庫進行中
  };
  await updateMaterial(payload);

  item.isError = true;              // 輸入數值正確後，重置 數字 為 紅色
  // begin block, 2025-06-24 add
  payload = {
    id: item.id,
    record_name: 'isLackMaterial',
    record_data: 99,
  };
  await updateMaterial(payload);
  item.isLackMaterial = 99;

  payload = {
    id: item.id,
    record_name: 'isTakeOk',
    record_data: true
  };
  await updateMaterial(payload);
  item.isTakeOk = true;
  // end block

  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }
};
//2025 mark the following function
/*
const updateItem = async () => {    //編輯 bom, material及process後端table資料
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

  if (!take_out) {                    // 該筆訂單檢料未完成, 缺料
    materialPayload = {               // 更新 materials 資料，shortage_note = '(缺料)'
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'shortage_note',
      record_data: '(缺料)'
    };
    await updateMaterial(materialPayload);
    selectedItem.value.shortage_note = '(缺料)';

    materialPayload = {               // 2. 更新 materials 資料，isLackMaterial = 1
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'isLackMaterial',
      record_data: 0,          //缺料
    };
    await updateMaterial(materialPayload);
    selectedItem.value.isLackMaterial = 0;
  } else {
    materialPayload = {
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'shortage_note',
      record_data: ''
    };
    await updateMaterial(materialPayload);
    selectedItem.value.shortage_note = '';

    materialPayload = {
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'isLackMaterial',
      record_data: 99,
    };
    await updateMaterial(materialPayload);
    selectedItem.value.isLackMaterial = 0;
  }

  materialPayload = {                       // 2. 更新 materials 資料, 按確定鍵的狀態
    //order_num: my_material_orderNum,
    id: selectedItem.value.id,
    record_name: 'isTakeOk',
    record_data: true
  };
  await updateMaterial(materialPayload);
  selectedItem.value.isTakeOk = true;

  if (take_out) {                     // 該筆訂單檢料完成
    materialPayload = {               // 2. 更新 materials 資料，show2_ok = 2
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'show2_ok',
      record_data: 2                  // 設為 2，表示備料完成
    };
    await updateMaterial(materialPayload);

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

    await listWarehouseForAssemble();
  }
  dialog.value = false;
};
*/
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
/*
const formatTime = (time) => {                            // 格式化時間為 hh:mm:ss
const hours = String(time.getHours()).padStart(2, '0');
const minutes = String(time.getMinutes()).padStart(2, '0');
const seconds = String(time.getSeconds()).padStart(2, '0');

return `${hours}:${minutes}:${seconds}`;
};
*/
const callAGV = async () => {
  console.log("callAGV()...")

  let payload = {};
  //let targetItem = {};

  //console.log("step1...")
  if (!isCallAGV.value) {
    //console.log("step2...")
    if (selectedItems.value.length == 0) {
      showSnackbar("請選擇送料的工單!", 'red accent-2');
      return;
    }

    isCallAGV.value = true
  } else {
    showSnackbar("請不要重複按鍵!", 'red accent-2');
    return;
  }

  selectedItems.value.forEach(async (item) => {
    //console.log("step4...")
    let targetItem = warehouses.value.find(
      (kk) => kk.id === item
    );
    console.log("targetItem:", targetItem)

    payload = {
      id: targetItem.id,
      record_name: 'show2_ok',
      record_data: 12      // 設為 12，入庫完成
    };
    await updateMaterial(payload);
    //console.log("step5...")
    payload = {
      id: targetItem.id,
      record_name: 'show3_ok',
      record_data: 13      // 設為 13，入庫完成
    };
    await updateMaterial(payload);
    //console.log("step6...")
    //紀錄該筆訂單入庫數量
    payload = {
      id: targetItem.id,
      record_name: 'allOk_qty',
      record_data: targetItem.allOk_qty
    };
    await updateMaterial(payload);
    //console.log("step7...")
    //紀錄該筆訂單入庫總數量
    let temp_total_allOk_qty = targetItem.total_allOk_qty + targetItem.allOk_qty
    payload = {
      id: targetItem.id,
      record_name: 'total_allOk_qty',
      record_data: temp_total_allOk_qty
    };
    await updateMaterial(payload);
    //console.log("step8...")
    //紀錄該筆的agv組裝完成狀態
    payload = {
      id: targetItem.id,
      record_name: 'isAllOk',
      record_data: true
    };
    await updateMaterial(payload);
    //console.log("step9...")
    //下面這一段, 待討論....

    if (Number(targetItem.delivery_qty) != temp_total_allOk_qty) { // 1張工單多批次運送
      console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

      let tempDelivery = targetItem.delivery_qty - temp_total_allOk_qty;

      payload = {
        copy_id: targetItem.id,
        total_delivery_qty: tempDelivery,
        allOk_qty: tempDelivery,
        show2_ok: 2,
        shortage_note: '',
      }
      await copyMaterial(payload);
    }
    //
    //let allOkTime = new Date();  // 使用 Date 來記錄當時時間
    let formattedallOkTime = formatDateTime(new Date());

    let processPayload = {
      begin_time: formattedallOkTime,
      end_time: formattedallOkTime,
      periodTime: '',
      user_id: currentUser.value.empID,
      order_num: targetItem.order_num,
      process_type: 31,
      id: targetItem.id,
    };
    await createProcess(processPayload);


  });

  // 記錄AGV狀態資料
  payload = {
    id: 1,
    status: 0,      // ready
    station:  3,    // 在成品區
  };
  await updateAGV(payload);
  console.log("step10...")
  // 插入延遲 3 秒
  await delay(3000);

  selectedItems.value = [];
  if (localStorage.getItem('selectedItems')) {
    localStorage.removeItem('selectedItems');
  }

  history.value = false;
  if (localStorage.getItem('history')) {
    localStorage.removeItem('history');
  }

  //待待
  //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};
/*
const readAllExcelFun = async () => {
console.log("readAllExcelFun()...");

if (fileCount.value === 0) {
  console.warn("No files available for import.");
  return;
}

try {
  // 等待 readAllExcelFiles 完成
  const excel_file_data = await readAllExcelFiles();
  console.log("data:", excel_file_data);

  if (excel_file_data.status) {
    fileCount.value = 0;
    await deleteAssemblesWithNegativeGoodQty();
    listWarehouseForAssemble();
  } else {
    showSnackbar(excel_file_data.message, 'red accent-2');
  }
} catch (error) {
  console.error("Error during execution:", error);
  showSnackbar("An error occurred.", 'red accent-2');
}
};

const updateModifyMaterialAndBomsFun = async () => {
let payload = {
  id: selectedId.value,
  date: selectedDate.value,
  qty: selectedReqQty.value,
  file_name: modify_file_name.value,
  bom_data: modify_boms.value,
};

await updateModifyMaterialAndBoms(payload)

editDialog.value = fals
}

const modifyExcelFilesFun = async () => {
console.log("modifyExcelFilesFun()...");

let payload = {
  id: selectedId.value,
  material_id: selectedOrderNum.value,
};

try {
  const modify_result = await modifyExcelFiles(payload);

  if (modify_result.status) {
    modify_boms.value = [...modify_result.modifyBom];
    modify_file_name.value = modify_result.modifyFileName;
    //console.log("modify_file_name:", modify_file_name.value);

    editDialogBtnDisable.value = false;
  } else {
    showSnackbar(modify_result.message, 'red accent-2');
  }
} catch (error) {
  console.error("Error during execution:", error);
  showSnackbar("An error occurred.", 'red accent-2');
}
};
*/
// 改變拖曳功能
const toggleDrag = () => {
  panel_flag.value = !panel_flag.value
}

// 控制面板樣式，包括邊框顏色和層級 (z-index)
const panelStyle = computed(() => ({
  cursor: panel_flag.value ? 'move' : 'default',
  border: panel_flag.value ? '2px solid blue' : '2px solid transparent',
  zIndex: panel_flag.value ? 9999 : 1, // 當可拖曳時，將面板提升至最上層
}))

const showSnackbar = (message, color) => {
snackbar_info.value = message;
snackbar_color.value = color;
snackbar.value = true;
};

// 雙擊事件處理函式（箭頭函式）
//const moveToUserFacets = (index) => {
//  const item = allFacets.value.splice(index, 1)[0];
//  userFacets.value.push(item);
//};

//const moveToAllFacets = (index) => {
//  const item = userFacets.value.splice(index, 1)[0];
//  allFacets.value.push(item);
//};
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
  color: red !important;
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
  color: var(--input-text-color);   // 使用 CSS 變數設置顏色
  min-width:60px;
  width:60px;
}

:deep(.v-btn-group--density-default.v-btn-group) {
  min-height: 36px;
  height: 36px;
  left: -10px;
  position: relative;
}

:deep(.v-picker__header) {
  display: none
}

:deep(.v-picker-title) {
  display: none
}

// 客製化 手推車/AGV切換按鍵
.button-container {
  position: relative;
  width: fit-content;     // 可調整寬度以適應按鈕

  right: 100px;
  top: 0px;
}

.blue-text {
  color: #003171;   // 設置字體顏色為深藍色
  //color: red;
  font-weight: 700;
}

.facet-container {
  width: 330px;
}

.right {
  float: right;
}

.left {
  float: left;
}

p {
  clear: both;
  padding-top: 1em;
}

.facet-list {
  list-style-type: none;
  margin: 0;
  padding: 0;
  margin-right: 10px;
  background: #eee;
  padding: 5px;
  width: 143px;
  min-height: 1.5em;
  font-size: 0.85em;
}

.facet-list li {
  margin: 5px;
  padding: 5px;
  font-size: 1.2em;
  width: 120px;
}

.facet-list li.placeholder {
  height: 1.2em;
}

.facet {
  border: 1px solid #bbb;
  background-color: #fafafa;
  cursor: pointer;
}

.placeholder {
  border: 1px solid orange;
  background-color: #fffffd;
}

:deep(.v-date-picker-month__weekday) {
  font-weight: bold;
  visibility: hidden; /* 隱藏原始內容，但保留空間 */
  position: relative; /* 必須為 ::after 提供相對定位 */
}

/* 添加新的中文字符 */
:deep(.v-date-picker-month__weekday:nth-child(1))::after {
  content: '日';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(2))::after {
  content: '一';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(3))::after {
  content: '二';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(4))::after {
  content: '三';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(5))::after {
  content: '四';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(6))::after {
  content: '五';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(7))::after {
  content: '六';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}

.text-caption {
  margin-right: 8px;      // 與輸入框內容留出間距
  color: gray;       // 設定文字顏色
  right: -20px;
  position: relative;
  font-size: 16px !important;
  font-weight: 600;
  font-family: '微軟正黑體', sans-serif;
}

.modify_order_num {
  position: relative;
  top:0px;
  width: 220px;
  right: -20px;
}

:deep(.modify_order_num span) {
  color:#0D47A1
}

:deep(.modify_qty span) {
  color:#0D47A1
}

:deep(.modify_qty .v-input__control) {
  min-width: 60px;
  width: 60px;
}

.modify_date {
  position: relative;
  top:0px;
  width: 150px;
  right: 0px;
}

:deep(.modify_date .v-input__prepend) {
  margin-inline-end: 0;
}

:deep(i.mdi-calendar) {
  color: #F44336;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

//.v-input--horizontal .v-input__prepend {
.custom-bordered-row {
  border: 2px solid #0D47A1; /* 設定邊框寬度與顏色 */
  border-radius: 8px;        /* 可選: 為邊框添加圓角 */
  padding: 16px;
}

.hidden-column {
  display: none;
}

:deep(.top_find_field .v-input__control) {
  position: relative;
  left: 50px;
  top: 10px;
}

</style>
