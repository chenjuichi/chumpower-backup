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

  <v-data-table
    :headers="headers"
    :items="filteredInformations"
    :row-props="getRowProps"
    :search="search"
    :custom-filter="customFilter"
    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"

    item-value="order_num"
    items-per-page="5"
    v-model:page="pagination.page"
  >
    <template v-slot:top>
      <v-card>
        <v-card-title class="align-center pe-2" style="font-weight:700; min-height:120px; height:120px;">
          <v-row class="mt-0">
            <v-col cols="12" md="3" class="pb-2">
              組裝區異常填報
            </v-col>

            <!--<v-col cols="12" md="2" class="pb-1" />-->

            <!-- 歷史紀錄按鍵 -->
            <v-col cols="12" md="2" class="pb-6">
              <v-btn
                @click="toggleHistory"
                :active="history"
                color="primary"
                variant="outlined"
              >
                <v-icon left color="blue">mdi-history</v-icon>
                <span style="color:black; font-weight:600;">歷史紀錄</span>
              </v-btn>
            </v-col>

            <!--搜尋欄位-->
            <v-col cols="12" md="2" class="pb-6">
              <v-text-field
                v-model="search"
                label="搜尋"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                hide-details
                single-line
                density="compact"
                class="top_find_field"
              />
            </v-col>

            <v-col cols="12" md="3" class="pb-1">
              <!-- 客製化barcode輸入 -->
              <v-text-field
                v-model="bar_code"
                :value="bar_code"
                ref="barcodeInput"
                @keyup.enter="handleBarCode"
                hide-details="auto"
                prepend-icon="mdi-barcode"
                style="min-width:200px; width:200px;"
                class="align-center"
                density="compact"
              />
            </v-col>

            <v-col cols="12" md="2" class="pb-1" />
          </v-row>

          <v-row class="mt-0 mb-0 row-hidden" style="min-height: 48px; height: 48px; flex-wrap: nowrap;">
            <!--日期範圍-->
            <v-col cols="4" class="d-flex justify-end align-center pt-0">
              <Transition name="slide">
                <div v-if="showFields">
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
            <v-col cols="4" class="d-flex justify-start align-center pt-0">
              <Transition name="slide">
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
                style="margin-top:20px;"
              />
              </Transition>
            </v-col>

            <!--Excel按鍵-->
            <v-col cols="4" class="d-flex justify-center align-center pb-12">
              <div class="flip_btn">
                <v-btn
                  color="white"
                  style="min-width: 90px; max-height: 34px; border-radius: 6px; border-width:1.5px; border-color:#64B5F6;"
                  class="side default-side primary thin mt-n1 mx-auto"
                  :disable="isAssembleErrorEmpty"
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
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '訂單編號' (order_num) 欄位的表頭 -->
    <template v-slot:header.order_num = "{ column }">
      <div style="line-height: 1;
        margin: 0; padding: 0;
        display: flex;
        justify-content: flex-start;
        cursor: pointer;
        position: relative; left: 8px;
        width: 60px;
      ">
        <span style="color:black; font-weight:600">{{ column.title }}</span>
      </div>
      <div style="color: #a6a6a6;
        font-size: 10px;
        font-weight: 600;
        text-align: center;
        line-height: 1;
        position:relative;
        right: 20px;
        top: 5px;
      ">
        途程
      </div>
    </template>

    <!-- 客製化 '現況進度' (show1_ok) 欄位的表頭 -->
    <template v-slot:header.show1_ok = "{ column }">
      <div style="line-height: 1;
        margin: 0; padding: 0;
        display: flex;
        justify-content: flex-start;
        cursor: pointer;
        position: relative; left: 8px;
        width: 80px;
      ">
        <span style="color:black; font-weight:600">{{ column.title }}</span>
      </div>
      <div style="color: #a6a6a6;
        font-size: 10px;
        font-weight: 600;
        text-align: center;
        line-height: 1;
        position:relative;
        right: 20px;
        top: 5px;
      ">
        組裝/雷射/檢驗
      </div>
    </template>

    <!-- 客製化 '訂單數量' (req_qty) 欄位表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align:center;
        white-space:normal;
        line-height:1.2;
        font-size:14px;
        color:black;
        font-weight:600;
      ">
        訂單<br />數量
      </div>
    </template>

    <!-- 客製化 '交期' 欄位表頭 -->
    <template v-slot:header.delivery_date="{ column }">
      <span style=" position:relative;
        left:20px;
        text-align:center;
        white-space:normal;
        line-height:1.2;
        font-size:14px;
        color:black;
        font-weight:600;
      ">
        {{ column.title }}
      </span>
    </template>

    <!-- 客製化 '現況數量' (delivery_qty) 欄位表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align:center;
        white-space:normal;
        line-height:1.2;
        font-size: 14px;
        color:black;
        font-weight:600;
      ">
        現況<br />數量
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div style="position:relative; right: 0.2vw;">
        <div>{{ item.order_num }}</div>
        <div style="color: #1a1aff; font-size:12px; position:relative; right: 1.2vw;">{{ item.work}}</div>
      </div>
    </template>

    <!-- 自訂 '現況進度' 欄位 -->
    <template v-slot:item.show1_ok="{ item }">
      <div style="position:relative; right: 1.5vw;">
        <div style="font-weight:600;">{{ item.show1_ok }}</div>
        <div style="color: #1a1aff; font-size:12px;">{{ item.show2_ok}}</div>
      </div>
    </template>

    <!-- 自訂 '現況備註' 欄位 -->
    <template v-slot:item.show3_ok="{ item }">
      <div style="font-weight:600;">{{ item.show3_ok }}</div>
    </template>

    <!-- 自訂 '交期' 欄位 -->
    <template v-slot:item.delivery_date="{ item }">
      <span style="position:relative; left:30px;">
        {{ item.delivery_date }}
      </span>
    </template>

    <!-- 自訂 '訂單數量' 欄位 -->
    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.date }}</div>
      </div>
    </template>

    <!-- 自訂 '點檢人員' 欄位 -->
    <template v-slot:item.user="{ item }">
        <div>
          {{item.work}}-{{ item.user }}
        </div>
    </template>

    <!-- 自訂 '說明' 欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
        <!--<div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>-->
      </div>
    </template>

    <!-- 自訂 '異常原因填寫' 欄位 -->
    <!--當使用者在 combobox 裡打字時，觸發 onSearchUpdate 方法-->
    <!--當 combobox 的選單打開或關閉時，觸發 onMenuUpdate 方法-->
    <!--當使用者選擇（或輸入）新值時，觸發 onValueUpdate 方法，並 item 當參數傳進去-->
    <template v-slot:item.cause_message="{ item }">
      <v-combobox
        v-model="item.cause_message"
        :items="abnormal_causes_msg"
        chips
        multiple

        class="custom-combobox"
        @update:search="onSearchUpdate"

        @update:menu="(isOpen) => onMenuUpdate(isOpen, item)"
        :ref="el => setComboboxRef(el, item.order_num)"
      >
        <template v-slot:selection="{ item }">
          <v-chip>{{ item.raw }}</v-chip>
        </template>
      </v-combobox>
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onUpdated , onMounted, onUnmounted, onBeforeMount, nextTick, onBeforeUnmount } from 'vue';

