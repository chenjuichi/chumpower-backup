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

  <v-dialog v-model="scheduling_dialog" persistent max-width="420">
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
            <!--
              <v-checkbox
                v-model="step.checked"

                :disabled="step.locked === true"

                hide-details
                density="compact"
                class="me-2"
              />
            -->
<!--0714丁副-->
<v-checkbox
  v-model="step.checked"
  hide-details
  density="compact"
  class="me-2"
/>
              <span :class="{ 'text-red-darken-2': step.checked }">
                {{ step.name }}
              </span>
            </div>
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="justify-center pb-4">
        <v-btn
          color="success"
          prepend-icon="mdi-check"
          text="確定"
          class="text-none"
          variant="flat"
          :loading="scheduling_dialog_loading"
          @click="confirmSchedulingDialog"
        />

        <v-btn
          color="error"
          prepend-icon="mdi-close"
          text="取消"
          class="text-none"
          variant="flat"
          @click="closeSchedulingDialog"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>

    <!-- 工序資料檢查 Alert -->
  <v-dialog v-model="scheduleAlertDialog" max-width="420" persistent>
    <v-card>
      <v-card-title class="text-h6" style="font-weight:700;">
        工序資料提醒
      </v-card-title>

      <v-card-text>
        <div
          class="erp-alert-box"
          :class="scheduleAlertType === 'all-empty' ? 'erp-alert-error' : 'erp-alert-warning'"
        >
          <v-icon
            size="34"
            class="mr-3"
            :color="scheduleAlertType === 'all-empty' ? 'red-darken-2' : 'blue-darken-2'"
          >
            {{ scheduleAlertType === 'all-empty' ? 'mdi-alert-circle' : 'mdi-information' }}
          </v-icon>

          <div
            class="erp-alert-message"
            :class="scheduleAlertType === 'all-empty' ? 'erp-alert-message-error' : 'erp-alert-message-warning'"
          >
            {{ scheduleAlertMessage }}
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="justify-center pb-4">
        <v-btn
          v-if="scheduleAlertType === 'partial'"
          color="success"
          prepend-icon="mdi-check"
          text="確定"
          class="text-none"
          variant="flat"
          @click="continueConfirmSchedulingDialog"
        />

        <v-btn
          color="error"
          prepend-icon="mdi-arrow-left"
          text="返回"
          class="text-none"
          variant="flat"
          @click="backToSchedulingDialog"
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
            style="top:22px; height:48px; flex:0 1 auto; max-width: calc(100% - 320px);"
          >
            <!--日期範圍-->
            <v-col cols="auto">
              <div class="date-slot">
              <Transition name="slide">
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

                        class="dateicon"
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

            <v-col cols="auto" class="d-flex justify-end align-center">
              <div class="batch-slot" v-if="hasDpRange2">

                <v-btn
                  v-if="!showBatchActions"
                  style="background:#E3F2FD !important;"

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
                    <v-icon left color="#ff0000">mdi-window-close</v-icon>
                    <span style="color:black; font-weight:600;">取消</span>
                  </v-btn>

                  <!-- 確定 -->
                  <v-btn
                    class="action-btn"
                    :disabled="isInformationEmpty"
                    @click="onConfirmBatchDelete"
                  >
                    <v-icon left color="green">mdi-check</v-icon>
                    <span style="color:black; font-weight:600;">確定</span>
                  </v-btn>
                </div>
              </div>
            </v-col>

            <!--客製化搜尋/barcode輸入框-->
            <v-col cols="auto" class="d-flex justify-end align-center" style="gap:5px;">
                <v-text-field
                  v-model="search"
                  label="資料搜尋"

                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  hide-details
                  single-line
                  class="top-input"
                />

                <v-text-field
                  id="bar_code"
                  v-model="bar_code"
                  label="條碼"

                  prepend-inner-icon="mdi-barcode"
                  :value="bar_code"
                  ref="barcodeInput"
                  @keyup.enter="handleBarCode"
                  hide-details
                  single-line

                  variant="outlined"
                  class="barcode-input top-input"
                />
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
        <div
          style="color:black; font-size:12px; margin-right:2px;"
          v-if="(String(item.shortage_note || '').includes('缺料') && item.isLackMaterial != 99)"
        >
          <v-icon style="color: green;" @click.stop="onDelete(item)" small>
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}&nbsp;
          <span style="color:red; font-weight:700; font-size:12px;">缺料</span>
        </div>

        <div
          style="color:black; font-size:12px; margin-right:2px;"
          v-else-if="!item.merge_enabled"
        >
          <v-icon style="color: green;" @click.stop="onDelete(item)" small>
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}&nbsp;
          <span style="color:blue; font-weight:700; font-size:12px;">缺料不併單</span>
        </div>

        <div
          style="color:black; font-size:12px; margin-right:20px; margin-left: -15px;"
          v-else
        >
          <v-icon style="color: green;" @click.stop="onDelete(item)" small>
            mdi-trash-can-outline
          </v-icon>
          {{ item.order_num }}
        </div>

        <div style="color: #a6a6a6; font-size:12px; margin-right: 10px;">
          {{ item.assemble_work }}
          <span v-if="getScheduleName(item)" style="font-weight:600; font-size:12px; color:black;">
            [{{ getScheduleName(item) }}]
          </span>

          <span v-if="item.is_abnormal_process" class="abnormal-process-text">-異常</span>
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
            <!--{{ item.must_receive_qty }} -->
            {{ item.remain_receive_qty ?? item.must_receive_qty }}
          </span>
        </template>
        <template v-else>
          <span style="margin-left: 25px;">
            <!--{{ item.must_receive_qty }} -->
            {{ item.remain_receive_qty ?? item.must_receive_qty }}
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
<!--
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
-->

<!--
<div
  v-if="
    isTableVisible &&
    activeBomItemId === item.id && getFilteredBoms(item).length > 0 && !isGifDisabled(item)"
  :style="adjustTablePosition"
>
-->
<div
  v-if="
    isTableVisible &&
    String(activeBomItemId) === String(item.id) &&
    getFilteredBoms(item).length > 0 &&
    !isGifDisabled(item)
  "
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
        v-for="(bom_item, index) in getFilteredBoms(item)"
        :key="bom_item.id || index"
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
          共 {{ getFilteredBoms(item).length }} 項
        </td>
      </tr>
    </tfoot>
  </v-table>
</div>

        </div>
      </v-hover>
    </template>

    <!-- 自訂 '+工序' 按鍵欄位 -->
    <template #item.add_process="{ item }">
      <!-- 尚未設定工序：維持原本 + 工序按鍵 -->
      <v-btn
        v-if="!isProcessStepEnabled(item)"
        size="small"
        class="btn-add-process"

        :class="{
          'btn-add-process--disabled': isAddProcessButtonDisabled(item),
          'btn-add-process--locked': isSchedulingDialogLocked(item)
        }"

        @click="onClickOpenSchedulingDialog(item)"
      >
        <v-icon start size="18">mdi-plus</v-icon>
        工序
      </v-btn>

      <!-- 已設定工序：改成 delete + pencil 兩個 icon 按鍵 -->
       <!--:disabled="isEditProcessDisabled(item) || item.has_any_running_process"-->
    <!--
      <div v-else class="add-process-icon-group">
        <v-btn
          size="small"
          icon
          class="btn-add-process-icon btn-add-process-icon--delete"

          :disabled="isEditProcessDisabled(item) || isSchedulingDialogLocked(item)"
          @click.stop="onClickDeleteSchedule(item)"
        >
          <v-icon size="20" color="red">mdi-delete</v-icon>
        </v-btn>

        <v-btn
          size="small"
          icon
          class="btn-add-process-icon btn-add-process-icon--edit"

          :disabled="isEditProcessDisabled(item) || isSchedulingDialogLocked(item)"
          @click="openSchedulingDialog(item)"
        >
          <v-icon size="20" color="blue">mdi-pencil</v-icon>
        </v-btn>
      </div>
    -->
