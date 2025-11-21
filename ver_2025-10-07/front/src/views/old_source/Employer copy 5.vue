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
            <v-divider class="mx-4" inset vertical /><v-spacer />

            <v-btn @click="dialog = true" color="primary" dark class="mb-2" v-if="currentUser.perm <= 2">
              <v-icon left dark>mdi-table-plus</v-icon>
              新增資料
            </v-btn>

            <v-dialog v-model="dialog" persistent max-width="700" max-height="auto" class="dialog-no-scroll">
              <v-card style="width: 100%; height: auto;" class="card-no-padding">
                <v-card-text style="padding: 0px;">
                  <div class="card_container creditcard">
                      <div id="ccsingle"></div>
                      <svg version="1.1" id="cardfront" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
                          x="0px" y="0px" viewBox="0 0 750 471" style="enable-background:new 0 0 750 471;" xml:space="preserve" >
                        <defs>
                          <clipPath id="clipPath">
                            <path id="Rectangle-1_1_" d="M40,0h670c22.1,0,40,17.9,40,40v391c0,22.1-17.9,40-40,40H40c-22.1,0-40-17.9-40-40V40
                            C0,17.9,17.9,0,40,0z" />
                          </clipPath>
                        </defs>
                        <g id="Page-1_1_" clip-path="url(#clipPath)">
                          <path id="Rectangle-1_1_" class="lightcolor grey" d="M40,0h670c22.1,0,40,17.9,40,40v391c0,22.1-17.9,40-40,40H40c-22.1,0-40-17.9-40-40V40
                          C0,17.9,17.9,0,40,0z" />
                          <image :href="imageSrc" x="0" y="0" height="100%" width="100%" preserveAspectRatio="none" />
                          <text x="500" y="30" fill="white" font-size="16px" font-family="Arial" clip-path="url(#clipPath)">
                            銓寶工業股份有限公司
                          </text>
                        </g>
                        <g id="CardBackground">
                          <path class="darkcolor greydark" d="M750,431V193.2c-217.6-57.5-556.4-13.5-750,24.9V431c0,22.1,17.9,40,40,40h670C732.1,471,750,453.1,750,431z" />
                          <foreignObject x="10" y="240" width="670" height="200">
                            <div xmlns="http://www.w3.org/1999/xhtml">
                              <v-row class="custom-row1">
                                <v-col cols="12" md="4" class="custom-col1">
                                  <div class="input-with-label">
                                    <span class="input-label">工號</span>
                                    <v-text-field
                                      v-model="editedItem.emp_id"
                                      :readonly="formTitle === '編輯資料'"
                                      variant="underlined"
                                    />
                                  </div>
                                </v-col>
                                <v-col cols="12" md="4" class="custom-col1">
                                  <div class="input-with-label">
                                    <span class="input-label">姓名</span>
                                    <v-text-field
                                      v-model="editedItem.emp_name"
                                      variant="underlined"
                                    />
                                  </div>
                                </v-col>
                                <v-col cols="12" md="4" class="custom-col2">
                                  <div class="input-with-label">
                                    <span class="input-label">部門</span>
                                    <v-select
                                      :items="departments"
                                      v-model="editedItem.emp_dep"
                                      variant="underlined"
                                    />
                                  </div>
                                </v-col>
                              </v-row>
                              <v-row class="custom-row2">
                                <v-col cols="12" md="6" class="custom-col21">
                                  <div class="d-flex align-center flex-column">
                                    <v-btn-toggle
                                      v-model="toggle"
                                      variant="outlined"
                                      divided
                                      color="#6200ea"
                                      density="compact"
                                    >
                                      <v-btn style="height: auto; padding: 0; font-size: 6px; width: 45px; min-width: 0px;" value="系統人員">
                                        <span class="fa-stack fa-2x">
                                          <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.2em; position: absolute; transform: translate(-10%, 30%);"></i>
                                          <i class="fa-solid fa-1 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                        </span>
                                      </v-btn>
                                      <v-btn style="height: auto; padding: 0; font-size: 6px; width: 45px; min-width: 0px;" value="管理人員" variant="tonal">
                                        <span class="fa-stack fa-2x">
                                          <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.2em; position: absolute; transform: translate(-10%, 30%);"></i>
                                          <i class="fa-solid fa-2 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                        </span>
                                      </v-btn>
                                      <v-btn style="height: auto; padding: 0; font-size: 6px; width: 45px; min-width: 0px;" value="主管">
                                        <span class="fa-stack fa-2x">
                                          <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.2em; position: absolute; transform: translate(-10%, 30%);"></i>
                                          <i class="fa-solid fa-3 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                        </span>
                                      </v-btn>
                                      <v-btn style="height: auto; padding: 0; font-size: 6px; width: 45px; min-width: 0px;" value="員工" variant="tonal">
                                        <span class="fa-stack fa-2x">
                                          <i class="fa-solid fa-user-lock fa-stack-2x" style="color: #1565C0; font-size: 1.2em; position: absolute; transform: translate(-10%, 30%);"></i>
                                          <i class="fa-solid fa-4 fa-stack-1x" style="color: #EF5350; font-weight:800; position: absolute; transform: translate(50%, -25%);"></i>
                                        </span>
                                      </v-btn>
                                    </v-btn-toggle>
                                    <pre class="pt-2" style="font-weight: 700;">{{ toggle }}</pre>
                                  </div>
                                </v-col>
                                <v-col cols="12" md="6">
                                  <div class="custom-card">
                                    <tree-view
                                      color="blue"
                                      :items="treeViewItems"
                                      v-model="treeViewSelection"
                                      dense
                                      open-all
                                      @select="handleSelect"
                                    />
                                    <!--{{ treeViewSelection.sort() }}-->
                                  </div>
                                  <div style="position: relative; top: 5px; right: 85px;">
                                    <v-btn color="blue darken-1" text @click="close" style="right: 60px;" class="btns">
                                      <i class="fa-regular fa-circle-xmark" style="color: #63E6BE;" />
                                      取消
                                    </v-btn>
                                    <v-btn color="blue darken-1" text @click="save" style="left: 20px;" class="btns">
                                      <i class="fa-regular fa-circle-check" style="color: #63E6BE;" />
                                      確定
                                    </v-btn>
                                  </div>
                                </v-col>
                              </v-row>
                            </div>
                          </foreignObject>
                        </g>
                      </svg>
                  </div>
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
import { ref, reactive, defineComponent, computed, watch, onMounted, onBeforeMount, nextTick } from 'vue';
import { TreeView } from "vue-tree-view";
//import TreeView from "vue3-treeview";
import "vue-tree-view/dist/style.css";
//import "vue3-treeview/dist/style.css";

