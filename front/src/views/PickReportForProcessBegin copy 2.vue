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

  <ConfirmDialog ref="confirmRef" />

  <v-data-table
    :headers="headers"
    :items="materials_and_assembles"

    :search="search"
    :custom-filter="customFilter"

    fixed-header
    density="comfortable"
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
    :items-per-page-options="footerOptions"
    item-key="name"
    items-per-page="5"
    :sort-by.sync="sortBy"
    :sort-desc.sync="sortDesc"
    class="elevation-10 custom-table"
  >
    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="d-flex align-center pe-2" style="font-weight:700; min-height:86px; height:86px;">
          加工區領料生產報工
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

           <!-- 組裝區來料異常備註 -->
          <div class="pa-4 text-center">
            <v-dialog v-model="abnormalDialog" max-width="500">
              <!--取消最大高度限制，讓卡片內容可以顯示完整-->
              <!--消自動捲軸，完全依內容高度決定是否超出-->
              <v-card :style="{ maxHeight: 'unset', overflowY: 'unset' }">
                <v-card-title class="text-h6 sticky-title text-center" style="background-color: #1b4965; color: white;">
                  組裝區來料異常備註
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

          <div style="display: flex; flex-direction: column; align-items: center;">
            <!--客製化搜尋-->
            <v-text-field
              id="bar_code"

              v-model="search"

              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              single-line
              style="position: relative; top: 45px; right: 250px; min-width: 150px;"
              density="compact"
            />

            <!-- 客製化barcode輸入 -->
            <v-text-field
              id="bar_code"
              v-model="bar_code"
              :value="bar_code"
              ref="barcodeInput"
              @keyup.enter="handleBarCode"
              hide-details="auto"
              prepend-icon="mdi-barcode"
              style="min-width:200px; position: relative; top: 15px; right: 50px;"
              class="align-center"
              density="compact"
            />
          </div>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '訂單編號' (order_num) 欄位的表頭 -->
    <template v-slot:header.order_num="{ column }">
      <v-hover v-slot="{ isHovering, props }">
        <div
          v-bind="props"
          style="display: flex; align-items: center; justify-content: center; cursor: pointer;"
          @click="toggleSort('order_num')"
        >
          <div>{{ column.title }}</div>
          <div style="min-width: 24px;">
            <!-- 僅在滑鼠移入或者正在排序的情況下顯示圖標 -->
            <v-icon v-if="sortBy.includes('order_num') && isHovering" style="margin-left: 2px;">
              {{ sortDesc[sortBy.indexOf('order_num')] ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
              <!--{{ sortDesc[0] === null ? 'mdi-minus' : (sortDesc[0] ? 'mdi-arrow-down' : 'mdi-arrow-up') }}-->
            </v-icon>
          </div>
        </div>
        <div style="color: #0000FF; font-size: 12px; margin-top: 2px; font-weight: 600; text-align: center; padding-right: 22px;">
          (工序)
        </div>
      </v-hover>
    </template>

    <!-- 客製化 '物料編號' (material_num) 欄位的表頭 -->
    <template v-slot:header.material_num="{ column }">
      <div style="left:20px; position:relative;">{{ column.title }}</div>
    </template>

    <!-- 客製化 '需求數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div>需求</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '領料數量' (delivery_qty) 欄位的表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div>領料</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '應領取數量' (must_receive_qty) 欄位的表頭 -->
    <template v-slot:header.must_receive_qty="{ column }">
      <div style="text-align: center;">
        <div>應領取</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div>

        <div style="color:black; font-size:12px; margin-right:20px; margin-left: -15px;">
          <v-icon
            style="color: green;"
            @click.stop="onDelete(item)"
            small
          >
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}
        </div>
        <div style="color:#0000FF; font-size:12px; font-weight:400; margin-right: 10px;">
          {{ item.assemble_work }}
          <span style="color:#FF2C2C; font-weight:600;">{{ item.isStockIn }}</span>
        </div>
      </div>
    </template>

    <!-- 自訂 '物料編號' 欄位的資料欄位 -->
    <template v-slot:item.material_num="{ item }">
      <div>
        <div>{{ item.material_num }}</div>
        <div :style="getStatusStyle(item.assemble_process_num)">{{ item.assemble_process }}</div>
      </div>
    </template>

    <!-- 自訂 '應領取數量'欄位的資料欄位 -->
    <template v-slot:item.must_receive_qty="{ item }">
      <div style="display: flex; align-items: center;">
        <!--
        <template v-if="item.process_step_code == 3 && item.is_copied_from_id == null">
          <v-icon
            style="transition: opacity 0.3s ease, visibility 0.3s ease;  margin-left: -10px;"
            :style="{ opacity: (currentUser.perm == 1 || currentUser.perm == 2)  ? 1 : 0, visibility: (currentUser.perm == 1 || currentUser.perm == 2) ? 'visible' : 'hidden' }"
            @click="addAbnormalInMaterial(item)"
            size="16"
            class="mr-2"
            :color="item.Incoming1_Abnormal ? 'light-blue lighten-3':'red lighten-4'"
          >
            mdi-bell-plus
          </v-icon>
          <span style="margin-left: 15px;">
            {{ item.must_receive_qty }}
          </span>
        </template>
        <template v-else>

        <template>
          -->
          <span style="margin-left: 25px;">
            {{ item.must_receive_qty }}
          </span>
          <!--
        </template>
      -->
      </div>
    </template>

    <!-- 自訂 '說明' 欄位的資料欄位 -->
    <template v-slot:item.comment="{ item }">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span
            style="text-align:left; position:relative; right:15px;"
            class="ellipsis-cell"
            v-bind="props"
          >
            {{ item.comment || '' }}
          </span>
        </template>
        <div class="tooltip-content">
          {{ item.comment || '' }}
        </div>
      </v-tooltip>
    </template>

    <!-- 自訂 '交期' 欄位的資料欄位 -->
    <template v-slot:item.delivery_date ="{ item }">
      <span style="text-align:left; position:relative; right:15px;">
        {{ item.delivery_date }}
      </span>
    </template>

    <!-- 自訂 gif 按鍵欄位 -->
    <template v-slot:item.gif="{ item, index }">
      <!--
      <div
        v-if="isGifDisabled(item)"
        class="text-caption"
        style="font-weight:700; position:relative; display:inline-block;"
      >
        廠內加工沒有領料
      </div>

      <v-hover v-slot:default="{ isHovering, props }" v-else>
      -->
      <v-hover v-slot:default="{ isHovering, props }">
        <div
          v-bind="props"
          style="position: relative; display: inline-block;"
          @mouseenter="handleGifClick(item, index); hoveredItemIndex = index; isTableVisible = true;"
          @mouseleave="hoveredItemIndex = null; isTableVisible = false;"
        >
          <img
            v-if="!isGifDisabled(item)"
            :src="isHovering ? animationImageSrc : staticImageSrc"
            alt="GIF"
            style="width: 25px; height: 25px;"
          />
          <!-- 動態顯示表格 -->
          <div
            v-if="isTableVisible && currentBoms.length > 0 && !isGifDisabled(item)"
            :style="adjustTablePosition"
          >
            <v-table style="width: 190px; overflow: hidden;" class="show_table">
              <thead>
                <tr>
                  <th style="text-align: left;">編號</th>
                  <th style="text-align: right;">數量</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(bom_item, index) in currentBoms"
                  :key="index"
                  :style="{backgroundColor: index % 2 === 0 ? '#ffffff' : '#edf2f4'}"
                  class="custom-row"
                >
                  <td style="text-align: left;">{{ bom_item.material_num }}</td>
                  <td style="text-align: right;">{{ bom_item.qty }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="2">
                    共 {{ currentBoms.length }} 項
                  </td>
                </tr>
              </tfoot>
            </v-table>
          </div>
        </div>
      </v-hover>
    </template>

    <!-- 自訂 '開始' 按鍵欄位 -->
    <template #item.action="{ item }">
      <!-- 開始鍵左側顯示「自己」的計時值 -->
      <span v-if="isMineStarted(item)"
        style="
          position: relative;
          left: 70px;
          color:#4000ff;
          width:88px;
          min-width:88px;
          font-variant-numeric:tabular-nums;"
      >
        <TimerDisplay
          :fontSize="18"
          :autoStart="false"

          :show="true"

          :key="`${item.id}:${item.assemble_id}:${item.process_step_code}:${currentUser.empID}`"

          :ref="el => setTimerEl(item, el)"
          :isPaused="isPausedOf(item)"
          @update:isPaused="val => setPausedOf(item, val)"
          @update:time="ms => onTickOf(item, ms)"

          class="me-2"
          style="min-width:88px; display:inline-block;"
        />
      </span>
      <!-- 綠點：這筆「有人」在開工（不限本人） -->
      <!--
      <v-badge
        :key="`badge-${item.index}-${item.count}`"
        v-bind="badgeProps(item)"
        :content="item.count"
        color="green"
        offset-x="6"
        offset-y="6"
        class="me-1"
      >
      -->
        <v-btn
          size="small"
          variant="tonal"

          style="font-size:14px; font-weight:700; font-family: '微軟正黑體', sans-serif;"
          :style="isMineStarted(item) ? { position: 'relative', left: '70px' } : {position: 'relative', left: '117px'}"

          @click="onClickBegin(item)"
          prepend-icon = "mdi-play"
          color="indigo-darken-4"

        >
          <v-icon start style="font-weight:700;">mdi-timer-outline</v-icon>
          開 始
        </v-btn>
      <!--
      </v-badge>
      -->
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, nextTick, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount, onDeactivated } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';

import TimerDisplay from "./TimerDisplayProcess.vue";
import { useProcessTimer } from "../mixins/useProcessTimerProcess.js";
import ConfirmDialog from "./confirmDialog";

import eventBus from '../mixins/enentBus.js';

import { useRoute } from 'vue-router';

const search = ref('');

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { assembles_active_user_count, boms, socket_server_ip }  from '../mixins/crud.js';
import { begin_count, end_count }  from '../mixins/crud.js';

import { materials_and_assembles }  from '../mixins/p_crud.js';
import { currentBoms, }  from '../mixins/p_crud.js';

import { apiOperation }  from '../mixins/crud.js';
import { p_apiOperation }  from '../mixins/p_crud.js';

// 使用 apiOperation 函式來建立 API 請求

//=== tables維護用 api ==

const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

const copyAssemble = apiOperation('post', '/copyAssemble');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const updateAssembleAlarmMessage = apiOperation('post', '/updateAssembleAlarmMessage');
const getActiveCountMap = apiOperation('post', '/getActiveCountMap');
const getCountMaterialsAndAssemblesByUser = apiOperation('post', '/getCountMaterialsAndAssemblesByUser');

const getMaterialsAndAssembles = apiOperation('post', '/getMaterialsAndAssembles');

//=== p_tables維護用 api ==

const listMaterialsAndAssembles = p_apiOperation('get', '/listMaterialsAndAssemblesP');

const getBoms = p_apiOperation('post', '/getBomsP');

const removeMaterialsAndRelationTable = p_apiOperation('post', '/removeMaterialsAndRelationTableP');

const updateMaterial = p_apiOperation('post', '/updateMaterialP');
const updateAssembleMustReceiveQtyByMaterialIDAndDate = p_apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialIDAndDateP');
const updateAssemble = p_apiOperation('post', '/updateAssembleP');

//=== component name ==
defineComponent({ name: 'PickReportForProcessBegin' });

//=== mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
// 刪除對話框相關
const deleteTitle = ref('刪除工單');
const deleteMessage = ref('此操作將刪除相關資料(BOM/Assemble/Process)，確定？');
const confirmRef = ref(null);

const animationImageSrc = ref(require('../assets/document-hover-swipe.gif'));
const staticImageSrc = ref(require('../assets/document-hover-swipe.png'));
const hoveredItemIndexForReqQty = ref(null);
const inputIDs = ref([]);

const showBackWarning = ref(true);

const station2_trans_ready = ref(false);    // false:堆高機沒有動作
const station2_trans_empID = ref('');
const station2_trans_empName = ref('');
const station2_trans_show1 = ref(false);
const station2_trans_password = ref('password');
const requiredRule = value => !!value || '必須輸入資料...';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';


const bar_code = ref('');
const barcodeInput = ref(null);

const hoveredItemIndex = ref(null); // 追蹤目前懸停在哪一筆資料上的 index
const isTableVisible = ref(false);  // 用來控制表格是否顯示
// 滑鼠位置(x, y)
const mouseX = ref(0);
const mouseY = ref(0);

const route = useRoute();   // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

//            0         1        2          3        4            5           6            7           8            9
//const str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc',]
//const str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '檢驗作業中', 'aa/bb/cc', '雷射作業中', 'aa/bb/00',]
//             0        1              2                3               4                 5              6              7            8
const str2=['未領料', '領料中',      '領料已完成',       '等待加工作業',  '加工作業進行中',  '加工作業已完成', '等待入庫作業', '入庫進行中', '入庫完成']


const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num', width:220 },
  { title: '物料編號', sortable: false, key: 'material_num', width:170},
  { title: '需求數量', sortable: false, key: 'req_qty', width:70 },
  { title: '領料數量', sortable: false, key: 'delivery_qty', width:70 },
  { title: '應領取數量', sortable: false, key: 'must_receive_qty', width:100 },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:100 },
  { title: '交期', align: 'start', sortable: false, key: 'delivery_date', width:110 },
  { title: '', sortable: false, key: 'gif' },
  { title: '', sortable: false, key: 'action', width:360 },
];
// 初始化Socket連接
const app_user_id = 'user_chumpower';
const clientAppName = 'PickReportForProcessBegin';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user_id, clientAppName);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const receive_qty_alarm = ref('');

