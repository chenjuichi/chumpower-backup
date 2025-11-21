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
      :items="materials"
      fixed-header
      style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
      :items-per-page-options="footerOptions"
      items-per-page="5"

      item-value="id"
      show-select
      :value="selectedItems"

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
          :disabled="!internalItem.raw.isTakeOk || internalItem.raw.delivery_qty == 0"
          color="primary"
          @update:model-value="toggleSelect(internalItem)"
          :class="{ 'blue-text': internalItem.raw.isTakeOk }"
        />
      </template>
      <!-- 客製化 top 區域 -->
      <template v-slot:top>
        <v-card>
          <v-card-title class="d-flex align-center pe-2" style="font-weight:700;">
            組裝區備料清單
            <v-divider class="mx-4" inset vertical></v-divider>
            <v-spacer></v-spacer>

            <!--客製化 匯入清單按鍵-->
            <v-btn
              :disabled="fileCount === 0"
              color="primary"
              variant="outlined"
              style="position: relative; right: 450px; top: 0px; font-weight: 700;"
              @click="readAllExcelFun"
            >
              <v-icon left color="green">mdi-microsoft-excel</v-icon>
              匯入清單
              <template v-if="fileCount > 0" v-slot:append>
                <v-badge color="info" :content="fileCount" inline />
              </template>
            </v-btn>

            <!--客製化 員工選單-->
            <v-menu  transition="scale-transition">
              <template v-slot:activator="{ props }">
                <v-btn :disabled="!showMenu" color="primary" variant="outlined" v-bind="props" style="position:relative; left:-115px; top: 1px; min-width: 100px;">
                  <!--<v-icon>mdi-button-cursor</v-icon>-->
                  <v-icon>mdi-account-search-outline</v-icon>
                    <span style="font-weight:700; color:black;"> 員工編號</span>
                  </v-btn>
              </template>

              <v-list>
                <v-list-item
                  v-for="(emp, i) in desserts"
                  :key="i"
                  @click="selectEmployee(emp)"
                >
                  <v-list-item-title>{{ emp.emp_name }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>

            <!--客製化 手動推車/AGV切換按鍵-->
            <div class="button-container">
              <v-btn-toggle >
                  <v-btn
                    variant="outlined"
                    :style="{
                      background: toggle_exclusive === 1 ? '#e67e22' : '#e7e9eb',
                      color: toggle_exclusive === 1 ? '#fff' : '#000',
                      fontWeight: '700'
                    }"
                    @click="setActive(1)"
                  >
                    <v-icon right color="#003171">mdi-cart-outline</v-icon>
                    <span>手動推車</span>
                  </v-btn>

                  <v-btn
                    variant="outlined"
                    :style="{
                      background: toggle_exclusive === 2 ? '#27ae60' : '#e7e9eb',
                      color: toggle_exclusive === 2 ? '#fff' : '#000',
                      fontWeight: '700'
                    }"
                    @click="setActive(2)"
                  >
                    <span>AGV送料</span>
                    <v-icon right color="#003171">mdi-truck-flatbed</v-icon>
                  </v-btn>
              </v-btn-toggle>
            </div>

            <!--客製化 備料送出按鍵-->
            <v-btn
              :disabled="c_isBlinking"
              color="primary"
              variant="outlined"
              style="position: relative; left: -100px; top: 0px; font-weight: 700;"
              @click="callAGV"
            >
              <v-icon left color="blue">mdi-account-arrow-right-outline</v-icon>
              備料送出
            </v-btn>

            <!-- 客製化黃綠燈 -->
            <div
              :style="{
                display: 'inline-block',
                borderRadius: '50%',
                width: '25px',
                height: '25px',
                position: 'relative',
                top: '0px',
                left: '-90px',

                opacity: isFlashLed && isVisible ? 1 : 0, // 根據 isFlashLed 和 isVisible 控制顯示
                transition: 'opacity 0.5s ease',          // 過渡效果
                background: background,                   // 背景顏色
                border: '1px solid black'                 // 黑色邊框
              }"
            />

            <v-dialog
              v-model="dialog"
              max-width="800px"
              @keydown.esc="handleEscClose"
              @click:outside="handleOutsideClick"
            >
              <v-card :style="{ maxHeight: boms.length > 5 ? '500px' : 'unset', overflowY: boms.length > 5 ? 'auto' : 'unset' }">
                <v-card-title class="text-h5 sticky-title" style="background-color: #1b4965; color: white;">
                  備料資訊
                  <v-fade-transition mode="out-in">
                    <v-btn
                      style="position: relative; right: -550px;"
                      color="success"
                      prepend-icon="mdi-check-circle-outline"
                      :disabled="enableDialogBtn"
                      text="確定"
                      class="text-none"
                      @click="updateItem"
                      variant="flat"
                      flat
                    />
                  </v-fade-transition>
                </v-card-title>

                <v-card-text>
                  <v-table class="inner" density="compact" fixed-header>
                    <thead style="color: black;">
                      <tr>
                        <th class="text-left">元件</th>
                        <th class="text-left">物料</th>
                        <th class="text-left">數量</th>
                        <th class="text-left">日期</th>
                        <th class="text-left">領料</th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr
                        v-for="(bom_item, index) in boms"
                        :key="bom_item.seq_num"
                        :style="{
                          backgroundColor: index % 2 === 0 ? '#ffffff' : '#edf2f4',
                        }"
                      >
                        <td>{{ bom_item.seq_num }}</td>
                        <td>
                          <div>
                            <div>{{ bom_item.material_num }}</div>
                            <div style="color: #33cccc; font-weight: 600">{{ bom_item.mtl_comment }}</div>
                          </div>
                        </td>
                        <td>
                          <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.qty }}</div>
                        </td>
                        <td>
                          <div>
                            <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.date }}</div>
                            <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.date_alarm }}</div>
                          </div>
                        </td>
                        <td>
                          <v-checkbox-btn v-model="bom_item.receive" :disabled="enableDialogBtn" />
                        </td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-card-text>
              </v-card>
            </v-dialog>
          </v-card-title>
        </v-card>
      </template>

      <!-- 客製化 '需求數量' (req_qty) 欄位表頭 -->
      <template v-slot:header.req_qty="{ column }">
        <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
          <div>{{ column.title }}</div>
          <div style="font-size:12px; margin-top: 5px;">(建立日期)</div>
        </div>
      </template>

      <!-- 自訂 '訂單編號' 欄位 -->
      <template v-slot:item.order_num="{ item }">
        <div>
          <div style="color: red;" v-if="item.isTakeOk && item.isLackMaterial != 99">
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{{ item.order_num }}&nbsp;&nbsp;
            <span style="font-weight: 700; font-size: 16px;">缺料</span>
          </div> <!--檢料完成-->
          <div style="color: blue;" v-else-if="item.isTakeOk && item.isLackMaterial == 99">{{ item.order_num }}</div> <!--檢料完成-->
          <div v-else>{{ item.order_num }}</div>
          <!--<div style="color: #a6a6a6; font-size:12px;">{{ item.process_num }}</div>-->
        </div>
      </template>

      <!--
      <template v-slot:item.material_num="{ item }">
        <div>
          <div>{{ item.material_num }}</div>
          <div :style="getStatusStyle(item.material_status)">{{ material_status[item.material_status] }}</div>
        </div>
      </template>
      -->

      <!-- 自訂 '需求數量' (req_qty) 欄位 -->
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

      <!-- 自訂 '詳情' 按鍵 -->
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

      <!-- 自訂 '備料數量' 輸入欄位 -->
      <template v-slot:item.delivery_qty="{ item }">
        <div style="position: relative; display: inline-block;">
          <!--
          :disabled="item.input_disable"
          :style="{
              '--input-text-color': (item.isError || item.input_disable) ? 'red' : 'black'  // 動態設置 CSS 變數
          }"
          -->
          <v-text-field
            v-model="item.delivery_qty"
            dense
            hide-details
            :id="`receiveQtyID-${item.id}`"
            @keydown="handleKeyDown"
            @update:modelValue="(value) => { item.delivery_qty = value; checkReceiveQty(item); }"
            @update:focused="(focused) => checkTextEditField(focused, item)"
            @keyup.enter="updateItem2(item)"
            :disabled="!item.isTakeOk"

            :style="{
              '--input-text-color': (item.isError || item.delivery_qty!=0) ? 'red' : 'black'  // 動態設置 CSS 變數
            }"
          />
          <span
            v-show="item.tooltipVisible"
            style="position: absolute; left: -60px; top: 20; z-index: 2; background-color: white; padding: 0; min-width: 120px; white-space: nowrap; color:red; text-align: left; font-weight: 400; font-size: 10px !important;"
          >
            {{ delivery_qty_alarm }}
          </span>
        </div>
      </template>

      <!-- 自訂 data table 在沒有資料時, 畫面的顯示資訊 -->
      <template #no-data>
        <strong><span style="color: red;">目前沒有資料</span></strong>
      </template>
    </v-data-table>
  </div>
  </template>

  <script setup>
  import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

  import { useRoute } from 'vue-router';

  import { useRouter } from 'vue-router';
  const router = useRouter();

  import { myMixin } from '../mixins/common.js';

  import { useSocketio } from '../mixins/SocketioService.js';

  import { materials, boms, desserts, currentAGV, material_copy_id ,socket_server_ip, fileCount }  from '../mixins/crud.js';
  import { apiOperation, setupGetBomsWatcher, setupListUsersWatcher }  from '../mixins/crud.js';

  // 使用 apiOperation 函式來建立 API 請求
  const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
  const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
  const countExcelFiles = apiOperation('get', '/countExcelFiles');
  const listMaterials = apiOperation('get', '/listMaterials');
  const listUsers = apiOperation('get', '/listUsers');
  const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

  const getBoms = apiOperation('post', '/getBoms');
  const getAGV = apiOperation('post', '/getAGV');
  const updateBoms = apiOperation('post', '/updateBoms');
  const updateMaterial = apiOperation('post', '/updateMaterial');
  const copyMaterial = apiOperation('post', '/copyMaterial');
  const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
  const createProcess = apiOperation('post', '/createProcess');
  const updateAGV = apiOperation('post', '/updateAGV');

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
  const snackbar = ref(false);
  const snackbar_info = ref('');
  const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

  const toggle_exclusive = ref(2);              // 控制選擇的按鈕, 預設AGV

  const isVisible = ref(true);                  // 設定初始狀態為顯示
  const isFlashLed = ref(false);                // 控制紅黃綠燈是否閃爍
  let intervalIdForLed = null;
  const background = ref('#ffff00');
  const isCallAGV = ref(false);                 // 確認是否已經按了callAGV按鍵, true:已經按鍵了, 不能重複按鍵
  const showMenu = ref(false);                  // 控制員工選單顯示
  const selectedEmployee = ref(null);

  let intervalId = null;                        // 10分鐘, 倒數計時器
  let debounceTimeout = null;

  const route = useRoute();                     // Initialize router

  const footerOptions = [
    { value: 5, title: '5' },
    { value: 10, title: '10' },
    { value: -1, title: '全部' }
  ];

  const headers = [
    { title: '  ', sortable: false, key: 'id', width: '2px' },
    { title: '訂單編號', sortable: true, key: 'order_num' },
    { title: '物料編號', sortable: false, key: 'material_num'},
    { title: '需求數量', sortable: false, key: 'req_qty' },
    //{ title: '場域位置', sortable: false, key: 'location' },
    //{ title: '缺料註記', sortable: false, key: 'shortage_note' },
    { title: '說明', align: 'start', sortable: false, key: 'comment' },
    { title: '備料內容', sortable: false, key: 'action' },
    //{ title: '待送料總數', sortable: false, key: 'total_delivery_qty' },
    { title: '應備數量', sortable: false, key: 'total_delivery_qty' },
    //{ title: '實際送料數', sortable: false, key: 'delivery_qty' },
    { title: '備料數量', sortable: false, key: 'delivery_qty' },
  ];

  const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)
  const inputValueForItems = ref([]); // 儲存輸入的值

  const inputIDs = ref([]);

  //const localIp = 'localhost';
  //const serverIp = process.env.VUE_SOCKET_SERVER_IP || '192.168.0.13';
  //const serverIp = '192.168.0.13';
  //const serverIp = process.env.VUE_SOCKET_SERVER_IP
  const userId = 'user_chumpower';
  //console.log("serverIp:", serverIp)
  // 初始化Socket連接
  //const { socket, setupSocketConnection } = useSocketio(localIp, userId);
  const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId);

  // 排序欄位及方向（需為陣列）
  //const sortBy = ref(['order_num'])
  //const sortDesc = ref([false])

  const delivery_qty_alarm = ref('');

  //const localIP = ref('');
  const from_agv_input_order_num = ref('');
  const isBlinking = ref(false);          // 控制按鍵閃爍
  const order_num_on_agv_blink=ref('');

  const currentUser = ref({});
  const componentKey = ref(0)       // key 值用於強制重新渲染

  //const permDialog = ref(false);
  const enableDialogBtn = ref(false);

  const current_cell = ref(null);

  const currentStartTime = ref(null);  // 記錄開始時間

  const agv1StartTime = ref(null);    //等待計時開始
  const agv1EndTime = ref(null);
  const agv2StartTime = ref(null);    //運行計時開始
  const agv2EndTime = ref(null);

  const dialog = ref(false);

  const selectedItem = ref(null); // 儲存當前點擊的記錄

  const pagination = reactive({
    itemsPerPage: 5, // 預設值, rows/per page
    page: 1,
  });

  //=== watch ===
  setupGetBomsWatcher();

  setupListUsersWatcher();

  // 監視 selectedItems 的變化，並將其儲存到 localStorage
  watch(selectedItems, (newItems) => {
    console.log("watch(), newItems:", newItems)
    localStorage.setItem('selectedItems', JSON.stringify(newItems));
    },
    { deep: true }
  );

  //=== computed ===
  const c_isBlinking = computed(() => selectedItems.value.length === 0);

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

    // 取得每個 v-text-field 的唯一 ID
    inputIDs.value.forEach((item) => {
      const myIdField = document.getElementById(`receiveQtyID-${item.id}`);
      myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
    });

    // 每10分鐘讀取excel檔案是否存在? 顯示檔案數目
    fileCount.value = countExcelFiles();
    console.log("fileCount:", fileCount.value);

    intervalId = setInterval(countExcelFiles, 10 * 60 * 1000);  // 每 10 分鐘調用一次 API, 10分鐘=600000毫秒

    // 設定紅黃綠燈閃爍週期
    intervalIdForLed = setInterval(() => {
      isVisible.value = !isVisible.value;  // 每秒切換顯示狀態
    }, 500);

    //
    isBlinking.value = selectedItems.value.length == 0 ? true:false;

    // 從 localStorage 中恢復 selectedItems
    let savedItems = localStorage.getItem('selectedItems');
    if (savedItems) {
      selectedItems.value = JSON.parse(savedItems);
    }

    // 從 localStorage 中恢復 inputValueForItems
    //let saveInputValue = localStorage.getItem('inputValueForItems');
    //if (saveInputValue) {
    //  inputValueForItems.value = JSON.parse(saveInputValue);
    //}

    console.log('等待socket連線...');
    try {
      await setupSocketConnection();
      /*
      if (!savedItems) {
        console.log('送出 agv_reset 指令');
        socket.value.emit('agv_reset');
      }
      */

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

          //from_agv_input_order_num.value = data;
          //order_num_on_agv_blink.value = "工單:" + data + "物料運送中...";
          //isBlinking.value = true; // 開始按鍵閃爍

          // 定義 materialPayload1
          const materialPayload1 = {
            order_num: from_agv_input_order_num.value, // 確保 my_material_orderNum 已定義
            record_name: 'show3_ok',
            record_data: 1    // 設為 1，等待agv
          };
          await updateMaterial(materialPayload1);
        } else {
          console.log('工單 '+ data + ' 還沒檢料完成!');
          socket.value.emit('station1_order_ng');
          order_num_on_agv_blink.value = '';
        }
      });
      */
      socket.value.on('agv_start', async () => {
        console.log('AGV 運行任務開始，press Start按鍵, 收到 agv_start 訊息');

        let payload = {};
        // 依據每個 item 的 id 進行資料更新
        selectedItems.value.forEach(async (item) => {
          console.log('selectedItems, item:', item);
          payload = {
            id: item,
            record_name: 'show3_ok',
            record_data: 1, // 設為 1，等待 agv
          };
          //await updateMaterial(materialPayload1);
          try {
            await updateMaterial(payload);
            console.log(`資料更新成功，id: ${item}`);
          } catch (error) {
            console.error(`資料更新失敗，id: ${item}`, error);
          }
        });
      });

      socket.value.on('station1_agv_begin', async () => {
        console.log('AGV暫停, 收到 station1_agv_begin 訊息');

        let payload = {};
        // 記錄agv在站與站之間運行開始時間
        agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
        console.log("AGV Start time:", agv2StartTime.value);

        selectedItems.value.forEach(async (item) => {
          console.log('selectedItems, item:', item);

          payload = {
            id: item,
            record_name: 'show3_ok',
            record_data: 2      // 設為 2，agv移動至組裝區中
          };
          try {
            await updateMaterial(payload);
            console.log(`資料更新成功，id: ${item}`);
          } catch (error) {
            console.error(`資料更新失敗，id: ${item}`, error);
          }
        });
        /*
        let agv1PeriodTime = calculatePeriodTime(agv1StartTime.value, agv1EndTime.value);  // 計算時間間隔
        let formattedStartTime = formatDateTime(agv1StartTime.value);
        let formattedEndTime = formatDateTime(agv1EndTime.value);
        console.log("Formatted AGV Start Time:", formattedStartTime);
        console.log("Formatted AGV End Time:", formattedEndTime);
        console.log("AGV Period time:", agv1PeriodTime);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv1PeriodTime,
          user_id: 'AGV1-2',
          order_num: from_agv_input_order_num.value,
          process_type: 1,
        };
        await createProcess(payload);
        */

        // 記錄AGV狀態資料
        payload = {
          id: 1,
          status: 2,      // 行走中
          station:  2,    // 行走至組裝區
        };
        await updateAGV(payload);

        background.value='#10e810'
      })

      socket.value.on('station2_agv_end', async () => {
        console.log('收到 station2_agv_end 訊息, AGV已到達組裝區!');

        // 記錄agv在站與站之間運行結束時間
        agv2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
        console.log("AGV Start time:", agv2EndTime.value);

        let payload = {};

        selectedItems.value.forEach(async (item) => {
          console.log('selectedItems, item:', item);
          payload = {
            id: item,
            show1_ok: 2,      //組裝站
            show2_ok: 3,      //未組裝
            show3_ok: 3,      //等待組裝中
            whichStation: 2,  //目標途程:組裝站
          };
          await updateMaterialRecord(payload);
        });
        console.log('agv_end 處理步驟1...');

        let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
        let formattedStartTime = formatDateTime(agv2StartTime.value);
        let formattedEndTime = formatDateTime(agv2EndTime.value);
        console.log("AGV 運行 Start Time:", formattedStartTime);
        console.log("AGV 運行 End Time:", formattedEndTime);
        console.log("AGV 運行 Period time:", agv2PeriodTime);

        let payload1 = {};
        let payload2 = {};
        let payload_new = {};

        console.log('agv_end 處理步驟2...');
        selectedItems.value.forEach(async (item) => {
          console.log('selectedItems, item:', item);

          let myMaterial = materials.value.find(m => m.id == item);

          payload1 = {
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: agv2PeriodTime,
            user_id: 'AGV1-2',                        //在備料區('AGV1'), 呼叫AGV的運行時間('-2'), 即簡稱AGV1-2
            order_num: myMaterial.order_num,
            process_type: 2,                          //在組裝區
          };
          await createProcess(payload1);
          console.log('步驟2-1...');

          payload2 = {
            id: item,
            record_name: 'delivery_qty',
            record_data: myMaterial.delivery_qty
          };
          await updateMaterial(payload2);
          console.log('步驟2-2...');

          //if (Number(myMaterial.delivery_qty) !=0 && Number(myMaterial.total_delivery_qty) !=0) {
          payload2 = {
            id: item,
            record_name: 'isShow',
            record_data: true
          };
          await updateMaterial(payload2);
          console.log('步驟2-3...');

          if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
            console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

            let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;

            payload_new = {
              copy_id: myMaterial.id,
              total_delivery_qty: tempDelivery,
              show2_ok: 2,
              shortage_note: '',
            }
            await copyMaterial(payload_new);
            console.log('步驟2-4...');
          }
        });
        // 記錄AGV狀態資料
        payload = {
          id: 1,
          status: 1,      // 準備中
          station:  2,    // 已在組裝區
        };
        await updateAGV(payload);
        console.log('agv_end 處理步驟3...');

        // 插入延遲 3 秒
        await delay(3000);

        isFlashLed.value = false;     //黃綠燈熄滅

        selectedItems.value = [];
        if (localStorage.getItem('selectedItems')) {
          localStorage.removeItem('selectedItems');
        }
        //待待
        window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
      });

      socket.value.on('station2_agv_ready', async () => {
        console.log('AGV 已在組裝區裝卸站, 收到 station2_agv_ready 訊息...');

      });

      socket.value.on('station1_agv_ready', async () => {
        console.log('AGV 已在備料區裝卸站, 收到 station1_agv_ready 訊息...');
        // 記錄等待agv到站結束時間
        agv1EndTime.value = new Date();
        console.log("AGV End time:", agv1EndTime.value);

        let agv1PeriodTime = calculatePeriodTime(agv1StartTime.value, agv1EndTime.value);  // 計算時間間隔
        let formattedStartTime = formatDateTime(agv1StartTime.value);
        let formattedEndTime = formatDateTime(agv1EndTime.value);
        console.log("AGV 等待 Start Time:", formattedStartTime);
        console.log("AGV 等待 End Time:", formattedEndTime);
        console.log("AGV 等待 Period time:", agv1PeriodTime);

        let payload = {};
        // 記錄備料區途程資料, 等待agv時間
        selectedItems.value.forEach(async (item) => {
          let myMaterial = materials.value.find(m => m.id == item);

          payload = {
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: agv1PeriodTime,
            user_id: 'AGV1-1',                        //在備料區('AGV1'), 呼叫AGV的等待時間('-1'), 即簡稱AGV1-1
            order_num: myMaterial.order_num,
            process_type: 1,                          //在備料區
          };
          await createProcess(payload);
        });
        // 記錄AGV狀態資料
        payload = {
          id: 1,
          status: 0,
          station:  1,
        };
        await updateAGV(payload);

        //startFlashing();
        background.value='#ffff00'
        isFlashLed.value = true;
      });

      socket.value.on('agv_ack', async () => {
        console.log('收到 agv_ack 回應');
      });
    } catch (error) {
      console.error('Socket連線失敗:', error);
    }
  });

  //=== unmounted ===
  onUnmounted(() => {   // 清除計時器（當元件卸載時）
    clearInterval(intervalId);
    //clearInterval(intervalIdForLed);
    stopFlashing();
  });

  //=== created ===
  onBeforeMount(() => {
    console.log("Employer, created()...")

    pagination.itemsPerPage = currentUser.value.setting_items_per_page;

    initAxios();
    initialize();
  });

  //=== method ===
  // 定義一個延遲函數
  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const initialize = async () => {
    try {
      console.log("initialize()...");

      // 使用 async/await 等待 API 請求完成，確保順序正確
      await listMaterials();

      await listUsers();

      await listSocketServerIP();
      console.log("initialize, socket_server_ip:", socket_server_ip.value)
    } catch (error) {
      console.error("Error during initialize():", error);
    }
  };

  // 啟動閃爍效果
  //const startFlashing = () => {
  //  console.log("startFlashing()...")
  //
  //  isFlashLed.value = true;
  //  intervalIdForLed = setInterval(() => {
  //    isVisible.value = !isVisible.value; // 每秒切換顯示狀態
  //  }, 500);
  //}

  // 停止閃爍效果
  const stopFlashing = () => {
    console.log("stopFlashing()...")

    clearInterval(intervalIdForLed);
    isVisible.value = true;               // 重設為顯示
    isFlashLed.value = false;
  }
  /*
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
  */
  const refreshComponent = () => {
    console.log('更新訂單按鈕已點擊');

    // 透過重新加載當前路由，來刷新組件
    //router.go(0);

    // 改變 key 值，Vue 會重新渲染整個元件
    componentKey.value += 1;
  };

  const setActive = (value) => {
    toggle_exclusive.value = value; // 設置當前活動按鈕
    if (toggle_exclusive.value == 1)
      showMenu.value = true;
    else
      showMenu.value = false;
  }

  const checkReceiveQty = (item) => {
      console.log("checkReceiveQty,", item);

      // 將輸入值轉換為數字，並確保是有效的數字，否則設為 0
      const deliveryQty = Number(item.delivery_qty) || 0;
      //const totalDeliveryQty = Number(item.total_delivery_qty) || 0;
      //const reqQty = Number(item.req_qty) || 0;
      const totalQty = Number(item.total_delivery_qty) || 0;

      //console.log("deliveryQty > reqQty:", deliveryQty, reqQty)
      console.log("deliveryQty > totalQty:", deliveryQty, totalQty)
      // 檢查是否超過需求數量
      if (deliveryQty > totalQty) {

      //const total = Number(item.delivery_qty) + Number(item.total_delivery_qty);
      //const temp = Number(item.req_qty)
      //if (total > temp) {
        delivery_qty_alarm.value = '備料數量超過應備數量!';
        item.tooltipVisible = true;       // 顯示 Tooltip
        setTimeout(() => {
          item.tooltipVisible = false;    // 2秒後隱藏 Tooltip
          //item.delivery_qty = '';         // 清空輸入欄位
        }, 2000);
        //console.error('送料數量超過需求數量');
      } else {
        item.tooltipVisible = false;
        delivery_qty_alarm.value = '';    // 清除警告
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

  // 如果按下的鍵不是數字，阻止輸入
  if (!/^\d$/.test(inputChar)) {
    event.preventDefault();  // 阻止非數字輸入
    return;
  }

  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 檢查輸入的長度是否超過3，阻止多餘的輸入
  if (inputValue.length >= 3) {
    event.preventDefault();
    return;
  }

    /*

    const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

    // 使用正規化運算式檢查是否為數字且長度不超過3
    //if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
    if (!/^\d$/.test(inputChar) || inputValue.length >= 3) {
      event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
      return;   // 確保阻止後執行中止
    }
    */
    // 偵測是否按下 Enter 鍵
    if (event.key === 'Enter' || event.keyCode === 13) {
      console.log('Return key pressed');
      // 如果需要，這裡可以執行其他操作，或進行額外的驗證
      //checkReceiveQty(event.target.item);  // 檢查接收數量的驗證
    }
  };

  const isSelected = (item) => {
    //console.log("isSelected(), item.columns.id", item.raw, item.columns.id); // 查看 item.columns 是否包含 id
    // 安全檢查，確保 item 和 item.columns 存在
    if (!item || !item.columns || typeof item.columns.id === 'undefined') {
      return false; // 預設未被選中
    }

    return selectedItems.value.includes(item.columns.id); // 根據 columns.id 檢查是否被選中
  };

  const toggleSelect = (item) => {
    //console.log("toggleSelect(), item.columns.id", item.raw, item.columns.id); // 查看 item.columns 是否包含 id
    // 檢查是否已呼叫 AGV
    if (isCallAGV.value) {
      showSnackbar('已呼叫 AGV，工單不能改變！', 'red accent-2');
      return; // 不改變選擇狀態
    }

    const index = selectedItems.value.indexOf(item.columns.id);
    if (index === -1) {
      selectedItems.value.push(item.columns.id); // 若未選中，則添加 columns.id
    } else {
      selectedItems.value.splice(index, 1);     // 若已選中，則移除 columns.id
    }
  };

  const handleEscClose = async () => {
    console.log("Dialog closed via ESC key, item:", selectedItem.value);

    // 記錄當前途程狀態
    let payload = {
      order_num: selectedItem.value.order_num,
      record_name: 'show2_ok',
      record_data: 0                //未備料
    };
    await updateMaterial(payload);
    //updateMaterial(payload).then(data => {
    //  !data && showSnackbar(data.message, 'red accent-2');
    //});

    dialog.value = false;
  };

  const handleOutsideClick = async () => {
    console.log("Dialog closed by clicking outside, item:", selectedItem.value);

    // 記錄當前途程狀態
    let payload = {
      order_num: selectedItem.value.order_num,
      record_name: 'show2_ok',
      record_data: 0                //未備料
    };
    await updateMaterial(payload);
    //updateMaterial(payload).then(data => {
    //  !data && showSnackbar(data.message, 'red accent-2');
    //});

    dialog.value = false;
  };

  const toggleExpand = async (item) => {
    console.log("toggleExpand(),", item.order_num);

    enableDialogBtn.value = item.isTakeOk && !item.isShow;    //備料完成(按確定鍵) && AGV還沒送出

    let payload = {};

    payload = {
      //order_num: item.order_num,
      id: item.id,
    };
    await getBoms(payload);
    current_cell.value = item.delivery_qty
    selectedItem.value = item;
    //console.log("toggleExpand, selectedItem.value", selectedItem.value)

    // 1.記錄當前開始備料時間
    currentStartTime.value = new Date();  // 使用 Date 來記錄當時時間
    console.log("Start time:", currentStartTime.value, item, item.id);

    // 2.記錄當前途程狀態
    payload = {
      id: item.id,
      //order_num: item.order_num,
      record_name: 'show2_ok',
      record_data: 1                //備料中
    };
    await updateMaterial(payload);

    payload = {
      id: item.id,
      //order_num: item.order_num,
      record_name: 'shortage_note',
      record_data: ''
    };
    await updateMaterial(payload);

    dialog.value = true;
  };

  const checkTextEditField = (focused, item) => {
    if (!focused) { // 當失去焦點時
      console.log("checkTextEditField(): 失去焦點");

      //updateItem2(item);
    } else {
      //console.log("checkTextEditField(): 獲得焦點");

    }
  };

  const updateItem2 = async (item) => {
    console.log("updateItem2(),", item);

    let deliveryQty = 0;
    // 檢查是否輸入了空白或 0
    if (!item.delivery_qty || Number(item.delivery_qty) === 0) {
      /*
      console.log("item.delivery_qty:", item.delivery_qty)
      delivery_qty_alarm.value = '送料數量不可為空白或0!'
      item.tooltipVisible = true;       // 顯示 Tooltip 提示
      item.isError = false;             // 設置 isError 為 true，使文字變紅
      setTimeout(() => {
        item.tooltipVisible = false;    // 2秒後隱藏 Tooltip
        item.delivery_qty = '';         // 清空輸入欄位
      }, 2000);
      console.error('送料數量不可為空白或0!');
      return;
      */
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

  const updateItem = async () => {    //編輯 bom, material及process後端table資料
    console.log("updateItem(),", boms.value);

    let my_material_orderNum = boms.value[0].order_num;

    let endTime = new Date();                                               // 記錄當前結束時間
    let periodTime = calculatePeriodTime(currentStartTime.value, endTime);  // 計算時間間隔
    let formattedStartTime = formatDateTime(currentStartTime.value);
    let formattedEndTime = formatDateTime(endTime);

    // 使用 .some() 檢查是否有任何 `receive` 為 false 的項目，若有則將 `take_out` 設為 false
    let take_out = !boms.value.some(bom => !bom.receive);
    console.log("take_out:", take_out);

    // 1. 更新 boms 資料
    let response0 = await updateBoms(boms.value);
    if (!response0) {
      showSnackbar(response0.message, 'red accent-2');
      dialog.value = false;
      return;
    }

    let materialPayload = {}

    if (!take_out) {                    // 該筆訂單檢料未完成, 缺料
      materialPayload = {               // 更新 materials 資料，shortage_note = '(缺料)'
        //order_num: my_material_orderNum,
        id: selectedItem.value.id,
        record_name: 'shortage_note',
        record_data: '(缺料)'
      };
      await updateMaterial(materialPayload);
      selectedItem.value.shortage_note = '(缺料)';

      materialPayload = {               // 2. 更新 materials 資料，isLackMaterial = 1
        //order_num: my_material_orderNum,
        id: selectedItem.value.id,
        record_name: 'isLackMaterial',
        record_data: 0,          //缺料
      };
      await updateMaterial(materialPayload);
      selectedItem.value.isLackMaterial = 0;
    } else {
      materialPayload = {
        //order_num: my_material_orderNum,
        id: selectedItem.value.id,
        record_name: 'shortage_note',
        record_data: ''
      };
      await updateMaterial(materialPayload);
      selectedItem.value.shortage_note = '';

      materialPayload = {
        //order_num: my_material_orderNum,
        id: selectedItem.value.id,
        record_name: 'isLackMaterial',
        record_data: 99,
      };
      await updateMaterial(materialPayload);
      selectedItem.value.isLackMaterial = 0;
    }

    materialPayload = {                       // 2. 更新 materials 資料, 按確定鍵的狀態
      //order_num: my_material_orderNum,
      id: selectedItem.value.id,
      record_name: 'isTakeOk',
      record_data: true
    };
    await updateMaterial(materialPayload);
    selectedItem.value.isTakeOk = true;

    if (take_out) {                     // 該筆訂單檢料完成
      materialPayload = {               // 2. 更新 materials 資料，show2_ok = 2
        //order_num: my_material_orderNum,
        id: selectedItem.value.id,
        record_name: 'show2_ok',
        record_data: 2                  // 設為 2，表示備料完成
      };
      await updateMaterial(materialPayload);

      console.log("Formatted Start Time:", formattedStartTime);
      console.log("Formatted End Time:", formattedEndTime);
      console.log("Period time:", periodTime);
      let processPayload = {
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
    // 記錄等待agv到站開始時間
    agv1StartTime.value = new Date();  // 使用 Date 來記錄當時時間
    console.log("AGV Start time:", agv1StartTime.value);
  };

  const selectEmployee = (emp) => {
    selectedEmployee.value = emp;
    //showMenu.value = false;
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
  const readAllExcelFun = async () => {
    console.log("readAllExcelFun()...");

    if (fileCount.value === 0) {
      console.warn("No files available for import.");
      return;
    }

    try {
      // 等待 readAllExcelFiles 完成
      const excel_file_data = await readAllExcelFiles();
      console.log("data:", excel_file_data);

      if (excel_file_data.status) {
        fileCount.value = 0;
        await deleteAssemblesWithNegativeGoodQty();
        listMaterials();
      } else {
        showSnackbar(excel_file_data.message, 'red accent-2');
      }
    } catch (error) {
      console.error("Error during execution:", error);
      showSnackbar("An error occurred.", 'red accent-2');
    }
  };

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
    //if (debounceTimeout) {
    //  clearTimeout(debounceTimeout);
    //}

    //debounceTimeout = setTimeout(() => {
      snackbar_info.value = message;
      snackbar_color.value = color;
      snackbar.value = true;
    //}, 100); // 防止短時間內重複觸發
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

  //:deep(.v-table.outer .v-table__wrapper) {
  //  overflow-y: hidden;
  //  max-height: 320px;
  //}

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
    background-color: white;              // 確保標題背景與卡片一致
    z-index: 2;                               // 提高z-index以確保標題在其他內容之上
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
    position: relative;         // 讓 sticky 定位相對於這個元素
    max-height: 440px;          // 設定產生滾動條的高度
    overflow-y: auto;           // 允許垂直滾動
  }

  .red-text {
    color: red !important;
  }

  .custom-table {
    border-radius: 0 0 20px 20px;
  }

  .custom-table theader th {
    background-color: #85aef2;    // 自訂背景顏色
  }

  .blinking {
    animation: blink-animation 1s steps(5, start) infinite;
  }

  @keyframes blink-animation {
    to {
      visibility: hidden;
    }
  }


  .light {
    display: inline-block;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    //margin-bottom: 8px;
    //opacity: 0.2;
    //transition: opacity 0.2s;
    position: relative;
  }

  .light span {
    transition: opacity 0.2s;
    color: #fff;
    font-size: 24px;
    position: absolute;
    right: 0;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    text-align: center;
    opacity: 0;
    visibility: hidden;
  }
  .light.active span {
    opacity: 1;
    visibility: visible;
  }
  .active {
    opacity: 1;
  }

  .yellow {
    background: #ffff00;
  /*
  background-color: #ffff00;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  */
  }
  .green {
    background: green;
  }

  :deep(.v-data-table-footer) {
    margin-bottom: -10px;
  }

  .no-footer {
    margin-bottom: 0;           // 沒有頁腳時的底部邊距
  }

  :deep(.custom-table .v-table__wrapper > table > thead > tr > th.v-data-table__th) {
    background-color: #85aef2;      // 自訂背景顏色
  }

  :deep(.custom-table th:nth-child(2)), /* 隱藏標題欄 */
  :deep(.custom-table td:nth-child(2)) { /* 隱藏數據欄 */
    display: none
  }

  :deep(.custom-table thead th:nth-child(1)) {
    padding-left: 16px !important;
  }

  :deep(.custom-table thead th:nth-child(3)) {
    padding-left: 32px !important;
  }

  :deep(.custom-table thead th:nth-child(4)) {
    padding-left: 40px !important;
  }

  :deep(.custom-table thead th:nth-child(5)) {
    padding-left: 32px !important;
  }
  // 資料表
  :deep(.custom-table thead th:nth-child(7)) {
    padding-left: 40px !important;
  }

  // 選擇框
  :deep(span.custom-header) {
    display: block;
    width: 80px;      // 設定最小寬度
  }

  // 輸入欄位 <v-text-field />
  :deep(input[type="text"]) {
    min-height: 20px;
    height:20px;
    opacity: 1;
    padding: 0px;
    text-align: center;
    color: var(--input-text-color);   // 使用 CSS 變數設置顏色
    min-width:60px;
    width:60px;
  }

  :deep(.v-btn-group--density-default.v-btn-group) {
    min-height: 36px;
    height: 36px;
    left: -10px;
    position: relative;
  }

  //.flip_wrapper {
  //  perspective: 800px;
  //}

  //.flip_btn {
  //  position: relative;
  //  top: 3px;
  //  right: 100px;
  //  height: 36px;
  //  width: 100px;
  //  transform-style: preserve-3d;
  //  transition: transform 500ms ease-in-out;
  //  transform: translateZ(-20px);
  //}

  //.flip_btn:hover {
  //    transform: rotateX(-90deg) translateY(20px);
  //}

  //.side {
  //  position: absolute;
  //  backface-visibility: hidden;
  //  width: 100%;
  //  height: 100%;
  //  display: flex;
  //}

  //.default-side {
  //  transform: translateZ(20px);
  //}

  //.hover-side {
  //  transform: rotateX(90deg) translateZ(20px) translateY(-3px);  // 向上移動 3px;
  //}

  // 客製化 手推車/AGV切換按鍵
  .button-container {
    position: relative;
    width: fit-content;     // 可調整寬度以適應按鈕

    right: 100px;
    top: 0px;
  }

  .blue-text {
    color: #0d47a1;   // 設置字體顏色為藍色
    //color: red;
    font-weight: 700;
  }
  </style>
