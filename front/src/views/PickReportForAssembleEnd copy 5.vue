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

    <!-- 燈號控制面板 -->
    <DraggablePanel v-show="toggle_exclusive === 2" :initX="panelX" :initY="panelY" :isDraggable="true" ref="draggablePanel">
      <LedLights :activeColor="activeColor" />
    </DraggablePanel>

    <ConfirmDialog ref="confirmRef" />

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
          :disabled="(!internalItem.raw.isAssembleStationShow || internalItem.raw.receive_qty == 0) && warehouse_in_all_pass=='待完工'"
          color="primary"
          @update:model-value="toggleSelect(internalItem)"
          :class="{ 'blue-text': internalItem.raw.isAssembleStationShow}"
        />
      </template>

      <!-- 客製化 top 區域 -->
      <template v-slot:top>
        <v-card>
          <v-card-title
            class="d-flex align-center pe-2"
            style="font-weight:700;"
          >
            <div style="display: flex; flex-direction: column;">
            <div>
            組裝區完成生產報工
            </div>
                        <!--客製化 模式switch按鍵-->

            <v-switch
              v-model="warehouse_in_all_pass"
              color="indigo"
              :label="`模式: ${warehouse_in_all_pass}`"
              false-value="待完工"
              true-value="待入庫"
              hide-details

            />
              </div>

            <v-divider class="mx-2" inset vertical></v-divider>


            <!--客製化 員工選單-->
            <div style="position:relative; width:160px; right: 5px;">
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
                  <v-icon right color="#003171">mdi-forklift</v-icon>
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
              style="position:relative; left:5px; top:0px; font-weight:700; padding-left:8px;
                    padding-right:8px;"
              @click="select_transportation_method"
              ref="sendButton"
            >
              <v-icon left color="blue">mdi-account-arrow-right-outline</v-icon>
              <span>{{ transport_message }}</span>
            </v-btn>

            <div style="display: flex; flex-direction: column; align-items: center;">
              <span
                style="position:relative; top:30px; right:180px;"
                :style="{
                  'fontSize': '14px',
                  'display': 'inline-block',
                  'min-width': '120px',
                  'visibility': isCallForklift ? 'visible' : 'hidden',
                }"
              >
                堆高機送料中
              </span>

              <!--客製化搜尋-->
              <v-text-field
                id="bar_code"

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
                id="bar_code"
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
            <!--
            <v-switch
              v-model="warehouse_in_all_pass"
              color="indigo"
              :label="`模式: ${warehouse_in_all_pass}`"
              false-value="待完工"
              true-value="待入庫"
              hide-details
            ></v-switch>
            -->
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
            <div style="right:10px; position:relative;">{{ column.title }}</div>
            <div style="min-width: 24px;">
              <!-- 僅在滑鼠移入或者正在排序的情況下顯示圖標 -->
              <v-icon v-if="sortBy.includes('order_num') && isHovering" style="margin-left: 2px;">
                {{ sortDesc[sortBy.indexOf('order_num')] ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
              </v-icon>
            </div>
          </div>
          <div style="right:10px; position:relative; color:#0000FF; font-size:12px; margin-top:2px; font-weight: 600; text-align: center; padding-right: 22px;">
            (工序)
          </div>
        </v-hover>
      </template>

      <!-- 客製化 '物料編號' (material_num) 欄位的表頭 -->
      <template v-slot:header.material_num="{ column }">
        <div style="left:20px; position:relative;">{{ column.title }}</div>
      </template>

      <!-- 客製化 '作業數量' (req_qty) 欄位的表頭 -->
      <template v-slot:header.req_qty="{ column }">
        <div style="text-align: center;">
          <div>需求</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '領取數量' (ask_qty) 欄位的表頭 -->
      <template v-slot:header.ask_qty="{ column }">
        <div style="text-align: center;">
          <div>領取</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '應完成數量' (must_receive_end_qty) 欄位的表頭 -->
      <template v-slot:header.must_receive_end_qty="{ column }">
        <div style="text-align: center;">
          <div>應完成</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '已完成總數' (total_completed_qty_num) 欄位的表頭 -->
      <template v-slot:header.total_completed_qty_num="{ column }">
        <div style="text-align: center;">
          <div>已完成</div>
          <div>總數量</div>
        </div>
      </template>

      <!-- 客製化 '完成數量' (receive_qty) 欄位的表頭 -->
      <template v-slot:header.receive_qty="{ column }">
        <div style="text-align: center;">
          <div>完成</div>
          <div>數量</div>
        </div>
      </template>

      <!-- 客製化 '異常數量' (abnormal_qty) 欄位的表頭 -->
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
          <!--檢料完成(缺料)-->
          <!--<div style="color: red; margin-right: 2px;" v-if="item.isAssembleStation3TakeOk && item.isAssembleStationShow && item.isLackMaterial != 99">-->
          <div style="color: red; margin-right: 2px;" v-if="item.isAssembleStationShow && item.isLackMaterial != 99">
            <div>
              {{ item.order_num }}&nbsp;&nbsp;
              <span style="font-weight: 700; font-size: 16px;">缺料</span>
            </div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div>

          <!--檢料完成-->
          <!--<div style="color: blue; margin-right: 20px;" v-else-if="item.isAssembleStation3TakeOk && item.isAssembleStationShow && item.isLackMaterial == 99">-->
          <div style="color: blue; margin-right: 20px;" v-else-if="item.isAssembleStationShow && item.isLackMaterial == 99">
            <div>{{ item.order_num }}</div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div>

          <!--檢料還未完成-->
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

      <!-- 自訂 '應完成數量'欄位 -->
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

            @update:modelValue="(value) => onAbnormalQtyUpdate(item, value)"
            @update:focused="(focused) => checkAbnormalField(focused, item)"

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
      <!--
      <template v-slot:item.comment="{ item }">
        <div>
          <div style="text-align:left; color: #669999; font-size:12px; font-family: '微軟正黑體', sans-serif;">{{ item.comment }}</div>
        </div>
      </template>
      -->

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
          <!--計時器-->
          <span v-if="!item.isShowLastTime"
            style="color:#4000ff; width:88px; font-variant-numeric:tabular-nums;"
          >
            <TimerDisplay
              :fontSize="16"
              :autoStart="false"
              :show="true"

              :ref="el => setTimerEl(item, el)"

              :initialMs="getInitialMs(item)"

              :isPaused="isPausedOf(item)"

              :displayMs="closedDisplayMs(item)"

              @update:isPaused="val => setPausedOf(item, val)"

              @update:time="ms => onTickOf(makeKey(item), item, ms)"

              class="me-2"
              style="min-width:88px; display:inline-block;"
            />
          </span>
          <span v-else
            class="me-2"
            style="
              color:#4000ff;
              width:88px;
              min-width:88px;
              font-size: 16px;
              font-variant-numeric:tabular-nums;
              display:inline-block;
              text-align: right;"
          >
            {{ item.last_time }}
          </span>

          <!-- 自訂 暫停/開始 按鍵欄位-->
          <v-btn
            size="small"
            density="comfortable"
            variant="tonal"
            :prepend-icon = "getIcon(isRowPaused(item))"

            :disabled="item.isAssembleStationShow"
            :style="{ background: isRowPaused(item) ? '#4CAF50' : '#FFEB3B', color: isRowPaused(item) ? '#fff' : '#000' }"

            @click="onPauseToggle(item)"
            style="font-size:13px; font-weight:700; font-family: '微軟正黑體', sans-serif;"
          >
            <v-icon start style="font-weight:700;">mdi-timer-outline</v-icon>
            {{ pauseLabel(item) }}
          </v-btn>

          <!-- 自訂 '結束' 按鍵欄位 -->
            <!--:disabled="Boolean(isButtonDisabled(item) || isRowPaused(item))"-->
          <v-btn
            size="small"
            density="comfortable"
            class="mr-2"
            variant="tonal"
            :disabled="item.input_end_disable"
            @click="onClickEnd(item)"
            color="indigo-darken-4"
            style="
              font-size: 13px;
              font-weight: 700;
              font-family: '微軟正黑體', sans-serif;
              padding: 0 5px !important;
              "
          >
            結 束
            <v-icon color="indigo-darken-4" start>mdi-close-circle-outline</v-icon>
          </v-btn>

          <!-- 自訂 '異常' 按鍵欄位 -->
          <v-btn
            size="small"
            density="comfortable"
            variant="tonal"

            @click="onClickAbnormal(item)"
            style="padding: 0 5px !important;"
            :style="getBtnStyle(item)"
            :disabled="item.input_abnormal_disable"
          >
            異 常
            <v-icon start :style="getBtnStyle(item)">mdi-alert-circle-outline</v-icon>
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
import { ref, reactive, nextTick, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onDeactivated } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';

import TimerDisplay from "./TimerDisplayBegin.vue";
import { useProcessTimer } from "../mixins/useProcessTimerBegin.js";
import ConfirmDialog from "./confirmDialog";

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';

import { useRoute } from 'vue-router';
const search = ref('');

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { materials_and_assembles_by_user }  from '../mixins/crud.js';
import { currentAGV }  from '../mixins/crud.js';

import { desserts2 }  from '../mixins/crud.js';
import { socket_server_ip }  from '../mixins/crud.js';

import { apiOperation}  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');
const listUsers2 = apiOperation('get', '/listUsers2');
const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');

const updateAssembleMustReceiveQtyByMaterialID = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialID');
const copyNewAssemble = apiOperation('post', '/copyNewAssemble');
const copyAssembleForDifference = apiOperation('post', '/copyAssembleForDifference');
const copyNewIdAssemble = apiOperation('post', '/copyNewIdAssemble');
const updateAssembleMustReceiveQtyByAssembleID = apiOperation('post', '/updateAssembleMustReceiveQtyByAssembleID');
const getMaterialsAndAssemblesByUser = apiOperation('post', '/getMaterialsAndAssemblesByUser');
const getCountMaterialsAndAssemblesByUser = apiOperation('post', '/getCountMaterialsAndAssemblesByUser');
const getMaterialsAndAssemblesAndTime = apiOperation('post', '/getMaterialsAndAssemblesAndTime');
//const getEndOkByMaterialIdAndStepCode  = apiOperation('post', '/getEndOkByMaterialIdAndStepCode');
const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const updateAGV = apiOperation('post', '/updateAGV');
const getAGV = apiOperation('post', '/getAGV');
const updateAssembleProcessStep  = apiOperation('post', '/updateAssembleProcessStep');
const updateAssmbleDataByMaterialID = apiOperation('post', '/updateAssmbleDataByMaterialID');
const updateProcessData = apiOperation('post', '/updateProcessData');
const updateAssembleTableData = apiOperation('post', '/updateAssembleTableData');

//=== component name ==
defineComponent({
  name: 'PickReportForAssembleEnd'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
// 結束已領料工單對話框相關
const endTitle = ref('結束已領料工單');
const endMessage = ref('確定？');
const confirmRef = ref(null);

const transport_message = ref('組裝完成自動送出')

const history = ref(false);               // 設定歷史紀錄為不顯示

const isCallAGV = ref(false);             // 確認是否已經按了callAGV按鍵, true:已經按鍵了, 不能重複按鍵
const showMenu = ref(false);                  // 控制員工選單顯示
const placeholderTextForEmployee = ref('請選擇員工');
const inputSelectEmployee = ref(null);
const toggle_exclusive = ref(2);              // 控制選擇的按鈕, 預設AGV

const isCallForklift = ref(false);            // 確認是否已經呼叫了CallForklift(), true:已經按鍵了, 不能重複按鍵

//const isVisible = ref(true);              // 設定初始狀態為顯示
const isFlashLed = ref(false);            // 控制是否閃爍Led
//let intervalIdForLed = null;
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
  { title: '  ', sortable: false, key: 'index', width: 30, class: 'hidden-column' },
  { title: '訂單編號', sortable: true, key: 'order_num', width:150 },
  { title: '物料編號', sortable: false, key: 'material_num', width:180 },
  { title: '需求數量', sortable: false, key: 'req_qty', width:70 },
  //{ title: '備料數量', sortable: false, key: 'delivery_qty', width:100 }, // 2025-06-13 mark, 改順序
  { title: '領取數量', sortable: false, key: 'ask_qty', width:70 },
  { title: '應完成總數量', sortable: false, key: 'must_receive_end_qty', width:70 },       // 2025-06-13 add, 改順序
  { title: '已完成總數量', sortable: false, key: 'total_completed_qty_num', width:70 },
  { title: '完成數量', sortable: false, key: 'receive_qty', width:70 },
  { title: '異常數量', sortable: false, key: 'abnormal_qty', width:70 },             // 2025-06-13 add, 改順序
  //{ title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '交期', sortable: false, key: 'delivery_date', width:100 },
  { title: '', sortable: false, key: 'action', width:300 },
];

const app_user_id = 'user_chumpower';
const clientAppName = 'PickReportForAssembleEnd';

const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user_id, clientAppName);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const receive_qty_alarm = ref('');
const abnormal_qty_alarm = ref('');

//const from_agv_input_order_num = ref('');
//2025-10-20m, const isBlinking = ref(false);          // 控制按鍵閃爍
const order_num_on_agv_blink=ref('');

const selectedEmployee = ref(null);

//const inputStr = ref('');
const outputStatus = ref({
  step1: null,
  step2: null
});

const currentUser = ref({});
//const permDialog = ref(false);

const componentKey = ref(0)                 // key值用於強制重新渲染

const periodTime = ref('');                 // 記錄時間間距
//const currentStartTime = ref(null);       // 記錄開始時間

const agv1StartTime = ref(null);            // 等待agv計時開始
const agv1EndTime = ref(null);
const agv2StartTime = ref(null);            // 運行agv計時開始
const agv2EndTime = ref(null);

const forklift2StartTime = ref(null);       // 堆高機運行計時開始
const forklift2EndTime = ref(null);         // 堆高機運行計時結束

const pagination = reactive({
  itemsPerPage: 5,                          // 預設值, rows/per page
  page: 1,
});

const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const warehouse_in_all_pass=ref('待完工');

const panelX = ref(830);                      // led顯示面板x位置, 值越大, 越往右
const panelY = ref(11);                       // led顯示面板y位置, 值越大, 越往下
const activeColor = ref('green')              // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)                 // 允許拖曳的開關

// 獲取元件引用
const draggablePanel = ref(null);
const sendButton = ref(null);

const screenSizeInInches = ref(null);

const qtyInput = ref({});

//== timerDisplay用 ==
const timerMap = new Map();
const timerRefMap = new Map()
const lastTickMsMap = reactive(new Map())  // key: item.id, value: 畫面最後一次 @update:time 的毫秒數
const frozenMsMap   = reactive(new Map())  // key: item.id, value: 按結束時要凍結顯示的毫秒數

let __disposedAll = false;
const lastKeys = ref(new Set())

const keyOf = (row, uId) => `${row.id}:${row.assemble_id}:${processTypeOf(row)}:${uId}`
const makeKey = (row) => `${row.id}:${row.assemble_id}:${processTypeOf(row)}:${currentUser.value.empID}`

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

//== timerDisplay用 ==
watch(materials_and_assembles_by_user, (rows) => {
  const now = new Set((rows || []).map(makeKey))

  // 找出被刪除（從 lastKeys 有、現在沒有）的 key
  for (const key of lastKeys.value) {
    if (!now.has(key)) {
      // 反查出 row 的必要欄位（或你也可以把整個 row 存在 last snapshot）
      const [id, asm, ptype, uid] = key.split(':')
      releaseRowTimer({ id: Number(id), assemble_id: Number(asm), process_step_code: revMapPtype(ptype) }, uid)
    }
  }
  lastKeys.value = now
}, { immediate: true })

//=== computed ===
const userId = computed(() => currentUser.value.empID ?? '')

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

const todayStr = computed(() => {
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
})

// 控制面板樣式，包括邊框顏色和層級 (z-index)
const panelStyle = computed(() => ({
  cursor: panel_flag.value ? 'move' : 'default',
  border: panel_flag.value ? '2px solid blue' : '2px solid transparent',
  zIndex: panel_flag.value ? 9999 : 1, // 當可拖曳時，將面板提升至最上層
}))

//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleEnd.vue, mounted()...");

  //+++
  const dpi = window.devicePixelRatio || 1;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
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

  console.log("current routeName:", routeName.value);

  //user define
  let userRaw = sessionStorage.getItem('auth_user');
  if (!userRaw) {
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
  console.log("currentUser:", currentUser.value, currentUser.value.perm, currentUser.value.empID);

  initialize();

  // 取得每個 v-text-field 的唯一 ID
  inputIDs.value.forEach((item) => {
    const myIdField = document.getElementById(`receiveQtyID-${item.order_num}`);
    myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  });

  //intervalIdForLed = setInterval(() => {
  //  isVisible.value = !isVisible.value;       // 每秒切換顯示狀態
  //}, 500);

  //2025-10-20m, isBlinking.value = materials_and_assembles_by_user.value.length == 0 || materials_and_assembles_by_user.value.every(item => !item.isAssembleStation1TakeOk && !item.isAssembleStation2TakeOk && !item.isAssembleStation3TakeOk);

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
    socket.value.on('station2_error', async () => {
      console.log("receive station2_error socket...");
      activeColor.value = 'green'  // 預設亮綠燈, 區域閒置
    });

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

      // 取乾淨且去重的 index 陣列
      const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIdx.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(i => i.index === idx);
        if (!rec) {
          console.warn('找不到資料，index =', idx);
          continue;
        }
        console.log('targetItem:', rec);

        // Material：show3_ok = 16 (AGV start)
        try {
          await updateMaterial({
            id: rec.id,
            record_name: 'show3_ok',
            record_data: 16,
          });
        } catch (e) {
          console.error(`updateMaterial 失敗，material.id=${rec.id}`, e);
        }

        // Assemble：優先用 rec.assemble_id，沒有就退回 rec.id
        const assembleId = rec.assemble_id ?? rec.id;
        try {
          await updateAssemble({
            assemble_id: assembleId,
            record_name: 'show3_ok',
            record_data: 16,
          });
        } catch (e) {
          console.error(`updateAssemble 失敗，assemble_id=${assembleId}`, e);
        }
      }

      /*
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
      */
    });

    socket.value.on('station2_agv_begin', async () => {
      console.log('AGV暫停, 收到 station2_agv_begin 訊息');

      // 記錄 agv 在站與站之間運行開始時間
      agv2StartTime.value = new Date();
      console.log('AGV Start time:', agv2StartTime.value);

      // 取乾淨且去重的 index 陣列
      const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIdx.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      let successCount = 0;

      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(i => i.index === idx);
        if (!rec) {
          console.warn('找不到資料，index =', idx);
          continue;
        }
        console.log('targetItem:', rec);

        // Material：show3_ok = 10（AGV 移動至成品區中）
        try {
          await updateMaterial({
            id: rec.id,
            record_name: 'show3_ok',
            record_data: 10, // 10: agv 移動至成品區中
          });
        } catch (e) {
          console.error(`updateMaterial 失敗，material.id=${rec.id}`, e);
        }

        // Assemble：優先用 assemble_id，沒有就退回 material id
        const assembleId = rec.assemble_id ?? rec.id;
        try {
          await updateAssemble({
            assemble_id: assembleId,
            record_name: 'show3_ok',
            record_data: 10,        // 10: agv 移動至成品區中
          });
          successCount++;
        } catch (e) {
          console.error(`updateAssemble 失敗，assemble_id=${assembleId}`, e);
        }
      }

      // 成功至少一筆再更新 AGV 狀態與 UI
      if (successCount > 0) {
        await updateAGV({
          id: 1,
          status: 2, // 行走中
          station: 3, // 行走至成品區
        });

        background.value = '#10e810';   // 變換黃綠燈顏色
        activeColor.value = 'SeaGreen';  // 物料出站
      } else {
        console.warn('沒有任何資料成功更新，略過 AGV 狀態更新與 UI 變更');
      }

      /*
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
      */
    })

    socket.value.on('station3_agv_end', async () => {
      console.log('收到 station3_agv_end 訊息, AGV已到達成品區!');

      // 記錄 agv 在站與站之間運行結束時間
      agv2EndTime.value = new Date();
      //console.log('AGV end time:', agv2EndTime.value);

      // 確保時間 end >= start
      const startDate = new Date(agv2StartTime.value || Date.now());
      const endDate   = new Date(agv2EndTime.value   || Date.now());
      const startMs   = +startDate;
      const endMs     = Math.max(+endDate, startMs);

      const formattedStartTime = formatDateTime(new Date(startMs));
      const formattedEndTime   = formatDateTime(new Date(endMs));
      const agv2PeriodTime     = calculatePeriodTime(new Date(startMs), new Date(endMs));

      console.log('AGV 運行 Start Time:', formattedStartTime);
      console.log('AGV 運行 End   Time:', formattedEndTime);
      console.log('AGV 運行 Period    :', agv2PeriodTime);

      // 取乾淨且去重的 index 陣列
      const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIdx.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      // === 步驟1：更新 Material/Assemble 顯示狀態與欄位 ===
      let step1Success = 0;

      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
        if (!rec) {
          console.warn('找不到資料，index =', idx);
          continue;
        }
        console.log('targetItem:', rec);

        const current_material_id = rec.id;
        const current_assemble_id = rec.assemble_id
        console.log("VVV station3_agv_end step1... VVV")
        try {
          // Material：成品站/等待入庫/等待組裝中/目標途程=成品站
          await updateMaterialRecord({
            id: current_material_id,
            show1_ok: 3,   // 成品站
            show2_ok: 10,  // 等待入庫
            show3_ok: 3,   // 等待組裝中
            whichStation: 3, // 目標途程: 成品站
          });

          // Assemble（by material_id）：同步三個狀態
          await updateAssmbleDataByMaterialID({
            material_id: current_material_id,
            delivery_qty: 0,
            record_name1: 'show1_ok',
            record_data1: 3,
            record_name2: 'show2_ok',
            record_data2: 10,
            record_name3: 'show3_ok',
            record_data3: 3,            // 等待組裝中
          });

          // 將組裝站顯示關閉（用你現有的 API 名稱）
          await updateAssembleMustReceiveQtyByMaterialID({
            material_id: current_material_id,
            record_name: 'isAssembleStationShow',
            record_data: false,
          });

          console.log("VVV station3_agv_end step1-1... VVV")

          // must_allOk_qty = 收料數（數值化）
          await updateMaterial({
            id: current_material_id,
            record_name: 'must_allOk_qty',
            record_data: Number(rec.receive_qty) || 0,
          });

          step1Success++;
        } catch (e) {
          console.error('步驟1 更新失敗：material_id =', current_material_id, e);
        }
      }

      console.log('agv_end 處理步驟1...');

      // === 步驟2：建立 Process + 更新完成數量與顯示 ===
      let step2Success = 0;

      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
        if (!rec) continue;
        console.log('targetItem:', rec);

        console.log("VVV station3_agv_end step2... VVV")

        try {
          // 2-1. 建立「組裝區 → 成品區」運行流程
          await createProcess({
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: agv2PeriodTime,
            user_id: 'AGV2-2',       // 組裝區(AGV2)到成品區的運行時間
            order_num: rec.order_num,
            id: rec.id,
            process_type: 3,         // 在成品區
            normal_work_time: true,  // 正常工時
          });
          console.log('步驟2-1...');

          // 2-2. 本批完成數量（組裝完成）
          await updateMaterial({
            id: rec.id,
            record_name: 'assemble_qty',
            record_data: Number(rec.delivery_qty) || 0,
          });
          console.log('步驟2-2...');

          // 2-3. 訂單累計完成數量
          const temp_total_assemble_qty =
            (Number(rec.total_assemble_qty) || 0) + (Number(rec.delivery_qty) || 0);
          await updateMaterial({
            id: rec.id,
            record_name: 'total_assemble_qty',
            record_data: temp_total_assemble_qty,
          });
          console.log('步驟2-3...');

          // 2-4. 在組裝站的顯示狀態（此處設為 true，依你原本流程）
          await updateMaterial({
            id: rec.id,
            record_name: 'isAssembleStationShow',
            record_data: true,
          });
          console.log('VVV 步驟2-4...');

          step2Success++;
        } catch (e) {
          console.error('步驟2 更新失敗：material_id =', rec.id, e);
        }
      }

      // === 步驟3：更新 AGV 狀態（僅在前面有成功時做） ===
      if (step1Success > 0 || step2Success > 0) {

        console.log("VVV station3_agv_end step3... VVV")

        try {
          await updateAGV({
            id: 1,
            status: 1, // 準備中
            station: 3, // 已在成品區
          });
          console.log('agv_end 處理步驟3...');
        } catch (e) {
          console.error('更新 AGV 狀態失敗：', e);
        }

        activeColor.value = 'DarkOrange'; // 物料送達

        // 插入延遲 3 秒
        await delay(3000);

        isFlashLed.value = false; // 黃綠燈熄滅

        // 清理選取
        selectedItems.value = [];
        if (localStorage.getItem('selectedItems')) {
          localStorage.removeItem('selectedItems');
        }
      } else {
        console.warn('步驟1/步驟2 無成功更新，略過 AGV 狀態更新與 UI 收尾');
      }

      /*
      // 記錄agv在站與站之間運行結束時間
      agv2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV end time:", agv2EndTime.value);

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
          id: current_material_id,
          show1_ok: 3,        // 成品站
          show2_ok: 10,       // 等待入庫
          show3_ok: 3,        // 等待組裝中
          whichStation: 3,    // 目標途程:成品站
        };
        await updateMaterialRecord(payload);

        payload = {
          material_id: current_material_id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 3,
          record_name2: 'show2_ok',
          record_data2: 10,
          record_name3: 'show3_ok',
          record_data3: 3,
        };
        await updateAssmbleDataByMaterialID(payload)

        payload = {
          material_id: current_material_id,
          record_name: 'isAssembleStationShow',
          record_data: false,
        };
        await updateAssembleMustReceiveQtyByMaterialID(payload);

        payload = {
          id: current_material_id,
          record_name: 'must_allOk_qty',
          record_data: Number(targetItem.receive_qty)
        };
        await updateMaterial(payload);

      }); // end forEach
      console.log('agv_end 處理步驟1...');

      let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv2StartTime.value);
      let formattedEndTime = formatDateTime(agv2EndTime.value);
      console.log("AGV 運行 Start Time:", formattedStartTime);
      console.log("AGV 運行 End Time:", formattedEndTime);
      console.log("AGV 運行 Period time:", agv2PeriodTime);

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
          user_id: 'AGV2-2',                        // 在組裝區('AGV2')至成品區, 呼叫AGV的運行時間('-2'), 即簡稱AGV1-2
          order_num: targetItem.order_num,
          id: targetItem.id,                        //2025-02-24 add
          process_type: 3,                          // 在成品區

          normal_work_time: true,                   // 正常工時
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
        console.log('步驟2-3...');

        //紀錄該筆的agv組裝完成狀態
        payload = {
          id: targetItem.id,
          record_name: 'isAssembleStationShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-4...');
        //下面這一段, 待討論....
        //
        //if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
        //  console.log("1張工單多批次運送, 新增未運送數量(相同工單)")
        //
        //  let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;
        //
        //  payload_new = {
        //    copy_id: myMaterial.id,
        //    total_delivery_qty: tempDelivery,
        //    show2_ok: 2,
        //    shortage_note: '',
        //  }
        //  await copyMaterial(payload_new);
        //  console.log('步驟2-4...');
        //}
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
      */
      // 待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    });

    socket.value.on('station3_trans_end', async (data) => {
      console.log("收到 station3_trans_ready訊息...", data);

      socket.value.emit('station3_trans_over');
      console.log('送出 station3_trans_over 訊息...');

      // 記錄 forklift 在站與站之間運行結束時間
      forklift2EndTime.value = new Date();
      console.log('forklift end time:', forklift2EndTime.value);

      // 取乾淨且去重的 index 陣列
      const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIdx.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      // === 步驟1：狀態欄位更新（成品站 / 等待入庫 / 關閉組裝站顯示 / 手動搬運標記 等）===
      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
        if (!rec) {
          console.warn('找不到資料，index =', idx);
          continue;
        }
        console.log('targetItem:', rec);

        const current_material_id = rec.id;

        try {
          // Material：成品站/等待入庫/等待組裝中/目標途程=成品站
          await updateMaterialRecord({
            id: current_material_id,
            show1_ok: 3,   // 成品站
            show2_ok: 10,  // 等待入庫
            show3_ok: 3,   // 等待組裝中
            whichStation: 3,
          });

          // Assemble（by material_id）：同步三個狀態
          await updateAssmbleDataByMaterialID({
            material_id: current_material_id,
            delivery_qty: 0,
            record_name1: 'show1_ok',
            record_data1: 3,
            record_name2: 'show2_ok',
            record_data2: 10,
            record_name3: 'show3_ok',
            record_data3: 3,            // 等待組裝中
          });

          // 關閉組裝站顯示
          await updateAssembleMustReceiveQtyByMaterialID({
            material_id: current_material_id,
            record_name: 'isAssembleStationShow',
            record_data: false,
          });

          // must_allOk_qty 用收料數（轉數值）
          await updateMaterial({
            id: current_material_id,
            record_name: 'must_allOk_qty',
            record_data: Number(rec.receive_qty) || 0,
          });

          // 搬運方式2：false = 手動(堆高機)
          await updateMaterial({
            id: current_material_id,
            record_name: 'move_by_automatic_or_manual_2',
            record_data: false,
          });
        } catch (e) {
          console.error('步驟1 更新失敗：material_id =', current_material_id, e);
        }
      }
      console.log('trans_end 處理步驟1...');

      // === 時間安全計算：確保 end >= start ===
      const startDate = new Date(forklift2StartTime.value || Date.now());
      const endDate   = new Date(forklift2EndTime.value   || Date.now());
      const startMs   = +startDate;
      const endMs     = Math.max(+endDate, startMs);

      const transStartTime   = formatDateTime(new Date(startMs));
      const transEndTime     = formatDateTime(new Date(endMs));
      const transPeriodTime  = calculatePeriodTime(new Date(startMs), new Date(endMs));

      console.log('forklift 運行 Start Time:', transStartTime);
      console.log('forklift 運行 End   Time:', transEndTime);
      console.log('forklift 運行 Period    :', transPeriodTime);

      // === 步驟2：建立 Process（成品區）＋ 完成數量寫回 ===
      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
        if (!rec) continue;
        console.log('targetItem:', rec);

        try {
          // 2-1. 建立「組裝區 → 成品區（堆高機）」流程
          await createProcess({
            begin_time: transStartTime,
            end_time: transEndTime,
            periodTime: transPeriodTime,
            user_id: currentUser.value?.empID ?? '',
            order_num: rec.order_num,
            id: rec.id,
            process_type: 6,         // 在成品區（堆高機）
            normal_work_time: true,
          });
          console.log('步驟2-1...');

          // 2-2. 本批完成數量（組裝完成）
          await updateMaterial({
            id: rec.id,
            record_name: 'assemble_qty',
            record_data: Number(rec.delivery_qty) || 0,
          });
          console.log('步驟2-2...');

          // 2-3. 累計完成數量（避免字串相加）
          const total = (Number(rec.total_assemble_qty) || 0) + (Number(rec.delivery_qty) || 0);
          await updateMaterial({
            id: rec.id,
            record_name: 'total_assemble_qty',
            record_data: total,
          });
          console.log('步驟2-3...');

          // 2-4. 在組裝站顯示狀態（依你原本流程設為 true）
          await updateMaterial({
            id: rec.id,
            record_name: 'isAssembleStationShow',
            record_data: true,
          });
          console.log('步驟2-4...');
        } catch (e) {
          console.error('步驟2 更新失敗：material_id =', rec.id, e);
        }
      }

      // 插入延遲 3 秒
      await delay(3000);

      // 清理選取
      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }

      /*
      socket.value.emit('station3_trans_over');
      console.log("送出 station3_trans_over訊息...");

      // 記錄forklift在站與站之間運行結束時間
      forklift2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("forklift end time:", forklift2EndTime.value);

      let payload = {};
      let targetItem = {};

      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (kk) => kk.index === item
        );
        console.log("targetItem:", targetItem)

        let current_assemble_id=targetItem.assemble_id
        let current_material_id=targetItem.id

        payload = {
          id: current_material_id,
          show1_ok: 3,        // 成品站
          show2_ok: 10,       // 等待入庫
          show3_ok: 3,        // 等待組裝中
          whichStation: 3,    // 目標途程:成品站
        };
        await updateMaterialRecord(payload);

        payload = {
          material_id: current_material_id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 3,
          record_name2: 'show2_ok',
          record_data2: 10,
          record_name3: 'show3_ok',
          record_data3: 3,
        };
        await updateAssmbleDataByMaterialID(payload)

        payload = {
          material_id: current_material_id,
          record_name: 'isAssembleStationShow',
          record_data: false,
        };
        await updateAssembleMustReceiveQtyByMaterialID(payload);

        payload = {
          id: current_material_id,
          record_name: 'must_allOk_qty',
          record_data: Number(targetItem.receive_qty)
        };
        await updateMaterial(payload);

        payload = {
          id: targetItem.id,
          record_name: 'move_by_automatic_or_manual_2',
          record_data: false
        };
        await updateMaterial(payload);
      });
      // end forEach loop
      console.log('trans_end 處理步驟1...');

      let transPeriodTime = calculatePeriodTime(forklift2StartTime.value, forklift2EndTime.value);  // 計算時間間隔
      let transStartTime = formatDateTime(forklift2StartTime.value);
      let transEndTime = formatDateTime(forklift2EndTime.value);
      console.log("forklift 運行 Start Time:", transStartTime);
      console.log("forklift 運行 End Time:", transEndTime);
      console.log("forklift 運行 Period time:", transPeriodTime);

      console.log('agv_end 處理步驟2...');
      selectedItems.value.forEach(async (item) => {
        targetItem = materials_and_assembles_by_user.value.find(
          (kk) => kk.index === item
        );
        console.log("targetItem:", targetItem)

        payload = {
          begin_time: transStartTime,
          end_time: transEndTime,
          periodTime: transPeriodTime,
          user_id: currentUser.value.empID,
          order_num: targetItem.order_num,
          id: targetItem.id,
          process_type: 6,                          // 在成品區

          normal_work_time: true,                   // 正常工時
        };
        await createProcess(payload);
        console.log('步驟2-1...');

        //紀錄該筆的組裝完成數量
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
        console.log('步驟2-3...');

        //紀錄該筆的組裝完成狀態
        payload = {
          id: targetItem.id,
          record_name: 'isAssembleStationShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-4...');

        //下面這一段, 待討論....
        //
        //if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
        //  console.log("1張工單多批次運送, 新增未運送數量(相同工單)")
        //
        //  let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;
        //
        //  payload_new = {
        //    copy_id: myMaterial.id,
        //    total_delivery_qty: tempDelivery,
        //    show2_ok: 2,
        //    shortage_note: '',
        //  }
        //  await copyMaterial(payload_new);
        //  console.log('步驟2-4...');
        //}
        //
      });

      // 插入延遲 3 秒
      await delay(3000);

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }
      */
      //待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    })

    socket.value.on('station2_agv_ready', async () => {
      console.log('AGV 已在組裝區裝卸站, 收到 station2_agv_ready 訊息...');

      order_num_on_agv_blink.value = '';

      // 記錄等待 agv 到站結束時間
      agv1EndTime.value = new Date();
      console.log('AGV End time:', agv1EndTime.value);

      // 時間安全計算：確保 end >= start
      const startDate = new Date(agv1StartTime.value || Date.now());
      const endDate   = new Date(agv1EndTime.value   || Date.now());
      const startMs   = +startDate;
      const endMs     = Math.max(+endDate, startMs);

      const formattedStartTime = formatDateTime(new Date(startMs));
      const formattedEndTime   = formatDateTime(new Date(endMs));
      const agv1PeriodTime     = calculatePeriodTime(new Date(startMs), new Date(endMs));

      console.log('AGV 等待 Start Time:', formattedStartTime);
      console.log('AGV 等待 End   Time:', formattedEndTime);
      console.log('AGV 等待 Period    :', agv1PeriodTime);

      // 取乾淨且去重的 index 陣列
      const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIdx.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      // 記錄組裝區（AGV2）等待 AGV 的途程資料（process_type: 29）
      let successCount = 0;
      for (const idx of selectedIdx) {
        const rec = materials_and_assembles_by_user.value.find(i => i.index === idx);
        if (!rec) {
          console.warn('找不到資料，index =', idx);
          continue;
        }
        console.log('targetItem:', rec);

        try {
          await createProcess({
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: agv1PeriodTime,
            user_id: 'AGV2-1',  // 在組裝區(AGV2)等待時間(-1)
            order_num: rec.order_num,
            id: rec.id,         // material id
            process_type: 29,   // 在組裝區等待 AGV
            normal_work_time: true,
          });
          successCount++;
        } catch (e) {
          console.error('createProcess 失敗, material_id =', rec.id, e);
        }
      }

      // 成功至少一筆才更新 AGV 狀態與 UI
      if (successCount > 0) {
        await updateAGV({
          id: 1,
          status: 0, // ready
          station: 2, // 在組裝區
        });

        // UI 效果
        background.value = '#ffff00';
        isFlashLed.value = true;
        activeColor.value = 'blue'; // 機器人進站
      } else {
        console.warn('沒有任何流程寫入成功，略過 AGV 狀態更新與 UI 變更');
      }

      /*
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
          process_type: 29,                         //在組裝區

          normal_work_time: true,
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
      */
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
//onUnmounted(() => {   // 清除計時器（當元件卸載時）
  //window.removeEventListener('popstate', handlePopState)

  //clearInterval(intervalId);
//});

onBeforeRouteLeave(() => { disposeAllTimersOnce(); });
onUnmounted(() => { disposeAllTimersOnce(); });
onDeactivated(() => { disposeAllTimersOnce(); });

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  //initialize();
});

