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
    items-per-page-text="每頁的資料筆數"
  >
    <template v-slot:top>
      <v-card>
        <v-card-title class="align-center pe-2" style="font-weight:700; min-height:100px; height:100px;">
          <v-row class="mt-0">
            <v-col cols="12" md="3" class="pb-1">
              組裝區異常填報
            </v-col>
            <v-col cols="12" md="2" class="pb-1" />
            <!-- 歷史紀錄按鍵 -->
            <v-col cols="12" md="2" class="pb-1">
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
            <v-col cols="12" md="2" class="pb-1">
              <v-text-field
                v-model="search"
                label="Search"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                hide-details
                single-line
                class="top_find_field"
                density="compact"
              />
            </v-col>
            <!-- excel報表按鍵 -->
            <v-col cols="12" md="3" class="pb-1">
            <!--
              <v-btn
                color="primary"
                variant="outlined"
                class="primary thin mt-n1 mr-15 mx-auto excel_wrapper"
                :disable="isAssembleErrorEmpty"
                @click="exportToExcelFun"
              >
                <v-icon left color="green">mdi-microsoft-excel</v-icon>
                <span style="color:black; font-weight:600;">Excel</span>
              </v-btn>
            -->
            </v-col>
          </v-row>
          <v-row class="mt-0 mb-0 row-hidden" style="min-height:48px; height:48px;">
            <v-col cols="12" md="2" class="pt-3" />

            <!-- 這裡的 transition-group 只包裹 div，內部 v-col 不受影響 -->
            <transition-group name="fade-in-up" tag="div" appear>
              <div v-if="showFields" key="date-input">
                <!-- 日期範圍輸入 -->
                <v-col cols="12" md="2" class="myPadding1" style="animation-delay: 0.2s">
                  <v-locale-provider locale="zhHant">
                    <v-date-input
                      label="日期範圍"
                      variant="underlined"
                      v-model="fromDateValStart"
                      cancel-text="取消"
                      ok-text="確定"
                      :value="formattedRange"
                      placeholder="yyyy-mm-dd ~ yyyy-mm-dd"
                      multiple="range"
                      density="compact"
                      position="relative"
                      class="small-date-input"
                    />
                  </v-locale-provider>
                </v-col>
              </div>

              <div v-if="showFields" key="work-order">
                <!-- 工單範圍輸入 -->
                <v-col cols="12" md="2" class="myPadding2" style="animation-delay: 0.4s">
                  <v-text-field
                    label="工單範圍"
                    variant="outlined"
                    v-model="creditCardNumber"
                    maxlength="25"
                    inputmode="numeric"
                    density="compact"
                    prepend-icon="mdi-archive-check-outline"
                    placeholder="xxxxxxxxxxxx-xxxxxxxxxxxx"
                    @input="formatCreditCard"
                  />
                </v-col>
              </div>
            </transition-group>

            <!-- Excel 按鈕 -->
            <v-col cols="12" md="2" class="myPadding3">
              <v-btn
                color="white"
                style="min-width: 90px; max-height: 34px; border-radius: 6px; border-width:1.5px; border-color:#64B5F6;"
                class="primary thin mt-n1 mr-15 mx-auto"
                :disable="isAssembleErrorEmpty"
                @click="showFields = !showFields"
              >
                <v-icon left color="green" style="font-weight: 700;">mdi-microsoft-excel</v-icon>
                <span style="color:black; font-weight:600;">Excel</span>
              </v-btn>
            </v-col>

            <v-col cols="12" md="4" class="pt-3" />
          </v-row>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '現況進度' (show1_ok) 欄位的表頭 -->
    <template v-slot:header.show1_ok = "{ column }">
      <div
        style="line-height: 1;
        margin: 0; padding: 0;
        display: flex;
        justify-content: flex-start;
        cursor: pointer;
        position: relative; left: 8px;
        width: 80px;"
      >
        <span style="color:black; font-weight:600">{{ column.title }}</span>
      </div>
      <div
        style=" color: #a6a6a6;
                font-size: 10px;
                font-weight: 600;
                text-align: center;
                line-height: 1;
                position:relative;
                right: 20px;
                top: 5px;
              "
      >
        組裝/雷射/檢驗
      </div>
    </template>

    <!-- 客製化 '訂單數量' (req_qty) 欄位表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div
        style=" text-align:center;
                white-space:normal;
                line-height:1.2;
                font-size:14px;
                color:black;
                font-weight:600;
              "
      >
        訂單<br />數量
      </div>
    </template>

    <!-- 客製化 '現況數量' (delivery_qty) 欄位表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div
        style=" text-align:center;
                white-space:normal;
                line-height:1.2;
                font-size: 14px;
                color:black;
                font-weight:600;
              "
      >
        現況<br />數量
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

    <!-- 自訂 '異常原因填寫' 欄位 -->
    <template v-slot:item.cause_message="{ item }">
      <v-combobox
        v-model="item.cause_message"
        :items="abnormal_causes_msg"
        chips
        multiple
        @update:search="onSearchUpdate"
        @update:menu="onMenuUpdate"
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

