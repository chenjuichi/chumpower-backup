<template>
  <div :class="['page_contain', { 'no-footer': !showFooter }]" :style="containerStyle">
    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" location="top right" :timeout="snackbar_timeout" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn :color="snackbar_icon_color" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <!-- Data Table -->
  <!--
      :custom-key-sort="customKeySort"
      v-model:sort-by="sortBy"
      v-model:sort-desc="sortDesc"
      @update:sort-by="onSortByChange"
      @update:sort-desc="onSortDescChange"
  -->
    <v-data-table
      :headers="headers"
      :items="desserts"
      :row-props="setRowClass"
      class="elevation-1 table_border_radius"
      fixed-header
      height="400"
      density='compact'
      v-model:items-per-page="pagination.itemsPerPage"
      :items-per-page-options="footerOptions"
      :items-length="totalItems"

      v-model:page="pagination.page"
      itemsPerPageText="每頁的資料筆數"
      disableItemsPerPage="false"

      :style="['margin-bottom: 5px', tableStyle]"

    >
      <template #top>
        <v-toolbar flat color="white">
          <v-toolbar-title style="font-weight: bolder; color:blue">部門資料</v-toolbar-title>
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="outlined" style="position: relative; left: -100px; top: -7px;" @click="addItem">
            <v-icon left dark>mdi-plus</v-icon>新增資料
          </v-btn>
        </v-toolbar>
      </template>

      <template v-slot:item="{ item }">
        <tr :class="item.id%2 == 0 ? 'table_odd_row_color' : 'table_even_row_color'">
          <td>
            <v-text-field
              v-model="item.deptId"
              :hide-details="true"
              dense
              single-line


              name="deptId"

              @keypress="handleKeyDown"
              @input="checkForDuplicates(item.deptId)"
              :readonly="editedItem.isReadOnly"
              class="text-field-custom fixed-width"
              :style="{ width: item.deptId ? '75%' : 'auto' }"
              v-if="item.id === editedItem.id">
            </v-text-field>
            <span class="text-span fixed-width" v-else>{{ item.deptId }}</span>
          </td>

          <td>
            <v-text-field
              v-model="item.deptCname"
              :hide-details="true"
              dense
              single-line


              name="deptCname"
              :readonly="item.id !== editedItem.id"
              class="text-field-custom fixed-width"
              :style="{ width: item.deptCname ? '75%' : 'auto' }"
              v-if="item.id === editedItem.id">
            </v-text-field>
            <span class="text-span fixed-width" v-else>{{ item.deptCname }}</span>
          </td>

          <td>
            <v-combobox
              id="main-container"
              v-model="item.deptEname"
              :items="combobox_ary_desserts"
              density="compact"


              hide-details="true"

              item-color="blue"
              class="text-field-custom fixed-width"
              style="height: 56px !important;"
              :style="{ minWidth: '100px !important', width: item.deptEname ? '60%' : 'auto' }"

              @input="handleComboboxInput"
              v-if="item.id === editedItem.id">
            </v-combobox>
            <span class="text-span fixed-width" v-else>{{ item.deptEname }}</span>
          </td>

          <td>
            <v-text-field
              v-model="item.deptAname"
              :hide-details="true"
              dense
              single-line


              class="text-field-custom fixed-width"
              :style="{ width: item.deptAname ? '75%' : 'auto' }"
              v-if="item.id === editedItem.id">
            </v-text-field>
            <span class="text-span fixed-width" v-else>{{ item.deptAname }}</span>
          </td>

          <td>
            <div v-if="item.id === editedItem.id">
              <v-icon color="red" class="mr-3" @click="closeDialog(item)">mdi-close</v-icon>
              <v-icon color="green" @click="saveItem(item)" name="saveIcon" :disabled="isSaveOK">mdi-content-save</v-icon>
            </div>
            <div v-else>
              <v-icon color="green" class="mr-3" @click="editItem(item)">mdi-pencil</v-icon>
              <v-icon color="red" @click="confirmDelete(item)">mdi-delete</v-icon>
            </div>
          </td>
        </tr>
      </template>


      <template #no-data>
        <!--<strong style="color: red;">目前沒有資料</strong>-->
      </template>
    </v-data-table>

    <!-- Confirmation Dialog -->
    <v-dialog v-model="dialog" persistent max-width="290">
      <v-card>
        <v-card-title class="headline">刪除確認</v-card-title>
        <v-card-text>確定刪除這筆資料?</v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="green darken-1" text @click="closeDialog()">取消</v-btn>
          <v-btn color="green darken-1" text @click="deleteItem()">確定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted, onBeforeMount, nextTick, onBeforeUnmount, defineComponent } from 'vue';