//const outputStatus = ref({
//  step1: null,
//  step2: null
//});

const currentUser = ref({});
const componentKey = ref(0) // key 值用於強制重新渲染

const pagination = reactive({
  itemsPerPage: 5,              // 預設值, rows/per page
  page: 1,
});

const panelX = ref(820);
const panelY = ref(10);
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

const screenSizeInInches = ref(null);

const abnormalDialogBtnDisable = ref(true);
const abnormalDialog = ref(false);
const abnormalDialog_order_num = ref('');
const abnormalDialog_delivery_qty = ref('');
const abnormalDialog_must_receive_qty = ref('');
const abnormalDialog_new_must_receive_qty = ref('');
const abnormalDialog_message = ref('');
const abnormalDialog_display = ref(true);

const abnormalDialog_record = ref(null);

const timerMap = new Map();

let __disposedAll = false;

const PROCESS_TYPES = ['21', '22', '23']
const countsByType = ref({ '21': {}, '22': {}, '23': {} })
const activeMap = reactive({
  '21': {}, '22': {}, '23': {}
})

const selectedAsmId = ref(null);

//=== watch ===
//setupGetBomsWatcher();

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

/*
watch(hoveredItem, async (item) => {
  if (!item) {
    boms.value = []
    return
  }

  await getBoms({ id: item.id })
  boms.value = [...currentBoms.value]
},
{ immediate: true })
*/
//=== computed ===
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0',
}));