import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
dayjs.extend(isSameOrBefore);   //啟用 plugin

import { useRoute } from 'vue-router';

//import { useLocale } from 'vuetify';

import { myMixin } from '../mixins/common.js';

//import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { abnormal_causes, alarm_objects_list }  from '../mixins/crud.js';
import { informations_for_assemble_error, schedules_for_assemble_error }  from '../mixins/crud.js';

import { apiOperation }  from '../mixins/crud.js';
import { apiOperationB } from '../mixins/crudB.js';

// 使用 apiOperation 函式來建立 API 請求
//const listInformationsForAssembleError = apiOperation('get', '/listInformationsForAssembleError');
const listAbnormalCauses = apiOperation('get', '/listAbnormalCauses');

const updateAssemble = apiOperation('post', '/updateAssemble');
const updateAssembleAlarmMessage = apiOperation('post', '/updateAssembleAlarmMessage');
const getInformationsForAssembleErrorByHistory = apiOperation('post', '/getInformationsForAssembleErrorByHistory');
const getSchedulesForAssembleError = apiOperation('post', '/getSchedulesForAssembleError');

const exportToExcelForError = apiOperation('post', '/exportToExcelForError');

const downloadFile = apiOperationB('post', '/downloadXlsxFile');

//=== component name ==
defineComponent({ name: 'PickReportForAssembleError' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
let intervalId = null;              // 10秒鐘, 倒數計時器

let observer = null;

const showBackWarning = ref(true);

const bar_code = ref('');
const barcodeInput = ref(null);

const comboboxRefs = ref({});

const route = useRoute(); // Initialize router

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num', width:110 },
  { title: '現況進度', sortable: false, key: 'show1_ok', width:110 },
  { title: '現況備註', sortable: false, key: 'show3_ok', width:110 },
  { title: '交期', sortable: false, key: 'delivery_date', width:90 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:40 },
  { title: '現況數量', sortable: false, key: 'delivery_qty', width:40 },
  { title: '點檢人員', sortable: false, key: 'user', width:120 },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:320 },
  { title: '異常原因', sortable: false, key: 'cause_message' },
  //{ title: '異常原因填寫', sortable: false, key: 'cause_message' },
];

