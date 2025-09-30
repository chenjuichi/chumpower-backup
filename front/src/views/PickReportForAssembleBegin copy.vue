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

  <!--items-per-page-text="每頁的資料筆數"-->
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
          組裝區領料生產報工
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

          <!--客製化 堆高機送料中按鍵-->
          <!--
          <v-btn
            :disabled="!station2_trans_ready"
            color="primary"
            variant="outlined"
            :style="{
              position: 'relative',
              right: screenSizeInInches > 20 ? '600px' : '570px',
              top: '0px',
              fontWeight: '700',
              width: '120px',
              background: '#e67e22',
              background: station2_trans_ready ? '#e67e22' : '#e7e9eb',
            }"
            @click="forkliftNoticeFun"
          >

            <div v-if="station2_trans_ready" class="blink" style="display: flex; align-items: center;">
              <v-icon left color="#fff">mdi-forklift</v-icon>
              <span style="color: #fff;">堆高機送料中</span>
            </div>
            <div v-else style="display: flex; align-items: center;">
              <v-icon left color="#000">mdi-forklift</v-icon>
              <span style="color: #000;">堆高機送料中</span>
            </div>
          </v-btn>

          <div style="display: flex; flex-direction: column; align-items: center;">
            <div style="position:relative;right: 550px; font-size: 16px;">{{ station2_trans_empName }}</div>
          </div>
          -->

          <!--
          <v-btn
            v-if="materials_and_assembles.length > 0"
            color="primary"
            variant="outlined"
            style="position: relative; right: 500px; top: 0px;"
            @click="refreshComponent"
          >
            <v-icon left color="blue">mdi-refresh</v-icon>
            更新訂單
          </v-btn>
          -->

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

    <!-- 客製化 '需求數量' (req_qty) 欄位的表頭 2025-06-13 modify, 改順序 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div>需求</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '備料數量' (delivery_qty) 欄位的表頭 2025-06-13 modify, 改順序 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div>備料</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '應領取數量' (must_receive_qty) 欄位的表頭 2025-06-13 add, 改順序 -->
    <template v-slot:header.must_receive_qty="{ column }">
      <div style="text-align: center;">
        <div>應領取</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '領取數量' (receive_qty) 欄位的表頭 -->
  <!--ready modify 2025-09-15
    <template v-slot:header.receive_qty="{ column }">
      <div style="text-align: center;">
        <div>領取</div>
        <div>數量</div>
      </div>
    </template>
  -->

    <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
    <template v-slot:item.order_num="{ item }">
    <!--
      <div>
        <div>{{ item.order_num }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
      </div>
    -->
      <div>
        <div style="color:black; font-size:12px; margin-right:2px;" v-if="item.isLackMaterial != 99">
          {{ item.order_num }}&nbsp;&nbsp;
          <span style="color:red; font-weight:700; font-size:12px;">缺料</span>
        </div>
        <div style="color:black; font-size:12px; margin-right:20px; margin-left: -15px;" v-else>
          {{ item.order_num }}
        </div>
        <div style="color: #a6a6a6; font-size:12px; margin-right: 40px;">{{ item.assemble_work }}</div>
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
            <span v-for="(pickItem, idx) in item.pickBegin" :key="idx">
              {{ pickItem }}
              <span v-if="idx < item.pickBegin.length - 1">, </span>
            </span>
            ]
          </span>
        </div>
      </v-hover>
    </template>
  -->
    <!-- 自訂 '應領取數量'欄位的資料藍位 -->
    <template v-slot:item.must_receive_qty="{ item }">
      <div style="display: flex; align-items: center;">
        <template v-if="item.process_step_code == 3 && item.is_copied_from_id == null"> <!--組裝途程-->
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
          <span style="margin-left: 25px;">
            {{ item.must_receive_qty }}
          </span>
        </template>
        <!--
        <span style="margin-left: 15px;">
          {{ item.must_receive_qty }}
        </span>
        -->
      </div>
    </template>

    <!-- 自訂 '領取數量' 輸入欄位 -->
  <!--ready modify 2025-09-15
    <template v-slot:item.receive_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
          v-model="item.receive_qty"
          dense
          hide-details
          :id="`receiveQtyID-${item.assemble_id}`"
          @keydown="handleKeyDown"
          @update:modelValue="checkReceiveQty(item)"
          @update:focused="(focused) => checkTextEditField(focused, item)"
          @keyup.enter="updateItem2(item)"
          :disabled="isButtonDisabled(item)"
        />
        <span
          v-show="item.tooltipVisible"
          style="position: absolute; left: 60px; top: 0; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 700;"
        >
          {{ receive_qty_alarm }}
        </span>
      </div>
    </template>
  -->

    <!-- 自訂 '說明' 欄位的資料欄位 -->
  <!--
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: '微軟正黑體', sans-serif;">{{ item.comment }}</div>
      </div>
    </template>
  -->

    <!-- 自訂 gif 按鍵欄位 -->
    <template v-slot:item.gif="{ item, index }">
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
            v-if="isTableVisible && boms.length > 0 && !isGifDisabled(item)"
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
                  v-for="(bom_item, index) in filteredBoms"
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
                    共 {{ filteredBoms.length }} 項
                  </td>
                </tr>
              </tfoot>
            </v-table>
          </div>
        </div>
      </v-hover>
    </template>

    <!-- 自訂 '開始' 按鍵欄位 -->
    <!--
    <template v-slot:item.action="{ item }">
      <TimerDisplay
        :fontSize="18"
        :autoStart="false"
        :show="true"

        :ref="setTimerEl(item.raw)"
        :isPaused="getT(item.raw).isPaused"
        @update:isPaused="val => (getT(item.raw).isPaused = val)"
        @update:time="getT(item.raw).onTick"

        class="me-2"
        style="min-width:88px; display:inline-block;"
      />
        <v-badge
          :model-value="hasAnyoneStarted(item)"
          dot
          color="green"
          offset-x="6"
          offset-y="6"
          class="me-1"
        >
          <template #default>
            <v-btn
              size="small"
              variant="tonal"
              style="font-size: 14px; font-weight: 700; font-family: '微軟正黑體', sans-serif;"
              :disabled="isButtonDisabled(item)"
              @click="onStart(item.raw)"
              color="indigo-darken-4"
            >
              開 始
              <v-icon color="indigo-darken-4" end>mdi-open-in-new</v-icon>
            </v-btn>
          </template>
        </v-badge>
    </template>
    -->

    <!-- 自訂 '開始' 按鍵欄位 -->
    <template #item.action="{ item }">
      <!-- 開始鍵左側顯示「自己」的計時值 -->
      <TimerDisplay
        :fontSize="18"
        :autoStart="false"
        :show="true"

        :ref="setTimerEl(item.raw)"
        :isPaused="isPausedOf(item.raw)"
        @update:isPaused="val => setPausedOf(item.raw, val)"
        @update:time="payload => onTickOf(item.raw, payload)"

        class="me-2"
        style="min-width:88px; display:inline-block;"
      />

      <!-- 綠點：這筆「有人」在開工（不限本人） -->
      <v-badge
        :model-value="hasAnyoneStarted(item.raw)"
        dot
        color="green"
        offset-x="6"
        offset-y="6"
        class="me-1"
      >

          <v-btn
            size="small"
            variant="tonal"
            style="font-size: 14px; font-weight: 700; font-family: '微軟正黑體', sans-serif;"
            :disabled="isButtonDisabled(item)"
            @click="onStart(item)"
            color="indigo-darken-4"
          >
            開 始
            <v-icon color="indigo-darken-4" end>mdi-open-in-new</v-icon>
          </v-btn>

      </v-badge>
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, nextTick, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount } from 'vue';