<!--0714 丁副-->
<div v-else class="add-process-icon-group">
  <v-btn
    size="small"
    icon
    class="btn-add-process-icon btn-add-process-icon--edit"
    :disabled="
      isEditProcessDisabled(item) ||
      isSchedulingDialogLocked(item)
    "
    @click.stop="openSchedulingDialog(item)"
  >
    <v-icon size="20" color="blue">
      mdi-pencil
    </v-icon>
  </v-btn>
</div>
    </template>

    <!-- 自訂 '開始' 按鍵欄位 -->
    <template #item.action="{ item }">
      <!-- 開始鍵左側顯示「自己」的計時值 -->
      <div class="begin-cell begin-cell-shift">
        <div class="begin-timer-slot">
          <span v-if="checkShowTimer(item)" class="begin-timer-text">
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

        <div class="start-btn-wrap">
          <span
            v-if="hasOtherUserStarted(item)"
            class="other-user-dot"
          />

          <v-btn
            size="small"
            variant="tonal"
            class="begin-btn"
            :class="{ 'begin-btn--disabled': isStartButtonDisabled(item) }"
            :disabled="isStartButtonDisabled(item)"

            @click="onClickBegin(item)"
            prepend-icon = "mdi-play"
          >
            <v-icon start style="font-weight:700;">mdi-timer-outline</v-icon>
            開 始
          </v-btn>
        </div>
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
import { currentBoms, }  from '../mixins/crud.js';

import { materials_and_assembles, assembles_active_user_count, boms,  socket_server_ip }  from '../mixins/crud.js';

import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const listMaterialsAndAssembles = apiOperation('get', '/listMaterialsAndAssembles');

const updateAssembleMustReceiveQtyByMaterialIDAndDate = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialIDAndDate');

const updateAssemble = apiOperation('post', '/updateAssemble');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateAssembleScheduleRows = apiOperation('post', '/updateAssembleScheduleRows');

const getBoms = apiOperation('post', '/getBoms');

const getOrderPickedBoms = apiOperation('post', '/getOrderPickedBoms');

const removeMaterialsAndRelationTable = apiOperation('post', '/removeMaterialsAndRelationTable');
const removeMaterialsAndRelationTableByDeliveryDateRange = apiOperation('post', '/removeMaterialsAndRelationTableByDeliveryDateRange');

const deleteAssembleScheduleRow = apiOperation('post', '/deleteAssembleScheduleRow');

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

const schedulingDialogLockedIds = ref(new Set());
const schedulingClientId = `${app_user_id}-${Date.now()}-${Math.random().toString(36).slice(2)}`

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
const scheduleAlertDialog = ref(false)
const scheduleAlertMessage = ref('')
const scheduleAlertType = ref('')     // none / all-empty / partial
const scheduledMaterialIds = ref(new Set())

const refreshing = ref(false);

const timerMap = new Map();

let __disposedAll = false;

//const PROCESS_TYPES = ['21', '22', '23']
//const countsByType = ref({ '21': {}, '22': {}, '23': {} })
//const activeMap = reactive({
//  '21': {}, '22': {}, '23': {}
//})

const selectedAsmId = ref(null);

// 控制是否顯示 確定/取消
const showBatchActions = ref(false)

const bomsMap = ref({})
const activeBomItemId = ref(null)

//=== watch ===

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

const hasDpRange2 = computed(() => {
  return Array.isArray(dpRange2.value)
    && dpRange2.value.length === 2
    && !!dpRange2.value[0]
    && !!dpRange2.value[1]
})

