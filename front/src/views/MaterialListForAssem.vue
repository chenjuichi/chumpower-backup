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
      <v-card flat class="card-container">
        <v-card-title class="d-flex align-center pe-2 sticky-card-title">
          組裝區備料清單
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="outlined" style="position: relative; left: -10px; top: 0px;" @click="readAllExcelFun">
            <v-icon left color="green">mdi-microsoft-excel</v-icon>匯入清單
          </v-btn>

          <v-btn color="primary" variant="outlined" style="position: relative; left: 0px; top: 0px;" @click="addItem">
            <v-icon left color="blue">mdi-truck-flatbed</v-icon>呼叫AGV
          </v-btn>
        </v-card-title>
        <v-divider></v-divider>
        <v-data-table
          :headers="headers"
          :items="roles"
          fixed-header
          items-per-page="5"
          item-value="order_num"
          :items-length="roles.length"
          v-model:page="pagination.page"
          class="outer custom-header"
          :style="tableStyle"
          :footer-props="{'prev-icon': 'mdi-chevron-left', 'next-icon': 'mdi-chevron-right',}"
        >
          <template #top>
            <v-dialog v-model="dialog" style="top: 30px;">
              <v-table
                class="inner"
                density="compact"
                height="280px"
                fixed-header
              >
                <template #top>
                  <div class="text-h5 sticky-title">
                    備料資訊
                    <v-btn
                      color="primary"
                      variant="outlined"
                      @click="addItem"
                      style="position: relative; left: 990px; top:10px;">
                      <v-icon left color="blue" >mdi-check-circle-outline</v-icon>確定
                    </v-btn>
                  </div>
                </template>

                <thead>
                  <tr>
                    <th class="text-left">元件</th>
                    <th class="text-left">物料</th>
                    <th class="text-left">數量</th>
                    <th class="text-left">日期</th>
                    <th class="text-left">領取</th>
                    <th class="text-left">缺料</th>
                  </tr>
                </thead>

                <tbody style="overflow-y:auto;">
                  <tr v-for="item in virtualBoats" :key="item.element_num">
                    <td>{{ item.element_num }}</td>
                    <td>
                      <div>
                        <div>{{ item.material_num }}</div>
                        <div style="color: #33cccc; font-weight:600">{{ item.mtl_comment }}</div>
                      </div>
                    </td>
                    <td>
                      <div :class="{'red-text': item.date_alarm}">{{ item.qty }}</div>
                    </td>
                    <td>
                      <div>
                        <div :class="{'red-text': item.date_alarm}">{{ item.date }}</div>
                        <div :class="{'red-text': item.date_alarm}">{{ item.date_alarm }}</div>
                      </div>
                    </td>
                    <td><v-checkbox-btn v-model="item.receive" /></td>
                    <td><v-checkbox-btn v-model="item.lack" /></td>
                  </tr>
                </tbody>
              </v-table>
            </v-dialog>
          </template>

          <template v-slot:item.order_num="{ item }">
            <div>
              <div>{{ item.order_num }}</div>
              <div style="color: #a6a6a6; font-size:12px;">{{ item.process_num }}</div>
            </div>
          </template>

          <template v-slot:item.material_num="{ item }">
            <div>
              <div>{{ item.material_num }}</div>
              <div :style="getStatusStyle(item.material_status)">{{ material_status[item.material_status] }}</div>
            </div>
          </template>

          <template v-slot:item.req_qty="{ item }">
            <div>
              <div>{{ item.req_qty }}</div>
              <div style="color: #a6a6a6; font-size:12px;">{{ item.date }}</div>
            </div>
          </template>

          <template v-slot:item.comment="{ item }">
            <div>
              <div style="color: #669999; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment }}</div>
              <div style="color: #a6a6a6; font-size:12px; font-family: 'cwTeXYen', sans-serif;">{{ item.comment2 }}</div>
            </div>
          </template>

          <template v-slot:item.action="{ item }">
            <v-btn
              size="small"
              variant="tonal"
              style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"
              @click="toggleExpand(item)"
            >
              詳 情
              <v-icon color="orange-darken-4" end>mdi-open-in-new</v-icon>
            </v-btn>
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

  import { useRoute } from 'vue-router'; // Import useRouter

  import { myMixin } from '../mixins/common.js';

  import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

  import { apiOperation, }  from '../mixins/crud.js';

  // 使用 apiOperation 函式來建立 API 請求
  const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
  const listMaterials = apiOperation('get', '/listMaterials');

  //=== component name ==
  defineComponent({
    name: 'MaterialListForAssem'
  });

  // === mix ==
  const { initAxios } = myMixin();

  //=== props ===
  const props = defineProps({
    showFooter: Boolean
  });

  //=== data ===

  const route = useRoute(); // Initialize router

  const headers = [
    { title: '訂單編號', sortable: true, key: 'order_num' },
    { title: '物料編號', sortable: false, key: 'material_num'},
    { title: '需求數量', sortable: false, key: 'req_qty' },
    { title: '場域位置', sortable: false, key: 'location' },
    { title: '缺料註記', sortable: false, key: 'shortage_note' },
    { title: '說明', align: 'center', sortable: false, key: 'comment' },
    { title: '', key: 'action' },
  ];

  const headers_detail = [
    { title: '元件', align: 'start', key: 'element_num' },
    { title: '物料', align: 'end', key: 'material_num' },
    { title: '數量', align: 'end', key: 'qty' },
    { title: '日期', align: 'end', key: 'date' },
    { title: '領取', align: 'end', key: 'receive' },
    { title: '缺料', align: 'end', key: 'lack' },
  ]
  const footerOptions = [
    { value: 5, title: '5' },
    //{ value: 10, title: '10' },
    //{ value: 25, title: '25' },
    //{ value: -1, title: '全部' }
  ];

  const material_status = ['未備料', '備料完成', '備料中', '備料中(缺料)']

  const roles = [
    { order_num: 'A23456789012', process_num: '010', material_num: '1234567890123456', material_status: 0, req_qty: 100, date: '2024/01/10',location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'B23456789012', process_num: '010', material_num: '1234567890123456', material_status: 0, req_qty: 100, date: '2024/11/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'C23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/11/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'D23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/11/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'E23456789012', process_num: '010', material_num: '1234567890123456', material_status: 2, req_qty: 100, date: '2024/09/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'F23456789012', process_num: '010', material_num: '1234567890123456', material_status: 3, req_qty: 100, date: '2024/09/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'G23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/09/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'H23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/10/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'I23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/10/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
    { order_num: 'J23456789012', process_num: '010', material_num: '1234567890123456', material_status: 1, req_qty: 100, date: '2024/10/10', location: 'M5-3', shortage_note: '元件缺料',comment: '1備料清單說明測試字串2備料清單說明測試字串25字', comment2: 'BT50-WFE20-165L'},
  ];

  const virtualBoats = [
  { element_num: '0010', material_num: 'A13456789012', mtl_comment: 'KL16S本體', qty: 100, date: '2024/10/30', date_alarm:'' ,receive: false, lack: false },
  { element_num: '0020', material_num: 'A23456789012', mtl_comment: 'KL16S三爪', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0030', material_num: 'A33456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0040', material_num: 'A43456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0050', material_num: 'A53456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0060', material_num: 'A63456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0070', material_num: 'A73456789012', mtl_comment: 'HELLO', qty: 10, date: '2024/11/10', date_alarm:'超過一周未領' , receive: false, lack: false },
  { element_num: '0080', material_num: 'A83456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0090', material_num: 'A93456789012', mtl_comment: 'HELLO', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0100', material_num: 'A03456789012', mtl_comment: 'KL16S三爪', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  { element_num: '0110', material_num: 'A03456789012', mtl_comment: 'KL16S三爪', qty: 100, date: '2024/10/30', date_alarm:'' , receive: false, lack: false },
  ]

  const EmpID_max_length = 8;       //員工編號最多數字個數

  const currentUser = ref({});
  const permDialog = ref(false);
  const rightDialog = ref(false);
  const showExplore = ref(false);
  const showVirtualTable = ref(false);


  const EmpIDInput = ref(null);
  const tableComponent = ref(null);

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
    itemsPerPage: 5, // 預設值, rows/per page
    page: 1,
  });
//
  //const reactiveLinks = reactive(flatItems.value);
  //const initialSelection = Array(26).fill(0).map((_, i) => (roleMappings['員工'].includes(i + 1) ? 1 : 0));
  //const emit = defineEmits(['setLinks']);
//


  //=== watch ===
  watch(currentUser, (newUser) => {
    if (newUser.perm < 1) {
      permDialog.value = true;
    }
  });

  //=== computed ===
  const tableStyle = computed(() => ({
    height: props.showFooter ? 'calc(100vh - 120px)' : 'calc(100vh - 60px)',
    width: '1050px',
    overflowY: 'hidden',
    position: 'relative',
    top: '-30px',
    marginBottom: '5px',
  }));

  const containerStyle = computed(() => ({
    bottom: props.showFooter ? '60px' : '0'
  }));

  const routeName = computed(() => route.name);

  //=== mounted ===
  onMounted(() => {
    console.log("MaterialListForAssem.vue, mounted()...");

    let userData = JSON.parse(localStorage.getItem('loginedUser'));
    console.log("current routeName:", routeName.value);
    console.log("current userData:", userData);

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
    //initialize();
  });

  //=== method ===
  const initialize = () => {
    console.log("initialize()...")

    listUsers();
    listDepartments();
  };

  const getStatusStyle = (status) =>{
    const colorMap = {
      0: '#ff4000',
      1: '#0040ff',
      2: '#669999',
      3: '#ffbf00',
    };

    return {
      color: colorMap[status],
      fontWeight: '600',
      fontSize: '12px',
    };
  };

  const toggleExpand = (item) => {
    console.log("toggleExpand(),", item)
    //item._showDetails = !item._showDetails;
    dialog.value = true;

  };

  const addItem = () => {
    console.log("addItem()...")
    //item._showDetails = !item._showDetails;
    dialog.value = false;
  };


  const readAllExcelFun= () => {
    console.log("readAllExcelFun()...");

    readAllExcelFiles().then(data => {
      console.log("data:", data);

      data.status ? listMaterials() : showSnackbar(data.message, 'red accent-2');
    });


    /*
    this.isLoading = true;
    const path = '/readAllExcelFiles';
    axios.get(path)
    .then((res) => {
      this.isLoading = false;
      if (res.data.status) {
        //this.readAllExcelFiles_isOK=true;
        //this.showTosterForOK(res.data.message);
        this.close();
        window.location.reload(); // Reloads the current page
      } else {
        this.showTosterForError(res.data.message);
      }
    })
    .catch((error) => {
      this.isLoading = false;
      console.error(error);
      this.showTosterForError('錯誤! API連線問題...');
    });
    */
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
      Object.assign(desserts.value[editedIndex.value], editedItem);
    } else {
      createItem(editedItem);
      desserts.value.push({ ...editedItem });
    }
    close();
  }

  //const reverseEmpPermMapping = Object.fromEntries(
  //  Object.entries(empPermMapping).map(([key, value]) => [value, key])
  //);

  //const getEmpPermText = (emp_perm) => {
  //  return empPermMapping[emp_perm] || '未知';
  //};

  //const getEmpPermKey = (permText) => {
  //  return reverseEmpPermMapping[permText] || '未知';
  //};

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

    editedIndex.value = desserts.value.indexOf(item);
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
    editedIndex.value = desserts.value.indexOf(item);
    Object.assign(editedItem, desserts.value[editedIndex.value]);
    dialogDelete.value = true;
  }

  const deleteItemConfirm = () => {
    removeItem(editedItem.emp_id);

    desserts.value.splice(editedIndex.value, 1);
    closeDelete();
  }

  const closeDelete=() => {
    dialogDelete.value = false;
  }

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

      foundDessert.value = temp_desserts.value.find(dessert => dessert.emp_id === registerUser.empID);
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
    z-index: 10; // 保证标题在内容上方显示
    background: white; // 避免内容滚动时标题被遮盖
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
    background-color: white; /* 確保標題背景與卡片一致 */
    z-index: 2; /* 提高z-index以確保標題在其他內容之上 */
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
  position: relative; /* 讓 sticky 定位相對於這個元素 */
  max-height: 440px; /* 設定合適的高度來產生滾動條 */
  overflow-y: auto; /* 允許垂直滾動 */
}

.red-text {
  color: red;
}

.custom-header theader th {
  background-color: #85aef2; /* 自訂背景顏色 */
}
  </style>
