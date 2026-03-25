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

  <!--
  <v-row align="center" justify="center" v-if="currentUser.perm >= 1">
    <v-card width="60vw" class="pa-md-4 mt-3 pb-2 mx-lg-auto">
  -->
    <v-card class="pa-md-4 mt-3 pb-2 mx-lg-auto employer-main-card">
      <!--items-per-page-text="每頁的資料筆數"-->
      <v-data-table
        :headers="headers"
        :items="desserts2"
        class="elevation-1 table_border_radius"
        density="compact"
        v-model:items-per-page="pagination.itemsPerPage"
        :items-per-page-options="footerOptions"
        :items-length="totalItems"
        v-model:page="pagination.page"

        :style="['margin-bottom: 5px', tableStyle]"
      >
        <template #top>
          <v-toolbar flat>
            <v-toolbar-title>員工資料</v-toolbar-title>
            <v-divider class="mx-4" inset vertical /><v-spacer />
            <v-spacer></v-spacer>
            <v-dialog
              v-model="dialog"
              max-width="1000"
              content-class="employer-edit-dialog"
            >
              <template v-slot:activator="{ props: activatorProps }">
                  <!--<v-btn v-bind="activatorProps" @click="openDialog" color="primary" dark class="mb-2" v-if="currentUser.perm <= 2">-->
                  <v-btn v-bind="activatorProps" @click="dialog = true" color="primary" dark class="mb-2" v-if="currentUser.perm <= 2">
                  <v-icon left dark>mdi-table-plus</v-icon>
                  新增資料
                </v-btn>
              </template>
              <v-card class="employer-dialog-card">
                <v-card-title class="dialog-title-bar">
                  <span class="text-h5">{{ formTitle }}</span>
                </v-card-title>

                <v-card-text class="dialog-body">
                  <!-- 上半部：基本資料 + 權限 -->
                  <v-row class="dialog-main-row" align="stretch">
                    <!-- 左側：基本資料 -->
                    <v-col cols="12" lg="7">
                      <div class="dialog-section">
                        <div class="section-title">基本資料</div>
                        <v-row>
                          <v-col cols="12" sm="3">
                            <v-text-field
                              label="工號"
                              v-model="editedItem.emp_id"
                              :rules="[requiredRule, empIDRule]"
                              variant="underlined"
                              :readonly="formTitle === '編輯資料'"
                              ref="EmpIDInput"
                              @update:focused="checkUsers"
                              @keypress="handleKeyDown"
                            />
                          </v-col>
                          <v-col cols="12" sm="3">
                            <v-text-field
                              label="姓名"
                              v-model="editedItem.emp_name"
                              :rules="[requiredRule, nameRule]"
                              variant="underlined"
                            />
                          </v-col>
                          <v-col cols="12" sm="6">
                            <v-select
                              label="部門"
                              :items="departments"
                              v-model="editedItem.dep_name"
                              variant="underlined"
                            />
                          </v-col>
                        </v-row>

                        <div class="section-subtitle">群組</div>
                        <div class="role-block">
                          <v-btn-toggle
                            v-model="toggle"
                            variant="outlined"
                            divided
                            color="#6200ea"
                            density="compact"
                            class="role-toggle"
                          >
                            <v-btn
                              v-for="(role, index) in roles"
                              :key="index"
                              :value="role"
                              class="role-btn"
                            >
                              <span class="fa-stack role-icon">
                                <i
                                  class="fa-solid fa-user-lock fa-stack-2x"
                                  style="color: #1565C0; font-size: 1.2em; position: absolute; transform: translate(-10%, 30%);"
                                ></i>
                                <i
                                  :class="role.iconClass"
                                  style="color: #EF5350; font-weight: 800; position: absolute; transform: translate(50%, -25%);"
                                ></i>
                              </span>
                            </v-btn>
                          </v-btn-toggle>

                          <div class="role-text">
                            目前群組：{{ toggle }}
                          </div>
                        </div>

                        <div v-if="editedIndex != -1" class="password-reset-block">
                          <div class="password-reset-title">
                            重設密碼為預設值 <span class="password-note">(a12345)</span>
                          </div>
                          <v-radio-group
                            v-model="password_reset"
                            hide-details
                            inline
                            class="password-reset-radio"
                          >
                            <v-radio value="no" label="否"></v-radio>
                            <v-radio value="yes" label="是"></v-radio>
                          </v-radio-group>
                        </div>
                      </div>
                    </v-col>

                    <!-- 右側：權限 -->
                    <v-col cols="12" lg="5">
                      <div class="dialog-section">
                        <div class="section-title">功能權限</div>
                        <div class="custom-card permission-card">
                          <tree-view
                            color="blue"
                            :items="treeViewItems"
                            v-model="treeViewSelection"
                            dense
                            open-all
                            @select="handleSelect"
                          />
                        </div>
                      </div>
                    </v-col>
                  </v-row>

                  <!-- 下半部：請假 -->
                  <v-row class="leave-row">
                      <div class="dialog-section leave-section">
                        <div class="section-title">員工請假</div>
                        <v-row
                          class="mt-0 mb-0 row-hidden"
                          style="min-height:48px; height:48px; flex-wrap:nowrap;"
                        >
                          <v-col cols="8" class="d-flex align-center pt-0 pb-0">
                            <div class="leave-date-wrap">
                              <v-menu
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
                                    label="請假日期與時間"
                                    :model-value="leaveFormattedRange"
                                    readonly
                                    variant="underlined"
                                    density="compact"
                                    style="margin-top:20px;"
                                    placeholder="yyyy-mm-dd HH:mm:ss ~ yyyy-mm-dd HH:mm:ss"
                                    prepend-icon="mdi-calendar-clock"
                                    class="dateicon leave-date-field"
                                    clearable
                                    @click:clear="clearLeaveRange"
                                  />
                                </template>

                                <div class="leave-datepicker">
                                  <VueDatePicker
                                    v-model="editedItem.leave_range"
                                    range
                                    :enable-time-picker="true"
                                    :time-picker-inline="true"
                                    :minutes-increment="1"
                                    :seconds-increment="1"
                                    :inline="true"
                                    :auto-apply="true"
                                    locale="zh-TW"
                                    week-num-name=""
                                    :day-names="['星期一','星期二','星期三','星期四','星期五','星期六','星期日']"
                                  />
                                </div>
                              </v-menu>
                            </div>
                          </v-col>

                          <v-col cols="4" class="d-flex align-center pt-0 pb-0">
                            <div class="leave-type-wrap">
                              <div class="section-subtitle leave-type-title">假別</div>

                              <v-radio-group
                                v-model="editedItem.leave_type"
                                hide-details
                                class="leave-radio-group leave-radio-grid"
                                style="position:relative; right:50px;"
                              >
                                <v-row no-gutters>
                                  <v-col
                                    cols="4"
                                    v-for="item in leaveTypes"
                                    :key="item.value"
                                    class="py-1"
                                  >
                                    <v-radio
                                      :label="item.label"
                                      :value="item.value"
                                    />
                                  </v-col>
                                </v-row>
                              </v-radio-group>

                              <v-row>
  <v-col cols="12" md="7">
    <v-select
      label="代理人"
      v-model="editedItem.delegate_emp_id"

      :items="users.filter(u => u.emp_id !== editedItem.emp_id)"

      item-title="emp_name"
      item-value="emp_id"
      variant="underlined"
      density="compact"
      prepend-icon="mdi-account-switch"
      placeholder="選擇代理人"
    />
  </v-col>