watch(hasDpRange2, (val) => {
  if (!val) {
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

    socket.value?.on('assemble-started', handleAssembleStarted);

    socket.value?.on('schedule_mode-ok', handleScheduleModeOk);

    socket.value?.on('icon-disable', handleIconDisable);

    socket.value?.on('assemble-batch-released2', handleAssembleBatchReleased);
    socket.value?.on('assemble-abnormal-created', handleAssembleBatchReleased);

    socket.value?.on('assemble-feed-released', handleAssembleFeedReleased);

    socket.value?.on('assemble-schedule-updated', handleAssembleScheduleUpdated);

    socket.value?.on('assemble-scheduling-dialog-lock', handleSchedulingDialogLock);
    socket.value?.on('assemble-scheduling-dialog-unlock', handleSchedulingDialogUnlock);

    // 先註冊接收目前 lock 清單
    socket.value?.on('assemble-scheduling-dialog-locks', handleSchedulingDialogLocks);

    // 再向 server 詢問目前有哪些 lock
    socket.value?.emit('get-assemble-scheduling-dialog-locks');

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
  if (!socket.value) return

  socket.value?.off('assemble-started', handleAssembleStarted);
  socket.value?.off('schedule_mode-ok', handleScheduleModeOk);
  socket.value?.off('icon-disable', handleIconDisable);

  socket.value?.off('assemble-batch-released2', handleAssembleBatchReleased);
  socket.value?.off('assemble-abnormal-created', handleAssembleBatchReleased);
  socket.value?.off('assemble-feed-released', handleAssembleFeedReleased);

  socket.value?.off('assemble-schedule-updated', handleAssembleScheduleUpdated);

  socket.value?.off('assemble-scheduling-dialog-lock', handleSchedulingDialogLock);
  socket.value?.off('assemble-scheduling-dialog-unlock', handleSchedulingDialogUnlock);

  socket.value?.off('assemble-scheduling-dialog-locks', handleSchedulingDialogLocks);

});

//=== method ===
const deepClone = (arr) => JSON.parse(JSON.stringify(arr || []))

const fmt = (d) => {
  if (!d) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const openDateMenu = () => {
  menuOpen.value = true
}

const runQuery = async () => {
  const payload = buildListInformationsPayload();
  await listInformations(payload);
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

function processTypeOf(row) {
  const workNum = String(row?.work_num || '')
  const step = Number(row?.process_step_code ?? 0)

  if (workNum === 'B109' || step === 3) return 21 // 組裝
  if (workNum === 'B110' || step === 2) return 22 // 檢驗
  if (workNum === 'B106' || step === 1) return 23 // 雷射

  return 0
}


// 以 material 為粒度，idKey 取 material_id（列表裡是 id=material.id）
// 若後端已支援 assemble 粒度，改成 row.assemble_id 並把 key 換成 'assemble'
function idOf(row) {
  return row.id;
}

/*
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
*/

/*
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
*/
const shouldRestoreRow = (row) => {
  if (!row) return false;

  const hasActiveTimer =
    row.show_timer === true ||
    row.show_timer === 1 ||
    row.show_timer === '1' ||
    Number(row.my_process_id || 0) > 0 ||
    Number(row.active_process_id || 0) > 0 ||
    Array.isArray(row.begin_records) && row.begin_records.length > 0;

  if (hasActiveTimer) {
    console.log('[shouldRestoreRow] active timer row=', {
      id: row.id,
      assemble_id: row.assemble_id,
      order_num: row.order_num,
      show_name: row.show_name,
      my_process_id: row.my_process_id,
      begin_records: row.begin_records,
      currentStartTime: row.currentStartTime,
    });
  }

  return hasActiveTimer;
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
    //row.show_name = me;
    //
    row.show_name =
    row.show_name ||
    row.active_user_ids?.[0] ||
    row.begin_records?.[0]?.user_id ||
    me;
    //
  }

  await nextTick();

  for (const row of rows) {
    const t = getT(row);
    if (!t?.restoreProcess) continue;

    const pType = processTypeOf(row)

    if (!pType) {
      console.warn('[restore] processTypeOf(row) failed:', row)
      continue
    }

    try {
      /*
      await t.restoreProcess(
        row.id,
        processTypeOf(row),
        me,
        row.assemble_id
      );
      */
      //
      const restoreUserId =
        row.show_name ||
        row.active_user_ids?.[0] ||
        row.begin_records?.[0]?.user_id ||
        me;

      await t.restoreProcess(
        row.id,
        processTypeOf(row),
        restoreUserId,
        row.assemble_id
      );
      //

      row._showMyTimer = true;
      //row.show_name = me;
      //
      row.show_name = restoreUserId;
      //
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

  materials_and_assembles.value[targetIndex].count=count

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

function checkShowTimer(row) {
  if (row?.show_timer === true || row?.show_timer === 1 || row?.show_timer === '1') {
    return true
  }

  if (Number(row?.my_process_id || 0) > 0) {
    return true
  }

  const t = getT(row)
  return !!(t && t.processId.value && (t.hasStarted.value || !t.isPaused.value))
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
    showSnackbar("已經領料生產報工了...", "orange-darken-2")
    return
  }

  selectedAsmId.value = row.index;

  // ✅ 先讓畫面立即顯示 timer，不等 refresh / 後端
  row._showMyTimer = true;
  row.show_timer = true;
  row.show_name = me;

  // ✅ 按開始後，立即讓 delete / pencil disable
  row.hasStarted = true;
  row.startStatus = true;
  row.isOpen = true;
  row.isOpenEmpId = me;
  //

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
    } else {

      // 同訂單 工序 全部 disable
      markSameOrderProcessLocked(row)

      console.log("emit socket assemble-started")
      socket.value?.emit('assemble-started', {
        assemble_id: row.assemble_id,
        material_id: row.id,
        order_num: row.order_num,
        //user_id: currentUser.value?.empID || currentUser.value?.emp_id || '',
        user_id: me,
        user_name: currentUser.value?.name || '',
      })

      console.log("emit socket icon-disable")
      const materialId = row.material_id || row.id
      socket.value?.emit('icon-disable', {
        material_id: materialId,
        assemble_id: row.assemble_id,
        order_num: row.order_num,
        //index: row.index,
      })

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
    //await listMaterialsAndAssembles();
    await reloadAssembleData()
    //await nextTick();
    //await restoreAllMyTimers();
  } finally {
    refreshing.value = false;
  }
};

const handleScheduleModeOk = async ()  => {
  console.log("handleScheduleModeOk 被觸發！")

  //await safeRefresh();
  //await listMaterialsAndAssembles({
  //  user_id: currentUser.value?.empID
  //})

  await reloadAssembleData();
}

const handleIconDisable = (data) => {
  console.log("handleIconDisable 被觸發！", data)

  const orderNum = data?.order_num
  if (!orderNum) return

  lockedOrderNums.value.add(orderNum)

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    if (row.order_num !== orderNum) return row

    return {
      ...row,
      has_any_running_process: true
    }
  })
}

const handleAssembleBatchReleased = async (payload) => {
  console.log('Begin 收到工序變更通知:', payload)
  await delay(300)
  await safeRefresh()
}

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

const customFilter = (value, query, item) => {
  if (!query) return true

  const q = String(query).toUpperCase()

  const raw = item?.raw || item || {}

  return [
    raw.order_num,
    raw.material_num,
    raw.material_comment,
    raw.comment,
    raw.assemble_work,
    raw.work_num,
  ].some(v => String(v || '').toUpperCase().includes(q))
}

const handleBarCode = async () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)

  await showMatchedItem(bar_code.value)
}

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
    const rowEl = document.getElementById(`receiveQtyID-${item.assemble_id}`)
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

const resetBatchDeleteState = () => {
  showBatchActions.value = false

  // 清空日期範圍
  dpRange2.value = []

  // 清掉顯示字串
  formattedDateRange.value = ''

  // 強制 VueDatePicker 重建
  menuKey.value++

  // 關閉 menu
  menuOpen.value = false

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
  return (
    Number(item?.process_step_enable || 0) === 1 ||
    item?.process_step_enable === true ||
    scheduledMaterialIds.value.has(item?.id)
  )
}

/*
const isEditProcessDisabled = (item) => {
  return (
    item?.has_any_running_process === true ||

    Number(item?.abnormal_qty || 0) > 0 ||
    Number(item?.isAssembleFirstAlarm_qty || 0) > 0 ||
    item?.is_abnormal_process === true
  )
}
*/

/*
const isEditProcessDisabled = (item) => {
  const row = item?.raw || item || {}

  return (
    row?.has_any_running_process === true ||
    row?.has_any_running_process === 1 ||
    row?.has_any_running_process === '1' ||
    row?.has_any_running_process === 'true' ||

    row?.hasStarted === true ||
    row?.hasStarted === 1 ||
    row?.hasStarted === '1' ||
    row?.startStatus === true ||
    row?.startStatus === 1 ||
    row?.startStatus === '1' ||

    Number(row?.abnormal_qty || 0) > 0 ||
    Number(row?.isAssembleFirstAlarm_qty || 0) > 0 ||
    row?.is_abnormal_process === true
  )
}
*/


const isEditProcessDisabled = (item) => {
  const row = item?.raw || item || {}

  const hasRunningProcess =
    row?.has_any_running_process === true ||
    row?.has_any_running_process === 1 ||
    row?.has_any_running_process === '1' ||
    row?.has_any_running_process === 'true'

  const hasStarted =
    row?.hasStarted === true ||
    row?.hasStarted === 1 ||
    row?.hasStarted === '1'

  const hasAbnormal =
    Number(row?.abnormal_qty || 0) > 0 ||
    Number(row?.isAssembleFirstAlarm_qty || 0) > 0 ||
    row?.is_abnormal_process === true

  return (
    hasRunningProcess ||
    hasStarted ||
    hasAbnormal
  )
}

const markSameOrderProcessLocked = (item) => {
  const orderNum = item?.order_num
  if (!orderNum) return

  lockedOrderNums.value.add(orderNum)

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    if (row.order_num !== orderNum) return row

    return {
      ...row,
      has_any_running_process: true
    }
  })
}

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

const fetchBomsV2 = async (item) => {
  try {
    const key = String(item.id)

    activeBomItemId.value = key
    isTableVisible.value = true

    const payload = {
      id: item.id,
      mode: 'picked',
    };

    console.log("getBoms payload:", payload);

    //const res = await getBoms(payload);
    await getBoms(payload);

    //bomsMap.value[item.id] = res?.data?.boms || [];
    bomsMap.value[item.id] = currentBoms.value

    //console.log("bomsMap:", item.id, bomsMap.value[item.id]);
    console.log("activeBomItemId:", activeBomItemId.value)
    console.log("bomsMap:", key, bomsMap.value[key])
    console.log("getFilteredBoms:", getFilteredBoms(item))

  } catch (e) {
    console.error("fetchBomsV2 failed:", e);
    //bomsMap.value[item.id] = [];
    bomsMap.value[String(item.id)] = []
  }
};

/*
const closeSchedulingDialog = () => {
  scheduling_dialog.value = false;
  scheduling_target_item.value = null;
};
*/