//import { routerLinks } from '../router/index.js';

import { useRoute } from 'vue-router'; // Import useRouter

import { myMixin } from '../../mixins/common.js';

import { apiOperation, showSnackbar, setupListUsersWatcher }  from '../../mixins/crud.js';
import { departments }  from '../../mixins/crud.js';
import { snackbar, snackbar_info, snackbar_color, desserts } from '../../mixins/crud.js';

const imageSrc = ref(require('../assets/organic-1280537_1280.jpg')); //企業視覺圖像


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
const showExplore = ref(false);

const dialog = ref(false);
const dialogDelete = ref(false);
const totalItems = ref(0);
const toggle= ref('');

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
//const treeViewItems = reactive({
  {
    id: 1,
    name: "在製品生產",
    children: [
      { id: 2, name: "1.加工區" },
      { id: 3, name: "2.組裝區" },
    ]
  },

  {
    id: 4,
    name: "備料清單",
    children: [
      { id: 5, name: "1.加工區" },
      { id: 6, name: "2.組裝區" },
    ]
  },
  {
    id: 7,
    name: "組裝生產",
    children: [
      { id: 8, name: "1.領料生產報工" },
      { id: 9, name: "2.完成生產報工" },
      { id: 10, name: "3.異常填報" }
    ]
  },
  {
    id: 11,
    name: "成品入庫",
  },
  {
    id: 12,
    name: "加工生產",
    children: [
      { id: 13, name: "1.領料生產報工" },
      { id: 14, name: "2.完成生產報工" },
      { id: 15, name: "3.異常填報" }
    ]
  },
  {
    id: 16,
    name: "系統設定",
    children: [
      { id: 17, name: "1.機台資料維護" },
      { id: 18, name: "2.組裝站資料維護" },
      { id: 19, name: "3.加工異常原因維護" },
      { id: 20, name: "4.組裝異常原因維護" },
      { id: 21, name: "5.人員資料維護" },
    ]
  },
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