</v-row>
                            </div>
                          </v-col>
                        </v-row>

                        <v-row class="leave-info-row">
                          <v-col cols="12" md="4">
                            <div class="leave-info-item">
                              <span class="leave-info-label">開始：</span>
                              <span>{{ editedItem.leave_start || '未設定' }}</span>
                            </div>
                          </v-col>
                          <v-col cols="12" md="4">
                            <div class="leave-info-item">
                              <span class="leave-info-label">結束：</span>
                              <span>{{ editedItem.leave_end || '未設定' }}</span>
                            </div>
                          </v-col>
                        </v-row>
                      </div>

                  </v-row>

                  <v-row justify="center" class="dialog-action-row">
                    <v-col cols="auto">
                      <v-btn text @click="close" class="btns">
                        <i class="fa-regular fa-circle-xmark" />
                        取消
                      </v-btn>
                    </v-col>
                    <v-col cols="auto">
                      <v-btn text @click="save" class="btns" :disabled="!validateFields">
                        <i class="fa-regular fa-circle-check" />
                        確定
                      </v-btn>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-dialog>

            <v-dialog v-model="dialogDelete" max-width="360px">
              <v-card>
                <v-card-title class="text-h5" align="center">
                  確定刪除這筆資料?<br />
                  (資料刪除後, 即為離職人員!)
                </v-card-title>
                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn color="blue darken-1" text @click="closeDelete">取消</v-btn>
                  <v-btn color="blue darken-1" text @click="deleteItemConfirm">刪除</v-btn>
                  <v-spacer></v-spacer>
                </v-card-actions>
              </v-card>
            </v-dialog>

            <v-dialog v-model="rightDialog" transition="dialog-bottom-transition" max-width="500">
              <v-card>
                <v-toolbar color="primary" dark>錯誤訊息!</v-toolbar>
                <v-card-text>
                  <div class="text-h4 pa-12">使用這項功能, 請通知管理人員...</div>
                </v-card-text>
                <v-card-actions class="justify-end">
                  <v-spacer></v-spacer>
                  <v-btn text @click="rightCloseFun">取消</v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </v-toolbar>
        </template>

        <template v-slot:item.emp_perm="{ item }">
          {{ getEmpPermText(item.emp_perm) }}
        </template>

        <template v-slot:item.actions="{ item }">
          <v-icon small class="mr-2" @click="editItem(item)" style="color: blue;">
            mdi-pencil
          </v-icon>
          <v-icon small @click="deleteItem(item)" style="color: red;">
            mdi-delete
          </v-icon>
        </template>

        <template #no-data>
          <strong><span style="color: red;">目前沒有資料</span></strong>
        </template>
      </v-data-table>
    </v-card>
<!--

  </v-row>
-->
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onBeforeMount, nextTick } from 'vue';
import { TreeView } from "vue-tree-view";

import "vue-tree-view/dist/style.css";

import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
dayjs.extend(isSameOrBefore);             //啟用 plugin

import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

import { useRoute } from 'vue-router'; // Import useRouter

import { myMixin } from '../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { apiOperation }  from '../mixins/crud.js';

import { departments }  from '../mixins/crud.js';
import { desserts2 }  from '../mixins/crud.js';
import { empPermMapping, roleMappings, treeViewItems } from '../mixins/MenuConstants.js';

import { parseRoutingPriv, serializeRoutingPriv } from '../mixins/MenuConstants'