//=== method ===

//== timerDisplay用 ==

function onTimeUpdate(key, row, ms) {
  console.log('%c[TD] tick', 'color:#6A1B9A', key, ms)  // ← 應該會一直印
  lastTickMsMap.set(key, Number(ms) || 0)
}

// === B) 刷新後『從資料列』判斷是否已結束，計算要顯示的毫秒 ===
// 依你的資料欄位取用：常見有 end_time / isClosed / elapsedActive_time 等
function isRowClosed(item) {
  return !!(item?.end_time || item?.process_end_time || item?.isClosed === true)
}

// 從資料列取「最後的有效秒數」轉毫秒（依你的欄位擇一）
// 優先順序：elapsed_ms(毫秒) > *_ms 欄位 > *_time(秒)*1000 > 沒有就 0
function finalMsFromRow(item) {
  const candidates = [
    item?.elapsed_ms,
    item?.elapsedActive_time_ms,
    item?.elapsed_time_ms,
    (item?.elapsedActive_time ?? item?.elapsed_time) * 1000,
  ]
  for (const v of candidates) {
    const n = Number(v)
    if (Number.isFinite(n) && n >= 0) return n
  }
  return null
}

// 4) 從 localStorage 還原（刷新後用）
function pickMsFromLocalStorage(row) {
  const keys = []
  if (row?.process_id) {
    keys.push(`cp:lastClosedMs:pid:${row.process_id}`)
  }
  const asm = row?.assemble_id ?? 0
  const psc = row?.process_step_code ?? row?.process_type
  if (row?.id && psc != null) {
    keys.push(`cp:lastClosedMs:mat:${row.id}:pt:${psc}:asm:${asm}`)
  }
  for (const k of keys) {
    try {
      const raw = localStorage.getItem(k)
      if (!raw) continue
      const obj = JSON.parse(raw)
      if (obj && Number.isFinite(Number(obj.ms))) return Number(obj.ms)
    } catch {}
  }
  return null
}