watch(toggle, (newVal) => {
  console.log("watch:", toggle.value, newVal);
  if (toggle.value === '系統人員') {
    updateSelection([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]);
  } else if (toggle.value === '管理人員') {
    updateSelection([1, 2, 3, 16, 17, 18, 19, 20]);
  } else if (toggle.value === '主管') {
    updateSelection([4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
  } else if (toggle.value === '員工') {
    updateSelection([4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]);
  }
}, { deep: true });



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

const updateSelection = (newSelection) => {
  treeViewSelection.value = [];
  nextTick().then(() => {
    treeViewSelection.value = newSelection;
  });
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

/* CHANGEABLE CARD ELEMENTS */
.creditcard .lightcolor,
.creditcard .darkcolor {
    transition: fill .5s;
}

.creditcard .grey {
    fill: #bdbdbd;
}

.creditcard .greydark {
    //fill: #616161;
    fill: #E3F2FD
}

/* FRONT OF CARD */
#cardfront .st2 {
    fill: #FFFFFF;
}

.form_container {
    margin-top: 20px; /* Optional: Add some margin to separate form from SVG */
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

.custom-row1 {
  top: -35px;
  position: relative;
  margin: 0px;
  height: 60px;
}
.custom-row2 {
  top: -50px;
  position: relative;
  margin: 0px;
  height: 60px;
}/*
/*
.custom-card {
  background-color: #036358;
  box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  max-width: 300px;
  max-height: 110px;
  transition: all 0.5s ease;
  overflow-y: auto;   // Vertical scroll
  overflow-x: hidden;
  text-align: justify;
  //border: 1px solid #1a1a1a;    // Darker border color
  box-sizing: border-box;         // Include border in the element's dimensions
  padding-right: 15px;            // Ensure scrollbar doesn't overlap the border
}
*/
//
.custom-card {
	background-color: #B3E5FC;
	box-shadow: 0px 10px 20px rgba(0, 0, 0, 0.1);
  //box-shadow: inset 0px 0px 0px 1px #2c2c2c, 0px 10px 20px rgba(0, 0, 0, 0.1);
	border-radius: 10px;
	max-width: 300px;
  max-height: 110px;
	transition: all 0.5s ease;
  overflow-x: hidden;
  overflow-y: auto;
  text-align: justify;
  //border: 1px solid #1a1a1a;
  //border: none;
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
  border-radius: 10px;      // 滾動條滑塊圓角
}

// 滾動條滑塊懸停樣式
.custom-card::-webkit-scrollbar-thumb:hover {
  background: #4FC3F7;    // 滾動條滑塊懸停顏色
}

.no-rounded-icon-btn .v-btn__icon {
  border-radius: 0 !important;
}
//
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
  margin-right: 8px; /* 調整間距 */
  font-size: 16px; /* 調整字體大小 */
  color: #000; /* 調整文字顏色 */
  font-weight: 700;
}

.custom-col1 {
  max-width: 110px;
  padding-right: 0px;
  padding-left: 0px;
}
.custom-col2 {
  max-width: 170px;
  padding-right: 0px;
  padding-left: 0px;
}

.custom-col21 {
  position: relative;
  top: 40px;
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

</style>