// 使用 apiOperation 函式來建立 API 請求
const listDepartments = apiOperation('get', '/listDepartments');

const listUsers2 = apiOperation('get', '/listUsers2');
const removeUser = apiOperation('post', '/removeUser');
const updateUser = apiOperation('post', '/updateUser');
const register = apiOperation('post', '/register');

//=== component name ==
defineComponent({
  name: 'Employer'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
  showFooter: Boolean
});

//=== data ===
const nameRule = value => value.length <= 10 || '長度太長!';
const requiredRule = value => !!value || '必須輸入資料!';

const empIDRule = value => {
  return /^[0-9]{7}$/.test(value) || /^[0-9]{8}$/.test(value) && value[0] === '0'
    ? true
    : '必須是7或8(0)位數!';
};

const route = useRoute(); // Initialize router

const headers = [
  { title: '工號', sortable: true, value: 'emp_id' },
  { title: '姓名', sortable: false, value: 'emp_name'},
  { title: '部門', sortable: true, value: 'dep_name' },
  { title: '群組', sortable: false, value: 'emp_perm' },
  { title: '請假', value: 'is_user_delegate', width: 110 },
  { title: 'Actions', sortable: false, value: 'actions' },
];

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: 25, title: '25' },
  { value: -1, title: '全部' }
];

const roles = [
  { value: '系統人員', iconClass: 'fa-solid fa-1' },
  { value: '管理人員', iconClass: 'fa-solid fa-2' },
  { value: '主管', iconClass: 'fa-solid fa-3' },
  { value: '員工', iconClass: 'fa-solid fa-4' },
];

const leaveTypes = [
  { label: '事假', value: 'personal' },
  { label: '病假', value: 'sick' },
  { label: '特休', value: 'annual' },
  { label: '公假', value: 'official' },
  { label: '其他', value: 'other' },
];

const EmpID_max_length = 8;       //員工編號最多數字個數

const currentUser = ref({});
const permDialog = ref(false);
const rightDialog = ref(false);
const showExplore = ref(false);

const EmpIDInput = ref(null);

const users = ref([]);          // for 代理人

const dialog = ref(false);
const dialogDelete = ref(false);
const totalItems = ref(0);
const toggle= ref('');

const treeViewSelection = ref([]);
const currentSetting = ref(new Array(26).fill(0));
//const initialSelection = Array(26).fill(0).map((_, i) => (roleMappings['員工'].includes(i + 1) ? 1 : 0));
const password_reset = ref('no');
const editedIndex = ref(-1);

const editedItem = reactive({
  emp_id: '',
  emp_name: '',
  dep_name: '',
  emp_perm: 4,    // member
  routingPriv: '',
  password_reset: 'no',

  // ===== 員工請假 =====
  leave_type: '',               // 假別
  leave_range: null,            // [startDate, endDate]
  leave_start: '',              // yyyy-mm-dd HH:mm:ss
  leave_end: '',                // yyyy-mm-dd HH:mm:ss
  delegate_emp_id: '',
});

const defaultItem = reactive({
  emp_id: '',
  emp_name: '',
  dep_name: '',
  emp_perm: 4,    // member
  routingPriv: '',
  password_reset: 'no',

  // ===== 員工請假 =====
  leave_type: '',
  leave_range: null,
  leave_start: '',
  leave_end: '',
});

const pagination = reactive({
  itemsPerPage: 10, // 預設值, rows/per page
  page: 1,
});

//=== watch ===
/*
watch(() => editedItem.leave_range,  (newVal) => {
    if (!newVal || !Array.isArray(newVal) || newVal.length !== 2) {
      editedItem.leave_start = '';
      editedItem.leave_end = '';
      return;
    }

    //editedItem.leave_start = newVal[0] ? formatDateTime(newVal[0]) : '';
    //editedItem.leave_end = newVal[1] ? formatDateTime(newVal[1]) : '';

    editedItem.leave_start = dayjs(newVal[0]).format('YYYY-MM-DD HH:mm:ss')
    editedItem.leave_end = dayjs(newVal[1]).format('YYYY-MM-DD HH:mm:ss')
  },
  { deep: true }
);
*/

const pad22 = (n) => String(n).padStart(2, '0')

const formatDateTime22 = (date) => {
  if (!date) return ''
  const d = new Date(date)
  return `${d.getFullYear()}-${pad22(d.getMonth() + 1)}-${pad22(d.getDate())} ${pad22(d.getHours())}:${pad22(d.getMinutes())}:${pad22(d.getSeconds())}`
}

watch(() => editedItem.leave_range, (newVal) => {
    if (!newVal || !Array.isArray(newVal) || newVal.length !== 2) {
      editedItem.leave_start = ''
      editedItem.leave_end = ''
      return
    }

    editedItem.leave_start = newVal[0] ? formatDateTime22(newVal[0]) : ''
    editedItem.leave_end = newVal[1] ? formatDateTime22(newVal[1]) : ''
  },
  { deep: true }
)

// ===

watch(currentUser, (newUser) => {
  if (newUser.perm < 1) {
    permDialog.value = true;
  }
});

watch(toggle, (newVal) => {
  if (editedIndex.value == -1) {
    console.log("watch:", toggle.value, newVal);

    // 使用映射表來更新選擇
    const selection = roleMappings[newVal] || [];
    updateSelection(selection);
  }
});

watch(() => editedItem.emp_perm, (newValue) => {
    toggle.value = empPermMapping[newValue];
  }
);