import { useRoute } from 'vue-router'; // Import useRouter

import { useLocale } from 'vuetify';

import { myMixin } from '../../mixins/common.js';

//import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../../mixins/crud.js';

import { abnormal_causes, informations_for_assemble_error }  from '../../mixins/crud.js';

import { apiOperation }  from '../../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
//const listInformationsForAssembleError = apiOperation('get', '/listInformationsForAssembleError');
const listAbnormalCauses = apiOperation('get', '/listAbnormalCauses');

const updateAssemble = apiOperation('post', '/updateAssemble');
const getInformationsForAssembleErrorByHistory = apiOperation('post', '/getInformationsForAssembleErrorByHistory');
const exportToExcelForError = apiOperation('post', '/exportToExcelForError');

//=== component name ==
defineComponent({ name: 'PickReportForAssembleError' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
let intervalId = null;              // 10分鐘, 倒數計時器

const route = useRoute(); // Initialize router

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num', width:110 },
  { title: '現況進度', sortable: false, key: 'show1_ok', width:110 },
  { title: '現況備註', sortable: false, key: 'show3_ok', width:110 },
  { title: '交期', sortable: false, key: 'delivery_date', width:90 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:40 },
  { title: '現況數量', sortable: false, key: 'delivery_qty', width:40 },
  { title: '點檢人員', sortable: false, key: 'user', width:110 },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:300 },
  { title: '異常原因', sortable: false, key: 'cause_message' },
  //{ title: '異常原因填寫', sortable: false, key: 'cause_message' },
];

const comboboxRef = ref(null);
const searchText = ref("");

const search = ref('');

const currentUser = ref({});
const componentKey = ref(0)             // key值用於強制重新渲染
const permDialog = ref(false);

const fromDateValP = ref(null);

const fromDateStart = ref("");
//const fromDateValStart = ref(null);
const fromDateValStart = ref([]);
//const compareDateStart = ref("");       //查詢開始日期

//const fromDateValStart = ref(new Date().toISOString().split("T")[0]); // YYYY-MM-DD
const showFields = ref(false);            // 用來控制是否顯示額外的欄位

const fromDateMenuEnd = ref(false);
const fromDateValEnd = ref(null);
//const compareDateEnd = ref("");         //查詢截止日期
const creditCardNumber = ref("");
const orderNumRange = ref(["", ""]); // 用來儲存第一組與第二組的數字

const minDate = ref("2024-07-01");
const maxDate = ref("2054-06-30");

const history = ref(true);

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

watch(
  () => informations_for_assemble_error.value || [],
  (newVal) => {
    console.log("Updated cause_message:", newVal);
  },
  { deep: true }
);

watch(fromDateValStart, (val) => {
  //fromDateStart.value = formatDate3(val);
  //console.log("watch: fromDateStart.value:",fromDateStart.value)
  console.log("watch(), fromDateValStart:", fromDateValStart.value)

  if (!val || val.length === 0) {
    fromDateStart.value = [];
  } else {
    fromDateStart.value = val.map((date) => formatDate3(date));
  }
  console.log("watch: fromDateStart.value:", fromDateStart.value);
});