const causeMessageMap = ref([]); // 儲存用戶輸入的 cause_message，使用 order_num 作為鍵

const comboboxRef = ref(null);
const searchText = ref("");

const search = ref('');

const currentUser = ref({});
const componentKey = ref(0)             // key值用於強制重新渲染

const pick_date_dialog = ref(false);    // 控制 v-pick_date Dialog 顯示
const selectedRange = ref([])           // 最終選定日期範圍
const tempRange = ref([])               // 選單中暫存日期範圍

const fromDateValP = ref(null);

const fromDateStart = ref("");
const fromDateValStart = ref([]);

const showFields = ref(false);            // 用來控制是否顯示額外的excel btn欄位

const fromDateMenuEnd = ref(false);
const fromDateValEnd = ref(null);
//const compareDateEnd = ref("");         //查詢截止日期
const creditCardNumber = ref("");
const orderNumRange = ref(["", ""]); // 用來儲存第一組與第二組的數字

const selected_alarm_objects_list = ref([]);


//const minDate = ref("2024-07-01");
//const maxDate = ref("2054-06-30");

//const comboboxWidth = ref(220);

const history = ref(true);

const pagination = reactive({
  itemsPerPage: 5, // 預設值, rows/per page
  page: 1,
});

const selectedFile = ref(null); 						                // 儲存已選擇檔案的名稱
const topPath = ref('C:\\vue\\chumpower\\excel_export'); 	  // 初始路徑
const downloadFilePath = ref('');
const selectedFileName = ref('');						                // 用於追蹤目前選取的檔案名稱

