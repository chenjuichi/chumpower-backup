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

  <ConfirmDialog ref="confirmRef" />

  <v-dialog v-model="scheduling_dialog" max-width="420">
    <v-card>
      <v-card-title style="font-weight: 600">
        <span style="font-size:12px; color:red;">訂單編號{{scheduling_dialog_orde_num}}&nbsp;</span>
        <span style="font-size:18px;color:black;">工序勾選/排序設定</span>
      </v-card-title>
      <v-card-text>
        <div class="d-flex align-center justify-space-between mb-3">
          <span class="text-subtitle-2">工序類型</span>
          <v-switch
            :model-value="scheduleMode === 'check'"
            color="indigo"
                      hide-details
            @update:modelValue="val => switchScheduleMode(val ? 'check' : 'assemble')"
          >
            <template #label>
              <span class="text-subtitle-2" style="font-weight:600; color:black;">
                {{ scheduleMode === 'assemble' ? '組裝工序' : '檢驗工序' }}
              </span>
            </template>
          </v-switch>
        <!--
          <v-radio-group
            :model-value="scheduleMode"
            @update:modelValue="switchScheduleMode"
            inline
            class="d-flex justify-center"
          >
            <v-radio label="組裝工序" value="assemble" class="mr-4" />
            <v-radio label="檢驗工序" value="check" />
          </v-radio-group>
        -->
        </div>

        <div class="text-grey-darken-1 mb-3">
          可勾選工序，並以拖曳改變順序
        </div>

        <div v-auto-animate class="scheduling-list">
          <div v-for="(step, index) in schedulingSteps"
            :key="`${scheduleMode}-${step.id}`"
            class="scheduling-item"
            draggable="true"
            @dragstart="onDragStartStep(index)"
            @dragover="onDragOverStep"
            @drop="onDropStep(index)"
            @dragend="onDragEndStep"
          >
            <div class="scheduling-item-left">
              <v-icon size="18" class="drag-handle me-2">mdi-drag</v-icon>
            <!--
              <v-checkbox
                :model-value="step.checked"
                hide-details
                density="compact"
                class="me-2"

                @click.stop="step.checked = !step.checked"
              />
            -->
              <v-checkbox
                v-model="step.checked"
                hide-details
                density="compact"
                class="me-2"
              />
              <!--<span>{{ index + 1 }}. {{ step.name }}</span>-->
              <span :class="{ 'text-red-darken-2': step.checked }">
                {{ step.name }}
              </span>
            </div>
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="justify-center pb-4">
        <v-btn
          color="error"
          prepend-icon="mdi-close"
          text="取消"
          class="text-none"
          variant="flat"
          @click="closeSchedulingDialog"
        />
        <v-btn
          color="success"
          prepend-icon="mdi-check"
          text="確定"
          class="text-none"
          variant="flat"
          :loading="scheduling_dialog_loading"
          @click="confirmSchedulingDialog"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-data-table
    :headers="headers"
    :items="materials_and_assembles"

    :search="search"
    :custom-filter="customFilter"

    fixed-header
    density="comfortable"
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
    :items-per-page-options="footerOptions"

    item-value="row_key"

    v-model:items-per-page="pagination.itemsPerPage"
    v-model:page="pagination.page"



    :sort-by.sync="sortBy"
    :sort-desc.sync="sortDesc"
    class="elevation-10 custom-table"
  >
    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="d-flex align-center pe-2" style="font-weight:700; min-height:86px; height:86px;">
          組裝區領料生產報工
          <v-divider class="mx-4" inset vertical></v-divider>
          <v-spacer></v-spacer>

           <!-- 組裝區來料異常備註 -->
          <div class="pa-4 text-center">
            <v-dialog v-model="abnormalDialog" max-width="500">
              <!--取消最大高度限制，讓卡片內容可以顯示完整-->
              <!--消自動捲軸，完全依內容高度決定是否超出-->
              <v-card :style="{ maxHeight: 'unset', overflowY: 'unset' }">
                <v-card-title class="text-h6 sticky-title text-center" style="background-color: #1b4965; color: white;">
                  組裝區來料異常備註
                </v-card-title>

                <v-card-text>
                  <!-- 若 Incoming1_Abnormal 為 true，顯示第1與第2行 -->
                  <template v-if="abnormalDialog_display">
                    <v-row style="margin-bottom: 4px;" dense justify="center">
                      <v-col cols="4" class="pa-0">訂單編號</v-col>
                      <v-col cols="4" class="pa-0">來料數量</v-col>
                      <v-col cols="4" class="pa-0">實際數量</v-col>
                    </v-row>
                    <v-row dense>
                      <v-col cols="4" class="pa-0">{{ abnormalDialog_order_num }}</v-col>
                      <v-col cols="4" class="pa-0">{{ abnormalDialog_delivery_qty }}</v-col>
                      <v-col cols="4" class="pa-0">
                        <v-text-field
                          v-model="abnormalDialog_new_must_receive_qty"
                          variant="underlined"
                          style="max-width: 60px;"
                        />
                      </v-col>
                    </v-row>
                  </template>
                  <!-- 顯示第3行 -->
                  <template v-else>
                    <v-row style="margin-bottom: 4px;" dense justify="center">
                      {{ abnormalDialog_message }}
                    </v-row>
                    </template>
                </v-card-text>

                <v-card-actions class="justify-center">
                  <v-btn
                    color="success"
                    prepend-icon="mdi-content-save"

                    text="確定"
                    class="text-none"
                    @click="createAbnormalFun"
                    variant="flat"
                  />
                  <v-btn
                    color="error"
                    prepend-icon="mdi-close"
                    text="取消"
                    class="text-none"
                    @click="abnormalDialog = false"
                    variant="flat"
                  />
                </v-card-actions>
              </v-card>
            </v-dialog>
          </div>

          <v-row
            class="ma-0 toolbar-row"
            align="center"
            no-gutters
            style="position:relative; left:-45px; top:22px; height:48px;"
          >
            <!--日期範圍-->
            <v-col cols="auto">
              <div class="date-slot">
              <Transition name="slide">
                <!--<div v-if="showFields" class="date-box">-->
                <div class="date-box">
                  <v-menu
                    v-model="menuOpen"
                    :close-on-content-click="false"
                    location="bottom start"
                    origin="top start"
                    :offset="[0, 8]"
                    :width="480"
                    :min-width="480"
                    transition="fade-transition"
                    :open-on-focus="false"
                    :open-on-hover="false"
                  >
                    <template #activator="{ props }">
                      <v-text-field
                        v-bind="props"
                        label="交期範圍"
                        v-model="formattedDateRange"
                        readonly
                        variant="underlined"
                        density="compact"

                        :placeholder="dateFieldActive ? 'yyyy-mm-dd ~ yyyy-mm-dd' : ''"
                        prepend-icon="mdi-calendar-check"

                        class="dateicon date-range-field"
                        clearable
                        hide-details

                        @click="openDateMenu"
                        @focus="dateFieldActive = true"
                        @blur="dateFieldActive = false"
                        @click:clear="clearDates"
                      />
                    </template>

                    <div class="dp-stretch">
                      <VueDatePicker
                        :key="menuKey"
                        :start-date="today"
                        v-model="dpRange2"
                        :enable-time-picker="false"
                        range
                        :inline="true"
                        :auto-apply="true"
                        locale="zh-TW"
                        week-num-name=""
                        :day-names="['星期一','星期二','星期三','星期四','星期五','星期六','星期日']"
                      />
                    </div>
                  </v-menu>
                </div>
              </Transition>
              </div>
            </v-col>

            <v-col cols="auto">
              <div class="batch-slot" v-if="hasDpRange2">

                <v-btn
                  v-if="!showBatchActions"
                  style="background:#E3F2FD !important;"
                  class="thin"
                  :disabled="isInformationEmpty"
                  @click="onClickBatchDelete"
                >
                  <v-icon left color="green" style="font-weight:700;">
                    mdi-sticker-remove-outline
                  </v-icon>
                  <span style="color:black; font-weight:600;">整批刪除</span>
                </v-btn>

                <!-- ===== 狀態2：取消 / 確定 ===== -->
                <div
                  v-else
                  class="batch-actions"
                >
                  <!-- 取消 -->
                  <v-btn
                    class="action-btn"
                    :disabled="isInformationEmpty"
                    @click="onCancelBatchDelete"
                  >
                    <v-icon left color="#ff0000">
                      mdi-window-close
                    </v-icon>
                    <span style="color:black; font-weight:600;">取消</span>
                  </v-btn>

                  <!-- 確定 -->
                  <v-btn
                    class="action-btn"
                    :disabled="isInformationEmpty"
                    @click="onConfirmBatchDelete"
                  >
                    <v-icon left color="green">
                      mdi-check
                    </v-icon>
                    <span style="color:black; font-weight:600;">確定</span>
                  </v-btn>
                </div>

              </div>
            </v-col>

            <!--客製化搜尋輸入框-->
            <v-col cols="auto">
              <div class="search-slot">
                <v-text-field
                  v-model="search"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  hide-details
                  label="全文搜尋"
                  single-line
                  density="compact"
                  class="toolbar-field toolbar-field--24 search-field"
                />
              </div>
            </v-col>

            <!-- 客製化barcode輸入框 -->
            <v-col cols="auto">
              <div class="barcode-slot">
                <v-text-field
                  id="bar_code"
                  v-model="bar_code"
                  :value="bar_code"
                  ref="barcodeInput"
                  @keyup.enter="handleBarCode"
                  hide-details="auto"
                  prepend-icon="mdi-barcode"

                  density="compact"
                  class="toolbar-field toolbar-field--24 barcode-field"
                />
              </div>
            </v-col>
          </v-row>
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

    <!-- 客製化 '物料編號' (material_num) 欄位的表頭 -->
    <template v-slot:header.material_num="{ column }">
      <div style="left:20px; position:relative;">{{ column.title }}</div>
    </template>

    <!-- 客製化 '需求數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div>需求</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '備料數量' (delivery_qty) 欄位的表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div>備料</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '應領取數量' (must_receive_qty) 欄位的表頭 -->
    <template v-slot:header.must_receive_qty="{ column }">
      <div style="text-align: center;">
        <div>應領取</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位的資料欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div>
        <!--<div style="color:black; font-size:12px; margin-right:2px;" v-if="item.isLackMaterial != 99">-->
        <div
          style="color:black; font-size:12px; margin-right:2px;"
          v-if="(String(item.shortage_note || '').includes('缺料') || item.isLackMaterial != 99) &&
          item.has_receive_true < item.has_bom" >

          <v-icon
            style="color: green;"
            @click.stop="onDelete(item)"
            small
          >
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}&nbsp;&nbsp;
          <span style="color:red; font-weight:700; font-size:12px;">缺料</span>
        </div>
        <div style="color:black; font-size:12px; margin-right:20px; margin-left: -15px;" v-else>
          <v-icon
            style="color: green;"
            @click.stop="onDelete(item)"
            small
          >
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}
        </div>
        <!--<div style="color: #a6a6a6; font-size:12px; margin-right: 10px;">{{ item.assemble_work }}</div>-->
        <div style="color: #a6a6a6; font-size:12px; margin-right: 10px;">
          {{ item.assemble_work }}
          <span v-if="getScheduleName(item)" style="font-weight:600; font-size:12px; color:black;"> [{{ getScheduleName(item) }}]</span>
          <!--<span v-if="item.alarm_enable" style="font-weight:600; font-size:12px; color:red;">-異常</span>-->
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

    <!-- 自訂 '應領取數量'欄位的資料欄位 -->
    <template v-slot:item.must_receive_qty="{ item }">
      <div style="display: flex; align-items: center;">
        <template v-if="item.process_step_code == 3 && item.is_copied_from_id == null && item.begin_records == 0"> <!--組裝途程-->
          <v-icon
            style="transition: opacity 0.3s ease, visibility 0.3s ease;  margin-left: -10px;"
            @click="addAbnormalInMaterial(item)"
            size="16"
            class="mr-2"
            :color="item.Incoming1_Abnormal ? 'light-blue lighten-3':'red lighten-4'"

          >
            mdi-bell-plus
          </v-icon>
          <span style="margin-left: 15px;">
            {{ item.must_receive_qty }}
          </span>
        </template>
        <template v-else>
          <span style="margin-left: 25px;">
            {{ item.must_receive_qty }}
          </span>
        </template>
        <!--
        <span style="margin-left: 15px;">
          {{ item.must_receive_qty }}
        </span>
        -->
      </div>
    </template>

    <!-- 自訂 '說明' 欄位的資料欄位 -->
    <template v-slot:item.comment="{ item }">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span
            class="ellipsis-cell"
            v-bind="props"
          >
            {{ item.comment || '' }}
          </span>
        </template>
        <div class="tooltip-content">
          {{ item.comment || '' }}
        </div>
      </v-tooltip>
    </template>

    <!-- 自訂 gif 按鍵欄位 -->
    <template v-slot:item.gif="{ item, index }">
      <v-hover v-slot:default="{ isHovering, props }">
        <div
          v-bind="props"
          style="position: relative; display: inline-block;"
          @mouseenter="handleGifClick(item, index); hoveredItemIndex = index; isTableVisible = true;"
          @mouseleave="hoveredItemIndex = null; isTableVisible = false;"
        >
          <img
            v-if="!isGifDisabled(item)"
            :src="isHovering ? animationImageSrc : staticImageSrc"
            alt="GIF"
            style="width: 25px; height: 25px;"
          />
          <!-- 動態顯示表格 -->
          <div
            v-if="isTableVisible && boms.length > 0 && !isGifDisabled(item)"
            :style="adjustTablePosition"
          >
            <v-table style="width: 190px; overflow: hidden;" class="show_table">
              <thead>
                <tr>
                  <th style="text-align: left;">編號</th>
                  <th style="text-align: right;">數量</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(bom_item, index) in filteredBoms"
                  :key="index"
                  :style="{backgroundColor: index % 2 === 0 ? '#ffffff' : '#edf2f4'}"
                  class="custom-row"
                >
                  <td style="text-align: left;">{{ bom_item.material_num }}</td>
                  <td style="text-align: right;">{{ bom_item.qty }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <td colspan="2">
                    共 {{ filteredBoms.length }} 項
                  </td>
                </tr>
              </tfoot>
            </v-table>
          </div>
        </div>
      </v-hover>
    </template>

    <!-- 自訂 '+工序' 按鍵欄位 -->
  <!--
    <template #item.add_process="{ item }">
      <v-btn
        size="small"
        class="btn-add-process"
        :class="{ 'btn-add-process--disabled': item.process_step_enable }"
        :disabled="checkBegin(item)"
        @click="openSchedulingDialog(item)"
      >
        +工序
      </v-btn>
    </template>
  -->
    <template #item.add_process="{ item }">
      <v-btn
        size="small"
        class="btn-add-process"
        :class="{ 'btn-add-process--disabled': isProcessStepEnabled(item) }"
        :disabled="isAddProcessDisabledV2(item) ||
                   item.top_work_rank != item.process_step_code ||
                   item.delivery_qty != item.must_receive_qty"
        @click="openSchedulingDialog(item)"
      >
        +工序
      </v-btn>
    </template>

    <!-- 自訂 '-工序' 按鍵欄位 -->
  <!--
    <template #item.remove_process="{ item }">
      <v-btn
        size="small"
        class="btn-remove-process"
        :class="{ 'btn-remove-process--disabled': !item.process_step_enable }"
        :disabled="!item.process_step_enable"
        @click="removeSchedulingDialog(item)"
      >
        -工序
      </v-btn>
    </template>
  -->

    <!-- 自訂 '開始' 按鍵欄位 -->
    <template #item.action="{ item }">
      <!-- 開始鍵左側顯示「自己」的計時值 -->
      <div class="begin-cell">
        <div class="begin-timer-slot">
          <span
            v-if="item._showMyTimer || isMineStarted(item) || item.show_name == userId"
            class="begin-timer-text"
          >
            <TimerDisplay
              :fontSize="18"
              :autoStart="false"
              :show="true"
              :key="`${item.id}:${item.assemble_id}:${processTypeOf(item)}:${safeUserId}`"
              :ref="el => setTimerEl(item, el)"
              :isPaused="isPausedOf(item)"
              @update:isPaused="val => setPausedOf(item, val)"
              @update:time="ms => onTickOf(item, ms)"
              class="begin-timer"
            />
          </span>
        </div>
        <!-- 綠點：這筆「有人」在開工（不限本人） -->
        <!--
        <v-badge
          :key="`badge-${item.index}-${item.count}`"
          v-bind="badgeProps(item)"
          :content="item.count"
          color="green"
          offset-x="6"
          offset-y="6"
          class="me-1"
        >
        -->
          <v-btn
            size="small"
            variant="tonal"
            class="begin-btn"
            :class="{ 'begin-btn--disabled': !canBeginBySchedule(item) }"
            :disabled="!canBeginBySchedule(item)"

            @click="onClickBegin(item)"
            prepend-icon = "mdi-play"

          >
            <v-icon start style="font-weight:700;">mdi-timer-outline</v-icon>
            開 始
          </v-btn>
        <!--
        </v-badge>
        -->
      </div>
    </template>

    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>
</div>
</template>

<script setup>
import { ref, reactive, nextTick, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount, onDeactivated } from 'vue';

import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
dayjs.extend(isSameOrBefore);             //啟用 plugin

import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

import { onBeforeRouteLeave } from 'vue-router';

import TimerDisplay from "./TimerDisplayBegin.vue";
import { useProcessTimer } from "../mixins/useProcessTimerBegin.js";
import ConfirmDialog from "./confirmDialog";

import eventBus from '../mixins/enentBus.js';

import { useRoute } from 'vue-router';

const search = ref('');

import { useRouter } from 'vue-router';
const router = useRouter();

// +++
const isFlipped = ref(false);

const showFields = ref(false);            // 用來控制是否顯示額外的excel btn欄位
const menuOpen = ref(false)
const today = new Date()
const menuKey = ref(0)
const settingDefaultRange = ref(false)

const dpRange2 = ref([])
const formattedDateRange = ref('')    // 綁給 <v-text-field>
const dateFieldActive = ref(false)

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { materials_and_assembles, assembles_active_user_count, boms,  socket_server_ip }  from '../mixins/crud.js';
//import { temp_isLackMaterial }  from '../mixins/crud.js';
//import { begin_count, end_count }  from '../mixins/crud.js';
import { apiOperation, setupGetBomsWatcher }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listMaterialsAndAssembles = apiOperation('get', '/listMaterialsAndAssembles');
//const listWaitForAssemble = apiOperation('get', '/listWaitForAssemble');
//const listSocketServerIP = apiOperation('get', '/listSocketServerIP');

const updateAssembleMustReceiveQtyByMaterialIDAndDate = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialIDAndDate');

//const copyAssemble = apiOperation('post', '/copyAssemble');
const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateAssembleScheduleRows = apiOperation('post', '/updateAssembleScheduleRows');
//const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
//const createProcess = apiOperation('post', '/createProcess');
const getBoms = apiOperation('post', '/getBoms');

const getOrderPickedBoms = apiOperation('post', '/getOrderPickedBoms');

//const updateAssembleAlarmMessage = apiOperation('post', '/updateAssembleAlarmMessage');
//const getActiveCountMap = apiOperation('post', '/getActiveCountMap');
//const getCountMaterialsAndAssemblesByUser = apiOperation('post', '/getCountMaterialsAndAssemblesByUser');

const removeMaterialsAndRelationTable = apiOperation('post', '/removeMaterialsAndRelationTable');
const removeMaterialsAndRelationTableByDeliveryDateRange = apiOperation('post', '/removeMaterialsAndRelationTableByDeliveryDateRange');

//const getMaterialsAndAssembles = apiOperation('post', '/getMaterialsAndAssembles');

//=== component name ==
defineComponent({ name: 'PickReportForAssembleBegin' });

//=== mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
// 刪除對話框相關
const deleteTitle = ref('刪除工單');
const deleteMessage = ref('此操作將刪除相關資料(BOM/Assemble/Process)，確定？');
const confirmRef = ref(null);

const animationImageSrc = ref(require('../assets/document-hover-swipe.gif'));
const staticImageSrc = ref(require('../assets/document-hover-swipe.png'));
const inputIDs = ref([]);

const myBoms = ref([]);

const showBackWarning = ref(true);

const station2_trans_ready = ref(false);    // false:堆高機沒有動作

const requiredRule = value => !!value || '必須輸入資料...';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';

const bar_code = ref('');
const barcodeInput = ref(null);

const hoveredItemIndex = ref(null); // 追蹤目前懸停在哪一筆資料上的 index
const isTableVisible = ref(false);  // 用來控制表格是否顯示
// 滑鼠位置(x, y)
const mouseX = ref(0);
const mouseY = ref(0);

const route = useRoute();   // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

//            0         1        2          3        4            5           6            7           8            9
//const str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '雷射作業中', 'aa/bb/00', '檢驗作業中', 'aa/bb/cc',]
const str2=['未備料', '備料中', '備料完成', '未組裝', '組裝作業中', 'aa/00/00', '檢驗作業中', 'aa/bb/cc', '雷射作業中', 'aa/bb/00',]

const headers = [
  { title: '訂單編號', sortable: true, key: 'order_num', width:220 },
  { title: '物料編號', sortable: false, key: 'material_num', width:160},
  { title: '需求數量', sortable: false, key: 'req_qty', width:60 },
  { title: '備料數量', sortable: false, key: 'delivery_qty', width:60 },
  { title: '應領取數量', sortable: false, key: 'must_receive_qty', width:100 },  // 2025-06-13 add, 改順序
  //{ title: '領取數量', sortable: false, key: 'receive_qty' },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:120 },
  { title: '交期', align: 'start', sortable: false, key: 'delivery_date', width:100 },
  { title: '', sortable: false, key: 'gif' },
  { title: '', sortable: false, key: 'add_process' },
  //{ title: '', sortable: false, key: 'remove_process' },
  { title: '', sortable: false, key: 'action' },
];
// 初始化Socket連接
const app_user_id = 'user_chumpower';
const clientAppName = 'PickReportForAssembleBegin';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user_id, clientAppName);