//=== computed ===
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);
/*
const abnormal_causes_msg = computed(() =>
  abnormal_causes.value.map(cause => `${cause.message}(${cause.number})`)
);
*/
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
/*
const formattedDate = computed({
  get: () => {
    if (!fromDateValStart.value) return "";

    const date = new Date(fromDateValStart.value);
    return date.toLocaleDateString("zhHant", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).replace(/\//g, "-");
  },
  set: (val) => {
    if (!val) {
      fromDateValStart.value = null;
      return;
    }

    fromDateValStart.value = new Date(val); // 轉回 Date 物件
  }
});
*/
const formattedRange = computed(() => {
  if (!fromDateValStart.value || fromDateValStart.value.length === 0) return "";

  // 轉換格式
  const formattedDates = fromDateValStart.value.map((date) => formatDate3(date));

  if (formattedDates.length === 1) {
    return formattedDates[0]; // 只有選擇一個日期時
  } else if (formattedDates.length >= 2) {
    return `${formattedDates[0]} ~ ${formattedDates[formattedDates.length - 1]}`; // 開始 + 空白 + 結束
  }
  return "";
});

// 計算屬性 - 過濾符合條件的資訊
const filteredInformations = computed(() => {
  return informations_for_assemble_error.value.filter(item => {
    const isWithinDateRange = checkDateInRange(item.delivery_date);
    const isWithinOrderRange = checkOrderInRange(item.order_num);
    return isWithinDateRange && isWithinOrderRange;
  });
});

/*
const fromDateValStartComputed = computed({
  get: () => fromDateValStart.value,  // 確保是 YYYY-MM-DD
  set: (val) => {
    if (!val) return;
    if (typeof val === "string") {
      fromDateValStart.value = val;  // 直接使用 YYYY-MM-DD
    } else {
      fromDateValStart.value = val.toISOString().split("T")[0];  // 轉換日期
    }
  }
});
*/
//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleError.vue, mounted()...");

  const { current } = useLocale();
  console.log("目前語系:", current.value); // 應該輸出 "zhHant"

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
  //setTimeout(moveWin, 600);
  intervalId = setInterval(getInformationsForAssembleErrorByHistoryFun, 10 * 1000);  // 每 10秒鐘調用一次 API

  /*
  requestAnimationFrame(() => {
    const buttons = document.querySelectorAll(".v-date-picker-month__day--selected > button");
    buttons.forEach(button => {
      button.style.backgroundColor = "red";
      button.style.color = "white";
    });
  });
  */

  const observer = new MutationObserver(() => {
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
});

//=== onUpdated ===
onUpdated(() => {
  // text content should be the same as current `count.value`
  //console.log(document.getElementById('count').textContent)
})

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時）
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
}

const exportToExcelFun = async () => {
  console.log('PickReportForAssembleError, exportToExcelFun()...');

  const obj = {
    order_num: '訂單編號',
    comment: '說明',
    delivery_date: '交期',
    req_qty: '訂單數量',
    delivery_qty: '現況數量',
    user: '點檢人員',
    cause_message: '異常原因',
    cause_user: '異常原因填寫人員',
    cause_date: '異常原因填寫日期',
  };

  const object_Desserts = [obj, ...informations_for_assemble_error.value];

  let payload = {
    blocks: object_Desserts,
    count: object_Desserts.length,
    name: currentUser.value.name,
  };

  try {
    const export_file_data = await exportToExcelForError(payload);
    console.log("data:", export_file_data);

    if (export_file_data.status) {
      let temp_message = `庫存記錄(${export_file_data.message})轉檔完成!`;
      showSnackbar(temp_message, '#008184');
    } else {
      showSnackbar(excel_file_data.message, 'red accent-2');
    }
  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("存檔錯誤!", 'red accent-2');
  }
};

// 當v-combobox輸入欄位輸入值時觸發
const onSearchUpdate = (search) => {
  searchText.value = search;
};

