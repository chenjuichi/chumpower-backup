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
      :items="materials_and_assembles_by_user"

      :search="search"
      :custom-filter="customFilter"

      fixed-header
      density="comfortable"
      style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
      :items-per-page-options="footerOptions"
      item-key="name"
      items-per-page="5"

      item-value="index"
      show-select
      :value="selectedItems"

      :sort-by.sync="sortBy"
      :sort-desc.sync="sortDesc"

      class="elevation-10 custom-table"

    >
      <!-- 客製化 '選擇框' 欄位表頭 -->
      <template v-slot:header.data-table-select>
        <span class="custom-header">送料</span>
      </template>

      <!-- 自定義每行的選擇框 -->
      <template v-slot:item.data-table-select="{ internalItem }">
        <v-checkbox-btn
          :model-value="isSelected(internalItem)"
          :disabled="!internalItem.raw.isShow || internalItem.raw.receive_qty == 0"
          color="primary"
          @update:model-value="toggleSelect(internalItem)"
          :class="{ 'blue-text': internalItem.raw.isShow}"
        />
      </template>

      <!-- 客製化 top 區域 -->
      <template v-slot:top>
        <v-card>
          <v-card-title class="d-flex align-center pe-2" style="font-weight:700;">
            組裝區完成生產報工
            <v-divider class="mx-4" inset vertical></v-divider>

            <!--客製化 員工選單-->
            <div style="position: relative; width: 160px; margin-right:5px;">
              <!-- v-text-field 用於顯示選中員工 -->
              <v-text-field
                v-model="selectedEmployee"
                @keyup.enter="handleEmployeeSearch"

                variant="outlined"
                density="comfortable"
                style="
                  min-width: 160px;
                  width: 160px;
                  position: absolute;
                  z-index: 2;
                  transition: opacity 0.3s ease, visibility 0.3s ease;
                "
                :style="{ opacity: showMenu ? 1 : 0, visibility: showMenu ? 'visible' : 'hidden' }"
              />

              <!-- v-select 用於選擇員工 -->
              <v-select
                v-model="inputSelectEmployee"
                :items="formattedDesserts"
                item-title="display"
                item-value="emp_id"
                :placeholder="placeholderTextForEmployee"
                variant="outlined"
                density="comfortable"
                @update:modelValue="updateEmployeeFieldFromSelect"
                style="
                  min-width: 160px;
                  width: 160px;
                  position: relative;
                  top: 23px;
                  z-index: 1;
                  transition: opacity 0.3s ease, visibility 0.3s ease;
                "
                :style="{ opacity: showMenu ? 1 : 0, visibility: showMenu ? 'visible' : 'hidden' }"
              />
            </div>

            <!--客製化 手動推車/AGV切換按鍵-->
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
                  <span>AGV送料</span>
                  <v-icon right color="#003171">mdi-truck-flatbed</v-icon>
                </v-btn>
              </v-btn-toggle>
            </div>

            <!--客製化 備料送出按鍵-->
            <v-btn
              :disabled="c_isBlinking"
              color="primary"
              variant="outlined"
              style="position: relative; top:0px; height:48px; font-weight: 700;"
              @click="callAGV"
            >
              <v-icon left color="blue">mdi-account-arrow-right-outline</v-icon>
              <span>組裝送出</span>
            </v-btn>

            <!-- 測試用訊息-->
            <!--
            <span
              :style="{
              'fontSize': '14px',
              'display': 'inline-block',
              'min-width': '120px',
              'visibility': (!isFlashLed && isCallAGV) ? 'visible' : 'hidden',
            }">
              {{order_num_on_agv_blink}}
            </span>
            -->

            <div style="display: flex; flex-direction: column; align-items: center;">
              <!-- 測試用黃綠燈-->
              <!--
              <div
                :style="{
                  display: 'inline-block',
                  borderRadius: '50%',
                  width: '25px',
                  height: '25px',
                  position: 'relative',
                  top: '0px',
                  left: '-90px',

                  opacity: isFlashLed && isVisible ? 1 : 0, // 根據 isFlashLed 和 isVisible 控制顯示
                  transition: 'opacity 0.5s ease',          // 過渡效果
                  background: background,                   // 背景顏色
                  border: '1px solid black'                 // 黑色邊框
                }"
              ></div>

              <div style="position: relative; top:0px; left: -90px;"></div>
            -->
              <!--客製化搜尋-->
              <v-text-field
                v-model="search"

                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                hide-details
                single-line
                style="position: relative; top: 55px; right: -50px; min-width: 150px;"
                density="compact"
              />

              <!-- 客製化barcode輸入 -->
              <v-text-field
                v-model="bar_code"
                :value="bar_code"
                ref="barcodeInput"
                @keyup.enter="handleBarCode"
                hide-details="auto"
                prepend-icon="mdi-barcode"
                style="min-width:200px; position: relative; top: 25px; left:280px;"
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

      <!-- 客製化 '作業數量' (req_qty) 欄位的表頭 2025-06-13 modify, 改順序 -->
      <template v-slot:header.req_qty="{ column }">
        <div style="text-align: center;">
          <div>需求</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '領取數量' (total_ask_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
      <template v-slot:header.total_ask_qty="{ column }">
        <div style="text-align: center;">
          <div>領取</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '應完成數量' (must_receive_end_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
      <template v-slot:header.must_receive_end_qty="{ column }">
        <div style="text-align: center;">
          <div>應完成</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '完成數量' (receive_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
      <template v-slot:header.receive_qty="{ column }">
        <div style="text-align: center;">
          <div>完成</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '異常數量' (abnormal_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
      <template v-slot:header.abnormal_qty="{ column }">
        <div style="text-align: center;">
          <div>異常</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 自訂 index 欄位的資料欄位 -->
      <template v-slot:item.index="{ item }">
        <!-- 空白顯示 -->
      </template>

      <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
      <template v-slot:item.order_num="{ item }">
        <div style="display: flex; align-items: center;">
          <div style="color: red; margin-right: 2px;" v-if="item.isTakeOk && item.isShow && item.isLackMaterial != 99">
            <div>
              {{ item.order_num }}&nbsp;&nbsp;
              <span style="font-weight: 700; font-size: 16px;">缺料</span>
            </div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div> <!--檢料完成-->
          <div style="color: blue; margin-right: 20px;" v-else-if="item.isTakeOk && item.isShow && item.isLackMaterial == 99">
            <div>{{ item.order_num }}</div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div> <!--檢料完成-->
          <div style="margin-right: 20px;" v-else>
            <div>{{ item.order_num }}</div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
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

      <!-- 自訂 '需求數量' 欄位的資料欄位 -->
      <!--<template v-slot:item.req_qty="{ item }">-->
        <!--
          v-bind="props":
          使用 v-bind 將 props 綁定到 div 上，使其具有 v-hover 的 hover 功能，
          當滑鼠移入或移出該 div 時，就能觸發 isHovering 的變化。

          isHovering:
          根據是否 hover 自動變為 true 或 false，用來控制 span 中的文字顯示。
        -->
      <!--
        <v-hover v-slot="{ isHovering, props }">
          <div
            v-bind="props"
            style="position: relative; display: inline-block;"
            @mouseenter="hoveredItemIndexForReqQty = index"
            @mouseleave="hoveredItemIndexForReqQty = null"
          >
            <div>
              <div>{{ item.req_qty }}</div>
              <div style="color: #a6a6a6; font-size:12px;">{{ item.total_receive_qty }}</div>
            </div>

            <span
              v-if="isHovering"
              style="
                position: absolute;
                top: -5px;
                left: 35px;
                background-color: white;
                padding: 5px;
                border-radius: 5px;
                box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1);
                font-size: 12px;
                color: #333;
                white-space: nowrap;
              "
            >
              目前領取順序為[
              <span v-for="(pickItem, idx) in item.pickEnd" :key="idx">
                {{ pickItem }}
                <span v-if="idx < item.pickEnd.length - 1">, </span>
              </span>
              ]
            </span>
          </div>
        </v-hover>
      </template>
    -->

      <template v-slot:item.must_receive_end_qty="{ item }">
        {{ item.must_receive_end_qty }}
      </template>

      <!-- 自訂 '完成數量' 輸入欄位 -->
      <template v-slot:item.receive_qty="{ item }">
        <div style="position: relative; display: inline-block;">
          <v-text-field
            v-model="item.receive_qty"
            dense
            hide-details
            style="max-width: 60px; text-align: center; z-index: 1;"
            :id="`receiveQtyID-${item.assemble_id}`"
            @keydown="handleKeyDown"
            @update:modelValue="checkReceiveQty(item)"
            @update:focused="(focused) => checkTextEditField(focused, item)"
            @keyup.enter="updateItem2(item)"
            :disabled="item.input_end_disable"
          />
          <span
            v-show="item.tooltipVisible"
            style="position: absolute; left: 60px; top: 0; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 700;"
          >
            {{ receive_qty_alarm }}
          </span>
        </div>
      </template>

      <!-- 自訂 '異常數量' 輸入欄位 -->
      <template v-slot:item.abnormal_qty = "{ item }">
        <div style="position: relative; display: inline-block;">
          <v-text-field
            v-model="item.abnormal_qty"
            dense
            hide-details
            style="max-width: 60px; text-align: center; z-index: 1;"
            :id="`abnormalQtyID-${item.assemble_id}`"
            @keydown="handleKeyDown"
            @update:modelValue="checkAbnormalQty(item)"
            @update:focused="(focused) => checkTextEditField(focused, item)"

            :disabled="item.input_abnormal_disable"
          />
          <span
            v-show="item.abnormal_tooltipVisible"
            style="position: absolute; left: 60px; top: 0; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 700;"
          >
            {{ abnormal_qty_alarm }}
          </span>
        </div>
      </template>

      <!-- 自訂 '說明' 欄位的資料欄位 -->
      <template v-slot:item.comment="{ item }">
        <div>
          <div style="text-align:left; color: #669999; font-size:12px; font-family: '微軟正黑體', sans-serif;">{{ item.comment }}</div>
        </div>
      </template>

      <!-- 自訂 '結束' 按鍵欄位 -->
       <!--
      z-index: 2;
              transition: opacity 0.3s ease, visibility 0.3s ease;
              "
            :style="{
              opacity: enableDialogBtn ? 1 : 0,
              visibility: enableDialogBtn ? 'visible' : 'hidden'}"
      -->
      <template v-slot:item.action="{ item }">
        <div class="action-cell">
          <v-btn
            size="small"
            class="mr-2"
            variant="tonal"
            :disabled="isButtonDisabled(item)"
            @click="updateItem(item)"
            color="indigo-darken-4"
            style="
              font-size: 13px;
              font-weight: 700;
              font-family: '微軟正黑體', sans-serif;
              padding-left:4px;
              padding-right:4px;
              margin-right:10px !important;
              "
          >
            結 束
            <v-icon color="indigo-darken-4" end>mdi-close-circle-outline</v-icon>
          </v-btn>

          <!-- 自訂 '異常' 按鍵欄位 -->
          <v-btn
            size="small"
            variant="tonal"

            @click="updateAbnormal(item)"
            :style="{
              fontSize: '13px',
              fontWeight: '700',
              fontFamily: '\'微軟正黑體\', sans-serif',
              marginLeft: '20px',
              paddingLeft: '4px',
              paddingRright: '4px',
              marginLeft: '0px !important',
              background: item.alarm_enable ? '#e8eaf6' : '#ff0000',
              color: item.alarm_enable ? '#000' : '#fff'
            }"
          >
            異 常
            <v-icon
              :style="{color: item.alarm_enable ? '#000' : '#fff'}"
              end
            >
              mdi-alert-circle-outline
            </v-icon>
          </v-btn>
        </div>
      </template>

      <template #no-data>
        <strong><span style="color: red;">目前沒有資料</span></strong>
      </template>
    </v-data-table>
  </div>
  </template>

<script setup>
import { ref, reactive, nextTick, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount } from 'vue';

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';

import { useRoute } from 'vue-router';
const search = ref('');

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

//import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';
import { materials_and_assembles_by_user }  from '../mixins/crud.js';
import { currentAGV }  from '../mixins/crud.js';
//import { desserts }  from '../mixins/crud.js';
import { desserts2 }  from '../mixins/crud.js';
import { socket_server_ip }  from '../mixins/crud.js';

import { apiOperation}  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');
const listUsers2 = apiOperation('get', '/listUsers2');
const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');

const updateAssembleMustReceiveQtyByMaterialID = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialID');
const copyNewAssemble = apiOperation('post', '/copyNewAssemble');
const updateAssembleMustReceiveQtyByAssembleID = apiOperation('post', '/updateAssembleMustReceiveQtyByAssembleID');
const getMaterialsAndAssemblesByUser = apiOperation('post', '/getMaterialsAndAssemblesByUser');
const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const updateAGV = apiOperation('post', '/updateAGV');
const getAGV = apiOperation('post', '/getAGV');
const updateAssembleProcessStep  = apiOperation('post', '/updateAssembleProcessStep');

//const getMaterial = apiOperation('post', '/getMaterial');

//=== component name ==
defineComponent({
  name: 'PickReportForAssembleEnd'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const history = ref(false);               // 設定歷史紀錄為不顯示

const isCallAGV = ref(false);             // 確認是否已經按了callAGV按鍵, true:已經按鍵了, 不能重複按鍵
const showMenu = ref(false);                  // 控制員工選單顯示
const placeholderTextForEmployee = ref('請選擇員工');
const inputSelectEmployee = ref(null);
const toggle_exclusive = ref(2);              // 控制選擇的按鈕, 預設AGV

const isVisible = ref(true);              // 設定初始狀態為顯示
const isFlashLed = ref(false);            // 控制是否閃爍Led
let intervalIdForLed = null;
const background = ref('#ffff00');

const hoveredItemIndexForReqQty = ref(null);  // 追蹤目前懸停在哪一筆資料上的 index

//let receiveQtyID_max_length = 3;
//const inputRefs = ref(new Map()); // 用來存放所有的 input refs
const inputIDs = ref([]);
const selectedItems = ref([]);          // 儲存選擇的項目 (基於 id)

const showBackWarning = ref(true);

const bar_code = ref('');
const barcodeInput = ref(null);

const route = useRoute();               // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  //{ value: 25, title: '25' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'index', width: 0, class: 'hidden-column' },
  { title: '訂單編號', sortable: true, key: 'order_num' },
  { title: '物料編號', sortable: false, key: 'material_num' },
  { title: '需求數量', sortable: false, key: 'req_qty', width:80 },
  //{ title: '備料數量', sortable: false, key: 'delivery_qty', width:100 }, // 2025-06-13 mark, 改順序
  { title: '領取數量', sortable: false, key: 'total_ask_qty', width:80 },
  { title: '應完成數量', sortable: false, key: 'must_receive_end_qty', width:100 },       // 2025-06-13 add, 改順序
  { title: '完成數量', sortable: false, key: 'receive_qty', width:80 },
  { title: '異常數量', sortable: false, key: 'abnormal_qty', width:80 },             // 2025-06-13 add, 改順序
  { title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '交期', sortable: false, key: 'delivery_date', width:110 },
  { title: '', sortable: false, key: 'action' },
];

const userId = 'user_chumpower';
const clientAppName = 'PickReportForAssembleEnd';

const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const receive_qty_alarm = ref('');
const abnormal_qty_alarm = ref('');

//const from_agv_input_order_num = ref('');
const isBlinking = ref(false);          // 控制按鍵閃爍
const order_num_on_agv_blink=ref('');

const selectedEmployee = ref(null);

//const inputStr = ref('');
const outputStatus = ref({
  step1: null,
  step2: null
});

const currentUser = ref({});
//const permDialog = ref(false);

const componentKey = ref(0)             // key值用於強制重新渲染

const periodTime = ref('');             // 記錄時間間距
//const currentStartTime = ref(null);  // 記錄開始時間

const agv1StartTime = ref(null);
const agv1EndTime = ref(null);
const agv2StartTime = ref(null);
const agv2EndTime = ref(null);

const pagination = reactive({
  itemsPerPage: 5, // 預設值, rows/per page
  page: 1,
});

const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const panelX = ref(830);
const panelY = ref(11);
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

const screenSizeInInches = ref(null);

// === watch ===

// 監視 selectedItems 的變化，並將其儲存到 localStorage
watch(selectedItems, (newItems) => {
  console.log("watch(), newItems:", newItems)
  localStorage.setItem('selectedItems', JSON.stringify(newItems));
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
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0',
}));

const routeName = computed(() => route.name);

const formattedDesserts = computed(() =>
  desserts2.value.map(emp => ({
    ...emp,
    display: `${emp.emp_id} ${emp.emp_name}`,
  }))
);

const c_isBlinking = computed(() => selectedItems.value.length === 0);

//const c_enableDialogBtn = computed(() => {
//return (item) => {
//  let temp = item.isTakeOk && !item.isShow;
//  console.log("c_enableDialogBtn() item.isTakeOk, !item.isShow, temp, !temp:", item.isTakeOk, !item.isShow, temp, !temp)
//  return temp;
//};
//});

//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleEnd.vue, mounted()...");

  //+++
  const dpi = window.devicePixelRatio || 1;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  //const dpiEstimate = 96 * dpi;
  const dpiEstimate = 96 * dpi;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);
  //+++

  // 阻止直接後退
  window.history.pushState(null, null, document.URL);
  //history.pushState(null, null, document.URL);
  window.addEventListener('popstate', handlePopState);

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

  // 取得每個 v-text-field 的唯一 ID
  inputIDs.value.forEach((item) => {
    const myIdField = document.getElementById(`receiveQtyID-${item.order_num}`);
    myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  });

  intervalIdForLed = setInterval(() => {
    isVisible.value = !isVisible.value;  // 每秒切換顯示狀態
  }, 500);

  isBlinking.value = materials_and_assembles_by_user.value.length == 0 || materials_and_assembles_by_user.value.every(item => !item.isAssembleStation1TakeOk && !item.isAssembleStation2TakeOk && !item.isAssembleStation3TakeOk);

  // 從 localStorage 中恢復 selectedItems
  let savedItems = localStorage.getItem('selectedItems');
  if (savedItems) {
    selectedItems.value = JSON.parse(savedItems);
  }

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }

  //處理socket連線
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();
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
    socket.value.on('station2_loading_ready', async(data) => {
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


    socket.value.on('station2_agv_start', async () => {
      console.log('AGV 運行任務開始，press Start按鍵, 收到 station2_agv_start 訊息');

      let payload = {};
      let targetItem = {};
      // 依據每個 item 的 material id 進行資料更新
      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (i) => i.index === item
        );
        console.log("targetItem:", targetItem)

        payload = {
          id: targetItem.id,
          record_name: 'show3_ok',
          record_data: 16,           // agv start
        };
        await updateMaterial(payload);

        payload = {
          assemble_id: targetItem.id,
          record_name: 'show3_ok',
          record_data: 16,
        };
        await updateAssemble(payload);

        //try {
        //  await updateMaterial(payload);
        //  console.log(`資料更新成功，id: ${item}`);
        //} catch (error) {
        //  console.error(`資料更新失敗，id: ${item}`, error);
        //}
      });
    });

    socket.value.on('station2_agv_begin', async () => {
      console.log('AGV暫停, 收到 station2_agv_begin 訊息');

      let payload = {};
      let targetItem = {};

      // 記錄agv在站與站之間運行開始時間
      agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2StartTime.value);

      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (i) => i.index === item
        );
        console.log("targetItem:", targetItem)

        payload = {
          id: targetItem.id,
          record_name: 'show3_ok',
          record_data: 10      // 設為 10，agv移動至成品區中
        };
        await updateMaterial(payload);

        payload = {
          assemble_id: targetItem.id,
          record_name: 'show3_ok',
          record_data: 10,
        };
        await updateAssemble(payload);

        //try {
        //  await updateMaterial(payload);
        //  console.log(`資料更新成功，id: ${item}`);
        //} catch (error) {
        //  console.error(`資料更新失敗，id: ${item}`, error);
        //}
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 2,      // 行走中
        station:  3,    // 行走至成品區
      };
      await updateAGV(payload);

      background.value='#10e810'      //變換黃綠燈顏色
      activeColor.value='SeaGreen';   // 物料出站
    })

    socket.value.on('station3_agv_end', async () => {
      console.log('收到 station3_agv_end 訊息, AGV已到達成品區!');

      // 記錄agv在站與站之間運行結束時間
      agv2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2EndTime.value);

      let payload = {};
      let targetItem = {};

      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (kk) => kk.index === item
        );
        console.log("targetItem:", targetItem)

        let current_assemble_id=targetItem.assemble_id
        let current_material_id=targetItem.id
        console.log("current_material_id, current_assemble_id:", current_material_id, current_assemble_id)

        payload = {
          //id: targetItem.id,
          id: current_material_id,
          show1_ok: 3,        //成品站
          show2_ok: 10,      //等待入庫
          show3_ok: 3,       //等待組裝中
          whichStation: 3,  //目標途程:組裝站
        };
        await updateMaterialRecord(payload);

        // 2025-06-24, add
        payload = {
          material_id: current_material_id,
          record_name: 'isAssembleStationShow',
          record_data: false,
        };
        await updateAssembleMustReceiveQtyByMaterialID(payload);

        // 2025-06-24, add
        payload = {
          //id: item.id,
          id: current_material_id,
          record_name: 'must_allOk_qty',
          record_data: targetItem.receive_qty
        };
        await updateMaterial(payload);

        /*
        payload = {
          assemble_id: targetItem.id,
          record_name: 'show1_ok',
          record_data: 3,
        };
        await updateAssemble(payload);
        payload = {
          assemble_id: targetItem.id,
          record_name: 'show2_ok',
          record_data: 10,
        };
        await updateAssemble(payload);
        payload = {
          assemble_id: targetItem.id,
          record_name: 'show3_ok',
          record_data: 3,
        };
        await updateAssemble(payload);
        payload = {
          assemble_id: targetItem.id,
          record_name: 'whichStation',
          record_data: 3,
        };
        await updateAssemble(payload);
        */
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
        targetItem = materials_and_assembles_by_user.value.find(
          (kk) => kk.index === item
        );
        console.log("targetItem:", targetItem)

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv2PeriodTime,
          user_id: 'AGV2-2',                        //在組裝區('AGV2')至成品區, 呼叫AGV的運行時間('-2'), 即簡稱AGV1-2
          order_num: targetItem.order_num,
          id: targetItem.id,                        //2025-02-24 add
          process_type: 3,                          //在成品區
        };
        await createProcess(payload);
        console.log('步驟2-1...');

        //紀錄該筆的agv組裝完成數量
        payload = {
          id: targetItem.id,
          record_name: 'assemble_qty',
          record_data: targetItem.delivery_qty
        };
        await updateMaterial(payload);
        console.log('步驟2-2...');

        //紀錄該筆訂單已組裝完成總數量
        let temp_total_assemble_qty = targetItem.total_assemble_qty + targetItem.delivery_qty
        payload = {
          id: targetItem.id,
          record_name: 'total_assemble_qty',
          record_data: temp_total_assemble_qty
        };
        await updateMaterial(payload);
        console.log('步驟2-2-1...');

        //紀錄該筆的agv組裝完成狀態
        //if (Number(myMaterial.delivery_qty) !=0 && Number(myMaterial.total_delivery_qty) !=0) {
        payload = {
          id: targetItem.id,
          record_name: 'isAssembleStationShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-3...');
        //下面這一段, 待討論....
        /*
        if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
          console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

          let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;

          payload_new = {
            copy_id: myMaterial.id,
            total_delivery_qty: tempDelivery,
            show2_ok: 2,
            shortage_note: '',
          }
          await copyMaterial(payload_new);
          console.log('步驟2-4...');
        }
        */
        //
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 1,      // 準備中
        station:  3,    // 已在成品區
      };
      await updateAGV(payload);
      console.log('agv_end 處理步驟3...');

      activeColor.value='DarkOrange';   //物料送達

      // 插入延遲 3 秒
      await delay(3000);

      isFlashLed.value = false;       //黃綠燈熄滅

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    });

    //socket.value.on('station3_agv_ready', async () => {
    //  console.log('AGV 已在成品區裝卸站, 收到 station3_agv_ready 訊息...');
    //});

    socket.value.on('station2_agv_ready', async () => {
      console.log('AGV 已在組裝區裝卸站, 收到 station2_agv_ready 訊息...');

      order_num_on_agv_blink.value='';

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
      let targetItem = {};
      // 記錄備料區途程資料, 等待agv時間
      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (i) => i.index === item
        );
        console.log("targetItem:", targetItem)

        //紀錄AGV等待時間
        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv1PeriodTime,
          user_id: 'AGV2-1',                        //在組裝區('AGV2'), 呼叫AGV的等待時間('-1'), 即簡稱AGV1-1
          order_num: targetItem.order_num,
          id: targetItem.id,                        //2025-02-24 add
          process_type: 29,                          //在組裝區
        };
        await createProcess(payload);
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 0,
        station:  2,  //在組裝區
      };
      await updateAGV(payload);

      //startFlashing();
      background.value='#ffff00'
      isFlashLed.value = true;
      activeColor.value='blue';   // 機器人進站
    });

    socket.value.on('kuka_server_not_ready', (data) => {
      let temp_msg= data?.message || 'kuka端伺服器未準備好';
      console.warn(temp_msg);
      showSnackbar(temp_msg, 'red accent-2');
    });

    //socket.value.on('agv_ack', async () => {
    //  console.log('收到 agv_ack 回應');
    //});

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
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  //window.removeEventListener('popstate', handlePopState)

  //clearInterval(intervalId);
});

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  //initialize();
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

    await listSocketServerIP();
    console.log("initialize, socket_server_ip:", socket_server_ip.value)

    // 使用 async/await 等待 API 請求完成，確保順序正確
    let payload = {
      user_id: currentUser.value.empID,
      //history: history.value,
    };
    await getMaterialsAndAssemblesByUser(payload);

    // 為materials_and_assembles_by_user每個物件增加 pickEnd 屬性，初始為空陣列 []
    materials_and_assembles_by_user.value.forEach(item => {
      item.pickEnd = [];
    });

    await listUsers2();

  } catch (error) {
    console.error("Error during initialize():", error);
  }
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
  //history.pushState(history.state, '', document.URL)
  window.history.pushState(history.state, '', document.URL)

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const isButtonDisabled = (item) => {
  return (item.whichStation != 2 || item.input_end_disable) || !item.process_step_enable;
};