import { useRoute } from 'vue-router';
import axios from 'axios';
import { myMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'MyTable'
});

//=== mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
  showFooter: Boolean
});

//=== data ===
const currentUser = ref(null);
const route = useRoute();

const snackbar = ref(false);
const snackbar_color = ref('red accent-2');
const snackbar_info = ref('');
const snackbar_icon_color = ref('#adadad');
const snackbar_timeout = ref(2000);

const list_table_is_ok = ref(false);
const isSaveOK = ref(false);
//const isSelecting = ref(true);
const editedIndex = ref(-1);
const counter = ref(1);
const last_counter = ref(0);
const totalItems = ref(0);
const temp_desserts = ref([]);
const desserts = ref([]);
const combobox_desserts = ref([]);
const combobox_ary_desserts = ref([]);
const dialog = ref(false);
const itemToDelete = ref(null);

const pagination = reactive({
  itemsPerPage: 5,      //records inside the page
  page: 1 ,             //start page index
  sortBy: ['deptId'], // 默認排序欄位應為數組
  sortDesc: [false], // 默認排序順序應為數組  (false = 升冪, true = 降冪)
});

const defaultItem = reactive({
  id: -1,
  isReadOnly: false,
  selecting: false,
  deptId: '',
  deptCname: '',
  deptEname: '',
  deptAname: '',
});

const editedItem = reactive({
  id: -1,
  isReadOnly: false,
  selecting: false,
  deptId: '',
  deptCname: '',
  deptEname: '',
  deptAname: '',
});
//
const customKeySort = ref({
  deptId: (a, b) => a.deptId - b.deptId,
});

const sortBy = ref([]);   // Current sort key as an array
const sortDesc = ref([]); // Current sort order as an array
//
let timeoutId = null;     // timer timeout ID

//=== method ===
const initialize = () => {
  list_table_is_ok.value = false;
  listDepts();
};

const handleComboboxInput = (event) => {
  const value = event.target.value;
  const key = event.key;

  const allowedKeys = ['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'];

  if (allowedKeys.includes(key) || validateInput(value)) {
    if (value) {
      const stringValue = String(value);        // 確保 value 是字串
      editedItem.value.deptEname = stringValue;
      // 驗證輸入或過濾選項
      if (validateInput(stringValue)) {
        filterOptions(stringValue);
      }
    } else {
      console.warn("Input is empty");
    }
  } else {
    console.warn("Invalid key pressed");
  }
};

const validateInput = (input) => {
  const pattern = /^[A-Z0-9_]+$/;
  const isValid=pattern.test(input);
  if (!isValid) {
    console.warn("Invalid input:", input);
    snackbar_info.value = '僅允許大寫字母、底線和數字';
    snackbar.value = true;
  }
  return isValid;
};

const filterOptions = (input) => {
  const stringInput = String(input);  // 確保 input 是字串
  const filteredOptions = combobox_ary_desserts.value.filter(option =>
    option.toLowerCase().includes(stringInput.toLowerCase())
  );
};

/* grace
const onSortByChange = (sortBy) => {
  console.log("sortBy:", sortBy, sortBy[0], sortDesc.value)
  if (sortBy[0].key === 'deptId') {
    console.log("sortBy:", sortBy[0].order)
    if (sortBy[0].order === 'asc') {  //目前為升冪
      sortDesc.value = true;          //降冪排序
      sortBy[0].order = 'desc'
    } else {
      sortDesc.value = false;         //升冪排序
      sortBy[0].order = 'asc'
    }
  }
};
*/
const handleKeyDown = (event) => {
  const inputChar = event.key;

  // 允許左右方向鍵、backspace和delete鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }
  const inputValue = event.target.value || ''; // 确保 inputValue 是字符串

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
    event.preventDefault();
  }
};

const closeDialog = (item) => {
  console.log("closeDialog()...");

  if (item != undefined) {
    //console.log("item, editedItem.value, editedIndex.value:", item, editedItem.value, editedIndex.value);

    // Remove the new item if not saved
    if (editedIndex.value === -1) {
      desserts.value.shift(); // 移除第一筆空白紀錄
    } else {
      Object.assign(desserts.value[editedIndex.value], editedItem.value);
    }
  }
  //combobox_dialog.value = false;

  //editedItem.value = Object.assign({}, defaultItem.value);
  // 重置編輯狀態
  editedItem.value = { ...defaultItem.value };
  editedIndex.value = -1;

  dialog.value = false;
  itemToDelete.value = null;
};