const routeName = computed(() => route.name);

// 計算懸浮表格的位置，根據資料筆數動態調整高度
const adjustTablePosition = computed(() => ({
  position: 'fixed',
  //top: `${mouseY.value + 10}px`,
  //left: `${mouseX.value - 150}px`,

  top: '80px',      // 固定上邊距離
  right: '190px',   // 固定左邊距離

  backgroundColor: 'white',
  padding: '5px',
  borderRadius: '5px',
  boxShadow: '0px 2px 10px rgba(0, 0, 0, 0.1)',
  fontSize: '10px',
  color: '#333',
  whiteSpace: 'nowrap',
  width: '190px',
  zIndex: 999,
  margin: '0 3px',
  height: `${currentBoms.length * 15}px`, // 根據資料筆數動態調整高度
  overflowY: 'hidden', // 禁止垂直滾動條
  overflowX: 'hidden', // 禁止水平滾動條
}));

const userId = computed(() => currentUser.value.empID ?? '')

// index -> idx (0-based)
const indexToIdx = computed(() => {
  return new Map(
    materials_and_assembles.value.map((item, i) => [item.index, i]),
  );
});

// index -> count
const indexToCount = computed(() => {
  const m = new Map();
  const rows = materials_and_assembles.value ?? [];
  const counts = assembles_active_user_count.value ?? [];
  for (let i = 0; i < rows.length; i++) {
    m.set(rows[i].index, Number(counts[i] ?? 0));
  }
  return m;
});