const checkReceiveQty = (item) => {
  console.log("checkReceiveQty(),", item);

  //const total = Number(item.receive_qty)+Number(item.abnormal_qty)
  const total = Number(item.receive_qty) || 0;    //完成數量
  const temp = Number(item.must_receive_end_qty)  //應完成數量
  if (total > temp) {
    //console.log("total, temp, step1...");
    receive_qty_alarm.value = '完成數量錯誤!';
    item.tooltipVisible = true;     // 顯示 Tooltip
    setTimeout(() => {
      item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.receive_qty = '';        // 清空輸入欄位
    }, 2000);
    console.error('完成數量錯誤!');
  } else {
    item.tooltipVisible = false;
  }
};

const checkAbnormalQty = (item) => {
  console.log("checkAbnormalQty(),", item);

  //const total = Number(item.receive_qty) + Number(item.abnormal_qty);
  const total = Number(item.abnormal_qty) || 0;   //異常數量
  const temp = Number(item.must_receive_end_qty) - Number(item.receive_qty);  //應完成數量 - 完成數量
  if (total > temp) {
    //console.log("total, temp, step1...");
    abnormal_qty_alarm.value = '異常數量錯誤!';
    item.abnormal_tooltipVisible = true;     // 顯示 Tooltip
    setTimeout(() => {
      item.abnormal_tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.abnormal_qty = '';        // 清空輸入欄位
    }, 2000);
    console.error('異常數量錯誤!');
  } else {
    item.abnormal_tooltipVisible = false;
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

const setActive = (value) => {
  toggle_exclusive.value = value; // 設置當前活動按鈕
  if (toggle_exclusive.value == 1)
    showMenu.value = true;
  else
    showMenu.value = false;
}

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

const isSelected = (item) => {
  // 安全檢查，確保 item 和 item.columns 存在
  if (!item || !item.columns || typeof item.columns.index === 'undefined') {
    return false; // 預設未被選中
  }

  return selectedItems.value.includes(item.columns.index); // 根據 columns.index 檢查是否被選中
};

const toggleSelect = (item) => {
  // 檢查是否已呼叫 AGV
  if (isCallAGV.value) {
    showSnackbar('已呼叫 AGV，工單不能改變！', 'red accent-2');
    return;     // 不改變選擇狀態
  }

  let nn = selectedItems.value.indexOf(item.columns.index);
  if (nn === -1) {
    selectedItems.value.push(item.columns.index);  // 若未選中，則添加 columns.index
  } else {
    selectedItems.value.splice(nn, 1);       // 若已選中，則移除 columns.index
  }
};

const callAGV = async () => {
  console.log("callAGV()...")

  let payload = {};

  if (!isCallAGV.value) {
    if (selectedItems.value.length == 0) {
      showSnackbar("請選擇送料的工單!", 'red accent-2');
      return;
    }

    payload = {agv_id: 1};
    await getAGV(payload);
    console.log("hello, 組裝區叫車, AGV 狀態:", currentAGV.value);
    if (currentAGV.value.station != 2 || currentAGV.value.status != 0) {
    //  showSnackbar("AGV目前忙碌中...", 'red accent-2');
    //  return;
    }

    isCallAGV.value = true
  } else {
    showSnackbar("請不要重複按鍵!", 'red accent-2');
    return;
  }

  //isBlinking.value = true;
  socket.value.emit('station2_call');
  console.log("送出 station2_call訊息...")
  order_num_on_agv_blink.value='叫車進站中...'

  activeColor.value='red';    // 等待運輸

  agv1StartTime.value = new Date();  // 使用 Date 來記錄等待agv開始時間
  console.log("AGV Start time:", agv1StartTime.value);

  selectedItems.value.forEach(async (item) => {
    console.log('selectedItems, item:', item);

    payload = {
      id: item,
      record_name: 'show3_ok',
      record_data: 1      // 設為 1，等待agv
    };
    await updateMaterial(payload);

    payload = {
      assemble_id: item,
      record_name: 'show3_ok',
      record_data: 1,
    };
    await updateAssemble(payload);

  });
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  // 檢查是否輸入了空白或 0
  if (!item.receive_qty || Number(item.receive_qty) === 0) {
    item.receive_qty = item.must_receive_end_qty || 0;
  //} else {
  //  item.receive_qty = Number(item.receive_qty) || 0;
  }

  item.isError = true;              // 輸入數值正確後，重置 數字 為 紅色

  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }
};

const updateItem = async (item) => {
  console.log("PickReportForAssembleEnd, updateItem(),", item);

  // 檢查完成數量欄位是否為空白或輸入了0
  if (!item.receive_qty || Number(item.receive_qty) === 0) {
    receive_qty_alarm.value = '完成數量不可為空白或0!'
    item.tooltipVisible = true;     // 顯示 Tooltip 提示
    setTimeout(() => {
      item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.receive_qty = '';        // 清空完成數量欄位
    }, 2000);
    console.error('領取數量不可為空白或0!');
    return;
  }

  // targetIndex為目前table data record 的 index
  const targetIndex = materials_and_assembles_by_user.value.findIndex(
    (kk) => kk.assemble_id === item.assemble_id
  );
  console.log("targetIndex assemble_id:", targetIndex)

  // //組裝區途程完成(按結束定鍵) && AGV還沒送出
  //enableDialogBtn.value = item.isTakeOk && !item.isShow;

  let current_assemble_id=materials_and_assembles_by_user.value[targetIndex].assemble_id
  let current_material_id=materials_and_assembles_by_user.value[targetIndex].id

  // 1.更新記錄, 完成數量
  let current_completed_qty= Number(item.receive_qty);    //完成數量
  console.log("current:", current_completed_qty, current_assemble_id)
  let payload = {
    //assemble_id: item.assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'completed_qty',
    record_data: current_completed_qty,
  };
  await updateAssemble(payload);

  item.pickEnd.push(item.receive_qty);

  let current_total_completed_qty=Number(item.total_receive_qty_num);   //已完成總數量
  let total = current_total_completed_qty + current_completed_qty;
  item.total_receive_qty_num = total;
  item.total_receive_qty ='(' + total.toString().trim() + ')';

  // 記錄當前完成總數量
  payload = {
    //assemble_id: item.assemble_id,
    assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    record_name: 'total_completed_qty',
    record_data: total,
  };
  await updateAssemble(payload);

  // 紀錄當前已結束(完成)總數量顯示順序
  let temp_qty=1
  if (item.process_step_code == 2 )
    temp_qty=2
  if (item.process_step_code == 1 )
    temp_qty=3
  payload = {
    //assemble_id: item.assemble_id,
    assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    record_name: 'total_ask_qty_end',
    record_data: temp_qty,
  };
  await updateAssemble(payload);
  //console.log("temp_qty:", temp_qty)

  // 2.取得組裝區目前途程的show2_ok/show3_ok訊息類型(結束)
  checkInputStr(item.assemble_work);
  //console.log("outputStatus:", outputStatus.value)
  //console.log("current_completed_qty, total:", current_completed_qty, total)

  //console.log("step1...")
  //console.log("current_completed_qty == total ?", current_completed_qty,total)
  //if (current_completed_qty == total) {   // 2025-06-18 mark, 改順序
  //console.log("step2...")

  // 3.更新組裝區目前途程的show2_ok狀態顯示訊息類型(結束)
  payload = {
    //order_num: item.order_num,
    //id: item.id,
    //id: materials_and_assembles_by_user.value[targetIndex].id,
    id: current_material_id,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step2
  };
  await updateMaterial(payload);

  payload = {
    //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step2,
  };
  await updateAssemble(payload);

  // 4.更新組裝區目前途程的show3_ok狀態顯示訊息類型(結束)
  payload = {
    //order_num: item.order_num,
    //id: item.id,
    //id: materials_and_assembles_by_user.value[targetIndex].id,
    id: current_material_id,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step2
  };
  await updateMaterial(payload);

  payload = {
    //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step2,
  };
  await updateAssemble(payload);

  // 5. 更新組裝區目前途程紀錄, 不能再輸入
  payload = {
    //assemble_id: item.assemble_id,
    //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'input_end_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  // 顯示目前途程欄位狀態, disable完成數量欄位
  //item.input_end_disable = true;

    //2025-02-08 mark the following function
    //payload = {
    //  id: item.id,
    //  record_name: 'isShow',
    //  record_data: true
    //};
    //await updateMaterial(payload);
  //}   // 2025-06-18 mark, 改順序

  //const total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
  //let temp = Number(item.req_qty)
  //console.log("step3...")
  //console.log("total == temp ?", total, temp)
  //if (total == temp) {    //, 2025-06-18 add, 改順序
  //  console.log("step4...")
  //  // 記錄當前紀錄, 不能再輸入
  //  payload = {
  //    assemble_id: item.assemble_id,
  //    record_name: 'input_end_disable',
  //    record_data: true,
  //  };
  //  await updateAssemble(payload);

    await listWaitForAssemble();

    //if (targetItem) {
    //  targetItem.input_end_disable = true;
    //}
    if (targetIndex !== -1) {
      // 用 Vue 的方式確保觸發響應式更新
      materials_and_assembles_by_user.value[targetIndex] = {
        ...materials_and_assembles_by_user.value[targetIndex],
        input_end_disable: true,
      };
    }
    //item.input_end_disable = true;
    //待查
    payload = {
      //assemble_id: item.assemble_id,
      //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
      assemble_id: current_assemble_id,

      record_name: 'isAssembleStationShow',
      record_data: true,
    };
    await updateAssemble(payload);
    //
    //if (targetItem) {
    //  targetItem.isShow = true;
    //}
    if (targetIndex !== -1) {
      // 用 Vue 的方式確保觸發響應式更新
      materials_and_assembles_by_user.value[targetIndex] = {
        ...materials_and_assembles_by_user.value[targetIndex],
        isShow: true,
      };
    }
    //item.isShow = true;

    // 記錄當前完工生產結束時間
    let formattedStartTime = item.currentStartTime  //領料生產報工開始時間
    let endTime = new Date();                                                         // 記錄當前結束時間
    let formattedEndTime = formatDateTime(endTime); //完工生產報工結束時間
    periodTime.value = calculatePeriodTimeStr(formattedStartTime, formattedEndTime);  // 計算時間間隔
    payload = {
      //assemble_id: item.assemble_id,
      //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
      assemble_id: current_assemble_id,

      record_name: 'currentEndTime',
      record_data: formattedEndTime,
    };
    await updateAssemble(payload);

    let temp_no = 0;
    if (item.assemble_work.includes('109')) {             //組裝 開始/結束
      //temp_no = 23
      temp_no = 21
    } else if (item.assemble_work.includes('106')) {      //雷射 開始/結束
      //temp_no = 22
      temp_no = 23
    } else if (item.assemble_work.includes('110')) {      //檢驗 開始/結束
      //temp_no = 21
      temp_no = 22
    }

    let processPayload = {
      begin_time: formattedStartTime,
      end_time: formattedEndTime,
      periodTime: periodTime,
      user_id: currentUser.value.empID,
      order_num: item.order_num,
      process_type: temp_no,
      //id: item.id,
      id: materials_and_assembles_by_user.value[targetIndex].id,
    };
    await createProcess(processPayload);

    // 記錄當前紀錄, 目前途程結束
    payload = {
      //assemble_id: item.assemble_id,
      assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
      record_name: 'process_step_code',
      record_data: 0,
    };
    await updateAssemble(payload);

    // 若組裝區內所有途程結束, 並記錄組裝區內所有途程結束
    payload = {
      //id: item.id,
      //asm_id: item.assemble_id,
      id: materials_and_assembles_by_user.value[targetIndex].id,
      assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
    };
    //await updateAssembleProcessStep(payload);
    let response = await updateAssembleProcessStep(payload);
    if (response) {
      console.log("take ok...")

      //if (targetItem) {
      //  targetItem.isTakeOk = true;
      //}
      if (targetIndex !== -1) {
        // 用 Vue 的方式確保觸發響應式更新
        materials_and_assembles_by_user.value[targetIndex] = {
          ...materials_and_assembles_by_user.value[targetIndex],
          isTakeOk: true,
        };
      }
      //item.isTakeOk = true
    }

  //}     , 2025-06-18 mark, 改順序
  console.log("step5...");

  // 紀錄組裝去下一製程的應領取數量, 2025-06-17 add, 改順序
  payload = {
    assemble_id: item.id,
    must_receive_qty: 'must_receive_end_qty',
    completed_qty: current_completed_qty,
  };
  await updateAssembleMustReceiveQtyByAssembleID(payload);

  //payload = {
  //  user_id: currentUser.value.empID,
  //};
  //await getMaterialsAndAssemblesByUser(payload);

  //待待
  window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};

//const listWaitForAssembleFun = async () => {
//  await listWaitForAssemble();
//}

const updateAbnormal = async (item) => {
  console.log("updateAbnormal(),", item);
  /*
  // 檢查是否輸入了空白或 0
  if (!item.receive_qty || Number(item.receive_qty) === 0) {
    receive_qty_alarm.value = '領取數量不可為空白或0!'
    item.tooltipVisible = true;     // 顯示 Tooltip 提示
    setTimeout(() => {
      item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.receive_qty = '';        // 清空輸入欄位
    }, 2000);
    console.error('領取數量不可為空白或0!');
    return;
  }
  */
  // 檢查異常欄位是否輸入了空白或 0

  if (item.input_abnormal_disable) {   //input_abnormal_disable=false:最後製成

    let temp_isAssembleFirstAlarm = !item.isAssembleFirstAlarm;

    const targetIndex_0 = materials_and_assembles_by_user.value.findIndex(
      (kk) => kk.assemble_id === item.assemble_id
    );

    const current_material_id_0 = materials_and_assembles_by_user.value[targetIndex_0].id;

    //顯示按鍵之後的值(顏色)
    if (targetIndex_0 !== -1) {
      // 用 Vue 的方式確保觸發響應式更新
      materials_and_assembles_by_user.value[targetIndex_0] = {
        ...materials_and_assembles_by_user.value[targetIndex_0],
        isAssembleFirstAlarm: temp_isAssembleFirstAlarm,
      };
    }

    payload = {
      id: current_material_id_0,
      record_name: 'isAssembleFirstAlarm',
      record_data: temp_isAssembleFirstAlarm
    };
    await updateMaterial(payload);

    return;
  }

  if (!item.abnormal_qty || Number(item.abnormal_qty) === 0) {
    abnormal_qty_alarm.value = '異常數量不可為空白或0!'
    item.abnormal_tooltipVisible = true;     // 顯示 Tooltip 提示
    setTimeout(() => {
      item.abnormal_tooltipVisible = false;  // 2秒後隱藏 Tooltip
      item.abnormal_qty = '';        // 清空輸入欄位
    }, 2000);
    console.error('領取數量不可為空白或0!');
    return;
  }

  const targetIndex = materials_and_assembles_by_user.value.findIndex(
    (kk) => kk.assemble_id === item.assemble_id
  );
  console.log("targetIndex:", targetIndex)

  let current_assemble_id=materials_and_assembles_by_user.value[targetIndex].assemble_id
  let current_material_id=materials_and_assembles_by_user.value[targetIndex].id

  //按鍵之前
  let temp_alarm_enable = item.alarm_enable;

  //按鍵之後
  temp_alarm_enable = !temp_alarm_enable

  // 記錄組裝區當前紀錄, 按鍵之後的值
  let payload = {
    //assemble_id: item.assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'alarm_enable',
    record_data: temp_alarm_enable,
  };
  await updateAssemble(payload);

  //顯示按鍵之後的值(顏色)
  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      alarm_enable: temp_alarm_enable,
    };
  }

  // 記錄訂單當前紀錄, 異常狀況(false:異常, true:正常)
  //let temp_isAssembleAlarm = item.isAssembleAlarm;
  //console.log("a.temp_isAssembleAlarm:", temp_isAssembleAlarm)
  //temp_isAssembleAlarm = temp_isAssembleAlarm | temp_alarm_enable;
  //console.log("b.temp_isAssembleAlarm, temp_alarm_enable:", temp_isAssembleAlarm, temp_alarm_enable)
  payload = {
    //id: item.id,
    id: current_material_id,
    record_name: 'isAssembleAlarm',
    record_data: temp_alarm_enable
  };
  await updateMaterial(payload);

  //處理異常....

  // 1.更新記錄, 異常數量
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'abnormal_qty',
    record_data: item.abnormal_qty,
  };
  await updateAssemble(payload);
  /*
  // 1-1. 更新記錄, 應完成數量
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'must_receive_end_qty',
    record_data: item.must_receive_end_qty - item.abnormal_qty,
  };
  await updateAssemble(payload);
  */

  // 2. 更新組裝區目前途程異常欄位, 不能再輸入
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_abnormal_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  await listWaitForAssemble();

  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      input_abnormal_disable: true,
    };
  }

  // 3. 新增異常組裝製程的應領取數量
  payload = {
    copy_id: current_assemble_id,
    must_receive_qty: item.abnormal_qty,
  }
  await copyNewAssemble(payload);

  payload = {
    user_id: currentUser.value.empID,
  };
  await getMaterialsAndAssemblesByUser(payload);
};