import TimerDisplay from "./TimerDisplay.vue";
import { useProcessTimer } from "../mixins/useProcessTimer.js";

import eventBus from '../mixins/enentBus.js';

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';

import { useRoute } from 'vue-router';

const search = ref('');

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { materials_and_assembles, boms, socket_server_ip }  from '../mixins/crud.js';
import { begin_count, end_count }  from '../mixins/crud.js';
import { apiOperation, setupGetBomsWatcher }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listMaterialsAndAssembles = apiOperation('get', '/listMaterialsAndAssembles');
const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');
const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

const updateAssembleMustReceiveQtyByMaterialID = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialID');
const copyAssemble = apiOperation('post', '/copyAssemble');
const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
//const createProcess = apiOperation('post', '/createProcess');
const getBoms = apiOperation('post', '/getBoms');
const updateAssembleAlarmMessage = apiOperation('post', '/updateAssembleAlarmMessage');
const getActiveCountMap = apiOperation('post', '/getActiveCountMap');

//=== component name ==
defineComponent({ name: 'PickReportForAssembleBegin' });

//=== mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
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

//const showText = ref(true) // 控制閃爍
//let blinkInterval = null

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
const str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '檢驗作業中', 'aa/bb/cc', '雷射作業中', 'aa/bb/00',]

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num', width:160 },
  { title: '物料編號', sortable: false, key: 'material_num', width:180},
  { title: '需求數量', sortable: false, key: 'req_qty', width:80 },
  { title: '備料數量', sortable: false, key: 'delivery_qty', width:80 },
  { title: '應領取數量', sortable: false, key: 'must_receive_qty', width:100 },  // 2025-06-13 add, 改順序
  //{ title: '領取數量', sortable: false, key: 'receive_qty' },
  //{ title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '交期', align: 'start', sortable: false, key: 'delivery_date', width:110 },
  { title: '', sortable: false, key: 'gif' },
  { title: '', sortable: false, key: 'action' },
];
// 初始化Socket連接
const app_user_id = 'user_chumpower';
const clientAppName = 'PickReportForAssembleBegin';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user_id, clientAppName);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const receive_qty_alarm = ref('');

