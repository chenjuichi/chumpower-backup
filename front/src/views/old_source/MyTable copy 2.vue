<template>
  <div class="page_contain">
    <v-snackbar v-model="snackbar" location="top right" :timeout="snackbar_timeout" :color="snackbar_color">
      {{ snackbar_info }}
      <template v-slot:actions>
        <v-btn :color="snackbar_icon_color" @click="snackbar = false">
          <v-icon dark>mdi-close-circle</v-icon>
        </v-btn>
      </template>
    </v-snackbar>

    <v-data-table
      :headers="headers"
      :items="desserts"
      :row-props="setRowClass"
      class="elevation-1"
      fixed-header
      height="400"
      density='compact'
      v-model:items-per-page="pagination.itemsPerPage"
      :items-per-page-options="footerOptions"
      :items-length="totalItems"
      :page.sync="pagination.page"
      itemsPerPageText="每頁的資料筆數"
      disableItemsPerPage="false"
    >
      <template v-slot:top>
        <v-toolbar flat color="white">
          <v-toolbar-title style="font-weight: bolder; color:blue">部門資料</v-toolbar-title>
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="outlined" style="position: relative; left: -100px;" @click="addNew">
            <v-icon left dark>mdi-plus</v-icon>新增資料</v-btn>
        </v-toolbar>
      </template>

      <template v-slot:item.deptId = "{ item }">
        <v-text-field
          v-model="item.deptId"
          :hide-details="true"
          dense
          single-line
          clearable
          clear-icon="mdi-close-circle"
          name="deptId"

          @keypress="handleKeyDown"
          @input="checkForDuplicates(item.deptId)"
          :readonly="editedItem.isReadOnly"
          class="text-field-custom fixed-width"
          :style="{ width: item.deptId ? '75%' : 'auto' }"
          v-if="item.id === editedItem.id">
        </v-text-field>
        <span class="text-span fixed-width" v-else>{{ item.deptId }}</span>
      </template>

      <template v-slot:item.deptCname = "{ item }">
        <v-text-field
          v-model="item.deptCname"
          :hide-details="true"
          dense
          single-line
          clearable
          clear-icon="mdi-close-circle"
          name="deptCname"
          :readonly="item.id !== editedItem.id"
          class="text-field-custom fixed-width"
          :style="{ width: item.deptCname ? '75%' : 'auto' }"
          v-if="item.id === editedItem.id">
        </v-text-field>
        <span class="text-span fixed-width" v-else>{{ item.deptCname }}</span>
      </template>
    <!--
      <template v-slot:item.deptEname = "{ item }">
        <v-select
          v-model="item.deptEname"
          :items="combobox_ary_desserts"
          density="compact"
          clearable
          clear-icon="mdi-close-circle"
          hide-details="true"

          item-color="blue"
          class="text-field-custom fixed-width"
          style="height: 56px !important;"
          :style="{ minWidth: '100px !important', width: item.deptEname ? '55%' : 'auto' }"
          v-if="item.id === editedItem.id">
        </v-select>
        <span class="text-span fixed-width" v-else>{{ item.deptEname }}</span>
      </template>
    -->

    <template v-slot:item.deptEname="{ item }">
      <div>
        <v-text-field
          v-if="!item.selecting && item.id === editedItem.id"
          v-model="item.deptEname"
          hide-details="true"
          dense
          single-line
          clearable
          clear-icon="mdi-close-circle"
          class="text-field-custom fixed-width"
          append-inner-icon="mdi-toggle-switch-off"
          :style="{ width: item.deptEname ? '75%' : 'auto' }"
          @click:appendInner="toggleSelecting(item)"
          @input="updateComboBoxArray(item.deptEname)"
        ></v-text-field>
        <v-select
          v-else-if="item.selecting && item.id === editedItem.id"
          v-model="item.deptEname"
          :items="combobox_ary_desserts"
          dense
          clearable
          clear-icon="mdi-close-circle"
          hide-details="true"
          item-color="blue"
          class="text-field-custom fixed-width"
          style="height: 56px !important;"
          :menu-props="{ auto: true }"
          @change="handleChange(item)"
          @blur="handleBlur(item)"
        ></v-select>
        <span class="text-span fixed-width" v-else>{{ item.deptEname }}</span>
      </div>
    </template>

      <template v-slot:item.deptAname = "{ item }">
        <v-text-field
          v-model="item.deptAname"
          :hide-details="true"
          dense
          single-line
          clearable
          clear-icon="mdi-close-circle"
          class="text-field-custom fixed-width"
          :style="{ width: item.deptAname ? '75%' : 'auto' }"
          v-if="item.id === editedItem.id">
        </v-text-field>
        <span class="text-span fixed-width" v-else>{{ item.deptAname }}</span>
      </template>

      <template v-slot:item.actions="{ item }">
        <div v-if="item.id === editedItem.id">
          <v-icon color="red" class="mr-3" @click="closeDialog(item)">mdi-close</v-icon>
          <v-icon color="green" @click="saveItem(item)" name="saveIcon" :disabled="isSaveOK">mdi-content-save</v-icon>
        </div>
        <div v-else>
          <v-icon color="green" class="mr-3" @click="editItem(item)">mdi-pencil</v-icon>
          <v-icon color="red" @click="confirmDelete(item)">mdi-delete</v-icon>
        </div>
      </template>

      <template v-slot:no-data>
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
import { ref, watch, onMounted, onBeforeMount, computed, nextTick, onBeforeUnmount, defineComponent } from 'vue';
import axios from 'axios';
import { myMixin } from '../../mixins/common.js';