const checkInputStr = (inputStr) => {
  console.log("checkInputStr(),", inputStr)

  if (inputStr.includes('109')) {             //組裝 開始/結束
    outputStatus.value = { step1: 4, step2: 5, };
  } else if (inputStr.includes('106')) {      //雷射 開始/結束
    outputStatus.value = { step1: 8, step2: 9 };
  } else if (inputStr.includes('110')) {      //檢驗 開始/結束
    outputStatus.value = { step1: 6, step2: 7 };
  } else {
    outputStatus.value = { step1: null, step2: null };  // 無匹配時清空結果
  }
};

// 計算兩個時間字串的差值，返回格式化的時間差
const calculatePeriodTimeStr = (startTime, endTime) => {
  const startDate = new Date(startTime);
  const endDate = new Date(endTime);

  // 確保 startTime 和 endTime 都有效
  //if (isNaN(startDate) || isNaN(endDate)) {
  //  return '無效的時間格式';
  //}

  // 計算毫秒差異
  const diffInMs = endDate - startDate;

  // 計算天、時、分、秒
  const diffInSeconds = Math.floor(diffInMs / 1000);
  const days = Math.floor(diffInSeconds / (24 * 60 * 60));
  const hours = Math.floor((diffInSeconds % (24 * 60 * 60)) / (60 * 60));
  const minutes = Math.floor((diffInSeconds % (60 * 60)) / 60);
  const seconds = diffInSeconds % 60;

  // 將時間差格式化為字串
  return `${days} 天, ${hours} 小時, ${minutes} 分鐘, ${seconds} 秒`;
};