// 排序欄位及方向（需為陣列）
const sortBy = ref(['order_num'])
const sortDesc = ref([false])

const outputStatus = ref({
  step1: null,
  step2: null
});

const currentUser = ref(null);

const componentKey = ref(0) // key 值用於強制重新渲染

const safeUserId = computed(() => String(currentUser.value?.empID ?? '').trim());
const userId = computed(() => safeUserId.value);

function loadCurrentUser() {
  let userRaw = sessionStorage.getItem('auth_user');

  if (!userRaw) {
    userRaw = localStorage.getItem('loginedUser');
    if (userRaw) {
      sessionStorage.setItem('auth_user', userRaw);
    }
  }

  try {
    currentUser.value = userRaw ? JSON.parse(userRaw) : null;
  } catch (e) {
    console.error('loadCurrentUser parse failed:', e, userRaw);
    currentUser.value = null;
  }
}

const pagination = reactive({
  itemsPerPage: 5,              // 預設值, rows/per page
  page: 1,
});

const highlightedRowId = ref(null)
//const currentPage = ref(1)
//const itemsPerPage = ref(10)   // 依你實際綁定值

const panelX = ref(820);
const panelY = ref(10);
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

const screenSizeInInches = ref(null);

const abnormalDialogBtnDisable = ref(true);
const abnormalDialog = ref(false);
const abnormalDialog_order_num = ref('');
const abnormalDialog_delivery_qty = ref('');
const abnormalDialog_must_receive_qty = ref('');
const abnormalDialog_new_must_receive_qty = ref('');
const abnormalDialog_message = ref('');
const abnormalDialog_display = ref(true);