const confirmDelete = (item) => {
  console.log("confirmDelete()...")

  itemToDelete.value = item;

  dialog.value = true;
};

const saveItem = (item) => {
  console.log("saveItem()...", item)

  if (item && !combobox_ary_desserts.value.includes(item.deptEname)) {
    combobox_ary_desserts.value.push(item.deptEname);
  }

  Object.assign(editedItem.value, item);
  if (editedIndex.value > -1) {
    Object.assign(desserts.value[editedIndex.value], item);
    updateDept();
  } else {
    desserts.value.splice(0, 1);
    desserts.value.push(Object.assign({}, item));
    createDept();
    totalItems.value = desserts.value.length; // Update totalItems value
  }
  //console.log("dessert:", desserts.value)
  closeDialog();
};

const editItem = (item) => {
  console.log("editItem()...",item);

  editedIndex.value = desserts.value.indexOf(item);
  //editedItem.value = Object.assign({}, item);
  editedItem.value = { ...item }; // 使用淺拷貝來避免直接修改原始數據
  editedItem.value.isReadOnly = true;
  editedItem.value.id = item.id;

  nextTick(() => {
    const deptCnameInput = document.querySelector('input[name="deptCname"]');
    if (deptCnameInput) {
      deptCnameInput.focus();
    }
  });
};

const deleteItem = () => {
  console.log("deleteItem()...");

  const index = desserts.value.indexOf(itemToDelete.value);

  desserts.value.splice(index, 1);

  deleteDept();
  totalItems.value = desserts.value.length;
  closeDialog();
};

const addItem = () => {
  //const addObj = Object.assign({}, defaultItem.value);
  const addObj = { ...defaultItem.value };

  addObj.id = last_counter.value+1;
  //addObj.isReadOnly = false;
  last_counter.value++;
  // 插入空白行在第一行
  desserts.value.unshift(addObj);

  totalItems.value = desserts.value.length;

  totalItems.value = desserts.value.length;

  // Initialize editedItem
  //editedItem.value = Object.assign({}, addObj);
  editedItem.value = addObj;
  editedIndex.value = -1;

  pagination.value.page = 0;

  timeoutId = setTimeout(() => {
    pagination.value.page = 1;
    nextTick(() => {
      nextTick(() => {
        focusOnDeptIdInput();
      });
    });
  }, 200);
};

const focusOnDeptIdInput = () => {
  let retryCount = 0;
  const maxRetries = 20;

  const attemptFocus = () => {
    const deptIdInput = document.querySelector('input[name="deptId"]');
    //console.log("Attempting to focus on input[name='deptId']: ", deptIdInput); // Log the input element
    if (deptIdInput) {
      deptIdInput.focus();
      //console.log("Focused on input[name='deptId']"); // Log if focusing succeeded
    } else {
      retryCount++;
      if (retryCount < maxRetries) {
        //console.log(`input[name='deptId'] not found, retrying... (${retryCount})`);
        setTimeout(attemptFocus, 100);
      } else {
        //console.log("input[name='deptId'] not found after maximum retries");
      }
    }
  };

  attemptFocus();
};

const setRowClass = (data) => {
  if (data.item && data.item.deptId) {
    const temp3 = last_counter.value % pagination.value.itemsPerPage;

    if ((temp3 == data.item.id) && (desserts.value.length == last_counter.value)) {
      //if (desserts.value.length == last_counter.value) {
        const temp1 = desserts.value[0].deptId.trim().length;
        const temp2 = desserts.value[0].deptCname.trim().length;

        if (temp1 == 0 || temp2 == 0) {
          isSaveOK.value = true;
          /*
          nextTick(() => {
            const deptSaveIcon = document.querySelector('i[name="saveIcon"]');
            if (deptSaveIcon) {
              //deptSaveIcon.disabled = true;
              deptSaveIcon.classList.add('my-filter');
            }
          });
          */
        } else {
          isSaveOK.value = false;
          /*
          nextTick(() => {
            const deptSaveIcon = document.querySelector('i[name="saveIcon"]');
            if (deptSaveIcon) {
              //deptSaveIcon.disabled = false;
              deptSaveIcon.classList.remove('my-filter');
            }
          });
          */
        }
      //}
    }
  }
};