//const from_agv_input_order_num = ref('');
//const isBlinking = ref(false);          // 控制按鍵閃爍
//const order_num_on_agv_blink=ref('');

//const inputStr = ref('');
const outputStatus = ref({
  step1: null,
  step2: null
});

const currentUser = ref({});
const componentKey = ref(0) // key 值用於強制重新渲染

const currentBoms = ref([]);

//const currentStartTime = ref(null);  // 記錄開始時間

//const agv1StartTime = ref(null);
//const agv1EndTime = ref(null);
//const agv2StartTime = ref(null);
//const agv2EndTime = ref(null);

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

let pollId = null;                                  // 每 10 秒輪詢
const refreshPollIdTimerMs = ref(10 * 1000);        // 10秒

const timerMap = new Map();

//=== watch ===
//watch(currentUser, (newUser) => {
//  if (newUser.perm < 1) {
//    permDialog.value = true;
//  }
//});
setupGetBomsWatcher();

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})
/*
// 監控 station2_trans_ready
watch(station2_trans_ready, (newVal) => {
  if (newVal) {
    // 開始閃爍
    blinkInterval = setInterval(() => {
      showText.value = !showText.value
    }, 500)
  } else {
    // 停止閃爍
    clearInterval(blinkInterval)
    blinkInterval = null
    showText.value = true
  }
})
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
  right: '190px',  // 固定左邊距離

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
  height: `${boms.length * 15}px`, // 根據資料筆數動態調整高度
  overflowY: 'hidden', // 禁止垂直滾動條
  overflowX: 'hidden', // 禁止水平滾動條
}));

const filteredBoms = computed(() =>
  boms.value.filter(item => item?.receive)
);

const userId = computed(() => currentUser.value?.empID ?? '')

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
  //history.pushState(null, null, document.URL)
  window.history.pushState(null, null, document.URL)
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
  console.log("currentUser:", currentUser.value, currentUser.value.perm, currentUser.value.empID);

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

      initialize();
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
});

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

onBeforeUnmount(() => {
  if (pollId)
    clearInterval(pollId);
});

//=== method ===
// 粒度選擇：如果後端已把 Process.assemble_id 落實，改成 'assemble' 更精準
const KEY = 'material' // 'material' 或 'assemble'

const getT = (row) => useRowTimer(row, userId.value)
const setTimerEl = (row) => (el) => { getT(row).timerRef.value = el }

// 下面這三個轉接器, 可避免在模板裡出現「函式呼叫＋屬性賦值」，VS Code 會比較乾淨

// 取得／設定 isPaused（避免在模板裡對函式呼叫結果賦值）
const isPausedOf = (row) => getT(row).isPaused
const setPausedOf = (row, v) => { getT(row).isPaused = v }
// 轉接 onTick（避免直接把函式呼叫結果當 handler）
const onTickOf = (row, payload) => { getT(row).onTick(payload) }

// ====== process_type 推導與 id 取得 ======
// 依 row.process_step_code → process_type
function processTypeOf(row) {
  const step = Number(row?.process_step_code ?? 0)
  if (step === 3) return 21  // 組裝
  if (step === 2) return 22  // 檢驗
  if (step === 1) return 23  // 雷射（依你的實際對照）
  return 21                  // 預設給 21，避免落空
}

// 以 material 為粒度，idKey 取 material_id（列表裡是 id=material.id）
// 若後端已支援 assemble 粒度，改成 row.assemble_id 並把 key 換成 'assemble'
function idOf(row) {
  return KEY === 'assemble' ? (row?.assemble_id ?? null) : (row?.id ?? row?.material_id ?? null)
}

// 依 process_type 分組 → 並行打 API → 合併回 rows
async function refreshActiveCounts() {
  const rows = materials_and_assembles?.value || []
  if (!rows.length) return

  // 1) 按 process_type 分組蒐集 ids
  const groups = {} // e.g. { "21": Set([...]), "22": Set([...]) }
  for (const row of rows) {
    const pt = String(processTypeOf(row))
    const id = idOf(row)
    if (id == null) continue
    (groups[pt] ||= new Set()).add(id)
  }

  // 2) 準備 payload（新格式：groups）；你的後端也相容舊格式
  const payload = {
    key: KEY,
    groups: Object.fromEntries(Object.entries(groups).map(([pt, set]) => [pt, Array.from(set)])),
  }
  print("groups:", Object.fromEntries(Object.entries(groups).map(([pt, set]) => [pt, Array.from(set)])))
  try {
    await getActiveCountMap(payload);
    //console.log("data:", data);

    if (!data?.status) {
      console.error('getActiveCountMap api', data)
      return
    }
  } catch (e) {
    console.error('getActiveCountMap error', e)
    return
  }

  // 4) 回填 active_user_count
  const countsByType = data.counts || {} // { "21": { "id": cnt }, "22": {...} }
  for (const row of rows) {
    const pt = String(processTypeOf(row))
    const id = String(idOf(row))
    const map = countsByType[pt] || {}
    row.active_user_count = Number(map[id] || 0)
  }
}

async function restoreMyTimers() {
  const uid = userId.value
  if (!uid) return
  for (const row of materials_and_assembles.value || []) {
    const t = getT(row)
    try {
      await t.startProcess(row.material_id ?? row.id, processTypeOf(row), uid, row.assemble_id)
      // 不 toggle，避免誤開暫停的工單
    } catch(e) {
      console.debug('restore timer skip', row?.id, e);
    }
  }
}

// 讓每個 row 取到自己的 timer（沒有就建一個）
function useRowTimer(row, currentUserId) {
  //const key = `${row.id}:${currentUserId}`
  const rowKey = row?.id ?? row?.assemble_id ?? row?.material_id
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

  if (!timerMap.has(key)) {
    const timerRef = ref(null)
    const t = useProcessTimer(() => timerRef.value)
    timerMap.set(key, { ...t, timerRef })
  }
  return timerMap.get(key)
}

// 這筆是否有人在開工（顯示綠點）
function hasAnyoneStarted(row) {
  return Number(row?.active_user_count || 0) > 0
}

function reachTarget(row) {
  return Number(row.total_ask_qty_end || 0) >= Number(row.must_receive_end_qty || 0)
}

async function onStart(row) {
  console.log("onStart(), row", row);

  const t = getT(row)
  //const t = useRowTimer(row, currentUser.value.empID)

  // 同一人不能對自己已開工的紀錄重複開始
  if (t.processId?.value) {
    showSnackbar('領料進行中...', 'orange-darken-2')
    return
  }

  // 組裝站請用對應的 process_type（例如 21=組裝）
  let temp_process_type=0
  if (row.process_step_code == 3 )
    temp_process_type=21
  if (row.process_step_code == 2 )
    temp_process_type=22
  if (row.process_step_code == 1 )
    temp_process_type=23
  console.log("row.id, temp_process_type, userId.value, row.assemble_id:",row.id, temp_process_type, userId.value, row.assemble_id)

  // 1) 先 start（後端可能只建立/取回流程，仍為暫停狀態）
  await t.startProcess(row.id, temp_process_type, userId.value, row.assemble_id)

  // 2) 立刻做一次 “恢復”（unpause, 以觸發後端寫入 begin_time
  //    不改 hook、不改後端；直接用既有的 hook 方法
  if (t.isPaused) {
    await t.toggleTimer()   // paused -> active（後端寫 begin_time）
  }

  // 3) 樂觀把「有人在開工」數 +1（等下一輪 refresh 再校正）
  row.active_user_count = Number(row.active_user_count || 0) + 1

  await updateItem(row);

  await refreshActiveCounts();
}

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

  // 綠點先回來
  await refreshActiveCounts();

  // 還原計時器（依後端真實狀態）
  await restoreMyTimers();

  /*
  const ids = materials_and_assembles.value.map(r => r.id);
  if (!ids.length)
    return;

  // 組裝站請用對應的 process_type（例如 21=組裝）
  let temp_process_type=0
  if (row.process_step_code == 3 )
    temp_process_type=21
  if (row.process_step_code == 2 )
    temp_process_type=22
  if (row.process_step_code == 1 )
    temp_process_type=23
  console.log("row.id, temp_process_type, userId.value, row.assemble_id:",row.id, temp_process_type, userId.value, row.assemble_id)

  let payload = {
    ids: ids,
    key: 'material',
    process_type: 21,
  };

  let res = await getActiveCountMap(payload);

  console.log("res:", res);

  if (res?.success) {
    const counts = res.counts || {}
    // 合併回 rows（沒有就當 0）
    rows.value.forEach(r => {
      const k = String(r.material_id)     // 若用 assemble_id 就換成 String(r.id) 或 r.assemble_id
      r.active_user_count = Number(counts[k] || 0);
    })
  }
  */
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    await listMaterialsAndAssembles();

    // 為materials_and_assembles每個物件增加 pickBegin 屬性，初始為空陣列 []
    materials_and_assembles.value.forEach(item => {
      item.pickBegin = [];
    });

    // 綠點先回來
    await refreshActiveCounts();

    // 還原計時器（依後端真實狀態）
    await restoreMyTimers();

    pollId = setInterval(refreshActiveCounts, refreshPollIdTimerMs.value);
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
  //history.pushState(history.state, '', document.URL);
  window.history.pushState(history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const isButtonDisabled = (item) => {
  console.log("item.whichStation:",item.whichStation, item.whichStation != 2);
  console.log("item.input_disable:",item.input_disable);
  console.log("!item.process_step_enable:",!item.process_step_enable);
  console.log("OR return value:",(item.whichStation != 2 || item.input_disable) || !item.process_step_enable);
  return (item.whichStation != 2 || item.input_disable) || !item.process_step_enable || item.isLackMaterial ==0;
  //return (item.whichStation != 2 || item.input_disable) || item.process_step_enable==0;
};

const isGifDisabled = (item) => {
  return item.whichStation != 2 || item.input_disable || !item.process_step_enable;
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
    let temp_str = '(' + abnormalDialog_delivery_qty.value + abnormalDialog_new_must_receive_qty.value + ')'
    abnormalDialog_message.value = '備料區來料數量不對! '+ temp_str;
    console.log("temp_str:", temp_str);
    let payload = {}

    try {
      //payload = {
      //  assemble_id: item.assemble_id,
      //  cause_message: ['備料區來料數量不對'],
      //  cause_user: currentUser.value.empID,
      //};
      //await updateAssembleAlarmMessage(payload);

      payload = {
        assemble_id: abnormalDialog_record.value.assemble_id,
        record_name: 'Incoming1_Abnormal',
        record_data: abnormalDialog_message.value,
      };
      await updateAssemble(payload);
      abnormalDialog_record.value.Incoming1_Abnormal=false;

      // targetIndex為目前table data record 的 index
      const targetIndex = materials_and_assembles.value.findIndex(
        (kk) => kk.id === item.id
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

const updateItem = async (item) => {
  console.log("PickReportForAssembleBegin, updateItem(),", item);

  /* ready modify 2025-09-15
  //item.receive_qty = item.receive_qty || 0;

  // 檢查是否輸入了空白或 0
  if (!item.receive_qty || Number(item.receive_qty) === 0) {
    console.log("item.receive_qty:", item.receive_qty)
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
  let payload = {};

  let startTime = new Date();                                                         // 記錄當前結束時間
  let formattedStartTime = formatDateTime(startTime); //完工生產報工開始時間
  console.log("formattedStartTime:", formattedStartTime)
  //console.log("item.pickBegin.length ==1 && Number(item.total_receive_qty)!=0:", item.pickBegin.length, Number(item.total_receive_qty_num));
  console.log("startTime step 1...")
  //2025-02-24 mark if condition
  // 確認是第1次領料
  //if (item.pickBegin.length ==1 && Number(item.total_receive_qty_num)!=0) {
  console.log("startTime step 2...")
  // 記錄當前領料生產開始時間
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'currentStartTime',
    record_data: formatDateTime(new Date()),
  };
  await updateAssemble(payload);
  //}
  //
  // 2.記錄當前途程領取數量
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'ask_qty',                 //領取數量
    record_data: Number(item.receive_qty),
  };
  await updateAssemble(payload);

  // 2-a.紀錄該筆的完工應領取數量
  payload = {
    material_id: item.id,
    record_name: 'must_receive_end_qty',
    record_data: Number(item.receive_qty),
  };
  await updateAssembleMustReceiveQtyByMaterialID(payload);

  //// 2-b.紀錄該筆的應領取數量, 2025-06-18 add, 改順序
  //payload = {
  //  material_id: item.id,
  //  record_name: 'must_receive_qty',
  //  record_data: Number(item.must_receive_end_qty) - Number(item.receive_qty),
  //};
  //await updateAssembleMustReceiveQtyByMaterialID(payload);

  // 3.暫存每次領取數量
  //item.pickBegin.push(item.receive_qty);

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

  // 取得組裝區目前途程的show2_ok訊息類型(開始)
  checkInputStr(item.assemble_work);
  console.log("outputStatus:", outputStatus.value, typeof(outputStatus.value.step1), typeof(outputStatus.value.step1))

  // 6.按開始鍵後, 記錄當前途程開始狀態顯示訊息
  payload = {
    order_num: item.order_num,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step1
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: item.assemble_id,
    record_name: 'show2_ok',
    record_data: true,
  };
  await updateAssemble(payload);

  item.assemble_process = str2[outputStatus.value.step1]
  item.assemble_process_num = outputStatus.value.step1

  // 7.按開始鍵後, 記錄當前途程狀態訊息show3_ok
  payload = {
    order_num: item.order_num,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step1
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: item.assemble_id,
    record_name: 'show3_ok',
    record_data: true,
  };
  await updateAssemble(payload);

  let temp = Number(item.req_qty)
  // 確認 已領取數量總數=需求數量(訂單數量)
  console.log("total == temp ?",total, temp)
  //if (total == temp) {    // 2025-06-16 mark, 改順序

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

  /* ready modify 2025-09-15
  if (Number(item.must_receive_qty) != Number(item.receive_qty)) {
    console.log("item.must_receive_qty != item.receive_qty", item.must_receive_qty, item.receive_qty)

    let temp_qty = item.must_receive_qty - item.receive_qty;
    console.log("temp_qty:", temp_qty)

    //2025-08-04
    payload = {
      material_id: item.id,
      record_name: 'must_receive_qty',
      record_data: Number(item.receive_qty),
    };
    await updateAssembleMustReceiveQtyByMaterialID(payload);
    //
    payload = {
      copy_id: item.assemble_id,
      must_receive_qty: temp_qty,
    }
    await copyAssemble(payload);
  }
  */

  //待待
  //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};

const checkInputStr = (inputStr) => {
  console.log("checkInputStr(),", inputStr)
  //參考後端python, str2[]的指標
  if (inputStr.includes('109')) {             //組裝
    outputStatus.value = { step1: 4, step2: 5, };
  } else if (inputStr.includes('106')) {      //雷射
    // 2025-06-12, 改順序
    //outputStatus.value = { step1: 6, step2: 7 };
    outputStatus.value = { step1: 8, step2: 9 };
  } else if (inputStr.includes('110')) {      //檢驗
    // 2025-06-12, 改順序
    //outputStatus.value = { step1: 8, step2: 9 };
    outputStatus.value = { step1: 6, step2: 7 };
  } else {
    outputStatus.value = { step1: null, step2: null };  // 無匹配時清空結果
  }
};
/*
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
/*
const formatTime = (time) => {                            // 格式化時間為 hh:mm:ss
  const hours = String(time.getHours()).padStart(2, '0');
  const minutes = String(time.getMinutes()).padStart(2, '0');
  const seconds = String(time.getSeconds()).padStart(2, '0');

  return `${hours}:${minutes}:${seconds}`;
};
*/
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

  //boms.value = [];
  let payload = {
    //order_num: item.order_num,
    id: item.id,
  };
  await getBoms(payload);
  console.log('Current hovered item index:', hoveredItemIndex.value);
  //reactiveBoms = reactive({ data: [...boms.value] });
  //reactiveBoms = ref([...boms.value]);
  console.log("bom[]:", boms.value)
  //console.log("reactiveBoms:", reactiveBoms)
  //currentBoms.value = [...boms.value];
  //console.log("currentBoms[]:", currentBoms.value)
  //console.log("currentBoms.rec:", currentBoms.value[0].receive)
  //console.log("Raw currentBoms:", toRaw(currentBoms.value));
  //await nextTick();
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
</style>