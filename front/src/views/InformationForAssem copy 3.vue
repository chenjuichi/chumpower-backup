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
    <!--
      <v-btn
        @click="toggleHistory"
        :active="history"
        color="#c39898"
        variant="outlined"
        style="position:relative; left:20px;"
      >
        <v-icon left color="#664343">mdi-history</v-icon>
        歷史紀錄
      </v-btn>
    -->
    </v-col>
    <v-col cols="4" class="d-flex justify-start align-center pb-0">
    <!--
      <v-text-field
        v-model="search"
        label="搜尋"
        prepend-inner-icon="mdi-magnify"
        variant="outlined"
        hide-details
        single-line

        density="compact"
      />
    -->
    </v-col>
  </v-row>

  <v-row
    class="mt-0 mb-0 row-hidden"
    style="min-height:48px; height:48px; flex-wrap:nowrap; position:relative; top:25px; left:5px;"
  >
    <!--日期範圍-->
    <v-col cols="3" class="d-flex justify-end align-center pt-0 pb-0" style="position: relative; left:100px;">
      <Transition name="slide">
        <div v-if="showFields" style="min-width:290px;">
          <v-menu
            v-model="menuOpen"
            :close-on-content-click="false"
            location="bottom start"
            origin="top start"
            :offset="[0, 8]"
            :width="480"
            :min-width="480"
            transition="fade-transition"
            :open-on-focus="false"
            :open-on-hover="false"
          >
            <template #activator="{ props }">
              <v-text-field
                v-bind="props"
                label="交期範圍"
                v-model="formattedDateRange"
                readonly
                variant="underlined"
                density="compact"
                style="margin-top:20px;"
                placeholder="yyyy-mm-dd ~ yyyy-mm-dd"
                prepend-icon="mdi-calendar-check"
                class="dateicon"
                clearable
                @click="menuOpen = true"
                @click:clear="clearDates"
              />
            </template>
              <div class="dp-stretch">
              <VueDatePicker
                :key="menuKey"
                :start-date="today"
                v-model="dpRange2"
                :enable-time-picker="false"
                range
                :inline="true"

                :auto-apply="true"
                locale="zh-TW"
                week-num-name=""

                :day-names="['星期一','星期二','星期三','星期四','星期五','星期六','星期日']"
              />
              </div>
          </v-menu>
        </div>
      </Transition>
    </v-col>

    <!-- 工單範圍（萬用字元搜尋 + 多選）-->
    <v-col cols="3" class="d-flex justify-end align-center pt-0 pb-0">
      <Transition name="slide">
        <div v-if="showFields" style="min-width:260px; width:260px; position:relative; left:50px;">
          <!-- 1) 萬用字元搜尋 -->
          <v-text-field
            label="工單搜尋"
            variant="outlined"
            v-model="orderWildcard"
            density="compact"
            class="papericon"
            prepend-icon="mdi-magnify"
            placeholder="例：1212*、*6134、1212????6134、??34"
            clearable
            style="margin-top:20px; min-width:290px; width:290px; position:relative; top:5px;"
          />

          <!-- 2) 下拉多選（顯示符合搜尋的工單） -->
          <v-select
            v-model="selectedOrderNums"
            :items="filteredOrderItems"
            item-title="title"
            item-value="value"
            label="符合的工單（可多選）"
            multiple
            chips
            closable-chips
            variant="outlined"
            density="comfortable"
            prepend-icon="mdi-archive-check-outline"
            :menu-props="{ maxHeight: 360 }"
            style="margin-top:15px; min-width:290px; width:290px;"
            class="select_papericon"
          >
            <!-- Select All -->
            <template v-slot:prepend-item>
              <v-list-item title="Select All（目前搜尋結果）" @click="toggleSelectAllOrders">
                <template v-slot:prepend>
                  <v-checkbox-btn
                    :indeterminate="likesSomeFilteredOrders && !likesAllFilteredOrders"
                    :model-value="likesAllFilteredOrders"
                  />
                </template>
              </v-list-item>
              <v-divider class="mt-2" />
            </template>

            <!-- footer 訊息 -->
            <template v-slot:append-item>
              <v-divider class="mb-2" />
              <v-list-item
                :title="orderSelectTitle"
                :subtitle="orderSelectSubtitle"
                disabled
              />
            </template>
          </v-select>
        </div>
      </Transition>
    </v-col>

    <!-- 未完成工單顯示switch-->
    <v-col cols="2" class="d-flex justify-start align-center pt-0 pb-0">
      <Transition name="slide">
        <div v-if="showFields" style="position:relative; left:70px;" class="checkbox-container">
          <label class="switch">
              <input
                type="checkbox"
                style="position:relative; left:20px;" v-model="switchValue"
              />
              <span class="slider">
                <span class="txt on">ON</span>
                <span class="txt off">OFF</span>
              </span>
          </label>

          <span class="switch-title">
            {{ switchValue_string }}
          </span>
        </div>
      </Transition>
    </v-col>

    <!--搜尋按鍵-->
    <v-col cols="4" class="d-flex justify-center align-center pt-0 pb-0">
      <!-- 翻轉效果 -->
      <div class="flip_btn">
        <v-btn
          color="white"
          style="min-width: 90px; max-height: 34px; border-radius: 6px; border-width:1.5px; border-color:#64B5F6;"
          class="side default-side primary thin mt-1 mx-auto"
          :disable="isInformationEmpty"
          @mouseenter="showFields = true"
        >
          <v-icon left color="green" style="font-weight:700;">mdi-magnify</v-icon>
          <span style="color:black; font-weight:600;">搜尋</span>
        </v-btn>
        <div class="side hover-side">
          <!-- 取消按鍵 -->
          <v-btn
            style="position:relative; right:3px; top:7px; width:80px; border-radius:6px; border-width:1.5px; border-color:#64B5F6;"
            class="mt-n1 mr-15 mx-auto"
            @click="showFields = false"
          >
            <v-icon left color="#ff0000">mdi-window-close</v-icon>
            <span style="color:black; font-weight:600;">取消</span>
          </v-btn>

          <!-- Excel按鍵 -->
          <v-btn
            style="position:relative; left:3px; top:7px; width:80px; border-radius:6px; border-width:1.5px; border-color:#64B5F6;"
            class="mt-n1 mr-15 mx-auto"
            @click="exportToExcelFun">
            <v-icon left color="green">mdi-microsoft-excel</v-icon>
            <span style="color:black; font-weight:600;">Excel</span>
          </v-btn>
        </div>
      </div>

      <!-- 在線員工按鍵 -->
      <v-btn
        class="ml-4 mt-1"
        color="indigo-darken-4"
        variant="outlined"
        style="
        position:relative;
        left:50px;
        top:5px;
        min-width:110px; max-height:34px; border-radius:6px;"
        prepend-icon="mdi-account-details-outline"
        @click="onClickOnlineUsers"
      >
        在線員工
      </v-btn>
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

    v-model:items-per-page="pagination.itemsPerPage"
    v-model:page="pagination.page"
  >
    <template v-slot:top>
      <v-card style="min-height:100px; overflow:visible; position:relative; top: -20px;">
        <v-card-title class="d-flex align-center pe-2 sticky-card-title" :max-width="dialogWidth" style="width: 100%; ">
          <v-row style="margin-left:3vw;">
            <v-col cols="9">
              <div style="display: flex; justify-content: center; gap: 45px; font-size: 20px; color: blue">
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span style="font-size: 16px;">~ 至 {{ twoWeeksAgoDate }}</span>
                  <!--<span style="font-size: 16px;">{{ todayDate }} 至 {{ twoWeeksAgoDate }}</span>-->
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <span>工單數</span>
                  <span style="position:relative; top:10px; font-size:30px;">{{ order_count }}</span>
                </div>
                <div style="display: flex; flex-direction: column; align-items: center;">
                  <!--<span>備料送出</span>-->
                  <span>備料準備中</span>
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
                  <span>組裝進行中</span>
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
                  <span>等待入庫中</span>
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
            <v-dialog v-model="process_dialog" min-width="1260px">
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
                        <th class="text-left" style="width:320px; padding-left:0px; padding-right:8px;">備料/組裝</th>
                        <th class="text-left" style="width:110px; padding-left:0px; padding-right:0px;">開始時間</th>
                        <th class="text-left" style="width:110px; padding-left:0px; padding-right:0px;">結束時間</th>
                        <th class="text-left" style="padding-left:0px; padding-right:0px;">數量</th>
                        <th class="text-left" style="padding-left:0px; padding-right:0px;">
                          實際耗時
                        </th>
                        <th class="text-left" style="padding-left:0px; padding-right:0px;">
                          <div style="line-height: 1.2; text-align: left;">
                          實際工時<br />(分/PCS)
                          </div>
                        </th>
                        <th class="text-left" style="padding-left:0px; padding-right:0px;">
                          <div style="line-height: 1.2; text-align: left;">
                          單件標工<br />(分/PCS)
                          </div>
                        </th>
                        <th class="text-left" style="padding-left:0px; padding-right:0px;">人員註記</th>
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
                        <td style="width:300px; padding-left:0px; padding-right:8px; font-size:14px;">
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
                        <td style="font-size:12px; font-weight: 600;">{{ process_item.user_comment }}</td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-card-text>
              </v-card>
            </v-dialog>

            <!-- 在線員工 dialog -->
            <v-dialog v-model="onlineDialog" max-width="800px">
              <v-card>
                <v-card-title class="d-flex justify-space-between align-center">
                  <span class="text-h6">在線員工</span>
                  <v-btn icon="mdi-close" variant="text" @click="onlineDialog = false" />
                </v-card-title>

                <v-card-text>
                  <v-data-table
                    :headers="onlineHeaders"
                    :items="filteredOnlineUsers"
                    density="compact"
                    class="elevation-1"
                  >
                    <!-- Dept 欄位 header + combobox -->
                    <template v-slot:header.dep_name = "{ column }">
                      <div class="d-flex align-center">
                        <span class="mr-2">{{ column.title }}</span>
                        <v-combobox
                          v-model="selectedDeptForOnline"
                          :items="deptOptionsForOnline"
                          density="compact"
                          hide-details
                          variant="underlined"
                          style="max-width: 150px;"
                        />
                      </div>
                    </template>

                    <!-- workHours 欄位 header + combobox -->
                    <template #header.workHours="{ column }">
                      <div class="d-flex align-center justify-end">
                        <span class="mr-2">{{ column.title }}</span>
                        <v-combobox
                          v-model="selectedWorkHours"
                          :items="workHourOptions"
                          item-title="label"
                          item-value="value"
                          density="compact"
                          hide-details
                          variant="underlined"
                          style="max-width: 180px;"
                        />
                      </div>
                    </template>

                    <!-- onLine 欄位，依值改背景色 -->
                    <template v-slot:item.online="{ item }">
                      <div class="text-center pa-1" :style="getOnlineCellStyle(item.online)">
                        <!--{{ item.online }}-->
                        {{ getOnlineText(item.online) }}
                      </div>
                    </template>
                  </v-data-table>
                </v-card-text>

                <v-card-actions class="justify-end">
                  <v-btn color="primary" @click="onlineDialog = false">關閉</v-btn>
                </v-card-actions>
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
        margin: 0;
        padding: 0;
        padding-left: 18px;
        display: flex;
        cursor: pointer;
        position: relative;
        left: 8px;"
      >
        <span>{{ column.title }}</span>
      </div>
      <div
        style="color: #a6a6a6; font-size: 10px; font-weight: 600; text-align: center; line-height: 1; margin-left: -10px;"
      >
        組裝/檢驗/雷射
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
      <div style="font-weight:600; text-align:left;">{{ item.show3_ok }}</div>
    </template>

    <!-- 自訂 '訂單數量' 欄位 -->
    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.date }}</div>
      </div>
    </template>

    <!-- 自訂 '說明' 欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>-->
      </div>
    </template>

    <!-- 定義 '詳情' 按鍵外觀 -->
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
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount ,nextTick } from 'vue';

