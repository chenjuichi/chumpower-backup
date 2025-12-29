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

  <ConfirmDialog ref="confirmRef" />

  <!-- data table -->
  <v-data-table
    :headers="headers"
    :items="warehouses"
    :row-props="getRowProps"
    :search="search"
    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"

    item-value="index"
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
        :disabled="!(internalItem.raw.allOk_qty != 0 && internalItem.raw.input_allOk_disable)"
        color="primary"
        @update:model-value="toggleSelect(internalItem)"
        :class="{ 'blue-text': internalItem.raw.input_allOk_disable }"
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
              <v-btn-toggle >
                <v-btn
                  :value="true"
                  variant="outlined"
                  :style="{
                    background: history === true ? '#e67e22' : '#e7e9eb',
                    color: history === true ? '#fff' : '#000',
                    fontWeight: '700'
                  }"
                  @click="setActive2(true)"
                >
                  <span>歷史紀錄</span>
                </v-btn>

                <v-btn
                  :value="false"
                  variant="outlined"
                  :style="{
                    background: history === false ? '#27ae60' : '#e7e9eb',
                    color: history === false ? '#fff' : '#000',
                    fontWeight: '700'
                  }"
                  @click="setActive2(false)"
                >
                  <span>等待入庫</span>
                </v-btn>
              </v-btn-toggle>
            </v-col>

            <!--客製化 入庫登記按鍵-->
            <v-col cols="12" md="2">
              <v-btn
                :disabled="c_isBlinking"
                color="primary"
                variant="outlined"
                style="position: relative; right: 30px; top: 0px; font-weight: 700;"
                @click="onClickWarehouseIn"
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
                style="position: relative; top: 10px; right:60px;"
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
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '訂單數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">訂單</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '到庫數量' (delivery_qty) 欄位的表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">到庫</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '應入庫總數量' (must_allOk_qty) 欄位的表頭 -->
    <template v-slot:header.must_allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">應入庫</div>
        <div>總數量</div>
      </div>
    </template>

    <!-- 客製化 '已入庫登記總數量' (total_allOk_qty) 欄位的表頭 -->
    <template v-slot:header.total_allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">已入庫登記</div>
        <div>總數量</div>
      </div>
    </template>

    <!-- 客製化 '入庫數量' (allOk_qty) 欄位的表頭 -->
    <template v-slot:header.allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">入庫</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 自訂 index 欄位的資料欄位 -->
    <template v-slot:item.index="{ item }">
      <!-- 空白顯示 -->
    </template>

    <!-- 自訂 '訂單編號' 欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: center;">
        <!--入庫數輸入完成-->
        <div style="color: blue; margin-right: 20px;" v-if="item.input_allOk_disable">
          {{ item.order_num }}
        </div>
        <!--入庫數輸入尚未完成-->
        <div style="margin-right: 20px;" v-else>
          {{ item.order_num }}
        </div>
      </div>
    </template>

    <!-- 自訂 '說明' 欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>-->
      </div>
    </template>

    <!-- 自訂 應入庫數量 欄位資料欄位 -->
    <template v-slot:item.must_allOk_qty="{ item }">
      <div style="display:flex; align-items:center; left:25px; position:relative;">
        <v-icon
          v-if="!history"
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
    <!--
      :disabled="(selectedItems.includes(item.index) || item.isAllOk) || history"
    -->
    <template v-slot:item.allOk_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
          v-model="item.allOk_qty"
          dense
          hide-details
          style="max-width: 60px; text-align: center; z-index: 1;"
          :id="`allOkQtyID-${item.index}`"
          @keydown="handleKeyDown"
          @update:modelValue="(value) => { item.allOk_qty = value; checkQtyField(item); }"

          @update:focused="(focused) => checkTextEditField(focused, item)"
          @keyup.enter="updateItem2(item)"
          :disabled="item.input_allOk_disable"
          :style="{
            '--input-text-color': (item.isError || Number(item.allOk_qty) > 0) ? 'red' : 'black'
          }"
        />
        <span
          v-show="item.tooltipVisible"
          style="
            position: absolute;
            left: -200px;
            top: -15px;
            z-index: 2;
            background-color: transparent;
            padding: 0;
            min-width: 120px;
            white-space: nowrap;
            color:red;
            text-align: left;
            font-weight: 700;
            font-size: 12px;"
        >
          {{ over_qty_alarm }}
        </span>
      </div>
    <!--
      <div v-show="item.isAllOk" style=" position: relative; left: -20px; top: -5px; font-weight: 400; font-size: 10px;">
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