const checkForDuplicates = (deptId) => {
  const inputValue = deptId ? deptId.toString().trim() : '';  // 確保 deptId 是字串

  if (inputValue === '' || inputValue.length < 3) {
    return; // 如果輸入值為空字串或字串長度<3，直接返回
  }

  //if (inputValue.length >= 3) {
    const matchingItems = desserts.value.filter(item => item.deptId === inputValue && item.id != last_counter.value);

    if (matchingItems.length > 0) {
      snackbar_info.value = '輸入編號與' + matchingItems[0].deptId + ' - ' + matchingItems[0].deptCname + '重複!';
      snackbar.value = true;
    }
    //console.log("checkForDuplicates: error message ", snackbar_info.value);
  //}
};

//=== API ===
const listDepts = () => {     //顯示後端dept table所有資料
  console.log("listDepts, Axios get data...");

  list_table_is_ok.value = true;
  /*
  const path = '/dept';
  axios.get(path)
  .then((res) => {
    temp_desserts.value = res.data.data;
    console.log("list dept data ok, total records:", res.data.data, temp_desserts.value);
    list_table_is_ok.value = true;
  })
  .catch((error) => {
    console.error(error);
  });
  */
};

const updateDept = () => {    //編輯後端dept table 單筆資料
  console.log("updateDept(),", editedItem.value);

  const path='/dept2/update';
  let payload= {
    deptId: editedItem.value.deptId,
    deptCname: editedItem.value.deptCname,
    deptEname: editedItem.value.deptEname,
    deptAname: editedItem.value.deptAname,
  };
  axios.post(path, payload)
  .then(res => {
    console.log("update dept data status: ", res.data.msg)
  })
  .catch(err => {
    console.error(err);
  });

};

const createDept = () => {    //新增後端 dept table 單筆資料
  console.log("createDept(),", editedItem.value);

  const path='/dept2/insert';
  let payload= {
    deptId: editedItem.value.deptId,
    deptCname: editedItem.value.deptCname,
    deptEname: editedItem.value.deptEname,
    deptAname: editedItem.value.deptAname,
  };
  axios.post(path, payload)
  .then(res => {
    console.log("create dept data status: ", res.data.msg)
  })
  .catch(err => {
    console.error(err);
  });

};

const deleteDept = () => {    //刪除後端 dept table 單筆資料
  console.log("deleteDept(),", itemToDelete.value);

  const path='/dept2/delete';
  let payload= {
    deptId: itemToDelete.value.deptId,
    deptCname: itemToDelete.value.deptCname,
    deptEname: itemToDelete.value.deptEname,
    deptAname: itemToDelete.value.deptAname,
  };
  axios.post(path, payload)
  .then(res => {
    console.log("delete dept data status: ", res.data.msg)
  })
  .catch(err => {
    console.error(err);
  });

};

//=== watch ===
watch(list_table_is_ok, (val) => {
  if (val) {

    temp_desserts.value = [
      { deptId: '110', deptCname: '會計110', deptEname: 'FIN_E110', deptAname: 'FIN_A110' },
      { deptId: '160', deptCname: '會計160', deptEname: 'FIN_E160', deptAname: 'FIN_A160' },
      { deptId: '120', deptCname: '會計120', deptEname: 'FIN_E120', deptAname: 'FIN_A120' },
      { deptId: '130', deptCname: '會計130', deptEname: 'FIN_E130', deptAname: 'FIN_A130' },
      { deptId: '100', deptCname: '會計100', deptEname: 'FIN_E100', deptAname: 'FIN_A100' },
      { deptId: '140', deptCname: '會計140', deptEname: 'FIN_E140', deptAname: 'FIN_A140' },
      { deptId: '150', deptCname: '會計150', deptEname: 'FIN_E150', deptAname: 'FIN_A150' },
      { deptId: '170', deptCname: '會計170', deptEname: 'FIN_E170', deptAname: 'FIN_A170' }
    ];

    temp_desserts.value.sort((a, b) => a.deptId - b.deptId);  //升冪排序
    const newArray = temp_desserts.value.map(v => ({ ...v, id: counter.value++, isReadonly: false, selecting: false }));
    desserts.value = Object.assign([], newArray);
    /*
    desserts.value = [
      { id: 1, isReadonly: false, selecting: false, deptId: '100', deptCname: '會計100', deptEname: 'FIN_E100', deptAname: 'FIN_A100' },
      { id: 2, isReadonly: false, selecting: false, deptId: '110', deptCname: '會計110', deptEname: 'FIN_E110', deptAname: 'FIN_A110' },
      { id: 3, isReadonly: false, selecting: false, deptId: '120', deptCname: '會計120', deptEname: 'FIN_E120', deptAname: 'FIN_A120' },
      { id: 4, isReadonly: false, selecting: false, deptId: '130', deptCname: '會計130', deptEname: 'FIN_E130', deptAname: 'FIN_A130' },
      { id: 5, isReadonly: false, selecting: false, deptId: '140', deptCname: '會計140', deptEname: 'FIN_E140', deptAname: 'FIN_A140' },
      { id: 6, isReadonly: false, selecting: false, deptId: '150', deptCname: '會計150', deptEname: 'FIN_E150', deptAname: 'FIN_A150' },
      { id: 7, isReadonly: false, selecting: false, deptId: '160', deptCname: '會計160', deptEname: 'FIN_E160', deptAname: 'FIN_A160' },
      { id: 8, isReadonly: false, selecting: false, deptId: '170', deptCname: '會計170', deptEname: 'FIN_E170', deptAname: 'FIN_A170' }
    ];
    */
    ///const fields = ['deptEname',]
    ///combobox_desserts.value = desserts.value.map(i => Object.fromEntries(fields.map(f => [f, i[f]])));
    //combobox_ary_desserts.value = combobox_desserts.value.map(item => item.deptEname);
    combobox_desserts.value = desserts.value.map(({ deptEname }) => ({ deptEname }));
    combobox_ary_desserts.value = combobox_desserts.value.map(({ deptEname }) => deptEname);
    console.log("combobox_desserts:", combobox_desserts.value);
    console.log("combobox_ary_desserts:", combobox_ary_desserts.value);

    totalItems.value = desserts.value.length;
    last_counter.value = totalItems.value;
    list_table_is_ok.value = false;
  }
});