watch(dialog, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
});

watch(  () => treeViewSelection.value,
  (newVal) => {
    updateSelection(newVal || [])
  },
  { deep: true }
)

//=== computed ===
const formTitle = computed(() => (editedIndex.value === -1 ? '新增資料' : '編輯資料'));

/*
const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)'
}));
*/
const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 220px)' : 'calc(100vh - 160px)'
}));

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

/*
const validateFields = computed(() => {
  // 新增模式先不擋
  if (editedIndex.value === -1) return false

  const original = desserts2.value[editedIndex.value] || {}

  // 1. 部門 / 群組 / 重設密碼 有修改
  const depChanged = editedItem.dep_name !== original.dep_name

  const roleChanged =
    Number(editedItem.emp_perm) !== Number(original.emp_perm)

  const passwordChanged = password_reset.value === 'yes'

  // 2. 功能權限有修改
  const originalRoutingPriv = String(original.routingPriv || '')
    .split(',')
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))
    .sort((a, b) => a - b)

  const currentRoutingPriv = [...currentSetting.value]
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))
    .sort((a, b) => a - b)

  const permissionChanged =
    originalRoutingPriv.length !== currentRoutingPriv.length ||
    originalRoutingPriv.some((v, i) => v !== currentRoutingPriv[i])

  const basicChanged = depChanged || roleChanged || passwordChanged || permissionChanged

  // 2. 請假資料都有設定
  const leaveFullySet =
    !!editedItem.leave_start &&
    !!editedItem.leave_end &&
    !!editedItem.leave_type &&
    !!editedItem.delegate_emp_id

  return basicChanged || leaveFullySet
})
*/

const sameNumberArray = (a = [], b = []) => {
  const arr1 = [...a]
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))
    .sort((x, y) => x - y)

  const arr2 = [...b]
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))
    .sort((x, y) => x - y)

  return arr1.length === arr2.length && arr1.every((v, i) => v === arr2[i])
}

const validateFields = computed(() => {
  // 新增模式先不擋
  if (editedIndex.value === -1) return false

  const original = desserts2.value[editedIndex.value] || {}

  // 1. 部門 / 群組 / 重設密碼 有修改
  const depChanged = editedItem.dep_name !== original.dep_name

  const roleChanged =
    Number(editedItem.emp_perm) !== Number(original.emp_perm)

  const passwordChanged = password_reset.value === 'yes'

  // 2. 功能權限有修改
  const originalRoutingPriv = String(original.routingPriv || '')
    .split(',')
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))

  const currentRoutingPriv = [...currentSetting.value]
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))

  const permissionChanged =
    !sameNumberArray(originalRoutingPriv, currentRoutingPriv)

  const basicChanged =
    depChanged || roleChanged || passwordChanged || permissionChanged

  // 3. 請假資料都有設定
  const leaveFullySet =
    !!editedItem.leave_start &&
    !!editedItem.leave_end &&
    !!editedItem.leave_type &&
    !!editedItem.delegate_emp_id

  return basicChanged || leaveFullySet
})

//=== mounted ===
onMounted(() => {
  console.log("Employer, mounted()...");

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
});

//=== unmounted ===

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();
});

//=== method ===

const pad2 = (n) => String(n).padStart(2, '0');

const formatDateTime = (date) => {
  if (!date) return '';
  const d = new Date(date);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
};

const leaveFormattedRange = computed(() => {
  if (!editedItem.leave_range || !Array.isArray(editedItem.leave_range) || editedItem.leave_range.length !== 2) {
    return '';
  }

  const [start, end] = editedItem.leave_range;
  if (!start || !end) return '';

  return `${formatDateTime(start)} ~ ${formatDateTime(end)}`;
});

const clearLeaveRange = () => {
  editedItem.leave_range = null;
  editedItem.leave_start = '';
  editedItem.leave_end = '';
};

const initialize = async () => {
  console.log("initialize()...")

  await listUsers2();
  await listDepartments();

  users.value = desserts2.value;
};

// 輸入框失去焦點時補全0
const normalizeEmpId = (focused) => {
  if (!focused) {
    if (editedItem.emp_id.length == 7) {
      editedItem.emp_id = editedItem.emp_id.padStart(8, '0');
    }
  }
};

const close = () => {
    console.log("close()");

    dialog.value = false;
    showExplore.value = false;
    editedIndex.value = -1;
    Object.assign(editedItem, defaultItem);
};

/*
const save = () => {
  console.log("save(),", toggle.value);

  editedItem.emp_perm = parseInt(getEmpPermKey(toggle.value));
  updateSelection(treeViewSelection.value);

  // 取得物件的值並轉換為陣列
  let valuesArray = Object.keys(currentSetting.value).map(key => currentSetting.value[key]);
  // 轉換為以逗號分隔的字串
  let valuesString = valuesArray.join(',');
  editedItem.routingPriv = valuesString
  console.log("editedItem:", editedItem);

  if (editedIndex.value > -1) {
    updateItem(editedItem);
    Object.assign(desserts2.value[editedIndex.value], editedItem);
  } else {
    createItem(editedItem);
    desserts2.value.push({ ...editedItem });
  }
  close();
}
*/