// 5) 給 <TimerDisplay :displayMs="closedDisplayMs(item)">
function closedDisplayMs(item) {
  // 同頁剛結束的即時凍結
  if (frozenMsMap.has(item.id)) return frozenMsMap.get(item.id)

  // 刷新後：若 row 已結束 -> 優先用 row 的最終秒數
  if (isRowClosed(item)) {
    const msRow = finalMsFromRow(item)
    if (msRow != null) return msRow

    // row 沒帶值 -> 從 localStorage 撈
    const msCache = pickMsFromLocalStorage(item)
    if (msCache != null) return msCache
  }
  // 其他（未結束）-> 不凍結
  return null
}


function frozenMsOf(item) {
  return frozenMsMap.has(item.id) ? frozenMsMap.get(item.id) : null
}

function disposeAllTimersOnce() {
  if (__disposedAll) return;
  __disposedAll = true;

  try {
    for (const t of timerMap.values()) {
      try { t?.dispose?.(); } catch (_e) {}
    }
  } finally {
    timerMap.clear();
  }

  // 若不存在 pollId 變數，下面不會有副作用；存在就清掉
  try {
    if (typeof pollId !== 'undefined' && pollId) {
      clearInterval(pollId);
      // @ts-ignore
      pollId = null;
    }
  } catch (_e) {}
}