import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
dayjs.extend(isSameOrBefore);             //啟用 plugin

import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

import { useRoute } from 'vue-router';

import { myMixin } from '../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { informations, boms, fileCount }  from '../mixins/crud.js';
import { order_count, prepare_count, assemble_count, warehouse_count, processes }  from '../mixins/crud.js';

import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';
import { apiOperationB } from '../mixins/crudB.js';

// 使用 apiOperation 函式來建立 API 請求
const listInformations = apiOperation('get', '/listInformations');
const listWorkingOrderStatus = apiOperation('get', '/listWorkingOrderStatus');

//const getBoms = apiOperation('post', '/getBoms');
//const updateBoms = apiOperation('post', '/updateBoms');
//const updateMaterial = apiOperation('post', '/updateMaterial');
//const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');

const getProcessesByOrderNum = apiOperation('post', '/getProcessesByOrderNum');
const exportToExcelForAssembleInformation = apiOperation('post', '/exportToExcelForAssembleInformation');
const getUsersDepsProcesses = apiOperation('post', '/getUsersDepsProcesses');

const downloadFile = apiOperationB('post', '/downloadXlsxFile');

//=== component name ==
defineComponent({ name: 'InformationForAssem' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
let _qTimer = null;
let intervalId = null;                    // 5分, 倒數計時器
let intervalIdForProgressCircle = null;   // 5分, 倒數計時器

const route = useRoute();                 // Initialize router

const showFields = ref(false);            // 用來控制是否顯示額外的excel btn欄位
const menuOpen = ref(false)
const today = new Date()
const menuKey = ref(0)
const settingDefaultRange = ref(false)

const dpRange = ref(null)             // 外部值（清空用 null，不要 []）
const dpRange2 = ref([])
const dpInternal = ref(null)          // 內部值：選取當下就會更新
const formattedDateRange = ref('')    // 綁給 <v-text-field>

const fromDateStart = ref("");
const fromDateValStart = ref([]);

// == 工單範圍 v-select 用 begin ==
// 工單萬用字元搜尋 + 多選
const orderWildcard = ref('');          // * ? 搜尋字串
const selectedOrderNums = ref([]);      // v-select multiple 選到的工單
// == 工單範圍 v-select 用 end ==

const screenWidth = ref(window.innerWidth);

// 取得今日日期 (格式：YYYY/MM/DD)
//const todayDate = ref(new Date().toISOString().split("T")[0].replace(/-/g, "/"));

const formatDate = (date) => {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}/${m}/${d}`
}
const getTwoWeeksAgoFromString = (dateStr) => {
  const [y, m, d] = dateStr.split('/').map(Number)
  const base = new Date(y, m - 1, d)
  base.setDate(base.getDate() + 12)
  return formatDate(base)
}

const twoWeeksAgoDate = ref(getTwoWeeksAgoFromString(todayDate.value))

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num' },
  { title: '現況進度', sortable: false, key: 'show1_ok', width:150 },
  { title: '現況備註', sortable: false, key: 'show3_ok', width:170 },
  { title: '交期', sortable: false, key: 'delivery_date', width:110 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:90 },
  { title: '現況數量', sortable: false, key: 'delivery_qty', width:90 },
  { title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '', sortable: false, key: 'action' },
];

const onlineHeaders = [
  { title: '  ',  sortable: false, key: 'id', width: '2px' },
  { title: '部門',     key: 'dep_name' },
  { title: '員工姓名', key: 'emp_name' },
  { title: '工時合計', key: 'workHours', align: 'end' },
  { title: '在線資訊', key: 'online', align: 'end' },
];

// 工時篩選（0=當天工時，1=前一天，3=前三天總和，7=一星期總和）
const selectedWorkHours = ref(0)  // 預設值 select = 0 => 當天工時

const workHourOptions = ref([
  { label: '當天',       value: 0 },
  { label: '前一天',     value: 1 },
  { label: '前三天內', value: 3 },
  { label: '一星期內', value: 7 },
])

const onlineDialog = ref(false)     // 在線員工 dialog
const allOnlineUsers = ref([])      // 原始員工資料（等你從後端拿）

// 部門下拉選單 + 目前選取的部門
const selectedDeptForOnline = ref('全部')
const deptOptionsForOnline = ref(['全部'])

const search = ref('');

const history = ref(false);
const currentUser = ref({});
//const currentUser = ref(null);

const current_order_num = ref('');

const process_dialog = ref(false);

const pagination = reactive({
  itemsPerPage: 5,                    // 預設值, rows/per page
  page: 1,
});

const wakeLock = ref(null);           // 用於存儲 Wake Lock 物件
const isWakeLockActive = ref(false);  // 是否啟用螢幕鎖定

const selectedFile = ref(null); 						                // 儲存已選擇檔案的名稱
const downloadFilePath = ref('');
const selectedFileName = ref('');						                // 用於追蹤目前選取的檔案名稱

const switchValue = ref("OFF");
//const switchValue_string = ref("顯示訂單編號");
const switchValue_string = ref("只顯示未完成訂單編號");

//=== watch ===
setupGetBomsWatcher();

watch(switchValue, async (val)=> {
  console.log("目前switch:", val ? "ON" : "OFF")
  if (val)
    switchValue_string.value="只顯示未完成訂單編號"
  else
    //switchValue_string.value="顯示訂單編號"
    switchValue_string.value="只顯示未完成訂單編號"

  await listInformations({
    only_unfinished: val ? 1 : 0,

    // ✅ 分頁
    page: page.value,
    limit: limit.value,
    offset: offset.value,
  })
})

watch(menuOpen, (open) => {
  if (open) {
    // 每次開都回今天那個月
    menuKey.value++

    //如果希望「使用者已經選過日期就不要覆蓋」
    if (!dpRange2.value?.[0] || !dpRange2.value?.[1]) {
      // 每次開都預設今天~+7天
      setDefaultRange()
    }
  }
})

//watch([() => pagination.page, () => pagination.itemsPerPage], () => {
//  runQueryDebounced();
//})

// 畫面控制
watch(dpRange2, ([start, end]) => {
  if (settingDefaultRange.value) return   // ✅ 預設值時不關 menu

  if (start && end) {
    formattedDateRange.value = `${fmt(start)} ~ ${fmt(end)}`
    menuOpen.value = false                 // ✅ 使用者選完才關
  }
})

// 資料查詢, 日期 / 工單 / switch 變更就查
watch([dpRange2, selectedOrderNums, orderWildcard, switchValue], () => {
  if (settingDefaultRange.value) return   // ⭐ 防止初始化觸發
  pagination.page = 1;
  runQueryDebounced();
}, { deep: true })

//watch(() => informations.value || [], (newVal) => {
//    console.log("Updated informations...", newVal);
//  },
//  { deep: true }
//);

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

watch([dpInternal, dpRange], () => {
  const src = dpInternal.value ?? dpRange.value
  if (!src || !Array.isArray(src) || !src[0]) return
  const [start, end] = src
  formattedDateRange.value = end ? `${fmt(start)} ~ ${fmt(end)}` : fmt(start)
}, { deep: true })

//=== computed ===

/*
page：第幾頁（1-based）
limit：每頁幾筆
offset：跳過前面幾筆（0-based）
*/
const limit = computed(() => Number(pagination.itemsPerPage || 20))
const page  = computed(() => Number(pagination.page || 1))
const offset = computed(() => (page.value - 1) * limit.value)

const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)',
  width: 'min(100%, 1500px)', // 讓表格最多1200px，但不超過螢幕
  minWidth: '700px',           // 避免過小
  maxWidth: '100%',            // 不超過父容器
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

//const progress_value1 = computed(() => order_count.value);
const progress_value2 = computed(() => order_count.value !=0 ? (prepare_count.value / order_count.value)* 100 : 0 );
const progress_value3 = computed(() => order_count.value !=0 ? (assemble_count.value / order_count.value)* 100 : 0 );
const progress_value4 = computed(() => order_count.value !=0 ? (warehouse_count.value / order_count.value)* 100 : 0 );

const isInformationEmpty = computed(() => {
  return informations.value.length === 0;
});

// 過濾符合條件的資訊
const filteredInformations = computed(() => {
  const filtered = informations.value.filter(item => {
    const isWithinDateRange = checkDateInRange(item.delivery_date);
    const isWithinOrderRange = checkOrderInRange(item.order_num);
    return isWithinDateRange && isWithinOrderRange;
  });

  // 去重：同 order_num 只保留一筆（保留最後一筆）
  const map = new Map();
  for (const it of filtered) map.set(it.order_num, it);
  return Array.from(map.values());
});

//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  console.log("裝置像素比 (DPR):", window.devicePixelRatio);

  console.log("current routeName:", routeName.value);

/*
  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  //#
  let userRaw = sessionStorage.getItem('auth_user');
  if (!userRaw)
    userRaw = localStorage.getItem('loginedUser');

  try {
    const u = userRaw ? JSON.parse(userRaw) : null;
    // 只讀，避免被誤改
    currentUser.value = u ? Object.freeze({ ...u }) : null;
  } catch {
    currentUser.value = null;
  }
  console.log('currentUser:', currentUser.value);
  //#
*/

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

  if (currentUser.value?.empID) {
  //if (currentUser.value) {
    currentUser.value.setting_items_per_page = pagination.itemsPerPage;
    currentUser.value.setting_lastRoutingName = routeName.value;

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }

  console.log("currentUser:", currentUser.value);

  intervalId = setInterval(listInformationsFun, 5 * 60 * 1000);  // 每 5分鐘調用一次 API
  intervalIdForProgressCircle = setInterval(listWorkingOrderStatusFun, 5 * 60 * 1000);  // 每 5分鐘調用一次 API

  window.addEventListener('resize', updateScreenWidth);
  updateScreenWidth(); // 確保初始時執行一次

  document.addEventListener("visibilitychange", handleVisibilityChange);
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

// 根據部門過濾後，給 v-data-table 的 items
const filteredOnlineUsers = computed(() => {
  if (selectedDeptForOnline.value === '全部') {
    return allOnlineUsers.value
  }
  return allOnlineUsers.value.filter(
    (u) => u.dep_name === selectedDeptForOnline.value
  )
})

// onLine 欄位背景顏色：0=淡綠, 1=淡紅, 2=淡黃
const getOnlineCellStyle = (status) => {
  const v = Number(status)
  if (v === 0) {
    return { backgroundColor: '#d5f5e3' } // 淡綠
  }
  if (v === 1) {
    return { backgroundColor: '#f5b7b1' } // 淡紅
  }
  if (v === 2) {
    return { backgroundColor: '#fcf3cf' } // 淡黃
  }
  return {}
}

const onClickOnlineUsers = async () => {
  // 先開 dialog，避免資料還沒回來就看不到反應
  onlineDialog.value = true

  // 可以先用假資料測，排除 template / reactivity 問題
  const resp = await getUsersDepsProcesses({select: selectedWorkHours.value});
  allOnlineUsers.value = resp || [];

  // 再從 allOnlineUsers 裡面抓 dep_name 做選單
  const src = allOnlineUsers.value || [];
  const depts = Array.from(
    new Set(src.map(u => u.dep_name).filter(Boolean))
  );
  deptOptionsForOnline.value = ['全部', ...depts];
}

//=== method ===

const getOnlineText = (val) => {
  if (val === 0) return '請假'
  if (val === 1) return '在線'
  if (val === 2) return '離線'
  return ''
}

const runQuery = async () => {
  const payload = buildListInformationsPayload();
  await listInformations(payload);

  /*
  const payload = buildQueryPayload();
  const resp = await listInformationsFiltered(payload);

  // 依你 p_apiOperation 回傳格式調整：常見是 resp.data
  const data = resp?.data || resp;
  informations.value = data?.informations || [];
  */
};

const runQueryDebounced = () => {
  if (_qTimer) clearTimeout(_qTimer);
  _qTimer = setTimeout(runQuery, 200);
};

// ===

/*
// 日期比較工具（統一格式）
const toDateOnly = (v) => {
  if (!v) return null

  // 已是 Date
  if (v instanceof Date) {
    const d = new Date(v)
    d.setHours(0,0,0,0)
    return d.getTime()
  }

  // 字串 yyyy-mm-dd 或 yyyy-mm-dd hh:mm:ss
  if (typeof v === 'string') {
    const d = new Date(v.split(' ')[0])
    if (isNaN(d)) return null
    d.setHours(0,0,0,0)
    return d.getTime()
  }

  return null
}
*/

// 加天數
const addDays = (date, days)=>{
  const d = new Date(date)
  d.setDate(d.getDate()+days)
  return d
}

// 設定預設區間（今天~7天）
const setDefaultRange = ()=>{
  const start = new Date()
  const end   = addDays(start, 7)

  settingDefaultRange.value = true
  dpRange2.value = [start, end]

  //formattedDateRange.value =
  //  `${start.toISOString().slice(0,10)} ~ ${end.toISOString().slice(0,10)}`
  formattedDateRange.value = `${fmt(start)} ~ ${fmt(end)}`

  // 下一個 tick 再解除旗標，避免 watcher 立刻關 menu
  queueMicrotask(() => {
    settingDefaultRange.value = false
  })
}

const clearDates = () => {
  dpRange2.value = [null, null]
  formattedDateRange.value = ''
  menuKey.value++            // ✅ 重新掛載，避免卡在奇怪月份
}

//const isEmpty = (v) => v === "" || v === null || v === undefined;

// ✅ 空值顯示成 "(空白)"
//const displayBlank = (v) => (isEmpty(v) ? "(空白)" : String(v));

// ✅ 轉數字（給統計用）；空值視為 0
const toNum = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

// ✅ 摘要統計（只統計 >0 的值）
const totalScrap = computed(() =>
  (processes.value || []).reduce((sum, p) => sum + Math.max(0, toNum(p.abnormal_qty)), 0)
);

const totalStockin = computed(() =>
  (processes.value || []).reduce((sum, p) => sum + Math.max(0, toNum(p.completed_qty)), 0)
);

const totalRows = computed(() => (processes.value || []).length);

// ===

// == 工單範圍 v-select 用 begin ==

// 把萬用字元 pattern 轉成可用的比對函式
// 規則：
// - 若包含 * 或 ? ：用「整段匹配」(像檔案總管常見的 pattern)
// - 若不含萬用字元：用「包含」(substring)
const buildWildcardMatcher = (pattern) => {
  const p = (pattern ?? '').trim();
  if (!p) return () => true;

  const hasWildcard = /[*?]/.test(p);

  // escape regex special chars (除了 * ?)
  const escaped = p.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  const regexStr = hasWildcard
    ? '^' + escaped.replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
    : escaped; // 無萬用字元：用 contains

  const re = new RegExp(regexStr, 'i');
  return hasWildcard
    ? (s) => re.test(String(s ?? ''))
    : (s) => re.test(String(s ?? '')); // contains（因為沒加 ^$）
};

// 全部工單候選（去重排序）
const allOrderItems = computed(() => {
  const uniq = new Set(
    (informations.value || [])
      .map(x => x?.order_num)
      .filter(Boolean)
      .map(x => String(x))
  );
  return [...uniq]
    .sort()
    .map(o => ({ title: o, value: o }));
});

// 依萬用字元輸入過濾後的候選清單（顯示在 v-select）
const filteredOrderItems = computed(() => {
  const match = buildWildcardMatcher(orderWildcard.value);
  return allOrderItems.value.filter(it => match(it.value));
});

// 目前「搜尋結果」對應的 value 清單
const filteredOrderValues = computed(() => filteredOrderItems.value.map(x => x.value));

// Select All 狀態：針對「目前搜尋結果」集合
const likesAllFilteredOrders = computed(() => {
  const vals = filteredOrderValues.value;
  if (vals.length === 0) return false;
  return vals.every(v => selectedOrderNums.value.includes(v));
});

const likesSomeFilteredOrders = computed(() => {
  const vals = filteredOrderValues.value;
  return vals.some(v => selectedOrderNums.value.includes(v));
});

// Select All：只全選/全取消「目前搜尋結果」
const toggleSelectAllOrders = () => {
  const vals = filteredOrderValues.value;

  if (vals.length === 0) {
    selectedOrderNums.value = [];
    return;
  }

  if (likesAllFilteredOrders.value) {
    // 取消目前搜尋結果（但保留不在搜尋結果內、你先前可能選的）
    const keep = selectedOrderNums.value.filter(v => !vals.includes(v));
    selectedOrderNums.value = keep;
  } else {
    // 加入目前搜尋結果（去重）
    const merged = new Set([...(selectedOrderNums.value || []), ...vals]);
    selectedOrderNums.value = [...merged];
  }
};

const orderSelectTitle = computed(() => {
  if (likesAllFilteredOrders.value) return '已全選（目前搜尋結果）';
  if (likesSomeFilteredOrders.value) return '已選擇部分（目前搜尋結果）';
  return '尚未選擇';
});

const orderSelectSubtitle = computed(() => {
  const total = filteredOrderValues.value.length;
  const picked = selectedOrderNums.value.length;
  return `搜尋結果 ${total} 筆；已選 ${picked} 筆`;
});

// == 工單範圍 v-select 用 end ==

const fmt = (d) => {
  if (!d) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const isOrderInList = (orderNum) => {
  return order_num_list.value.includes(orderNum)
}

const initialize = async () => {
  try {
    console.log("initialize()...")

    switchValue.value = 0;
    await listInformations({
      only_unfinished: switchValue.value,

      // ✅ 分頁
      page: page.value,
      limit: limit.value,
      offset: offset.value,
    });
    await listWorkingOrderStatus();

    /*
    //allOnlineUsers.value = await getUsersDepsProcesses({select: selectedWorkHours.value});
    const resp = await getUsersDepsProcesses({select: selectedWorkHours.value});
    allOnlineUsers.value = resp || [];

    const depts = Array.from(
      new Set(src.map(u => u.dep_name).filter(Boolean))
    );
    deptOptionsForOnline.value = ['全部', ...depts];
    */
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

// == 工單範圍 v-select 用 begin ==

// 工單篩選規則：
// 1) 若 v-select 有多選 => 只顯示被選到的工單
// 2) 否則若有輸入萬用字元/文字 => 用 pattern 過濾
// 3) 否則不限制
const checkOrderInRange = (orderNum) => {
  const o = String(orderNum ?? '');

  // 1) 多選優先
  if (Array.isArray(selectedOrderNums.value) && selectedOrderNums.value.length > 0) {
    return selectedOrderNums.value.includes(o);
  }

  // 2) 萬用字元 / 文字搜尋
  const pat = (orderWildcard.value ?? '').trim();
  if (pat) {
    const match = buildWildcardMatcher(pat);
    return match(o);
  }

  return true;
};
// == 工單範圍 v-select 用 end ==

const exportToExcelFun = async () => {
  console.log('InformationForAssem.vue, exportToExcelFun()...');

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
    material_num: item.material_num ?? '',
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
  const payload = buildListInformationsPayload();
  await listInformations(payload);
};

// 共用 payload builder（含 switchValue）
const buildListInformationsPayload = () => ({
  only_unfinished: switchValue.value ? 1 : 0,

  // ✅ 分頁
  page: page.value,
  limit: limit.value,
  offset: offset.value,
});

const listWorkingOrderStatusFun = async () => {
  await listWorkingOrderStatus();
};

const customFilter = (value, search, item) => {
  if (!search) return true;
  search = search.toLowerCase();

  return Object.values(item).some(val =>
    String(val).toLowerCase().includes(search)
  );
};

//const toggleHistory = async () => {
//  history.value = !history.value;
//  await getInformationsByHistoryFun();
//};

//const getInformationsByHistoryFun = async () => {
//  let payload = {
//    history_flag: history.value,
//  };
//  await getInformationsByHistory(payload);
//}

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

  process_dialog.value = false;
};

const formatDate3 = (date) => {
  if (!date) return null;
  const localDate = new Date(date);
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset()); // 修正時區
  const isoDate = localDate.toISOString().split("T")[0]; // yyyy-mm-dd

  const [year, month, day] = isoDate.split("-");
  return `${year}-${month}-${day}`;
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
  --v-input-control-height: 30px;
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

//:deep(.v-table.outer .v-table__wrapper) {
//  overflow-y: auto;
//  max-height: none;
//}

:deep(.v-table.outer .v-table__wrapper) {
  max-height: none;
  overflow-y: visible;
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

:deep(.dp__calendar_header .dp__calendar_header_item) {
  font-size: 0.8em;
}

// ------- 沒有週數欄（共 7 欄）：一～五綠，六日紅 -------
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(-n+5)) {
  background: #2e7d32; color: #fff;
}
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(6)),
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(7)) {
  background: #c62828; color: #fff;
}

// ------- 有週數欄（第 1 欄是週數）：星期從第 2～8 欄 -------
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(n+2):nth-child(-n+6)) {

  background: #2e7d32; color: #fff;   // 第 2～6 欄 = 一～五 → 綠
}
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(7)),
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(8)) {

  background: #c62828; color: #fff;   // 第 7、8 欄 = 六、日 → 紅
}

// 如果週數欄（W）有開啟，不要上色它
:deep(.dp-colored .dp__calendar_header_item_week) {
  background: transparent !important;
  color: inherit !important;
}

:deep(.dp__month_year_select) {
  color: #1976d2;
  font-weight: bold;
}

:deep(.dateicon > .v-input__prepend .v-icon) {
  color: #F48FB1 !important;
}

// 讓 DatePicker 撐滿 v-menu 設定的寬度
:deep(.dp-stretch .dp__main) {
  width: 100%;
}

:deep(.dp__outer_menu_wrap) {
  width: 140%;
}

// == 工單範圍 v-select 用 begin ==
:deep(.papericon > .v-input__prepend .v-icon) {
  color: #90CAF9 !important;
}

:deep(.select_papericon > .v-input__prepend .v-icon) {
  color: #90CAF9 !important;
}

:deep(.papericon .v-input__details) {
  display:none;
}
// == 工單範圍 v-select 用 end ==

// 讓 DatePicker 撐滿 v-menu 設定的寬度
:deep(.dp-stretch .dp__main) {
  width: 100%;
}

:deep(.v-overlay__content) {
  max-height: none !important;
  overflow-y: hidden !important;
}

.slider {
  position: absolute;

  min-width: 80px;
  width: 80px;
  min-height: 24px;
  height: 24px;

  inset: 0;
  background-color: #e9513a;
  transition: 0.4s;
  border-radius: 25px;
  cursor: pointer;

  // 文字定位基準
  overflow: hidden;

  .txt {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 10px;
    font-weight: 800;
    color: #fff;
    user-select: none;
    pointer-events: none;
    opacity: 1;
    transition: 0.2s;
  }

  .txt.on {
    left: 8px;
    opacity: 0;          // 預設不顯示 ON
  }

  .txt.off {
    right: 8px;          // 預設顯示 OFF
  }

  // knob
  &::before {
    content: "";
    position: absolute;
    width: 19px;
    height: 19px;
    top: 0;
    bottom: 0;
    margin: auto;
    left: 3px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
    z-index: 2;
  }
}

.switch input[type="checkbox"]:checked + .slider,
.switch.is-checked .slider {
  background-color: #4fbe79;

  &::before {
    transform: translateX(55px);
  }

  .txt.on {
    opacity: 1;      // checked 顯示 ON
  }

  .txt.off {
    opacity: 0;      // checked 隱藏 OFF
  }
}

.switch-title{
  font-size: 12px;
  font-weight: 600;
  color: #333;
  margin-bottom: 4px;
  white-space: nowrap;
  position: relative;
  left: 70px;
}
</style>