// 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
const calculatePeriodTime = (start, end) => {
  const diffMs = end - start;                         // 差異時間（毫秒）
  const diffSeconds = Math.floor(diffMs / 1000);      // 轉換為秒

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

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const checkTextEditField = (focused, item) => {
  if (!focused) { // 當失去焦點時
    console.log("checkTextEditField()...");

    //if (item.receive_qty.trim().length == 0)
    //  item.receive_qty =0;
    // 檢查 item.pickBegin 是否為空陣列
    /*
    if (item.pickEnd.length == 0) {
      item.receive_qty = 0; // 若為空陣列，設置 item.receive_qty 為 0
    } else {
      // 若不是空陣列，將最後一筆值 assign 給 item.receive_qty
      item.receive_qty = item.pickEnd[item.pickEnd.length - 1];
    }
    */
  }
};

const toggleSort = (key) => {
  let nn = sortBy.value.indexOf(key)

  if (nn !== -1) {
    // 若目前已經是排序該欄位，則切換排序方向
    sortDesc.value[nn] = !sortDesc.value[nn]
  } else {
    // 否則新增排序欄位，並預設為升序
    sortBy.value = [key]
    sortDesc.value = [false]
  }
}

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
  background-color: #85aef2;    // 自訂背景顏色
}

:deep(.v-data-table .v-table__wrapper > table > tbody tr:nth-of-type(odd)) {
    background-color: rgba(0, 0, 0, .05);
  }