const isPausedOf  = (row) => getT(row)?.isPaused.value ?? true;

const getT = (row) => useRowTimer(row, currentUser.value.empID)

function getTByKey(key) {
   return timerMap.get(key) ?? makeStub()
}

function isRowPaused(row) {
  return !!useRowTimer(row, currentUser.value.empID).isPaused.value
}

function pauseLabel(row) {
  return isRowPaused(row) ? '開始' : '暫停'
}

function getInitialMs(row) {
  const t = useRowTimer(row, currentUser.value.empID)
  return Number(t?.elapsedMs?.value ?? 0)
}

async function ensureRestored(row) {
  const t = useRowTimer(row, currentUser.value.empID)
  if (!t) return
  // 21/22/23 的對應你已有邏輯，照舊取出 pType
  //const pType = row.process_step_code === 3 ? 21 : row.process_step_code === 2 ? 22 : 23
  const pType = processTypeOf(row)
  // 只做還原，不重置 begin_time
  await t.restoreProcess(row.id, pType, currentUser.value.empID, row.assemble_id || 0)
  return t
}

// 依 row.process_step_code → process_type
function processTypeOf(row) {
  const step = Number(row.process_step_code ?? 0)
  const work = row.assemble_work
  if (step === 3 || (step === 0 && work.includes('B109'))) return 21  // 組裝
  if (step === 2 || (step === 0 && work.includes('B110'))) return 22  // 檢驗
  if (step === 1 || (step === 0 && work.includes('B106'))) return 23  // 雷射
}

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