const closeSchedulingDialog = () => {
  const item = scheduling_target_item.value

  if (item?.id) {
    socket.value?.emit('assemble-scheduling-dialog-unlock', {
      source: 'PickReportForAssembleBegin',
      material_id: item.id,
      order_num: item.order_num,
      user_id: currentUser.value?.empID || '',
      user_name: currentUser.value?.name || '',
      client_id: schedulingClientId,
    })
  }

  scheduling_dialog.value = false
  scheduling_target_item.value = null
}

/*
const confirmSchedulingDialog = async () => {
  if (!scheduling_target_item.value?.id) {
    closeSchedulingDialog()
    return
  }

  // 先保存目前畫面 mode 的勾選狀態
  saveCurrentSchedulingSteps(scheduleMode.value)

  const hasAssemble = hasCheckedStep(assemble_steps.value)
  const hasCheck = hasCheckedStep(check_steps.value)

  // 1. 組裝 + 檢驗 都沒選
  if (!hasAssemble && !hasCheck) {
    scheduleAlertType.value = 'all-empty'
    scheduleAlertMessage.value = '在組裝及檢驗還沒有工序資料'
    scheduleAlertDialog.value = true
    return
  }

  // 2. 其中一種沒選
  if (!hasAssemble || !hasCheck) {
    scheduleAlertType.value = 'partial'

    if (!hasAssemble) {
      scheduleAlertMessage.value = '在組裝工序的工序資料不完整'
    } else {
      scheduleAlertMessage.value = '在檢驗工序的工序資料不完整'
    }

    scheduleAlertDialog.value = true
    return
  }

  // 3. 兩種都有選，直接走原本程序
  await doConfirmSchedulingDialog()

  console.log("schedule_mode-ok sock")

  socket.value?.emit('schedule_mode-ok');
}

const doConfirmSchedulingDialog = async () => {
  console.log("process_steps, assemble: ", assemble_steps.value)
  console.log("process_steps, check: ", check_steps.value)

  scheduling_dialog_loading.value = true

  try {
    const tt = await updateAssembleScheduleRows({
      id: scheduling_target_item.value.id,
      process_steps: {
        assemble: assemble_steps.value,
        check: check_steps.value
      }
    })

    console.log('準備開啟工序, updateAssembleScheduleRows res:', tt.status, tt.msg)

    //
    if (tt?.status) {
      console.log("開啟工序...")
      socket.value?.emit('assemble-batch-released2', {
        source: 'PickReportForAssembleBegin',
        reason: 'schedule_rows_updated',
        material_id: scheduling_target_item.value.id,
        order_num: scheduling_target_item.value.order_num,
      })

      socket.value?.emit('assemble-schedule-updated', {
        source: 'PickReportForAssembleBegin',
        reason: 'schedule_rows_updated',
        material_id: scheduling_target_item.value?.id,
        order_num: scheduling_target_item.value?.order_num,
      })
    }

    if (!tt?.status) {
      //showSnackbar(...)
      return
    }
    //

    const targetId = Number(scheduling_target_item.value.id)

    scheduling_target_item.value.process_step_enable = true
    scheduledMaterialIds.value.add(targetId)

    materials_and_assembles.value = materials_and_assembles.value.map(row => {
      if (Number(row.id) === targetId) {
        return {
          ...row,
          process_step_enable: true,
          process_steps: {
            assemble: deepClone(assemble_steps.value),
            check: deepClone(check_steps.value),
          },
        }
      }
      return row
    })

    await safeRefresh()

    materials_and_assembles.value = materials_and_assembles.value.map(row => {
      if (Number(row.id) === targetId) {
        return {
          ...row,
          process_step_enable: true
        }
      }
      return row
    })

    showSnackbar('已完成工序設定', 'success')
    closeSchedulingDialog()
  } catch (error) {
    console.error('confirmSchedulingDialog error:', error)
    showSnackbar('工序設定失敗', 'red-darken-2')
  } finally {
    scheduling_dialog_loading.value = false
  }
}
*/


const confirmSchedulingDialog = async () => {
  if (!scheduling_target_item.value?.id) {
    closeSchedulingDialog()
    return
  }

  // 先保存目前畫面 mode 的勾選狀態
  saveCurrentSchedulingSteps(scheduleMode.value)

  const hasAssemble = hasCheckedStep(assemble_steps.value)
  const hasCheck = hasCheckedStep(check_steps.value)

  // 除錯：確認目前開啟的是哪個 material
  console.log('[testconfirmSchedulingDialog] target=', {
    material_id: scheduling_target_item.value?.id,
    order_num: scheduling_target_item.value?.order_num,
    process_step_enable:
      scheduling_target_item.value?.process_step_enable,
    assemble_steps: deepClone(assemble_steps.value),
    check_steps: deepClone(check_steps.value),
  })

  // 1. 組裝 + 檢驗都沒選
  if (!hasAssemble && !hasCheck) {
    scheduleAlertType.value = 'all-empty'
    scheduleAlertMessage.value = '在組裝及檢驗還沒有工序資料'
    scheduleAlertDialog.value = true
    return
  }

  // 2. 其中一種沒選
  if (!hasAssemble || !hasCheck) {
    scheduleAlertType.value = 'partial'

    if (!hasAssemble) {
      scheduleAlertMessage.value = '在組裝工序的工序資料不完整'
    } else {
      scheduleAlertMessage.value = '在檢驗工序的工序資料不完整'
    }

    scheduleAlertDialog.value = true
    return
  }

  // 3. 兩種都有選
  await doConfirmSchedulingDialog()

  console.log('schedule_mode-ok sock')

  socket.value?.emit('schedule_mode-ok')
}

