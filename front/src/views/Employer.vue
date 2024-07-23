<template>
<div class="container">
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
    {{ snackbar_info }}
    <template v-slot:actions>
      <v-btn color="#adadad" @click="snackbar = false">
        <v-icon dark>mdi-close-circle</v-icon>
      </v-btn>
    </template>
  </v-snackbar>

  <v-row align="center" justify="center" v-if="currentUser.perm >= 1">
    <v-card width="50vw" class="pa-md-4 mt-5 mx-lg-auto">
      <v-data-table
        :headers="headers"
        :items="desserts"
        class="elevation-1"
        :options.sync="pagination"
        :footer-props="{ itemsPerPageText: '每頁的資料筆數' }"
      >
        <template v-slot:top>
          <v-toolbar flat>
            <v-toolbar-title>員工資料</v-toolbar-title>
            <v-divider class="mx-4" inset vertical></v-divider>
            <v-spacer></v-spacer>
            <v-dialog v-model="dialog" max-width="500px" :content-class="temp_css">
              <template v-slot:activator="{ on, attrs }">
                <v-btn color="primary" dark class="mb-2" v-bind="attrs" v-on="on" v-show="currentUser.perm <= 2">
                  <v-icon left dark>mdi-table-plus</v-icon>
                  新增資料
                </v-btn>
              </template>
              <v-card>
                <v-card-title>
                  <span class="text-h5">{{ formTitle }}</span>
                </v-card-title>

                <v-card-text>
                  <v-container>
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field
                          label="員工編號"
                          prepend-icon="mdi-account"
                          v-model="editedItem.emp_id"
                          :readonly="formTitle === '編輯資料'"
                          @focus="fieldFocus"
                        ></v-text-field>
                        <small class="msgErr" v-text="IDErrMsg"></small>
                      </v-col>

                      <v-col cols="12" md="4">
                        <v-text-field
                          label="姓名"
                          prepend-icon="mdi-account-edit"
                          v-model="editedItem.emp_name"
                          @focus="fieldFocus"
                        ></v-text-field>
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-select
                          :items="departments"
                          label="組別"
                          prepend-icon="mdi-account-group"
                          v-model="editedItem.emp_dep"
                          @focus="fieldFocus"
                        ></v-select>
                      </v-col>
                    </v-row>

                    <v-row v-if="editedIndex != -1">
                      <v-col cols="12" md="2"></v-col>
                      <v-col cols="12" md="9">
                        <v-subheader style="margin-bottom: 0; height: 18px; font-size: 18px;">
                          <span style="font-weight: bold;">重設密碼預設值</span>
                          <span style="font-weight: normal;">(a12345678)</span>
                        </v-subheader>
                        <v-radio-group
                          v-model="password_reset"
                          hide-details
                          row
                          style="margin-top: 0; position: relative; left: 15px;"
                        >
                          <v-radio value="no" label="否"></v-radio>
                          <v-radio value="yes" label="是"></v-radio>
                        </v-radio-group>
                      </v-col>
                      <v-col cols="12" md="1"></v-col>
                    </v-row>
                  </v-container>
                </v-card-text>

                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn color="blue darken-1" text @click="close">取消</v-btn>
                  <v-btn color="blue darken-1" text @click="save" :disabled="checkDataForSaveButton">確定</v-btn>
                </v-card-actions>
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

            <v-dialog v-show="rightDialog" v-model="rightDialog" transition="dialog-bottom-transition" max-width="500">
              <v-card>
                <v-toolbar color="primary" dark>錯誤訊息!</v-toolbar>
                <v-card-text>
                  <div class="text-h4 pa-12">使用這項功能, 請通知管理人員...</div>
                </v-card-text>
                <v-card-actions class="justify-end">
                  <v-spacer></v-spacer>
                  <v-btn text @click="rightCloseFun"> 取消 </v-btn>
                </v-card-actions>
              </v-card>
            </v-dialog>
          </v-toolbar>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <v-icon small class="mr-2" @click="editItem(item)" style="color: blue;">
            mdi-pencil
          </v-icon>
          <v-icon small @click="deleteItem(item)" style="color: red;">
            mdi-delete
          </v-icon>
        </template>

        <template v-slot:no-data>
          <strong><font color="red">目前沒有資料</font></strong>
        </template>
      </v-data-table>
    </v-card>
  </v-row>

  <v-row align="center" justify="space-around" v-else>
    <v-dialog v-model="permDialog" transition="dialog-bottom-transition" max-width="500">
      <v-card>
        <v-toolbar color="primary" dark>錯誤訊息!</v-toolbar>
        <v-card-text>
          <div class="text-h4 pa-12">權限不足...</div>
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-spacer></v-spacer>
          <v-btn text @click="permCloseFun"> 取消 </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-row>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onBeforeMount } from 'vue';