function setTimerEl(row, el) {
  if (!row || !row.id) {
    console.warn('setTimerEl(): row undefined', row)
    return
  }
  const t = getT(row);
  if (t)
    t.timerRef.value = el || null;
}

const setPausedOf = (row, v) => {
  const t = getT(row);

  //透過雙重否定，強制把任何輸入轉成純布林（truthy → true，falsy → false）
  //例如 1/"yes" 會變 true，0/""/null/undefined 會變 false
  //如果 t 存在且有 isPaused 這個 ref，就把它的值設成布林化後的 v
  if (t?.isPaused)
    t.isPaused.value = !!v
}

// 轉接 onTick（避免直接把函式呼叫結果當 handler）
const onTickOf = (key, row, ms) => {
  console.log("onTickOf..")
  //lastTickMsMap.set(row.id, Number(ms) || 0)
  lastTickMsMap.set(key, Number(ms) || 0)

  //const t = getT(row)
  const t = getTByKey(key)
  t?.onTick?.(ms)
}

function useRowTimer(row, uId) {
  // 🔐 防呆：row 或 id 不存在，回 stub
  if (!row || !row.id) {
    return makeStub()
  }

  const key = keyOf(row, uId)
  if (!timerMap.has(key)) {
    const timerRef = ref(null)
    const t = useProcessTimer(() => timerRef.value)     // hook
    // 這裡 t 內通常有：isPaused(ref)、elapsedMs(ref)、processId(ref)、onTick(fn)...
    timerMap.set(key, { ...t, timerRef })
  }
  return timerMap.get(key)
}

function releaseRowTimer(row, uId) {
  if (!row || !row.id) return
  const key = keyOf(row, uId)
  const t = timerMap.get(key)
  t?.dispose?.()
  timerMap.delete(key)
}

function revMapPtype(ptype) {
  const p = Number(ptype)
  if (p === 21) return 3   // 組裝 → step_code 3
  if (p === 22) return 2   // 檢驗 → step_code 2
  if (p === 23) return 1   // 雷射 → step_code 1
  return 3                 // 預設成 3（視你系統習慣）
}

const getIcon = (isPaused) => {
  return isPaused ? "mdi-play" : "mdi-pause"
}
//===

function reachTarget(row) {
  return Number(row.total_ask_qty_end || 0) >= Number(row.must_receive_end_qty || 0)
}

async function ensureStarted(row) {
  const t = useRowTimer(row, currentUser.value.empID)
  if (!t.processId.value) {
    const pType = processTypeOf(row)
    /*
    let temp_process_type=0
    if (row.process_step_code == 3 )
      temp_process_type=21
    if (row.process_step_code == 2 )
      temp_process_type=22
    if (row.process_step_code == 1 )
      temp_process_type=23
    console.log("row.id, temp_process_type, currentUser.value.empID, row.assemble_id:",row.id, temp_process_type, currentUser.value.empID, row.assemble_id)

    await t.startProcess(row.id, temp_process_type, currentUser.value.empID, row.assemble_id)
    */
    await t.startProcess(row.id, pType, currentUser.value.empID, row.assemble_id)
  }
  return t
}

async function onPauseToggle(row) {
  //if (reachTarget(row)) return
  const t = await ensureStarted(row)
  await t.toggleTimer()
}
/*
async function endTimer(row) {
  if (reachTarget(row)) return
  const q = Number(qtyInput.value[row.id] || 0)
  if (!q || q <= 0) {
    alert('請先輸入完成數量（receive_qty > 0）')
    return
  }
  const t = await ensureStarted(row)  // 必須已開始
  const res = await t.closeProcess({ receive_qty: q, assemble_id: row.id }) // 透過 hook

  if (!res?.success) {
    alert(res?.message || '關閉失敗')
    return
  }
  if (typeof res.total_completed === 'number') {
    row.total_ask_qty_end = res.total_completed
  }
  // 達標 → Begin / End 的按鈕皆會因 reachTarget(row) 被鎖
  qtyInput.value[row.id] = 0
}
*/
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
    await getCountMaterialsAndAssemblesByUser(payload);

    // 為materials_and_assembles_by_user每個物件增加 pickEnd 屬性，初始為空陣列 []
    materials_and_assembles_by_user.value.forEach(item => {
      item.pickEnd = [];
    });

    //== timerDisplay用 ==
    await nextTick()

    // 把正確的時間 & 暫停狀態直接推到 <TimerDisplay />
    for (const row of materials_and_assembles_by_user.value) {
      await ensureRestored(row)   // 還原「目前是否在跑、已經跑了幾秒」
    }
    //===

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
  //let temp_TF =(item.whichStation != 2 || item.input_end_disable) || item.process_step_code;
  //let temp_TF =(item.whichStation != 2 || item.input_end_disable);
  let temp_TF = item.input_end_disable;
  //let temp_TF =(item.whichStation != 2 || item.input_end_disable) || !item.process_step_enable;
  //console.log("temp_TF:", item.input_end_disable, "TF:", temp_TF)
  //console.log("temp_TF:", item.assemble_id,  temp_TF)
  return temp_TF;
};