const doConfirmSchedulingDialog = async () => {
  const targetItem = scheduling_target_item.value

  if (!targetItem?.id) {
    showSnackbar('找不到目前設定工序的工單', 'red-darken-2')
    return
  }

  // 先固定住此次送出的 material，避免 refresh 或其他動作改掉 ref
  const targetId = Number(targetItem.id)
  const targetOrderNum = targetItem.order_num || ''

  // 保留此次設定完成的工序，避免 refresh 被舊資料覆蓋
  const savedProcessSteps = {
    assemble: deepClone(assemble_steps.value),
    check: deepClone(check_steps.value),
  }

  const payload = {
    id: targetId,
    process_steps: deepClone(savedProcessSteps),
  }
  //const payload = {
  //  id: targetId,
  //  process_steps: {
  //    assemble: deepClone(assemble_steps.value),
  //    check: deepClone(check_steps.value),
  //  },
  //}

  console.log(
  '[testconfirmSchedulingDialog] target=',
  JSON.stringify({
    material_id: scheduling_target_item.value?.id,
    order_num: scheduling_target_item.value?.order_num,
    process_step_enable:
      scheduling_target_item.value?.process_step_enable,
    assemble_checked: assemble_steps.value
      .filter(step => step.checked)
      .map(step => ({
        id: step.id,
        name: step.name,
      })),
    check_checked: check_steps.value
      .filter(step => step.checked)
      .map(step => ({
        id: step.id,
        name: step.name,
      })),
  }, null, 2)
)

  console.log(
    '[testdoConfirmSchedulingDialog] payload=',
    deepClone(payload)
  )

  scheduling_dialog_loading.value = true

  try {
    const tt = await updateAssembleScheduleRows(payload)

    console.log(
      '[testupdateAssembleScheduleRows] response=',
      tt
    )

    console.log(
      '準備開啟工序, updateAssembleScheduleRows res:',
      tt?.status,
      tt?.msg
    )

    // API 失敗時，不可以繼續把前端改成已設定
    if (!tt?.status) {
      console.error(
        '[testupdateAssembleScheduleRows] failed',
        {
          material_id: targetId,
          order_num: targetOrderNum,
          response: tt,
        }
      )

      showSnackbar(
        tt?.msg || '工序設定失敗',
        'red-darken-2'
      )
      return
    }

    console.log(
      '[testupdateAssembleScheduleRows] success',
      {
        material_id: targetId,
        order_num: targetOrderNum,
      }
    )

    socket.value?.emit('assemble-batch-released2', {
      source: 'PickReportForAssembleBegin',
      reason: 'schedule_rows_updated',
      material_id: targetId,
      order_num: targetOrderNum,
    })

    socket.value?.emit('assemble-schedule-updated', {
      source: 'PickReportForAssembleBegin',
      reason: 'schedule_rows_updated',
      material_id: targetId,
      order_num: targetOrderNum,
    })

    // 只有後端成功後，才更新前端狀態
    if (scheduling_target_item.value) {
      scheduling_target_item.value.process_step_enable = true
    }

    scheduledMaterialIds.value.add(targetId)

    materials_and_assembles.value =
    materials_and_assembles.value.map(row => {
      if (Number(row.id) === targetId) {
        return {
          ...row,
          process_step_enable: true,
          process_steps: deepClone(savedProcessSteps),
        }
      }

      return row
    })

    //materials_and_assembles.value =
    //materials_and_assembles.value.map(row => {
    //  if (Number(row.id) === targetId) {
    //    return {
    //      ...row,
    //      process_step_enable: true,
    //      process_steps: {
    //        assemble: deepClone(assemble_steps.value),
    //        check: deepClone(check_steps.value),
    //      },
    //    }
    //  }
    //
    //  return row
    //})

    console.log(
      '[before safeRefresh]',
      {
        targetId,
        targetOrderNum,
      }
    )

    await safeRefresh()

    console.log(
      '[after safeRefresh] matching rows=',
      materials_and_assembles.value
        .filter(row => Number(row.id) === targetId)
        .map(row => ({
          id: row.id,
          order_num: row.order_num,
          assemble_id: row.assemble_id,
          schedule_id: row.schedule_id,
          process_step_enable:
            row.process_step_enable,
          assemble_work: row.assemble_work,
        }))
    )

    // refresh 後，再保護一次前端旗標
    //materials_and_assembles.value =
    //materials_and_assembles.value.map(row => {
    //  if (Number(row.id) === targetId) {
    //    return {
    //      ...row,
    //      process_step_enable: true,
    //    }
    //  }
    //
    //  return row
    //})

    // refresh 後，再保護此次最新工序
    materials_and_assembles.value =
    materials_and_assembles.value.map(row => {
      if (Number(row.id) === targetId) {
        return {
          ...row,
          process_step_enable: true,
          process_steps: deepClone(savedProcessSteps),
        }
      }

      return row
    })

    showSnackbar('已完成工序設定', 'success')
    closeSchedulingDialog()
  } catch (error) {
    console.error(
      '[doConfirmSchedulingDialog] error=',
      error
    )

    showSnackbar(
      '工序設定失敗',
      'red-darken-2'
    )
  } finally {
    scheduling_dialog_loading.value = false
  }
}

/*
const lockExistingSteps = (steps = []) => {
  return deepClone(steps).map(step => ({
    ...step,
    checked: !!step.checked,
    locked: !!step.checked,   // 已經選過的工序鎖住，不能取消
  }))
}
*/
//
/*
const lockExistingSteps = (steps = []) => {
  return deepClone(steps).map(step => ({
    ...step,
    checked: !!step.checked,
    locked: !!step.checked,   // 只有 checked=true 才鎖住
  }))
}
*/
//
// 0714 丁副版本
const lockExistingSteps = (steps = []) => {
  return deepClone(Array.isArray(steps) ? steps : [])
    .filter(step => !step?.deleted)
    .map(step => ({
      ...step,
      checked: step?.checked === true,
      locked: false,
      deleted: false,
    }))
}

const hasUncheckedStep = (steps = []) => {
  return (steps || []).some(step => !step.checked)
}

const isAddProcessButtonDisabled = (item) => {
  //
  if (String(item.shortage_note || '').includes('缺料') && item.isLackMaterial != 99)
    return true
  //
  const ps = item?.process_steps || {}

  const assemble = Array.isArray(ps.assemble) ? ps.assemble : []
  const check = Array.isArray(ps.check) ? ps.check : []

  // 組裝與檢驗全部都已經勾完，才不能再新增
  const noMoreAssemble = !hasUncheckedStep(assemble)
  const noMoreCheck = !hasUncheckedStep(check)

  if (noMoreAssemble && noMoreCheck) return true

  // 原本這些條件保留
  if (item.top_work_rank != item.process_step_code) return true
  //if (item.delivery_qty != item.must_receive_qty) return true
  //
  // 尚未按 +工序的 B109 樣板列，must_receive_qty 可為 0
  if (
    !item.is_unscheduled_template &&
    Number(item.delivery_qty || 0) !== Number(item.must_receive_qty || 0)
  ) {
    return true
  }
  //
  return false
}
/*
const openSchedulingDialog = (item) => {
  scheduling_target_item.value = item

  const ps = item.process_steps || {}

  assemble_steps.value = lockExistingSteps(ps.assemble || [])
  check_steps.value = lockExistingSteps(ps.check || [])

  if (hasUncheckedStep(assemble_steps.value)) {
    scheduleMode.value = 'assemble'
    schedulingSteps.value = deepClone(assemble_steps.value)
  } else {
    scheduleMode.value = 'check'
    schedulingSteps.value = deepClone(check_steps.value)
  }

  scheduling_dialog_orde_num.value = item.order_num
  scheduling_dialog.value = true
}
*/

const resetUnscheduledSteps = (steps = []) => {
  return (Array.isArray(steps) ? steps : [])
    .filter(step => !step?.deleted)
    .map(step => ({
      ...step,
      checked: false,
      locked: false,
      deleted: false,
    }))
}