//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleBegin.vue, mounted()...");

  // 通知合併工單顯示, 進行handleMaterialUpdate
  eventBus.on('merge_work_orders', handleMaterialUpdate);

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);

  if (screenSizeInInches.value != null) {
    panelX.value = screenSizeInInches.value > 20 ? 1250 : 625;
    panelY.value = screenSizeInInches.value > 20 ? 21 : 21;
  }
  //+++

  // 阻止直接後退
  ////history.pushState(null, null, document.URL)
  //window.history.pushState(null, null, document.URL)
  // 阻止直接後退，但保留 Vue Router 的 state
  window.history.replaceState(window.history.state, '', document.URL);
  window.addEventListener('popstate', handlePopState)

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
  console.log("currentUser:", currentUser.value.empID);

  // 取得每個 v-text-field 的唯一 ID
  inputIDs.value.forEach((item) => {
    const myIdField = document.getElementById(`receiveQtyID-${item.assemble_id}`);
    myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  });

  // 在組件掛載時添加事件監聽器
  window.addEventListener('mousemove', updateMousePosition);

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }

  //await initialize_for_mounted();

  await listMaterialsAndAssembles()
  //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

  await nextTick()
  materials_and_assembles.value.forEach(r => getT(r))     // 先建好 t
  await nextTick()
  await restoreAllMyTimers()                              // 逐列 t.restoreProcess(...)
  //2025-11-18 await refreshActiveCounts()
  //2025-11-18 pollId = setInterval(refreshActiveCounts, refreshPollIdTimerMs.value)

  //處理socket連線
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();
    // 燈號
    socket.value.on('station2_loading_ready', async(data) => {
      const num = parseInt(data.message, 10);

      activeColor.value='yellow';  // 物料進站

      if ([1, 2, 3].includes(num)) {
        const temp_msg = `物料已經進入第${num}號裝卸站!`;
        console.warn(temp_msg);
        //activeColor.value='yello';  // 物料進站
        //showSnackbar(temp_msg, 'yellow lighten-5');
      } else {
        console.error('接收到不合法的裝卸站號碼:', data.message);
      }
    });
    // 燈號
    socket.value.on('station2_agv_begin', async () => {
      activeColor.value='SeaGreen';   // 物料出站
    })
    // 燈號
    socket.value.on('station3_agv_end', async (data) => {
      activeColor.value='DarkOrange';   //物料送達成品區
    })
    // 燈號
    socket.value.on('station1_agv_ready', async () => {
      activeColor.value='blue';   // 機器人進入組裝區
    })

    socket.value.on('station2_trans_ready', async (data) => {
      console.log("收到 station2_trans_ready訊息...", data);
      //station2_trans_empID.value =data.empID;
      //station2_trans_empName.value =data.empName;
      station2_trans_ready.value = true;
      forkliftNoticeFun();

      await initialize_for_created();
      //initialize();
    })

    socket.value.on('triggerLogout', async (data) => {
      console.log("收到 triggerLogout 強迫登出訊息，empID:", data.empID, "目前 empID:", currentUser.value.empID);

      if (data.empID && data.empID === currentUser.value.empID) {
        console.log("本裝置符合 empID，執行強制登出流程");

        let payload = {
          itemsPerPage: 0,
          seeIsOk: '0',
          lastRoutingName: 'Main',
          empID: currentUser.value.empID,
        };

        try {
          await updateSetting(payload);
        } finally {
          localStorage.setItem('Authenticated', false);
          removelocalStorage();
          //#
          sessionStorage.removeItem('auth_user');  // 刪掉使用者
          //#
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
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  window.removeEventListener('popstate', handlePopState)

  //clearInterval(intervalId);
  window.removeEventListener('mousemove', updateMousePosition);

  //clearInterval(blinkInterval);

  eventBus.off('merge_work_orders', handleMaterialUpdate)

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);
  //+++

  disposeAllTimersOnce();
});

// 在各種離開情境下都要收尾
onBeforeRouteLeave(() => { disposeAllTimersOnce(); });

onDeactivated(() => { disposeAllTimersOnce(); });

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize_for_created();
  //initialize();
});

onBeforeUnmount(() => {
  //2025-11-18 if (pollId)
  //2025-11-18   clearInterval(pollId);
});

//=== method ===
const KEY = 'material' // 'material' 或 'assemble'

const keyOf = (row, uId) => `${row.id}:${row.assemble_id}:${row.process_step_code}:${uId}`

const getT = (row) => useRowTimer(row, currentUser.value.empID)

function setTimerEl(row, el) {
  if (!row || !row.id) {
    console.warn('setTimerEl(): row undefined', row)
    return
  }
  const t = getT(row);
  if (t)
    t.timerRef.value = el || null;
}

// ---- 收尾清理（Begin 專用：含輪詢計時器）----
function disposeAllTimersOnce() {
  if (__disposedAll) return;
  __disposedAll = true;

  try {
    // 1) 逐一釋放每列的 useProcessTimer 實例
    for (const t of timerMap.values()) {
      try { t?.dispose?.(); } catch (_e) {}
    }
  } finally {
    timerMap.clear();
  }

  /* //2025-11-18
  // 2) 清掉頁面用的輪詢（Begin.vue 有使用）
  try {
    if (typeof pollId !== 'undefined' && pollId) {
      clearInterval(pollId);
      // @ts-ignore
      pollId = null;
    }
  } catch (_e) {}
  */
}

// 下面這三個轉接器, 可避免在模板裡出現「函式呼叫＋屬性賦值」，VS Code 會比較乾淨

// 取得／設定 isPaused（避免在模板裡對函式呼叫結果賦值）
//const isPausedOf = (row) => getT(row).isPaused
const isPausedOf  = (row) => getT(row)?.isPaused.value ?? true;

const setPausedOf = (row, v) => {
  const t = getT(row);

  //透過雙重否定，強制把任何輸入轉成純布林（truthy → true，falsy → false）
  //例如 1/"yes" 會變 true，0/""/null/undefined 會變 false
  //如果 t 存在且有 isPaused 這個 ref，就把它的值設成布林化後的 v
  if (t?.isPaused) t.isPaused.value = !!v
}

// 轉接 onTick（避免直接把函式呼叫結果當 handler）
const onTickOf = (row, ms) => {
  console.log("onTickOf..")

  const t = getT(row)
  t?.onTick?.(ms)
}

function onTimeUpdate(row, ms) {
  onTickOf(row, ms)
}

// 依 row.process_step_code → process_type
function processTypeOf(row) {
  console.log("processTypeOf:", row.process_step_code)

  const step = Number(row.process_step_code ?? 0)
  return step
  //const work = row.assemble_work
  //if (step === 3 || (step === 0 && work.includes('B109'))) return 21  // 組裝
  //if (step === 2 || (step === 0 && work.includes('B110'))) return 22  // 檢驗
  //if (step === 1 || (step === 0 && work.includes('B106'))) return 23  // 雷射
}

// 以 material 為粒度，idKey 取 material_id（列表裡是 id=material.id）
// 若後端已支援 assemble 粒度，改成 row.assemble_id 並把 key 換成 'assemble'
function idOf(row) {
  return row.id;
  //return KEY === 'assemble' ? (row.assemble_id ?? null) : (row.id ?? row.material_id ?? null)
}

async function restoreAllMyTimers() {
  const me = currentUser.value.empID      // 你用的登入人員代號
  const rows = materials_and_assembles.value || []
  for (const row of rows) {
    const t = getT(row)
    console.log("t:", t)
    if (!t?.restoreProcess) continue
    try {
      // 讓後端回傳 elapsed / paused 狀態；restoreOnly=true 不會重寫 begin_time
      await t.restoreProcess(row.id, row.process_step_code, me, row.assemble_id)
      // useProcessTimerBegin.js 內已處理：paused 就 pause；running 就啟動本地 ticker + autoUpdate
    } catch (e) {
      console.warn('restore fail for row', row.id, e)
    }
  }
}

