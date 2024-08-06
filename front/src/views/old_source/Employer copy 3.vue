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

    <v-row align="center" justify="center" v-if="currentUser.perm >= 1">
      <v-card width="60vw" class="pa-md-4 mt-3 pb-2 mx-lg-auto">
        <v-data-table
          :headers="headers"
          :items="desserts"
          class="elevation-1 table_border_radius"
          density="compact"
          v-model:items-per-page="pagination.itemsPerPage"
          :items-per-page-options="footerOptions"
          :items-length="totalItems"
          v-model:page="pagination.page"
          items-per-page-text="每頁的資料筆數"
          :style="['margin-bottom: 5px', tableStyle]"
        >
          <template #top>
            <v-toolbar flat>
              <v-toolbar-title>員工資料</v-toolbar-title>
              <v-divider class="mx-4" inset vertical></v-divider>
              <v-spacer></v-spacer>

              <v-btn @click="dialog = true" color="primary" dark class="mb-2" v-if="currentUser.perm <= 2">
                <v-icon left dark>mdi-table-plus</v-icon>
                新增資料
              </v-btn>

              <v-dialog v-model="dialog" persistent max-width="760">
                <v-card>
                  <v-card-title>
                    <span class="text-h5">{{ formTitle }}</span>
                  </v-card-title>

                  <v-card-text>
                    <v-container>
                      <v-row>
                        <v-col cols="12" md="4">
                          <v-text-field
                            label="工號"
                            prepend-icon="mdi-account"
                            v-model="editedItem.emp_id"
                            :readonly="formTitle === '編輯資料'"
                          />
                        </v-col>
                        <v-col cols="12" md="4">
                          <v-text-field
                            label="姓名"
                            prepend-icon="mdi-account-edit"
                            v-model="editedItem.emp_name"
                          />
                        </v-col>
                        <v-col cols="12" md="4">
                          <v-select
                            :items="departments"
                            label="部門"
                            prepend-icon="mdi-account-group"
                            v-model="editedItem.emp_dep"
                          />
                        </v-col>
                      </v-row>
                      <v-row>
                        <v-col cols="12" md="6">
                          <div class="d-flex align-center flex-column pa-6" style="padding-top: 0px !important;">
                            <v-btn-toggle
                              v-model="toggle"
                              variant="outlined"
                              divided
                              density="compact"
                            >
                              <v-btn style="height: auto; padding: 0; font-size: 8px;">
                                <span class="fa-stack fa-2x">
                                  <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.4em; position: absolute; transform: translate(-10%, 30%);"></i>
                                  <i class="fa-solid fa-1 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                </span>
                              </v-btn>
                              <v-btn style="height: auto; padding: 0; font-size: 8px;" variant="tonal">
                                <span class="fa-stack fa-2x">
                                  <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.4em; position: absolute; transform: translate(-10%, 30%);"></i>
                                  <i class="fa-solid fa-2 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                </span>
                              </v-btn>
                              <v-btn style="height: auto; padding: 0; font-size: 8px;">
                                <span class="fa-stack fa-2x">
                                  <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.4em; position: absolute; transform: translate(-10%, 30%);"></i>
                                  <i class="fa-solid fa-3 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                </span>
                              </v-btn>
                              <v-btn style="height: auto; padding: 0; font-size: 8px;" variant="tonal">
                                <span class="fa-stack fa-2x">
                                  <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.4em; position: absolute; transform: translate(-10%, 30%);"></i>
                                  <i class="fa-solid fa-4 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                </span>
                              </v-btn>
                            </v-btn-toggle>
                          </div>
                        </v-col>
                        <v-col cols="12" md="6">
                          <div style="display: flex">
                            <tree-view
                              color="blue"
                              :items="treeViewItems"
                              v-model="treeViewSelection"
                              dense
                              open-all
                              @select="handleSelect"
                            />
                            {{ treeViewSelection.sort() }}
                          </div>
                        </v-col>
                      </v-row>
                      <v-row v-if="editedIndex != -1">
                        <v-col cols="12" md="2"></v-col>
                        <v-col cols="12" md="9">
                          <v-divider></v-divider>
                          <div class="my-2 text-subtitle-1">
                            <strong>重設密碼預設值</strong> (a12345678)
                          </div>
                          <v-radio-group v-model="passwordReset" row>
                            <v-radio label="否" value="no"></v-radio>
                            <v-radio label="是" value="yes"></v-radio>
                          </v-radio-group>
                        </v-col>
                        <v-col cols="12" md="1"></v-col>
                      </v-row>
                    </v-container>
                  </v-card-text>

                  <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="blue darken-1" text @click="close">取消</v-btn>
                    <!--<v-btn color="blue darken-1" text @click="save" :disabled="checkDataForSaveButton">確定</v-btn>-->
                    <v-btn color="blue darken-1" text @click="save">確定</v-btn>
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
          <template v-slot:item.actions="{ item }">
            <v-icon small class="mr-2" @click="editItem(item)" style="color: blue;">
              mdi-pencil
            </v-icon>
            <v-icon small @click="deleteItem(item)" style="color: red;">
              mdi-delete
            </v-icon>
          </template>
          <template #no-data>
            <v-btn @click="initialize">重整資料</v-btn>
          </template>
        </v-data-table>
      </v-card>
    </v-row>
  </div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onBeforeMount } from 'vue';