/*
const openSchedulingDialog = (item) => {
  if (isSchedulingDialogLocked(item)) {
    showSnackbar(
      `此工單正在由 ${item.scheduling_dialog_locked_by || '其他人'} 設定工序`,
      'red-darken-2'
    )
    return
  }

  scheduling_target_item.value = item

  socket.value?.emit('assemble-scheduling-dialog-lock', {
    source: 'PickReportForAssembleBegin',
    material_id: item.id,
    order_num: item.order_num,
    user_id: currentUser.value?.empID || '',
    user_name: currentUser.value?.name || '',
    client_id: schedulingClientId,
  })

  const ps = item.process_steps || {}

  assemble_steps.value = lockExistingSteps(ps.assemble || [])
  check_steps.value = lockExistingSteps(ps.check || [])

  if (hasUncheckedStep(assemble_steps.value)) {
    scheduleMode.value = 'assemble'
    schedulingSteps.value = deepClone(assemble_steps.value)
  } else {
    scheduleMode.value = 'check'
    schedulingSteps.value = deepClone(check_steps.value)
  }

  scheduling_dialog_orde_num.value = item.order_num
  scheduling_dialog.value = true
}
*/
//
/*
const openSchedulingDialog = (item) => {
  if (isSchedulingDialogLocked(item)) {
    showSnackbar(
      `此工單正在由 ${item.scheduling_dialog_locked_by || '其他人'} 設定工序`,
      'red-darken-2'
    )
    return
  }

  scheduling_target_item.value = item

  socket.value?.emit('assemble-scheduling-dialog-lock', {
    source: 'PickReportForAssembleBegin',
    material_id: item.id,
    order_num: item.order_num,
    user_id: currentUser.value?.empID || '',
    user_name: currentUser.value?.name || '',
    client_id: schedulingClientId,
  })

  //const ps = item.process_steps || {}
  const ps = item.process_steps ?? {
    assemble: [],
    check: [],
  }

  const isUnscheduled =
    Number(item.process_step_enable ?? 0) === 0

  if (isUnscheduled) {
    // 尚未設定工序：
    // 每次開啟都全部清空，且 checkbox 可操作
    assemble_steps.value = (Array.isArray(ps.assemble) ? ps.assemble : [])
      .filter(step => !step?.deleted)
      .map(step => ({
        ...step,
        checked: false,
        locked: false,
        deleted: false,
      }))

    check_steps.value = (Array.isArray(ps.check) ? ps.check : [])
      .filter(step => !step?.deleted)
      .map(step => ({
        ...step,
        checked: false,
        locked: false,
        deleted: false,
      }))
  } else {
    // 已設定工序：
    // 保留原本已勾選與 locked 狀態
    assemble_steps.value = lockExistingSteps(
      Array.isArray(ps.assemble)
        ? ps.assemble.filter(step => !step?.deleted)
        : []
    )

    check_steps.value = lockExistingSteps(
      Array.isArray(ps.check)
        ? ps.check.filter(step => !step?.deleted)
        : []
    )
  }

  // 尚未設定工序時，固定先顯示組裝頁籤
  if (isUnscheduled) {
    scheduleMode.value = 'assemble'
    schedulingSteps.value = deepClone(assemble_steps.value)
  } else if (hasUncheckedStep(assemble_steps.value)) {
    scheduleMode.value = 'assemble'
    schedulingSteps.value = deepClone(assemble_steps.value)
  } else {
    scheduleMode.value = 'check'
    schedulingSteps.value = deepClone(check_steps.value)
  }

  scheduling_dialog_orde_num.value = item.order_num
  scheduling_dialog.value = true
}
*/
//
const openSchedulingDialog = (item) => {
  const row = item?.raw || item

  if (!row?.id) {
    showSnackbar('找不到工單資料', 'red-darken-2')
    return
  }

  if (isSchedulingDialogLocked(row)) {
    showSnackbar(
      `此工單正在由 ${
        row.scheduling_dialog_locked_by || '其他人'
      } 設定工序`,
      'red-darken-2'
    )
    return
  }

  if (isEditProcessDisabled(row)) {
    showSnackbar(
      '此工單已有工序開工，不能再修改工序',
      'red-darken-2'
    )
    return
  }

  scheduling_target_item.value = row

  socket.value?.emit('assemble-scheduling-dialog-lock', {
    source: 'PickReportForAssembleBegin',
    material_id: row.id,
    order_num: row.order_num,
    user_id: currentUser.value?.empID || '',
    user_name: currentUser.value?.name || '',
    client_id: schedulingClientId,
  })

  const processSteps = row.process_steps || {
    assemble: [],
    check: [],
  }

  // 保留後端目前的 checked 結果，但全部 checkbox 可修改
  assemble_steps.value = lockExistingSteps(
    Array.isArray(processSteps.assemble)
      ? processSteps.assemble
      : []
  )

  check_steps.value = lockExistingSteps(
    Array.isArray(processSteps.check)
      ? processSteps.check
      : []
  )

  // 每次打開固定先顯示組裝工序
  scheduleMode.value = 'assemble'
  schedulingSteps.value = deepClone(assemble_steps.value)

  scheduling_dialog_orde_num.value = row.order_num || ''
  scheduling_dialog.value = true
}
//

const onClickDeleteSchedule = async (item) => {
  if (isEditProcessDisabled(item)) return

  const scheduleId = Number(item.schedule_id || 0)

  if (!scheduleId) {
    alert('找不到 schedule_id，無法刪除此工序')
    return
  }

  if (!confirm(`確定刪除此工序？\n訂單：${item.order_num}`)) {
    return
  }

  try {
    const tt = await deleteAssembleScheduleRow({
      id: item.id,
      assemble_id: item.assemble_id,
      schedule_id: scheduleId,
      work_num: item.work_num,
    })

    if (!tt.status) {
      showSnackbar(tt.msg || '刪除工序失敗', 'red accent-2');

      // 返回後重新載入，保留原本最後製程資料

      await reloadAssembleData()

      return;
    }

    showSnackbar("刪除工序完成!", "green darken-1");

    await reloadAssembleData()

  } catch (err) {
    console.error('deleteAssembleScheduleRow error:', err)
    showSnackbar('刪除工序發生錯誤', 'red accent-2');
  }
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

/*
function canBeginBySchedule(item) {

  const row = item?.raw || item || {}

  if (!(Number(row.schedule_id) > 0))
    return false

  if (row.show_timer)
    return false

  if (row.has_any_running_process)
    return false

  if (Number(row.users_for_press_start || 0) > 0)
    return false

  if ((row.active_user_ids || []).length > 0)
    return false

  return true
}
*/
function canBeginBySchedule(item) {
  return !isStartButtonDisabled(item)
}

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

  console.log("startTime step 1...")

  console.log("startTime step 2...")
  // 記錄當前領料生產開始時間
  payload = {
    assemble_id: item.assemble_id,
    record_name: 'currentStartTime',
    record_data: formatDateTime(new Date()),
  };
  await updateAssemble(payload);

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
    const mergeEnabled = Boolean(item.merge_enabled);

    const payload = mergeEnabled
      ? {
          order_num: item.order_num,
          mode: 'picked',
        }
      : {
          id: item.id,
          mode: 'picked',
        };

    console.log("getOrderPickedBoms payload:", payload);

    res = await getOrderPickedBoms(payload);

    boms.value = res?.data?.boms || [];
  } catch (e) {
    console.error("fetchBoms failed:", e);
    boms.value = [];
  }
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

const hasCheckedStep = (steps) => {
  return (steps || []).some(step => step.checked === true)
}

const resetSchedulingDialogToInitialMode = () => {
  scheduleMode.value = 'assemble'
  schedulingSteps.value = deepClone(assemble_steps.value)
}

const backToSchedulingDialog = () => {
  scheduleAlertDialog.value = false

  if (scheduleAlertType.value === 'all-empty') {
    resetSchedulingDialogToInitialMode()
  }

  scheduleAlertType.value = ''
}

const continueConfirmSchedulingDialog = async () => {
  scheduleAlertDialog.value = false
  scheduleAlertType.value = ''
  await doConfirmSchedulingDialog()
}

const getFilteredBoms = (item) => {
  return (bomsMap.value[String(item.id)] || []).filter(bom => bom.receive)
}

const hasOtherUserStarted = (row) => {
  const r = row?.raw || row || {}

  const me = String(
    currentUser.value?.empID ||
    currentUser.value?.emp_id ||
    currentUser.value?.user_id ||
    ''
  ).trim()

  const assembleKey = String(r.assemble_id)

  const users = Array.isArray(startedUsersByAssembleId.value[assembleKey])
    ? startedUsersByAssembleId.value[assembleKey]
    : Array.isArray(r.active_user_ids)
      ? r.active_user_ids
      : []

  if (users.length > 0) {
    return users.some(uid => String(uid).trim() && String(uid).trim() !== me)
  }

  const count = Number(r.users_for_press_start || 0)
  return count > 0 && String(r.user_id || '').trim() !== me
}

