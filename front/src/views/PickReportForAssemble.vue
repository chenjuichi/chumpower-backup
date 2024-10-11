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
          組裝區領料生產報工
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

          <!-- disable:agv已到站及agv運行中-->
          <v-btn
            :disabled="isBlinking"
            color="primary"
            variant="outlined"
            style="position: relative; left: 0px; top: 0px;"
            @click="callAGV"
          >
            <v-icon left color="blue">mdi-truck-flatbed</v-icon>
            呼叫AGV
          </v-btn>

          <span
            style="margin-left: 10px; font-size: 14px;"
            :class="{ 'blinking': isBlinking }"
          >
            {{order_num_on_agv_blink}}
          </span>
        </v-card-title>
        <v-divider></v-divider>
        <v-data-table
          :headers="headers"
          :items="sortedItems"
          fixed-header
          items-per-page="5"
          item-value="order_num"
          :items-length="materials_and_assembles.length"
          v-model:page="pagination.page"
          class="outer custom-header"
          :style="tableStyle"
          :footer-props="{'prev-icon': 'mdi-chevron-left', 'next-icon': 'mdi-chevron-right',}"
        >
          <!-- 使用動態插槽來客製化 '訂單編號' (order_num) 欄位的表頭 -->
          <template v-slot:header.order_num="{ column }">
            <div
              style="line-height: 1; margin: 0; padding: 0; text-align: left; display: flex; align-items: center; cursor: pointer;"
              @click="toggleSort('order_num')"
              @mouseover="onMouseOver('order_num')"
              @mouseleave="onMouseLeave('order_num')"
            >
              <span>{{ column.title }}</span>
              <v-icon v-if="isHovered || sortBy[0] === 'order_num'" style="font-size: 20px; margin-left: 4px; font-weight: 700;">
                {{ sortBy[0] === 'order_num' ? (sortDesc[0] ? 'mdi-chevron-down' : 'mdi-chevron-up') : 'mdi-chevron-up' }}
              </v-icon>
            </div>
            <div
              style="color: #a6a6a6; font-size: 12px; font-weight: 600; text-align: center; line-height: 1; margin-left: -60px;"
            >
              途 程
            </div>
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
            <v-flex xs12 class="mt-5">
            <v-tooltip
              v-model="tooltipVisible"
              top
            >
              <template v-slot:activator="{ props }">
            <v-text-field
              v-bind="props"
              v-model="item.receive_qty"
              dense
              hide-details
              style="max-width: 60px; text-align: center;"
              @keyup.enter="saveQty(item)"
              @keypress="handleKeyDown"
              :id="`receiveQtyID-${item.order_num}`"
              @update:modelValue="checkReceiveQty(item)"
            />

          </template>
          <span>領取數量超過需求數量</span>
      </v-tooltip>
    </v-flex>
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
              :disabled="item.isTakeOk"
              @click="toggleExpand(item)"
            >
              開 始
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
  import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

  import { useRoute } from 'vue-router'; // Import useRouter

  import { myMixin } from '../mixins/common.js';

  import { useSocketio } from '../mixins/SocketioService.js';

  import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

  import { materials_and_assembles, boms, socket_server_ip, fileCount }  from '../mixins/crud.js';

  import { apiOperation, setupGetBomsWatcher}  from '../mixins/crud.js';

  // 使用 apiOperation 函式來建立 API 請求
  //const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
  const countExcelFiles = apiOperation('get', '/countExcelFiles');
  const listMaterialsAndAssembles = apiOperation('get', '/listMaterialsAndAssembles');
  const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

  const getBoms = apiOperation('post', '/getBoms');
  const updateBoms = apiOperation('post', '/updateBoms');
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
  //let intervalId = null;              // 10分鐘, 倒數計時器

  let receiveQtyID_max_length = 3;
  //const receiveQtyField = ref(null);
  const inputRefs = ref(new Map()); // 用來存放所有的 input refs
  const inputIDs = ref([]);

  const route = useRoute(); // Initialize router

  const headers = [
    { title: '訂單編號', sortable: true, key: 'order_num'},
    { title: '物料編號', sortable: false, key: 'material_num'},
    { title: '作業數量', sortable: false, key: 'req_qty' },
    { title: '領取數量', sortable: false, key: 'receive_qty' },
    { title: '說明', align: 'start', sortable: false, key: 'comment' },
    { title: '交期', align: 'start', sortable: false, key: 'delivery_date' },
    { title: '', key: 'action' },
  ];

  const userId = 'user_chumpower';
  const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId);

  // 定義排序的相關狀態
  //const sortBy = ref(['order_num']);  // 默認按 'order_num' 排序
  //const sortDesc = ref([false]);      // 默認為升序排序
  const sortBy = ref([]); // 默認不排序
  const sortDesc = ref([]);
  const isHovered = ref(false)
  //const tooltipVisible = ref(false);  // 控制 tooltip 顯示與隱藏

  //const localIP = ref('');
  const from_agv_input_order_num = ref('');
  const isBlinking = ref(false);          // 控制按鍵閃爍
  const order_num_on_agv_blink=ref('');

  const currentUser = ref({});
  const permDialog = ref(false);

  const currentStartTime = ref(null);  // 記錄開始時間

  const agv1StartTime = ref(null);
  const agv1EndTime = ref(null);
  const agv2StartTime = ref(null);
  const agv2EndTime = ref(null);

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

  setupGetBomsWatcher();

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

  const sortedItems = computed(() => {
    if (sortBy.value.length === 0) {
      return materials_and_assembles.value;
    }

    return [...materials_and_assembles.value].sort((a, b) => {
      const order = sortDesc.value[0] ? -1 : 1; // 根據排序方向決定排序方式
      return (a[sortBy.value[0]] < b[sortBy.value[0]] ? -1 : 1) * order; // 使用第一個排序欄位進行比較
    });
  });

  //=== mounted ===
  onMounted(async () => {
    console.log("PickReportForAssemble.vue, mounted()...");

    let userData = JSON.parse(localStorage.getItem('loginedUser'));
    console.log("current routeName:", routeName.value);
    console.log("current userData:", userData);

    userData.setting_items_per_page = pagination.itemsPerPage;
    userData.setting_lastRoutingName = routeName.value;
    localStorage.setItem('loginedUser', JSON.stringify(userData));

    let user = localStorage.getItem("loginedUser");
    currentUser.value = user ? JSON.parse(user) : null;
    console.log("currentUser:", currentUser.value);

    fileCount.value = countExcelFiles();
    console.log("fileCount:", fileCount.value);

    //myIdField = document.getElementById("receiveQtyID");
    //myIdField && (myIdField.addEventListener('keydown', handleKeyDown));

    // 取得每個 v-text-field 的唯一 ID
    inputIDs.value.forEach((item) => {
      const myIdField = document.getElementById(`receiveQtyID-${item.order_num}`);
      myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
    });

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

          from_agv_input_order_num.value = data;
          order_num_on_agv_blink.value = "工單:" + data + "物料運送中...";
          //isBlinking.value = true; // 開始按鍵閃爍

          // 定義 materialPayload1
          const materialPayload1 = {
            order_num: from_agv_input_order_num.value, // 確保 my_material_orderNum 已定義
            record_name: 'show3_ok',
            record_data: 1 // 設為 2，表示備料完成
          };
          await updateMaterial(materialPayload1);
        } else {
          console.log('工單 '+ data + ' 還沒檢料完成!');
          socket.value.emit('station1_order_ng');
          order_num_on_agv_blink.value = '';
        }
      });

      socket.value.on('station1_agv_begin', async () => {
        console.log('AGV暫停, 收到 station1_agv_begin 訊息');

        // 記錄agv在站與站之間運行開始時間
        agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
        console.log("AGV Start time:", agv2StartTime.value);

        const materialPayload1 = {
          order_num: from_agv_input_order_num.value, // 確保 my_material_orderNum 已定義
          record_name: 'show3_ok',
          record_data: 2 // 設為 2，表示備料完成
        };
        await updateMaterial(materialPayload1);

        let agv1PeriodTime = calculatePeriodTime(agv1StartTime.value, agv1EndTime.value);  // 計算時間間隔
        let formattedStartTime = formatDateTime(agv1StartTime.value);
        let formattedEndTime = formatDateTime(agv1EndTime.value);
        console.log("Formatted AGV Start Time:", formattedStartTime);
        console.log("Formatted AGV End Time:", formattedEndTime);
        console.log("AGV Period time:", agv1PeriodTime);

        const processPayload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv1PeriodTime,
          user_id: 'AGV1',
          order_num: from_agv_input_order_num.value,
          process_type: 1,
        };
        await createProcess(processPayload);
      })

      socket.value.on('station1_agv_end', async () => {
        console.log('AGV暫停, 收到 station1_agv_end 訊息');

        const materialPayload1 = {
          order_num: from_agv_input_order_num.value,
          show1_ok: 2,      //組裝站
          show2_ok: 3,      //未組裝
          show3_ok: 0,      //空白
          whichStation: 2,  //目標途程:組裝站
        };
        await updateMaterialRecord(materialPayload1);

        let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
        let formattedStartTime = formatDateTime(agv2StartTime.value);
        let formattedEndTime = formatDateTime(agv2EndTime.vale);
        console.log("Formatted AGV Start Time:", formattedStartTime);
        console.log("Formatted AGV End Time:", formattedEndTime);
        console.log("AGV Period time:", agv2PeriodTime);

        const processPayload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv2PeriodTime,
          user_id: 'AGV2',
          order_num: from_agv_input_order_num.value,
          process_type: 2,
        };
        await createProcess(processPayload);


        isBlinking.value = false;           // 停止工單運送字串閃爍
        order_num_on_agv_blink.value = '';
      });

      socket.value.on('station1_agv_ready', async () => {
        console.log('AGV 已到達裝卸站, 收到 station1_agv_ready 訊息...');
        // 記錄等待ag到站結束時間
        agv1EndTime.value = new Date();  // 使用 Date 來記錄當時時間
        console.log("AGV End time:", agv1EndTime.value);

      });
    } catch (error) {
      console.error('Socket連線失敗:', error);
    }
  });

  //=== unmounted ===
  onUnmounted(() => {   // 清除計時器（當元件卸載時）
    //clearInterval(intervalId);
  });

  //=== created ===
  onBeforeMount(() => {
    console.log("Employer, created()...")

    pagination.itemsPerPage = currentUser.value.setting_items_per_page;

    initAxios();
    initialize();
  });

  //=== method ===
  const initialize = async () => {
    try {
      console.log("initialize()...");

      // 使用 async/await 等待 API 請求完成，確保順序正確
      await listMaterialsAndAssembles();

      await listSocketServerIP();
      console.log("initialize, socket_server_ip:", socket_server_ip.value)
    } catch (error) {
      console.error("Error during initialize():", error);
    }
  };

  const checkReceiveQty = (item) => {
    console.log("checkReceiveQty,", item)

    if (!item || item.receive_qty === undefined || item.total_receive_qty_num === undefined || item.req_qty === undefined) {
      console.error('item 或相關屬性為 undefined');
      return;
    }
    // 如果 receive_qty + total_receive_qty 超過 req_qty，將 receive_qty 清空
    const total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
    const temp = Number(item.req_qty)
    if (total > temp) {
      item.receive_qty = '';  // 清空輸入欄位
      tooltipVisible.value = true;  // 顯示 tooltip
      console.error('領取數量超過需求數量');
    } else {
      item.showTooltip = false;  // 符合條件則隱藏 tooltip
    }
  };
  /*
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
    if (!/^\d$/.test(inputChar) || inputValue.length >= receiveQtyID_max_length) {
      event.preventDefault();
    }
  };
  */
  const handleKeyDown = (event) => {
    const inputChar = event.key;

    const caps = event.getModifierState && event.getModifierState('CapsLock');
    console.log("CapsLock is: ", caps); // true when CapsLock is on

    // 允許左右方向鍵、backspace 和 delete 鍵
    if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
      return;
    }

    const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

    // 使用正規化運算式檢查是否為數字且長度不超過3
    if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
      event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
    }

    // 偵測是否按下 Enter 鍵
    if (event.key === 'Enter' || event.keyCode === 13) {
      console.log('Return key pressed');
      // 如果需要，這裡可以執行其他操作，或進行額外的驗證
      //checkReceiveQty(event.target.item);  // 檢查接收數量的驗證
    }
  };


  // 動態設置 ref
  const setInputRef = (item) => (el) => {
    if (el) {
      inputRefs.value.set(item.order_num, el);
    }
  };
  /*
  const checkUsers = (focused, item) => {
    if (focused) { // 當取得焦點時
      console.log("checkUser()...");

      nextTick(() => {
        const inputElement = inputRefs.value.get(item.order_num)?.$el.querySelector('input');
        if (inputElement) {
          const length = item.receive_qty?.length || 0;
          const middle = Math.floor(length / 2);
          inputElement.setSelectionRange(middle, middle);
        }
      });
    }
  };
  */
  const checkUsers = (focused, item) => {
    if (focused) { // 當取得焦點時
      console.log("checkUser(), step1...");

      nextTick(() => {
        const inputElement = inputRefs.value.get(item.order_num)?.$el.querySelector('input');
        if (inputElement) {
          console.log("checkUser(), step2...");

          // 確保 item.receive_qty 的值已經設定，並在這裡計算長度
          const length = item.receive_qty ? item.receive_qty.toString().length : 0;
          const middle = Math.floor(length / 2);

          // 設定游標範圍
          inputElement.setSelectionRange(middle, middle);
          inputElement.focus(); // 確保輸入框有焦點
        }
      });
    }
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


// 當鼠標進入時顯示升序箭頭
/*
const onMouseOver = (key) => {
  if (sortBy.value.length === 0) {
    // 當滑鼠移入時，設置預設排序為升序
    sortBy.value = [key]; // 設置排序欄位
    sortDesc.value = [false]; // 預設為升序
  }
  isHovered.value = true; // 設置為懸停狀態
};
*/
const onMouseOver = (key) => {
  isHovered.value = true; // 設置為懸停狀態
  if (sortBy.value.length === 0) {
    // 當滑鼠移入時，設置預設排序為升序
    sortBy.value = [key]; // 設置排序欄位
    sortDesc.value = [false]; // 預設為升序
  }
};

// 當鼠標離開時
/*
const onMouseLeave = () => {
  isHovered.value = false; // 清除懸停狀態
};
*/
const onMouseLeave = () => {
  isHovered.value = false; // 清除懸停狀態
};

  // 切換排序的函數
  const toggleSort = (key) => {
  const sortIndex = sortBy.value.indexOf(key);

  if (sortIndex === -1) {
    // 沒有排序，設置升序
    sortBy.value = [key];
    sortDesc.value = [false]; // 設置為升序
  } else {
    // 已經排序過，切換排序方向
    sortDesc.value[sortIndex] = !sortDesc.value[sortIndex]; // 反轉當前排序方向
  }
  // 確保在每次點擊後都重新計算排序
  sortedItems.value; // 這會觸發計算屬性重新計算

    /*
    if (sortIndex !== -1) {
      // 如果已經在排序中，則切換升序或降序
      sortDesc.value[sortIndex] = !sortDesc.value[sortIndex];
    } else {
      // 如果不是排序中的欄位，將其加入排序並預設為升序
      sortBy.value = [key];
      sortDesc.value = [false];
    }
    */
    /*
    if (sortBy.value === key) {
      // 如果點擊的是當前排序欄位，則切換升降序
      sortDesc.value = !sortDesc.value;
    } else {
      // 如果點擊的是不同欄位，則將其設為排序欄位，並默認為升序
      sortBy.value = key;
      sortDesc.value = false;
    }
    */
  };

  // 監聽並更新排序
  const onSortUpdate = (newSortBy) => {
    sortBy.value = newSortBy;
  };

  const onSortDescUpdate = (newSortDesc) => {
    sortDesc.value = newSortDesc;
  };
  /*
  const getServerIP = async () => {   // 定義一個異步函數來請求socket伺服器 IP
    try {
      const response = await axios.get('http://localhost:6500/server-ip'); // 請求伺服器 IP
      serverIP.value = response.data.ip;
    } catch (error) {
      console.error('無法獲取伺服器 IP:', error);
      serverIP.value = '無法獲取伺服器 IP';
    }
  };
  */
  const toggleExpand = (item) => {
    console.log("toggleExpand(),", item.order_num);

    let payload = {
      order_num: item.order_num,
    };
    getBoms(payload);

    // 記錄當前開始備料時間
    currentStartTime.value = new Date();  // 使用 Date 來記錄當時時間
    console.log("Start time:", currentStartTime.value);

    payload = {
      order_num: item.order_num,
      record_name: 'show2_ok',
      record_data: 1                //備料中
    };
    updateMaterial(payload).then(data => {
      !data && showSnackbar(data.message, 'red accent-2');
    });

    dialog.value = true;
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
      const processPayload = {
        begin_time: formattedStartTime,
        end_time: formattedEndTime,
        periodTime: periodTime,
        user_id: currentUser.value.empID,
        order_num: my_material_orderNum,
        process_type: 1,
      };
      await createProcess(processPayload);

      await listMaterials();
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
    if (!date || !(date instanceof Date)) {
      console.error("Invalid date passed to formatDateTime:", date);
      return 'Invalid Date';
    }

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

  const callAGV = async () => {
    console.log("callAGV()...")
    /*
    const materialPayload1 = {        // 2. 更新 materials 資料，show2_ok = 2
      order_num: my_material_orderNum,
      record_name: 'show3_ok',
      record_data: 1                  // 設為 2，表示備料完成
    };

    await updateMaterial(materialPayload1);
    */
    isBlinking.value = true; // 開始按鍵閃爍
    socket.value.emit('station1_call');
    // 記錄等待agv到站開始時間
    agv1StartTime.value = new Date();  // 使用 Date 來記錄當時時間
    console.log("AGV Start time:", agv1StartTime.value);
  };
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
  // 獲取本機 IP 的函數
  const getLocalIP = async () => {
    try {
      const rtc = new RTCPeerConnection({ iceServers: [] });
      rtc.createDataChannel(''); // 創建一個數據通道以避免錯誤
      const offer = await rtc.createOffer();
      await rtc.setLocalDescription(offer);

      return new Promise((resolve, reject) => {
        rtc.onicecandidate = (ice) => {
          if (ice && ice.candidate && ice.candidate.candidate) {
            const ipMatch = ice.candidate.candidate.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
            if (ipMatch) {
              for (let i = 0; i < ipMatch.length; i++) {
                console.log("local ip:",ipMatch[i])
              }
              //resolve(ipMatch[1]); // 返回找到的 IP 地址
              const ip = ipMatch[0];
              // 檢查 IP 是否為無線網卡的 IP 地址
              // 假設無線網卡的 IP 是 192.168.*.* 或 10.*.*.*
              //if (ip.startsWith('192.168.') || ip.startsWith('10.')) {
              //if (ip.startsWith('192.168.')) {
                  resolve(ip); // 返回找到的無線 IP 地址
              //}
            }
          }
        };

        // 超時處理
        setTimeout(() => {
          reject('無法獲取 IP 地址');
        }, 1000);
      });
    } catch (err) {
      console.error('獲取本機 IP 時出現錯誤:', err);
      error.value = '無法獲取本機 IP';
    }
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

  :deep(input[type="text"]) {
    min-height: 20px;
    opacity: 1;
    padding: 0px;
    text-align: center;
    color: red;
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

.blinking {
  animation: blink-animation 1s steps(5, start) infinite;
}

@keyframes blink-animation {
  to {
    visibility: hidden;
  }
}
</style>