//import { routerLinks } from '../router/index.js';
import { myMixin } from '../mixins/common.js';

import { apiOperation, showSnackbar, setupListUsersWatcher }  from '../mixins/crud.js';
import { departments }  from '../mixins/crud.js';
import { snackbar, snackbar_info, desserts } from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listDepartments = apiOperation('get', '/listDepartments');
const listUsers = apiOperation('get', '/listUsers');

//=== component name ==
defineComponent({
  name: 'Employer'
});

// === mix ==
const { initAxios } = myMixin();

//=== data ===
const currentUser = ref({});
const permDialog = ref(false);
const rightDialog = ref(false);

const dialog = ref(false);
const dialogDelete = ref(false);

const pagination = reactive({
  itemsPerPage: 10, // 預設值, rows/per page
  page: 1,
});

const delete_confirm_string = ref('確定刪除這筆資料? (資料刪除後, 即為離職人員!)');

const IDErrMsg = ref('');
const nameErrMsg = ref('');

const headers = [
  { text: '工號', sortable: true, value: 'emp_id', width: '20%', align: 'start' },
  { text: '姓名', sortable: false, value: 'emp_name', width: '30%' },
  { text: '部門', sortable: true, value: 'emp_dep', width: '30%' },
  { text: '權限別', sortable: true, value: 'emp_perm', width: '30%' },
  { text: 'Actions', sortable: false, value: 'actions', width: '10%' },
];

const editedIndex = ref(-1);
const editedItem = reactive({
  emp_id: '',
  emp_name: '',
  emp_dep: '',
  emp_perm: 3,    // member
  password_reset: 'no',
});
const defaultItem = reactive({
  emp_id: '',
  emp_name: '',
  emp_dep: '',
  emp_perm: 3,    // member
  password_reset: 'no',
});

const temp_css = ref('add_modalbox');
const password_reset = ref('no');

//=== watch ===
setupListUsersWatcher();

watch(currentUser, (newUser) => {
  if (newUser.perm < 1) {
    permDialog.value = true;
  }
});

//=== computed ===
const formTitle = computed(() => (editedIndex.value === -1 ? '新增資料' : '編輯資料'));

const routeName = computed(() => route.name);

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

  initAxios();
  initialize();
});

//=== method ===
const initialize = () => {
  console.log("initialize()...")

  listUsers();
  listDepartments();
};

  function close() {
    dialog.value = false;
    editedIndex.value = -1;
    Object.assign(editedItem, defaultItem);
  }

  function save() {
    if (editedIndex.value > -1) {
      Object.assign(desserts.value[editedIndex.value], editedItem);
    } else {
      desserts.value.push({ ...editedItem });
    }
    close();
  }

  function editItem(item) {
    editedIndex.value = desserts.value.indexOf(item);
    Object.assign(editedItem, item);
    dialog.value = true;
  }

  function deleteItem(item) {
    editedIndex.value = desserts.value.indexOf(item);
    dialogDelete.value = true;
  }

  function deleteItemConfirm() {
    desserts.value.splice(editedIndex.value, 1);
    closeDelete();
  }

  function closeDelete() {
    dialogDelete.value = false;
  }

  function permCloseFun() {
    permDialog.value = false;
  }

  function rightCloseFun() {
    rightDialog.value = false;
  }

  function checkDataForSaveButton() {
    // Custom validation logic
    return false; // return true if data is invalid, false otherwise
  }

  function fieldFocus() {
    // Custom focus logic
  }
</script>

<style scoped>
  .add_modalbox {
    width: 500px;
  }
</style>