const handleAssembleStarted = async (payload) => {
  const assembleId = Number(payload?.assemble_id)
  const userId = String(payload?.user_id || '').trim()
  const orderNum = payload?.order_num

  if (!assembleId || !userId) return

  // delete / pencil：同訂單全部鎖住
  if (orderNum) {
    lockedOrderNums.value.add(orderNum)
  }

  // 開始按鍵綠點：只記錄該 assemble_id
  const key = String(assembleId)
  const oldList = Array.isArray(startedUsersByAssembleId.value[key])
    ? [...startedUsersByAssembleId.value[key]]
    : []

  if (!oldList.includes(userId)) {
    oldList.push(userId)
  }

  startedUsersByAssembleId.value[key] = oldList

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    const sameOrder = row.order_num === orderNum
    const sameAssemble = Number(row.assemble_id) === assembleId

    return {
      ...row,

      // 同訂單 b1/b2/b3 刪除/編輯都 disable
      has_any_running_process: sameOrder
        ? true
        : row.has_any_running_process,

      // 只有被開始的那一筆顯示「已有人開工」
      active_user_ids: sameAssemble
        ? oldList
        : row.active_user_ids
    }
  })

  await delay(300)
  await safeRefresh()
}

const reloadAssembleData = async () => {
  await listMaterialsAndAssembles({
    user_id: currentUser.value?.empID
  })

  // ------------------------------------------------------------
  // DEBUG：檢查 121100020280 為什麼 Begin 顯示 4 筆
  // ------------------------------------------------------------
  console.table("assembleTable",
    (materials_and_assembles.value || [])
      .filter(
        row =>
          String(row.order_num || '').trim() === '121100020280'
      )
      .map(row => ({
        id: row.id,
        assemble_id: row.assemble_id,
        work_num: row.work_num,
        schedule_id: row.schedule_id,
        schedule_name: row.schedule_name,
        reason: row.reason,
        release_batch_no: row.release_batch_no,
        process_step_code: row.process_step_code,
        isAssembleStationShow: row.isAssembleStationShow,
        hasStarted: row.hasStarted,
        show_timer: row.show_timer,
        row_key: row.row_key,
      }))
  )

  applyOrderRunningLocks()
}

const handleAssembleFeedReleased = async (payload) => {
  console.log('[Begin] assemble-feed-released', payload)

  await safeRefresh()
}

const handleAssembleScheduleUpdated = async (payload) => {
  console.log('Begin 收到 assemble-schedule-updated:', payload)

  await delay(500)
  await safeRefresh()
}

// 延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/*
const isScheduleActionDisabled = (item) => {
  const row = item?.raw || item || {}

  return (
    isEditProcessDisabled(row) ||
    row.has_any_running_process === true ||
    row.has_any_running_process === 1 ||
    row.has_any_running_process === '1' ||
    row.has_any_running_process === 'true' ||
    hasOtherUserStarted(row) ||
    row.show_timer === true
  )
}
*/
const isScheduleActionDisabled = (item) => {
  const row = item?.raw || item || {}
  const orderNum = String(row.order_num || '').trim()

  return (
    lockedOrderNums.value.has(orderNum) ||

    row.order_has_started_process === true ||
    row.order_has_started_process === 1 ||
    row.order_has_started_process === '1' ||

    isEditProcessDisabled(row) ||

    row.has_any_running_process === true ||
    row.has_any_running_process === 1 ||
    row.has_any_running_process === '1' ||
    row.has_any_running_process === 'true' ||

    hasOtherUserStarted(row) ||
    row.show_timer === true
  )
}

const lockedOrderNums = ref(new Set());

const startedUsersByAssembleId = ref({});

const isTruthy = (v) =>
  v === true || v === 1 || v === '1' || v === 'true'

const rowHasRunningProcess = (row) => {
  return (
    isTruthy(row?.has_any_running_process) ||
    isTruthy(row?.show_timer) ||
    Number(row?.users_for_press_start || 0) > 0 ||
    Number(row?.active_count || 0) > 0 ||
    (Array.isArray(row?.active_user_ids) && row.active_user_ids.length > 0)
  )
}

const applyOrderRunningLocks = () => {
  const runningOrders = new Set([...lockedOrderNums.value])

  materials_and_assembles.value.forEach(row => {
    if (rowHasRunningProcess(row) && row?.order_num) {
      runningOrders.add(row.order_num)
    }
  })

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    const assembleKey = String(row.assemble_id)
    const localActiveUsers = startedUsersByAssembleId.value[assembleKey]

    return {
      ...row,

      // refresh 後仍維持同訂單刪除/編輯 disable
      has_any_running_process:
        rowHasRunningProcess(row) || runningOrders.has(row.order_num),

      // refresh 後補回該工序的 active_user_ids
      active_user_ids: Array.isArray(localActiveUsers)
        ? localActiveUsers
        : row.active_user_ids
    }
  })

  lockedOrderNums.value = runningOrders
}

/*
const handleSchedulingDialogLock = (payload) => {

  if (payload?.client_id === schedulingClientId) return

  const materialId = Number(payload?.material_id)
  if (!materialId) return

  schedulingDialogLockedIds.value.add(materialId)

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    if (Number(row.id) !== materialId) return row

    return {
      ...row,
      scheduling_dialog_locked: true,
      scheduling_dialog_locked_by: payload?.user_name || payload?.user_id || '其他人'
    }
  })

}
*/
//
const handleSchedulingDialogLock = (payload) => {
  const myUserId = String(currentUser.value?.empID || '').trim()
  const lockUserId = String(payload?.user_id || '').trim()

  // 同一個瀏覽器分頁／連線
  if (payload?.client_id === schedulingClientId) return

  // 同一位員工，即使重新整理或開另一個分頁，也不顯示紅色鎖定
  if (myUserId && lockUserId && myUserId === lockUserId) return

  const materialId = Number(payload?.material_id)
  if (!materialId) return

  schedulingDialogLockedIds.value.add(materialId)

  materials_and_assembles.value =
    materials_and_assembles.value.map(row => {
      if (Number(row.id) !== materialId) return row

      return {
        ...row,
        scheduling_dialog_locked: true,
        scheduling_dialog_locked_by:
          payload?.user_name ||
          payload?.user_id ||
          '其他人'
      }
    })
}

/*
const handleSchedulingDialogUnlock = (payload) => {

  if (payload?.client_id === schedulingClientId) return

  const materialId = Number(payload?.material_id)
  if (!materialId) return

  schedulingDialogLockedIds.value.delete(materialId)

  materials_and_assembles.value = materials_and_assembles.value.map(row => {
    if (Number(row.id) !== materialId) return row

    return {
      ...row,
      scheduling_dialog_locked: false,
      scheduling_dialog_locked_by: ''
    }
  })

}
*/
//
const handleSchedulingDialogUnlock = (payload) => {
  const myUserId = String(currentUser.value?.empID || '').trim()
  const lockUserId = String(payload?.user_id || '').trim()

  if (payload?.client_id === schedulingClientId) return

  // 同一位員工的 unlock 不需處理，因為自己的畫面本來就沒加入 lockedIds
  if (myUserId && lockUserId && myUserId === lockUserId) return

  const materialId = Number(payload?.material_id)
  if (!materialId) return

  schedulingDialogLockedIds.value.delete(materialId)

  materials_and_assembles.value =
    materials_and_assembles.value.map(row => {
      if (Number(row.id) !== materialId) return row

      return {
        ...row,
        scheduling_dialog_locked: false,
        scheduling_dialog_locked_by: ''
      }
    })
}

const isSchedulingDialogLocked = (item) => {
  return schedulingDialogLockedIds.value.has(Number(item?.id))
}

const onClickOpenSchedulingDialog = (item) => {
  if (isSchedulingDialogLocked(item)) {
    showSnackbar(
      `此工單正在由 ${item.scheduling_dialog_locked_by || '其他人'} 設定工序，請稍後再試`,
      'red-darken-2'
    )
    return
  }

  if (isAddProcessButtonDisabled(item)) {
    showSnackbar('此工單目前不可設定工序', 'red-darken-2')
    return
  }

  openSchedulingDialog(item)
}