import { TreeView } from "vue-tree-view";
import "vue-tree-view/dist/style.css";
//import { routerLinks } from '../router/index.js';
import { useRoute } from 'vue-router'; // Import useRouter

import { myMixin } from '../../mixins/common.js';

import { apiOperation, showSnackbar, setupListUsersWatcher }  from '../../mixins/crud.js';
import { departments }  from '../../mixins/crud.js';
import { snackbar, snackbar_info, snackbar_color, desserts } from '../../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listDepartments = apiOperation('get', '/listDepartments');
const listUsers = apiOperation('get', '/listUsers');

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
const currentUser = ref({});
const permDialog = ref(false);
const rightDialog = ref(false);

const dialog = ref(false);
const dialogDelete = ref(false);
const totalItems = ref(0);
const toggle= ref(2);

const pagination = reactive({
  itemsPerPage: 10, // 預設值, rows/per page
  page: 1,
});

//const delete_confirm_string = ref('確定刪除這筆資料? (資料刪除後, 即為離職人員!)');

const headers = [
  { title: '工號', sortable: true, key: 'emp_id', align: 'start' },
  { title: '姓名', sortable: false, key: 'emp_name', align: 'start' },
  { title: '部門', sortable: true, key: 'dep_name', align: 'start' },
  { title: '權限別', sortable: false, key: 'emp_perm', align: 'start' },
  { title: 'Actions', sortable: false, key: 'actions' , align: 'end'},
];

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: 25, title: '25' },
  //{ value: -1, title: '$vuetify.dataFooter.itemsPerPageAll' }
  { value: -1, title: '全部' }
];
const treeViewItems = reactive([
  {
    id: 1,
    name: "在製品生產資訊",
    children: [
      { id: 2, name: "加工區" },
      { id: 3, name: "組裝區", disabled: true },
      { id: 4, name: "ID 4" }
    ]
  },
  {
    id: 5,
    name: "備料區資訊",
    children: [
      {
        id: 6,
        name: "ID 6",
        children: [
          {
            id: 7,
            name: "ID 7",
            children: [
              { id: 8, name: "ID 8" },
              { id: 9, name: "ID 9" }
            ]
          }
        ]
      },
      {
        id: 10,
        name: "ID 10",
        children: [
          {
            id: 11,
            name: "ID 11",
            children: [
              { id: 12, name: "ID 12" },
              { id: 13, name: "ID 13" },
              { id: 14, name: "ID 14" }
            ]
          }
        ]
      }
    ]
  }
]);

const treeViewSelection = ref([]);

const editedIndex = ref(-1);
const editedItem = reactive({
  emp_id: '',
  emp_name: '',
  dep_name: '',
  emp_perm: 3,    // member
  password_reset: 'no',
});
const defaultItem = reactive({
  emp_id: '',
  emp_name: '',
  dep_name: '',
  emp_perm: 3,    // member
  password_reset: 'no',
});

const password_reset = ref('no');

const route = useRoute(); // Initialize router

//=== watch ===
setupListUsersWatcher();

watch(currentUser, (newUser) => {
  if (newUser.perm < 1) {
    permDialog.value = true;
  }
});

//=== computed ===
const formTitle = computed(() => (editedIndex.value === -1 ? '新增資料' : '編輯資料'));

const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)'
}));

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

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

const close = () => {
    dialog.value = false;
    editedIndex.value = -1;
    Object.assign(editedItem, defaultItem);
}

const save = () => {
    if (editedIndex.value > -1) {
      Object.assign(desserts.value[editedIndex.value], editedItem);
    } else {
      desserts.value.push({ ...editedItem });
    }
    close();
  }

const editItem = (item) => {
    editedIndex.value = desserts.value.indexOf(item);
    Object.assign(editedItem, item);
    dialog.value = true;
  }

const deleteItem = (item) => {
    editedIndex.value = desserts.value.indexOf(item);
    dialogDelete.value = true;
  }

const deleteItemConfirm = () => {
    desserts.value.splice(editedIndex.value, 1);
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

const checkDataForSaveButton = () => {
    // Custom validation logic
    return false; // return true if data is invalid, false otherwise
};

const handleSelect = (node) => {
  if (node.disabled) {
    return;
  }
  // 如果未禁用，則將其添加到選擇列表中
  if (!treeViewSelection.value.includes(node.id)) {
    treeViewSelection.value.push(node.id);
  }
};

</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);
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
  border-radius: 0px 0px $DATA_TABLE_BORDER_RADIUS $DATA_TABLE_BORDER_RADIUS;
}

.tree-view-item.disabled, .tree-view-node.disabled {
  pointer-events: none;
  color: gray;
  opacity: 0.6;
}

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
</style>