import ConfirmDialog from "./confirmDialog";

import draggable from 'vuedraggable'
import { useRoute } from 'vue-router';

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { desserts2 }  from '../mixins/crud.js';
import { materials, warehouses, boms, currentBoms, currentAGV, material_copy_id ,socket_server_ip, fileCount }  from '../mixins/crud.js';

import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
const countExcelFiles = apiOperation('get', '/countExcelFiles');

const listUsers2 = apiOperation('get', '/listUsers2');
const listProducts = apiOperation('get', '/listProducts');

const getBoms = apiOperation('post', '/getBoms');
const getAGV = apiOperation('post', '/getAGV');
//const updateBoms = apiOperation('post', '/updateBoms');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateAssemble = apiOperation('post', '/updateAssemble');
const copyMaterial = apiOperation('post', '/copyMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const updateAGV = apiOperation('post', '/updateAGV');
const modifyExcelFiles = apiOperation('post', '/modifyExcelFiles');
const updateModifyMaterialAndBoms = apiOperation('post', '/updateModifyMaterialAndBoms');
const getWarehouseForAssembleByHistory = apiOperation('post', '/getWarehouseForAssembleByHistory');
const updateProcessData = apiOperation('post', '/updateProcessData');
const createProduct = apiOperation('post', '/createProduct');
const updateProduct = apiOperation('post', '/updateProduct');

//=== component name ==
defineComponent({ name: 'WarehouseForAssemble' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
// 入庫對話框相關
const endTitle = ref('準備入庫');
const endMessage = ref('確定？');
const confirmRef = ref(null);

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

const editDialogBtnDisable = ref(true);

const fromDateMenu = ref(false);              // 日期menu 打開/關閉

const fromDateVal = ref('');

//# let intervalId = null;                        // 10分鐘, 倒數計時器

const route = useRoute();                     // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'index', width: 0, class: 'hidden-column' },
  { title: '訂單編號', sortable: true, key: 'order_num', width:110 },
  { title: '物料編號', sortable: true, key: 'material_num', width:110 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:80 },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:320 },
  { title: '交期', align: 'center', sortable: false, key: 'date', width:110 },
  { title: '到庫數量', sortable: false, key: 'delivery_qty', width:80 },
  { title: '應入庫總數量', align: 'center', sortable: false, key: 'must_allOk_qty', width:100 },
  { title: '已入庫登記總數量', sortable: false, key: 'total_allOk_qty', width:100 },

  { title: '入庫數量', sortable: false, key: 'allOk_qty', width:80 },
];

const search = ref('');

const history = ref(false);

const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)

const app_user = 'user_chumpower';
const clientAppName = 'WarehouseForAssemble';

const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user, clientAppName);

const over_qty_alarm = ref('');

const currentUser = ref({});
const componentKey = ref(0)       // key 值用於強制重新渲染