const handleSchedulingDialogLocks = (locks) => {
  if (!Array.isArray(locks)) return

  locks.forEach(lock => {
    handleSchedulingDialogLock(lock)
  })
}

/*
const isStartButtonDisabled = (item) => {
  const row = item?.raw || item || {}

  if (
  row.assemble_id == 4243 ||
  row.id == 4243
) {
  console.log("=====4243=====");
  console.log(JSON.parse(JSON.stringify(row)));
}

  if (!row) return true

  // 沒有工序，不可開始
  if (!(Number(row.schedule_id) > 0)) return true

  // 這筆本身正在計時，才 disable
  if (
    row.show_timer === true ||
    row.show_timer === 1 ||
    row.show_timer === '1' ||
    row.is_current_running === true ||
    row.is_current_running === 1 ||
    row.is_current_running === '1' ||
    Number(row.my_process_id || 0) > 0 ||
    Number(row.active_process_id || 0) > 0
  ) {
    return true
  }

  // 這筆已結束
  if (row.currentEndTime) return true

  // 只有 show2_ok = 3 可開始
  if (![3, '3'].includes(row.show2_ok)) return true

  // 這筆本身 input_disable = 1
  if (
    row.input_disable === true ||
    row.input_disable === 1 ||
    row.input_disable === '1'
  ) {
    return true
  }

  return false
}
*/

/*
const isStartButtonDisabled = (item) => {
  const row = item?.raw || item || {}
  if (!row) return true

  if (!(Number(row.schedule_id) > 0)) return true

  if (
    row.show_timer === true ||
    row.show_timer === 1 ||
    row.show_timer === '1' ||
    row.is_current_running === true ||
    row.is_current_running === 1 ||
    row.is_current_running === '1' ||
    Number(row.my_process_id || 0) > 0 ||
    Number(row.active_process_id || 0) > 0
  ) {
    return true
  }

  if (row.currentEndTime) return true

  // 注意：後端目前沒有回 show2_ok，所以不能用 undefined 擋開始鍵
  if (
    row.show2_ok !== undefined &&
    row.show2_ok !== null &&
    row.show2_ok !== '' &&
    ![3, '3'].includes(row.show2_ok)
  ) {
    return true
  }

  if (
    row.input_disable === true ||
    row.input_disable === 1 ||
    row.input_disable === '1'
  ) {
    return true
  }

  return false
}
*/
const isStartButtonDisabled = (item) => {
  const row = item?.raw || item || {}
  if (!row) return true

  // 沒有工序
  if (!(Number(row.schedule_id) > 0)) return true

  // 已完成
  if (row.currentEndTime) return true

  // show2_ok 不允許開始
  if (
    row.show2_ok !== undefined &&
    row.show2_ok !== null &&
    row.show2_ok !== '' &&
    ![3, '3'].includes(row.show2_ok)
  ) {
    return true
  }

  // 後端明確禁止輸入
  if (
    row.input_disable === true ||
    row.input_disable === 1 ||
    row.input_disable === '1'
  ) {
    return true
  }

  return false
}

</script>

<style lang="scss" scoped>
//@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

@import "../styles/variables.scss";

* {
  font-family:
    "Microsoft JhengHei",
    "微軟正黑體",
    "Noto Sans TC",
    sans-serif;
}

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

#bar_code :deep(input) {
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
}

/* disabled 狀態 */
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

/* 防止 hover 影響 */
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

// Vuetify disabled 預設會降低 opacity → 關掉
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

/* disabled */
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

.btn-add-process {
  background: #c8e6c9 !important;
  color: #1b5e20 !important;
  transform: translateX(20px);
}

.btn-add-process:hover {
  background: #a5d6a7 !important;
}

.btn-add-process--edit {
  background: #fff3cd !important; /* 淡黃色 */
  color: #7a5b00 !important;
}

.btn-add-process--edit:hover {
  background: #ffe8a1 !important;
}

.btn-add-process--disabled {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;
  cursor: not-allowed !important;
  box-shadow: none !important;
  opacity: 1 !important;
}

.add-process-icon-group {
  display: flex;
  align-items: center;
  gap: 10px;

  transform: translateX(26px);
}

.btn-add-process-icon {
  width: 34px !important;
  min-width: 34px !important;
  height: 32px !important;
  background: #fff3cd !important;
  color: #7a5b00 !important;
}

.btn-add-process-icon:hover {
  background: #ffe8a1 !important;
}


/* delete / pencil disabled 外觀 = 開始鍵 disabled */
.btn-add-process-icon.v-btn--disabled {
  background: #e0e0e0 !important;
  color: #9e9e9e !important;
  cursor: not-allowed !important;
  opacity: 1 !important;

}

.btn-add-process-icon.v-btn--disabled .v-icon {
  color: rgba(var(--v-theme-on-surface), 0.38) !important;
}

.begin-cell-shift {
  transform: translateX(30px);
}

.batch-actions {
  display: flex;
  gap: 8px;
}

.erp-alert-box {
  display: flex;
  align-items: center;
  min-height: 76px;
  padding: 16px 18px;
  border-radius: 8px;
  border-left: 6px solid;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
}

.erp-alert-error {
  background: #fff5f5;
  border-left-color: #d32f2f;
}

.erp-alert-warning {
  background: #f2f7ff;
  border-left-color: #1976d2;
}

.erp-alert-message {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.7;
}

.erp-alert-message-error {
  color: #c62828;
}

.erp-alert-message-warning {
  color: #1565c0;
}

.abnormal-process-text {
  color: red;
  font-weight: 700;
  margin-left: 6px;
}

.start-btn-wrap {
  position: relative;
  display: inline-block;
}

.other-user-dot {
  position: absolute;
  top: -8px;
  right: -8px;

  width: 15px;
  height: 15px;

  background: #00c853;
  color: white;

  border-radius: 50%;
  border: 2px solid white;

  display: flex;
  align-items: center;
  justify-content: center;

  font-size: 11px;
  font-weight: 700;

  z-index: 10;

  box-shadow: 0 0 4px rgba(0,0,0,.25);
}

.barcode-input :deep(.v-field__input) {
  padding-left: 12px;
}

.barcode-input :deep(.v-label) {
  margin-left: 30px;
}

.top-input {
  width: 180px;
}

.top-input :deep(.v-field) {
  height: 32px;
  min-height: 32px;
}

.top-input :deep(.v-field__field) {
  height: 32px;
}

.top-input :deep(.v-field__input) {
  min-height: 32px;
  height: 32px;
  padding-top: 0;
  padding-bottom: 0;
  align-items: center;
}

.top-input :deep(input) {
  height: 32px;
  line-height: 32px;
  padding-top: 0;
  padding-bottom: 0;
}

.toolbar-row {
  display: flex;
  align-items: center;

  flex-wrap: nowrap;
  //overflow-x: auto;
  min-width: 0 !important;
  overflow-x: hidden !important;
  overflow-y: hidden;
  gap: 16px;
}

//.toolbar-row {
//  min-width: 0 !important;
//  overflow-x: hidden !important;
//}

.toolbar-row .v-col {
  min-width: 0 !important;
}

.btn-add-process--disabled {
  opacity: 0.45;
  pointer-events: auto;
  cursor: not-allowed;
}

.btn-add-process--locked {
  background-color: #ffcdd2 !important;
  color: #b71c1c !important;
  border: 1px solid #e57373 !important;
}

.btn-add-process--locked:hover {
  background-color: #ef9a9a !important;
}

</style>