const abnormalDialog_record = ref(null);

const scheduling_dialog = ref(false);
const scheduling_target_item = ref(null);
const scheduling_dialog_loading = ref(false);
const scheduling_dialog_orde_num = ref('');
const schedulingSteps = ref([])   // dialog 內顯示的工序清單
const dragFromIndex = ref(null)   // 記錄拖曳來源 index

// ===== 預設工序 =====
const assemble_steps = ref([
  /*
  { id: 1, name: 'a1', checked: true },
  { id: 2, name: 'a2', checked: true },
  { id: 3, name: 'a3', checked: false },
  { id: 4, name: 'a4', checked: false },
  { id: 5, name: 'a5', checked: false },
  { id: 6, name: 'a6', checked: false },
  { id: 7, name: 'a7', checked: false },
  { id: 8, name: 'a8', checked: false },
  */
])

const check_steps = ref([
  /*
  { id: 1, name: 't1', checked: true },
  { id: 2, name: 't2', checked: true },
  { id: 3, name: 't3', checked: false },
  { id: 4, name: 't4', checked: false },
  { id: 5, name: 't5', checked: false },
  { id: 6, name: 't6', checked: false },
  { id: 7, name: 't7', checked: true },
  { id: 8, name: 't8', checked: true },
  */
])
const scheduleMode = ref('assemble')  // 工序模式（assemble / check）

const refreshing = ref(false);

const timerMap = new Map();

let __disposedAll = false;

const PROCESS_TYPES = ['21', '22', '23']
const countsByType = ref({ '21': {}, '22': {}, '23': {} })
const activeMap = reactive({
  '21': {}, '22': {}, '23': {}
})

const selectedAsmId = ref(null);

// 控制是否顯示 確定/取消
const showBatchActions = ref(false)

//=== watch ===
setupGetBomsWatcher();

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

watch(menuOpen, (open) => {
  if (open) {
    // 每次開都回今天那個月
    menuKey.value++

    //如果希望「使用者已經選過日期就不要覆蓋」
    if (!dpRange2.value?.[0] || !dpRange2.value?.[1]) {
      // 每次開都預設今天~+7天
      setDefaultRange()
    }
  }
})

watch(() => pagination.itemsPerPage, (val) => {
  if (!currentUser.value?.empID) return

  currentUser.value.setting_items_per_page = Number(val) || 10

  localStorage.setItem('loginedUser', JSON.stringify(currentUser.value))
  sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value))
},

{ immediate: true }
)

watch(() => safeUserId.value, async (uid) => {
  if (!uid) return;

  console.log('[safeUserId watcher] current user ready:', uid);

  await nextTick();

  if ((materials_and_assembles.value || []).length > 0) {
    await restoreActiveTimersOnly();
  }
},

{ immediate: true }
);

// 畫面控制
watch(dpRange2, ([start, end]) => {
  if (settingDefaultRange.value) return   // ✅ 預設值時不關 menu

  if (start && end) {
    formattedDateRange.value = `${fmt(start)} ~ ${fmt(end)}`
    menuOpen.value = false                 // ✅ 使用者選完才關
  }
})

/*
const hasDpRange2 = computed(() => {
  return Array.isArray(dpRange2.value) &&
    dpRange2.value.length > 0 &&
    dpRange2.value.every(v => !!v);
});
*/
const hasDpRange2 = computed(() => {
  return Array.isArray(dpRange2.value)
    && dpRange2.value.length === 2
    && !!dpRange2.value[0]
    && !!dpRange2.value[1]
})

watch(hasDpRange2, (val) => {
  if (!val) {
    showFields.value = false
  }
})

//=== computed ===

const isInformationEmpty = computed(() => {
  return materials_and_assembles.value.length === 0;
});

const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0',
}));

const routeName = computed(() => route.name);

// 計算懸浮表格的位置，根據資料筆數動態調整高度
const adjustTablePosition = computed(() => ({
  position: 'fixed',
  //top: `${mouseY.value + 10}px`,
  //left: `${mouseX.value - 150}px`,

  top: '130px',      // 固定上邊距離
  right: '225px',   // 固定左邊距離

  backgroundColor: 'white',
  padding: '5px',
  borderRadius: '5px',
  boxShadow: '0px 2px 10px rgba(0, 0, 0, 0.1)',
  fontSize: '10px',
  color: '#333',
  whiteSpace: 'nowrap',
  width: '190px',
  zIndex: 999,
  margin: '0 3px',
  height: `${boms.length * 15}px`, // 根據資料筆數動態調整高度
  overflowY: 'hidden', // 禁止垂直滾動條
  overflowX: 'hidden', // 禁止水平滾動條
}));

const filteredBoms = computed(() =>
  boms.value.filter(item => item.receive)
);

// index -> idx (0-based)
const indexToIdx = computed(() => {
  return new Map(
    materials_and_assembles.value.map((item, i) => [item.index, i]),
  );
});

// index -> count
const indexToCount = computed(() => {
  const m = new Map();
  const rows = materials_and_assembles.value ?? [];
  const counts = assembles_active_user_count.value ?? [];
  for (let i = 0; i < rows.length; i++) {
    m.set(rows[i].index, Number(counts[i] ?? 0));
  }
  return m;
});

//=== mounted ===
onMounted(async () => {
  console.log("PickReportForAssembleBegin.vue, mounted()...");

  // 通知合併工單顯示, 進行handleMaterialUpdate
  eventBus.on('merge_work_orders', handleMaterialUpdate);

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);

  if (screenSizeInInches.value != null) {
    panelX.value = screenSizeInInches.value > 20 ? 1250 : 625;
    panelY.value = screenSizeInInches.value > 20 ? 21 : 21;
  }
  //+++

  // 阻止直接後退，但保留 Vue Router 的 state
  window.history.replaceState(window.history.state, '', document.URL);
  window.addEventListener('popstate', handlePopState)

  console.log("current routeName:", routeName.value);

  //user define
  loadCurrentUser();

  if (currentUser.value?.empID) {
    pagination.itemsPerPage = Number(currentUser.value.setting_items_per_page) || 5
    currentUser.value.setting_lastRoutingName = routeName.value

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }

  console.log("currentUser:", safeUserId.value || '(empty)');

  // 取得每個 v-text-field 的唯一 ID
  inputIDs.value.forEach((item) => {
    const myIdField = document.getElementById(`receiveQtyID-${item.assemble_id}`);
    myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  });

  // 在組件掛載時添加事件監聽器
  window.addEventListener('mousemove', updateMousePosition);

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }

  await safeRefresh();

  materials_and_assembles.value = materials_and_assembles.value.map(it => ({
    ...it,
    pickBegin: Array.isArray(it.pickBegin) ? [...it.pickBegin] : [],
    count: typeof it.count === 'number' ? it.count : 0,
  }))

  materials_and_assembles.value.forEach(r => getT(r))     // 先建好 t
  await nextTick()

  if (safeUserId.value) {         // 逐列 t.restoreProcess(...)
    await restoreActiveTimersOnly();
  } else {
    console.warn('[mounted] skip initial restore: current user not ready');
  }

  //處理socket連線
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();
    // 燈號
    socket.value.on('station2_loading_ready', async(data) => {
      const num = parseInt(data.message, 10);

      activeColor.value='yellow';  // 物料進站

      if ([1, 2, 3].includes(num)) {
        const temp_msg = `物料已經進入第${num}號裝卸站!`;
        console.warn(temp_msg);
        //activeColor.value='yello';  // 物料進站
        //showSnackbar(temp_msg, 'yellow lighten-5');
      } else {
        console.error('接收到不合法的裝卸站號碼:', data.message);
      }
    });
    // 燈號
    socket.value.on('station2_agv_begin', async () => {
      activeColor.value='SeaGreen';   // 物料出站
    })
    // 燈號
    socket.value.on('station3_agv_end', async (data) => {
      activeColor.value='DarkOrange';   //物料送達成品區
    })
    // 燈號
    socket.value.on('station1_agv_ready', async () => {
      activeColor.value='blue';   // 機器人進入組裝區
    })

    socket.value.on('station2_trans_ready', async (data) => {
      console.log("收到 station2_trans_ready訊息...", data);

      station2_trans_ready.value = true;
      forkliftNoticeFun();

      await safeRefresh();
    })

    socket.value.on('triggerLogout', async (data) => {
      console.log("收到 triggerLogout 強迫登出訊息，empID:", data.empID, "目前 empID:", currentUser.value.empID);

      if (data.empID && data.empID === currentUser.value.empID) {
        console.log("本裝置符合 empID，執行強制登出流程");

        let payload = {
          itemsPerPage: 0,
          seeIsOk: '0',
          lastRoutingName: 'Main',
          empID: currentUser.value.empID,
        };

        try {
          await updateSetting(payload);
        } finally {
          localStorage.setItem('Authenticated', false);
          removelocalStorage();
          //#
          sessionStorage.removeItem('auth_user');  // 刪掉使用者
          //#
          const resolvedRoute = router.resolve({ name: 'LoginRegister' });
          const path = resolvedRoute.href;
          console.log('triggerLogout socket...', path)
          router.replace({ path });
        }
      } else {
        console.log("本裝置 empID 不符，忽略此 triggerLogout");
      }
    });
  } catch (error) {
    console.error('Socket連線失敗:', error);
  }
});

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時）
  window.removeEventListener('popstate', handlePopState)

  window.removeEventListener('mousemove', updateMousePosition);

  eventBus.off('merge_work_orders', handleMaterialUpdate)

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);
  //+++

  disposeAllTimersOnce();
});