//=== watch ===
watch(
  () => informations_for_assemble_error.value || [],
  (newVal) => {
    console.log("Updated cause_message:", newVal);
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

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

//=== computed ===
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

const abnormal_causes_msg = computed(() => {

  if (!searchText.value)
    return abnormal_causes.value.map(cause => `${cause.message}(${cause.number})`);

  return abnormal_causes.value
    .filter(cause =>
      cause.message.includes(searchText.value) ||         // 搜尋 message
      cause.number.toString().includes(searchText.value)  // 搜尋 number
    )
    .map(cause => `${cause.message}(${cause.number})`);
});

const isAssembleErrorEmpty = computed(() => {
  return informations_for_assemble_error.value.length === 0;
});

// 顯示格式：yyyy-mm-dd ~ yyyy-mm-dd
const formattedDateRange = computed(() => {

  const list = selectedRange.value
  if (list.length === 0) return ''
  const sorted = [...list].sort((a, b) => new Date(a) - new Date(b))
  const start = dayjs(sorted[0]).format('YYYY-MM-DD')
  const end = dayjs(sorted[sorted.length - 1]).format('YYYY-MM-DD')
  return start === end ? start : `${start} ~ ${end}`
})

// 計算屬性 - 過濾符合條件的資訊
const filteredInformations = computed(() => {
  return informations_for_assemble_error.value
  .map(item => ({
    ...item,
    // 確保 `cause_message` 不會被更新
    //cause_message: item.cause_message,
    cause_message: causeMessageMap.value[item.order_num] || item.cause_message,
  }))
  .filter(item => {
    const isWithinDateRange = checkDateInRange(item.delivery_date);
    const isWithinOrderRange = checkOrderInRange(item.order_num);
    return isWithinDateRange && isWithinOrderRange;
  });
});

//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleError.vue, mounted()...");

  // 阻止直接後退
  window.history.pushState(null, null, document.URL);
  //history.pushState(null, null, document.URL);
  window.addEventListener('popstate', handlePopState);

  //const { current } = useLocale();
  //console.log("目前語系:", current.value); // 應該輸出 "zhHant"

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
  //
  observer = new MutationObserver(() => {
    const buttons = document.querySelectorAll(".v-date-picker-month__day--selected > button");
    buttons.forEach(button => {
      button.style.backgroundColor = "red";
      button.style.color = "white";
    });

    const actionButtons = document.querySelectorAll(".v-picker__actions > button");
    actionButtons.forEach(button => {
      button.style.backgroundColor = "#64B5F6";
      button.style.color = "white";
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
  //

  //setTimeout(moveWin, 600);

  intervalId = setInterval(getSchedulesForAssembleErrorFun, 30 * 1000);  // 每 10秒鐘調用一次 API

  /*
  requestAnimationFrame(() => {
    const buttons = document.querySelectorAll(".v-date-picker-month__day--selected > button");
    buttons.forEach(button => {
      button.style.backgroundColor = "red";
      button.style.color = "white";
    });
  });
  */
});

// 自動 focus
if (barcodeInput.value) {
  barcodeInput.value.focus();
}

//=== onUpdated ===
onUpdated(() => {
  // text content should be the same as current `count.value`
  //console.log(document.getElementById('count').textContent)
})

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  window.removeEventListener('popstate', handlePopState)

  clearInterval(intervalId);

//  // 在組件卸載前停止監聽
//  if (observer) {
//    observer.disconnect();
//  }
});

//=== created ===
onBeforeMount(() => {
  console.log("PickReportForAssembleError.vue, created()...", currentUser.value)

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

onBeforeUnmount(() => {
  // 在組件卸載前停止監聽
  if (observer) {
    observer.disconnect();
  }
});

//=== method ===
const initialize = async () => {
  console.log("PickReportForAssembleError, initialize()...");

  try {
    await listAbnormalCauses();
  } catch (error) {
    console.error("Initialize Error in listAbnormalCauses():", error);
  }

  try {
    await getInformationsForAssembleErrorByHistoryFun();
  } catch (error) {
    console.error("InitializeError in getInformationsForAssembleErrorByHistoryFun():", error);
  }
};
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

const setComboboxRef = (el, orderNum) => {
  if (el) {
    comboboxRefs.value[orderNum] = el;
  }
};

const handleBarCode = () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)
  let myBarcode = filteredInformations.value.find(m => m.order_num == bar_code.value);

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

  const comboRef = comboboxRefs.value[item.order_num];
  if (comboRef) {
    // 取得 combobox 中的 input 元素並聚焦
    const input = comboRef.$el.querySelector('input');
    if (input) {
      input.focus();
      // 可選：模擬 Enter 鍵以觸發變更事件
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

const handlePopState = () => {
  // ✅ 正確方式：保留 Vue Router 的 state
  //history.pushState(history.state, '', document.URL)
  window.history.pushState(history.state, '', document.URL)

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const clearDates = () => {
  selectedRange.value = []
  tempRange.value = []
}

const generateDateRange = (start, end) => {
  const range = []
  let current = dayjs(start)
  const last = dayjs(end)

  while (current.isSameOrBefore(last)) {
    range.push(current.toDate())
    current = current.add(1, 'day')
  }
  return range
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

const toggleHistory = () => {
  history.value = !history.value;
  getInformationsForAssembleErrorByHistoryFun();
};

const getInformationsForAssembleErrorByHistoryFun = async () => {
  console.log('PickReportForAssembleError, getInformationsForAssembleErrorByHistoryFun()...');

  let payload = {
    history_flag: history.value,
  };
  await getInformationsForAssembleErrorByHistory(payload);
};

const getSchedulesForAssembleErrorFun = async () => {
  console.log('PickReportForAssembleError, getSchedulesForAssembleErrorFun()...');

  let payload = {
    history_flag: history.value,
  };
  await getSchedulesForAssembleError(payload);

  // 用 Map 加速查找
  const scheduleMap = new Map()
  for (const s of schedules_for_assemble_error.value) {
    const key = `${s.id}-${s.assemble_id}`
    scheduleMap.set(key, {
      show1_ok: s.show1_ok,
      show2_ok: s.show2_ok,
      show3_ok: s.show3_ok,
      work: s.work,
    })
  }

  console.log("scheduleMap:", scheduleMap);

  // 更新原始 informations.value 的資料
  informations_for_assemble_error.value = informations_for_assemble_error.value.map(info => {
    const key = `${info.id}-${info.assemble_id}`
    const schedule = scheduleMap.get(key)

    if (schedule) {
      return {
        ...info,
        show1_ok: schedule.show1_ok,
        show2_ok: schedule.show2_ok,
        show3_ok: schedule.show3_ok,
        work: schedule.work,

      }
    } else {
      return info // 沒變化就原封不動回傳
    }
  })
};

const exportToExcelFun = async () => {
  console.log('PickReportForAssembleError.vue, exportToExcelFun()...');

  const obj = {
    order_num: '訂單編號',
    comment: '說明',
    delivery_date: '交期',
    req_qty: '訂單數量',
    delivery_qty: '現況數量',
    user: '點檢人員',
    cause_message_str: '異常原因',
    cause_user: '填寫人員',
    cause_date: '填寫日期',
  };

  // 先取得 data table 內的 filteredInformations
  let filteredData = filteredInformations.value;
  console.log("1. filteredData: ", filteredData);

  // 再手動應用 customFilter()
  if (search.value) {
    filteredData = filteredData.filter(item => customFilter(search.value, item));
  }
  console.log("2. filteredData: ", filteredData);

  // 最終要匯出的資料
  //let object_Desserts = [obj, ...filteredData];

  //let updatedData = object_Desserts.map(item => ({
  //  ...item,
  //  cause_message_str: item.cause_message_str ?? ( // 若已存在則保留，否則轉換
  //    Array.isArray(item.cause_message) ? item.cause_message.join(',') : ''
  //  )
  //}));

  //let updatedData = object_Desserts.map(item => ({
  //  ...item,
  //  cause_message_str: Array.isArray(item.cause_message) ? item.cause_message.join(',') : ''
  //}));

  //let updatedData = filteredData.map(item => ({
  //  ...item,
  //  cause_message_str: Array.isArray(item.cause_message) && item.cause_message.length > 0
  //    ? item.cause_message.join(',')
  //    : ''
  //}));

  // 確保欄位名稱與 obj 一致
  let updatedData = filteredData.map(item => ({
    order_num: item.order_num ?? '',
    comment: item.comment ?? '',
    delivery_date: item.delivery_date ?? '',
    req_qty: item.req_qty ?? '',
    delivery_qty: item.delivery_qty ?? '',
    user: item.user ?? '',
    cause_message_str: Array.isArray(item.cause_message) && item.cause_message.length > 0
      ? item.cause_message.join(',')
      : '',
    cause_user: item.cause_user ?? '',
    cause_date: item.cause_date ?? '',
  }));
  console.log("3. updatedData: ", updatedData);

  let object_Desserts = [obj, ...updatedData];
  console.log("4. object_Desserts: ", object_Desserts);

  let payload = {
    blocks: object_Desserts,
    count: object_Desserts.length,
    name: currentUser.value.name,
  };

  try {
    const export_file_data = await exportToExcelForError(payload);
    console.log("data:", export_file_data);

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

// 當v-combobox輸入欄位輸入值時觸發
const onSearchUpdate = (search) => {
  searchText.value = search;
};

// 當v-combobox選單開啟或關閉時觸發
const onMenuUpdate = (isOpen, item) => {
  console.log("onMenuUpdate, 選單狀態:", isOpen ? "開啟" : "關閉");

  if (!isOpen) {
    console.log("選單關閉，更新這筆:", item);
    onValueUpdate(item);  // 觸發你的 API 更新邏輯
  } else  {
    //searchText.value = ""; // 清空搜尋框
    // 合併目前已選的 cause_message 與下拉選單中所有項目
    const selectedItems = item.cause_message || [];
    console.log("selectedItems:", selectedItems);
    abnormal_causes_msg.value = Array.from(new Set([
      ...abnormal_causes_msg.value,
      ...selectedItems
    ]));
  }

};

const onValueUpdate = async (item) => {
  console.log("onValueUpdate(),錯誤訊息陣列", item);
  /*
  let matchingIds = alarm_objects_list.value
    .filter(obj => item.cause_message.some(msg => msg.includes(obj.message)))
    .map(obj => obj.id)
    .join(',');

  console.log("matchingIds:",matchingIds);
  selected_alarm_objects_list.value = [...item.cause_message];
  */
  // 將 item.cause_message 複製進 ref
  //let payload = {
  //  assemble_id: item.assemble_id,
  //  record_name: 'alarm_message',
  //  record_data: item.cause_message.join(', '),
  //};
  //await updateAssemble(payload);

  const payload = {
    assemble_id: item.assemble_id,
    cause_message: item.cause_message,  // 是一個 array，例如 ["異常1", "異常2"]
    cause_user: currentUser.value.empID,
  };

  try {
    await updateAssembleAlarmMessage(payload);
    console.log('更新成功...');
  } catch (error) {
    console.error('更新失敗:', error.response?.data?.message || error.message);
  }

}

// 格式化日期顯示
const formatDate = () => {
  console.log("formatDate(), date:", fromDateValStart.value, typeof(fromDateValStart.value))

  if (!fromDateValStart.value) return "";
  const date = new Date(fromDateValStart.value);
  fromDateStart.value = date.toLocaleDateString("zhHant", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).replace(/\//g, "-"); // 轉換成 YYYY-MM-DD 格式

  console.log("日期:", fromDateStart.value);  // 轉換為 YYYY-MM-DD

  let kk=date.toLocaleDateString("zhHant", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).replace(/\//g, "-"); // 把 / 轉成 -
  console.log("kk日期:", kk);
  return kk; // 轉換為 YYYY-MM-DD
};
/*
const formatDate2 = (date) => {
  if (!date) return "";

  return new Date(date).toLocaleDateString("zhHant", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).replace(/\//g, "-"); // 把 "/" 轉成 "-"
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


const customFilter = (value, search, item) => {
//const customFilter = (search, item) => {
    if (!search) return true;
  search = search.toLowerCase();

  return Object.values(item).some(val =>
    String(val).toLowerCase().includes(search)
  );
};

/*
const customFilter = (value, search, item) => {
  return value != null &&
          query != null &&
          typeof value === 'string' &&
          value.toString().toLocaleUpperCase().indexOf(query) !== -1
}
*/
const dateClicked = (newValue) => {
  console.log("dateClicked(), 選擇的日期範圍：", newValue);
};
/*
const scrollToEnd = () => {
  nextTick(() => {
    if (comboboxRef.value) {
      const scrollContainer = comboboxRef.value.$el.querySelector(".v-field__input");
      if (scrollContainer) {
        scrollContainer.scrollLeft = scrollContainer.scrollWidth;
      }
    }
  });
};

const moveWin = async () => {
  await nextTick(); // 確保 DOM 更新完成
  const inputEl = comboboxRef.value?.$el?.querySelector(".v-field__input");
  if (inputEl) {
    inputEl.scrollLeft = inputEl.scrollWidth; // 滾動到最右邊
  }
};
*/
const moveWin = async () => {
  await nextTick(); // 確保 DOM 更新完成
  /*
  setTimeout(() => {
    const inputEl = comboboxRef.value?.$el?.querySelector(".v-field__input");
    if (inputEl) {
      inputEl.scrollLeft = inputEl.scrollWidth; // **滾動到最右邊**
    }
  }, 50); // 增加小延遲，確保滾動條正確定位
  */
  setTimeout(() => {
    requestAnimationFrame(() => {
      const inputEl = comboboxRef.value?.$el?.querySelector(".v-field__input");
      if (inputEl) {
        inputEl.scrollLeft = inputEl.scrollWidth;
      }
    });
  }, 300);

};
/*
const handleInputInField = async (item) => {
  console.log("handleInputInField(), item.cause_message:", item.cause_message);

  let payload = {
    assemble_id: item.assemble_id,
    record_name: 'alarm_message',
    record_data: item.cause_message,
  };
  await updateAssemble(payload);
};

// 更新當前資料行
const handleInput = async (item) => {
  console.log("handleInput(), item.cause_message:", item.cause_message);

  // 找到匹配的異常原因
  const match = abnormal_causes_msg.value.find((msg) => {
    const regex = new RegExp(`\\(${item.cause_message}\\)$`); // 檢查是否以 (number) 結尾
    return regex.test(msg);
  });

  if (match) {
    console.log("找到匹配的異常原因:", match);
    // 更新資料行的 cause_message
    item.cause_message = match;
    console.log("item:", item.assemble_id, item.cause_message)
    // 記錄當前送料數量
    let payload = {
      assemble_id: item.assemble_id,
      record_name: 'alarm_message',
      record_data: match,
    };
    await updateAssemble(payload);
  } else {
    console.log("未找到匹配的異常原因!");
    showSnackbar('未找到匹配的異常原因!', 'red accent-2');
  }
};
*/
const getRowProps = (item, index) => {

  // 偶數列與奇數列高度不同
  const backgroundColor = item.index % 2 === 0 ? '#ffffff' : '#edf2f4';

  return {
    style: {
      backgroundColor,
    },
  };
};

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  let payload = {
    assemble_id: item.assemble_id,
    record_name: 'alarm_message',
    record_data: item.cause_message,
  };
  await updateAssemble(payload);
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
  z-index: 10;              // 保证标题在内容上方显示
  background: white;    // 避免内容滚动时标题被遮盖
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
  background-color: white;  // 確保標題背景與卡片一致
  z-index: 2;                   // 提高z-index以確保標題在其他內容之上
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
  position: relative;   // 讓 sticky 定位相對於這個元素
  max-height: 440px;    // 設定合適的高度來產生滾動條
  overflow-y: auto;     // 允許垂直滾動
}

.red-text {
  color: red;
}

:deep(.v-input__control) {
  //min-height: 36px;
  //height: 36px;
  left: 150px;
  position: relative;
  width: 250px;
}

:deep(.v-field__field) {
  min-height : 20px;
  height: 34px;
}

:deep(.v-data-table-footer__info) {
  min-height : 30px;
  height: 40px;
}

.custom-header theader th {
  background-color: #85aef2;  // 自訂背景顏色
}

.blinking {
  animation: blink-animation 1s steps(5, start) infinite;
}

@keyframes blink-animation {
  to {
    visibility: hidden;
  }
}

//

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th > .v-data-table-header__content > span) {
  color: black;
  font-weight: 600;
}

:deep(.v-data-table tbody td) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:first-child div ) {
  display: flex;
  justify-content: center;
  align-items: center;
  //width: 130px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(3) div) {
  display: flex;
  //justify-content: center;
  justify-content: flex-start;
  align-items: center;
  //width: 110px !important;
  //width: auto !important;
  //white-space: nowrap; // 避免換行
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(4) div) {
  //display: flex;
  //justify-content: flex-start;
  //align-items: center;
  position: relative;
  right: 1vw;


  //width: 100px !important;
  //min-width: 100px !important;
  //width: auto !important;
  //white-space: nowrap; // 避免換行
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(7) div) {
  display: flex;
  justify-content: center;
  align-items: center;

}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:last-child) {
  display: flex;
  justify-content: center;
  align-items: center;

}

:deep(.v-field__input) {
  //overflow-x:auto;
  overflow-x:hidden;
  overflow-y:hidden;
  flex-wrap: nowrap;
}

:deep(.v-table__wrapper > table > tbody > tr > td:first-child) {
  text-align: center !important;
  //width: 130px !important;
}

:deep(.v-table__wrapper > table > tbody > tr > td:nth-child(3) div) {
//  //width: auto !important;
//  //white-space: nowrap; // 避免換行
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

:deep(.v-table__wrapper > table > tbody > tr > td:nth-child(4)) {
//  //width: auto !important;
//  //white-space: nowrap; // 避免換行
  position: relative;
  right: 2vw;

  display: flex;
  justify-content: flex-start;
  align-items: center;
}

:deep(.v-table__wrapper > table > tbody > tr > td:last-child > div ) {
  display: flex;
  justify-content: flex-start;
  align-items: center;

  position: relative;
  right: 5vw;
  top: 0px;
}

//調整搜尋欄位的位置
:deep(.top_find_field) {
  position: relative;
  left: -150px;
}

//v-combobox元件

//調整v-combobox的位置
:deep(.v-combobox .v-field ) {
  position: relative;
  right: 50px;
}

//調整v-combobox輸入欄位的寬度
:deep(.v-combobox .v-input__control) {
  min-width: 200px;
  width: 200px;
}

//調整v-combobox輸入欄位的位置
:deep(.v-combobox .v-field__input) {
  padding-bottom: 0px;
  padding-top: 0px;
  min-height: 45px;
  position: relative;
  top: -15px;
  //overflow-x: auto;
  //overflow-y: hidden;
  //flex-wrap: nowrap;
}

//調整v-combobox輸入欄位的位置
:deep(.v-combobox .v-field .v-field__input > input) {
  position:relative;
  top: 10px;
}

//調整v-chip的位置及寬度
:deep(.v-combobox__selection) {
  position: relative;
  top: 10px;
  max-width: 50px;
}

//v-chip的外框形式及顏色
:deep(.v-combobox__selection) {
  border: 1.5px solid blue !important;
  border-radius: 10px;
}

//v-chip的字體顏色
:deep(.v-combobox__selection .v-chip__content) {
  font-weight: 600;
  color: blue;
}
/*
:deep(.custom-combobox > .v-input__control) {
  max-height: 28px !important;
  min-height: 28px !important;
}

:deep(.custom-combobox > .v-input__control .v-field__input) {
  max-height: 28px !important;
  min-height: 28px !important;
}
*/

//===excel按鍵
:deep(.excel_wrapper) {
  //position: relative;
  //top: -4px !important;
  //right: -72px !important;
  width: 90px !important;
}

//===日期

/*
:deep(.v-picker__body) {
  transform: scale(0.8); // 整體縮小 80%
}

:deep(.v-picker__body) {
  font-size: 14px !important;  // 縮小字體
  max-width: 240px !important; // 限制最大寬度
}

:deep(.v-picker__body .v-btn) {
  min-width: 32px !important; // 按鈕變小
  height: 32px !important;
  font-size: 12px !important;
}

:deep(.v-picker__body .v-date-picker-header) {
  font-size: 14px !important; // 調整標題字體
}

:deep(.v-picker__body .v-date-picker-table) {
  padding: 4px !important; // 縮小格子間距
}

:deep(.v-picker__body .v-date-picker-table td) {
  width: 28px !important; // 日期格子的寬度
  height: 28px !important;
}
*/

/*
:deep(.small-date-input) {
  font-size: 12px;    // 調整日曆整體文字大小
}

:deep(.small-date-input .v-field__content) {
  min-height: 32px;   // 控制日曆高度
}

:deep(.small-date-input .v-input__control) {
  padding: 2px 8px;   // 縮小日曆內邊距
}

:deep(.small-date-input .v-icon) {
  font-size: 16px;    // 縮小日曆圖標大小
}

:deep(.small-date-input .v-btn) {
  min-width: 24px;    // 縮小按鈕大小
  height: 24px;
}
*/
:deep(.v-date-picker-header) {
  display: none !important;
}

:deep(.v-picker__actions .v-btn) {
    background-color: blue !important;
    color: #fff;
}

:deep(.v-input__prepend) {
  position:relative;
  left: 12vw;
  color: #64B5F6;
}

:deep(.v-data-table .v-table__wrapper) {
  overflow-x: hidden;
  width: 100%;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

//:deep(.v-combobox .v-input__control) {
//  min-width: 210px;       //default 200px
//}

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