const checkReceiveQty = (item) => {
  console.log("checkReceiveQty(),", item);

  item.receive_qty = Number(item.receive_qty || 0);

  //const total = Number(item.receive_qty)+Number(item.abnormal_qty)
  const total = Number(item.receive_qty) || 0;    //完成數量
  const temp = Number(item.must_receive_end_qty)  //應完成數量
  const diff = Number(item.abnormal_qty)
  const tmp = temp - diff
  if (total > tmp) {
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

const onAbnormalQtyUpdate = (item, value) => {
  item.abnormal_qty = value;

  // 當 item.code = '109' 時，組裝途程, 自動同步到 item.isAssembleFirstAlarm_qty
  if (item.code === '109') {
    item.isAssembleFirstAlarm_qty = value;
  }

  // 保留原本的檢查邏輯
  checkAbnormalQty(item);
};

const checkAbnormalQty = (item) => {
  console.log("checkAbnormalQty(),", item);

  item.abnormal_qty = Number(item.abnormal_qty || 0);

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

const getBtnStyle = (item) => {
  return {
    fontSize: '13px',
    fontWeight: '700',
    fontFamily: "'微軟正黑體', sans-serif",
    marginLeft: '0px !important',
    //paddingLeft: '4px',
    //paddingRright: '4px',
    background: computed(() => {
      if (item.process_step_code == 3) {
        return item.isAssembleFirstAlarm ? '#e8eaf6' : '#ff0000'
      } else {
        return item.alarm_enable ? '#e8eaf6' : '#ff0000'
      }
      /*
      if (!item.input_abnormal_disable) {
        return item.alarm_enable ? '#e8eaf6' : '#ff0000'
      } else {
        return item.isAssembleFirstAlarm ? '#e8eaf6' : '#ff0000'
      }
      */
    }).value,
    //color: item.alarm_enable ? '#000' : '#fff'

    color: computed(() => {
      if (item.process_step_code == 3) {
        return item.isAssembleFirstAlarm ? '#000' : '#fff'
      } else {
        return item.alarm_enable ? '#000' : '#fff'
      }
    }).value,
  }
}

const setActive = (value) => {
  toggle_exclusive.value = value;       // 設置當前活動按鈕
  if (toggle_exclusive.value == 1) {
    showMenu.value = true;
    transport_message.value = '組裝料件人工送出'
  } else {
    showMenu.value = false;
    transport_message.value = '組裝料件自動送出'
  }
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

const select_transportation_method = () => {
  if (toggle_exclusive.value == 1) {
    callForklift();
  } else {
    callAGV();
  }
};

const callForklift = async () => {
  console.log("callForklift()...");

  const selectedIdx = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
  if (selectedIdx.length === 0) {
    showSnackbar('請選擇送料的工單!', 'red accent-2');
    return;
  }
  if (isCallForklift.value) {
    showSnackbar('請不要重複按鍵!', 'red accent-2');
    return;
  }

  isCallForklift.value = true;
  try {
    console.log('trans_end 處理步驟1...');

    // 步驟1：更新各種狀態欄位（成品站 / 等待入庫 / 關閉組裝站顯示 / 堆高機標記 / must_allOk_qty）
    for (const idx of selectedIdx) {
      const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
      if (!rec) {
        console.warn('找不到資料，index =', idx);
        continue;
      }
      const mid = rec.id;

      await updateMaterialRecord({
        id: mid,
        show1_ok: 3,    // 成品站
        show2_ok: 10,   // 等待入庫
        show3_ok: 3,    // 等待組裝中
        whichStation: 3 // 目標途程: 成品站
      });

      await updateAssmbleDataByMaterialID({
        material_id: mid,
        delivery_qty: 0,
        record_name1: 'show1_ok',
        record_data1: 3,
        record_name2: 'show2_ok',
        record_data2: 10,
        record_name3: 'show3_ok',
        record_data3: 3               // 等待組裝中
      });

      // 堆高機搬運標記（第二段）
      await updateMaterial({
        id: mid,
        record_name: 'move_by_automatic_or_manual_2',
        record_data: false
      });

      // 關閉組裝站顯示
      await updateAssembleMustReceiveQtyByMaterialID({
        material_id: mid,
        record_name: 'isAssembleStationShow',
        record_data: false
      });

      // must_allOk_qty 以收料數為準（數值化）
      await updateMaterial({
        id: mid,
        record_name: 'must_allOk_qty',
        record_data: Number(rec.receive_qty) || 0
      });
    }

    console.log('agv_end 處理步驟2...');

    // 步驟2：建立 Process（成品區）＋ 完成數量/狀態寫回
    for (const idx of selectedIdx) {
      const rec = materials_and_assembles_by_user.value.find(kk => kk.index === idx);
      if (!rec) continue;

      await createProcess({
        //user_id: currentUser.value?.empID ?? '',
        user_id: selectedEmployee.value,
        id: rec.id,
        process_type: 6 // 在成品區（堆高機）
      });
      console.log('步驟2-1...');

      await updateMaterial({
        id: rec.id,
        record_name: 'assemble_qty',
        record_data: Number(rec.delivery_qty) || 0
      });
      console.log('步驟2-2...');

      const total = (Number(rec.total_assemble_qty) || 0) + (Number(rec.delivery_qty) || 0);
      await updateMaterial({
        id: rec.id,
        record_name: 'total_assemble_qty',
        record_data: total
      });
      console.log('步驟2-3...');

      await updateMaterial({
        id: rec.id,
        record_name: 'isAssembleStationShow',
        record_data: true
      });
      console.log('步驟2-4...');
    }

    // 插入延遲 3 秒
    await delay(3000);

    // 清理選取
    selectedItems.value = [];
    if (localStorage.getItem('selectedItems')) {
      localStorage.removeItem('selectedItems');
    }
  } catch (err) {
    console.error('堆高機流程例外：', err);
    showSnackbar('堆高機流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    // 一定要解鎖，避免按鈕被鎖死
    await delay(3000);

    isCallForklift.value = false;
  }

  /*
  let payload = {};

  if (!isCallForklift.value) {                          // 沒有重複呼叫
    if (selectedItems.value.length == 0) {              // 已點選選單
      showSnackbar("請選擇送料的工單!", 'red accent-2');
      return;
    }
    isCallForklift.value = true
  } else {
    showSnackbar("請不要重複按鍵!", 'red accent-2');
    return;
  } // end if

  console.log('trans_end 處理步驟1...');
  selectedItems.value.forEach(async (item) => {
    console.log('selectedItems, item:', item);

    targetItem = materials_and_assembles_by_user.value.find(
      (kk) => kk.index === item
    );
    console.log("targetItem:", targetItem)

    let current_assemble_id=targetItem.assemble_id
    let current_material_id=targetItem.id

    payload = {
      id: current_material_id,
      show1_ok: 3,        // 成品站
      show2_ok: 10,       // 等待入庫
      show3_ok: 3,        // 等待組裝中
      whichStation: 3,    // 目標途程:成品站
    };
    await updateMaterialRecord(payload);

    payload = {
      material_id: current_material_id,
      delivery_qty: 0,
      record_name1: 'show1_ok',
      record_data1: 3,
      record_name2: 'show2_ok',
      record_data2: 10,
      record_name3: 'show3_ok',
      record_data3: 3,
    };
    await updateAssmbleDataByMaterialID(payload)

    payload = {
      id: targetItem.id,
      record_name: 'move_by_automatic_or_manual_2',
      record_data: false
    };
    await updateMaterial(payload);

    payload = {
      material_id: current_material_id,
      record_name: 'isAssembleStationShow',
      record_data: false,
    };
    await updateAssembleMustReceiveQtyByMaterialID(payload);

    payload = {
      id: current_material_id,
      record_name: 'must_allOk_qty',
      record_data: Number(targetItem.receive_qty)
    };
    await updateMaterial(payload);
  }); // end forEach loop

  console.log('agv_end 處理步驟2...');
  selectedItems.value.forEach(async (item) => {
    targetItem = materials_and_assembles_by_user.value.find(
      (kk) => kk.index === item
    );
    console.log("targetItem:", targetItem)

    payload = {
      user_id: currentUser.value.empID,
      id: targetItem.id,
      process_type: 6,                          // 在成品區
    };
    await createProcess(payload);
    console.log('步驟2-1...');

    //紀錄該筆的組裝完成數量
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
    console.log('步驟2-3...');

    //紀錄該筆的組裝完成狀態
    payload = {
      id: targetItem.id,
      record_name: 'isAssembleStationShow',
      record_data: true
    };
    await updateMaterial(payload);
    console.log('步驟2-4...');

    //下面這一段, 待討論....
    //
    //if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
    //  console.log("1張工單多批次運送, 新增未運送數量(相同工單)")
    //
    //  let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;
    //
    //  payload_new = {
    //    copy_id: myMaterial.id,
    //    total_delivery_qty: tempDelivery,
    //    show2_ok: 2,
    //    shortage_note: '',
    //  }
    //  await copyMaterial(payload_new);
    //  console.log('步驟2-4...');
    //}
    //
  });

  // 插入延遲 3 秒
  await delay(3000);

  selectedItems.value = [];
  if (localStorage.getItem('selectedItems')) {
    localStorage.removeItem('selectedItems');
  }
  */
  //待待
  window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
//##
};

const callAGV = async () => {
  console.log("callAGV()...")

  const selectedRaw = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
  if (selectedRaw.length === 0) {
    showSnackbar('請選擇送料的工單!', 'red accent-2');
    return;
  }
  if (isCallAGV.value) {
    showSnackbar('請不要重複按鍵!', 'red accent-2');
    return;
  }

  isCallAGV.value = true;
  try {
    // 讀 AGV 狀態
    await getAGV({ agv_id: 1 });
    console.log('hello, 組裝區叫車, AGV 狀態:', currentAGV.value);
    // 若要強制攔截忙碌可解開下列註解
    // if (currentAGV.value?.station !== 2 || currentAGV.value?.status !== 0) {
    //   showSnackbar('AGV 目前忙碌中...', 'red accent-2');
    //   return;
    // }

    // 將 index / id 映射成完整記錄
    const entries = selectedRaw.map(item => {
      const rec = materials_and_assembles_by_user?.value
        ? materials_and_assembles_by_user.value.find(i => i.index === item)
        : null;
      // 兼容：若找不到 rec，fallback 用 item 當成 id/assemble_id
      return {
        index: item,
        id: rec?.id ?? item,
        assemble_id: rec?.assemble_id ?? rec?.id ?? item,
        order_num: rec?.order_num ?? null,
      };
    });

    // 送出叫車事件（真的帶 payload）
    socket.value.emit('station2_call', {
      indices: selectedRaw,
      materialIds: entries.map(e => e.id),
      assembleIds: entries.map(e => e.assemble_id),
      orderNums: entries.map(e => e.order_num).filter(Boolean),
    });
    console.log('送出 station2_call 訊息...');

    // UI：進入等待運輸
    order_num_on_agv_blink.value = '叫車進站中...';
    activeColor.value = 'red';

    // 記錄等待 agv 開始時間
    agv1StartTime.value = new Date();
    console.log('AGV Start time:', agv1StartTime.value);

    // 逐筆更新 show3_ok = 1（等待 AGV）
    for (const e of entries) {
      try {
        await updateMaterial({
          id: e.id,
          record_name: 'show3_ok',
          record_data: 1,             // 等待 AGV
        });

        await updateAssemble({
          assemble_id: e.assemble_id,
          record_name: 'show3_ok',
          record_data: 1,             // 等待 AGV
        });
      } catch (err) {
        console.error(`更新等待 AGV 狀態失敗，material_id=${e.id}, assemble_id=${e.assemble_id}`, err);
      }
    }
  } catch (err) {
    console.error('組裝區叫車流程例外：', err);
    showSnackbar('叫車流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    // 一定要解鎖，避免按鈕被卡住
    isCallAGV.value = false;
  }


  /*
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
  */
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  item.receive_qty = Number(item.receive_qty) || 0;

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

const onClickEnd = async (item) => {
  console.log("PickReportForAssembleEnd, onClickEnd(), 按結束鍵", item);

  item.receive_qty = Number(item.receive_qty || 0);

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

  const q = Number(item.receive_qty || 0);
  /*
  const ok = await confirmRef.value.open({
    title: endTitle.value,
    message: endMessage.value,
    okText: '確定',
    cancelText: '取消',
  })

  if (!ok) {
    return
  }
  */
  if (!(await confirmRef.value.open({
    title: endTitle.value,
    message: endMessage.value,
    okText: '確定',
    cancelText: '取消',
  }))) return

  console.log("判斷是否異常:", item.alarm_enable)
  const test_alarm_message='異常: 異常工時!'

  //# step block A
  // 先凍結畫面要停住的毫秒值（優先用最後 tick；沒有就用初始）
  //const lastMs = lastTickMsMap.get(item.id) ?? getInitialMs(item) ?? 0
  //frozenMsMap.set(item.id, lastMs)
  const k = makeKey(item)
  const lastMs = lastTickMsMap.get(k) ?? getInitialMs(item) ?? 0
  frozenMsMap.set(k, lastMs)

  const t = await ensureStarted(item)         // 確保有開始過（若沒開始會自動 start）
  let myProcessId=t.processId?.value ?? null
  await t.closeProcess({ receive_qty: q, alarm_enable: item.alarm_enable, alarm_message: test_alarm_message, assemble_id: item.assemble_id, elapsed_ms: lastMs });

  t.dispose()  // 再停止一切計時/回寫（避免之後還有 /dialog2UpdateProcessBegin）
  //#

  // 取得目前table data record 的 index, targetIndex
  const targetIndex = materials_and_assembles_by_user.value.findIndex(
    (kk) => kk.assemble_id === item.assemble_id
  );
  //console.log("targetIndex assemble_id:", targetIndex)

  // //組裝區途程完成(按結束定鍵) && AGV還沒送出
  //enableDialogBtn.value = item.isAssembleStation3TakeOk && !item.isAssembleStationShow;

  let current_assemble_id=materials_and_assembles_by_user.value[targetIndex].assemble_id
  let current_material_id=materials_and_assembles_by_user.value[targetIndex].id
  let current_code=materials_and_assembles_by_user.value[targetIndex].code

  // 1-1.更新記錄, 完成數量
  let current_completed_qty= Number(item.receive_qty);    //組裝區完成數量
  console.log("current:", current_completed_qty, current_assemble_id)

  let payload = {
    assemble_id: current_assemble_id,
    record_name: 'completed_qty',
    record_data: current_completed_qty,
    //record_data: 0,
  };
  await updateAssemble(payload);

  let current_total_completed_qty=Number(item.total_completed_qty_num);   //組裝區完成數量的總數(已完成總數量)
  let total = current_total_completed_qty + current_completed_qty;
  item.total_completed_qty_num = total;

  item.total_completed_qty ='(' + total.toString().trim() + ')';

  // 1-2.記錄當前已完成總數量
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'total_completed_qty',
    record_data: total,
  };
  await updateAssemble(payload);

  // 新增完成數量與完成數量不同時, 新紀錄的應領取數量
  let d0 = Number(item.must_receive_end_qty)
  let d1 = Number(item.receive_qty)
  let d2 = Number(item.abnormal_qty)
  //let difference = Number(item.must_receive_end_qty - item.receive_qty - item.abnormal_qty)
  let difference = d0 - d1 - d2
  //payload = {
  //  copy_assemble_id: current_assemble_id,
  //  copy_assemble_must_receive_qty: difference,
  //  copy_assemble_process_step_code: item.process_step_code
  //}
  //await copyNewIdAssemble(payload);
  if (difference != 0) {
    console.log("有difference...., difference,d0,d1,d2:", difference,d0,d1,d2)
    payload = {
      copy_id: current_assemble_id,
      must_receive_qty: difference,
    }
    await copyAssembleForDifference(payload);
  }

  // 紀錄當前已結束完成數量顯示順序(組裝/檢驗/雷射)
  let temp_qty=1  //組裝
  if (item.process_step_code == 2 )
    temp_qty=2    //檢驗
  if (item.process_step_code == 1 )
    temp_qty=3    //雷射
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'total_ask_qty_end',
    record_data: temp_qty,
  };
  await updateAssemble(payload);

  // 2.取得組裝區目前途程的show2_ok/show3_ok訊息類型(結束)
  checkInputStr(item.assemble_work);

  // 3.更新組裝區目前途程的show2_ok狀態顯示訊息類型(結束)
  payload = {
    id: current_material_id,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step2
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step2,
  };
  await updateAssemble(payload);

  // 4.更新組裝區目前途程的show3_ok狀態顯示訊息類型(結束)
  payload = {
    id: current_material_id,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step2
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step2,
  };
  await updateAssemble(payload);

  // 5. 更新組裝區目前途程紀錄, 不能再輸入
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_end_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_abnormal_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      input_end_disable: true,
      input_abnormal_disable: true,
    };
  }
  /*
  //待查
  // 完成組裝區目前製程(組裝 或 檢驗 或 雷射), 且是最後製程
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'isAssembleStationShow',
    record_data: true,
  };
  await updateAssemble(payload);

  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      isAssembleStationShow: true,
    };
  }
  */
  // 待待
  //await listWaitForAssemble();

  // 記錄當前完工生產結束時間
  let formattedStartTime = item.currentStartTime  //領料生產報工開始時間
  let endTime = new Date();                                                         // 記錄當前結束時間
  let formattedEndTime = formatDateTime(endTime); //完工生產報工結束時間
  periodTime.value = calculatePeriodTimeStr(formattedStartTime, formattedEndTime);  // 計算時間間隔
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'currentEndTime',
    record_data: formattedEndTime,
  };
  await updateAssemble(payload);

  // 記錄當前紀錄, 目前途程結束
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'process_step_code',
    record_data: 0,
  };
  await updateAssemble(payload);

  // 若組裝區內所有途程結束, 並記錄組裝區內所有途程結束
  //payload = {
  //  id: current_material_id,
  //  assemble_id: current_assemble_id,
  //};
  let response = await updateAssembleProcessStep({id: current_material_id, assemble_id: current_assemble_id});
  console.log("確認是否為最後工序或只有1個工序...")
  console.log("response || item.assemble_count == 1", response, item.assemble_count)

  if (response || item.assemble_count == 1) { //當前工單最終途程或當前工單只有1個途程(組裝)
    console.log("take ok...")
    /*
    // 記錄當前工單最終途程的完成總數量
    payload = {
      //assemble_id: item.assemble_id,
      //assemble_id: materials_and_assembles_by_user.value[targetIndex].assemble_id,
      assemble_id: current_assemble_id,
      record_name: 'total_completed_qty',
      record_data: current_completed_qty,
    };
    await updateAssemble(payload);
    */
    //if (targetItem) {
    //  targetItem.isAssembleStation3TakeOk = true;
    //}
    //if (targetIndex !== -1) {
    //  // 用 Vue 的方式確保觸發響應式更新
    //  materials_and_assembles_by_user.value[targetIndex] = {
    //    ...materials_and_assembles_by_user.value[targetIndex],
    //    isAssembleStation3TakeOk: true,
    //  };
    //}
    console.log("step5-0...");
    /*
    payload = {
      mid: current_material_id,
      code: current_code,
      user_id: currentUser.value.empID,
    };
    const tdata = await getMaterialsAndAssemblesAndTime(payload)
    console.log("last_time:",tdata)

    // 完成組裝區目前製程(組裝 或 檢驗 或 雷射), 且是最後製程
    payload = {
      assemble_id: current_assemble_id,
      record_name: 'isAssembleStationShow',
      record_data: true,
    };
    await updateAssemble(payload);

    payload = {
      assemble_id: current_assemble_id,
      record_name: 'isShowLastTime',
      record_data: true,
    };
    await updateAssemble(payload);

    payload = {
      assemble_id: current_assemble_id,
      record_name: 'LastTime',
      record_data: tdata.last_time,
    };
    await updateAssemble(payload);
    */
    if (targetIndex !== -1) {
      // 用 Vue 的方式確保觸發響應式更新
      materials_and_assembles_by_user.value[targetIndex] = {
        ...materials_and_assembles_by_user.value[targetIndex],
        isAssembleStationShow: true,
        //isShowLastTime: true,
        //LastTime: last_time,
      };
    }

    console.log("step5-1...");

    // 紀錄組裝去下一製程的應領取數量
    payload = {
      //assemble_id: item.id,
      assemble_id: current_assemble_id,
      must_receive_qty: 'must_receive_end_qty',
      completed_qty: current_completed_qty,
    };
    await updateAssembleMustReceiveQtyByAssembleID(payload);

    payload = {
      process_id: myProcessId,
      record_name: 'normal_work_time',
      record_data: 3,
    };
    await updateProcessData(payload);

  } else {
    console.log("step5-2...");

    // 紀錄組裝去下一製程的應領取數量
    payload = {
      //assemble_id: item.id,
      assemble_id: current_assemble_id,
      must_receive_qty: 'must_receive_end_qty',
      completed_qty: current_completed_qty,
      //completed_qty: 0,
    };
    await updateAssembleMustReceiveQtyByAssembleID(payload);

    payload = {
      process_id: myProcessId,
      record_name: 'normal_work_time',
      record_data: 1,
    };
    await updateProcessData(payload);

    ////待待
    //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
  }

  //待待
  window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};


const onClickAbnormal = async (item) => {
  console.log("onClickAbnormal(), 組裝異常資料:", item);

  // 檢查異常欄位是否輸入了空白或 0
  if (!item.abnormal_qty || Number(item.abnormal_qty) === 0) {
    console.log("檢驗異常程序...")

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

  let current_assemble_id=materials_and_assembles_by_user.value[targetIndex].assemble_id
  let current_material_id=materials_and_assembles_by_user.value[targetIndex].id

  //let temp_alarm_enable = item.alarm_enable;    //按鍵之前
  //temp_alarm_enable = !temp_alarm_enable        //按鍵之後

  // 更新紀錄, false: 按了異常鍵->異常
  let payload = {
    //assemble_id: item.assemble_id,
    assemble_id: current_assemble_id,
    record_name: 'alarm_enable',
    record_data: false,
  };
  await updateAssemble(payload);

  //顯示按鍵之後的值(顏色)
  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      alarm_enable: false,
    };
  }

  // 更新紀錄, 訂單當前組裝狀況(false:異常, true:正常)
  payload = {
    //id: item.id,
    id: current_material_id,
    record_name: 'isAssembleAlarm',
    record_data: false
  };
  await updateMaterial(payload);

  let temp_abnormal_qty = Number(item.abnormal_qty) || 0;
  let temp_diff = Number(item.must_receive_end_qty) - Number(item.abnormal_qty);
  console.log("temp_abnormal_qty, temp_diff:", temp_abnormal_qty, temp_diff)

  // 1.更新記錄, 異常數量
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'abnormal_qty',
    record_data: temp_abnormal_qty,
  };
  await updateAssemble(payload);


  await updateAssembleTableData(payload);

  //await listWaitForAssemble();

  // 3. 新增異常組裝製程的應領取數量
  payload = {
    copy_id: current_assemble_id,
    must_receive_qty: temp_abnormal_qty,
  }
  await copyNewAssemble(payload);

  // 2. 更新組裝區目前途程異常欄位, 不能再輸入
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_abnormal_disable',
    record_data: true,
  };
  await updateAssemble(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'alarm_enable',
    record_data: false,           // 異常
  };
  await updateAssemble(payload);

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'must_receive_end_qty',
    record_data: temp_diff,
  };
  await updateAssemble(payload);

  if (targetIndex !== -1) {
    // 用 Vue 的方式確保觸發響應式更新
    materials_and_assembles_by_user.value[targetIndex] = {
      ...materials_and_assembles_by_user.value[targetIndex],
      input_abnormal_disable: true,
      alarm_enable: false,              //異常
      must_receive_end_qty: temp_diff,
    };
  }

  await getMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID });
  await getCountMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID });

  //== timerDisplay用 ==
  await nextTick();
  // 把正確的時間 & 暫停狀態直接推到 <TimerDisplay />
  for (const row of materials_and_assembles_by_user.value) {
    await ensureRestored(row)   // 還原「目前是否在跑、已經跑了幾秒」
  }
  //===
};
// end onClickAbnormal()