// 在各種離開情境下都要收尾
onBeforeRouteLeave(() => { disposeAllTimersOnce(); });

onDeactivated(() => { disposeAllTimersOnce(); });

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  initAxios();
});

onBeforeUnmount(() => {

});

//=== method ===
const deepClone = (arr) => JSON.parse(JSON.stringify(arr || []))

/*
function parseProcessStepsV2(str) {
  const result = {
    assemble_steps: [],
    check_steps: [],
  }

  if (!str || typeof str !== 'string') return result

  const parts = str.split(';')

  const parsePart = (part) => {
    if (!part || !part.trim()) return []

    return part
      .split(',')
      .map(x => x.trim())
      .filter(Boolean)
      .map(item => {
        const arr = item.split(':')

        if (arr.length < 3) return null

        const id = arr[0].trim()
        const name = arr[1].trim()
        const checkedRaw = arr[2].trim().toLowerCase()

        return {
          id: Number(id) || id,
          name,
          checked: checkedRaw === 't',
        }
      })
      .filter(Boolean)
  }

  result.assemble_steps = parsePart(parts[0] || '')
  result.check_steps = parsePart(parts[1] || '')

  return result
}
*/

const fmt = (d) => {
  if (!d) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const batchRemoveRecords = async () => {
  console.log('batchRemoveRecords()...');

  showFields.value = false;
};

const openDateMenu = () => {
  menuOpen.value = true
  showFields.value = true
}

const runQuery = async () => {
  const payload = buildListInformationsPayload();
  await listInformations(payload);
};

const runQueryDebounced = () => {
  if (_qTimer) clearTimeout(_qTimer);
  _qTimer = setTimeout(runQuery, 200);
};

// 加天數
const addDays = (date, days)=>{
  const d = new Date(date)
  d.setDate(d.getDate()+days)
  return d
}

// 設定預設區間（今天~7天）
const setDefaultRange = ()=>{
  const start = new Date()
  const end   = addDays(start, 7)

  settingDefaultRange.value = true
  dpRange2.value = [start, end]

  formattedDateRange.value = `${fmt(start)} ~ ${fmt(end)}`

  // 下一個 tick 再解除旗標，避免 watcher 立刻關 menu
  queueMicrotask(() => {
    settingDefaultRange.value = false
  })
}

const clearDates = () => {
  dpRange2.value = [null, null]
  formattedDateRange.value = ''
  menuKey.value++            // ✅ 重新掛載，避免卡在奇怪月份
}

// ===

const KEY = 'material' // 'material' 或 'assemble'

const keyOf = (row, uId) => `${row.id}:${row.assemble_id}:${processTypeOf(row)}:${uId}`

//const getT = (row) => useRowTimer(row, currentUser.value.empID)
const getT = (row) => {
  const uid = safeUserId.value;
  if (!uid) return makeStub();
  return useRowTimer(row, uid);
};

function setTimerEl(row, el) {
  if (!row || !row.id) {
    console.warn('setTimerEl(): row undefined', row)
    return
  }
  const t = getT(row);
  if (t)
    t.timerRef.value = el || null;
}

// ---- 收尾清理（Begin 專用：含輪詢計時器）----
function disposeAllTimersOnce() {
  if (__disposedAll) return;
  __disposedAll = true;

  try {
    // 1) 逐一釋放每列的 useProcessTimer 實例
    for (const t of timerMap.values()) {
      try { t?.dispose?.(); } catch (_e) {}
    }
  } finally {
    timerMap.clear();
  }
}

// 下面這三個轉接器, 可避免在模板裡出現「函式呼叫＋屬性賦值」，VS Code 會比較乾淨

// 取得／設定 isPaused（避免在模板裡對函式呼叫結果賦值）
//const isPausedOf = (row) => getT(row).isPaused
const isPausedOf  = (row) => getT(row)?.isPaused.value ?? true;

const setPausedOf = (row, v) => {
  const t = getT(row);

  //透過雙重否定，強制把任何輸入轉成純布林（truthy → true，falsy → false）
  //例如 1/"yes" 會變 true，0/""/null/undefined 會變 false
  //如果 t 存在且有 isPaused 這個 ref，就把它的值設成布林化後的 v
  if (t?.isPaused) t.isPaused.value = !!v
}

// 轉接 onTick（避免直接把函式呼叫結果當 handler）
const onTickOf = (row, ms) => {
  console.log("onTickOf..")

  const t = getT(row)
  t?.onTick?.(ms)
}

function onTimeUpdate(row, ms) {
  onTickOf(row, ms)
}

// 依 row.process_step_code → process_type
function processTypeOf(row) {
  console.log("processTypeOf:", row.process_step_code)

  const step = Number(row.process_step_code ?? 0)
  const work = row.assemble_work
  if (step === 3 || (step === 0 && work.includes('B109'))) return 21  // 組裝
  if (step === 2 || (step === 0 && work.includes('B110'))) return 22  // 檢驗
  if (step === 1 || (step === 0 && work.includes('B106'))) return 23  // 雷射
}

// 以 material 為粒度，idKey 取 material_id（列表裡是 id=material.id）
// 若後端已支援 assemble 粒度，改成 row.assemble_id 並把 key 換成 'assemble'
function idOf(row) {
  return row.id;
}

async function restoreAllMyTimers() {
  const me = safeUserId.value;      // 登入人員代號
  if (!me) {
    console.warn('[restoreAllMyTimers] skip: current user not ready');
    return;
  }

  const rows = materials_and_assembles.value || []
  for (const row of rows) {
    const t = getT(row)
    console.log("t:", t)
    if (!t?.restoreProcess) continue
    try {
      // 讓後端回傳 elapsed / paused 狀態；restoreOnly=true 不會重寫 begin_time
      await t.restoreProcess(row.id, processTypeOf(row), me, row.assemble_id)
      // useProcessTimerBegin.js 內已處理：paused 就 pause；running 就啟動本地 ticker + autoUpdate
    } catch (e) {
      console.warn('restore fail for row', row.id, e)
    }
  }
}

const shouldRestoreRow = (row) => {
  const me = safeUserId.value;
  if (!me || !row) return false;

  const sameUser =
    String(row.isOpenEmpId ?? '') === me ||
    String(row.show_name ?? '') === me ||
    String(row.user_id ?? '') === me ||
    String(row.process_user_id ?? '') === me;

  const started =
    row.hasStarted === true ||
    row.hasStarted === 1 ||
    row.hasStarted === '1' ||
    row.startStatus === true ||
    row.startStatus === 1 ||
    row.startStatus === '1' ||
    row.show_timer === true ||
    row.show_timer === 1 ||
    row.show_timer === '1';

  const ok = sameUser && started;

  if (ok) {
    console.log('[shouldRestoreRow] match row=', {
      id: row.id,
      assemble_id: row.assemble_id,
      isOpenEmpId: row.isOpenEmpId,
      show_name: row.show_name,
      hasStarted: row.hasStarted,
      startStatus: row.startStatus,
      show_timer: row.show_timer,
    });
  }

  return ok;
};

async function restoreActiveTimersOnly() {
  const me = safeUserId.value;
  if (!me) {
    console.warn('[restoreActiveTimersOnly] skip: current user not ready');
    return;
  }

  const allRows = materials_and_assembles.value || [];

  console.log('[restore] me =', me);
  console.log(
    '[restore] scan =',
    allRows.slice(0, 20).map(r => ({
      id: r.id,
      assemble_id: r.assemble_id,
      isOpenEmpId: r.isOpenEmpId,
      show_name: r.show_name,
      hasStarted: r.hasStarted,
      startStatus: r.startStatus,
      show_timer: r.show_timer,
    }))
  );

  const rows = allRows.filter(shouldRestoreRow);

  console.log('[restore] rows=', rows.map(r => ({
    id: r.id,
    assemble_id: r.assemble_id,
  })));

  if (!rows.length) return;

  // 先把 timer 掛出來
  for (const row of rows) {
    row._showMyTimer = true;
    row.show_name = me;
  }

  await nextTick();

  for (const row of rows) {
    const t = getT(row);
    if (!t?.restoreProcess) continue;

    try {
      await t.restoreProcess(
        row.id,
        processTypeOf(row),
        me,
        row.assemble_id
      );

      row._showMyTimer = true;
      row.show_name = me;
    } catch (e) {
      console.warn('[restore] fail row=', row.id, e);
    }
  }
}

function makeStub() {
  const isPaused = ref(true)
  return {
    isPaused,
    timerRef: { value: null },
    onTick: () => {},
    startProcess: async () => {},
    toggleTimer: async () => {},
    processId: ref(null),
  }
}

const isMineStarted = (row) => {
  const t = getT(row)
  // 只要「我」對這筆有 active process（hook 恢復或新開），就顯示我的 Timer
  //console.log("Boolean(t.processId.value):",Boolean(t.processId.value))
  return Boolean(t.processId.value)
}

// 讓每個 row 取到自己的 timer（沒有就建一個）
function useRowTimer(row, currentUserId) {
  console.log("useRowTimer(), row, currentUserId:", row, currentUserId);

  // 🔐 防呆：row 或 id 不存在，回 stub
  if (!row || !row.id) {
    console.warn('useRowTimer(): row is undefined or has no id', row, currentUserId)
    return makeStub()
  }

  const key = keyOf(row, currentUserId)
  if (!timerMap.has(key)) {
    const timerRef = ref(null)
    const t = useProcessTimer(() => timerRef.value)     // hook
    console.log("t:", t)
    // t 內有：isPaused(ref)、elapsedMs(ref)、processId(ref)、onTick(fn)...

    // 收斂清理方法（清掉本地 ticker / 狀態）
    t.dispose = () => {
      try { t._stopLocalTicker?.() } catch (e) {}
      try { t.onTick = () => {} } catch (e) {}
      // 如有 setInterval / requestAnimationFrame 也在 hook 內清
    }

    timerMap.set(key, { ...t, timerRef })
  }
  return timerMap.get(key)
}

// 這筆是否有人在開工（顯示綠點）
function hasAnyoneStarted(row) {
  const t = getT(row) // 你的 useRowTimer 物件
  const idx = materials_and_assembles.value.findIndex(item => item.index === row.index);
  const pos = idx >= 0 ? idx + 1 : null;
  console.log("@@@@t?.processId?.value: ",t)
  console.log("@@@@t?.processId?.value: ",t, t.processId.value, t.isPaused.value)
  console.log("@@@@pos: ", pos, "user count:", assembles_active_user_count.value[idx])
  return assembles_active_user_count.value[idx] > 0
}

// 統一取得 row 的狀態（只算一次，O(1) 查 Map）
function getRowState(row) {
  const idx = indexToIdx.value.get(row.index);
  if (idx === undefined) {
    return { started: false, count: 0, pos: null };
  }
  const count = indexToCount.value.get(row.index) ?? 0;
  return {
    started: count > 0,     // 是否有人開始
    count,                  // 人數
    pos: idx + 1,           // 第幾個（1-based）
  };
}

// 提供 v-badge 需要的 props
function badgeProps(row) {
  console.log("&&&&&badgeProps()...")

  console.log("assembles_active_user_count: ", assembles_active_user_count.value)

  const { started, count } = getRowState(row);

  const targetIndex = materials_and_assembles.value.findIndex(
    (kk) => kk.index === row.index
  );
  //console.log("targetIndex:", targetIndex)

  //console.log("count:", count)

  materials_and_assembles.value[targetIndex].count=count

  //console.log("materials_and_assembles:", materials_and_assembles.value[targetIndex])

  return {
    modelValue: started, // 對應 :model-value
    //content: count,      // 對應 :content（若想點狀顯示就不要設 content）
  };
}

async function nudgeResume () {
  // 某些情況（列表虛擬化/初裝載）第一次 resume 可能沒有接上 interval
  timer()?.resume?.()
  await new Promise(r => setTimeout(r, 30))
  timer()?.resume?.()
}

async function onClickBegin(row) {
  console.log("onClickBegin(), row", row);

  const me = safeUserId.value;
  if (!me) {
    showSnackbar("使用者資料尚未載入，請稍後再試!", "red-darken-2");
    return;
  }

  if (!row || !row.id) {
    showSnackbar("資料異常，按鍵無效!", "red-darken-2")
    return
  }

  const t = getT(row) // 以 (row.id + step + userId) 當 key
  if (!t) {
    showSnackbar("計時器尚未準備好!", "red-darken-2")
    return
  }

  console.log("t, t.processId.value, t.hasStarted?.value, t.isPaused.value:", t, t.processId.value, t.hasStarted?.value, t.isPaused.value)

  if (t.processId.value && (t.hasStarted.value || !t.isPaused.value)) {
    showSnackbar("已經領料了...", "orange-darken-2")
    return
  }

  selectedAsmId.value = row.index;

  //
  // ✅ 先讓畫面立即顯示 timer，不等 refresh / 後端
  row._showMyTimer = true;
  row.show_timer = true;
  row.show_name = me;

  await nextTick();

  // 1) 先 start（後端可能只建立/取回流程，仍為暫停狀態）
  if (!t.processId?.value) {
    const pid = await t.startProcess(
      row.id,
      processTypeOf(row),
      me,
      row.assemble_id
    )

    if (!pid || (typeof pid === 'object' && pid.success === false)) {
      showSnackbar("開始失敗：使用者或流程資料異常!", "red-darken-2");
      return;
    }
  }

  console.log("t.isPaused:", t.isPaused.value)

  // 若後端回來是 paused，再切成 running
  if (t.isPaused.value) {
    await t.toggleTimer();    // paused -> active（後端寫 begin_time）
    t.isPaused.value = false;
  }

  await updateItem(row);

  // 不要整頁 refresh；只更新局部資料/綠點
  //await nextTick();
  //await safeRefresh();

  await nextTick();
  //await restoreAllMyTimers();
}

function startDisabled(row) {
  // 只要該站「已完成總和」達到「應完成數量」，Start 就 disable
  return Number(row.total_completed_qty || 0) >= Number(row.must_receive_end_qty || 0)
}

const handleSetLinks = (links) => {
  console.log("Received links:", links);
  updateNavLinks(links);
};

// 避免同時多次 refresh
const safeRefresh = async () => {
  if (refreshing.value) return;
  refreshing.value = true;
  try {
    await listMaterialsAndAssembles();
    //await nextTick();
    //await restoreAllMyTimers();
  } finally {
    refreshing.value = false;
  }
};

const handleMaterialUpdate = async ()  => {
  console.log("handleMaterialUpdate 被觸發！")

  await safeRefresh();
  //
  //await listMaterialsAndAssembles();
  //// 等表格與 <TimerDisplay> 都掛好，ref 才拿得到
  //await nextTick();
  //// 還原「自己」未結束的計時器（把已在跑的 ms / 狀態灌回每列的 timer）
  //await restoreAllMyTimers(); // ← 如果你的函式名是 restoreMyTimers，就用那個
  //
  // 再抓「有人開工」的綠點數（不只自己）
  //2025-11-18 await refreshActiveCounts();
}

async function onDelete(item) {
  const ok = await confirmRef.value.open({
    title: deleteTitle.value,
    message: deleteMessage.value,
    okText: '確定',
    cancelText: '取消',
  })
  if (ok) {
    await removeMaterialsAndRelationTableFun(item.id);

    //待待
    // window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)

    //const idx = materials_and_assembles.value.findIndex(row => row.id === item.id)
    //if (idx !== -1) {
    //  materials_and_assembles.value.splice(idx, 1)
    //}
  }
}

const removeMaterialsAndRelationTableFun = async (id) => {
  console.log("removeMaterialsAndRelationTableFun()...");

  console.log("id:", id);

  let ok = false;
  try {
    const result = await removeMaterialsAndRelationTable({id: id});
    // crud.js 直接回傳 res.data，後端 jsonify(True) 會得到布林 true
    ok = result === true;
    console.log("remove result:", result);
  } catch (err) {
    console.error("DELETE API failed:", err?.response?.status, err?.response?.data, err?.message);
    showSnackbar("刪除 API 失敗", 'red accent-2');
    return false;
  }

  if (!ok) {
    showSnackbar("找不到目標或已被刪除。", 'red accent-2');
    return;
  }

  const idx = materials_and_assembles.value.findIndex(row => row.id === id)
  if (idx !== -1) {
    materials_and_assembles.value.splice(idx, 1)
  }

  showSnackbar("刪除工單完成!", "green darken-1")
  return true;
}

const onClickRemoveByDeliveryDateRange = async () => {
  let ok = false
  let result = null

  try {
    const payload = {
      dpRange2: dpRange2.value,
      delete_copies: true,
    }

    result = await removeMaterialsAndRelationTableByDeliveryDateRange(payload)

    ok = result.status === true

    console.log("remove result:", result)

  } catch (err) {
    console.error(
      "DELETE API failed:",
      err?.response?.status,
      err?.response?.data,
      err?.message
    )

    showSnackbar("刪除 API 失敗", 'red accent-2')
    return
  }

  if (!ok) {
    showSnackbar("找不到目標或已被刪除。", 'red accent-2')
    return
  }

  // 刪除前端資料
  if (Array.isArray(result.deleted_ids) && result.deleted_ids.length > 0) {
    const deleteSet = new Set(result.deleted_ids)

    materials_and_assembles.value = materials_and_assembles.value.filter(row => !deleteSet.has(row.id))
  }

  showSnackbar(`整批刪除成功，共刪除 ${result.deleted_count ?? 0} 筆!`, "green darken-1")
}

// 點擊「整批刪除」
const onClickBatchDelete = () => {
  if (!hasDpRange2.value || isInformationEmpty.value) return
  showBatchActions.value = true
}

// 取消
const onCancelBatchDelete = () => {
  //showBatchActions.value = false;
  resetBatchDeleteState();
}

// 確定
const onConfirmBatchDelete = async () => {
  if (isInformationEmpty.value) return

  try {
    await onClickRemoveByDeliveryDateRange()
  } finally {
    resetBatchDeleteState()
  }
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    // 1. 先撈表格資料
    //await listMaterialsAndAssembles();
    await safeRefresh();

    //await getMaterialsAndAssembles({ user_id: currentUser.value.empID });

    // 2. 補上欄位（這會影響渲染）
    // 為materials_and_assembles每個物件增加 pickBegin 屬性，初始為空陣列 []
    materials_and_assembles.value.forEach(item => {
      item.pickBegin = [];
      item.count = 0;
    });

    materials_and_assembles.value.map(it => ({
      ...it,
      pickBegin: Array.isArray(it.pickBegin) ? [...it.pickBegin] : [],
      count: typeof it.count === 'number' ? it.count : 0,
    }));

    // 3) 等表格與 <TimerDisplay> 都掛好，ref 才拿得到
    await nextTick();

    // 4) 還原「自己」未結束的計時器（把已在跑的 ms / 狀態灌回每列的 timer）
    await restoreAllMyTimers(); // ← 如果你的函式名是 restoreMyTimers，就用那個

  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const customFilter = (value, query, item) => {
  if (value == null || query == null) return false

  return String(value).toUpperCase().includes(String(query).toUpperCase())
}

const handleBarCode = async () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)

  await showMatchedItem(bar_code.value)
  /*
  let myBarcode = materials_and_assembles.value.find(m => m.order_num == bar_code.value);

  // 在這裡做條碼比對、查詢、上傳等邏輯
  if (myBarcode) {
    console.log('找到條碼對應項目:', myBarcode.index);

    // focus到對應項目的欄位
    focusItemField(myBarcode);
  } else {
    showSnackbar('找不到對應條碼資料！', 'red accent-2');
    console.warn('找不到對應條碼資料!')
  }
  */
}