:deep(.v-data-table-footer) {
  margin-bottom: -10px;
}

:deep(input[type="text"]) {
  min-height: 20px;
  opacity: 1;
  padding: 0px;
  text-align: center;
  color: red;
  min-width:60px;
}

.custom-table {
  //border-collapse: collapse;  // 合併邊框
  //border: 1px solid #000;     // 表格的外框
  border-radius: 0 0 20px 20px;
}

.action-cell {
  padding-left: 2px;
  padding-right: 2px;
  width: 164px;
}

:deep(.custom-table th:nth-child(9)),
:deep(.custom-table td:nth-child(9)) {
  padding-left: 4px !important;
  padding-right: 4px !important;
  //margin-left:  0px !important;
  margin-right:  5px !important;
}

:deep(.custom-table th:nth-child(7)),
:deep(.custom-table td:nth-child(7)) {
  padding-left: 4px !important;
  padding-right: 4px !important;
}

:deep(.custom-table th:nth-child(8)),
:deep(.custom-table td:nth-child(8)) {
  padding-left: 4px !important;
  padding-right: 4px !important;
}

/*
.custom-table th,
.custom-table td {
  border: 1px solid #000;   // 單元格的邊框
  padding: 8px;             // 單元格的內邊距
  text-align: left;         // 文本對齊
}
*/

// 選擇框
:deep(span.custom-header) {
  display: block;
  width: 80px;      // 設定最小寬度
}

// 客製化 手推車/AGV切換按鍵
.button-container {
  position: relative;
  width: fit-content;     // 可調整寬度以適應按鈕

  //right: 100px;
  top: 0px;
}

.hidden-column {
  display: none;
}

// 限制樣式範圍到特定的 v-data-table
:deep(.v-table__wrapper > table > tbody td:first-child) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(2)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:first-child) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(2)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.blue-text {
  color: #003171;   // 設置字體顏色為深藍色
  //color: red;
  font-weight: 700;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

</style>