const save = async () => {
  const hasAnyLeaveField =
    !!editedItem.leave_start ||
    !!editedItem.leave_end ||
    !!editedItem.leave_type ||
    !!editedItem.delegate_emp_id

  const leaveFullySet =
    !!editedItem.leave_start &&
    !!editedItem.leave_end &&
    !!editedItem.leave_type &&
    !!editedItem.delegate_emp_id

  if (hasAnyLeaveField && !leaveFullySet) {
    alert('請假資料需同時填寫：開始時間、結束時間、假別、代理人工號')
    return
  }

  try {
    if (editedIndex.value > -1) {
      await updateItem(editedItem)
    } else {
      await createItem(editedItem)
    }

    await initialize()
    close()
  } catch (err) {
    console.error('save failed =', err)
    console.error('save failed status =', err?.response?.status)
    console.error('save failed data =', err?.response?.data)
    alert(err?.response?.data?.message || '儲存失敗')
  }
}

const reverseEmpPermMapping = Object.fromEntries(
  Object.entries(empPermMapping).map(([key, value]) => [value, key])
);

const getEmpPermText = (emp_perm) => {
  return empPermMapping[emp_perm] || '未知';
};

const getEmpPermKey = (permText) => {
  return reverseEmpPermMapping[permText] || '未知';
};

const updateItem = async (object) => {
  const leaveFullySet =
    !!object.leave_start &&
    !!object.leave_end &&
    !!object.leave_type &&
    !!object.delegate_emp_id

  const payload = {
    emp_id: object.emp_id,
    emp_name: object.emp_name,
    dep_name: object.dep_name,
    emp_perm: object.emp_perm,
    //routingPriv: currentSetting.value.join(','),
    routingPriv: serializeRoutingPriv(currentSetting.value),
    password_reset: password_reset.value,

    leave_start: leaveFullySet ? object.leave_start : '',
    leave_end: leaveFullySet ? object.leave_end : '',
    leave_type: leaveFullySet ? object.leave_type : '',
    delegate_emp_id: leaveFullySet ? object.delegate_emp_id : '',
  }

  console.log('updateUser payload =', JSON.stringify(payload, null, 2))

  return await updateUser(payload)
}

const createItem = (object) => {
  console.log("createItem(),", object);

  const defaultPassword='a12345';
  let payload= {
    emp_id: object.emp_id,
    emp_name: object.emp_name,
    password: defaultPassword,
    dep_name: object.dep_name,
    emp_perm: object.emp_perm,
    routingPriv: currentSetting.value.join(','),    // 轉換為以逗號分隔的字串

    leave_type: object.leave_type,
    leave_start: object.leave_start,
    leave_end: object.leave_end,
  };

  register(payload).then(status => {
    status && (editedItem = Object.assign({}, defaultItem));
  });
};

const editItem = (item) => {
  console.log("editItem()...")

  editedIndex.value = desserts2.value.indexOf(item);
  Object.assign(editedItem, item);
  console.log("editedItem.routingPriv:", editedItem.routingPriv)

  if (item.leave_start && item.leave_end) {
    editedItem.leave_range = [new Date(item.leave_start), new Date(item.leave_end)];
  } else {
    editedItem.leave_range = null;
  }

  //let routingPrivArray = editedItem.routingPriv.split(',').map(Number);
  //console.log("routingPrivArray,", routingPrivArray)

  //let routingPrivArray = String(editedItem.routingPriv || '')
  //.split(',')
  //.map(v => Number(v))
  //.filter(v => !Number.isNaN(v))

  // 真正存檔的是葉節點
  //currentSetting.value = [...routingPrivArray].sort((a, b) => a - b)

  //treeViewSelection.value = Array(26).fill(0);
  //treeViewSelection.value = getSelectedIds(treeViewItems.value, routingPrivArray);

  // UI 勾選要把父節點也補回去
  //treeViewSelection.value = expandSelectionWithParents(
  //  treeViewItems.value,
  //  currentSetting.value
  //)

  let routingPrivArray = parseRoutingPriv(editedItem.routingPriv)
  currentSetting.value = [...routingPrivArray]

  treeViewSelection.value = expandSelectionWithParents(
    treeViewItems.value,
    currentSetting.value
  )

  console.log("treeViewSelection:", treeViewSelection.value)
  editedItem.password_reset = 'no'

  editedItem.leave_end = item.leave_end || ''
  editedItem.leave_type = item.leave_type || ''
  editedItem.delegate_emp_id = item.delegate_emp_id || ''

  dialog.value = true;
}

const deleteItem = (item) => {
  editedIndex.value = desserts2.value.indexOf(item);
  Object.assign(editedItem, desserts2.value[editedIndex.value]);
  dialogDelete.value = true;
}

const deleteItemConfirm = () => {
  removeItem(editedItem.emp_id);

  desserts2.value.splice(editedIndex.value, 1);
  closeDelete();
}

const closeDelete=() => {
  dialogDelete.value = false;
}

const permCloseFun = () => {
  permDialog.value = false;
}

const rightCloseFun = () => {
  rightDialog.value = false;
}

const handleSelect = (node) => {
  if (node.disabled) {
    return;
  }
  // 如果未禁用，則將其添加到選擇列表中
  if (!treeViewSelection.value.includes(node.id)) {
    treeViewSelection.value.routingPriv.push(node.id);
  }
};

/*
const updateSelection = (newSelection) => {
  console.log("updateSelection,", newSelection)

  treeViewSelection.value = [];
  updateSetting(newSelection);
  console.log("currentSetting:", currentSetting.value);
  nextTick().then(() => {
    treeViewSelection.value = newSelection;
  });
};
*/