/*
const focusItemField = async (item) => {
  console.log("focusItemField()...");

  await nextTick() // 確保 DOM 已更新
  // 找到外層 v-text-field DOM
  //const wrapper = document.getElementById(`receiveQtyID-${item.index}`);
  setTimeout(() => {
    const wrapper = document.getElementById(`receiveQtyID-${item.id}`)
    wrapper?.focus()
  }, 50)

  if (wrapper) {
    // 聚焦到 v-text-field 本身
    console.log("wrapper ok...")
    wrapper.focus();

    // 往內找真正的 <input> 元素
    const input = wrapper.querySelector('input');
    if (input) {
      input.focus();

      // 模擬按下 Enter 鍵事件
      const enterEvent = new KeyboardEvent('keyup', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true,
      });
      input.dispatchEvent(enterEvent);
    }
  } else {
    console.warn(`找不到欄位: receiveQtyID-${item.index}`)
  }
}

const getRowProps = ({ item }) => {
  return {
    id: `row-${item.id}`,
    class: highlightedRowId.value === item.id ? 'highlight-row' : '',
  }
}
*/

const showMatchedItem = async (barcode) => {
  console.log('處理條碼：', barcode)

  const idx = materials_and_assembles.value.findIndex(
    x => String(x.order_num || '').trim() === String(barcode).trim()
  )

  if (idx === -1) {
    console.warn('找不到條碼對應項目:', barcode)
    return
  }

  const item = materials_and_assembles.value[idx]
  console.log('找到條碼對應項目:', item.id)

  // 切到該筆所在頁
  pagination.page = Math.floor(idx / pagination.itemsPerPage) + 1

  // 高亮
  highlightedRowId.value = item.id

  await nextTick()

  setTimeout(() => {
    const rowEl = document.getElementById(`row-${item.id}`)
    if (rowEl) {
      rowEl.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, 80)

  // 幾秒後取消高亮
  setTimeout(() => {
    if (highlightedRowId.value === item.id) {
      highlightedRowId.value = null
    }
  }, 3000)
}

const hasDateRange = computed(() => {
  return !!start_date.value && !!end_date.value
})

const resetBatchDeleteState = () => {
  showBatchActions.value = false

  // 清空日期範圍
  //dpRange2.value = null
  dpRange2.value = []

  // 清掉顯示字串
  formattedDateRange.value = ''

  // 強制 VueDatePicker 重建
  menuKey.value++

  // 關閉 menu
  menuOpen.value = false

  // 如果你另外有 start_date / end_date，也一起清空
  start_date.value = ''
  end_date.value = ''
}

const openBatchDeleteActions = () => {
  if (isInformationEmpty.value || !hasDpRange2.value) {
    showFields.value = false
    return
  }
  showFields.value = true
}

const closeBatchDeleteActions = () => {
  showFields.value = false
}

const onDeleteHoverEnter = () => {
  if (!hasDateRange.value) {
    isFlipped.value = false
    return
  }
  isFlipped.value = true
}

const onDeleteHoverLeave = () => {
  isFlipped.value = false
}

const forkliftNoticeFun = () => {
  console.log("forkliftNoticeFun()...");

  socket.value.emit('station2_trans_begin');

  station2_trans_ready.value = false;
}

const handlePopState = () => {
  // 重新把這一筆 entry 的 state 改回 Router 給的 state
  window.history.replaceState(window.history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const isProcessStepEnabled = (item) => {
  const raw = item?.process_step_enable;
  if (raw === true || raw === 1 || raw === '1') return true;
  if (raw === false || raw === 0 || raw === '0' || raw == null || raw === '') return false;
  return Boolean(raw);
};

//const isAddProcessDisabled = (item) => isProcessStepEnabled(item);

// ===== 切換時複製（重要：不能直接指向）=====
//const cloneSteps = (arr) => arr.map(x => ({ ...x }))
const cloneSteps = (arr) => (arr || []).map(x => ({ ...x }))

const saveCurrentSchedulingSteps = (mode) => {
  console.log("test...saveCurrentSchedulingSteps...", mode)

  if (mode === 'assemble') {
    console.log("test...save assemble step")
    assemble_steps.value = deepClone(schedulingSteps.value)
  } else {
    console.log("test...save check step")
    check_steps.value = deepClone(schedulingSteps.value)
  }

  console.log("test...assemble_steps:", assemble_steps.value)
  console.log("test...check_steps:", check_steps.value)
}

const loadSchedulingStepsByMode = (mode) => {
  console.log("test...loadSchedulingStepsByMode...", mode)

  if (mode === 'assemble') {
    console.log("test...load assemble step")
    schedulingSteps.value = deepClone(assemble_steps.value)
  } else {
    console.log("test...load check step")
    schedulingSteps.value = deepClone(check_steps.value)
  }

  console.log("test...schedulingSteps:", schedulingSteps.value)
  console.log("test...assemble_steps:", assemble_steps.value)
  console.log("test...check_steps:", check_steps.value)
}

const switchScheduleMode = (newMode) => {
  console.log("test...switchScheduleMode...", newMode)

  const oldMode = scheduleMode.value
  console.log("test...oldMode:", oldMode, "newMode:", newMode)

  // 先把目前畫面內容存回舊 mode
  saveCurrentSchedulingSteps(oldMode)

  // 再切換 mode
  scheduleMode.value = newMode

  // 再載入新 mode 的資料
  loadSchedulingStepsByMode(newMode)
}

/*
const openSchedulingDialog = (item) => {
  if (isProcessStepEnabled(item)) return;
  scheduling_target_item.value = item;

  console.log("process_steps:", item.process_steps)
  //const parsed = parseProcessStepsV2(item.process_steps)

  const ps = item.process_steps || {}
  //assemble_steps.value = ps.assemble || []
  //check_steps.value = ps.check || []
  assemble_steps.value = deepClone(ps.assemble)
  check_steps.value = deepClone(ps.check)

  scheduleMode.value = 'assemble'  // 預設組裝
  //schedulingSteps.value = cloneSteps(assemble_steps.value)
  schedulingSteps.value = deepClone(assemble_steps.value)

  scheduling_dialog_orde_num.value=item.order_num;
  scheduling_dialog.value = true;

  console.log("test...schedulingSteps:", schedulingSteps.value);
  console.log("test...assemble_steps:", assemble_steps.value);
  console.log("test...check_steps:", check_steps.value);
  console.log("test...1.scheduleMode:", scheduleMode.value)
};
*/
const openSchedulingDialog = (item) => {
  if (isProcessStepEnabled(item)) return

  scheduling_target_item.value = item

  console.log("process_steps:", item.process_steps)

  const ps = item.process_steps || {}

  assemble_steps.value = deepClone(ps.assemble || [])
  check_steps.value = deepClone(ps.check || [])

  scheduleMode.value = 'assemble'
  schedulingSteps.value = deepClone(assemble_steps.value)

  scheduling_dialog_orde_num.value = item.order_num
  scheduling_dialog.value = true

  console.log("test...schedulingSteps:", schedulingSteps.value)
  console.log("test...assemble_steps:", assemble_steps.value)
  console.log("test...check_steps:", check_steps.value)
  console.log("test...1.scheduleMode:", scheduleMode.value)
}

const toggleSchedulingStep = (index) => {
  schedulingSteps.value[index].checked = !schedulingSteps.value[index].checked
}

const onDragStartStep = (index) => {
  dragFromIndex.value = index
}

const onDragOverStep = (event) => {
  event.preventDefault()
}

const onDropStep = (dropIndex) => {
  if (dragFromIndex.value === null || dragFromIndex.value === dropIndex) return

  const list = [...schedulingSteps.value]
  const [movedItem] = list.splice(dragFromIndex.value, 1)
  list.splice(dropIndex, 0, movedItem)

  schedulingSteps.value = list
  dragFromIndex.value = null
}

const onDragEndStep = () => {
  dragFromIndex.value = null
}

//const removeSchedulingDialog = (item) => {
//  if (!isAddProcessDisabled(item)) return;
//};

const fetchBomsV2 = async (payload) => {
  try {
    await getBoms(payload)
    console.log("temp_boms:", currentBoms.value, boms.value)
    //myBoms.value = tempres?.data?.boms || []
  } catch (e) {
    console.error(e)
    //myBoms.value = []
  }
}

const closeSchedulingDialog = () => {
  scheduling_dialog.value = false;
  scheduling_target_item.value = null;
};

const confirmSchedulingDialog = async () => {
  if (!scheduling_target_item.value?.id) {
    closeSchedulingDialog();
    return;
  }

  saveCurrentSchedulingSteps(scheduleMode.value);

  // 先把 dialog 目前編輯的資料，寫回來源
  //if (scheduleMode.value === 'assemble') {
  //  assemble_steps.value = cloneSteps(schedulingSteps.value)
  //} else {
  //  check_steps.value = cloneSteps(schedulingSteps.value)
  //}

  console.log("process_steps, assemble: ", assemble_steps.value)
  console.log("process_steps, check: ", check_steps.value)

  scheduling_dialog_loading.value = true

  try {
    const tt=await updateAssembleScheduleRows({
      id: scheduling_target_item.value.id,
      process_steps: {
        assemble: assemble_steps.value,
        check: check_steps.value
      }
    })

    console.log('updateAssembleScheduleRows res:', tt.status, tt.msg)
    // 重新抓最新資料
    await safeRefresh();

    showSnackbar('已完成工序設定', 'success')
    closeSchedulingDialog()
  } catch (error) {
    console.error('confirmSchedulingDialog error:', error)
    showSnackbar('工序設定失敗', 'red-darken-2')
  } finally {
    scheduling_dialog_loading.value = false
  }
}

function hasAnyStartedInSameOrder(row) {
  if (!row?.order_num) return false

  return (materials_and_assembles.value || []).some(item => {
    if (item.order_num !== row.order_num) return false

    const t = getT(item)
    return !!(t && t.processId.value && (t.hasStarted.value || !t.isPaused.value))
  })
}

function isAddProcessDisabledV2(row) {
  return hasAnyStartedInSameOrder(row)
}

function getScheduleName(item) {
  if (!item) return ''
  console.log("getScheduleName...")

  const ps = item.process_steps || {}
  const workNum = String(item.work_num || '')
  const scheduleId = Number(item.schedule_id)

  if (!scheduleId) return ''

  let steps = []

  if (workNum.includes('B109')) {
    steps = Array.isArray(ps.assemble) ? ps.assemble : []
  } else if (workNum.includes('B110')) {
    steps = Array.isArray(ps.check) ? ps.check : []
  } else {
    return ''
  }
  console.log("getScheduleName, steps:", workNum, steps)
  const found = steps.find(x => Number(x.id) === scheduleId)
  console.log("getScheduleName, found:", found)
  return found?.name || ''
}

function checkBegin(row) {
  const t = getT(row);

  if (t && t.processId.value && (t.hasStarted.value || !t.isPaused.value)) {
    return true;
  }
  return false;
}

function canBeginBySchedule(item) {
  // 已經開始中的，這裡可依你原本 timer/process 邏輯再擋
  //const t = getT(item)
  //if (t && t.processId.value && (t.hasStarted.value || !t.isPaused.value)) {
  //  return false
  //}

  // 只要這筆有 schedule_id，就允許開始
  return item.schedule_id > 0;
}

//const isButtonDisabled = (item) => {
//  return item.whichStation != 2 || item.isLackMaterial == 0 || !item.process_step_enable;
//};

const isGifDisabled = (item) => {
  return item.whichStation != 2
};

const handleKeyDown = (event) => {
  const inputChar = event.key;

  const caps = event.getModifierState && event.getModifierState('CapsLock');
  console.log("CapsLock is: ", caps); // true when CapsLock is on

  // 允許左右方向鍵、backspace 和 delete 鍵
  if (['ArrowLeft', 'ArrowRight', 'Backspace', 'Delete'].includes(inputChar)) {
    return;
  }

  // 使用正規化運算式檢查是否為數字且長度不超過3
  if (!/^\d$/.test(inputChar)) {
    event.preventDefault();  // 阻止非數字輸入或超過長度的輸入
  }

  const inputValue = event.target.value || ''; // 確保 inputValue 是字符串

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入, 2025-07-02 modify
  if (inputValue.length > 5 && inputValue < 10000) {
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
    8: '#776472',
    9: '#85CB33',
  };

  return {
    color: colorMap[status],
    fontWeight: '600',
    fontSize: '12px',
  };
};

const addAbnormalInMaterial = (item) => {
  console.log("addAbnormalInMaterial(),", item);

  abnormalDialog_record.value = materials_and_assembles.value.find(m => m.assemble_id == item.assemble_id);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_delivery_qty.value = item.delivery_qty;
  abnormalDialog_new_must_receive_qty.value = item.must_receive_qty;
  abnormalDialog_must_receive_qty.value = item.must_receive_qty;
  abnormalDialog_display.value = item.Incoming1_Abnormal;

  abnormalDialog.value = true;
}

const createAbnormalFun = async () => {
  console.log("createAbnormalFun()...");

  if (abnormalDialog_new_must_receive_qty.value != abnormalDialog_must_receive_qty.value) {
    let temp_str = '(' + abnormalDialog_delivery_qty.value + ' / ' + abnormalDialog_new_must_receive_qty.value + ')'
    abnormalDialog_message.value = '備料區來料數量不對! '+ temp_str;
    console.log("temp_str:", temp_str);
    let payload = {}

    try {
      payload = {
        assemble_id: abnormalDialog_record.value.assemble_id,
        record_name: 'Incoming1_Abnormal',
        record_data: abnormalDialog_message.value,
      };
      await updateAssemble(payload);

      abnormalDialog_record.value.Incoming1_Abnormal=false;

      // targetIndex為目前table data record 的 index
      const targetIndex = materials_and_assembles.value.findIndex(
        (kk) => kk.id === abnormalDialog_record.value.id
      );

      if (targetIndex !== -1) {
        // 用 Vue 的方式確保觸發響應式更新
        materials_and_assembles.value[targetIndex] = {
          ...materials_and_assembles.value[targetIndex],
          Incoming1_Abnormal: false,
        };
      }

      console.log('更新成功...');
    } catch (error) {
      console.error('更新失敗:', error.response?.data?.message || error.message);
    }
  }
  abnormalDialog.value = false;
}

const updateItem = async (item) => {
  console.log("PickReportForAssembleBegin, updateItem(),", item);

  const me = safeUserId.value;
  if (!me) {
    throw new Error("current user not ready");
  }

  let payload = {};

  let startTime = new Date();                                                         // 記錄當前結束時間
  let formattedStartTime = formatDateTime(startTime); //完工生產報工開始時間
  console.log("formattedStartTime:", formattedStartTime)
  //console.log("item.pickBegin.length ==1 && Number(item.total_receive_qty)!=0:", item.pickBegin.length, Number(item.total_receive_qty_num));
  console.log("startTime step 1...")
  //2025-02-24 mark if condition
  // 確認是第1次領料
  //if (item.pickBegin.length ==1 && Number(item.total_receive_qty_num)!=0) {
  console.log("startTime step 2...")
  // 記錄當前領料生產開始時間
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'currentStartTime',
    record_data: formatDateTime(new Date()),
  };
  await updateAssemble(payload);
  //}
  //
  // 2.記錄當前途程領取數量
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'ask_qty',                 //領取數量
    record_data: Number(item.receive_qty),
  };
  await updateAssemble(payload);

  if (item.must_receive_end_qty==0) {
    // 2-a.紀錄該筆的完工應領取數量
    payload = {
      material_id: item.id,
      assemble_id: item.assemble_id,
      create_at: item.create_at,

      record_name: 'must_receive_end_qty',
      record_data: Number(item.receive_qty),
    };
    await updateAssembleMustReceiveQtyByMaterialIDAndDate(payload);
  }

  //// 2-b.紀錄該筆的應領取數量, 2025-06-18 add, 改順序
  //payload = {
  //  material_id: item.id,
  //  record_name: 'must_receive_qty',
  //  record_data: Number(item.must_receive_end_qty) - Number(item.receive_qty),
  //};
  //await updateAssembleMustReceiveQtyByMaterialIDAndDate(payload);

  // 3.暫存每次領取數量
  //item.pickBegin.push(item.receive_qty);

  // 4.記錄當前領取總數量
  let total = Number(item.receive_qty) + Number(item.total_receive_qty_num);
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'total_ask_qty',   //開始, /領取數量總數
    record_data: total,
  };
  await updateAssemble(payload);

  item.total_receive_qty ='(' + total.toString().trim() + ')';
  item.total_receive_qty_num = total;

  // 5.記錄當前領取人員工號
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'user_id',
    record_data: me,
  };
  await updateAssemble(payload);

  // 取得組裝區目前途程的show2_ok訊息類型(開始)
  checkInputStr(item.assemble_work);
  console.log("outputStatus:", outputStatus.value, typeof(outputStatus.value.step1), typeof(outputStatus.value.step1))

  if (outputStatus.value?.step1 == null) {
    throw new Error("outputStatus.value.step1 is undefined");
  }

  // 6.按開始鍵後, 記錄當前途程開始狀態顯示訊息
  payload = {
    order_num: item.order_num,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step1
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: item.assemble_id,
    record_name: 'show2_ok',
    record_data: outputStatus.value.step1
  };
  await updateAssemble(payload);

  item.assemble_process = str2[outputStatus.value.step1]
  item.assemble_process_num = outputStatus.value.step1

  // 7.按開始鍵後, 記錄當前途程狀態訊息show3_ok
  payload = {
    order_num: item.order_num,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step1
  };
  await updateMaterial(payload);

  payload = {
    assemble_id: item.assemble_id,
    record_name: 'show3_ok',
    record_data: outputStatus.value.step1
  };
  await updateAssemble(payload);

  let temp = Number(item.req_qty)
  // 確認 已領取數量總數=需求數量(訂單數量)
  //console.log("total == temp ?",total, temp)

  if (startDisabled(item)) {
    // 記錄當前紀錄, 不能再輸入
    payload = {
      assemble_id: item.assemble_id,
      record_name: 'input_disable',
      record_data: true,
    };
    await updateAssemble(payload);

    item.input_disable = true;
  }

  const key = `${item.id}:${item.assemble_id}:${processTypeOf(item)}:${me}`;
  localStorage.setItem(`PR_END_SYNC_${me}`, `${key}|${Date.now()}`);
  console.log("key key:", `PR_END_SYNC_${me}`, key);

  //待待
  //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};

const checkInputStr = (inputStr) => {
  console.log("checkInputStr(),", inputStr)
  //參考後端python, str2[]的指標
  if (inputStr.includes('109')) {             //組裝
    outputStatus.value = { step1: 4, step2: 5, };
  } else if (inputStr.includes('106')) {      //雷射
    outputStatus.value = { step1: 8, step2: 9 };
  } else if (inputStr.includes('110')) {      //檢驗
    outputStatus.value = { step1: 6, step2: 7 };
  } else {
    outputStatus.value = { step1: null, step2: null };  // 無匹配時清空結果
  }
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

const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const toggleSort = (key) => {
  const index = sortBy.value.indexOf(key)

  if (index !== -1) {
    // 若目前已經是排序該欄位，則切換排序方向
    sortDesc.value[index] = !sortDesc.value[index]
  } else {
    // 否則新增排序欄位，並預設為升序
    sortBy.value = [key]
    sortDesc.value = [false]
  }
}

// 滑鼠移入圖片，顯示表格
const handleGifClick = async (item, index) => {
  console.log(`GIF 點擊事件觸發，資料索引: ${index}, 資料內容:`, item);

  if (hoveredItemIndex.value === index && isTableVisible.value) {
    return;  // 如果表格已經顯示且資料已經加載，不再重複請求
  }

  hoveredItemIndex.value = index;
  isTableVisible.value = true;    // 設置表格可見

  await fetchBomsV2(item)
};

const fetchBoms = async (item) => {
  if (!item?.order_num) {
    boms.value = [];
    return;
  }

  let res;

  try {
    if (item.merge_enabled) {
      res = await getOrderPickedBoms({
        order_num: item.order_num,
      });
    } else {
      res = await getOrderPickedBoms({
        id: item.id,
      });
    }
    boms.value = res?.data?.boms || [];
  } catch (e) {
    console.error("fetchBoms failed:", e);
    boms.value = [];
    //return;
  }

  //boms.value = res.data?.boms || [];
};

// 滑鼠移入表格時，保持表格顯示
//const onMouseEnterTable = () => {
//  isTableVisible.value = true;
//}

// 滑鼠移出圖片或表格時，隱藏表格
//const onMouseLeaveTable = () => {
//  isTableVisible.value = false;   // 隱藏表格
//  //hoveredItemIndex.value = null;  // 重置 hoveredItemIndex
//}

// 滑鼠位置偵測
const updateMousePosition = (event) => {
  mouseX.value = event.clientX;
  mouseY.value = event.clientY;
}

// 清除localStorage內容
const removelocalStorage = () => {
  if (localStorage.getItem('loginedUser')) {
    localStorage.removeItem('loginedUser');
  }
  if (localStorage.getItem('Authenticated')) {
    localStorage.removeItem('Authenticated');
  }
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
  background-color: #85aef2;      // 自訂背景顏色
}

:deep(.v-data-table .v-table__wrapper > table > tbody tr:nth-of-type(odd)) {
   background-color: rgba(0, 0, 0, .05);
 }

:deep(.v-data-table-footer) {
  margin-bottom: -10px;
}

:deep(input[type="text"]) {
  min-height: 20px;
  height: 20px;
  opacity: 1;
  padding: 0px;
  text-align: center;
  color: red;
  min-width:60px;
  width:60px;
}

:deep(input#bar_code[type="text"]) {
  color: black !important;
}

.custom-table {
  //border-collapse: collapse;  // 合併邊框
  //border: 1px solid #000;     // 表格的外框
  border-radius: 0 0 20px 20px;
}

:deep(.show_table thead th) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
  color:blue;
  font-family: '微軟正黑體', sans-serif; margin-top:10px;
}

:deep(.show_table tfoot td) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
  font-weight: 700;
  color:blue;
  text-align: center;
  font-family: '微軟正黑體', sans-serif; margin-top:10px;
}