defineComponent({
  name: 'MyTable'
});

//=== mix ==
const { initAxios } = myMixin();

//=== data ===
const snackbar = ref(false);
const snackbar_color = ref('red accent-2');
const snackbar_info = ref('');
const snackbar_icon_color = ref('#adadad');
const snackbar_timeout = ref(2000);

const list_table_is_ok = ref(false);
const isSaveOK = ref(false);
const isSelecting = ref(true);
const editedIndex = ref(-1);
const counter = ref(1);
const last_counter = ref(0);
const totalItems = ref(0);
const temp_desserts = ref([]);
const desserts = ref([]);
const combobox_desserts = ref([]);
const combobox_ary_desserts = ref([]);

const dialog = ref(false);
const combobox_dialog = ref(false);

const itemToDelete = ref(null);

const pagination = ref({
  itemsPerPage: 5,
  //page: 1
});
const defaultItem = ref({
  id: -1,
  isReadOnly: false,
  selecting: false,
  deptId: '',
  deptCname: '',
  deptEname: '',
  deptAname: '',
});

const editedItem = ref({
  id: -1,
  isReadOnly: false,
  selecting: false,
  deptId: '',
  deptCname: '',
  deptEname: '',
  deptAname: '',
});

let timeoutId = null;   // Store the timeout ID

//=== method ===
const initialize = () => {
  list_table_is_ok.value = false;
  listDepts();
};

const toggleSelecting = (item) => {
  item.selecting = !item.selecting;
}

const handleChange = (item)  => {
  item.selecting = false; // Hide select after selection
}

const handleBlur = (item) => {
  item.selecting = false; // Hide select on blur without selection
}

const updateComboBoxArray = (value) => {
  // 確保值不為空再添加到 combobox_ary_desserts
  if (value && !combobox_ary_desserts.value.includes(value)) {
    combobox_ary_desserts.value.push(value);
  }

  //if (!combobox_ary_desserts.value.includes(value)) {
  //  combobox_ary_desserts.value.push(value);
  //}
};

const clearMessage = () => {
  if (editedItem.value && editedItem.value.deptId !== undefined) {
    editedItem.value.deptId = '';
    checkForDuplicates('');     // 檢查傳遞空字串而不是 null
  }
};

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
    console.log("item, editedItem.value, editedIndex.value:", item, editedItem.value, editedIndex.value);
  // Remove the new item if not saved
    if (editedIndex.value === -1) {
      desserts.value.shift(); // 移除第一筆空白紀錄
    } else {
      Object.assign(desserts.value[editedIndex.value], editedItem.value);
    }
  }
  combobox_dialog.value = false;

  editedItem.value = Object.assign({}, defaultItem.value);
  dialog.value = false;
  itemToDelete.value = null;
};

const confirmDelete = (item) => {
  console.log("confirmDelete()...")

  itemToDelete.value = item;
  console.log("desserts.value, item, itemToDelete.value:",desserts.value, item, itemToDelete.value)
  dialog.value = true;
};

const saveItem = (item) => {
  console.log("saveItem()...")

  //確認combobox選單內沒有相同內容選項
  if (!combobox_desserts.value.some(dessert => dessert.deptEname === item.deptEname)) {
    combobox_desserts.value.push({ deptEname: item.deptEname });
  }

  console.log("desserts.value, editedItem.value, item, editedIndex.value:",desserts.value, editedItem.value, item, editedIndex.value)
  if (editedIndex.value > -1) {
    Object.assign(desserts.value[editedIndex.value], item);
  } else {
    desserts.value.push(Object.assign({}, item));
    totalItems.value = desserts.value.length; // Update totalItems value
  }
  console.log("dessert:", desserts.value)
  closeDialog();
};