/* //2025-11-18
async function refreshActiveCounts() {
  console.log("@@@refreshActiveCounts...")

  const rows = materials_and_assembles.value || []
  if (!rows.length) return

  // 準備查詢分組
  const groups = { '21': [], '22': [], '23': [] }
  for (const row of rows) {

    console.log("row: ", row)

    const pt = String(processTypeOf(row))
    console.log("pt: ", pt)
    if (row.id != null) groups[pt].push(Number(row.id))
  }

  // 呼叫 API
  const res = await getActiveCountMap({
    key: 'material',
    groups
  })
  console.log('getActiveCountMap:', res)

  // 正規化回傳
  const incoming = (res && res.counts) ? res.counts : {}

  // ✅ 重點：維持每個 activeMap[pt] 的「同一個物件引用」，
  // 先清空，再覆蓋新資料
  for (const pt of PROCESS_TYPES) {
    const dst = activeMap[pt]            // 既有 reactive 物件
    const src = incoming[pt] || {}       // 新資料（可能不存在）

    // 1) 清空舊 key
    for (const k of Object.keys(dst)) delete dst[k]

    // 2) 覆蓋新 key
    for (const [id, cnt] of Object.entries(src)) {
      dst[String(id)] = Number(cnt) || 0
    }
  }

  //（可選）如果你還在每列上放快取欄位，這裡同步一下：
  for (const row of rows) {
    const pt = String(processTypeOf(row))
    const id = String(row.id)
    row.active_user_count = Number(activeMap[pt][id] || 0)
  }

  await listMaterialsAndAssembles();

  let payload = {
    user_id: currentUser.value.empID,
  };
  await getCountMaterialsAndAssemblesByUser(payload);
}
*/

/*
async function restoreMyTimers() {
  const uid = currentUser.value.empID
  if (!uid) return
  for (const row of materials_and_assembles.value || []) {
    const t = getT(row)
    try {
      await t.startProcess(row.material_id ?? row.id, processTypeOf(row), uid, row.assemble_id)
      // 不 toggle，避免誤開暫停的工單
    } catch(e) {
      console.debug('restore timer skip', row.id, e);
    }
  }
}
*/
function makeStub() {
  const isPaused = ref(true)
  return {
    isPaused,
    timerRef: { value: null },
    onTick: () => {},
    startProcess: async () => {},
    toggleTimer: async () => {},
    processId: ref(null),
  }
}

const isMineStarted = (row) => {
  const t = getT(row)
  // 只要「我」對這筆有 active process（hook 恢復或新開），就顯示我的 Timer
  //console.log("Boolean(t.processId.value):",Boolean(t.processId.value))
  return Boolean(t.processId.value)
}

// 讓每個 row 取到自己的 timer（沒有就建一個）
function useRowTimer(row, currentUserId) {
  console.log("useRowTimer(), row, currentUserId:", row, currentUserId);

  // 🔐 防呆：row 或 id 不存在，回 stub
  if (!row || !row.id) {
    console.warn('useRowTimer(): row is undefined or has no id', row, currentUserId)
    return makeStub()
  }

  /*
  const rowKey = row.id ?? row.assemble_id ?? row.material_id
  if (rowKey == null) {
    // 防守：渲染很早或資料異常時，回一個不會炸的空實例
    return {
      timerRef: { value: null },
      isPaused: true,
      onTick: () => {},
      startProcess: async () => {},
      toggleTimer: async () => {},
      processId: { value: null },
    }
  }

  const key = `${rowKey}:${currentUserId}`
  */
  const key = keyOf(row, currentUserId)
  if (!timerMap.has(key)) {
    const timerRef = ref(null)
    const t = useProcessTimer(() => timerRef.value)     // hook
    console.log("t:", t)
    // t 內有：isPaused(ref)、elapsedMs(ref)、processId(ref)、onTick(fn)...

    // 收斂清理方法（清掉本地 ticker / 狀態）
    t.dispose = () => {
      try { t._stopLocalTicker?.() } catch (e) {}
      try { t.onTick = () => {} } catch (e) {}
      // 如有 setInterval / requestAnimationFrame 也在 hook 內清
    }

    timerMap.set(key, { ...t, timerRef })
  }
  return timerMap.get(key)
}

// 這筆是否有人在開工（顯示綠點）
function hasAnyoneStarted(row) {
  const t = getT(row) // 你的 useRowTimer 物件
  const idx = materials_and_assembles.value.findIndex(item => item.index === row.index);
  const pos = idx >= 0 ? idx + 1 : null;
  console.log("@@@@t?.processId?.value: ",t)
  console.log("@@@@t?.processId?.value: ",t, t.processId.value, t.isPaused.value)
  console.log("@@@@pos: ", pos, "user count:", assembles_active_user_count.value[idx])
  return assembles_active_user_count.value[idx] > 0
  //return !!t?.processId?.value && t?.isPaused?.value === false // 自己已經按過開始鍵(不含暫停), 且正在跑
  //return !!t?.processId?.value    // 自己按過開始鍵(含暫停), 且正在跑

}

// 統一取得 row 的狀態（只算一次，O(1) 查 Map）
function getRowState(row) {
  const idx = indexToIdx.value.get(row.index);
  if (idx === undefined) {
    return { started: false, count: 0, pos: null };
  }
  const count = indexToCount.value.get(row.index) ?? 0;
  return {
    started: count > 0,     // 是否有人開始
    count,                  // 人數
    pos: idx + 1,           // 第幾個（1-based）
  };
}

// 提供 v-badge 需要的 props
function badgeProps(row) {
  console.log("&&&&&badgeProps()...")

  console.log("assembles_active_user_count: ", assembles_active_user_count.value)

  const { started, count } = getRowState(row);

  const targetIndex = materials_and_assembles.value.findIndex(
    (kk) => kk.index === row.index
    //(kk) => kk.index === selectedAsmId.value
  );
  console.log("targetIndex:", targetIndex)

  console.log("count:", count)
  //if (materials_and_assembles.value[targetIndex].index==selectedAsmId.value && selectedAsmId.value ==null ) {
  materials_and_assembles.value[targetIndex].count=count
  //selectedAsmId.value =null;
  //}

  console.log("materials_and_assembles:", materials_and_assembles.value[targetIndex])

  return {
    modelValue: started, // 對應 :model-value
    //content: count,      // 對應 :content（若想點狀顯示就不要設 content）
  };
}

