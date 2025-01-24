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
      :items="informations_for_assemble_error"
      fixed-header
      style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
      class="custom-data-table"
      items-per-page="5"
      item-value="order_num"
      v-model:page="pagination.page"
      items-per-page-text="每頁的資料筆數"
    >
      <template v-slot:top>
        <v-card>
          <v-card-title class="d-flex align-center pe-2" style="font-weight:700; min-height: 80px;">
            組裝區異常填報
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              variant="outlined"
              style="position: relative; left: 130px; top: 10px; min-height: 20px; height: 34px;"
            >
              <v-icon left color="blue">mdi-history</v-icon>
              歷史紀錄
            </v-btn>

            <v-text-field
              v-model="search"
              label="Search"
              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              single-line
              style="position: relative; top: -2px; min-height: 10px; height:10px;"
              density="compact"
            />
          </v-card-title>
        </v-card>
      </template>

      <!-- 客製化 '現況進度' (show1_ok) 欄位的表頭 -->
      <template v-slot:header.show1_ok = "{ column }">
        <div
          style="line-height: 1;
          margin: 0; padding: 0;
          display: flex;
          cursor: pointer;
          position: relative; left: 8px;
          width: 80px;"
        >
          <span>{{ column.title }}</span>
        </div>
        <div
          style=" color: #a6a6a6;
                  font-size: 10px;
                  font-weight: 600;
                  text-align: center;
                  line-height: 1;
                  position:relative;
                  right: 5px;

                "
        >
          組裝/雷射/檢驗
        </div>
      </template>

      <!-- 客製化 '訂單數量' (req_qty) 欄位表頭 -->
      <template v-slot:header.req_qty="{ column }">
        <div style="text-align: center; white-space: normal; line-height: 1.2; font-size: 14px;">
          訂單<br />數量
        </div>
      </template>

      <!-- 客製化 '現況數量' (delivery_qty) 欄位表頭 -->
      <template v-slot:header.delivery_qty="{ column }">
        <div style="text-align: center; white-space: normal; line-height: 1.2; font-size: 14px;">
          現況<br />數量
        </div>
      </template>

      <!-- 自訂 '現況進度' 欄位 -->
      <template v-slot:item.show1_ok="{ item }">
        <div>
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
          density="compact"
          hide-details="true"
          item-color="blue"

          @change="handleInput(item)"
          @keyup.enter="updateItem2(item)"

          style="position: relative; left: -140px;"
          v-if="!item.cause_message || item.cause_message.length == 0"
        />
        <span class="text-span fixed-width" v-else>{{ item.cause_message }}</span>
      </template>

      <template #no-data>
        <strong><span style="color: red;">目前沒有資料</span></strong>
      </template>
    </v-data-table>
  </div>
  </template>

  <script setup>
  import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

  import { useRoute } from 'vue-router'; // Import useRouter

  import { myMixin } from '../mixins/common.js';

  //import { useSocketio } from '../mixins/SocketioService.js';

  import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

  import { abnormal_causes, boms, informations_for_assemble_error }  from '../mixins/crud.js';

  import { apiOperation }  from '../mixins/crud.js';

  // 使用 apiOperation 函式來建立 API 請求
  const listInformationsForAssembleError = apiOperation('get', '/listInformationsForAssembleError');
  const listAbnormalCauses = apiOperation('get', '/listAbnormalCauses');

  const updateBoms = apiOperation('post', '/updateBoms');
  const updateMaterial = apiOperation('post', '/updateMaterial');
  const createProcess = apiOperation('post', '/createProcess');

  //=== component name ==
  defineComponent({
    name: 'PickReportForAssembleError'
  });

  // === mix ==
  const { initAxios } = myMixin();

  //=== props ===
  const props = defineProps({
    showFooter: Boolean
  });

  //=== data ===
  let intervalId = null;              // 10分鐘, 倒數計時器

  const route = useRoute(); // Initialize router

  const headers = [
    { title: '訂單編號', sortable: true, key: 'order_num', width:130 },
    { title: '現況進度', sortable: false, key: 'show1_ok', width:80 },
    { title: '現況備註', sortable: false, key: 'show3_ok', width:110 },
    { title: '交期', sortable: false, key: 'delivery_date', width:110 },
    { title: '訂單數量', sortable: false, key: 'req_qty', width:60 },
    { title: '現況數量', sortable: false, key: 'delivery_qty', width:60 },
    { title: '點檢人員', sortable: false, key: 'user', width:100 },
    { title: '說明', align: 'start', sortable: false, key: 'comment', width:180 },
    { title: '異常原因填寫', sortable: false, key: 'cause_message', width:110 },
  ];

  const userId = 'user_chumpower';
  // 初始化Socket連接
  //const { socket, setupSocketConnection } = useSocketio(localIp, userId);
  //const { socket, setupSocketConnection } = useSocketio(serverIp, userId);
  //const localIP = ref('');
  const from_agv_order_num = ref('');
  const isBlinking = ref(false);          // 控制按鍵閃爍
  const order_num_on_agv=ref('');
  const search = ref('');
  const inputSearchValue = ref('');

  const selectedErrorMsg = ref(null);
  const placeholderTextForErrorMsg = ref('請選擇異常訊息');
  const inputSelectErrorMsg = ref(null);

  //const abnormal_causes_msg = ref([]);

  const currentUser = ref({});
  const componentKey = ref(0)             // key值用於強制重新渲染
  const permDialog = ref(false);
  //const rightDialog = ref(false);
  //const showExplore = ref(false);
  //const showVirtualTable = ref(false);

  const currentStartTime = ref(null);  // 記錄開始時間

  const dialog = ref(false);

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

  //=== computed ===
  const containerStyle = computed(() => ({
    bottom: props.showFooter ? '60px' : '0'
  }));

  const routeName = computed(() => route.name);

  const abnormal_causes_msg = computed(() =>
  abnormal_causes.value.map(cause => `${cause.message}(${cause.number})`)
);

  //=== mounted ===
  onMounted(async () => {
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

    //fileCount.value = countExcelFiles();
    //console.log("fileCount:", fileCount.value);


    intervalId = setInterval(listInformationsForAssembleError, 10 * 1000);  // 每 10秒鐘調用一次 API
    /*
    console.log('取得本機ip...');
    try {
      localIP.value = await getLocalIP();
      console.error('本機ip:', localIP.value);
    } catch (err) {
      console.error(err);
    }
    */
    /*
    console.log('等待socket連線...');
    try {
      await setupSocketConnection();

      socket.value.on('station1_agv_wait', async (data) => {   //注意, 已修改為async 函數
        console.log('AGV開始, 收到 station1_agv_wait 訊息, 工單:', data);

        const materialPayload0 = {
          order_num: data,
        };
        const response0 = await getMaterial(materialPayload0);

        if(response0) {
          console.log('工單 '+ data + ' 已檢料完成!');
          socket.value.emit('station1_order_ok');

          from_agv_order_num.value = data;
          order_num_on_agv.value = "工單:" + data + "物料運送中...";
          //isBlinking.value = true; // 開始按鍵閃爍

          // 定義 materialPayload1
          const materialPayload1 = {
            order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
            record_name: 'show3_ok',
            record_data: 1 // 設為 2，表示備料完成
          };
          await updateMaterial(materialPayload1);
        } else {
          console.log('工單 '+ data + ' 還沒檢料完成!');
          socket.value.emit('station1_order_ng');
          order_num_on_agv.value = '';
        }
      });

      socket.value.on('station1_agv_begin', async () => {
        console.log('AGV暫停, 收到 station1_agv_begin 訊息');

        const materialPayload1 = {
          order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
          record_name: 'show3_ok',
          record_data: 2 // 設為 2，表示備料完成
        };
        await updateMaterial(materialPayload1);
      })

      socket.value.on('station1_agv_end', async () => {
        console.log('AGV暫停, 收到 station1_agv_end 訊息');

        const materialPayload1 = {
          order_num: from_agv_order_num.value, // 確保 my_material_orderNum 已定義
          show1_ok: 2,
          show2_ok: 20, // 設為 2，表示備料完成
          show3_ok: 2,
          whichStation: 2,
        };
        await updateMaterialRecord(materialPayload1);

        isBlinking.value = false; // 停止按鍵閃爍
        order_num_on_agv.value = '';
      });
    } catch (error) {
      console.error('Socket連接失敗:', error);
    }
    */
  });

  //=== unmounted ===
  onUnmounted(() => {   // 清除計時器（當元件卸載時）
    clearInterval(intervalId);
  });

  //=== created ===
  onBeforeMount(() => {
    console.log("Employer, created()...", currentUser.value)

    pagination.itemsPerPage = currentUser.value.setting_items_per_page;

    initAxios();
    initialize();
  });

  //=== method ===
  const initialize = () => {
    console.log("initialize()...")

    listAbnormalCauses();

    // 使用 map() 提取 message
    //abnormal_causes_msg.value = abnormal_causes.value.map(item => item.message);
    //abnormal_causes_msg.value = abnormal_causes.value.map(item => `${item.message}(${item.number})`);
    //console.log("abnormal_causes_msg.value:",abnormal_causes_msg.value)

    listInformationsForAssembleError();
  };
  /*
  const handleComboboxInput = (event) => {
    const value = event.target.value;
    const key = event.key;

    const allowedKeys = ['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'];

    if (allowedKeys.includes(key) || validateInput(value)) {
      if (value) {
        const stringValue = String(value);        // 確保 value 是字串
        selectedErrorMsg.value = stringValue;
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
  */
 // 更新當前資料行
 const handleInput = (item) => {
  console.log("1. item.cause_message:", item.cause_message);
  console.log("2. abnormal_causes_msg.value:", abnormal_causes_msg.value);

  // 找到匹配的異常原因
  const match = abnormal_causes_msg.value.find((msg) => {
    const regex = new RegExp(`\\(${item.cause_message}\\)$`); // 檢查是否以 (number) 結尾
    return regex.test(msg);
  });

  if (match) {
    console.log("找到匹配的異常原因:", match);
    // 更新資料行的 cause_message
    item.cause_message = match;
  } else {
    console.log("未找到匹配的異常原因");
  }
};

  const validateInput = (input) => {
    const pattern = /^[0-9]+$/;
    const isValid=pattern.test(input);
    if (!isValid) {
      console.warn("Invalid input:", input);
      snackbar_info.value = '僅允許數字';
      snackbar.value = true;
    }
    return isValid;
  };

  const filterOptions = (input) => {
    const stringInput = String(input);  // 確保 input 是字串
    console.log("input:", input)
    const filteredOptions = abnormal_causes_msg.value.filter(option =>
      option.toLowerCase().includes(stringInput.toLowerCase())
    );
    console.log("input, filteredOptions:", input, filteredOptions)
  };

  const updateItem2 = async (item) => {
    console.log("updateItem2(),", item);

    let deliveryQty = 0;
    // 檢查是否輸入了空白或 0
    if (!item.delivery_qty || Number(item.delivery_qty) === 0) {
      deliveryQty = Number(item.total_delivery_qty) || 0;
    } else {
      deliveryQty = Number(item.delivery_qty) || 0;
    }

    let payload = {};

    // 記錄當前送料數量
    payload = {
      id: item.id,
      record_name: 'delivery_qty',
      record_data: deliveryQty,
    };
    await updateMaterial(payload);
    item.delivery_qty = deliveryQty

    item.isError = true;              // 輸入數值正確後，重置 數字 為 紅色
  };
  /*
  const handleKeyDown = (event) => {
    const inputChar = event.key;

    const caps = event.getModifierState && event.getModifierState('CapsLock');
    console.log("CapsLock is: ", caps); // true when CapsLock is on

    // 允許左右方向鍵、backspace 和 delete 鍵
    if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
      return;
    }

    // 如果按下的鍵不是數字，阻止輸入
    if (!/^\d$/.test(inputChar)) {
      event.preventDefault();  // 阻止非數字輸入
      return;
    }

    const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

    // 檢查輸入的長度是否超過6，阻止多餘的輸入
    if (inputValue.length >= 6) {
      event.preventDefault();
      return;
    }

    // 偵測是否按下 Enter 鍵
    if (event.key === 'Enter' || event.keyCode === 13) {
      console.log('Return key pressed');
      // 如果需要，這裡可以執行其他操作，或進行額外的驗證
      //checkReceiveQty(event.target.item);  // 檢查接收數量的驗證
    }
  };
  */
  // 根據輸入搜尋員工編號
  const handleEmployeeSearch = () => {
    console.log("handleEmployeeSearch()...");

    let selected = desserts.value.find(emp => emp.emp_id.replace(/^0+/, '') === selectedErrorMsg.value);
    if (selected) {
      selectedErrorMsg.value = `${selected.emp_id} ${selected.emp_name}`;
      console.log("所選擇異常訊息已更新: ", selectedErrorMsg.value);

      inputSelectErrorMsg.value = placeholderTextForErrorMsg.value;
    } else {
      selectedErrorMsg.value = ''; // 清空值，防止未選擇時顯示錯誤內容
    }

    // 確保 placeholder 保持靜態文字
    placeholderTextForErrorMsg.value = "請選擇異常訊息";
  };

  const updateErrorMsgFieldFromSelect = () => {
    console.log("updateErrorMsgFieldFromSelect(),", inputSelectErrorMsg.value);

    const selected = desserts.value.find(emp => emp.emp_id === inputSelectErrorMsg.value);
    if (selected) {
      selectedErrorMsg.value = `${selected.emp_id} ${selected.emp_name}`;
      console.log("所選擇異常訊息已更新: ", selectedErrorMsg.value);

      inputSelectErrorMsg.value = placeholderTextForErrorMsg.value;
    } else {
      selectedErrorMsg.value = ''; // 清空值，防止未選擇時顯示錯誤內容
    }

      // 確保 placeholder 保持靜態文字
      placeholderTextForErrorMsg.value = "請選擇異常訊息";
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

  const updateItem = async () => {              //編輯 bom, material及process後端table資料
    console.log("updateItem(),", boms.value);

    let my_material_orderNum = boms.value[0].order_num;

    let endTime = new Date();                                               // 記錄當前結束時間
    let periodTime = calculatePeriodTime(currentStartTime.value, endTime);  // 計算時間間隔
    // 將 currentStartTime, endTime 轉換為字串格式 yyyy-mm-dd hh:mm:ss
    let formattedStartTime = formatDateTime(currentStartTime.value);
    let formattedEndTime = formatDateTime(endTime);

    // 使用 .some() 檢查是否有任何 `receive` 為 false 的項目，若有則將 `take_out` 設為 false
    let take_out = !boms.value.some(bom => !bom.receive);

    // 1. 更新 boms 資料
    const response0 = await updateBoms(boms.value);
    if (!response0) {
      showSnackbar(response0.message, 'red accent-2');
      dialog.value = false;
      return;
    }

    if (take_out) {                     // 該筆訂單檢料完成
      const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
        order_num: my_material_orderNum,
        record_name: 'show2_ok',
        record_data: 2                  // 設為 2，表示備料完成
      };
      await updateMaterial(materialPayload1);
      //const response1 = await updateMaterial(materialPayload1);
      //if (!response1) {
      //  showSnackbar(response1.message, 'red accent-2');
      //  dialog.value = false;
      //  return;
      //}

      const materialPayload11 = {        // 2. 更新 materials 資料，isTakeOk = true
        order_num: my_material_orderNum,
        record_name: 'isTakeOk',
        record_data: true
      };
      await updateMaterial(materialPayload11);
      //const response11 = await updateMaterial(materialPayload11);
      //if (!response11) {
      //  showSnackbar(response11.message, 'red accent-2');
      //  dialog.value = false;
      //  return;
      //}

      let myMaterial = materials.value.find(m => m.order_num == my_material_orderNum);
      myMaterial.isTakeOk = true;    // 更新該項目的 isTakeOk 為 true
      myMaterial.show2_ok = 2;  // 更新 bom_agv_status

      console.log("Formatted Start Time:", formattedStartTime);
      console.log("Formatted End Time:", formattedEndTime);
      console.log("Period time:", periodTime);

      // 4. 新增 後端 process的相應項目
      const processPayload = {
        begin_time: formattedStartTime,
        end_time: formattedEndTime,
        periodTime: periodTime,
        user_id: currentUser.value.empID,
        order_num: my_material_orderNum,
        process_type: 1,
        //process_status: 2,
      };

      const response3 = await createProcess(processPayload);
      if (!response3) {
        showSnackbar(response3.message, 'red accent-2');
        dialog.value = false;
        return;
      }

      listMaterials();
    }

    dialog.value = false;
  };

  const calculatePeriodTime = (start, end) => {     // 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
    const diffMs = end - start;                     // 差異時間（毫秒）
    const diffSeconds = Math.floor(diffMs / 1000);  // 轉換為秒

    const hours = Math.floor(diffSeconds / 3600);
    const minutes = Math.floor((diffSeconds % 3600) / 60);
    const seconds = diffSeconds % 60;

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  const formatDateTime = (date) => {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');  // 月份是從0開始的，所以加1
    const dd = String(date.getDate()).padStart(2, '0');
    const hh = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const ss = String(date.getSeconds()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`;
  };

  const formatTime = (time) => {                            // 格式化時間為 hh:mm:ss
    const hours = String(time.getHours()).padStart(2, '0');
    const minutes = String(time.getMinutes()).padStart(2, '0');
    const seconds = String(time.getSeconds()).padStart(2, '0');

    return `${hours}:${minutes}:${seconds}`;
  };

  //const callAGV = async () => {
  //  console.log("callAGV()...")
    /*
    const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
      order_num: my_material_orderNum,
      record_name: 'show3_ok',
      record_data: 1                  // 設為 2，表示備料完成
    };

    await updateMaterial(materialPayload1);
    */
  //  isBlinking.value = true; // 開始按鍵閃爍
  //  socket.value.emit('station1_call');
  //};
  //
  /*
  const readAllExcelFun = () => {
    console.log("readAllExcelFun()...");

    if (fileCount.value == 0) {
      console.warn("No files available for import.");
      return;
    }

    readAllExcelFiles().then(data => {
      console.log("data:", data);

      if (data.status) {
        fileCount.value = 0;
        listMaterials();
      } else {
        showSnackbar(data.message, 'red accent-2');
      }
      //data.status ? listMaterials() : showSnackbar(data.message, 'red accent-2');
    });
  };
  */

  /*
  const refreshComponent = () => {
    console.log('更新訂單按鈕已點擊');

    // 透過重新加載當前路由，來刷新組件
    //router.go(0);

    // 改變 key 值，Vue 會重新渲染整個元件
    componentKey.value += 1;
  };
  */
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
  background-color: #85aef2; /* 自訂背景顏色 */
}

.blinking {
  animation: blink-animation 1s steps(5, start) infinite;
}

@keyframes blink-animation {
  to {
    visibility: hidden;
  }
}

//:deep(.v-table__wrapper table header tr th) {
:deep(.v-data-table .v-table__wrapper > table > thead > tr > th) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-data-table tbody td) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

//:deep(.custom-data-table .v-data-table-header th:first-child) {
//:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:first-child > div) {
//  text-align: center !important;
//}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:first-child div ) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 130px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(2))  {
  width: 80px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(3) div) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 110px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(4) div) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 110px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(7) div) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100px !important;
}

:deep(.v-data-table .v-table__wrapper > table > thead > tr > th:nth-child(9) div) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 140px !important;
}

//:deep(.custom-data-table .v-data-table tbody td:first-child) {
:deep(.v-table__wrapper > table > tbody > tr > td:first-child) {
  text-align: center !important;
  //min-width: 160px;
  //width: 160px;
}

:deep(.v-table__wrapper > table > tbody > tr > td:nth-child(2) div) {
  width: 80px !important;
}

:deep(.v-table__wrapper > table > tbody > tr > td:nth-child(3) div) {
  width: 110px !important;
}

:deep(.v-table__wrapper > table > tbody > tr > td:nth-child(9) .v-input__control) {
  width: 140px !important;
}

:deep(.v-table__wrapper > table > tbody > tr > td > v-input .v-combobox__selection span) {
  font-size:12px !important;
  font-weight: 600 !important;
}
</style>
