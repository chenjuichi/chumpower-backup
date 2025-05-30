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

    <!-- data table -->
    <v-data-table
      :headers="headers"
      :items="materials_and_assembles_by_user"
      fixed-header
      density="comfortable"
      style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
      :items-per-page-options="footerOptions"
      item-key="name"
      items-per-page="5"

      item-value="index"
      show-select
      :value="selectedItems"

      :sort-by.sync="sortBy"
      :sort-desc.sync="sortDesc"

      class="elevation-10 custom-table"

      items-per-page-text="每頁的資料筆數"
    >
      <!-- 客製化 '選擇框' 欄位表頭 -->
      <template v-slot:header.data-table-select>
        <span class="custom-header">送料</span>
      </template>

      <!-- 自定義每行的選擇框 -->
      <template v-slot:item.data-table-select="{ internalItem }">
        <v-checkbox-btn
          :model-value="isSelected(internalItem)"
          :disabled="!internalItem.raw.isTakeOk || internalItem.raw.receive_qty == 0"
          color="primary"
          @update:model-value="toggleSelect(internalItem)"
          :class="{ 'blue-text': internalItem.raw.isTakeOk }"
        />
      </template>

      <!-- 客製化 top 區域 -->
      <template v-slot:top>
        <v-card>
          <v-card-title class="d-flex align-center pe-2" style="font-weight:700;">
            組裝區完成生產報工
            <v-divider class="mx-4" inset vertical></v-divider>
            <v-spacer />
          <!--
            <v-btn
              v-if="materials_and_assembles_by_user.length > 0"
              color="primary"
              variant="outlined"
              style="position: relative; left: -50px; top: 0px;"
              @click="refreshComponent"
            >
              <v-icon left color="blue">mdi-refresh</v-icon>
              更新訂單
            </v-btn>
          -->
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

            <div>
              <span
                :style="{
                  display: 'inline-block',
                  borderRadius: '50%',
                  width: '25px',
                  height: '25px',
                  position: 'relative',
                  top: '7px',
                  left: '5px',

                  opacity: isFlashLed && isVisible ? 1 : 0, // 根據 isFlashLed 和 isVisible 控制顯示
                  transition: 'opacity 0.5s ease',    // 過渡效果
                  background: background,             // 背景顏色
                  border: '1px solid black'           // 黑色邊框
                }"
              />
              <span style="margin-left: 10px; font-size: 14px;" :class="{ 'blinking': isBlinking }">
                {{order_num_on_agv_blink}}
              </span>
            </div>
          </v-card-title>
        </v-card>
      </template>

      <!-- 客製化 '訂單編號' (order_num) 欄位的表頭 -->
      <template v-slot:header.order_num="{ column }">
        <v-hover v-slot="{ isHovering, props }">
          <div
            v-bind="props"
            style="display: flex; align-items: center; justify-content: center; cursor: pointer;"
            @click="toggleSort('order_num')"
          >
            <div>{{ column.title }}</div>
            <div style="min-width: 24px;">
              <!-- 僅在滑鼠移入或者正在排序的情況下顯示圖標 -->
              <v-icon v-if="sortBy.includes('order_num') && isHovering" style="margin-left: 2px;">
                {{ sortDesc[sortBy.indexOf('order_num')] ? 'mdi-arrow-down' : 'mdi-arrow-up' }}
                <!--{{ sortDesc[0] === null ? 'mdi-minus' : (sortDesc[0] ? 'mdi-arrow-down' : 'mdi-arrow-up') }}-->
              </v-icon>
            </div>
          </div>
          <div style="color: #0000FF; font-size: 12px; margin-top: 2px; font-weight: 600; text-align: center; padding-right: 22px;">
            (工序)
          </div>
        </v-hover>
      </template>

      <!-- 使用動態插槽來客製化 '作業數量' (req_qty) 欄位的表頭 -->
      <template v-slot:header.req_qty="{ column }">
        <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
          <div>{{ column.title }}</div>
          <div style="color: #0000FF; font-size:12px; margin-top: 10px; font-weight:600;">
            (已完成總數量)
          </div>
        </div>
      </template>

      <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
      <template v-slot:item.order_num="{ item }">
        <div style="display: flex; align-items: center;">
          <div style="color: red; margin-right: 2px;" v-if="item.isTakeOk && item.isLackMaterial != 99">
            <div>
              {{ item.order_num }}&nbsp;&nbsp;
              <span style="font-weight: 700; font-size: 16px;">缺料</span>
            </div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div> <!--檢料完成-->
          <div style="color: blue; margin-right: 20px;" v-else-if="item.isTakeOk && item.isLackMaterial == 99">
            <div>{{ item.order_num }}</div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div> <!--檢料完成-->
          <div style="margin-right: 20px;" v-else>
            <div>{{ item.order_num }}</div>
            <div style="color: #a6a6a6; font-size:12px;">{{ item.assemble_work }}</div>
          </div>
        </div>
      </template>

      <!-- 自訂 '物料編號' 欄位的資料欄位 -->
      <template v-slot:item.material_num="{ item }">
        <div>
          <div>{{ item.material_num }}</div>
          <div :style="getStatusStyle(item.assemble_process_num)">{{ item.assemble_process }}</div>
        </div>
      </template>

      <!-- 自訂 '需求數量' 欄位的資料欄位 -->
      <template v-slot:item.req_qty="{ item }">
        <!--
          v-bind="props":
          使用 v-bind 將 props 綁定到 div 上，使其具有 v-hover 的 hover 功能，
          當滑鼠移入或移出該 div 時，就能觸發 isHovering 的變化。

          isHovering:
          根據是否 hover 自動變為 true 或 false，用來控制 span 中的文字顯示。
        -->
        <v-hover v-slot="{ isHovering, props }">
          <div
            v-bind="props"
            style="position: relative; display: inline-block;"
            @mouseenter="hoveredItemIndexForReqQty = index"
            @mouseleave="hoveredItemIndexForReqQty = null"
          >
            <div>
              <div>{{ item.req_qty }}</div>
              <div style="color: #a6a6a6; font-size:12px;">{{ item.total_receive_qty }}</div>
            </div>

            <span
              v-if="isHovering"
              style="
                position: absolute;
                top: -5px;
                left: 35px;
                background-color: white;
                padding: 5px;
                border-radius: 5px;
                box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1);
                font-size: 12px;
                color: #333;
                white-space: nowrap;
              "
            >
              目前領取順序為[
              <span v-for="(pickItem, idx) in item.pickEnd" :key="idx">
                {{ pickItem }}
                <span v-if="idx < item.pickEnd.length - 1">, </span>
              </span>
              ]
            </span>
          </div>
        </v-hover>
      </template>

      <!-- 自訂 '完成數量' 輸入欄位 -->
      <template v-slot:item.receive_qty="{ item }">
        <div style="position: relative; display: inline-block;">
          <v-text-field
            v-model="item.receive_qty"
            dense
            hide-details
            style="max-width: 60px; text-align: center; z-index: 1;"
            :id="`receiveQtyID-${item.assemble_id}`"
            @update:modelValue="checkReceiveQty(item)"
            @update:focused="(focused) => checkTextEditField(focused, item)"
            @keyup.enter="updateItem2(item)"
            :disabled="item.input_disable"
          />
          <span
            v-show="item.tooltipVisible"
            style="position: absolute; left: 60px; top: 0; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 700;"
          >
            {{ receive_qty_alarm }}
          </span>
        </div>
      </template>

      <!-- 自訂 '說明' 欄位的資料欄位 -->
      <template v-slot:item.comment="{ item }">
        <div>
          <div style="text-align:left; color: #669999; font-size:12px; font-family: '微軟正黑體', sans-serif;">{{ item.comment }}</div>
        </div>
      </template>

      <!-- 自訂 '結束' 按鍵欄位 -->
      <template v-slot:item.action="{ item }">
        <div class="action-cell">
          <v-btn
            size="small"
            class="mr-2"
            variant="tonal"
            style="font-size: 13px; font-weight: 700; font-family: '微軟正黑體', sans-serif; padding-left:4px; padding-right:4px; margin-right:10px !important;"
            :disabled="isButtonDisabled(item)"
            @click="updateItem(item)"
            color="indigo-darken-4"
          >
            結 束
            <v-icon color="indigo-darken-4" end>mdi-close-circle-outline</v-icon>
          </v-btn>
          <!-- 自訂 '異常' 按鍵欄位 -->
          <v-btn
            size="small"
            variant="tonal"
            @click="updateAlarm(item)"
            :style="{
              fontSize: '13px',
              fontWeight: '700',
              fontFamily: '\'微軟正黑體\', sans-serif',
              marginLeft: '20px',
              paddingLeft: '4px',
              paddingRright: '4px',
              marginLeft: '0px !important',
              background: item.isAssembleAlarm ? '#e8eaf6' : '#ff0000',
              color: item.isAssembleAlarm ? '#000' : '#fff'
            }"

          >
            異 常
            <v-icon
              :style="{color: item.isAssembleAlarm ? '#000' : '#fff'}"
              end
            >
              mdi-alert-circle-outline
            </v-icon>
          </v-btn>
        </div>
      </template>

      <template #no-data>
        <strong><span style="color: red;">目前沒有資料</span></strong>
      </template>
    </v-data-table>
  </div>
  </template>

  <script setup>
  import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount } from 'vue';

  import { useRoute } from 'vue-router'; // Import useRouter

  import { myMixin } from '../../mixins/common.js';

  import { useSocketio } from '../../mixins/SocketioService.js';

  import { snackbar, snackbar_info, snackbar_color } from '../../mixins/crud.js';

  import { materials_and_assembles_by_user, socket_server_ip }  from '../../mixins/crud.js';

  import { apiOperation, setupGetBomsWatcher}  from '../../mixins/crud.js';

  // 使用 apiOperation 函式來建立 API 請求
  const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

  const getMaterialsAndAssemblesByUser = apiOperation('post', '/getMaterialsAndAssemblesByUser');
  const updateAssemble = apiOperation('post', '/updateAssemble');
  const updateMaterial = apiOperation('post', '/updateMaterial');
  const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
  const createProcess = apiOperation('post', '/createProcess');
  const updateAssembleProcessStep  = apiOperation('post', '/updateAssembleProcessStep');

  //const getMaterial = apiOperation('post', '/getMaterial');

  //=== component name ==
  defineComponent({
    name: 'PickReportForAssembleEnd'
  });

  // === mix ==
  const { initAxios } = myMixin();

  //=== props ===
  const props = defineProps({
    showFooter: Boolean
  });

  //=== data ===
  const history = ref(false);               // 設定歷史紀錄為不顯示

  const isCallAGV = ref(false);             // 確認是否已經按了callAGV按鍵, true:已經按鍵了, 不能重複按鍵

  const isVisible = ref(true);              // 設定初始狀態為顯示
  const isFlashLed = ref(false);            // 控制是否閃爍Led
  let intervalIdForLed = null;
  const background = ref('#ffff00');

  const hoveredItemIndexForReqQty = ref(null);  // 追蹤目前懸停在哪一筆資料上的 index

  //let receiveQtyID_max_length = 3;
  //const inputRefs = ref(new Map()); // 用來存放所有的 input refs
  const inputIDs = ref([]);
  const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)

  const route = useRoute(); // Initialize router

  const footerOptions = [
    { value: 5, title: '5' },
    { value: 10, title: '10' },
    //{ value: 25, title: '25' },
    { value: -1, title: '全部' }
  ];

  const headers = [
    { title: '  ', sortable: false, key: 'index', width: 2 },
    { title: '訂單編號', sortable: true, key: 'order_num' },
    { title: '物料編號', sortable: false, key: 'material_num' },
    { title: '需求數量', sortable: false, key: 'req_qty', width:120 },
    { title: '現況數量', sortable: false, key: 'delivery_qty', width:100 },
    { title: '領料數量', sortable: false, key: 'total_ask_qty', width:100 },
    { title: '完成數量', sortable: false, key: 'receive_qty', width:100 },
    { title: '說明', align: 'start', sortable: false, key: 'comment' },
    { title: '交期', sortable: false, key: 'delivery_date', width:100 },
    { title: '', sortable: false, key: 'action' },
  ];

  const userId = 'user_chumpower';
  const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId);

  // 排序欄位及方向（需為陣列）
  const sortBy = ref(['order_num'])
  const sortDesc = ref([false])

  const receive_qty_alarm = ref('');

  //const from_agv_input_order_num = ref('');
  const isBlinking = ref(false);          // 控制按鍵閃爍
  const order_num_on_agv_blink=ref('');

  //const inputStr = ref('');
  const outputStatus = ref({
    step1: null,
    step2: null
  });

  const currentUser = ref({});
  //const permDialog = ref(false);

  const componentKey = ref(0)             // key值用於強制重新渲染

  const periodTime = ref('');             // 記錄時間間距
  //const currentStartTime = ref(null);  // 記錄開始時間

  //const agv1StartTime = ref(null);
  //const agv1EndTime = ref(null);
  //const agv2StartTime = ref(null);
  //const agv2EndTime = ref(null);

  //const dialog = ref(false);

  const pagination = reactive({
    itemsPerPage: 5, // 預設值, rows/per page
    page: 1,
  });

  //=== watch ===
  //watch(currentUser, (newUser) => {
  //  if (newUser.perm < 1) {
  //    permDialog.value = true;
  //  }
  //});

  //=== computed ===
  const containerStyle = computed(() => ({
    bottom: props.showFooter ? '60px' : '0',
  }));

  const routeName = computed(() => route.name);

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

    initialize();

    // 取得每個 v-text-field 的唯一 ID
    inputIDs.value.forEach((item) => {
      const myIdField = document.getElementById(`receiveQtyID-${item.order_num}`);
      myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
    });

    intervalIdForLed = setInterval(() => {
      isVisible.value = !isVisible.value;  // 每秒切換顯示狀態
    }, 500);

    isBlinking.value = materials_and_assembles_by_user.value.length == 0 || materials_and_assembles_by_user.value.every(item => !item.isAssembleStation1TakeOk && !item.isAssembleStation2TakeOk && !item.isAssembleStation3TakeOk);

    console.log('等待socket連線...');
    try {
      await setupSocketConnection();
    /*
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
      */
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
    //initialize();
  });

  //=== method ===
  const initialize = async () => {
    try {
      console.log("initialize()...");

      await listSocketServerIP();
      console.log("initialize, socket_server_ip:", socket_server_ip.value)

      // 使用 async/await 等待 API 請求完成，確保順序正確
      let payload = {
        user_id: currentUser.value.empID,
        //history: history.value,
      };
      await getMaterialsAndAssemblesByUser(payload);

      // 為materials_and_assembles_by_user每個物件增加 pickEnd 屬性，初始為空陣列 []
      materials_and_assembles_by_user.value.forEach(item => {
        item.pickEnd = [];
      });
    } catch (error) {
      console.error("Error during initialize():", error);
    }
  };

  const isButtonDisabled = (item) => {
    return (item.whichStation != 2 || item.input_disable) || !item.process_step_enable;
  };

  const checkReceiveQty = (item) => {
    console.log("checkReceiveQty,", item);

    const total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
    const temp = Number(item.req_qty)
    if (total > temp) {
      //console.log("total, temp, step1...");
      receive_qty_alarm.value = '領取數量超過作業數量!';
      item.tooltipVisible = true;     // 顯示 Tooltip
      setTimeout(() => {
        item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
        item.receive_qty = '';        // 清空輸入欄位
      }, 2000);
      console.error('領取數量超過需求數量');
    } else {
      item.tooltipVisible = false;
    }
  };

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

  const getStatusStyle = (status) =>{
    const colorMap = {
      0: '#ff0018',
      1: '#0000f9',
      2: '#669999',
      3: '#009acc',
      4: '#008018',
      5: '#86007d',
      6: '#ffa52c',
      7: '#008018',
    };

    return {
      color: colorMap[status],
      fontWeight: '600',
      fontSize: '12px',
    };
  };

  const isSelected = (item) => {
    // 安全檢查，確保 item 和 item.columns 存在
    if (!item || !item.columns || typeof item.columns.index === 'undefined') {
      return false; // 預設未被選中
    }

    return selectedItems.value.includes(item.columns.index); // 根據 columns.index 檢查是否被選中
  };

  const toggleSelect = (item) => {
    // 檢查是否已呼叫 AGV
    if (isCallAGV.value) {
      showSnackbar('已呼叫 AGV，工單不能改變！', 'red accent-2');
      return;     // 不改變選擇狀態
    }

    let nn = selectedItems.value.indexOf(item.columns.index);
    if (nn === -1) {
      selectedItems.value.push(item.columns.index);  // 若未選中，則添加 columns.index
    } else {
      selectedItems.value.splice(nn, 1);       // 若已選中，則移除 columns.index
    }
  };

  const callAGV = async () => {
    console.log("callAGV()...")

    if (!isCallAGV.value) {
      if (selectedItems.value.length == 0) {
        showSnackbar("請選擇送料的工單!", 'red accent-2');
        return;
      }

      let payload = {agv_id: 1};
      await getAGV(payload);
      //待待
      //console.log("hello, currentAGV:", currentAGV.value);
      //if (currentAGV.value.status != 0) {
      //  showSnackbar("AGV目前忙碌中...", 'red accent-2');
      //  return;
      //}

      isCallAGV.value = true
    } else {
      showSnackbar("請不要重複按鍵!", 'red accent-2');
      return;
    }

    //isBlinking.value = true;
    socket.value.emit('station1_call');

    agv1StartTime.value = new Date();  // 使用 Date 來記錄等待agv開始時間
    console.log("AGV Start time:", agv1StartTime.value);
  };

  const updateItem2 = async (item) => {
    console.log("updateItem2(),", item);

    // 檢查是否輸入了空白或 0
    if (!item.receive_qty || Number(item.receive_qty) === 0) {
      item.receive_qty = Number(item.delivery_qty) || 0;
    } else {
      item.receive_qty = Number(item.receive_qty) || 0;
    }

    item.isError = true;              // 輸入數值正確後，重置 數字 為 紅色
  };

  const updateItem = async (item) => {
    console.log("updateItem(),", item);

    // 檢查是否輸入了空白或 0
    if (!item.receive_qty || Number(item.receive_qty) === 0) {
      receive_qty_alarm.value = '領取數量不可為空白或0!'
      item.tooltipVisible = true;     // 顯示 Tooltip 提示
      setTimeout(() => {
        item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
        item.receive_qty = '';        // 清空輸入欄位
      }, 2000);
      console.error('領取數量不可為空白或0!');
      return;
    }

    // 記錄當前完成數量
    let payload = {
      assemble_id: item.assemble_id,
      record_name: 'completed_qty',
      record_data: Number(item.receive_qty),
    };
    await updateAssemble(payload);

    item.pickEnd.push(item.receive_qty);

    // 記錄當前完成總數量
    let current_completed_qty= Number(item.receive_qty)
    let total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
    payload = {
      assemble_id: item.assemble_id,
      record_name: 'total_completed_qty',
      record_data: total,
    };
    await updateAssemble(payload);
    item.total_receive_qty ='(' + total.toString().trim() + ')';
    item.total_receive_qty_num = total;

    checkInputStr(item.assemble_work);
    console.log("outputStatus:", outputStatus.value)
    console.log("current_completed_qty, total:", current_completed_qty, total)

    if (current_completed_qty == total) {
      // 記錄當前途程結束狀態
      payload = {
        order_num: item.order_num,
        record_name: 'show2_ok',
        record_data: outputStatus.value.step2
      };
      await updateMaterial(payload);

      payload = {
        order_num: item.order_num,
        record_name: 'show3_ok',
        record_data: outputStatus.value.step2
      };
      await updateMaterial(payload);
    }

    //const total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
    let temp = Number(item.req_qty)
    if (total == temp) {
      // 記錄當前紀錄, 不能再輸入
      payload = {
        assemble_id: item.assemble_id,
        record_name: 'input_end_disable',
        record_data: true,
      };
      await updateAssemble(payload);

      // 記錄當前完工生產結束時間
      let formattedStartTime = item.currentStartTime  //領料生產報工開始時間
      let endTime = new Date();                                                         // 記錄當前結束時間
      let formattedEndTime = formatDateTime(endTime); //完工生產報工結束時間
      periodTime.value = calculatePeriodTimeStr(formattedStartTime, formattedEndTime);  // 計算時間間隔
      payload = {
        assemble_id: item.assemble_id,
        record_name: 'currentEndTime',
        record_data: formattedEndTime,
      };
      await updateAssemble(payload);

      // 記錄當前紀錄, 目前途程結束
      payload = {
        assemble_id: item.assemble_id,
        record_name: 'process_step_code',
        record_data: 0,
      };
      await updateAssemble(payload);

      // 若組裝區內所有途程結束, 並記錄組裝區內所有途程結束
      payload = {
        id: item.id,
      };
      let response = await updateAssembleProcessStep(payload);
      if (response)
        item.isTakeOk = true

      item.input_disable = true;
    }
  };

  const updateAlarm = async (item) => {
    console.log("updateAlarm(),", item);

    // 檢查是否輸入了空白或 0
    if (!item.receive_qty || Number(item.receive_qty) === 0) {
      receive_qty_alarm.value = '領取數量不可為空白或0!'
      item.tooltipVisible = true;     // 顯示 Tooltip 提示
      setTimeout(() => {
        item.tooltipVisible = false;  // 2秒後隱藏 Tooltip
        item.receive_qty = '';        // 清空輸入欄位
      }, 2000);
      console.error('領取數量不可為空白或0!');
      return;
    }

    // 記錄當前紀錄, 目前途程結束
    let payload = {
      assemble_id: item.assemble_id,
      record_name: 'alarm_enable',
      record_data: true,
    };
    await updateAssemble(payload);
  };

  const checkInputStr = (inputStr) => {
    console.log("checkInputStr(),", inputStr)

    if (inputStr.includes('109')) {             //組裝 開始/結束
      outputStatus.value = { step1: 4, step2: 5, };
    } else if (inputStr.includes('106')) {      //雷射 開始/結束
      outputStatus.value = { step1: 6, step2: 7 };
    } else if (inputStr.includes('110')) {      //檢驗 開始/結束
      outputStatus.value = { step1: 8, step2: 9 };
    } else {
      outputStatus.value = { step1: null, step2: null };  // 無匹配時清空結果
    }
  };

  // 計算兩個時間字串的差值，返回格式化的時間差
  const calculatePeriodTimeStr = (startTime, endTime) => {
    const startDate = new Date(startTime);
    const endDate = new Date(endTime);

    // 確保 startTime 和 endTime 都有效
    //if (isNaN(startDate) || isNaN(endDate)) {
    //  return '無效的時間格式';
    //}

    // 計算毫秒差異
    const diffInMs = endDate - startDate;

    // 計算天、時、分、秒
    const diffInSeconds = Math.floor(diffInMs / 1000);
    const days = Math.floor(diffInSeconds / (24 * 60 * 60));
    const hours = Math.floor((diffInSeconds % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((diffInSeconds % (60 * 60)) / 60);
    const seconds = diffInSeconds % 60;

    // 將時間差格式化為字串
    return `${days} 天, ${hours} 小時, ${minutes} 分鐘, ${seconds} 秒`;
  };

  // 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
  const calculatePeriodTime = (start, end) => {
    const diffMs = end - start;                         // 差異時間（毫秒）
    const diffSeconds = Math.floor(diffMs / 1000);      // 轉換為秒

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

  // 格式化時間為 hh:mm:ss
  const formatTime = (time) => {
    const hours = String(time.getHours()).padStart(2, '0');
    const minutes = String(time.getMinutes()).padStart(2, '0');
    const seconds = String(time.getSeconds()).padStart(2, '0');

    return `${hours}:${minutes}:${seconds}`;
  };

  const showSnackbar = (message, color) => {
    console.log("showSnackbar,", message, color)

    snackbar_info.value = message;
    snackbar_color.value = color;
    snackbar.value = true;
  };

  const checkTextEditField = (focused, item) => {
    if (!focused) { // 當失去焦點時
      console.log("checkTextEditField()...");

      //if (item.receive_qty.trim().length == 0)
      //  item.receive_qty =0;
      // 檢查 item.pickBegin 是否為空陣列
      /*
      if (item.pickEnd.length == 0) {
        item.receive_qty = 0; // 若為空陣列，設置 item.receive_qty 為 0
      } else {
        // 若不是空陣列，將最後一筆值 assign 給 item.receive_qty
        item.receive_qty = item.pickEnd[item.pickEnd.length - 1];
      }
      */
    }
  };

  const toggleSort = (key) => {
    let nn = sortBy.value.indexOf(key)

    if (nn !== -1) {
      // 若目前已經是排序該欄位，則切換排序方向
      sortDesc.value[nn] = !sortDesc.value[nn]
    } else {
      // 否則新增排序欄位，並預設為升序
      sortBy.value = [key]
      sortDesc.value = [false]
    }
  }

  const refreshComponent = () => {
    console.log('更新訂單按鈕已點擊');

    // 透過重新加載當前路由，來刷新組件
    //router.go(0);

    // 改變 key 值，Vue 會重新渲染整個元件
    componentKey.value += 1;
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
    overflow-y: auto;           // 添加 scrollbar，防止內容溢出
    overflow-x: hidden;
  }

  .no-footer {
    margin-bottom: 0;           // 沒有頁腳時的底部邊距
  }

  :deep(.v-data-table .v-table__wrapper > table > thead > tr > th.v-data-table__th) {
    background-color: #85aef2;    // 自訂背景顏色
  }

  :deep(.v-data-table .v-table__wrapper > table > tbody tr:nth-of-type(odd)) {
     background-color: rgba(0, 0, 0, .05);
   }

  :deep(.v-data-table-footer) {
    margin-bottom: -10px;
  }

  :deep(input[type="text"]) {
    min-height: 20px;
    opacity: 1;
    padding: 0px;
    text-align: center;
    color: red;
    min-width:60px;
  }

  .custom-table {
    //border-collapse: collapse;  // 合併邊框
    //border: 1px solid #000;     // 表格的外框
    border-radius: 0 0 20px 20px;
  }

  .action-cell {
    padding-left: 2px;
    padding-right: 2px;
    width: 164px;
  }

  :deep(.custom-table th:nth-child(9)),
  :deep(.custom-table td:nth-child(9)) {
    padding-left: 4px !important;
    padding-right: 4px !important;
    //margin-left:  0px !important;
    margin-right:  5px !important;
  }

  :deep(.custom-table th:nth-child(7)),
  :deep(.custom-table td:nth-child(7)) {
    padding-left: 4px !important;
    padding-right: 4px !important;
  }

  :deep(.custom-table th:nth-child(8)),
  :deep(.custom-table td:nth-child(8)) {
    padding-left: 4px !important;
    padding-right: 4px !important;
  }

  /*
  .custom-table th,
  .custom-table td {
    border: 1px solid #000;   // 單元格的邊框
    padding: 8px;             // 單元格的內邊距
    text-align: left;         // 文本對齊
  }
  */

  // 選擇框
  :deep(span.custom-header) {
    display: block;
    width: 80px;      // 設定最小寬度
  }

  </style>