function reachTarget(row) {
  return Number(row.total_ask_qty_end || 0) >= Number(row.must_receive_end_qty || 0)
}

async function nudgeResume () {
  // 某些情況（列表虛擬化/初裝載）第一次 resume 可能沒有接上 interval
  timer()?.resume?.()
  await new Promise(r => setTimeout(r, 30))
  timer()?.resume?.()
}

const onClickBegin =  async (row) => {
  console.log("onClickBegin(), row", row);

  if (!row || !row.id) {
    showSnackbar("資料異常，按鍵無效!", "red-darken-2")
    return
  }

  const t = getT(row) // 以 (row.id + step + userId) 當 key
  if (!t) {
    showSnackbar("計時器尚未準備好!", "red-darken-2")
    return
  }

  console.log("t.processId.value:", t.processId.value, t)

  if (t.processId?.value && t.hasStarted?.value && !t.isPaused?.value) {
    showSnackbar("已經領料了...", "orange-darken-2")
    return
  }

  await nextTick();

  selectedAsmId.value = row.index;

  // 1) 先 start（後端可能只建立/取回流程，仍為暫停狀態）
  if (!t.processId?.value) {
    await t.startProcess(row.id, row.process_step_code, currentUser.value.empID, row.assemble_id)
  }
  // 2) 立刻做一次 “恢復”（unpause, 以觸發後端寫入 begin_time
  console.log("t.isPaused:", t.isPaused.value)
  if (t.isPaused.value) {
    //await t.nudgeResume?.()
    await t.toggleTimer();    // paused -> active（後端寫 begin_time）
    t.isPaused.value =false;
  }

  await updateItem(row);

  //2025-11-18 await refreshActiveCounts();
}

const updateItem = async (item) => {
  console.log("PickReportForAssembleBegin, updateItem(),", item);

  let payload = {};
  let startTime = new Date();                                                         // 記錄當前結束時間
  let formattedStartTime = formatDateTime(startTime); //完工生產報工開始時間
  console.log("formattedStartTime:", formattedStartTime)

  console.log("startTime step 1...")
  // 記錄當前領料生產開始時間
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'currentStartTime',
    record_data: formatDateTime(new Date()),
  };
  await updateAssemble(payload);

  // 2.記錄當前途程領取數量
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'ask_qty',                 //領取數量
    record_data: Number(item.receive_qty),
  };
  await updateAssemble(payload);

  if (item.must_receive_end_qty==0) {
    // 2-a.紀錄該筆的完工應領取數量
    payload = {
      material_id: item.id,

      create_at: item.create_at,

      record_name: 'must_receive_end_qty',
      record_data: Number(item.receive_qty),
    };
    await updateAssembleMustReceiveQtyByMaterialIDAndDate(payload);
  }

  // 4.記錄當前領取總數量
  let total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'total_ask_qty',   //開始, /領取數量總數
    record_data: total,
  };
  await updateAssemble(payload);

  item.total_receive_qty ='(' + total.toString().trim() + ')';
  item.total_receive_qty_num = total;

  // 5.記錄當前領取人員工號
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'user_id',
    record_data: currentUser.value.empID,
  };
  await updateAssemble(payload);

  //if (item.assemble_work.includes('109')) {
  //  payload = {
  //    assemble_id: item.assemble_id,
  //    record_name: 'input_abnormal_disable',
  //    record_data: true,
  //  };
  //  await updateAssemble(payload);
  //}

  // 6.按開始鍵後, 記錄當前途程開始狀態顯示訊息
  payload = {
    order_num: item.order_num,
    record_name: 'show2_ok',
    //record_data: outputStatus.value.step1,
    record_data: 4,       // 加工作業進行中
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: item.assemble_id,
    record_name: 'show2_ok',
    //record_data: outputStatus.value.step1
    record_data: 4,       // 加工作業進行中
  };
  await updateAssemble(payload);

  item.assemble_process = str2[4]   // 加工作業進行中
  item.assemble_process_num = 4     // 加工作業進行中

  let temp = Number(item.req_qty)
  // 確認 已領取數量總數=需求數量(訂單數量)
  console.log("total == temp ?",total, temp)

  if (startDisabled(item)) {
    // 記錄當前紀錄, 不能再輸入
    payload = {
      assemble_id: item.assemble_id,
      record_name: 'input_disable',
      record_data: true,
    };
    await updateAssemble(payload);
    item.input_disable = true;
  }

  const key = `${item.id}:${item.assemble_id}:${item.process_step_code}:${currentUser.value.empID}`
  localStorage.setItem(`PROCESS_PR_END_SYNC_${currentUser.value.empID}`, `${key}|${Date.now()}`)
  console.log("key key:",`PROCESS_PR_END_SYNC_${currentUser.value.empID}`, key)

  //待待
  window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};

function startDisabled(row) {
  // 只要該站「已完成總和」達到「應完成數量」，Start 就 disable
  return Number(row.total_completed_qty || 0) >= Number(row.must_receive_end_qty || 0)
}

const handleSetLinks = (links) => {
  console.log("Received links:", links);
  updateNavLinks(links);
};

const handleMaterialUpdate = async ()  => {
  console.log("handleMaterialUpdate 被觸發！")

  await listMaterialsAndAssembles();
  //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

  // 等表格與 <TimerDisplay> 都掛好，ref 才拿得到
  await nextTick();

  // 還原「自己」未結束的計時器（把已在跑的 ms / 狀態灌回每列的 timer）
  await restoreAllMyTimers(); // ← 如果你的函式名是 restoreMyTimers，就用那個

  // 再抓「有人開工」的綠點數（不只自己）
  //2025-11-18 await refreshActiveCounts();
}

async function onDelete(item) {
  const ok = await confirmRef.value.open({
    title: deleteTitle.value,
    message: deleteMessage.value,
    okText: '確定',
    cancelText: '取消',
  })
  if (ok) {
    removeMaterialsAndRelationTableFun(item.id);

    //待待
    window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
  }
}