const pagination = reactive({
  itemsPerPage: 5,                // 預設值, rows/per page
  page: 1
});

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

  // 阻止直接後退，但保留 Vue Router 的 state
  window.history.replaceState(window.history.state, '', document.URL);
  window.addEventListener('popstate', handlePopState);

  console.log("current routeName:", routeName.value);

  //user define
  let userRaw = sessionStorage.getItem('auth_user');
  if (!userRaw) {
    // 只在第一次開分頁時，從 localStorage 複製一份
    userRaw = localStorage.getItem('loginedUser');
    if (userRaw) {
      sessionStorage.setItem('auth_user', userRaw);
    }
  }
  currentUser.value = userRaw ? JSON.parse(userRaw) : null;

  if (currentUser.value) {
    currentUser.value.setting_items_per_page = pagination.itemsPerPage;
    currentUser.value.setting_lastRoutingName = routeName.value;

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }
  console.log("currentUser:", currentUser.value);
  //

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

      activeColor.value='yellow';  // 物料進站
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

    socket.value.on('triggerLogout', async (data) => {
      console.log("收到 triggerLogout 強迫登出訊息，empID:", data.empID, "目前 empID:", currentUser.value.empID);

      if (data.empID && data.empID === currentUser.value.empID) {
        console.log("本裝置符合 empID，執行強制登出流程");

        let payload = {
          itemsPerPage: 0,
          seeIsOk: '0',
          lastRoutingName: 'Main',
          empID: userData.empID,
        };

        try {
          await updateSetting(payload);
        } finally {
          localStorage.setItem('Authenticated', false);
          removelocalStorage();

          const resolvedRoute = router.resolve({ name: 'LoginRegister' });
          const path = resolvedRoute.href;
          console.log('triggerLogout socket...', path)
          router.replace({ path });
        }
      } else {
        console.log("本裝置 empID 不符，忽略此 triggerLogout");
      }
    });

  } catch (error) {
    console.error('Socket連線失敗:', error);
  }
});

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時
  window.removeEventListener('popstate', handlePopState)

  //# clearInterval(intervalId);
});

//=== created ===
onBeforeMount(() => {
console.log("Employer, created()...")

pagination.itemsPerPage = currentUser.value.setting_items_per_page;

initAxios();
initialize();
});