const updateSelection = (selection) => {
  console.log('updateSelection,', selection)

  // 先只取葉節點，作為真正要存回 DB 的 routingPriv
  const leafIds = extractLeafIdsFromSelection(treeViewItems.value, selection)

  // 再補父節點，作為 UI 顯示用勾選狀態
  const fullSelection = expandSelectionWithParents(treeViewItems.value, leafIds)

  if (!sameNumberArray(treeViewSelection.value, fullSelection)) {
    treeViewSelection.value = fullSelection
  }

  currentSetting.value = [...leafIds].sort((a, b) => a - b)

  console.log('currentSetting:', currentSetting.value)
}

const updateSetting = (arr) => {
  currentSetting.value = currentSetting.value.map(() => 0);   // 將 Setting 陣列重置為全 0

  arr.forEach((index) => {    // 根據 kk 中的數字設置 Setting 中的對應位置為 1
    if (index >= 1 && index <= currentSetting.value.length) {
      currentSetting.value[index - 1] = 1;
    }
  });
};

const removeItem = (id) => {  //依user id來刪除後端table資料
  console.log("removeItem(),", id);

  let payload= {ID: id};
  //removeUser(payload).then(status => {
  //  if (status) {
  //    Object.assign(editedItem, defaultItem);
  //  }
  //});
  removeUser(payload)
  .finally(() => {
    Object.assign(editedItem, defaultItem);
  });
};

const checkUsers = (focused) => {
  // 只在失焦時檢查
  if (focused) return

  // 編輯模式不檢查工號重複
  if (editedIndex.value !== -1) return

  //if (!focused) { // 當失去焦點時
  //  console.log("checkUser()...");

  const empId = String(editedItem.emp_id || '').trim()
  if (!empId) return

    if (editedItem.emp_id.length == 7) {
      editedItem.emp_id = editedItem.emp_id.padStart(8, '0');
    }

    //let foundDessert = desserts2.value.find(dessert => dessert.emp_id === registerUser.empID);
    let foundDessert = desserts2.value.find(dessert => String(dessert.emp_id || '') === empId);
    console.log("foundDessert:",foundDessert);
    if (foundDessert) {
      if (editedItem.emp_id !='') {
        let temp_info = snackbar_info.value = '錯誤, 工號' + editedItem.emp_id + '重複!';
        showSnackbar(temp_info, 'red accent-2');

        editedItem.emp_id = '';
      }

      nextTick(() => {
        EmpIDInput.value.focus();
      })
    }
  //}
};

const handleKeyDown = (event) => {
  const inputChar = event.key;

  const caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when you press the keyboard CapsLock key

  // 允許左右方向鍵、backspace和delete鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }

  const inputValue = event.target.value || ''; // 确保 inputValue 是字符串

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar) || inputValue.length >= EmpID_max_length) {
    event.preventDefault();
  }
};

// 遞歸處理樹狀結構
const getSelectedIds = (items, privArray) => {
  let selectedIds = [];
  let index = 0;

  const traverse = (itemList) => {
    console.log("itemList:", itemList);

    itemList.forEach((item) => {
      if (privArray[index] === 1) {
        selectedIds.push(item.id);
      }
      index++;
      if (item.children) {
        traverse(item.children);
      }
    });
  };

  traverse(items);
  return selectedIds;
}

const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const isLeafNode = (node) => {
  return !node.children || node.children.length === 0
}

const getAllLeafIds = (items = []) => {
  const result = []

  const walk = (nodes) => {
    for (const node of nodes || []) {
      if (isLeafNode(node)) {
        result.push(Number(node.id))
      } else {
        walk(node.children)
      }
    }
  }

  walk(items)
  return result
}

const extractLeafIdsFromSelection = (items = [], selectedIds = []) => {
  const selectedSet = new Set((selectedIds || []).map(v => Number(v)))
  const result = []

  const walk = (nodes) => {
    for (const node of nodes || []) {
      const nodeId = Number(node.id)

      if (isLeafNode(node)) {
        if (selectedSet.has(nodeId)) {
          result.push(nodeId)
        }
      } else {
        walk(node.children)
      }
    }
  }

  walk(items)
  return result
}

const expandSelectionWithParents = (items = [], selectedIds = []) => {
  const selectedSet = new Set((selectedIds || []).map(v => Number(v)))

  const walk = (nodes) => {
    let allLeafSelectedUnderThisLevel = true

    for (const node of nodes || []) {
      const nodeId = Number(node.id)

      if (isLeafNode(node)) {
        if (!selectedSet.has(nodeId)) {
          allLeafSelectedUnderThisLevel = false
        }
      } else {
        const allChildrenSelected = walk(node.children)

        if (allChildrenSelected) {
          selectedSet.add(nodeId)   // 補父節點
        } else {
          allLeafSelectedUnderThisLevel = false
        }
      }
    }

    return allLeafSelectedUnderThisLevel
  }

  walk(items)

  return [...selectedSet]
    .map(v => Number(v))
    .filter(v => !Number.isNaN(v))
    .sort((a, b) => a - b)
}
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

@import "../styles/variables.scss";

.page_contain {
  position: fixed;
  left: 0px !important;
  top: 60px !important;       // 確保在導航欄下方
  bottom: 60px !important;    // 確保在頁腳上方
  padding: 0px 10px;
  //width: 100vw;               // 視窗寬度
  width: 100%;
  margin: 0;
  overflow-y: auto;           // 添加scrollbar，防止內容溢出
  //overflow-y: hidden;
  overflow-x:hidden;
  overflow: hidden;

}