:deep(.show_table tbody td) {
  padding: 3px !important;
  height: 15px !important;
  font-size: 12px !important;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.blink {
  animation: blink 1s infinite;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

.ellipsis-cell {
  max-width: 100px;
  display: inline-block;     // 讓 ellipsis 生效
  overflow: hidden;
  text-overflow: ellipsis;   // 顯示 abcdef...
  white-space: nowrap;
  vertical-align: bottom;
}

.tooltip-content {
  max-width: 520px;          // 避免太寬，可調整
  white-space: pre-wrap;     // 保留換行
}

.slide-enter-from
{
  transform: translateX(-100%);
}

.slide-leave-to {
  transform: translateX(100%);
}

//===過場特效
.flip_btn {
  position: relative;
  top: -5px;
  left: 30px;
  height: 20px;
  width: 130px;
  transform-style: preserve-3d;
  transition: transform 500ms ease-in-out;
  transform: translateZ(-20px);
}

.flip_btn:hover {
  transform: rotateX(-90deg) translateY(20px);
}

.side {
  position: absolute;
  backface-visibility: hidden;
  width: 130px;
  //width: 100%;
  height: 100%;
  display: flex;
}

.default-side {
  transform: translateZ(20px);
}

.hover-side {
  transform: rotateX(90deg) translateZ(20px);
}


:deep(.dp__calendar_header .dp__calendar_header_item) {
  font-size: 0.8em;
}

// ------- 沒有週數欄（共 7 欄）：一～五綠，六日紅 -------
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(-n+5)) {
  background: #2e7d32; color: #fff;
}
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(6)),
:deep(.dp__calendar_header:not(:has(.dp__calendar_header_item_week))
      .dp__calendar_header_item:nth-child(7)) {
  background: #c62828; color: #fff;
}