const editItem = (item) => {
  console.log("editItem()...");

  editedIndex.value = desserts.value.indexOf(item);
  editedItem.value = Object.assign({}, item);
  editedItem.value.isReadOnly = true;
  nextTick(() => {
    const deptCnameInput = document.querySelector('input[name="deptCname"]');
    if (deptCnameInput) {
      deptCnameInput.focus();
    }
  });
};

const deleteItem = () => {
  console.log("deleteItem()...");

  console.log("desserts.value, itemToDelete.value:", desserts.value, itemToDelete.value);

  const index = desserts.value.indexOf(itemToDelete.value);
  console.log("index, desserts.value, itemToDelete.value:", index, desserts.value, itemToDelete.value);
  desserts.value.splice(index, 1);
  console.log("desserts.value:", desserts.value);

  totalItems.value = desserts.value.length;
  closeDialog();
};

const addNew = () => {
  const addObj = Object.assign({}, defaultItem.value);
  addObj.id = last_counter.value+1;
  addObj.isReadOnly = false;
  last_counter.value++;
  desserts.value.unshift(addObj);
  totalItems.value = desserts.value.length;

  // Initialize editedItem
  editedItem.value = Object.assign({}, addObj);
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
    console.log("Attempting to focus on input[name='deptId']: ", deptIdInput); // Log the input element
    if (deptIdInput) {
      deptIdInput.focus();
      console.log("Focused on input[name='deptId']"); // Log if focusing succeeded
    } else {
      retryCount++;
      if (retryCount < maxRetries) {
        console.log(`input[name='deptId'] not found, retrying... (${retryCount})`);
        setTimeout(attemptFocus, 100);
      } else {
        console.log("input[name='deptId'] not found after maximum retries");
      }
    }
  };

  attemptFocus();
};

const setRowClass = (data) => {
  //console.log("setRowClass()...");

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
  // 確保 deptId 是字串
  const inputValue = deptId ? deptId.toString().trim() : '';

  console.log('checkForDuplicates inputValue:', inputValue);

  if (inputValue === '') {
    return; // 如果輸入值為空字串，直接返回
  }

  if (deptId.length >= 3) {
    //console.log('checkForDuplicates item.id, last_counter.value-1:', last_counter.value-1);
    const matchingItems = desserts.value.filter(item => item.deptId === deptId && item.id != last_counter.value);

    //console.log("checkForDuplicates: matchingItems ", matchingItems, matchingItems.length);

    if (matchingItems.length > 0) {
      snackbar_info.value = '輸入編號與' + matchingItems[0].deptId + ' - ' + matchingItems[0].deptCname + '重複!';
      snackbar.value = true;
    }
    console.log("checkForDuplicates: error message ", snackbar_info.value);
  }
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
    console.log("GET ok, total records:", res.data.data, temp_desserts.value);
    list_table_is_ok.value = true;
  })
  .catch((error) => {
    console.error(error);
  });
  */
};

const updateDept = () => {    //編輯後端dept table資料
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

const createDept = () => {    //新增後端 dept table資料
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
    console.log("save dept data status: ", res.data.msg)
  })
  .catch(err => {
    console.error(err);
  });
};

//=== watch ===
watch(list_table_is_ok, (val) => {
  if (val) {
    //const newArray = temp_desserts.value.map(v => ({ ...v, id: counter.value++, isReadonly: false, selecting: false }));
    //desserts.value = Object.assign([], newArray);

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

    const fields = ['deptEname',]
    combobox_desserts.value = desserts.value.map(i => Object.fromEntries(fields.map(f => [f, i[f]])));
    combobox_ary_desserts.value = combobox_desserts.value.map(item => item.deptEname);

    totalItems.value = desserts.value.length;
    last_counter.value = totalItems.value;
    list_table_is_ok.value = false;
  }
});

//=== mounted ===
onMounted(() => {
});

//=== computed ===
const checkData = computed(() => {
  return !(
    editedItem.value.deptId.trim() &&
    editedItem.value.deptCname.trim()
    //editedItem.value.deptEname.trim() &&
    //editedItem.value.deptAname.trim()
  );
});

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
  { value: -1, title: '$vuetify.dataFooter.itemsPerPageAll' }
];
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional'
);
@import "../styles/variables.scss";

.page_contain {
  position: fixed;
  left: 0px;
  top: 60px;        /* 確保在導航欄下方 */
  bottom: 60px;     /* 確保在頁腳上方 */
  padding: 0px 10px;
  width: 100vw;     /* 視窗寬度 */
  margin: 0;
  overflow-y: auto; /* 添加滾動條，防止內容溢出 */
}
.v-data-table {
  height: calc(100vh - 120px); /* 計算導航欄和頁腳的高度 */
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

*:disabled {
  background-color: dimgrey !important;
  color: linen !important;
  opacity: 0.2 !important;
}

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
</style>