// 當v-combobox選單開啟或關閉時觸發
const onMenuUpdate = (isOpen) => {
  console.log("onMenuUpdate, 選單狀態:", isOpen ? "開啟" : "關閉");

  if (isOpen) {
    searchText.value = ""; // 清空搜尋框
  }
};

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

  //fromDateStart.value = fromDateValStart.value.toISOString().split("T")[0];
  //if (typeof date === "string") return date; // 確保格式為 YYYY-MM-DD
  console.log("日期:", fromDateStart.value);  // 轉換為 YYYY-MM-DD
  //let kk =date.toISOString().split("T")[0];
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
  /*
  if (!date) return null;
  // 確保 date 是 Date 物件，再轉換成 yyyy-mm-dd 格式

  const localDate = new Date(date);
  localDate.setMinutes(localDate.getMinutes() - localDate.getTimezoneOffset()); // 修正時區
  const isoDate = localDate.toISOString().split("T")[0]; // yyyy-mm-dd

  const [year, month, day] = isoDate.split("-");
  console.log("formatDate3", `${day}-${month}-${year}`)
  return `${year}-${month}-${day}`;
  */

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
  if (!search) return true;
  search = search.toLowerCase();

  return Object.values(item).some(val =>
    String(val).toLowerCase().includes(search)
  );
};

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
  //width: 100px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:last-child) {
  display: flex;
  justify-content: center;
  align-items: center;
  //width: 140px !important;
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
  min-width: 300px;
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

//excel按鍵
:deep(.excel_wrapper) {
  //position: relative;
  //top: -4px !important;
  //right: -72px !important;
  width: 90px !important;
}

///日期
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

:deep(.small-date-input) {
  font-size: 12px;    // 調整整體文字大小
}

:deep(.small-date-input .v-field__content) {
  min-height: 32px;   // 控制高度
}

:deep(.small-date-input .v-input__control) {
  padding: 2px 8px;   // 縮小內邊距
}

:deep(.small-date-input .v-icon) {
  font-size: 16px;    // 縮小日曆圖標大小
}

:deep(.small-date-input .v-btn) {
  min-width: 24px;    // 縮小按鈕大小
  height: 24px;
}
/*
:deep(.v-input--plain-underlined input::placeholder) {
  color: red;

}
*/
/*
:deep(.small-date-input .v-date-picker-month__day--selected .v-btn) {
  background-color: red !important;
  color: white;
}

:deep(.small-date-input .v-date-picker-month__day--selected.v-date-picker-month__day--week-start .btn) {
  background-color: red !important;
  color: white;
}

:deep(.small-date-input .v-date-picker-month__day--selected.v-date-picker-month__day--week-end .btn) {
  background-color: red !important;
  color: white;
}
*
/*
.v-date-picker-month__day--selected > button {
  background: red !important;
  color: white;
}
*/
:deep(.myPadding1 > .v-locale-provider > .v-input > .v-input__control) {
  max-width: 220px;
  position: relative;
  left: 140px;
  top: 5px;
}

:deep(.myPadding1 > .v-locale-provider > .v-input > .v-input__prepend) {
  position: relative;
  left: 150px;
  top: 5px;
}

:deep(.myPadding1 > .v-locale-provider > .v-input > .v-input__prepend > i.mdi-calendar) {
  color: #64B5F6;
}

:deep(.myPadding2 > .v-input > .v-input__control) {
  min-width: 270px;
  position: relative;
  left: 200px;
  top: 5px;
}

:deep(.myPadding2 > .v-input > .v-input__prepend) {
  position: relative;
  left: 210px;
  top: 5px;
}

:deep(.myPadding2 > .v-input > .v-input__prepend > i.mdi-archive-check-outline) {
  color:#64B5F6;
}

:deep(.myPadding3 > button) {
  position: relative;
  left: 270px;
  top: 5px;
}

.myPadding1, .myPadding2, .myPadding3 {
  padding-top: 12px;
}

:deep(.v-picker__actions .v-btn) {
    background-color: blue !important;
    color: #fff;

}

.fade-in-up-enter-active, .fade-in-up-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease-out;
}

.fade-in-up-enter-from {
  opacity: 0;
  transform: translateY(-15px);
}

.fade-in-up-leave-to {
  opacity: 0;
  transform: translateY(15px);
}
</style>