const removeMaterialsAndRelationTableFun = async (id) => {
  console.log("removeMaterialsAndRelationTableFun()...");

  console.log("id:", id);

  let ok = false;
  try {
    const result = await removeMaterialsAndRelationTable({id: id});
    // crud.js 直接回傳 res.data，後端 jsonify(True) 會得到布林 true
    ok = result === true;
    console.log("remove result:", result);
  } catch (err) {
    console.error("DELETE API failed:", err?.response?.status, err?.response?.data, err?.message);
    showSnackbar("刪除 API 失敗", 'red accent-2');
    return;
  }

  if (!ok) {
    showSnackbar("找不到目標或已被刪除。", 'red accent-2');
    return;
  }

  try {
    editDialog.value = false;

    await listMaterialsAndAssembles();
    //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

    showSnackbar("刪除工單完成!", 'green darken-1');
  } catch (err) {
    console.error("REFRESH failed:", err?.response?.status, err?.response?.data, err?.message);
    //showSnackbar("刪除成功，但刷新列表失敗。請稍後重試。", 'red accent-2');
    showSnackbar("刪除工單完成!", 'green darken-1');
  }
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    // 1) 先撈表格資料
    await listMaterialsAndAssembles();
    //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

    // 2) 補上欄位（這會影響渲染）
    // 為materials_and_assembles每個物件增加 pickBegin 屬性，初始為空陣列 []
    materials_and_assembles.value.forEach(item => {
      item.pickBegin = [];
      item.count = 0;
    });

    materials_and_assembles.value.map(it => ({
      ...it,
      pickBegin: Array.isArray(it.pickBegin) ? [...it.pickBegin] : [],
      count: typeof it.count === 'number' ? it.count : 0,
    }));

    // 3) 等表格與 <TimerDisplay> 都掛好，ref 才拿得到
    await nextTick();

    // 4) 還原「自己」未結束的計時器（把已在跑的 ms / 狀態灌回每列的 timer）
    await restoreAllMyTimers(); // ← 如果你的函式名是 restoreMyTimers，就用那個

    // 5) 再抓「有人開工」的綠點數（不只自己）
    //2025-11-18 await refreshActiveCounts();

    // 還原計時器（依後端真實狀態）
    //await restoreMyTimers();

    //2025-11-18 pollId = setInterval(refreshActiveCounts, refreshPollIdTimerMs.value);
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const initialize_for_created = async () => {
  await listMaterialsAndAssembles();
  //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

  materials_and_assembles.value.map(it => ({
    ...it,
    pickBegin: Array.isArray(it.pickBegin) ? [...it.pickBegin] : [],
    count: typeof it.count === 'number' ? it.count : 0,
  }));
};

const initialize_for_mounted = async () => {
  await nextTick();
  materials_and_assembles.value.forEach(r => getT(r));
  await nextTick();

  await restoreAllMyTimers();

  //2025-11-18 await refreshActiveCounts();

  //2025-11-18 if (pollId) clearInterval(pollId);
  //2025-11-18 pollId = setInterval(refreshActiveCounts, refreshPollIdTimerMs.value);
};

const customFilter =  (value, query, item)  => {
  return value != null &&
    query != null &&
    typeof value === 'string' &&
    value.toString().toLocaleUpperCase().indexOf(query) !== -1
}

const handleBarCode = () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)
  let myBarcode = materials_and_assembles.value.find(m => m.order_num == bar_code.value);

  // 在這裡做條碼比對、查詢、上傳等邏輯
  if (myBarcode) {
    console.log('找到條碼對應項目:', myBarcode.index);

    // focus到對應項目的欄位
    focusItemField(myBarcode);
  } else {
    showSnackbar('找不到對應條碼資料！', 'red accent-2');
    console.warn('找不到對應條碼資料!')
  }
}

const focusItemField = async (item) => {
  console.log("focusItemField()...");

  await nextTick() // 確保 DOM 已更新
  // 找到外層 v-text-field DOM
  const wrapper = document.getElementById(`receiveQtyID-${item.index}`);
  if (wrapper) {
    // 聚焦到 v-text-field 本身
    console.log("wrapper ok...")
    wrapper.focus();

    // 往內找真正的 <input> 元素
    const input = wrapper.querySelector('input');
    if (input) {
      input.focus();

      // 模擬按下 Enter 鍵事件
      const enterEvent = new KeyboardEvent('keyup', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true,
      });
      input.dispatchEvent(enterEvent);
    }
  } else {
    console.warn(`找不到欄位: receiveQtyID-${item.index}`)
  }
}

const forkliftNoticeFun = () => {
  console.log("forkliftNoticeFun()...");

  socket.value.emit('station2_trans_begin');

  station2_trans_ready.value = false;
}