/*
let abnormalBusy = false

const onClickAbnormal = async (rawItem) => {
  if (abnormalBusy) return
  abnormalBusy = true

  // 先做快照，避免中途 reactive 變動
  const item = { ...rawItem }

  try {
    console.log("onClickAbnormal(), 組裝異常資料:", item)

    // ===== 1) 基本驗證 =====
    const parsedQty = Number(item.abnormal_qty)
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      abnormal_qty_alarm.value = '異常數量不可為空白或 0！'
      rawItem.abnormal_tooltipVisible = true
      setTimeout(() => { rawItem.abnormal_tooltipVisible = false; rawItem.abnormal_qty = '' }, 2000)
      console.error('異常數量不可為空白或 0！')
      return
    }

    // 取 assemble/material 的識別
    const list = materials_and_assembles_by_user.value || []
    const targetIndex = list.findIndex(kk => kk.assemble_id === item.assemble_id)

    // 安全取得 id（targetIndex=-1 也能跑）
    const current_assemble_id = targetIndex !== -1
      ? list[targetIndex].assemble_id
      : (item.assemble_id ?? item.id)
    const current_material_id = targetIndex !== -1
      ? list[targetIndex].id
      : (item.id ?? item.material_id)

    if (!current_assemble_id || !current_material_id) {
      abnormal_qty_alarm.value = '系統資料不完整（缺少組裝/訂單識別），請重整後再試。'
      rawItem.abnormal_tooltipVisible = true
      setTimeout(() => { rawItem.abnormal_tooltipVisible = false }, 2000)
      console.error('缺少 assemble_id 或 material_id')
      return
    }

    // ===== 2) 夾限 & 計算新值 =====
    const remain = Number(item.must_receive_end_qty) || 0
    if (remain <= 0) {
      abnormal_qty_alarm.value = '目前無可扣減的應結數量。'
      rawItem.abnormal_tooltipVisible = true
      setTimeout(() => { rawItem.abnormal_tooltipVisible = false }, 2000)
      return
    }

    const abnormalQty = Math.min(parsedQty, remain) // 不超過剩餘
    const newRemain = Math.max(0, remain - abnormalQty)
    if (abnormalQty !== parsedQty) {
      abnormal_qty_alarm.value = `異常數量自動調整為 ${abnormalQty}（不可超過剩餘 ${remain}）。`
      rawItem.abnormal_tooltipVisible = true
      setTimeout(() => { rawItem.abnormal_tooltipVisible = false }, 2000)
    }

    // ===== 3) UI 樂觀更新（一次到位，避免前後不一致）=====
    const optimisticRow = {
      ...(targetIndex !== -1 ? list[targetIndex] : rawItem),
      alarm_enable: false,                 // 異常 → 鈴鐺關
      input_abnormal_disable: true,       // 異常欄位唯讀
      abnormal_qty: abnormalQty,          // 顯示夾限後數量
      must_receive_end_qty: newRemain,    // 扣掉異常數量
    }
    if (targetIndex !== -1) {
      materials_and_assembles_by_user.value[targetIndex] = optimisticRow
    } else {
      Object.assign(rawItem, optimisticRow)
    }

    // ===== 4) 後端更新（盡量併發）=====
    // A. 先把 alarm 與 material 狀態落地（你的語意：true=正常、false=異常）
    await Promise.all([
      updateAssemble({ assemble_id: current_assemble_id, record_name: 'alarm_enable', record_data: false }),
      updateMaterial({ id: current_material_id, record_name: 'isAssembleAlarm', record_data: false }),
    ])

    // B. 寫入異常數量 / 鎖住異常欄位 / 更新剩餘
    await Promise.all([
      updateAssemble({ assemble_id: current_assemble_id, record_name: 'abnormal_qty', record_data: abnormalQty }),
      updateAssemble({ assemble_id: current_assemble_id, record_name: 'input_abnormal_disable', record_data: true }),
      updateAssemble({ assemble_id: current_assemble_id, record_name: 'must_receive_end_qty', record_data: newRemain }),
    ])

    // C. 產生異常返工/補料單位的「新組裝」應領取數
    await copyNewAssemble({
      copy_id: current_assemble_id,
      must_receive_qty: abnormalQty,
    })

    // ===== 5) 重新拉資料（避免與後端飄移）=====
    await Promise.all([
      getMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID }),
      getCountMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID }),
    ])

    // ===== 6) == TimerDisplay 用 ==（你補的段落）=====
    await nextTick()
    for (const row of materials_and_assembles_by_user.value) {
      await ensureRestored(row)   // 還原「目前是否在跑、已經跑了幾秒」
    }

  } catch (err) {
    console.error('onClickAbnormal 發生錯誤：', err)
    // 簡單回滾策略：重新拉資料覆蓋本地樂觀更新
    await Promise.all([
      getMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID }),
      getCountMaterialsAndAssemblesByUser({ user_id: currentUser.value.empID }),
    ])
    abnormal_qty_alarm.value = '提交異常失敗，請稍後再試或聯絡系統管理員。'
    rawItem.abnormal_tooltipVisible = true
    setTimeout(() => { rawItem.abnormal_tooltipVisible = false }, 2000)

  } finally {
    // 清空輸入避免殘值
    rawItem.abnormal_qty = ''
    abnormalBusy = false
  }
}
*/

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
  console.log("outputStatus:", outputStatus.value);
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

    console.log("離開 focus");
    if (item.receive_qty === '' || item.receive_qty === null || item.receive_qty === undefined) {
      item.receive_qty = 0;
    }

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
  //}
  } else {
    console.log("進入 focus");
    if (item.receive_qty === 0 || item.receive_qty === '0') {
      item.receive_qty = '';
    }
  }
};