//=== mounted ===
onMounted(() => {
  console.log("MyTable, mounted()...");

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;

  console.log("currentUser:", currentUser.value);

});

//=== computed ===
const routeName = computed(() => route.name);

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const tableStyle = computed(() => ({
  height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)'
}));

//=== created ===
onBeforeMount(() => {
  initAxios();
  initialize();
});

//=== destroyed ===
onBeforeUnmount(() => {
  console.log("in onBeforeUnmount()");

  if (timeoutId) {
    clearTimeout(timeoutId); // Clear the timeout when the component is unmounted
  }
});

//=== constant ===
const headers = [
  { title: '部門編號', key: 'deptId', sortable: true },
  { title: '部門簡稱(英文)', key: 'deptCname', sortable: false},
  { title: '部門名稱', key: 'deptEname', sortable: false },
  { title: '部門簡稱(中文)', key: 'deptAname', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false },
];

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: 25, title: '25' },
  //{ value: -1, title: '$vuetify.dataFooter.itemsPerPageAll' }
  { value: -1, title: '全部' }
];
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
}

.no-footer {
  bottom: 0; // 當頁腳隱藏時，調整底部邊距
}

.text-field-custom .v-input__icon--clear {
  visibility: visible !important;
}

:deep(.v-input__control) {
  height: 56px !important;  /* 自定義高度 */
}
/*
.text-field-custom {
  width: 150px;
}

.text-span {
  display: inline-block;
  width: 150px;
}

.fixed-width {
  width: 150px;
}
*/
.my-filter {
  display: none;
  visibility: hidden;
}
/*
*:disabled {
  background-color: dimgrey !important;
  color: linen !important;
  opacity: 0.2 !important;
}
*/
:deep(header) {
  height: 50px !important;
}

:deep(thead) {
  background-color: $SYSTEM_COLOR;
}

:deep(tbody > tr td) {
  text-align: left !important;
}

:deep(thead > tr th span) {
  font-weight: bolder !important;
}
//v-data-table css
:deep(.v-table__wrapper > table > thead > tr th) {
  background: $DATA_TABLE_HEADER_BG_COLOR !important;
}
.table_odd_row_color {
  background: $ODD_ROW_COLOR !important;
}

.table_even_row_color {
  background: $EVEN_ROW_COLOR !important;
}

.table_border_radius {
  border-radius: 0px 0px $DATA_TABLE_BORDER_RADIUS $DATA_TABLE_BORDER_RADIUS;
}

:deep(.v-table__wrapper > table > thead th:first-child) {
  border-radius: $DATA_TABLE_BORDER_RADIUS 0 0 0;
}

:deep(.v-table__wrapper > table > thead th:last-child) {
  border-radius: 0 $DATA_TABLE_BORDER_RADIUS 0 0;
}

:deep(.v-data-table > .v-data-table-footer) {
  border-radius: $DATA_TABLE_BORDER_RADIUS $DATA_TABLE_BORDER_RADIUS 0 0;
}

</style>