:deep(.v-table__wrapper) {
  scrollbar-width: none;
}

:deep(.v-table__wrapper::-webkit-scrollbar) {
  width: 0;
  display: none;
}

.table_border_radius {
  border-radius: 0px 0px $DATA_TABLE_BORDER_RADIUS $DATA_TABLE_BORDER_RADIUS;
}

.tree-view-item.disabled, .tree-view-node.disabled {
  pointer-events: none;
  color: gray;
  opacity: 0.6;
}
:deep(.treeview-node__content span) {
  font-size: 14px;
  font-weight: 600;
  font-family: 'cwTeXYen', sans-serif;
}
/*
.tree-view-item[aria-disabled="true"] {
  pointer-events: none;
  color: gray;
  opacity: 0.6;
}

.disabled {
  color: grey;
  opacity: 0.6;
  pointer-events: none;
  cursor: not-allowed;
}
*/
.card_container {
   // width: 100%;
   // max-width: 400px;
   // max-height: 251px;
   // height: 54vw;
  padding: 20px;
}

#ccsingle {
  position: absolute;
  right: 15px;
  top: 20px;
}

#ccsingle svg {
  width: 100px;
max-height: 60px;
}

.creditcard svg#cardfront {
  width: 100%;
  height: auto;
  box-shadow: 1px 5px 6px 0px black;
  border-radius: 40px;
}

.creditcard .lightcolor, .creditcard .darkcolor {
  transition: fill .5s;
}

.creditcard .grey {
  fill: #bdbdbd;
}

.creditcard .greydark {
    //fill: #616161;
  fill: #E3F2FD
}

// FRONT OF CARD
#cardfront .st2 {
  fill: #FFFFFF;
}

.form_container {
  margin-top: 20px; /* Optional: Add some margin to separate form from SVG */
}
/*
:deep(.v-overlay__content) {
    //overflow: hidden !important;
  overflow-y: hidden !important;
  top: 20px !important;
  border-radius: 40px;
}
*/
:deep(.v-overlay__content) {
  overflow-y: hidden !important;
  top: 20px !important;
  border-radius: 0 !important;
}

.card-no-padding .v-card {
  margin: 0 !important;
  padding: 0 !important;
}

:deep(.v-card-text .card_container) {
  padding: 0px;
}
/*
.custom-card {
	//background-color: #B3E5FC;
	box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.1);
  //box-shadow: inset 0px 0px 0px 1px #2c2c2c, 0px 10px 20px rgba(0, 0, 0, 0.1);
	border-radius: 10px;
	max-width: 240px;
  max-height: 240px;
	transition: all 0.5s ease;
  overflow-x: hidden;
  overflow-y: auto;
  text-align: justify;
  //border: 1px solid #1a1a1a;
  //border: none;
}
*/
.custom-card {
  box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.1);
  border-radius: 0;
  width: 100%;
  max-width: none;
  max-height: 360px;
  transition: all 0.5s ease;
  overflow-x: hidden;
  overflow-y: auto;
  text-align: justify;
}

// 滾動條樣式
.custom-card::-webkit-scrollbar {
  width: 12px;  // 滾動條寬度
}

.custom-card::-webkit-scrollbar-track {
  background: #B3E5FC;  // 滾動條軌道顏色
}

.custom-card::-webkit-scrollbar-thumb {
  background: #81D4FA;    // 滾動條滑塊顏色
  border-radius: 10px;        // 滾動條滑塊圓角
}

// 滾動條滑塊懸停樣式
.custom-card::-webkit-scrollbar-thumb:hover {
  background: #4FC3F7;    // 滾動條滑塊懸停顏色
}

.no-rounded-icon-btn .v-btn__icon {
  border-radius: 0 !important;
}

//.v-input--custom-text-input-density  {
//    //--v-input-control-height: 30px;
//}
.v-input--custom-text-input-density .v-field--variant-underlined {
  --v-input-control-height: 30px; //change here
  --v-field-padding-top: 0px;
  --v-field-padding-bottom: 0px;
}

.input-with-label {
  display: flex;
  align-items: center;
}

.input-label {
  margin-right: 8px;    // 調整間距
  font-size: 16px;      // 調整字體大小
  color: #000;      // 調整文字顏色
  font-weight: 700;
}

.btns {
  width: 75px;
  //height: 3.077rem;
  //font-size: 1.154rem;
  color: #FFF;
  //font-weight: bold;
  text-align: center;
  background-color: #8BB5D6;
  border-radius: 0.615rem;
  border: none;
  //margin-top: 1.538rem;
  margin-top: 10px !important;
  padding: 0rem 1.538rem;
  transition: border 0.05s ease;
}

.btns:hover {
  border: 1.5px solid white;
}

.my-grid-wrapper {
  display: grid;
  grid-template-columns: repeat(13, 1fr);
  grid-auto-rows: 60px;
  grid-auto-columns: 60px;
  grid-column-gap: 5px;
  grid-row-gap: 10px;
}
.my-grid-box1 {
  grid-column-start: 1;
  grid-column-end: 3;
  grid-row-start: 1;
  grid-row-end: 2;
}
.my-grid-box2 {
  grid-column-start: 3;
  grid-column-end: 5;
  grid-row-start: 1;
  grid-row-end: 2;
}
.my-grid-box3 {
  grid-column-start: 5;
  grid-column-end: 8;
  grid-row-start: 1;
  grid-row-end: 2;
}
.my-grid-box4 {
  grid-column-start: 9;
  grid-column-end: 13;
  grid-row-start: 1;
  grid-row-end: 3;
}