const checkAbnormalField = (focused, item) => {
  if (!focused) { // 當失去焦點時
    console.log("checkAbnormalField()...");

    console.log("離開 focus");
    if (item.abnormal_qty === '' || item.abnormal_qty === null || item.abnormal_qty === undefined) {
      item.abnormal_qty = 0;
    }

  } else {
    console.log("進入 focus");
    if (item.abnormal_qty === 0 || item.abnormal_qty === '0') {
      item.abnormal_qty = '';
    }
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

:deep(input#bar_code[type="text"]) {
  color: black !important;
}

.custom-table {
  //border-collapse: collapse;  // 合併邊框
  //border: 1px solid #000;     // 表格的外框
  border-radius: 0 0 20px 20px;
}


.action-cell {
  display: flex;
  align-items: center;
  gap: 6px;             // 按鈕間距
  white-space: nowrap;  // 禁止換行
  width: 300px;         // 寬度（可視需要調整）
  padding: 0 2px;
  position: relative;
  right:40px;
}

.action-cell .v-btn {
  min-width: 0 !important;      // 取消 64px 的預設
  padding: 0 8px !important;    // 縮小內距
}

.action-cell .v-btn .v-icon {
  margin-inline-start: 4px;     // icon 與文字保留一點距離
}
/*
:deep(.custom-table th:nth-child(9)),
:deep(.custom-table td:nth-child(9)) {
  padding-left: 4px !important;
  padding-right: 4px !important;
  //margin-left:  0px !important;
  margin-right:  5px !important;
}
*/
:deep(.custom-table th:nth-child(5)),
:deep(.custom-table td:nth-child(5)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(6)),
:deep(.custom-table td:nth-child(6)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(7)),
:deep(.custom-table td:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(8)),
:deep(.custom-table td:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table td:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table td:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.custom-table td:nth-child(11)) {
  padding-left: 0 !important;
  //padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(11)) {
  padding-left: 0 !important;
  //padding-right: 0 !important;
}

:deep(.custom-table th:nth-child(10) div) {
  justify-content: center;
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

:deep(.v-table__wrapper > table > thead th:first-child > span) {
  position: relative;
  left: 5px;
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

:deep(.v-switch .v-label) {
  font-weight: 600;
}
</style>