// ------- 有週數欄（第 1 欄是週數）：星期從第 2～8 欄 -------
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(n+2):nth-child(-n+6)) {

  background: #2e7d32; color: #fff;   // 第 2～6 欄 = 一～五 → 綠
}
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(7)),
:deep(.dp__calendar_header:has(.dp__calendar_header_item_week)
      .dp__calendar_header_item:nth-child(8)) {

  background: #c62828; color: #fff;   // 第 7、8 欄 = 六、日 → 紅
}

// 如果週數欄（W）有開啟，不要上色它
:deep(.dp-colored .dp__calendar_header_item_week) {
  background: transparent !important;
  color: inherit !important;
}

:deep(.dp__month_year_select) {
  color: #1976d2;
  font-weight: bold;
}

:deep(.dateicon > .v-input__prepend .v-icon) {
  color: #F48FB1 !important;
}

// 讓 DatePicker 撐滿 v-menu 設定的寬度
:deep(.dp-stretch .dp__main) {
  width: 100%;
}

:deep(.dp__outer_menu_wrap) {
  width: 140%;
}

.toolbar-row {
  display: flex;
  align-items: center;

  flex-wrap: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  gap: 16px;
}

// 4. 日期範圍往左調整
.date-slot {
  width: 290px;
  min-width: 290px;
}

