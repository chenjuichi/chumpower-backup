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

  <v-data-table
    :headers="headers"
    :items="boats"
    fixed-header
    density="comfortable"
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
    item-key="name"
    items-per-page="5"
    :sort-by.sync="sortBy"
    :sort-desc.sync="sortDesc"
    class="elevation-10 custom-table"
  >
    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="d-flex align-center pe-2" style="font-weight:700;">
          組裝區領料生產報工
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

          <v-btn
            color="primary"
            variant="outlined"
            style="position: relative; left: -50px; top: 0px;"
            @click="refreshComponent"
          >
            <v-icon left color="blue">mdi-refresh</v-icon>
            更新訂單
          </v-btn>
        </v-card-title>
      </v-card>
    </template>

    <!-- 使用動態插槽來客製化 'Boat Type' (name) 欄位的表頭 -->
    <template v-slot:header.name="{ column }">
      <v-hover v-slot="{ isHovering, props }">
        <div
          v-bind="props"
          style="display: flex; align-items: center; justify-content: center; cursor: pointer;"
          @click="toggleSort('name')"
        >
          <div>{{ column.title }}</div>
          <div style="min-width: 24px;">
          <!-- 顯示排序圖標，如果正在排序或者滑鼠移入時顯示 -->
          <v-icon v-if="sortBy.includes('name') && isHovering" style="margin-left: 2px;">
            {{ sortDesc[sortBy.indexOf('name')] ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
          </v-icon>
          </div>
        </div>
        <div style="color: #0000FF; font-size: 12px; margin-top: 2px; font-weight: 600; text-align: center; padding-left: 24px;">
          (已領數量)
        </div>
      </v-hover>
    </template>

    <!-- 使用動態插槽來客製化 '作業數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
        <div>{{ column.title }}</div>
        <div style="color: #0000FF; font-size:12px; margin-top: 2px; font-weight:600;">(已領數量)</div> <!-- 在 '訂單編號' 下方插入 '途程' -->
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div>
        <div>{{ item.order_num }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
      </div>
    </template>

    <!-- 自訂 '物料編號' 欄位的資料欄位 -->
    <template v-slot:item.material_num="{ item }">
      <div>
        <div>{{ item.material_num }}</div>
        <div :style="getStatusStyle(item.assemble_process)">{{ item.assemble_process }}</div>
      </div>
    </template>

    <!-- 自訂 '作業數量' 欄位的資料欄位 -->
    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.total_receive_qty }}</div>
      </div>
    </template>

    <!-- 自訂 '領取數量' 輸入欄位 -->
    <template v-slot:item.receive_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
          v-model="item.receive_qty"
          dense
          hide-details
          style="max-width: 60px; text-align: center; z-index: 1;"
          :id="`receiveQtyID-${item.order_num}`"
          @update:modelValue="checkReceiveQty(item)"
          @keyup.enter="updateItem(item)"
          :disabled="item.input_disable"
        />
        <span
          v-show="item.tooltipVisible"
          style="position: absolute; left: 45px; top: 0; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 700;"
        >
          {{ receive_qty_alarm }}
        </span>
      </div>
    </template>

    <!-- 自訂 '說明' 欄位的資料欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="text-align:left; color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
      </div>
    </template>

    <!-- 自訂 '開始' 按鍵欄位 -->
    <template v-slot:item.action="{ item }">
      <v-btn
        size="small"
        variant="tonal"
        style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"
        :disabled="isButtonDisabled(item)"
        @click="updateItem(item)"
      >
        開 始
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
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount } from 'vue';

import { useRoute } from 'vue-router'; // Import useRouter

import { myMixin } from '../../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../../mixins/crud.js';

import { materials_and_assembles }  from '../../mixins/crud.js';

import { apiOperation, setupGetBomsWatcher}  from '../../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listMaterialsAndAssembles = apiOperation('get', '/listMaterialsAndAssembles');

const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const getMaterial = apiOperation('post', '/getMaterial');

//=== component name ==
defineComponent({
  name: 'PickReportForAssemble'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
  showFooter: Boolean
});

//=== data ===

// 定義欄位標題
const headers = [
  { title: 'Boat Type', align: 'start', key: 'name', sortable: true },
  { title: 'Speed (knots)', align: 'end', key: 'speed', sortable: false },
  { title: 'Length (m)', align: 'end', key: 'length', sortable: false },
  { title: 'Price ($)', align: 'end', key: 'price', sortable: false },
  { title: 'Year', align: 'end', key: 'year', sortable: false },
]

// 定義船隻資料
const boats = ref([
  { name: 'Speedster', speed: 35, length: 22, price: 300000, year: 2021 },
  { name: 'Speedster1', speed: 35, length: 22, price: 300000, year: 2021 },
  { name: 'Speedster2', speed: 35, length: 22, price: 300000, year: 2021 },
  { name: 'Speedster3', speed: 35, length: 22, price: 300000, year: 2021 },
  { name: 'Speedster4', speed: 35, length: 22, price: 300000, year: 2021 },
  { name: 'OceanMaster', speed: 25, length: 35, price: 500000, year: 2020 },
  { name: 'Voyager', speed: 20, length: 45, price: 700000, year: 2019 },
  { name: 'WaveRunner', speed: 40, length: 19, price: 250000, year: 2022 },
  { name: 'SeaBreeze', speed: 28, length: 31, price: 450000, year: 2018 },
  { name: 'HarborGuard', speed: 18, length: 50, price: 800000, year: 2017 },
])

const route = useRoute(); // Initialize router

// 排序欄位及方向（需為陣列）
const sortBy = ref(['name'])
const sortDesc = ref([false])

//=== computed ===
const containerStyle = computed(() => ({
    bottom: props.showFooter ? '60px' : '0',
}));

//=== method ===
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
  console.log('更新訂單按鈕已點擊')

  // 透過重新加載當前路由，來刷新組件
  router.go(0);
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
  background-color: #85aef2; /* 自訂背景顏色 */
}

:deep(.v-data-table .v-table__wrapper > table > tbody tr:nth-of-type(odd)) {
   background-color: rgba(0, 0, 0, .05);
 }

:deep(.v-data-table-footer) {
  margin-bottom: -10px;
}

.custom-table {
  //border-collapse: collapse;  // 合併邊框
  //border: 1px solid #000;     // 表格的外框
  border-radius: 0 0 20px 20px;
}
/*
.custom-table th,
.custom-table td {
  border: 1px solid #000;   // 單元格的邊框
  padding: 8px;             // 單元格的內邊距
  text-align: left;         // 文本對齊
}
*/
</style>