.my-grid-box5 {
  grid-column-start: 3;
  grid-column-end: 8;
  grid-row-start: 2;
  grid-row-end: 3;
}

.my-grid-box6 {
  grid-column-start: 8;
  grid-column-end: 10;
  grid-row-start: 3;
  grid-row-end: 4;
}

.my-grid-box7{
  grid-column-start: 1;
  grid-column-end: 5;
  grid-row-start: 3;
  grid-row-end: 4;
}

.toggle-display {
  //width: 100%;
  //text-align: center;
  //margin-top: 8px;        /* 調整間距 */
  //margin-right: 350px;
  overflow: hidden;
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

/*
.custom-text-field .v-messages__message {
  white-space: nowrap;
  overflow: visible;
  text-overflow: clip;
  max-width: none;
  width: auto;
  position: absolute;
  left: 0;
  right: 0;
}
*/

.leave-card {
  border: 1px solid #BBDEFB;
  background: #F8FBFF;
  border-radius: 12px;
}

.dp-stretch {
  padding: 8px 12px 12px;
  background: white;
}

.leave-radio-group {
  gap: 10px;
}

:deep(.dateicon > .v-input__prepend .v-icon) {
  color: #1976D2;
}

// == new
:deep(.employer-edit-dialog) {
  border-radius: 0 !important;
  overflow: visible !important;
}

:deep(.employer-edit-dialog .v-card) {
  border-radius: 0 !important;
}

.employer-dialog-card {
  border-radius: 0 !important;
}

.dialog-title-bar {
  border-bottom: 1px solid #e0e0e0;
  padding: 14px 20px 12px;
}

.dialog-body {
  padding: 20px 22px 16px !important;
}

.dialog-main-row {
  margin-bottom: 6px;
}

.dialog-section {
  border: 1px solid #e3e8ef;
  padding: 16px 16px 12px;
  background: #fcfdff;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1565c0;
  margin-bottom: 12px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 700;
  color: #455a64;
  margin: 8px 0 10px;
}

.role-block {
  margin-top: 6px;
}

.role-toggle {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.role-btn {
  height: 42px !important;
  width: 48px !important;
  min-width: 48px !important;
  padding: 0 !important;
}

.role-text {
  margin-top: 10px;
  font-size: 15px;
  font-weight: 700;
  color: #37474f;
}

.role-icon {
  font-size: 0.95rem;
}

.role-icon .fa-user-lock {
  font-size: 1rem;
}

.role-icon i:last-child {
  font-size: 0.9rem;
}

.password-reset-block {
  margin-top: 18px;
  padding-top: 12px;
  border-top: 1px dashed #cfd8dc;
}

.password-reset-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 6px;
}

.password-note {
  font-weight: 400;
}
/*
.permission-section {
  //height: 100%;
  //display: flex;
  //flex-direction: column;
  //flex: 1;
}
*/

.permission-card {
  //max-width: none;
  //width: 100%;
  //height: 100%;
  //min-height: 320px;
  //max-height: 360px;
  //border-radius: 0;
  flex: 1;
  width: 100%;
  overflow-y: auto;
  border-radius: 0;
}

.leave-row {
  margin-top: 4px;
}

.leave-section {
  margin-top: 4px;
}

.leave-picker-wrap {
  background: #fff;
  padding: 10px;
}

.leave-type-title {
  margin-top: 2px;
}

.leave-radio-group {
  row-gap: 4px;
}

.leave-info-row {
  margin-top: 6px;
}

.leave-info-item {
  font-size: 14px;
  color: #455a64;
  background: #f5f9ff;
  padding: 10px 12px;
  border-left: 4px solid #90caf9;
}

.leave-info-label {
  font-weight: 700;
  margin-right: 6px;
}

.dialog-action-row {
  margin-top: 8px;
}

.leave-date-wrap {
  min-width: 480px;
  width: 480px;

}

:deep(.v-overlay__content) {
  overflow-x: hidden;
}

.leave-date-field {
  margin-top: 20px;
}

.leave-type-wrap {
  position: relative;
  left: 50px;
  top: 20px;
}

.leave-radio-grid {
  margin-top: 4px;
}

.leave-radio-grid :deep(.v-selection-control-group) {
  width: 100%;
}

.leave-radio-grid :deep(.v-label) {
  font-size: 14px;
}

.leave-radio-grid :deep(.v-selection-control) {
  min-height: 32px;
}

.leave-radio-grid :deep(.v-radio) {
  margin-bottom: 0;
}

//////
.leave-datepicker {
  width: 100%;
  padding: 10px 14px;
  background: white;
}

.leave-datepicker :deep(.dp__main) {
  width: 100%;
}

.leave-datepicker :deep(.dp__calendar_wrap) {
  width: 100%;
}

.leave-datepicker :deep(.dp__calendar) {
  width: 100%;
}

.leave-datepicker :deep(.dp__month_year_row) {
  width: 100%;
}

.leave-datepicker :deep(.dp__week_days) {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.leave-datepicker :deep(.dp__calendar_row) {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

:deep(.dp__instance_calendar) {
  width: 480px !important;
  min-width: 480px !important;
}

.employer-main-card {
  height: calc(100% - 16px);
  overflow: hidden;
}

// ***
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

</style>