.date-box {
  width: 290px;
}

// 1 + 2. 整批刪除固定寬度，不跟搜尋框重疊，也不擠壓別人
.batch-slot {
  width: 180px;
  min-width: 180px;
  display: flex;
  align-items: center;
  justify-content: center;

  position:relative;
  top: -2px;
}

.fixed-flip-btn {
  width: 180px;
  min-width: 180px;
  position: relative;
  left: -10px;
}

.fixed-flip-btn .default-side {
  width: 100%;
  min-width: 100%;
  max-height: 34px;
  border-radius: 6px;
  border-width: 1.5px;
  border-color: #64B5F6;
}

.hover-actions {
  width: 180px;
  min-width: 180px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.action-btn {
  width: 76px;
  min-width: 76px;
  border-radius: 6px;
  border-width: 1.5px;
  border-color: #64B5F6;
  position: relative;
  top: 5px;
}

// 搜尋框固定寬度，避免被擠壓或重疊
:deep(.search-slot) {
  width: 180px;
  min-width: 180px;
  position: relative;
  top: 5px;
}

// 3. barcode 再往右移
:deep(.barcode-slot) {
  width: 220px;
  min-width: 220px;

  position: relative;
  top: 8px;
}

:deep(.barcode-slot .v-input__control) {
  position: relative;
  top: 3px;
}

.toolbar-field {
  width: 100%;
}

// 外框高度統一
:deep(.toolbar-field--24 .v-field) {
  min-height: 24px !important;
  height: 24px !important;
  align-items: center !important;
  border-radius: 4px;
}

// input 區高度統一
:deep(.toolbar-field--24 .v-field__input) {
  min-height: 24px !important;
  height: 24px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  display: flex !important;
  align-items: center !important;
}

// 真正輸入文字的 input：讓游標垂直置中
:deep(.toolbar-field--24 input) {
  height: 24px !important;
  line-height: 24px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  align-self: center !important;
}

:deep(.date-box .v-text-field input) {
  top: 7px;
}

.batch-slot.is-disabled {
  cursor: not-allowed !important;
  opacity: 0.65;
}

/*
.batch-slot.is-disabled * {
  cursor: not-allowed !important;
}

.batch-slot.is-disabled .flip_btn:hover {
  transform: none !important;
}

.batch-slot.is-disabled .hover-side {
  pointer-events: none !important;
}

.batch-slot.is-disabled .default-side {
  pointer-events: auto !important;
}
*/
.fixed-flip-btn {
  position: relative;
  width: 180px;
  height: 40px;
}

.fixed-flip-btn .side {
  position: absolute;
  inset: 0;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fixed-flip-btn .default-side {
  opacity: 1;
  pointer-events: auto;
  transform: rotateY(0deg);
}

.fixed-flip-btn .hover-side {
  opacity: 0;
  pointer-events: none;
  transform: rotateY(90deg);
  display: flex;
  align-items: center;
  gap: 8px;
}

.fixed-flip-btn.show-fields .default-side {
  opacity: 0;
  pointer-events: none;
  transform: rotateY(-90deg);
}

.fixed-flip-btn.show-fields .hover-side {
  opacity: 1;
  pointer-events: auto;
  transform: rotateY(0deg);
}

.hover-actions .action-btn {
  min-width: 72px;
}

//=
/* 正常狀態 */
.btn-add-process {
  background: #c8e6c9;
  color: #1b5e20;
  //transition: none !important;
}

/* hover（正常時） */
.btn-add-process:hover {
  background: #a5d6a7;
  //color: #1b5e20;
}

/* 🔥 disabled 狀態 */
.btn-add-process--disabled {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;

  //cursor: not-allowed !important;
  //pointer-events: none !important;
  //pointer-events: auto !important;

  box-shadow: none !important;
  opacity: 1 !important; /* 防止 Vuetify 自己降透明 */

  //filter: grayscale(20%);
}

/* 🔥 防止 hover 影響 */
.btn-add-process--disabled:hover {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;
}

.btn-add-process--disabled,
.btn-add-process--disabled * {
  cursor: not-allowed !important;
}
//
.btn-add-process {
  transform: translateX(20px);
}
//
//=

// 正常狀態（淡綠)
//.btn-add-process {
//  background: #c8e6c9 !important;
//  color: #1b5e20 !important;
//  font-weight: 600;
//}

// disabled 狀態（淡灰 + 文字灰 + 禁止滑鼠)
//.btn-add-process--disabled {
//  background: #e0e0e0 !important;
//  color: #9e9e9e !important;
//  cursor: not-allowed !important;
//  pointer-events: auto !important; // 保留 cursor 效果
//}

// hover 完全無效果
//.btn-add-process:hover {
//  background: #c8e6c9 !important;
//}

//.btn-add-process--disabled:hover {
//  background: #e0e0e0 !important;
//}

// Vuetify disabled 預設會降低 opacity → 關掉
//:deep(.v-btn--disabled.btn-add-process--disabled) {
:deep(.v-btn--disabled) {
  cursor: not-allowed !important;
  opacity: 1 !important;
}

// 正常狀態（淡紅)
.btn-remove-process {
  background: #ffcdd2 !important;   // 淡紅
  color: #b71c1c !important;        // 深紅字
  font-weight: 600;
}

// disabled 狀態（淡灰）
.btn-remove-process--disabled {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;
  cursor: not-allowed !important;
  pointer-events: auto !important;
}

// hover 無效果
.btn-remove-process:hover {
  background: #ffcdd2 !important;
}

.btn-remove-process--disabled:hover {
  background: #e0e0e0 !important;
}

// 關掉 Vuetify disabled opacity
:deep(.v-btn--disabled.btn-remove-process--disabled) {
  opacity: 1 !important;
}

.begin-cell {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 0;
  overflow: visible;
}

.begin-timer-slot {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 90px;
  flex: 0 0 auto;
  margin-left: 0 !important;
  padding-left: 0 !important;
}

.begin-timer-text {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.begin-timer {
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.begin-btn {
  flex: 0 0 auto;
  margin-left: 0 !important;
  white-space: nowrap;
}

/* 正常 */
.begin-btn {
  background: #3949ab;   /* indigo */
  color: white;
}

/* hover */
.begin-btn:hover {
  background: #303f9f;
}

/* 🔥 disabled */
.begin-btn--disabled {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;
  cursor: not-allowed !important;
  opacity: 1 !important;
}

/* 禁止 hover */
.begin-btn--disabled:hover {
  background: #e0e0e0 !important;
}

.scheduling-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scheduling-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 52px;
  //padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 10px;
  background: #fafafa;
  cursor: grab;
  user-select: none;

  padding: 0px;
  min-height: 36px;
}

.scheduling-item:active {
  cursor: grabbing;
}

.scheduling-item:hover {
  background: #f5f5f5;
}

.scheduling-item-left {
  display: flex;
  align-items: center;
  min-width: 0;
}

.drag-handle {
  color: #757575;
  cursor: grab;
}

.process-btn {
  letter-spacing: 0;
}

/*
.highlight-row td {
  background-color: #A7FFEB !important;
  transition: background-color 0.3s ease;
}
*/

.batch-actions {
  display: flex;
  gap: 8px;
}

</style>