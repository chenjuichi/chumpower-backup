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
              <v-toolbar-title>組裝站資料維護</v-toolbar-title>
              <v-divider class="mx-4" inset vertical /><v-spacer />
              <v-spacer></v-spacer>
              <v-dialog v-model="dialog" max-width="700" rounded='lg'>
                <template v-slot:activator="{ props: activatorProps }">
                  <v-btn v-bind="activatorProps" @click="dialog = true" color="primary" dark class="mb-2" v-if="currentUser.perm <= 2">
                    <v-icon left dark>mdi-table-plus</v-icon>
                    新增資料
                  </v-btn>
                </template>
                <v-card class="rounded-card mx-auto mt-5">
                <!--
                  <v-card-title>
                    <span class="text-h5">{{ formTitle }}</span>
                  </v-card-title>
                -->
                  <v-img
                    class="align-end text-white custom-img"
                    height="200"
                    :src="imageSrc"
                    cover
                  >
                    <v-card-title>{{ company_name }}</v-card-title>
                  </v-img>

                  <v-card-subtitle class="pt-2">
                    <i class="fa-solid fa-unlock-keyhole" style="color: #63E6BE;" />
                    組裝站資訊
                  </v-card-subtitle>

                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field
                          label="場域代號"
                          v-model="editedItem.emp_id"
                          :rules="[requiredRule, empIDRule]"
                          variant="underlined"
                          :readonly="formTitle === '編輯資料'"
                          ref="EmpIDInput"
                          @update:focused ="checkUsers"
                          @keypress="handleKeyDown"
                        />
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field
                        label="產品名稱"
                        v-model="editedItem.emp_name"
                        :rules="[requiredRule, nameRule]"
                        variant="underlined"
                      />
                      </v-col>
                      <v-col cols="12" md="4">
                      <v-text-field
                        label="產品型號"
                        v-model="editedItem.emp_name"
                        :rules="[requiredRule, nameRule]"
                        variant="underlined"
                      />
                      </v-col>
                    </v-row>
                    <v-row>
                      <v-col cols="12" md="4">
                        <v-text-field
                          label="作業狀態"
                          v-model="editedItem.emp_id"
                          :rules="[requiredRule, empIDRule]"
                          variant="underlined"

                          ref="EmpIDInput"
                          @update:focused ="checkUsers"
                          @keypress="handleKeyDown"
                        />
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field
                        label="工序"
                        v-model="editedItem.emp_name"
                        :rules="[requiredRule, nameRule]"
                        variant="underlined"
                      />
                      </v-col>
                      <v-col cols="12" md="4">
                        <v-text-field
                        label="負責人"
                        v-model="editedItem.emp_name"
                        :rules="[requiredRule, nameRule]"
                        variant="underlined"
                      />
                      </v-col>
                    </v-row>
                    <v-row justify="center">
                      <v-col cols="auto">
                        <v-btn text @click="close" class="btns"><i class="fa-regular fa-circle-xmark" />取消</v-btn>
                      </v-col>
                      <v-col cols="auto">
                        <v-btn text @click="save" class="btns" :disabled='validateFields'><i class="fa-regular fa-circle-check" />確定</v-btn>
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

  import { myMixin } from '../mixins/common.js';

  import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

  //import { setupListUsersWatcher }  from '../mixins/crud.js';
  import { apiOperation }  from '../mixins/crud.js';
  import { departments }  from '../mixins/crud.js';
  //import { desserts }  from '../mixins/crud.js';
  import { desserts2 }  from '../mixins/crud.js';
  import { empPermMapping, roleMappings, treeViewItems } from '../mixins/MenuConstants.js';

  // 使用 apiOperation 函式來建立 API 請求
  const listDepartments = apiOperation('get', '/listDepartments');
  //const listUsers = apiOperation('get', '/listUsers');
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
  const company_name = ref('銓寶工業股份有限公司')
  const imageSrc = ref(require('../assets/online-4208112.jpg')); //企業視覺圖像

  const nameRule = value => value.length <= 10 || '長度太長!';
  const requiredRule = value => !!value || '必須輸入資料!';
  //const empIDRule = value => /^[0-9]{4,5}$/.test(value) || '必須是7或8位數!';  // ^ 和 $ 分別表示字符串的開始和結束, [0-9] 表示數字, {4,5} 4到5位數
  // 必須是7或8位數，且8位數時首位必須為0!
  //const empIDRule = value => {
  //  const normalizedValue = value.padStart(8, '0');
  //  return /^[0-9]{7,8}$/.test(normalizedValue) && normalizedValue.length === 8 && normalizedValue[0] === '0'
  //    ? true : '必須是7或8位數!';
  //};
  //const empIDRule = value => {
  //  return /^[0-9]{7,8}$/.test(value) && (value.length === 8 ? value[0] === '0' : true)
  //    ? true : '必須是7或8位數!';
  //};
  //const empIDRule = value => {
  //  return /^[0-9]{7,8}$/.test(value) && (value.length === 8 ? value[0] === '0' : true)
  //    ? true
  //    : '必須是7或8位數!';
  //};
  // 驗證規則
  //const empIDRule = value => {
  //  return (value.length === 7 || (value.length === 8 && value[0] === '0'))
  //    ? true : '必須是7或8位數!';
  //};
  const empIDRule = value => {
    return /^[0-9]{7}$/.test(value) || /^[0-9]{8}$/.test(value) && value[0] === '0'
      ? true
      : '必須是7或8(0)位數!';
  };

  const route = useRoute(); // Initialize router

  const headers = [
    { title: '場域代號', sortable: false, value: 'location_id' },
    { title: '產品名稱', sortable: false, value: 'prd_name'},
    { title: '產品型號', sortable: false, value: 'prd_type' },
    { title: '作業狀態', sortable: false, value: 'work_type' },
    { title: '工序', sortable: false, value: 'process' },
    { title: '負責人', sortable: false, value: 'emp_name' },
    { title: 'Actions', sortable: false, value: 'actions' },
  ];

  const footerOptions = [
    { value: 5, title: '5' },
    { value: 10, title: '10' },
    { value: 25, title: '25' },
    //{ value: -1, title: '$vuetify.dataFooter.itemsPerPageAll' }
    { value: -1, title: '全部' }
  ];

  const roles = [
    { value: '系統人員', iconClass: 'fa-solid fa-1' },
    { value: '管理人員', iconClass: 'fa-solid fa-2' },
    { value: '主管', iconClass: 'fa-solid fa-3' },
    { value: '員工', iconClass: 'fa-solid fa-4' },
  ];

  const EmpID_max_length = 8;       //員工編號最多數字個數

  const currentUser = ref({});
  const permDialog = ref(false);
  const rightDialog = ref(false);
  const showExplore = ref(false);

  const EmpIDInput = ref(null);

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
  });

  const defaultItem = reactive({
    emp_id: '',
    emp_name: '',
    dep_name: '',
    emp_perm: 4,    // member
    routingPriv: '',
    password_reset: 'no',
  });

  const pagination = reactive({
    itemsPerPage: 10, // 預設值, rows/per page
    page: 1,
  });

  //const snackbar = ref(false);
  //const snackbar_info = ref('');
  //const snackbar_color = ref('red accent-2');

  //=== watch ===
  //setupListUsersWatcher();

  // 監聽輸入值變化，自動補0
  //watch(() => editedItem.emp_id, (newVal) => {
  //  if (newVal.length === 7) {
  //    editedItem.emp_id = newVal.padStart(8, '0');
  //  }
  //});

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

  watch(
    () => editedItem.emp_perm,
    (newValue) => {
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

  //=== computed ===
  const formTitle = computed(() => (editedIndex.value === -1 ? '新增資料' : '編輯資料'));

  const tableStyle = computed(() => ({
    height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)'
  }));

  const containerStyle = computed(() => ({
    bottom: props.showFooter ? '60px' : '0'
  }));

  const routeName = computed(() => route.name);

  const validateFields = computed(() => {
    if (currentUser.value.empID==editedItem.emp_id && currentUser.value.name==editedItem.emp_name) {
      return true;
    }

    return ['emp_id', 'emp_name', 'dep_name'].some(field => !editedItem[field]);
  });

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
  const initialize = async () => {
    console.log("initialize()...")

    //listUsers();
    await listUsers2();
    await listDepartments();
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

  const reverseEmpPermMapping = Object.fromEntries(
    Object.entries(empPermMapping).map(([key, value]) => [value, key])
  );

  const getEmpPermText = (emp_perm) => {
    return empPermMapping[emp_perm] || '未知';
  };

  const getEmpPermKey = (permText) => {
    return reverseEmpPermMapping[permText] || '未知';
  };

  const updateItem = (object) => {  //編輯 user後端table資料
    console.log("updateItem(),", object);

    let payload= {
      emp_id: object.emp_id,
      emp_name: object.emp_name,
      dep_name: object.dep_name,
      emp_perm: object.emp_perm,
      routingPriv: currentSetting.value.join(','),          // 轉換為以逗號分隔的字串
      password_reset: password_reset.value,
    };

    updateUser(payload).then(data => {
      !data && showSnackbar(data.message, 'red accent-2');  // update失敗
    });
  };

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

    let routingPrivArray = editedItem.routingPriv.split(',').map(Number);
    console.log("routingPrivArray,", routingPrivArray)

    treeViewSelection.value = Array(26).fill(0);
    treeViewSelection.value = getSelectedIds(treeViewItems, routingPrivArray);

    console.log("treeViewSelection:", treeViewSelection.value)
    editedItem.password_reset = 'no'
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

  const updateSelection = (newSelection) => {
    console.log("updateSelection,", newSelection)

    treeViewSelection.value = [];
    updateSetting(newSelection);
    console.log("currentSetting:", currentSetting.value);
    nextTick().then(() => {
      treeViewSelection.value = newSelection;
    });
  };

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
    if (!focused) { // 當失去焦點時
      console.log("checkUser()...");

      if (editedItem.emp_id.length == 7) {
        editedItem.emp_id = editedItem.emp_id.padStart(8, '0');
      }

      //foundDessert.value = temp_desserts.value.find(dessert => dessert.emp_id === registerUser.empID);
      foundDessert.value = desserts2.value.find(dessert => dessert.emp_id === registerUser.empID);
      console.log("foundDessert:",foundDessert.value);
      if (foundDessert.value) {
        if (editedItem.emp_id !='') {
          let temp_info = snackbar_info.value = '錯誤, 工號' + editedItem.emp_id + '重複!';
          showSnackbar(temp_info, 'red accent-2');

          editedItem.emp_id = '';
        }
        EmpIDInput.value.focus();
      }
    }
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
  </style>