/*
const handlePopState = () => {
  // 重新添加歷史紀錄以阻止實際後退
  history.pushState(null, null, document.URL)

  // 只在第一次顯示警告
  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面内的導航按鍵', 'red accent-2');
    showBackWarning.value = false
  }
}
*/
const handlePopState = () => {
  // ✅ 正確方式：保留 Vue Router 的 state
  ////history.pushState(history.state, '', document.URL);
  //window.history.pushState(history.state, '', document.URL);
  // 重新把這一筆 entry 的 state 改回 Router 給的 state
  window.history.replaceState(window.history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

//const isButtonDisabled = (item) => {
//  //return (item.whichStation != 2 || item.input_disable) || !item.process_step_enable || item.isLackMaterial ==0;
//  return item.whichStation != 2 || item.isLackMaterial ==0;
//};

const isGifDisabled = (item) => {
  //return item.whichStation != 2 || item.input_disable || !item.process_step_enable;
  //return item.whichStation != 2
  //return false
  return item.isShowBomGif;
};

const handleKeyDown = (event) => {
  const inputChar = event.key;

  const caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when CapsLock is on

  // 允許左右方向鍵、backspace 和 delete 鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar)) {
    event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
  }

  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入, 2025-07-02 modify
  if (inputValue.length > 5 && inputValue < 10000) {
    event.preventDefault();
    return;
  }

  // 偵測是否按下 Enter 鍵
  if (event.key === 'Enter' || event.keyCode === 13) {
    console.log('Return key pressed');
    // 如果需要，這裡可以執行其他操作，或進行額外的驗證
    //checkReceiveQty(event.target.item);  // 檢查接收數量的驗證
  }
};

const getStatusStyle = (status) =>{
  const colorMap = {
    0: '#ff0018',
    1: '#0000f9',
    2: '#669999',
    3: '#009acc',
    4: '#008018',
    5: '#86007d',
    6: '#ffa52c',
    7: '#008018',
  };

  return {
    color: colorMap[status],
    fontWeight: '600',
    fontSize: '12px',
  };
};

const addAbnormalInMaterial = (item) => {
  console.log("addAbnormalInMaterial(),", item);

  abnormalDialog_record.value = materials_and_assembles.value.find(m => m.assemble_id == item.assemble_id);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_delivery_qty.value = item.delivery_qty;
  abnormalDialog_new_must_receive_qty.value = item.must_receive_qty;
  abnormalDialog_must_receive_qty.value = item.must_receive_qty;
  abnormalDialog_display.value = item.Incoming1_Abnormal;

  abnormalDialog.value = true;
}

const createAbnormalFun = async () => {
  console.log("createAbnormalFun()...");

  if (abnormalDialog_new_must_receive_qty.value != abnormalDialog_must_receive_qty.value) {
    let temp_str = '(' + abnormalDialog_delivery_qty.value + ' / ' + abnormalDialog_new_must_receive_qty.value + ')'
    abnormalDialog_message.value = '備料區來料數量不對! '+ temp_str;
    console.log("temp_str:", temp_str);
    let payload = {}

    try {
      payload = {
        assemble_id: abnormalDialog_record.value.assemble_id,
        record_name: 'Incoming1_Abnormal',
        record_data: abnormalDialog_message.value,
      };
      await updateAssemble(payload);

      abnormalDialog_record.value.Incoming1_Abnormal=false;

      // targetIndex為目前table data record 的 index
      const targetIndex = materials_and_assembles.value.findIndex(
        (kk) => kk.id === abnormalDialog_record.value.id
      );

      if (targetIndex !== -1) {
        // 用 Vue 的方式確保觸發響應式更新
        materials_and_assembles.value[targetIndex] = {
          ...materials_and_assembles.value[targetIndex],
          Incoming1_Abnormal: false,
        };
      }

      console.log('更新成功...');
    } catch (error) {
      console.error('更新失敗:', error.response?.data?.message || error.message);
    }
  }
  abnormalDialog.value = false;
}

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

const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const toggleSort = (key) => {
  const index = sortBy.value.indexOf(key)

  if (index !== -1) {
    // 若目前已經是排序該欄位，則切換排序方向
    sortDesc.value[index] = !sortDesc.value[index]
  } else {
    // 否則新增排序欄位，並預設為升序
    sortBy.value = [key]
    sortDesc.value = [false]
  }
}

const refreshComponent = () => {
  console.log('更新訂單按鈕已點擊');

  // 透過重新加載當前路由，來刷新組件
  //router.go(0);

  // 改變 key 值，Vue 會重新渲染整個元件
  componentKey.value += 1;
};

// 滑鼠移入圖片，顯示表格
const handleGifClick = async (item, index) => {
  console.log(`GIF 點擊事件觸發，資料索引: ${index}, 資料內容:`, item);

  if (hoveredItemIndex.value === index && isTableVisible.value) {
    return;  // 如果表格已經顯示且資料已經加載，不再重複請求
  }

  hoveredItemIndex.value = index;
  isTableVisible.value = true;    // 設置表格可見

  await getBoms({id: item.id});
  //modify_boms.value = [...currentBoms.value];

  console.log('Current hovered item index:', hoveredItemIndex.value);
  console.log("bom[]:", currentBoms.value)
};

// 滑鼠移入表格時，保持表格顯示
//const onMouseEnterTable = () => {
//  isTableVisible.value = true;
//}

// 滑鼠移出圖片或表格時，隱藏表格
//const onMouseLeaveTable = () => {
//  isTableVisible.value = false;   // 隱藏表格
//  //hoveredItemIndex.value = null;  // 重置 hoveredItemIndex
//}

// 滑鼠位置偵測
const updateMousePosition = (event) => {
  mouseX.value = event.clientX;
  mouseY.value = event.clientY;
}

// 清除localStorage內容
const removelocalStorage = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
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

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th.v-data-table__th) {
  background-color: #85aef2;      // 自訂背景顏色
}

:deep(.v-data-table .v-table__wrapper > table > tbody tr:nth-of-type(odd)) {
   background-color: rgba(0, 0, 0, .05);
 }

:deep(.v-data-table-footer) {
  margin-bottom: -10px;
}

:deep(input[type="text"]) {
  min-height: 20px;
  height: 20px;
  opacity: 1;
  padding: 0px;
  text-align: center;
  color: red;
  min-width:60px;
  width:60px;
}

:deep(input#bar_code[type="text"]) {
  color: black !important;
}

.custom-table {
  //border-collapse: collapse;  // 合併邊框
  //border: 1px solid #000;     // 表格的外框
  border-radius: 0 0 20px 20px;
}

//:deep(.v-table) {
//  border-collapse: collapse; // 讓表格邊框不會分開
//}

//:deep(.v-table th, .v-table td) {
//  border: 1px solid #ddd;   // 邊框顏色
//}

:deep(.show_table thead th) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
  color:blue;
  font-family: '微軟正黑體', sans-serif; margin-top:10px;
}

:deep(.show_table tfoot td) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
  font-weight: 700;
  color:blue;
  text-align: center;
  font-family: '微軟正黑體', sans-serif; margin-top:10px;
}

:deep(.show_table tbody td) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.blink {
  animation: blink 1s infinite;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.ellipsis-cell {
  max-width: 100px;
  display: inline-block;     // 讓 ellipsis 生效
  overflow: hidden;
  text-overflow: ellipsis;   // 顯示 abcdef...
  white-space: nowrap;
  vertical-align: bottom;
}

.tooltip-content {
  max-width: 520px;          // 避免太寬，可調整
  white-space: pre-wrap;     // 保留換行
}

:deep(.v-table__wrapper > table > tbody td:first-child) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:first-child) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
</style>