//=== method ===
const setActive2 = async (value) => {
  history.value = value;       // 設置當前活動按鈕

  if (history.value) {
    await toggleHistory();
  } else {
    await getWarehouseForAssembleByHistoryFun();
  }
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    // 使用 async/await 等待 API 請求完成，確保順序正確
    //await listWarehouseForAssemble();
    await getWarehouseForAssembleByHistoryFun();

    await listUsers2();

    await setActive2(false);
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const handlePopState = () => {
  // 重新把這一筆 entry 的 state 改回 Router 給的 state
  window.history.replaceState(window.history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

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
  const myData = await listProducts();

  const items = Array.isArray(myData?.items)
  ? myData.items
  : Array.isArray(myData)                         // 萬一你的 listProducts 直接回傳 array
    ? myData
    : [];

  warehouses.value = items;
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

  return { style: { backgroundColor, }, };
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const checkQtyField = (item) => {
  // 將輸入值轉換為數字，並確保是有效的數字，否則設為 0

  const mustQty  = Number(item.must_allOk_qty) || 0;  // 應入庫數量
  const inputQty = Number(item.allOk_qty) || 0;       // 入庫數量（目前輸入）
  const total_allOk_qty = Number(item.total_allOk_qty) || 0;

  // 檢查是否超過需求數量
  if ((inputQty + total_allOk_qty) > mustQty) {
    over_qty_alarm.value = '入庫數量與已入庫登記總數量的和太大!';
    item.tooltipVisible = true;

    setTimeout(() => {
      item.tooltipVisible = false;    // 3秒後隱藏 Tooltip
    }, 3000);
  } else {
    item.tooltipVisible = false;
    item.isError = false;
    over_qty_alarm.value = '';    // 清除警告
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

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入
  if (inputValue.length > 5 && inputValue < 10000) {
    event.preventDefault();
    return;
  }

  // 偵測是否按下 Enter 鍵
  if (event.key === 'Enter' || event.keyCode === 13) {
    console.log('Return key pressed');
    // 如果需要，這裡可以執行其他操作，或進行額外的驗證
  }

  editDialogBtnDisable.value = false;
};

const isSelected = (item) => {
  // 安全檢查，確保 item 和 item.columns 存在
  if (!item || !item.columns || typeof item.columns.index === 'undefined') {
    return false; // 預設未被選中
  }

  return selectedItems.value.includes(item.columns.index); // 根據 columns.id 檢查是否被選中
};

const toggleSelect = (item) => {
  console.log("1.selectedItems.value:",selectedItems.value)

  const index = selectedItems.value.indexOf(item.columns.index);
  if (index === -1) {
    selectedItems.value.push(item.columns.index); // 若未選中，則添加 columns.id
  } else {
    selectedItems.value.splice(index, 1);         // 若已選中，則移除 columns.id
  }
  console.log("2.selectedItems.value:",selectedItems.value)
};

const checkTextEditField = (focused, item) => {
  if (!focused) {
    console.log("checkTextEditField(): 失去焦點");
  } else {
    console.log("checkTextEditField(): 獲得焦點");
  }
};

const addAbnormalInMaterial = (item) => {
  console.log("addAbnormalInMaterial(),", item);

  abnormalDialog_record.value = warehouses.value.find(m => m.index == item.index);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_delivery_qty.value = item.delivery_qty;
  abnormalDialog_new_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_display.value = item.Incoming2_Abnormal;

  abnormalDialog.value = true;
}

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  //* material table: 就目前工單, 更新該筆的顯示訊息
  //* assemble table: 就目前工單, 更新該筆的入庫數量
  // product table: 就目前工單,  新增一筆
  // process table: 就目前工單,  新增一筆

  let allOk_qty = 0;
  // 檢查是否輸入了空白或 0
  if (!item.allOk_qty || Number(item.allOk_qty) === 0) {
    allOk_qty = Number(item.delivery_qty) || 0;
  } else {
    allOk_qty = Number(item.allOk_qty) || 0;
  }

  const targetIndex = warehouses.value.findIndex(
    (kk) => kk.index === item.index
  );
  let current_assemble_id = warehouses.value[targetIndex].assemble_id
  let current_material_id = warehouses.value[targetIndex].id
  //let current_process_id = warehouses.value[targetIndex].process_id

  let payload = {};
  /* 要轉換
  // 記錄當前入庫數量
  payload = {
    process_id: current_process_id,
    record_name: 'allOk_qty',
    record_data: allOk_qty,
  };
  await updateProcessData(payload);

  payload = {
    process_id: current_process_id,
    record_name: 'isAllOk',
    record_data: true
  };
  await updateProcessData(payload);
  */
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_allOk_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'allOk_qty',
    record_data: allOk_qty,
  };
  await updateAssemble(payload);

  payload = {
    id: current_material_id,
    record_name: 'show2_ok',
    record_data: 11             // 設為 11，入庫進行中
  };
  await updateMaterial(payload);

  payload = {
    id: current_material_id,
    record_name: 'show3_ok',
    record_data: 12             // 設為 12，入庫進行中
  };
  await updateMaterial(payload);

  // 用 Vue 的方式確保觸發響應式更新
  warehouses.value[targetIndex] = {
    ...warehouses.value[targetIndex],
    allOk_qty: allOk_qty,
    isError: true,                    // 輸入數值正確後，重置 數字 為 紅色
    input_allOk_disable: true,
  };

  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }
};
/*
const calculatePeriodTime = (start, end) => {     // 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
  const diffMs = end - start;                     // 差異時間（毫秒）
  const diffSeconds = Math.floor(diffMs / 1000);  // 轉換為秒

  const hours = Math.floor(diffSeconds / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);
  const seconds = diffSeconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};
*/
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

const onClickWarehouseIn = async () => {
  console.log("onClickWarehouseIn()...")

  const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
  if (selectedIds.length === 0) {
    showSnackbar('請選擇入庫的工單!', 'red accent-2');
    return;
  }

  //* material table: 就目前工單, 更新該筆的顯示訊息
  // assemble table: 就目前工單, 更新該筆的入庫數量
  //* product table: 就目前工單,  新增一筆
  //* process table: 就目前工單,  新增一筆

  try {
    let successCount = 0;

    for (const id of selectedIds) {
      const targetIndex = warehouses.value.findIndex(
        (kk) => kk.index === id
      );
      let current_material_id = warehouses.value[targetIndex].id;
      let current_assemble_id = warehouses.value[targetIndex].assemble_id
      let current_allOk_qty = warehouses.value[targetIndex].allOk_qty
      let current_must_qty = warehouses.value[targetIndex].must_allOk_qty
      let current_total_qty = warehouses.value[targetIndex].total_allOk_qty

      /*
      let current_process_id=warehouses.value[targetIndex].process_id;
      let payload = {
        process_id: current_process_id,
        record_name: 'normal_work_time',
        record_data: 4,           // 入庫 process
      };
      await updateProcessData(payload);
      */

      let payload = {}
      let d0 = Number(current_must_qty)
      let d1 = Number(current_total_qty)
      let d2 = Number(current_allOk_qty)
      let difference = d0 - d1 - d2
      if (difference != 0) {
        console.log("有difference...., difference,d0,d1,d2:", difference,d0,d1,d2)

        payload = {
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: false,
        };
        await updateAssemble(payload);

        payload = {
          assemble_id: current_assemble_id,
          record_name: 'allOk_qty',
          //record_data: allOk_qty,
          record_data: 0,
        };
        await updateAssemble(payload);

        // 用 Vue 的方式確保觸發響應式更新
        warehouses.value[targetIndex] = {
          ...warehouses.value[targetIndex],
          allOk_qty: 0,
          isError: false,
          input_allOk_disable: false,
          isWarehouseStationShow: false
        };
      } else {

        await updateMaterial({
          id: current_material_id,
          record_name: 'show2_ok',
          record_data: 12,          // 入庫完成
        });

        await updateMaterial({
          id: current_material_id,
          record_name: 'show3_ok',
          record_data: 13,          // 入庫完成
        });

        payload = {
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: true,
        };
        await updateAssemble(payload);

        payload = {
          assemble_id: current_assemble_id,
          record_name: 'allOk_qty',
          record_data: current_allOk_qty,
        };
        await updateAssemble(payload);

        payload = {
          assemble_id: current_assemble_id,
          record_name: 'isWarehouseStationShow',
          record_data: true,
        };
        await updateAssemble(payload);

        // 用 Vue 的方式確保觸發響應式更新
        warehouses.value[targetIndex] = {
          ...warehouses.value[targetIndex],
          //allOk_qty: allOk_qty,
          allOk_qty: current_allOk_qty,
          isError: true,
          input_allOk_disable: true,
          isWarehouseStationShow: true
        };
      }

      // 建立「成品入庫」流程（process_type: 31）
      const nowStr = formatDateTime(new Date());
      const myProcess=await createProcess({
        begin_time: nowStr,
        end_time: nowStr,
        periodTime: '',
        order_num: warehouses.value[targetIndex].order_num,
        user_id: currentUser.value?.empID ?? '',
        process_type: 31,         // 成品入庫
        id: current_material_id,
        assemble_id: current_assemble_id,
        has_started: true,
        process_work_time_qty: d2,
      });
      console.log("myProcess:", myProcess)

      const myProduct=await createProduct({
        material_id: current_material_id,
        process_id: myProcess.process_id,
        allOk_qty: d2,
        good_qty: current_allOk_qty,
      });

      successCount++;
    }

    // 成功至少一筆才更新 AGV 狀態（在成品區、ready）
    if (successCount > 0) {
      await updateAGV({
        id: 1,
        status: 0,  // ready
        station: 3, // 在成品區
      });
      console.log('step10...');
    } else {
      console.warn('沒有任何記錄成功更新，略過 AGV 狀態更新');
    }

    // 插入延遲 3 秒
    await delay(3000);

    // 清理選取與歷史
    selectedItems.value = [];
    if (localStorage.getItem('selectedItems')) localStorage.removeItem('selectedItems');

    history.value = false;
    if (localStorage.getItem('history')) localStorage.removeItem('history');
  } catch (err) {
    console.error('入庫流程發生例外：', err);
    showSnackbar('入庫流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    // 一定要解鎖，避免按鈕被卡住
    //isWarehouseIn.value = false;
  }
  //待待
  //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};

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

:deep(.v-table__wrapper > table > thead th:nth-child(3)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(3)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(4)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(4)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(5)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(5)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(6)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(6)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

</style>
