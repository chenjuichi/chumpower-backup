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

  <!-- 燈號控制面板 -->
  <DraggablePanel v-show="toggle_exclusive === 2"  :initX="panelX" :initY="panelY" :isDraggable="true" ref="draggablePanel">
    <LedLights :activeColor="activeColor" />
  </DraggablePanel>

  <ConfirmDialog ref="confirmRef" />

  <!-- data table -->
  <v-data-table
    :headers="headers"
    :items="materials"

    :search="search"
    :custom-filter="customFilter"

    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"
    :items-per-page-options="footerOptions"
    items-per-page="5"
    item-value="id"
    show-select
    :value="selectedItems"
    class="elevation-10 custom-table"
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
        <v-card-title
          class="d-flex align-center pe-2"
          style="font-weight:700; position: relative; right: 10px;"
        >
          <v-menu
            v-model="show_dropdown"
            location="bottom start"
            :close-on-content-click="false"
            content-class="help-menu"
          >
            <template #activator="{ props }">
              <strong class="dropdown-label" v-bind="props">
                組裝區備料清單
              </strong>
            </template>
            <v-card
              class="text-caption help-card"
              color="black"
              variant='tonal'
            >
              <div style="font-weight:700; margin-bottom:6px;">
                操作說明（第 {{ page + 1 }} / {{ pages.length }} 頁）
              </div>

              <div class="help-body">
                <Transition :name="transitionName" mode="out-in">
                  <div :key="page" class="content-area">
                    <div v-for="(line, idx) in pages[page]" :key="idx">
                      <span v-html="line"></span>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- 底部換頁 -->
              <div class="help-footer d-flex align-center justify-space-evenly">
                <v-btn class="help-btn" size="small" variant="outlined" :disabled="page === 0" @click="goPrev">
                  上一頁
                </v-btn>

                <div class="help-page-indicator">
                  {{ page + 1 }} / {{ pages.length }}
                </div>

                <v-btn class="help-btn" size="small" variant="outlined" :disabled="page === pages.length - 1" @click="goNext">
                  下一頁
                </v-btn>
              </div>
            </v-card>
          </v-menu>

          <!--組裝區備料清單-->
          <v-spacer />

          <!--客製化 匯入清單按鍵-->
          <v-btn
            :disabled="fileCount === 0"
            color="primary"
            variant="outlined"

            :style="{
              position: 'relative',
              right: screenSizeInInches > 20 ? '600px' : '130px',
              top: '0px',
              fontWeight: '700',
              width: '120px'
            }"
            @click="readAllExcelFun"
          >
            <v-icon left color="green">mdi-microsoft-excel</v-icon>
            <span style="color: #000;">匯入清單</span>
            <template v-if="fileCount > 0" v-slot:append>
              <v-badge color="info" :content="fileCount" inline />
            </template>
          </v-btn>

          <!-- Bom 編輯對話視窗-->
          <div class="pa-4 text-center">
            <v-dialog v-model="editDialog" max-width="980">
              <v-card :style="{ maxHeight: modify_boms.length > 5 ? '800px' : 'unset', overflowY: modify_boms.length > 5 ? 'auto' : 'unset' }">
                <v-card-title class="text-h5 sticky-title" style="background-color: #1b4965; color: white;">
                  工單維護
                <!--
                  <v-fade-transition mode="out-in">
                    <v-btn
                      style="position: relative; right: -550px;"
                      color="success"
                      prepend-icon="mdi-content-save"
                      :disabled="editDialogBtnDisable"
                      text="確定"
                      class="text-none"
                      @click="updateModifyMaterialAndBomsFun"
                      variant="flat"
                      flat
                    />
                  </v-fade-transition>
                -->
                </v-card-title>
                <v-card-text>
                  <!--第 1 列-->
                  <v-row>
                    <v-col cols="12" md="3" class="d-flex" justify="start">
                      <v-text-field
                        v-model="selectedOrderNum"
                        @keyup.enter="handleOrderNumSearch"
                        variant="solo"
                        readonly
                        class="modify_order_num"
                      >
                        <template #prepend>
                          <span class="text-caption">訂單編號</span>
                        </template>
                      </v-text-field>
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex" justify="end">
                      <span style="color: #0D47A1;" class="mb-4 mr-5 text-caption">訂單日期</span>
                      <v-menu
                        v-model="fromDateMenu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        max-width="300px"
                        min-width="300px"
                      >
                        <template #activator="{ props }">
                          <v-text-field
                            prepend-icon="mdi-calendar"
                            readonly
                            :value="formattedDate"
                            v-bind="props"
                            variant="solo"
                            class="modify_date"
                          />
                        </template>
                        <v-date-picker
                          v-model="fromDateVal"
                          color="blue-lighten-1"
                          @update:model-value="handleDateChange"
                        />
                      </v-menu>
                    </v-col>
                    <v-col cols="12" md="3" class="d-flex">
                      <v-text-field
                        variant="solo"
                        required
                        class="modify_qty"
                        @keydown="handleKeyDown"
                        v-model="selectedReqQty"
                      >
                        <template #prepend>
                          <span class="text-caption">訂單數量</span>
                        </template>
                      </v-text-field>
                    </v-col>
                    <v-col cols="12" md="2" class="d-flex" justify="start">
                      <v-btn
                        color="success"
                        prepend-icon="mdi-content-save"
                        text="修改"
                        class="text-none"
                        @click="updateModifyMaterialAndBomsFun"
                        variant="flat"
                      />
                    </v-col>
                  </v-row>
                    <div class="seperator" style="position:relative; left: 60px; top: -10px;">
                      <h5><span></span></h5>
                    </div>
                  <!--第 2 列-->
                  <v-row>
                    <v-col cols="12" md="2"
                      style="padding-top:0px; padding-bottom:0px; margin-top: -0px;"
                       class="d-flex justify-start align-center pt-0 pb-0">
                      <!--刪除工單按鍵-->
                        <v-btn
                          variant="outlined"
                          style="width:100px; min-width:100px; font-weight:700;"
                          class="warnning_btn"
                          @click="onDelete"
                        >
                          <v-icon left style="font-weight:700; color:#ff4444">mdi-file-remove</v-icon>
                          <span style="color: #0D47A1; font-weight:600;">刪除工單</span>
                        </v-btn>

                    <!--
                      <div class="flip_btn">
                        <v-btn
                          style="position:relative; right:45px; width:100px; min-width:100px; font-weight:700; border-radius:6px; border-width:1.5px; border-color:#ff5252"

                          class="warnning_btn side default-side primary thin mt-1 mx-auto"

                          @mouseenter="editDialog = true"
                        >
                          <v-icon left style="font-weight:700; color:#ff4444">mdi-file-remove</v-icon>
                          <span style="color: #0D47A1; font-weight:600;">刪除工單</span>
                        </v-btn>
                        <div class="side hover-side" style="position:relative; right:40px;">
                          <v-btn color="#ff4444" style="position:relative; right:3px; width:70px;" class="mt-n1 mr-15 mx-auto" @click="editDialog = false">
                            <v-icon left size="24px" color="#ffffff">mdi-close-circle-outline</v-icon>
                            <span style="color:#ffffff">取消</span>
                          </v-btn>
                          <v-btn color="#00c851" style="position:relative; left:3px; width:70px;" class="mt-n1 mr-15 mx-auto" @click="removeMaterialsAndRelationTableFun">
                            <v-icon left size="24px" color="#ffffff">mdi-check-circle-outline</v-icon>
                            <span style="color:#ffffff">確定</span>
                          </v-btn>
                        </div>
                      </div>
                    -->
                    </v-col>
                    <!--</v-col>-->
                    <v-col cols="12" md="10"></v-col>
                  </v-row>
                  <!--第 3 列-->
                  <v-row>
                    <v-col cols="12" md="2" style="margin-top: 15px;">
                      <!--匯入工單按鍵-->
                      <v-btn
                        color="primary"
                        variant="outlined"
                        style="width:100px; min-width:100px; font-weight:700;"
                        @click="onModify"
                      >
                        <v-icon left color="green">mdi-microsoft-excel</v-icon>
                        <span style="color: #0D47A1;">匯入工單</span>
                      </v-btn>
                    </v-col>
                    <v-col cols="12" md="10">
                      <v-table class="inner" density="compact" fixed-header>
                        <thead style="color: black;">
                          <tr>
                            <th class="text-left">元件</th>
                            <th class="text-left">物料</th>
                            <th class="text-left">數量</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr
                            v-for="(bom_item, index) in modify_boms"
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
                          </tr>
                        </tbody>
                      </v-table>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-dialog>
          </div>

          <!--客製化 員工選單-->
          <div class="employee-select" style="position: relative; right: 160px; width: 160px;">
            <v-text-field
              v-model="selectedEmployee"
              @keyup.enter="handleEmployeeSearch"

              variant="outlined"
              density="comfortable"
              style="
                min-width: 160px;
                width: 160px;
                position: absolute;
                z-index: 2;
                transition: opacity 0.3s ease, visibility 0.3s ease;
              "
              :style="{ opacity: showMenu ? 1 : 0, visibility: showMenu ? 'visible' : 'hidden' }"
            />

            <!-- v-select 用於選擇員工 -->
            <v-select
              v-model="inputSelectEmployee"
              :items="formattedDesserts"
              item-title="display"
              item-value="emp_id"
              :placeholder="placeholderTextForEmployee"
              variant="outlined"
              density="comfortable"
              @update:modelValue="updateEmployeeFieldFromSelect"
              style="
                min-width: 160px;
                width: 160px;
                position: relative;
                top: 20px;
                z-index: 1;
                transition: opacity 0.3s ease, visibility 0.3s ease;
              "
              :style="{ opacity: showMenu ? 1 : 0, visibility: showMenu ? 'visible' : 'hidden' }"
            />
          </div>

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
                <v-icon right color="#003171">mdi-forklift</v-icon>
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
            style="position:relative; right:155px; top:0px; font-weight:700; padding-left:8px;
                   padding-right:8px;"
            @click="onClickTrans"
            ref="sendButton"
          >
            <v-icon left color="blue">mdi-account-arrow-right-outline</v-icon>
            <span>{{ transport_message }}</span>
          </v-btn>

          <div style="display: flex; flex-direction: column; align-items: center;">
            <span
              style="position:relative; top:30px; right:180px;"
              :style="{
                'fontSize': '14px',
                'display': 'inline-block',
                'min-width': '120px',
                'visibility': isCallForklift ? 'visible' : 'hidden',
              }"
            >
              堆高機送料中
            </span>

            <!--客製化搜尋-->
            <v-text-field
              v-model="search"

              prepend-inner-icon="mdi-magnify"
              variant="outlined"
              hide-details
              single-line
              style="position: relative; top: 47px; left: -170px; min-width: 150px;"
              density="compact"
            />

            <!-- 客製化barcode輸入 -->
            <v-text-field
              v-model="bar_code"
              :value="bar_code"
              ref="barcodeInput"
              @keyup.enter="handleBarCode"
              hide-details="auto"
              prepend-icon="mdi-barcode"
              style="min-width:200px; position: relative; top: 18px;"
              class="align-center"
              density="compact"

            ></v-text-field>
          </div>

          <!-- Bom 顯示對話視窗-->
          <v-dialog
            v-for="dlg in dialogs"
            :key="dlg.material_id"
            v-model="dlg.dialogVisible"
            max-width="980px"
            @keydown.esc="handleEscClose(dlg)"
            @click:outside="handleOutsideClick(dlg)"
            :eager="true"
            >

            <v-card
              :style="{
              maxHeight: boms.length > 5 ? '500px' : 'unset',
              overflowY: boms.length > 5 ? 'auto' : 'unset'}">
              <v-card-title
                class="text-h5 sticky-title"
                style="background-color: #1b4965; color: white;">
                備料資訊
                <span style="font-size:16px;">
                  訂單{{ dlg.order_num }}
                </span>
                &nbsp;&nbsp;
                <!-- 透過 v-model:isPaused 自動建立 :isPaused="..." 與 @update:isPaused="..." 綁定 -->
                <TimerDisplay
                  :key="dlg.material_id"
                  :ref="setTimerRef(dlg)"
                  v-model:isPaused="dlg.proc.isPaused"
                  :show="!shouldBlockTimer"
                  :autoStart="false"
                  @update:time="dlg.proc.onTick"
                />
                <v-btn
                  @click="dlg.proc.toggleTimer()"
                  :disabled="shouldBlockTimer"
                  :prepend-icon = "getIcon(dlg.proc.isPaused)"
                  :style="{ background: dlg.proc.isPaused ? '#4CAF50' : '#FFEB3B', color: dlg.proc.isPaused ? '#fff' : '#000' }"
                >
                  <v-icon start style="font-weight:700;">mdi-timer-outline</v-icon>
                  {{ dlg.proc.isPaused ? "開始" : "暫停" }}
                </v-btn>

                <v-fade-transition mode="out-in">
                  <v-btn
                    style="position: relative; right: -250px;"
                    color="success"
                    prepend-icon="mdi-check-circle-outline"

                    :disabled="isDialogConfirmDisabled || dlg.proc.isPaused"

                    text="確定"
                    class="text-none"
                    @click="onConfirm(dlg)"
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
                      <th class="text-left" style="width: 520px;">物料</th>
                      <th class="text-left">數量</th>
                      <th class="text-left" style="width: 120px;">日期</th>
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
                      <td style="width: 520px;">
                        <div>
                          <div>{{ bom_item.material_num }}</div>
                          <div style="color: #33cccc; font-weight: 600">{{ bom_item.mtl_comment }}</div>
                        </div>
                      </td>
                      <td>
                        <div :class="{'red-text': bom_item.date_alarm}">{{ bom_item.qty }}</div>
                      </td>
                      <td style="width: 120px;">
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
          <!--</div>-->

          <!-- 備料區檢料異常備註 -->
          <div class="pa-4 text-center">
            <v-dialog v-model="abnormalDialog" max-width="500">
              <!--取消最大高度限制，讓卡片內容可以顯示完整-->
              <!--取消自動捲軸，完全依內容高度決定是否超出-->
              <v-card :style="{ maxHeight: 'unset', overflowY: 'unset' }">
                <v-card-title class="text-h6 sticky-title text-center" style="background-color: #1b4965; color: white;">
                  備料區檢料異常備註
                </v-card-title>

                <v-card-text>
                  <!-- 若 Incoming0_Abnormal 為 true，顯示第1與第2行 -->
                  <template v-if="abnormalDialog_display">
                    <v-row style="margin-bottom: 4px;" dense justify="center">
                      <v-col cols="3" class="pa-0">訂單編號</v-col>
                      <v-col cols="9" class="pa-0"></v-col>
                    </v-row>
                    <v-row dense>
                      <v-col cols="5" class="pa-0">{{ abnormalDialog_order_num }}</v-col>
                      <v-col cols="7" class="pa-0">
                        <v-autocomplete
                          v-model="abnormalDialog_autocomplete_message"
                          v-model:search="abnormalDialog_search"
                          :items="itemsWithIcons"
                          item-title="text"
                          item-value="id"
                          density="compact"
                          @update:menu="open => { if (open) abnormalDialog_search = '' }"
                        >
                          <template #item="{ item, props }">
                            <div v-bind="props" class="d-flex align-center px-4 py-2">
                              <v-icon class="mr-2" size="18" color="blue">{{ item.raw.icon }}</v-icon>
                              <span style="color: #212121; font-weight: 600">{{ item.raw.text }}</span>
                            </div>
                          </template>
                        </v-autocomplete>
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
                  <div v-if="abnormalDialog_display">
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
                  </div>
                  <v-btn v-else
                    color="success"
                    prepend-icon="mdi-exit-to-app"
                    text="離開"
                    class="text-none"
                    @click="abnormalDialog = false"
                    variant="flat"
                  />
                </v-card-actions>
              </v-card>
            </v-dialog>
          </div>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '需求數量' (req_qty) 欄位表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="line-height: 1; margin: 0; padding: 0; text-align: center;">
        <div>{{ column.title }}</div>
        <div style="font-size:12px; margin-top: 5px;">(交貨日期)</div>
      </div>
    </template>

    <!-- 自訂 '訂單編號' 欄位 -->
    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: center;">
        <v-icon style="color: blue;" @click="editOrderNum(item)" small>
          mdi-pencil-outline
        </v-icon>

        <!--備料完成(缺料)-->
        <div style="color:red;  width:185px;" v-if="item.isTakeOk && item.isLackMaterial != 99">
          <span style="right:25px; position:relative;">{{ item.order_num }}&nbsp;&nbsp;</span>
          <span style="font-weight: 700; font-size: 16px; right:25px; position:relative;">缺料</span>
        </div>

        <!--備料完成-->
        <div style="color: blue; margin-right: 20px;" v-else-if="item.isTakeOk && item.isLackMaterial == 99">
          {{ item.order_num }}
        </div>

        <!--備料尚未完成-->
        <div style="margin-right: 20px;" v-else>
          {{ item.order_num }}
        </div>
      </div>
    </template>

    <!-- 自訂 '需求數量' (req_qty) 欄位 -->
    <template v-slot:item.req_qty="{ item }">
      <div>
        <div>{{ item.req_qty }}</div>
        <div style="color: #a6a6a6; font-size:12px;">{{ item.delivery_date }}</div>
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
    <!--v-if="!item.finished && item.hasStarted"-->
    <template v-slot:item.action="{ item }">
      <v-badge
        v-if="item.hasStarted"
        dot
        :color="item.startStatus ? 'green' : 'red'"
        location="top end"
        offset-x="6"
        offset-y="6"
      >
        <v-btn
          size="small"
          variant="tonal"
          style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"
          @click="toggleExpand(item)"
        >
          詳 情
          <v-icon color='green-darken-3' end>
            {{ 'mdi-note-search-outline' }}
          </v-icon>
        </v-btn>
      </v-badge>

      <v-btn
        v-else
        size="small"
        variant="tonal"
        style="font-size: 16px; font-weight: 400; font-family: 'cwTeXYen', sans-serif;"
        @click="toggleExpand(item)"
      >
        詳 情
        <v-icon color='green-darken-3' end>
          {{ 'mdi-note-search-outline' }}
        </v-icon>
      </v-btn>
    </template>

    <!-- 自訂 '應備數量'欄位的資料欄位 -->
    <template v-slot:item.total_delivery_qty="{ item }">
      <div style="display:flex; align-items:center;">
        <v-icon
          style="transition:opacity 0.3s ease, visibility 0.3s ease;  margin-left: -10px;"
          :style="{ opacity: (currentUser.perm == 1 || currentUser.perm == 2)  ? 1 : 0, visibility: (currentUser.perm == 1 || currentUser.perm == 2) ? 'visible' : 'hidden' }"
          @click="addAbnormalInMaterial(item)"
          size="16"
          class="mr-2"
          :color="item.Incoming0_Abnormal ? 'light-blue lighten-3':'red lighten-4'"
        >
          mdi-bell-plus
        </v-icon>
        <span style="margin-left: 15px;">
          {{ item.total_delivery_qty }}
        </span>
      </div>
    </template>

    <!-- 自訂 '備料數量' 輸入欄位 -->
    <template v-slot:item.delivery_qty="{ item }">
      <div style="position: relative; display: inline-block;">
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
import { ref, reactive, shallowRef, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount, nextTick } from 'vue';

// AutoAnimate, Vue.js的動畫
//import { autoAnimatePlugin } from '@formkit/auto-animate/vue'

import TimerDisplay from "./TimerDisplay.vue";
import { useProcessTimer } from "../mixins/useProcessTimer.js";

import ConfirmDialog from "./confirmDialog";

import eventBus from '../mixins/enentBus.js';

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';

import draggable from 'vuedraggable';
import { useRoute } from 'vue-router';

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { desserts2 }  from '../mixins/crud.js';
import { materials, boms, currentBoms, currentAGV, material_copy, fileCount }  from '../mixins/crud.js';
import { socket_server_ip }  from '../mixins/crud.js';

import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
const countExcelFiles = apiOperation('get', '/countExcelFiles');
const listMaterials = apiOperation('get', '/listMaterials');
const listUsers2 = apiOperation('get', '/listUsers2');

const getBoms = apiOperation('post', '/getBoms');
const getAGV = apiOperation('post', '/getAGV');
const updateBoms = apiOperation('post', '/updateBoms');
const updateMaterial = apiOperation('post', '/updateMaterial');
const updateProcessData = apiOperation('post', '/updateProcessData');
const updateAssembleMustReceiveQtyByMaterialID = apiOperation('post', '/updateAssembleMustReceiveQtyByMaterialID');
const copyMaterial = apiOperation('post', '/copyMaterial');
const copyMaterialAndBom = apiOperation('post', '/copyMaterialAndBom');
const updateMaterialRecord = apiOperation('post', '/updateMaterialRecord');
const createProcess = apiOperation('post', '/createProcess');
const updateAGV = apiOperation('post', '/updateAGV');
const modifyExcelFiles = apiOperation('post', '/modifyExcelFiles');
const updateModifyMaterialAndBoms = apiOperation('post', '/updateModifyMaterialAndBoms');
const updateAssmbleDataByMaterialID = apiOperation('post', '/updateAssmbleDataByMaterialID');
const updateProcessDataByMaterialID = apiOperation('post', '/updateProcessDataByMaterialID');
const updateBomXorReceive = apiOperation('post', '/updateBomXorReceive');
const updateSetting = apiOperation('post', '/updateSetting');
const removeMaterialsAndRelationTable = apiOperation('post', '/removeMaterialsAndRelationTable');
const updateMaterialFields = apiOperation('post', 'updateMaterialFields');

//=== component name ==
defineComponent({ name: 'MaterialListForAssem' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const show_dropdown = ref(false);
const page = ref(0);

// 方向：next / prev
const transitionName = ref('slide-next')

// ✅ 每一頁是一個陣列（每一行可用 <br> 或直接一行一個）
const pages = [
  [
    '<span class="title-style">備料</span>',
    //'1) 點擊備料工單的「詳情」按鍵',
    '1) 點擊備料工單的 ' +
    '<span class="fake-vbtn fake-vbtn--tonal">' +
    '詳 情 ' +
    '<span class="fake-vicon mdi mdi-note-search-outline"></span>' +
    '</span> 按鍵',


    '2) 點擊「開始」按鍵以開始備料及報工計時<br />&nbsp; &nbsp; 點擊「暫停」按鍵以暫停報工計時',
    '3) 點擊「確定」按鍵以完成該筆工單的備料',
    '4) 就已完成備料的 <span class="order-no">訂單編號</span> 輸入備料數量並按「enter」鍵或',
        '直接按「enter」鍵',
    '5) 就已完成備料的 <span class="order-no">訂單編號</span> 勾選「送料」',
    '6) 點擊「備料完成自動送出」按鍵'
  ],
  [
    //'工單維護',
    '<span class="title-style">工單維護</span>',
    '1) 工單刪除',
    '2) 匯入工單以更新工單內容',
    '3) 修改訂單日期或訂單數量',
  ],
    [
    '<span class="title-style">異常備註</span>',
    //'1) 工單刪除',
    '1) 點擊備料工單的' +
       '<span class="fake-vicon-bell mdi mdi-bell-plus"></span>',
    '2) 點選&nbsp;' +
        '<span class="fake-vauto">' +
        '<span class="fake-vauto__icon">▾</span>' +
        '</span>' +
        '&nbsp;並選擇異常備註項目',
    '3) 點擊「確定」按鍵以完成異常備註',
  ],
]

// 刪除對話框相關
const deleteTitle = ref('刪除工單');
const deleteMessage = ref('此操作將刪除相關資料(BOM/Assemble/Process)，確定？');
const confirmRef = ref(null);

const transport_message = ref('備料完成自動送出')
const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const panelX = ref(820);          // led顯示面板x位置, 值越大, 越往右
const panelY = ref(10);           // led顯示面板y位置, 值越大, 越往下
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

// 獲取元件引用
const draggablePanel = ref(null)
const sendButton = ref(null)

const screenSizeInInches = ref(null);

const toggle_exclusive = ref(2);              // 控制選擇的按鈕, 預設AGV:2, 人推車:1

const editDialogBtnDisable = ref(true);

//const isVisible = ref(true);                  // 設定初始狀態為顯示
//const isFlashLed = ref(false);                // 控制紅黃綠燈是否閃爍

//let intervalIdForLed = null;

const background = ref('#ffff00');
const isCallAGV = ref(false);                 // 確認是否已經呼叫了callAGV(), true:已經按鍵了, 不能重複按鍵
const showMenu = ref(false);                  // 控制員工選單顯示

const isCallForklift = ref(false);            // 確認是否已經呼叫了CallForklift(), true:已經按鍵了, 不能重複按鍵

const fromDateMenu = ref(false);              // 日期menu 打開/關閉

const selectedEmployee = ref(null);

const selectedId = ref(0);
const selectedOrderNum = ref(null);
const selectedReqQty = ref(null);
const selectedDate = ref(null);
const fromDateVal = ref('');

const bar_code = ref('');
const barcodeInput = ref(null);         // 外部條碼欄位

const deliveryQtyInput = ref(null)      // 對應 table 中備料數量欄位（稍後動態取得）

const placeholderTextForEmployee = ref('請選擇員工');
const placeholderTextForOrderNum = ref('請選擇工單');
const inputSelectEmployee = ref(null);
const inputSelectOrderNum = ref(null);

let intervalId = null;                        // 10分鐘, 倒數計時器, for exce file 偵測
let refreshTimerId = null;                    // 11秒, for refresh materials[]
const refreshTimerMs = ref(11 * 1000);        // 11秒
const lastRefreshed = ref(null);
const tableLoading = ref(false);

const route = useRoute();                     // Initialize router

const search = ref('');

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'id', width: '2px' },
  { title: '訂單編號', sortable: true, key: 'order_num' },
  { title: '物料編號', sortable: false, key: 'material_num'},
  { title: '需求數量', sortable: false, key: 'req_qty', width:110 },
  //{ title: '場域位置', sortable: false, key: 'location' },
  //{ title: '缺料註記', sortable: false, key: 'shortage_note' },
  { title: '說明', align: 'start', sortable: false, key: 'comment' },
  { title: '備料內容', sortable: false, key: 'action' },
  //{ title: '待送料總數', sortable: false, key: 'total_delivery_qty' },
  { title: '應備數量', sortable: false, key: 'total_delivery_qty', width:110 },
  //{ title: '實際送料數', sortable: false, key: 'delivery_qty' },
  { title: '備料數量', sortable: false, key: 'delivery_qty', width:110 },
];

const modify_bom_headers =[
  {title:'元件', sortable: false, key:'id'},
  {title:'編號', sortable: false, key:'material_num'},
  {title:'名稱', sortable: false, key:'mtl_comment'},
  {title:'數量', sortable: false, key:'qty'},
]
const modify_boms = ref([]);
const modify_file_name = ref('');

const selectedItems = ref([]);      // 儲存選擇的項目 (基於 id)
const selectedOrderNums = ref([]);  // 儲存選擇的項目 (基於 orderNum)
const inputValueForItems = ref([]); // 儲存輸入的值

const app_user_id = 'user_chumpower';
const clientAppName = 'MaterialListForAssem';
// 初始化Socket連接
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user_id, clientAppName);

const delivery_qty_alarm = ref('');

const isBlinking = ref(false);          // 控制按鍵閃爍
const order_num_on_agv_blink=ref('');

const currentUser = ref({});
const componentKey = ref(0);            // key 值用於強制重新渲染
const currentProcessId = ref(0);

const editDialog = ref(false);
const enableDialogBtn = ref(false);

const editingRowId = ref(null);

const showBackWarning = ref(true);

const current_cell = ref(null);

const currentStartTime = ref(null);       // 記錄開始時間
const currentEndTime = ref(null);         // 記錄開始時間

const agv1StartTime = ref(null);          // 等待agv計時開始
const agv1EndTime = ref(null);
const agv2StartTime = ref(null);          // 運行agv計時開始
const agv2EndTime = ref(null);

const forklift2StartTime = ref(null);     // 堆高機運行計時開始
const forklift2EndTime = ref(null);       // 堆高機運行計時結束

const dialog_totalActiveTime = ref('00:00:00')  // 最終顯示開啟總時間

//let dialog_elapsedActive = 0            // 已經累積的有效秒數（扣掉暫停）
let dialog_pauseStart = null              // 暫停開始時間（毫秒）


const dialog = ref(false);
const dialog_order_num = ref('');

const dialogs = ref([]);              // 儲存多個 dialog 狀態

const isConfirmed = ref(false);

const editedRecord = ref(null);       // 點擊詳情按鍵的目前紀錄

//const pagination = reactive({
//  itemsPerPage: 5,  // 預設值, rows/per page
//  page: 1           // 第1頁
//});

const pagination = reactive({
  itemsPerPage: -1, // 預設值, rows/per page
});


// 定義 facet 列表
//const allFacets = ref(['Facet 2', 'Facet 3', 'Facet 5']);
//const userFacets = ref(['Facet 1', 'Facet 4']);

const test_count = ref(0);

const abnormalDialogBtnDisable = ref(true);
const abnormalDialog = ref(false);                      // dialog顯示切換開關
const abnormalDialog_order_num = ref('');               // 訂單編號
const abnormalDialog_autocomplete_message = ref(null);  // v-autocomplete component所選擇的字串
const abnormalDialog_search = ref('')                   // 控制搜尋字
const abnormalDialog_message = ref('');                 // dialog顯示訊息
const abnormalDialog_display = ref(true);

const abnormalDialog_record = ref(null);                // 點擊鈴鐺icon的目前紀錄

const itemsWithIcons = [
  { id:1, text: '臨時領料', icon: 'mdi-clock-outline' },
  { id:2, text: '堆高機搬運物料', icon: 'mdi-forklift' },
  { id:3, text: '多筆備料', icon: 'mdi-clock-check'},
]

//=== watch ===
setupGetBomsWatcher();

// help menu每次打開都回到第 1 頁
watch(show_dropdown, (open) => {
  if (open) {
    page.value = 0
    transitionName.value = 'slide-next'
  }
})

watch(materials, (mItems) => {
    if (materials.value.length==0)
      selectedItems.value = [];
});

// 監視 selectedItems 的變化，並將其儲存到 localStorage
watch(selectedItems, (newItems) => {
    //console.log("watch(), newItems:", newItems)
    localStorage.setItem('selectedItems', JSON.stringify(newItems));
  },
  { deep: true }
);

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

watch(
  () => dialogs.value.map(d => d.dialogVisible),
  async (newVals, oldVals = []) => {
    for (let i = 0; i < newVals.length; i++) {
      const dlg = dialogs.value[i];
      if (!dlg) continue; // 安全防呆

      const isOpenNow = !!newVals[i];
      const wasOpen   = !!oldVals[i];

      // === dialog 剛打開 ===
      if (isOpenNow && !wasOpen) {
        console.log("🟢 Dialog opened");

        // 先確保前一次的資源已釋放（若有殘留）
        //try { dlg.proc?.dispose?.(); } catch(_) {}
        //dlg.proc = null;

        // 設 isOpen = true（寫回資料庫）
        try {

          await updateMaterial({
            id: dlg.material_id,
            record_name: "isOpen",
            record_data: true,
          });

          await updateMaterial({
            id: dlg.material_id,
            record_name: "isOpenEmpId",
            record_data: currentUser.value.empID,
          });

         /*
          await updateMaterialFields({
            id: dlg.material_id,
            fields: {
              isOpen: true,
              isOpenEmpId: currentUser.value.empID,
            }
          });
          */
        } catch (e) {
          console.warn("update isOpen(true) or isOpenEmpId 失敗:", e);
        }

        // 在 table 中把該筆標成 isOpen=true（響應式）
        const targetIndex = materials.value.findIndex(kk => kk.id === dlg.material_id);
        if (targetIndex !== -1) {
          materials.value[targetIndex] = {
            ...materials.value[targetIndex],
            isOpen: true,
            isOpenEmpId: currentUser.value.empID,
          };
        }

        // 等待 DOM 渲染完成，TimerDisplay 的 ref 才能使用
        await nextTick();

        try {
          // 確保每個 dlg 都有自己的 useProcessTimer 實例（⚠ 要傳函式！）
          if (!dlg.proc) {
            dlg.proc = useProcessTimer(() => dlg.timerRef);
          }

          // 每次打開都用新的 useProcessTimer，避免舊 interval 殘留
          //dlg.proc = useProcessTimer(() => dlg.timerRef);

          // 每次打開都向後端取最新狀態並還原
          await dlg.proc.startProcess(dlg.material_id, dlg.process_type, dlg.user_id);
        } catch (e) {
          console.error("startProcess 失敗：", e);
        }
      }

      // === dialog 剛關閉 ===
      if (!isOpenNow && wasOpen) {
        console.log("Dialog closed");

        const reason = dlg.closeReason;

        if (dlg.proc.for_vue3_has_started) {  //工單已開始
          try {

            await updateMaterial({
              id: dlg.material_id,
              record_name: "hasStarted",
              record_data: true,
            });

            await updateMaterial({
              id: dlg.material_id,
              record_name: "isOpenEmpId",
              record_data: currentUser.value.empID,
            });

            /*
            await updateMaterialFields({
              id: dlg.material_id,
              fields: {
                hasStarted: true,
                isOpenEmpId: currentUser.value.empID,
              }
            });
            */
          } catch (e) {
            console.warn("update hasStarted(true) or isOpenEmpId 失敗:", e);
          }

          const targetIndex2 = materials.value.findIndex(kk => kk.id === dlg.material_id);
          if (targetIndex2 !== -1) {
            materials.value[targetIndex2] = {
              ...materials.value[targetIndex2],
              hasStarted: true,
              isOpenEmpId: currentUser.value.empID,
            };
          }
        } else {
          try {
            await updateMaterial({
              id: dlg.material_id,
              record_name: "isOpenEmpId",
              record_data: "",
              //record_data: currentUser.value.empID,
            });
          } catch (e) {
            console.warn("update isOpenEmpId 失敗:", e);
          }

          const targetIndex2 = materials.value.findIndex(kk => kk.id === dlg.material_id);
          if (targetIndex2 !== -1) {
            materials.value[targetIndex2] = {
              ...materials.value[targetIndex2],
              isOpenEmpId: "",
              //isOpenEmpId: currentUser.value.empID,
            };
          }
        }

        if (dlg._closingOnce === undefined) dlg._closingOnce = false;

        if (dlg._closingOnce) return;     // 已在關閉流程中 → 直接略過
        dlg._closingOnce = true;

        try {
          if (reason === 'esc' || reason === 'outside') {
            if (!dlg?.proc) return;   // ← 這裡加，避免 undefined 錯誤

            console.log("$$ esc狀態 $$")
            // ✅ ESC / 外點：流程保持運行，不暫停
            /*
            if (dlg?.proc?.updateActiveNoPause) {
              await dlg.proc.updateActiveNoPause();
            } else {
              console.warn('ESC/Outside close → proc not ready, skip keep-running update');
            }
            */
            // 根據當下狀態決定要維持暫停還是不中斷繼續
            console.log("dlg?.proc?.isPaused:",dlg?.proc?.isPaused)
            if (dlg?.proc?.isPaused) {
              console.log("暫停的狀態")
              // ✅ 現在是暫停 → 維持暫停離開
              await dlg.proc.updateKeepPaused();
              //await dlg.proc.updateProcess();           // 存入最新 elapsed（暫停狀態）
              // 同步表格列 → 紅
              setRowState(dlg.material_id, {
                is_paused: true,
                startStatus: false,
              });
            } else {
              console.log("開始的狀態")
              // ✅ 現在在跑 → 不中斷離開
              await dlg.proc.updateActiveNoPause();
              //await dlg.proc.updateProcess();           // 存入最新 elapsed（運行中）
              // 同步表格列 → 綠
              setRowState(dlg.material_id, {
                is_paused: false,
                startStatus: true,
                has_started: true,
                isOpenEmpId: String(currentUser.value.empID || ''),
              });
            }

            dlg.dialogVisible = false;

          } else {
            console.log("$$ 確定按鍵狀態 $$")

            // 🛑 一般關閉：暫停 + 回寫
            dlg?.timerRef?.pause?.(); // 視覺上暫停
            if (dlg?.proc?.isPaused) dlg.proc.isPaused.value = true;
            // 語法1, 容易了解
            //if (dlg.proc.updateProcess) await dlg.proc.updateProcess();   // 把目前 elapsed + is_paused 回後端
            //if (dlg.proc.closeProcess)  await dlg.proc.closeProcess();
            // 語法2, 簡潔
            // 用「可選鏈結呼叫」直接在存在時才呼叫；不存在就得到 undefined，await undefined 會立即通過，不丟錯。
            await dlg.proc.updateProcess?.();
            console.log("closeProcess(), qty:", editedRecord.value.delivery_qty)
            await dlg.proc.closeProcess?.();

            console.log("dialog , i:", i)
            dialogs.value.splice(i, 1);
          }
        } catch (e) {
          console.error("close-handling 失敗：", e);
        } finally {
          // ✅ 不論哪種關閉，都釋放本地 interval/輪詢，避免背景偷跑
          //try { dlg.proc?.dispose?.(); } catch (_) {}
          //dlg.proc = null;             // 下次打開會重建

          // 重置關閉原因，避免下次誤判
          dlg.closeReason = null;
          // 這次流程結束，讓下一次可以再執行
          dlg._closingOnce = false;
        }

        try {
          await updateMaterial({
            id: dlg.material_id,
            record_name: "isOpen",
            record_data: false,
          });
        } catch (e) {
          console.warn("update isOpen(false) 失敗:", e);
        }

        const targetIndex2 = materials.value.findIndex(kk => kk.id === dlg.material_id);
        if (targetIndex2 !== -1) {
          materials.value[targetIndex2] = {
            ...materials.value[targetIndex2],
            isOpen: false,
          };
        }

        // ✅ 從陣列移除該 dialog（放在 nextTick 後移除，避免索引變動干擾當前迭代）
        //const idxToRemove = i;
        //await nextTick();
        //dialogs.value.splice(idxToRemove, 1);

        // 清空條碼（只對當前 dlg）
        bar_code.value = '';

        // 聚焦欄位
        await nextTick();
        if (isConfirmed.value && editedRecord.value?.id != null) {
          document.getElementById(`receiveQtyID-${editedRecord.value.id}`)?.focus();
        } else {
          barcodeInput.value?.focus();
        }
        isConfirmed.value = false; // 重置狀態
      }
    }
  },
  { deep: true }
);

//=== computed ===
const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
const formatWeekday = computed(() => {
  return (day) => {
    console.log('day:', day); // 調試輸出
    return weekdays[day];
  };
});

const formattedDesserts = computed(() =>
desserts2.value.map(emp => ({
  ...emp,
  display: `${emp.emp_id} ${emp.emp_name}`,
}))
);

const c_isBlinking = computed(() => selectedItems.value.length === 0);

const containerStyle = computed(() => ( {bottom: props.showFooter ? '60px' : '0'} ));

const routeName = computed(() => route.name);

// 顯示格式化日期
const formattedDate = computed(() => {
  return fromDateVal.value ? fromDateVal.value.toISOString().split('T')[0] : ''; // 自動格式化
});

//const enableDialogBtnByReceive = computed(() => {
//  // 如果 boms 陣列是空的，或所有 receive 都是 false，就 disable 按鈕
//  return boms.length === 0 || boms.every(b => b.receive === false);
//});
const isDialogConfirmDisabled = computed(() => {
  // 如果 enableDialogBtn為true, 或boms 陣列是空的，或所有 receive 都是 false，就 disable 按鈕
  //return enableDialogBtn.value || boms.value.length === 0 || boms.value.every(b => b.receive === false || b.receive === null);
  return enableDialogBtn.value || boms.value.length === 0;
});

const isAllReceiveIsFalse = computed(() => {
  // 如果 enableDialogBtn為true, 或boms 陣列是空的，或所有 receive 都是 false，就 disable 按鈕
  //return boms.value.length === 0 || boms.value.every(b => b.receive === false || b.receive === null);
  return boms.value.length === 0;
});

const shouldBlockTimer = computed(() => {
  const list = boms.value || [];

  // 沒有任何 BOM → 一定不顯示計時、不讓按開始
  if (list.length === 0) return true;

  // 有 BOM，但每一筆都是 receive = false / null → 視為「全部缺料」
  const allLack = list.every(
    (b) => b.receive === false || b.receive === null
  );

  return allLack;
});

/*
const isStarted = computed(() => {
  return (item) => {
    const dlg = dialogs.value.find(
      d =>
        d.material_id === item.id &&
        d.user_id === currentUser.value.empID
    );
    // 如果找到 dlg，就回傳它的 for_vue3_pause_or_start_status (轉成 Boolean)
    console.log("dlg?.proc?.for_vue3_pause_or_start_status", dlg?.proc?.for_vue3_pause_or_start_status)
    return Boolean(dlg?.proc?.for_vue3_pause_or_start_status);
  };
});

const ishasWorked = computed(() => {
  return (item) => {
    const dlg = dialogs.value.find(
      d =>
        d.material_id === item.id &&
        d.user_id === currentUser.value.empID
    );
    // 如果找到 dlg，就回傳它的 for_vue3_pause_or_start_status (轉成 Boolean)
    return Boolean(dlg?.proc?.for_vue3_has_started);
  };
});
*/

//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  const dpiEstimate = 96 * dpi;
  //const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);

  if (screenSizeInInches.value != null) {
    //panelX.value = screenSizeInInches.value > 20 ? 1480 : 825;
    panelX.value = window.innerWidth - 195 + 114 + 5;
    //calculatePanelPosition();
    //panelY.value = screenSizeInInches.value > 20 ? 11 : 11;
    panelY.value = 11;
  }
  console.log("window.innerWidth, panelX, panelY:", window.innerWidth, panelX.value, panelY.value)
  //+++

  //calculatePanelPosition();

  // 如果窗口大小變化需要重新計算
  //window.addEventListener('resize', calculatePanelPosition);

  // 阻止直接後退，但保留 Vue Router 的 state
  window.history.replaceState(window.history.state, '', document.URL);
  window.addEventListener('popstate', handlePopState)

  console.log("current routeName:", routeName.value);

  //user define
  let userRaw = sessionStorage.getItem('auth_user');
  if (!userRaw) {
    // 只在第一次開分頁時，從 localStorage 複製一份
    userRaw = localStorage.getItem('loginedUser');
    if (userRaw) {
      sessionStorage.setItem('auth_user', userRaw);
    }
  }
  currentUser.value = userRaw ? JSON.parse(userRaw) : null;

  if (currentUser.value) {
    currentUser.value.setting_items_per_page = pagination.itemsPerPage;
    currentUser.value.setting_lastRoutingName = routeName.value;

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }
  console.log("currentUser:", currentUser.value);
  //

  // 取得每個 v-text-field 的唯一 ID
  //2025-02-13 mark the following function
  //inputIDs.value.forEach((item) => {
  //  const myIdField = document.getElementById(`receiveQtyID-${item.id}`);
  //  myIdField && (myIdField.addEventListener('keydown', handleKeyDown));
  //});
  //
  // 每10分鐘讀取excel檔案是否存在? 顯示檔案數目
  //fileCount.value = countExcelFiles();
  await countExcelFiles();
  console.log("fileCount:", fileCount.value);

  intervalId = setInterval(countExcelFiles, 10 * 60 * 1000);  // 每 10 分鐘調用一次 API, 10分鐘=600000毫秒

  // 設定紅黃綠燈閃爍週期
  //intervalIdForLed = setInterval(() => {
  //  isVisible.value = !isVisible.value;  // 每秒切換顯示狀態
  //}, 500);

  isBlinking.value = selectedItems.value.length == 0 ? true:false;

  // 從 localStorage 中恢復 selectedItems
  let savedItems = localStorage.getItem('selectedItems');
  if (savedItems) {
    selectedItems.value = JSON.parse(savedItems);
  }

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }

  //處理socket連線
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
    //socket.value.emit('station1_loading');
    socket.value.on('station1_error', async () => {
      console.log("receive station1_error socket...");
      activeColor.value = 'green'  // 預設亮綠燈, 區域閒置
    });

    socket.value.on('station1_loading_ready', async(data) => {
      //console.log("receive station1_loading_ready socket...");

      //activeColor.value='yellow';  // 物料進站
    });

    socket.value.on('station1_agv_start', async () => {
      console.log('AGV 運行任務開始，press Start按鍵, 收到 station1_agv_start 訊息');

      const selectedIds = Array.isArray(selectedItems.value) ? [...selectedItems.value] : [];
      if (selectedIds.length === 0) {
        console.warn('station1_agv_start: 沒有選取任何項目');
        return;
      }

      activeColor.value='yellow';  // 物料進站

      for (const id of selectedIds) {
        try {
          console.log('selected item:', id);
          await updateMaterial({
            id,
            record_name: 'show3_ok', // 看板要顯示的欄位名稱
            record_data: 16,         // 16: AGV start
          });
        } catch (err) {
          console.warn('updateMaterial 失敗, id =', id, err);
        }
      }
    });

    socket.value.on('station1_agv_begin', async () => {
      console.log('AGV暫停, 收到 station1_agv_begin 訊息');

      // 記錄 agv 在站與站之間運行開始時間（確保是 Date 物件）
      agv2StartTime.value = new Date();
      console.log('AGV Start time:', agv2StartTime.value);

      // 取出乾淨的 id 陣列
      const selectedIds = Array.isArray(selectedItems.value) ? [...selectedItems.value] : [];
      if (selectedIds.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      let successCount = 0;

      for (const id of selectedIds) {
        try {
          console.log('selected item:', id);
          await updateMaterial({
            id,
            record_name: 'show3_ok', // 看板欄位名稱
            record_data: 2,          // 2: agv移動至組裝區中
          });
          successCount++;
          console.log(`資料更新成功，id: ${id}`);
        } catch (error) {
          console.error(`資料更新失敗，id: ${id}`, error);
        }
      }

      // 若至少有一筆更新成功，再更新 AGV 狀態與 UI
      if (successCount > 0) {
        await updateAGV({
          id: 1,
          status: 2,  // 行走中
          station: 2, // 行走至組裝區
        });

        background.value = '#10e810';
        activeColor.value = 'SeaGreen'; // 物料出站
      } else {
        console.warn('沒有任何資料成功更新，略過 AGV 狀態更新與 UI 變色');
      }
      /*
      let payload = {};
      // 記錄agv在站與站之間運行開始時間
      agv2StartTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV Start time:", agv2StartTime.value);

      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        payload = {
          id: item,
          record_name: 'show3_ok',    //看板要顯示的欄位名稱
          record_data: 2              //看板要顯示的欄位內容, 2:agv移動至組裝區中
        };
        try {
          await updateMaterial(payload);
          console.log(`資料更新成功，id: ${item}`);
        } catch (error) {
          console.error(`資料更新失敗，id: ${item}`, error);
        }
      });

      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 2,      // 行走中
        station:  2,    // 行走至組裝區
      };
      await updateAGV(payload);

      background.value='#10e810'
      activeColor.value='SeaGreen';   // 物料出站
      */
    })

    //以下待確認

    socket.value.on('station2_agv_end', async (data) => {
      console.log('AGV 運行結束，已到達組裝區, 收到 station2_agv_end 訊息, material table id:', data);

      // 記錄agv在站與站之間運行結束時間
      agv2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("AGV end time:", agv2EndTime.value);

      let payload = {};
      let targetItem = {};
      console.log("selectedItems.value:", selectedItems.value);

      const selectedIds = Array.isArray(selectedItems.value)
        ? [...selectedItems.value]
        : [];

      if (selectedIds.length === 0) {
        console.warn('station2_agv_end：沒有選取任何項目');
        return;
      }

      // 步驟1：把 material/assemble 的顯示狀態先統一到「組裝站/未組裝/等待組裝中」
      for (const id of selectedIds) {
        const m = materials.value.find(x => x.id == id);
        if (!m) {
          console.warn('station2_agv_end：找不到 material，id=', id);
          continue;
        }

        await updateMaterialRecord({
          id: m.id,
          show1_ok: 2,      // 組裝站
          show2_ok: 3,      // 未組裝
          show3_ok: 3,      // 等待組裝中
          whichStation: 2,  // 目標途程: 組裝站
        });

        // 同步更新 Assemble（你的 API 名稱保留）
        await updateAssmbleDataByMaterialID({
          material_id: m.id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 2,
          record_name2: 'show2_ok',
          record_data2: 3,
          record_name3: 'show3_ok',
          record_data3: 3,
        });
      }
      /*
      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        targetItem = materials.value.find(m => m.id == item);
        console.log("targetItem:", targetItem)

        payload = {
          id: targetItem.id,
          show1_ok: 2,      //組裝站
          show2_ok: 3,      //未組裝
          show3_ok: 3,      //等待組裝中
          whichStation: 2,  //目標途程:組裝站
        };
        await updateMaterialRecord(payload);

        payload = {
          material_id: targetItem.id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 2,
          record_name2: 'show2_ok',
          record_data2: 3,
          record_name3: 'show3_ok',
          record_data3: 3,
        };
        await updateAssmbleDataByMaterialID(payload)
      });
      */
      console.log('agv_end 處理步驟1...');

      let agv2PeriodTime = calculatePeriodTime(agv2StartTime.value, agv2EndTime.value);  // 計算時間間隔
      let formattedStartTime = formatDateTime(agv2StartTime.value);
      let formattedEndTime = formatDateTime(agv2EndTime.value);
      console.log("AGV 運行 Start Time:", formattedStartTime);
      console.log("AGV 運行 End Time:", formattedEndTime);
      console.log("AGV 運行 Period time:", agv2PeriodTime);

      // 步驟2：逐筆建立 Process、寫回數量與狀態
      for (const id of selectedIds) {
        const m = materials.value.find(x => x.id == id);
        if (!m) continue;

        // 2-1. 建立 Process（AGV 傳送至組裝區）
        await createProcess({
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv2PeriodTime,
          user_id: 'AGV1-2',
          order_num: m.order_num,
          process_type: 2, // agv到組裝區
          id: m.id,
        });

        // 2-2. 記錄該筆 AGV 送料數量
        await updateMaterial({
          id: m.id,
          record_name: 'delivery_qty',
          record_data: m.delivery_qty, // 以當下畫面資料為準
        });

        // 2-2-a. 記錄應領取數量（用 total_delivery_qty）
        await updateAssembleMustReceiveQtyByMaterialID({
          material_id: m.id,
          record_name: 'must_receive_qty',
          record_data: m.total_delivery_qty,
        });

        // 2-3. 顯示該筆為「可顯示」
        await updateMaterial({
          id: m.id,
          record_name: 'isShow',
          record_data: true,
        });

        // 2-4. 判斷是否「多批次運送」
        const isMultiBatch = Number(m.delivery_qty) !== Number(m.total_delivery_qty);

        if (isMultiBatch) {
          const remain = Number(m.total_delivery_qty) - Number(m.delivery_qty);
          if (remain > 0) {
            // 產生一筆「尚未運送」的複製工單
            await copyMaterial({
              copy_id: m.id,                     // 工單 table id
              delivery_qty: m.delivery_qty,      // 本批備料數量
              total_delivery_qty: remain,        // 剩餘應備
              show2_ok: 2,                       // 備料完成
              shortage_note: '',
            });
            test_count.value = (test_count.value || 0) + 1;
            console.log('步驟2-4… 新增剩餘批次，count =', test_count.value);
          }
        } else {
          // 單批次 → 直接進「等待組裝作業」
          await updateMaterial({
            id: m.id,
            record_name: 'show2_ok',
            record_data: 3,
          });

          // 若是「合併工單」，後續 BOM/收料合併並通知前端刷新
          if (m.is_copied)  {
            await updateBomXorReceive({ copied_material_id: m.id });
            await delay(1000);
            eventBus.emit('merge_work_orders');
            console.log('合併工單顯示通知已發出');
          }
        }
      }
      console.log('agv_end 處理步驟2...');
      /*
      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        let myMaterial = materials.value.find(m => m.id == item);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv2PeriodTime,
          user_id: 'AGV1-2',                        //在備料區('AGV1'), 呼叫AGV的運行時間('-2'), 即簡稱AGV1-2
          order_num: myMaterial.order_num,
          process_type: 2,                          //agv到組裝區
          id: myMaterial.id,
        };
        await createProcess(payload);
        console.log('步驟2-1...');

        //紀錄該筆的agv送料數量
        payload = {
          id: myMaterial.id,
          record_name: 'delivery_qty',
          record_data: myMaterial.delivery_qty,
        };
        await updateMaterial(payload);
        console.log('步驟2-2...');

        //紀錄該筆的應領取數量, 2025-06-16 add, 改順序
        payload = {
          material_id: myMaterial.id,
          record_name: 'must_receive_qty',
          //record_data: myMaterial.delivery_qty,
          record_data: myMaterial.total_delivery_qty,
        };
        await updateAssembleMustReceiveQtyByMaterialID(payload);
        console.log('步驟2-2-a...');

        //紀錄該筆的agv送料狀態
        //if (Number(myMaterial.delivery_qty) !=0 && Number(myMaterial.total_delivery_qty) !=0) {
        payload = {
          id: myMaterial.id,
          record_name: 'isShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-3...');

        if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
          console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

          let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;

          payload = {
            copy_id: myMaterial.id,                 //工單table id
            delivery_qty: myMaterial.delivery_qty,  //備料數量
            total_delivery_qty: tempDelivery,       //應備數量
            show2_ok: 2,                            //備料完成
            shortage_note: '',
          }
          await copyMaterial(payload);
          test_count.value += 1;
          console.log('步驟2-4...', test_count.value);
        } else {
          //if (myMaterial.isLackMaterial == 0) {
            payload = {
              //order_num: my_material_orderNum,
              id: myMaterial.id,
              record_name: 'show2_ok',
              record_data: 3                  // 等待組裝作業
            };
            await updateMaterial(payload);
          //}
          //console.log("myMaterial.is_copied, id:", myMaterial.is_copied, myMaterial.id)
          if (myMaterial.is_copied)  {
            payload = {
              copied_material_id: myMaterial.id,
            };
            await updateBomXorReceive(payload);

            // 延遲 1 秒
            await delay(1000);

            // 通知合併工單顯示
            eventBus.emit('merge_work_orders');
            console.log('合併工單顯示通知已發出')
          }


        } // end else loop
      });
      */
      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 0,      // ready
        station:  2,    // 已在組裝區
      };
      await updateAGV(payload);
      console.log('agv_end 處理步驟3...');

      activeColor.value='DarkOrange';   //物料送達組裝區

      // 插入延遲 3 秒
      //await delay(3000);

      //isFlashLed.value = false;     //黃綠燈熄滅

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }
      //待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    }); // end socket loop

    socket.value.on('station2_trans_end', async (data) => {
      console.log("收到 station2_trans_end訊息...", data);

      // 送出事件
      socket.value.emit('station2_trans_over');
      console.log('送出 station2_trans_over 訊息...');

      // 記錄 forklift 在站與站之間運行結束時間
      forklift2EndTime.value = new Date();
      console.log('forklift end time:', forklift2EndTime.value);

      // 取出乾淨的 id 陣列
      const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIds.length === 0) {
        console.warn('trans_end：沒有選取任何項目');
        return;
      }

      // === 步驟1：更新 material/assemble 顯示狀態 + 記錄搬運方式 ===
      for (const id of selectedIds) {
        const m = materials.value.find(x => x.id == id);
        if (!m) {
          console.warn('trans_end：找不到 material，id=', id);
          continue;
        }

        // 組裝站 / 未組裝 / 等待組裝中 / 目標途程
        await updateMaterialRecord({
          id: m.id,
          show1_ok: 2,     // 組裝站
          show2_ok: 3,     // 未組裝
          show3_ok: 3,     // 等待組裝中
          whichStation: 2, // 目標途程：組裝站
        });

        // 同步更新 assemble
        await updateAssmbleDataByMaterialID({
          material_id: m.id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 2,
          record_name2: 'show2_ok',
          record_data2: 3,
          record_name3: 'show3_ok',
          record_data3: 3,
        });

        // 紀錄搬運方式：手動（堆高機）
        await updateMaterial({
          id: m.id,
          record_name: 'move_by_automatic_or_manual',
          record_data: false,
        });
      }
      console.log('trans_end 處理步驟1...');

      // === 安全計算時間（確保 end >= start） ===
      const startDate = new Date(forklift2StartTime.value || Date.now());
      const endDate   = new Date(forklift2EndTime.value   || Date.now());
      const startMs   = +startDate;
      const endMs     = Math.max(+endDate, startMs);

      const formattedStartTime = formatDateTime(new Date(startMs));
      const formattedEndTime   = formatDateTime(new Date(endMs));
      const PeriodTime         = calculatePeriodTime(new Date(startMs), new Date(endMs));

      console.log('forklift 運行 Start Time:', formattedStartTime);
      console.log('forklift 運行 End   Time:', formattedEndTime);
      console.log('forklift 運行 Period    :', PeriodTime);

      // === 步驟2：建立 Process、寫回數量與狀態、處理多批次 ===
      for (const id of selectedIds) {
        const m = materials.value.find(x => x.id == id);
        if (!m) continue;

        // 2-1. 建立「堆高機到組裝區」流程
        await createProcess({
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: PeriodTime,
          user_id: currentUser.value?.empID ?? '', // 操作人
          order_num: m.order_num,
          process_type: 5, // forklift到組裝區
          id: m.id,
        });
        console.log('步驟2-1...');

        // 2-1b.（保留你原本的備料報工）*若 editedRecord 存在才送*
        if (editedRecord?.value?.id) {
          await createProcess({
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: PeriodTime,
            user_id: currentUser.value?.empID ?? '',
            process_type: 1, // 備料
            id: editedRecord.value.id,
            process_work_time_qty: editedRecord.value.req_qty, // 報工數量
          });
        }

        // 2-2. 記錄送料數量
        await updateMaterial({
          id: m.id,
          record_name: 'delivery_qty',
          record_data: m.delivery_qty,
        });
        console.log('步驟2-2...');

        // 2-2-a. 記錄應領取數量（用 total_delivery_qty）
        await updateAssembleMustReceiveQtyByMaterialID({
          material_id: m.id,
          record_name: 'must_receive_qty',
          record_data: m.total_delivery_qty,
        });
        console.log('步驟2-2-a...');

        // 2-3. 顯示此筆為可顯示
        await updateMaterial({
          id: m.id,
          record_name: 'isShow',
          record_data: true,
        });
        console.log('步驟2-3...');

        // 2-4. 判斷是否多批次運送
        const isMultiBatch = Number(m.delivery_qty) !== Number(m.total_delivery_qty);

        if (isMultiBatch) {
          console.log('1張工單多批次運送, 新增未運送數量(相同工單)');
          const remain = Number(m.total_delivery_qty) - Number(m.delivery_qty);
          if (remain > 0) {
            await copyMaterial({
              copy_id: m.id,                   // 工單 table id
              delivery_qty: m.delivery_qty,    // 本批備料
              total_delivery_qty: remain,      // 剩餘應備
              show2_ok: 2,                     // 備料完成
              shortage_note: '',
            });
            test_count.value = (test_count.value || 0) + 1;
            console.log('步驟2-4...', test_count.value);
          }
        } else {
          // 單批次 → 直接進「等待組裝作業」
          await updateMaterial({
            id: m.id,
            record_name: 'show2_ok',
            record_data: 3,
          });

          if (m.is_copied) {
            await updateBomXorReceive({ copied_material_id: m.id });
            await delay(1000);
            eventBus.emit('merge_work_orders');
            console.log('合併工單顯示通知已發出');
          }
        }
      }

      /*
      socket.value.emit('station2_trans_over');
      console.log("送出 station2_trans_over訊息...");

      // 記錄forklift在站與站之間運行結束時間
      forklift2EndTime.value = new Date();  // 使用 Date 來記錄當時時間
      console.log("forklift end time:", forklift2EndTime.value);

      let payload = {};
      let targetItem = {};

      selectedItems.value.forEach(async (item) => {
        targetItem = materials.value.find(m => m.id == item);
        console.log("targetItem:", targetItem)

        payload = {
          id: targetItem.id,
          show1_ok: 2,      //組裝站
          show2_ok: 3,      //未組裝
          show3_ok: 3,      //等待組裝中
          whichStation: 2,  //目標途程:組裝站
        };
        await updateMaterialRecord(payload);

        payload = {
          material_id: targetItem.id,
          delivery_qty: 0,
          record_name1: 'show1_ok',
          record_data1: 2,
          record_name2: 'show2_ok',
          record_data2: 3,
          record_name3: 'show3_ok',
          record_data3: 3,
        };
        await updateAssmbleDataByMaterialID(payload)

        payload = {
          id: targetItem.id,
          record_name: 'move_by_automatic_or_manual',
          record_data: false
        };
        await updateMaterial(payload);
      });
      // end forEach loop
      console.log('trans_end 處理步驟1...');

      let formattedStartTime = formatDateTime(forklift2StartTime.value);
      let formattedEndTime = formatDateTime(forklift2EndTime.value);
      let PeriodTime = calculatePeriodTime(forklift2StartTime.value, forklift2EndTime.value);  // 計算時間間隔
      console.log("forklift 運行 Start Time:", formattedStartTime);
      console.log("forklift 運行 End Time:", formattedEndTime);
      console.log("forklift 運行 Period time:", PeriodTime);

      console.log('trans_end 處理步驟2...');
      selectedItems.value.forEach(async (item) => {
        console.log('selectedItems, item:', item);

        let myMaterial = materials.value.find(m => m.id == item);
        console.log('selectedItems, item:', myMaterial);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: PeriodTime,
          user_id: currentUser.value.empID,
          order_num: myMaterial.order_num,
          process_type: 5,                          //forklift到組裝區
          id: myMaterial.id,
        };
        await createProcess(payload);
        console.log('步驟2-1...');

        let processPayload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: PeriodTime,
          user_id: currentUser.value.empID,
          //order_num: my_material_orderNum,
          process_type: 1,                  // 備料
          id: editedRecord.value.id,
          process_work_time_qty: editedRecord.value.req_qty, // 報工數量
        };
        await createProcess(processPayload);

        //紀錄該筆的forklift送料數量
        payload = {
          id: myMaterial.id,
          record_name: 'delivery_qty',
          record_data: myMaterial.delivery_qty
        };
        await updateMaterial(payload);
        console.log('步驟2-2...');

        //紀錄該筆的應領取數量
        payload = {
          material_id: myMaterial.id,
          record_name: 'must_receive_qty',
          record_data: myMaterial.total_delivery_qty,
        };
        await updateAssembleMustReceiveQtyByMaterialID(payload);
        console.log('步驟2-2-a...');

        //紀錄該筆的forklift送料狀態
        payload = {
          id: myMaterial.id,
          record_name: 'isShow',
          record_data: true
        };
        await updateMaterial(payload);
        console.log('步驟2-3...');

        if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
          console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

          let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;

          payload = {
            copy_id: myMaterial.id,                 //工單table id
            delivery_qty: myMaterial.delivery_qty,  //備料數量
            total_delivery_qty: tempDelivery,       //應備數量
            show2_ok: 2,                            //備料完成
            shortage_note: '',
          }
          await copyMaterial(payload);
          test_count.value += 1;
          console.log('步驟2-4...', test_count.value);
        } else {
          payload = {
            id: myMaterial.id,
            record_name: 'show2_ok',
            record_data: 3                  // 等待組裝作業
          };
          await updateMaterial(payload);

          if (myMaterial.is_copied)  {
            payload = {
              copied_material_id: myMaterial.id,
            };
            await updateBomXorReceive(payload);

            // 延遲 1 秒
            await delay(1000);

            // 通知合併工單顯示
            eventBus.emit('merge_work_orders');
            console.log('合併工單顯示通知已發出')
          }

        } // end else loop
      });
      */

      // 插入延遲 3 秒
      await delay(3000);

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }
      //待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
    })

    socket.value.on('station1_agv_ready', async () => {
      console.log('AGV 已在備料區裝卸站, 收到 station1_agv_ready 訊息...');

      order_num_on_agv_blink.value = '';

      // 記錄等待 agv 到站結束時間（確保是 Date 物件）
      agv1EndTime.value = new Date();
      console.log('AGV End time:', agv1EndTime.value);

      // 安全計算時間：確保 end >= start
      const startDate = new Date(agv1StartTime.value || Date.now());
      const endDate   = new Date(agv1EndTime.value   || Date.now());
      const startMs   = +startDate;
      const endMs     = Math.max(+endDate, startMs);

      const formattedStartTime = formatDateTime(new Date(startMs));
      const formattedEndTime   = formatDateTime(new Date(endMs));
      const agv1PeriodTime     = calculatePeriodTime(new Date(startMs), new Date(endMs));

      console.log('AGV 等待 Start Time:', formattedStartTime);
      console.log('AGV 等待 End   Time:', formattedEndTime);
      console.log('AGV 等待 Period    :', agv1PeriodTime);

      // 取出乾淨的 id 陣列
      const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
      if (selectedIds.length === 0) {
        console.warn('沒有選取任何項目');
        return;
      }

      // 逐筆寫入 Process：AGV1-1（備料區等待）
      let successCount = 0;
      for (const id of selectedIds) {
        const myMaterial = materials.value.find(kk => kk.id == id);
        if (!myMaterial) {
          console.warn('找不到 material，id =', id);
          continue;
        }

        try {
          await createProcess({
            begin_time: formattedStartTime,
            end_time: formattedEndTime,
            periodTime: agv1PeriodTime,
            user_id: 'AGV1-1',          // 備料區(AGV1)等待時間(-1)
            order_num: myMaterial.order_num,
            process_type: 19,            // 在備料區等待 AGV
            id: myMaterial.id,
          });
          successCount++;
        } catch (err) {
          console.error('createProcess 失敗, id =', id, err);
        }
      }

      // 成功至少一筆再更新 AGV 狀態與 UI
      if (successCount > 0) {
        await updateAGV({
          id: 1,
          status: 1,  // 等待/忙碌
          station: 1, // 備料區
        });

        // UI 狀態
        background.value = '#ffff00';
        //isFlashLed.value = true;
        activeColor.value = 'blue'; // 機器人進站
      } else {
        console.warn('沒有任何流程寫入成功，略過 AGV 狀態更新與 UI 變更');
      }


      /*
      order_num_on_agv_blink.value='';

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
        let myMaterial = materials.value.find(kk => kk.id == item);

        payload = {
          begin_time: formattedStartTime,
          end_time: formattedEndTime,
          periodTime: agv1PeriodTime,
          user_id: 'AGV1-1',                          //在備料區('AGV1'), 呼叫AGV的等待時間('-1'), 即簡稱AGV1-1
          order_num: myMaterial.order_num,
          process_type: 19,                           //在備料區
          id: item,
        };
        await createProcess(payload);
      });
      // 記錄AGV狀態資料
      payload = {
        id: 1,
        status: 1,
        station:  1,
      };
      await updateAGV(payload);

      //startFlashing();
      background.value='#ffff00'
      isFlashLed.value = true;
      activeColor.value='blue';   // 機器人進站
      */
    });

    socket.value.on('kuka_server_not_ready', async (data) => {
      let temp_msg= data?.message || 'kuka端伺服器未準備好';
      console.warn(temp_msg);
      showSnackbar(temp_msg, 'red accent-2');
    });

    //socket.value.on('agv_ack', async () => {
    //  console.log('收到 agv_ack 回應');
    //});

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
          //setAuthenticated(isAuthenticated);
          //localStorage.setItem('Authenticated', isAuthenticated);
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

  window.removeEventListener('popstate', handlePopState);
  clearInterval(intervalId);
  //clearInterval(intervalIdForLed);
  //dialog_stopTimer();

  //stopFlashing();
});

//=== created ===
onBeforeMount(() => {
  console.log("Employer, created()...")

  pagination.itemsPerPage = currentUser.value.setting_items_per_page;

  initAxios();
  initialize();

  startAutoRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
});

/*
onBeforeUnmount(() => {
  stopAutoRefresh();
  document.removeEventListener('visibilitychange', handleVisibilityChange);

  // 元件銷毀前，把所有尚存的 proc 都釋放一次
  dialogs.value.forEach(d => {
    try { d.proc?.dispose?.(); } catch(_) {}
    d.proc = null;
  });
})
*/

onBeforeUnmount(() => {
  // 1) 停止自動更新（若內部會 clearInterval/timeout）
  try {
    stopAutoRefresh?.();
  } catch (e) {
    console.warn('stopAutoRefresh failed:', e);
  }

  // 2) DOM 事件
  document.removeEventListener('visibilitychange', handleVisibilityChange);

  /*
  // 3) 取消 watchers（請在建立 watch 時把 unwatch 收進這裡）
  try {
    stopWatchFns?.forEach(fn => { try { fn?.(); } catch(_) {} });
    if (Array.isArray(stopWatchFns)) stopWatchFns.length = 0;
  } catch (_) {}
  */

  // 5) 解除 socket 監聽（和 mounted 時註冊的事件一一對應）
  if (socket?.value) {
    try { socket.value.off?.('station2_trans_over', onStation2TransOver); } catch (_) {}
    try { socket.value.off?.('station2_agv_end', onStation2AgvEnd); } catch (_) {}
    try { socket.value.off?.('station1_call_result', onStation1CallResult); } catch (_) {}
    // 其他有 .on() 過的事件，也請逐一 off
  }

  // 7) 釋放每個 dialog 的計時/資源
  for (const d of (dialogs.value ?? [])) {
    try { d?.proc?.dispose?.(); } catch (_) {}
    if (d) d.proc = null;
  }

  // 9) 重置可能卡住的 UI 狀態（避免離開頁面時按鈕維持鎖定）
  try {
    isCallAGV.value = false;
    isCallForklift.value = false;
  } catch (_) {}
});

//=== method ===
function goPrev () {
  if (page.value <= 0) return
  transitionName.value = 'slide-prev'
  page.value -= 1
}

function goNext () {
  if (page.value >= pages.length - 1) return
  transitionName.value = 'slide-next'
  page.value += 1
}

function setRowState(materialId, patch) {
  const idx = materials.value.findIndex(r => r.id === materialId);
  if (idx === -1) return;
  materials.value[idx] = { ...materials.value[idx], ...patch };
}

function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimerId = setInterval(() => {
    // 頁籤在前景才拉，減少伺服器負擔
    if (document.visibilityState === 'visible') {
      fetchMaterials()
    }
  }, refreshTimerMs.value) // 10 秒
}

function stopAutoRefresh() {
  if (refreshTimerId) {
    clearInterval(refreshTimerId)
    refreshTimerId = null
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    // 回到前景就立刻更新一次，避免看到舊資料
    fetchMaterials()
  }
}

async function fetchMaterials() {
  try {
    tableLoading.value = true
    await listMaterials()
    lastRefreshed.value = new Date()
  } catch (err) {
    console.error('fetchMaterials error:', err)
  } finally {
    tableLoading.value = false
  }
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    // 使用 async/await 等待 API 請求完成，確保順序正確
    //await listMaterials();
    await fetchMaterials();

    console.log('## materials ##', materials)

    //await listUsers();
    await listUsers2();

    //await listSocketServerIP();
    //console.log("initialize, socket_server_ip:", socket_server_ip.value)
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const setTimerRef = (dlg) => {
  return (el) => {
    dlg.timerRef = el;
  };
}

const getIcon = (isPaused) => {
  return isPaused ? "mdi-play" : "mdi-pause"
}

const customFilter =  (value, query, item)  => {
  return value != null &&
    query != null &&
    typeof value === 'string' &&
    value.toString().toLocaleUpperCase().indexOf(query) !== -1
}

// 計算面板位置函數
const calculatePanelPosition = () => {
  nextTick(() => {
    if (sendButton.value?.$el) {
      const buttonRect = sendButton.value.$el.getBoundingClientRect()
      // 設置面板位置為按鈕右邊 + 5px
      panelX.value = buttonRect.right + 50
      console.log("panelX.value:",panelX.value);
      // 如果有需要可以調用面板的更新位置方法
      //if (draggablePanel.value?.updatePosition) {
      //  draggablePanel.value.updatePosition(panelX.value, panelY.value)
      //}
    }
  })
}

const handlePopState = () => {
  // ✅ 正確方式：保留 Vue Router 的 state
  ////history.pushState(history.state, '', document.URL)
  //window.history.pushState(history.state, '', document.URL)
  // 重新把這一筆 entry 的 state 改回 Router 給的 state
  window.history.replaceState(window.history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const handleDateChange = (newDate) => {
  if (newDate instanceof Date) {
    // 調整為本地時區日期
    const localDate = new Date(newDate.getTime() - newDate.getTimezoneOffset() * 60000);
    fromDateVal.value = localDate;
    formattedDate.value = localDate.toISOString().split('T')[0]; // 格式化為 YYYY-MM-DD

    editDialogBtnDisable.value = false;
  }
  fromDateMenu.value = false;
};

const parseDate = (formatted, format) => {
  const parts = formatted.split('/');
  switch (format) {
    case 'MM/DD/YYYY':
      return { month: parts[0], day: parts[1], year: parts[2] };
    case 'DD/MM/YYYY':
      return { day: parts[0], month: parts[1], year: parts[2] };
    case 'YYYY/MM/DD':
      return { year: parts[0], month: parts[1], day: parts[2] };
    default:
      throw new Error('Unsupported date format');
  }
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 根據輸入搜尋工單編號
const handleOrderNumSearch = () => {
  console.log("handleOrderNumSearch()...");

  let selected = materials.value.find(mat => mat.order_num === selectedOrderNum.value);
  if (selected) {
    selectedOrderNum.value = `${selected.order_num}`;
    console.log("已更新選中工單: ", selectedOrderNum.value);

    inputSelectOrderNum.value = placeholderTextForOrderNum.value;
  } else {
    selectedOrderNum.value = ''; // 清空值，防止未選擇時顯示錯誤內容
  }

  // 確保 placeholder 保持靜態文字
  placeholderTextForOrderNum.value = "請選擇工單";
};

const handleBarCode = () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)
  let myBarcode = materials.value.find(m => m.order_num == bar_code.value);

  // 在這裡做條碼比對、查詢、上傳等邏輯
  if (myBarcode) {
    console.log('找到條碼對應項目:', myBarcode.id);

    // 展開對應的項目
    toggleExpand(myBarcode);
  } else {
    showSnackbar('找不到對應條碼資料！', 'red accent-2');
    console.warn('找不到對應條碼資料!')
    bar_code.value = '' // 清空輸入框（或依需求保留）
  }

  // 清空輸入框（或依需求保留）
  //bar_code.value = ''
};

// 根據輸入搜尋員工編號
const handleEmployeeSearch = () => {
  console.log("handleEmployeeSearch()...");

  let selected = desserts2.value.find(emp => emp.emp_id.replace(/^0+/, '') === selectedEmployee.value);
  if (selected) {
    selectedEmployee.value = `${selected.emp_id} ${selected.emp_name}`;
    console.log("已更新選中員工: ", selectedEmployee.value);

    inputSelectEmployee.value = placeholderTextForEmployee.value;
  } else {
    selectedEmployee.value = ''; // 清空值，防止未選擇時顯示錯誤內容
  }

  // 確保 placeholder 保持靜態文字
  placeholderTextForEmployee.value = "請選擇員工";
};

const updateEmployeeFieldFromSelect = () => {
  console.log("更新 TextField: ", inputSelectEmployee.value);

  const selected = desserts2.value.find(emp => emp.emp_id === inputSelectEmployee.value);
  if (selected) {
    selectedEmployee.value = `${selected.emp_id} ${selected.emp_name}`;
    console.log("已更新選中員工: ", selectedEmployee.value);

    inputSelectEmployee.value = placeholderTextForEmployee.value;
  } else {
    selectedEmployee.value = ''; // 清空值，防止未選擇時顯示錯誤內容
  }

  // 確保 placeholder 保持靜態文字
  placeholderTextForEmployee.value = "請選擇員工";
};
/*
// 啟動閃爍效果
const startFlashing = () => {
  console.log("startFlashing()...")

  isFlashLed.value = false;
  intervalIdForLed = setInterval(() => {
    isVisible.value = !isVisible.value; // 每秒切換顯示狀態
  }, 500);
}
*/
// 停止閃爍效果
//const stopFlashing = () => {
//  console.log("stopFlashing()...")
//
//  clearInterval(intervalIdForLed);
//  isVisible.value = true;               // 重設為顯示
//  isFlashLed.value = false;
//}

const setActive = (value) => {
  toggle_exclusive.value = value;       // 設置當前活動按鈕
  if (toggle_exclusive.value == 1) {
    showMenu.value = true;
    transport_message.value = '備料完成人工送出'
  } else {
    showMenu.value = false;
    transport_message.value = '備料完成自動送出'
  }
}

const checkReceiveQty = (item) => {
  console.log("checkReceiveQty,", item);

  // 將輸入值轉換為數字，並確保是有效的數字，否則設為 0
  const deliveryQty = Number(item.delivery_qty) || 0;   //備料數量 (目前輸入)
  const totalQty = Number(item.total_delivery_qty);    //應備數量

  console.log("deliveryQty > totalQty:", deliveryQty, totalQty)

  if (item.isLackMaterial == 0  && deliveryQty != totalQty && deliveryQty != 0) {
    let temp_str = item.order_num + '工單缺料情況，備料數量不能改變！'
    showSnackbar(temp_str, 'red accent-2');
    return; // 不改變選擇狀態
  }

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
  console.log("handleKeyDown()...")
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

  const inputValue = event.target.value || ''; // 確保 inputValue 是字串

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入, 2025-07-02 modify
  if (inputValue.length > 5 && inputValue < 10000) {
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

  editDialogBtnDisable.value = false;
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
    selectedItems.value.push(item.columns.id);  // 若未選中，則添加 columns.id
  } else {
    selectedItems.value.splice(index, 1);       // 若已選中，則移除 columns.id
  }
};

const handleEscClose = (dlg) => {
  if (!dlg) return;                         // 防空
  if (dlg._closing) return;                 // 防重複關閉
  dlg._closing = true;

  dlg.closeReason = 'esc';
  dlg.dialogVisible = false;                // 交給 watcher 做後續回寫
};

const handleOutsideClick = (dlg) => {
  if (!dlg) return;
  if (dlg._closing) return;
  dlg._closing = true;

  dlg.closeReason = 'outside';
  dlg.dialogVisible = false;                // 交給 watcher 做後續回寫
};

const editOrderNum = async (item) => {
  console.log("editOrderNum(),", item);

  selectedId.value = item.id;
  selectedOrderNum.value = item.order_num;
  selectedReqQty.value = item.req_qty;
  selectedDate.value = item.date;

  fromDateVal.value = new Date(selectedDate.value)
  console.log("fromDateVal:", fromDateVal.value);

  let payload = {
    id: item.id,
  };
  await getBoms(payload);
  console.log("currentBoms:",currentBoms.value)
  modify_boms.value = [...currentBoms.value];
  console.log("boms, modify_boms:", currentBoms.value, modify_boms.value)

  editDialogBtnDisable.value = true;

  editDialog.value = true;
}

/*
async function enforceStartPausedIfNew(dlg) {
  // 先等 TimerDisplay 掛好
  await nextTick();

  // 取目前毫秒（優先用 TimerDisplay; 退回用 composable 的 elapsedMs）
  const ms =
    dlg?.timerRef?.getElapsedMs?.() ??
    dlg?.proc?.elapsedMs?.value ??
    0;

  // 只在「全新」(0 ms) 才處理；舊工單不動
  if (ms !== 0) return;

  // 1) 視覺 & 本地狀態 → 暫停
  dlg?.timerRef?.pause?.();
  if (dlg?.proc?.isPaused) dlg.proc.isPaused.value = true;

  // 2) 回寫到後端（把 is_paused=true + elapsed=0 同步上去）
  if (dlg?.proc?.updateProcess) {
    try {
      await dlg.proc.updateProcess();  // 會帶 is_paused=true 與目前 elapsed
    } catch (e) {
      console.warn('enforceStartPausedIfNew → updateProcess 失敗：', e);
    }
  }
}
*/

const toggleExpand = async (item) => {
  console.log("toggleExpand(),item.order_num, item.isOpen:", item.order_num, item.isOpen);

  if (item.isTakeOk) {
    showSnackbar("備料已完成!", "orange-darken-2");
    return;
  }

  if (item.hasStarted && item.isOpenEmpId !="" && item.isOpenEmpId != currentUser.value.empID) {
    let temp_msg = "員工" + item.isOpenEmpId + "備料進行中..."
    showSnackbar(temp_msg, "orange-darken-2");
    return;
  }

  if (item.isOpen && item.isOpenEmpId !="" && item.isOpenEmpId !="" && currentUser.value.empID != item.isOpenEmpId) {
    let temp_msg = "員工" + item.isOpenEmpId + "準備中..."
    showSnackbar(temp_msg, "orange-darken-2");
    return;
  }

  enableDialogBtn.value = item.isTakeOk && !item.isShow;    //備料完成(按確定鍵) && AGV還沒送出

  let payload = {};

  payload = {
    //order_num: item.order_num,
    id: item.id,
  };
  await getBoms(payload);

  current_cell.value = item.delivery_qty
  editedRecord.value = item;                // 點擊詳情按鍵的目前紀錄

  // 記錄當前開始備料時間
  currentStartTime.value = new Date();      // 使用 Date 來記錄當時時間
  console.log("Start time:", currentStartTime.value, item, item.id);

  // 記錄當前途程狀態
  payload = {
    id: item.id,
    //order_num: item.order_num,
    record_name: 'show2_ok',
    record_data: 0                //未備料
  };
  await updateMaterial(payload);

  payload = {
    id: item.id,
    //order_num: item.order_num,
    record_name: 'shortage_note',
    record_data: ''
  };
  await updateMaterial(payload);

  dialog_order_num.value=item.order_num;

  const user_id = currentUser.value.empID;
  const process_type = 1;
  const material_id = item.id;
  const order_num = item.order_num;

  let dlg = dialogs.value.find(d => d.material_id === material_id && d.user_id === user_id);
  if (!dlg) {
    dlg = reactive({
      material_id,
      order_num,
      user_id,
      process_type,
      dialogVisible: true,
      timerRef: null,

      proc: null,       // 每個 dialog 一個 useProcessTimer 實例

      _closing: false,  // ESC/外點防重入
      closeReason: null // 關閉原因（'esc' | 'outside' | 'normal' ...）
    });

    dialogs.value.push(dlg);

    // 立刻建立 proc（把 timerRef 傳進去）
    dlg.proc = useProcessTimer(() => dlg.timerRef);

    await nextTick();

    // 啟動/還原（從後端拿 elapsed_time / is_paused）
    await dlg.proc.startProcess(material_id, process_type, user_id);
    console.log("Process ID:", dlg.proc.processId);
    currentProcessId.value = dlg.proc.processId;

    // 若為全新工單就強制改成暫停
    //await enforceStartPausedIfNew(dlg);
    /*
    // 偵測新工單、且正在跑 → 立刻停住並回寫成暫停。
    // === 新增, begin：對「全新工單(00:00:00)」進場強制顯示「開始」 ===
    await nextTick(); // 先等 TimerDisplay 掛好

    setTimeout(async () => {
      const ms =
        dlg?.timerRef?.getElapsedMs?.() ??
        dlg?.proc?.elapsedMs?.value ??
        0;

      const running = dlg?.proc?.isPaused?.value === false;

      // 只有「毫秒 = 0」且「目前正在跑」才處理；其他全部不動
      if (ms === 0 && running) {
        // 1) 視覺先停住（畫面顯示「開始」）
        dlg?.timerRef?.pause?.();
        if (dlg?.proc?.isPaused) dlg.proc.isPaused.value = true;

        // 2) 回寫到後端（把 is_paused=true，同步成真正暫停）
        try {
          await dlg?.proc?.updateProcess?.(); // 你現有的 API 會帶 is_paused=true
        } catch (e) {
          console.warn('force-start-paused (new order) → updateProcess failed:', e);
        }
      }
    }, 0);
    // === 新增, end：
    */
  } else {
    dlg._closing = false;       // 重置關閉旗標
    dlg.closeReason = null;     // 重置關閉原因

    dlg.dialogVisible = true; // 只要打開就好

    await nextTick();
    // 再同步一次（例如換人接手或後端狀態變了）
    //await dlg.proc.startProcess(material_id, process_type, user_id);
  }
};

// 關閉 dialog
async function handleClose(dlg) {
  //await dlg.proc.closeProcess();   // 停表 + 回寫 + reset
  await dlg.proc.updateProcess();   // 先把目前時間回寫（不結束）
  dlg.dialogVisible = false;
}

// 按「確定」時（視你的流程，可能只是 update）
async function handleConfirm(dlg) {
  //await dlg.proc.updateProcess();   // 先把目前時間回寫(不結束)
  if (!dlg?.proc) return;
  console.log("closeProcess(), qty:", editedRecord.value.delivery_qty)
  await dlg.proc.closeProcess({ receive_qty: editedRecord.value.delivery_qty});   // 停表 + 回寫 + reset
  dlg.dialogVisible = false;

  // 可選：從 dialogs 移除
  const idx = dialogs.value.indexOf(dlg);
  if (idx !== -1) dialogs.value.splice(idx, 1);
}

const checkTextEditField = (focused, item) => {
  //if (!focused) { // 當失去焦點時
  //  console.log("checkTextEditField(): 失去焦點");
  //} else {
  //  console.log("checkTextEditField(): 獲得焦點");
  //}

  if (focused) {
    console.log("checkTextEditField(): 獲得焦點");
    editingRowId.value = item.id;
    //stopAutoRefresh()
  } else {
    console.log("checkTextEditField(): 失去焦點");
    editingRowId.value = null;
    //startAutoRefresh()
  }

  item._editing_delivery = !!focused

};

const addAbnormalInMaterial = (item) => {

  abnormalDialog_record.value = materials.value.find(m => m.id == item.id);

  console.log("addAbnormalInMaterial(),", item, abnormalDialog_record.value);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_autocomplete_message.value = null;
  abnormalDialog_search.value = ''                   // 清掉舊搜尋字
  abnormalDialog_display.value = item.Incoming0_Abnormal;
  abnormalDialog.value = true;
  abnormalDialog_message.value = item.Incoming0_Abnormal_message;
}

const createAbnormalFun = async () => {
  console.log("createAbnormalFun()...");

  if (abnormalDialog_autocomplete_message.value !== null) {
    const selected = itemsWithIcons.find(x => x.id === abnormalDialog_autocomplete_message.value)
    const temp_str = `(${selected?.text ?? ''})`
    //let temp_str = '(' + abnormalDialog_autocomplete_message.value + ')'
    abnormalDialog_message.value = `備料區檢料異常! ${temp_str}`;
    let payload = {}
    try {
      console.log("abnormalDialog_record.order_num:", abnormalDialog_record.value.order_num)

      payload = {
        order_num: abnormalDialog_record.value.order_num,
        record_name: 'Incoming0_Abnormal',
        record_data: abnormalDialog_message.value,
      };
      await updateMaterial(payload);

      abnormalDialog_record.value.Incoming0_Abnormal=false;
      abnormalDialog_record.value.Incoming0_Abnormal_message=abnormalDialog_message.value;

      // targetIndex為目前table data record 的 index
      const targetIndex = materials.value.findIndex(
        //(kk) => kk.id === item.id
        (kk) => kk.id === abnormalDialog_record.value.id
      );

      if (targetIndex !== -1) {
        // 用 Vue 的方式確保觸發響應式更新
        materials.value[targetIndex] = {
          ...materials.value[targetIndex],
          Incoming0_Abnormal: false,
          Incoming0_Abnormal_message: abnormalDialog_message.value,
        };
      }

      console.log('更新成功...');
    } catch (error) {
      console.error('更新失敗:', error.response?.data?.message || error.message);
    }
  }
  abnormalDialog.value = false;
}

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

  // 記錄當前備料數量
  payload = {
    id: item.id,
    record_name: 'delivery_qty',
    record_data: deliveryQty,
  };
  await updateMaterial(payload);
  item.delivery_qty = deliveryQty

  payload = {
    material_id: item.id,
    seq: 2,
    record_name1: 'process_work_time_qty',
    record_data1: deliveryQty,
  };
  await updateProcessDataByMaterialID(payload);

  item.isError = true;              // 輸入數值正確後，重置 數字 為 紅色

  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }
};

const onConfirm = async (dlg) => {
  try {
    await updateItem();       // 先更新
    await handleConfirm(dlg); // 再處理 dialog 收尾/關閉/寫後端等
  } catch (err) {
    console.error('confirm failed:', err);
  }
};

const updateItem = async () => {    //編輯 bom, material及process後端table資料
  console.log("MaterialListForAssm.vue, updateItem(),", boms.value);

  isConfirmed.value = true;

  //let my_material_orderNum = boms.value[0].order_num;

  currentEndTime.value = new Date();  // 記錄當前結束時間
  let periodTime = calculatePeriodTime(currentStartTime.value, currentEndTime.value);  // 計算時間間隔
  let formattedStartTime = formatDateTime(currentStartTime.value);
  let formattedEndTime = formatDateTime(currentEndTime.value);

  // 使用 .some() 檢查是否有任何 `receive` 為 false 的項目
  // 若有則將 `take_out` 設為 false, 缺料且檢料完成
  // 若無則將 `take_out` 設為 true, 沒有缺料且檢料完成
  let take_out = !boms.value.some(bom => !bom.receive);
  console.log("take_out:", take_out);

  // 1. 更新 boms 資料
  //2025-02-11 mark and update the following block
  //let response0 = await updateBoms(boms.value);
  //if (!response0) {
  //  showSnackbar(response0.message, 'red accent-2');
  //  dialog.value = false;
  //  return;
  //}
  await updateBoms(boms.value);

  let payload = {}

  // begin block檢查是否缺料
  if (!take_out) {                // 該筆訂單缺料且檢料完成
    payload = {                       // 更新 materials 資料，shortage_note = '(缺料)'
      //order_num: my_material_orderNum,
      id: editedRecord.value.id,
      record_name: 'shortage_note',
      record_data: '(缺料)'
    };
    await updateMaterial(payload);
    editedRecord.value.shortage_note = '(缺料)';

    payload = {                       // 2. 更新 materials 資料，isLackMaterial = 0
      //order_num: my_material_orderNum,
      id: editedRecord.value.id,
      record_name: 'isLackMaterial',
      record_data: 0,          //缺料flag
    };
    await updateMaterial(payload);

    editedRecord.value.isLackMaterial = 0;    //缺料(尚未拆單)且檢料完成

  } else {                        // 沒有缺料且檢料完成
    payload = {
      //order_num: my_material_orderNum,
      id: editedRecord.value.id,
      record_name: 'shortage_note',
      record_data: ''
    };
    await updateMaterial(payload);
    editedRecord.value.shortage_note = '';

    payload = {       // 2. 更新 materials 資料，isLackMaterial = 99
      //order_num: my_material_orderNum,
      id: editedRecord.value.id,
      record_name: 'isLackMaterial',
      record_data: 99,
    };
    await updateMaterial(payload);

    editedRecord.value.isLackMaterial = 99;   //沒有缺料且檢料完成 flag
  }
  // end block檢查是否缺料

  // 紀錄前端已經按了確定鍵的狀態
  payload = {
    //order_num: my_material_orderNum,
    id: editedRecord.value.id,
    record_name: 'isTakeOk',
    record_data: true
  };
  await updateMaterial(payload);
  editedRecord.value.isTakeOk = true;

  // 紀錄前端備料已完成
  payload = {
    //order_num: my_material_orderNum,
    id: editedRecord.value.id,
    record_name: 'hasStarted',
    record_data: false
  };
  await updateMaterial(payload);
  editedRecord.value.hasStarted = false;

  await nextTick();

  payload = {
    //order_num: my_material_orderNum,
    id: editedRecord.value.id,
    record_name: 'show2_ok',
    record_data: 2                  // 備料完成
  };
  await updateMaterial(payload);
  /*
  console.log("Formatted Start Time:", formattedStartTime);
  console.log("Formatted End Time:", formattedEndTime);
  console.log("Period time:", periodTime);
  console.log("editedRecord:", editedRecord.value);
  let processPayload = {
    begin_time: formattedStartTime,
    end_time: formattedEndTime,
    periodTime: periodTime,
    periodTime2: dialog_totalActiveTime.value,
    user_id: currentUser.value.empID,
    //order_num: my_material_orderNum,
    process_type: 1,                  // 備料
    id: editedRecord.value.id,
    process_work_time_qty: editedRecord.value.req_qty, // 報工數量
  };
  await createProcess(processPayload);
  */
  /*
  payload = {
    process_id: currentProcessId.value,
    record_name: 'end_time',
    record_data: formattedEndTime,
  };
  await updateProcessData(payload);
  */
  payload = {
    process_id: currentProcessId.value,
    record_name: 'process_work_time_qty',
    record_data: editedRecord.value.req_qty,
  };
  await updateProcessData(payload);

  //await listMaterials();    //2025-02-07 mark this line
  await fetchMaterials();

  if (!take_out) {                     // 該筆訂單檢料完成且缺料
    payload = {
      copy_id: editedRecord.value.id,
      delivery_qty: editedRecord.value.delivery_qty,
      //total_delivery_qty: tempDelivery,
      show2_ok: 2,            //備料完成
      shortage_note: '',
    }
    await copyMaterialAndBom(payload);
    //console.log("material_copy:", material_copy.value)

    payload = {               // 2. 更新 materials 資料，isLackMaterial = 0
      id: material_copy.value.id,
      record_name: 'isLackMaterial',
      record_data: 0,          //缺料flag
    };
    await updateMaterial(payload);
    material_copy.value.isLackMaterial = 0;

    materials.value.push(material_copy.value);

    // 立刻排序：
    materials.value.sort((a, b) => {
      if (a.order_num === b.order_num) {
        // isTakeOk: True 排前面 → False > True 時應該 return 1
        return (a.isTakeOk === b.isTakeOk) ? 0 : (a.isTakeOk ? -1 : 1);
      }
      // order_num 升序
      return a.order_num.localeCompare(b.order_num);
    });
  } // end if
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

const onClickTrans = () => {
  if (toggle_exclusive.value == 1) {
    callForklift();
  } else {
    callAGV();
  }
};

const callForklift = async () => {
  console.log("callForklift()...");

  // 防重複呼叫 + 基本檢查
  const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];
  if (selectedIds.length === 0) {
    showSnackbar('請選擇送料的工單!', 'red accent-2');
    return;
  }
  if (isCallForklift.value) {
    showSnackbar('請不要重複按鍵!', 'red accent-2');
    return;
  }

  if (!selectedEmployee.value) {
    showSnackbar('請先選擇領料送出的員工!', 'red accent-2');
    return;
  }

  isCallForklift.value = true;
  try {
    console.log('trans_end 處理步驟1...');

    // 步驟 1：更新 material/assemble 顯示狀態 + 紀錄搬運方式
    for (const id of selectedIds) {
      const m = materials.value.find(x => x.id == id);
      if (!m) {
        console.warn('找不到 material，id =', id);
        continue;
      }

      // 組裝站 / 未組裝 / 等待組裝中 / 目標途程
      await updateMaterialRecord({
        id: m.id,
        show1_ok: 2,     // 組裝站
        show2_ok: 3,     // 未組裝
        show3_ok: 3,     // 等待組裝中
        whichStation: 2, // 目標途程: 組裝站
      });

      // 同步更新 assemble
      await updateAssmbleDataByMaterialID({
        material_id: m.id,
        delivery_qty: 0,
        record_name1: 'show1_ok',
        record_data1: 2,
        record_name2: 'show2_ok',
        record_data2: 3,
        record_name3: 'show3_ok',
        record_data3: 3,
      });

      // 搬運方式：false = 手動(堆高機)
      await updateMaterial({
        id: m.id,
        record_name: 'move_by_automatic_or_manual',
        record_data: false,
      });
    }

    console.log('trans_end 處理步驟2...');

    // 步驟 2：建立流程、寫回數量/狀態、處理多批次
    for (const id of selectedIds) {
      const m = materials.value.find(x => x.id == id);
      if (!m) continue;

      // 2-1. 建立「forklift 到組裝區」流程
      await createProcess({
        //user_id: currentUser.value?.empID ?? '',
        user_id: selectedEmployee.value,
        process_type: 5, // forklift到組裝區
        id: m.id,
      });
      console.log('步驟2-1...');

      // 2-2. 記錄送料數量
      await updateMaterial({
        id: m.id,
        record_name: 'delivery_qty',
        record_data: m.delivery_qty,
      });
      console.log('步驟2-2...');

      // 2-2-a. 記錄應領取數量（用 total_delivery_qty）
      await updateAssembleMustReceiveQtyByMaterialID({
        material_id: m.id,
        record_name: 'must_receive_qty',
        record_data: m.total_delivery_qty,
      });
      console.log('步驟2-2-a...');

      // 2-3. 讓此筆在看板上顯示
      await updateMaterial({
        id: m.id,
        record_name: 'isShow',
        record_data: true,
      });
      console.log('步驟2-3...');

      // 2-4. 多批次 or 單批次
      const isMultiBatch = Number(m.delivery_qty) !== Number(m.total_delivery_qty);

      if (isMultiBatch) {
        console.log('1張工單多批次運送, 新增未運送數量(相同工單)');
        const remain = Number(m.total_delivery_qty) - Number(m.delivery_qty);
        if (remain > 0) {
          await copyMaterial({
            copy_id: m.id,                   // 工單 table id
            delivery_qty: m.delivery_qty,    // 本批備料
            total_delivery_qty: remain,      // 剩餘應備
            show2_ok: 2,                     // 備料完成
            shortage_note: '',
          });
          test_count.value = (test_count.value || 0) + 1;
          console.log('步驟2-4...', test_count.value);
        }
      } else {
        // 單批次 → 直接進「等待組裝作業」
        await updateMaterial({
          id: m.id,
          record_name: 'show2_ok',
          record_data: 3,
        });

        // 若為合併工單，處理 BOM/收料合併並通知前端刷新
        if (m.is_copied) {
          await updateBomXorReceive({ copied_material_id: m.id });
          await delay(1000);
          eventBus.emit('merge_work_orders');
          console.log('合併工單顯示通知已發出');
        }
      }
    }
  } catch (err) {
    console.error('trans_end 發生例外：', err);
    showSnackbar('堆高機流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    // 無論成功或失敗都解鎖，避免卡住無法再按
    await delay(3000);

    isCallForklift.value = false;
  }


/*
  let payload = {};
  let targetItem = {};

  if (!isCallForklift.value) {                          // 沒有重複呼叫
    if (selectedItems.value.length == 0) {              // 已點選選單
      showSnackbar("請選擇送料的工單!", 'red accent-2');
      return;
    }

    isCallForklift.value = true
  } else {
    showSnackbar("請不要重複按鍵!", 'red accent-2');
    return;
  } // end if

  console.log('trans_end 處理步驟1...');
  selectedItems.value.forEach(async (item) => {
    console.log('selectedItems, item:', item);

    targetItem = materials.value.find(m => m.id == item);
    console.log("targetItem:", targetItem)

    payload = {
      id: targetItem.id,
      show1_ok: 2,      //組裝站
      show2_ok: 3,      //未組裝
      show3_ok: 3,      //等待組裝中
      whichStation: 2,  //目標途程:組裝站
    };
    await updateMaterialRecord(payload);

    payload = {
      material_id: targetItem.id,
      delivery_qty: 0,
      record_name1: 'show1_ok',
      record_data1: 2,
      record_name2: 'show2_ok',
      record_data2: 3,
      record_name3: 'show3_ok',
      record_data3: 3,
    };
    await updateAssmbleDataByMaterialID(payload)

    payload = {
      id: targetItem.id,
      record_name: 'move_by_automatic_or_manual',
      record_data: false
    };
    await updateMaterial(payload);
  });

  console.log('trans_end 處理步驟2...');
  selectedItems.value.forEach(async (item) => {
    console.log('selectedItems, item:', item);

    let myMaterial = materials.value.find(m => m.id == item);
    console.log('selectedItems, item:', myMaterial);

    payload = {
      user_id: currentUser.value.empID,
      process_type: 5,                          //forklift到組裝區
      id: myMaterial.id,
    };
    await createProcess(payload);
    console.log('步驟2-1...');

    //紀錄該筆的forklift送料數量
    payload = {
      id: myMaterial.id,
      record_name: 'delivery_qty',
      record_data: myMaterial.delivery_qty
    };
    await updateMaterial(payload);
    console.log('步驟2-2...');

    //紀錄該筆的應領取數量
    payload = {
      material_id: myMaterial.id,
      record_name: 'must_receive_qty',
      record_data: myMaterial.total_delivery_qty,
    };
    await updateAssembleMustReceiveQtyByMaterialID(payload);
    console.log('步驟2-2-a...');

    //紀錄該筆的forklift送料狀態
    payload = {
      id: myMaterial.id,
      record_name: 'isShow',
      record_data: true
    };
    await updateMaterial(payload);
    console.log('步驟2-3...');

    if (Number(myMaterial.delivery_qty) != Number(myMaterial.total_delivery_qty)) { // 1張工單多批次運送
      console.log("1張工單多批次運送, 新增未運送數量(相同工單)")

      let tempDelivery = myMaterial.total_delivery_qty - myMaterial.delivery_qty;

      payload = {
        copy_id: myMaterial.id,                 //工單table id
        delivery_qty: myMaterial.delivery_qty,  //備料數量
        total_delivery_qty: tempDelivery,       //應備數量
        show2_ok: 2,                            //備料完成
        shortage_note: '',
      }
      await copyMaterial(payload);
      test_count.value += 1;
      console.log('步驟2-4...', test_count.value);
    } else {
      payload = {
        id: myMaterial.id,
        record_name: 'show2_ok',
        record_data: 3                  // 等待組裝作業
      };
      await updateMaterial(payload);

      if (myMaterial.is_copied)  {
        payload = {
          copied_material_id: myMaterial.id,
        };
        await updateBomXorReceive(payload);

        // 延遲 1 秒
        await delay(1000);

        // 通知合併工單顯示
        eventBus.emit('merge_work_orders');
        console.log('合併工單顯示通知已發出')
      }
    } // end else loop
  });
*/

      // 插入延遲 3 秒
      await delay(3000);

      selectedItems.value = [];
      if (localStorage.getItem('selectedItems')) {
        localStorage.removeItem('selectedItems');
      }
      //待待
      window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)

//##
};

const callAGV = async () => {
  console.log("callAGV()...");

  // 乾淨的 id 陣列（去重）
  const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];

  if (selectedIds.length === 0) {
    showSnackbar('請選擇送料的工單!', 'red accent-2');
    return;
  }
  if (isCallAGV.value) {
    showSnackbar('請不要重複按鍵!', 'red accent-2');
    return;
  }

  isCallAGV.value = true;
  try {
    // AGV 自動送料模式：先查 AGV 狀態
    if (toggle_exclusive.value === 2) {
      await getAGV({ agv_id: 1 });
      console.log('hello, 備料區叫車, AGV 狀態:', currentAGV.value);
      // 若要強制攔截忙碌狀態，可取消下面註解
      // if (currentAGV.value?.status !== 0) {
      //   const stationMap = {1: '備料區', 2: '組裝區', 3: '成品區'};
      //   const buf = stationMap[currentAGV.value?.station] || '未知區域';
      //   showSnackbar(`${buf}已經叫車，AGV 目前忙碌中...`, 'red accent-2');
      //   return;
      // }
    }

    // 送出叫車事件（真的帶 payload）
    socket.value.emit('station1_call', {
      items: selectedIds,
      orderNums: Array.isArray(selectedOrderNums.value) ? [...selectedOrderNums.value] : [],
    });
    console.log('送出 station1_call 訊息...');

    // UI 先切到等待狀態
    order_num_on_agv_blink.value = '叫車進站中...';
    activeColor.value = 'red'; // 等待運輸

    // 記錄等待 agv 到站開始時間
    agv1StartTime.value = new Date();
    console.log('AGV Start time:', agv1StartTime.value);

    // 逐筆更新「等待 AGV」狀態 + 相關 Process 欄位
    let successCount = 0;
    for (const id of selectedIds) {
      try {
        await updateMaterial({
          id,
          record_name: 'show3_ok', // 看板欄位
          record_data: 1,          // 1: 等待 agv
        });

        const m = materials.value.find(x => x.id == id);
        //if (!m) continue;

        await updateProcessDataByMaterialID({
          material_id: id,
          seq: 2,
          record_name1: 'process_work_time_qty',
          record_data1: m.delivery_qty,
        });

        successCount++;
      } catch (err) {
        console.error('更新等待 AGV 狀態失敗，id =', id, err);
      }
    }

    // 至少一筆成功才把 AGV 設為忙碌（避免空跑）
    if (successCount > 0) {
      await updateAGV({
        id: 1,
        status: 1,  // 忙碌/等待
        station: 1, // 備料區
      });
    } else {
      showSnackbar('沒有任何工單更新成功，未變更 AGV 狀態', 'red accent-2');
    }
  } catch (e) {
    console.error('叫車流程例外：', e);
    showSnackbar('叫車流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    // 無論成功失敗都解鎖，避免按鈕被卡住
    isCallAGV.value = false;
  }


  /*
  let payload = {};

  if (!isCallAGV.value) {       // 沒有重複按鍵
    //console.log("step2...");
    if (selectedItems.value.length == 0) {  //已點選選單
      //console.log("step2-1...");
      showSnackbar("請選擇送料的工單!", 'red accent-2');
      return;
    }

    if (toggle_exclusive.value == 2) {   //AGV自動送料
      //console.log("step3-1...");
      payload = {agv_id: 1};
      await getAGV(payload);
      console.log("hello, 備料區叫車, AGV 狀態:", currentAGV.value);

      //確定AGV目前是閒置
      if (currentAGV.value.status != 0) {
      //  const stationMap = {1: '備料區', 2: '組裝區',  3: '成品區'};
      //  const buf = stationMap[currentAGV.value.station] || '未知區域';
      //  showSnackbar(`${buf}已經叫車, AGV目前忙碌中...`, 'red accent-2');
      //  return;
      }

      isCallAGV.value = true
    }
    //console.log("step4...");
  } else {
    //console.log("step5...");
    showSnackbar("請不要重複按鍵!", 'red accent-2');
    return;
  }
  //console.log("step6...");

  // 更新AGV狀態資料, AGV忙碌中
  payload = {
    id: 1,
    status: 1,
    station:  1,
  };
  await updateAGV(payload);

  payload = {
    items: selectedItems.value,
    orderNums: selectedOrderNums.value,
  };

  socket.value.emit('station1_call');  //2025-02-24 add payload
  console.log("送出 station1_call訊息...")

  order_num_on_agv_blink.value='叫車進站中...'

  activeColor.value='red';    // 等待運輸

  // 記錄等待agv到站開始時間
  agv1StartTime.value = new Date();  // 使用 Date 來記錄當時時間
  console.log("AGV Start time:", agv1StartTime.value);

  selectedItems.value.forEach(async (item) => {
    console.log('selectedItems, item:', item);

    payload = {
      id: item,
      record_name: 'show3_ok',                  //看板要顯示的欄位名稱
      record_data: 1                            //看板要顯示的欄位內容, 1:等待agv
    };
    await updateMaterial(payload);

    payload = {
      material_id: item,
      seq: 1,
      record_name1: 'process_work_time_qty',
      record_data1: 10,
    };
    await updateProcessDataByMaterialID(payload);


  });
  //console.log("step7...");
  */
};

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

    fileCount.value = 0;
    if (excel_file_data.status) {
      //fileCount.value = 0;
      await deleteAssemblesWithNegativeGoodQty();

      //listMaterials();
      await fetchMaterials();

      // 自動 focus, 2025-06-03
      if (barcodeInput.value) {
        barcodeInput.value.focus();
      }

    } else {
      showSnackbar(excel_file_data.message, 'red accent-2');
    }
  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("An error occurred.", 'red accent-2');
  }
};

const updateModifyMaterialAndBomsFun = async () => {
  console.log("updateModifyMaterialAndBomsFun()...");

  let payload = {
    id: selectedId.value,
    date: selectedDate.value,
    qty: selectedReqQty.value,
    file_name: modify_file_name.value,
    bom_data: modify_boms.value,
  };

  await updateModifyMaterialAndBoms(payload)

  editDialog.value = false

  await listMaterials();
  await nextTick();
}

async function onModify() {
  const ok = await confirmRef.value.open({
    title: '匯入工單',
    message: '匯入新的資料將修改目前工單資料(BOM/Assemble/Process)，確定？',
    okText: '確定',
    cancelText: '取消',
  })
  if (ok) {
    modifyExcelFilesFun();
  }
}

async function onDelete() {
  const ok = await confirmRef.value.open({
    title: '刪除工單',
    message: '此操作將刪除目前工單資料(BOM/Assemble/Process)，確定？',
    okText: '確定',
    cancelText: '取消',
  })
  if (ok) {
    removeMaterialsAndRelationTableFun();
  }
}

const removeMaterialsAndRelationTableFun = async () => {
  console.log("removeMaterialsAndRelationTableFun()...");

  console.log("id:",selectedId.value);
  let payload = {
    id: selectedId.value,                   // material table id
  };

  try {
    const status = await removeMaterialsAndRelationTable(payload);
    console.log("status:", status)
    if (status) {
      editDialog.value = false
      await listMaterials();
      await nextTick();   // 操作「更新後的 DOM」, 如自動捲動/聚焦/量尺寸才需要
      showSnackbar("刪除工單完成!", 'green darken-1');
    }
  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("An error occurred.", 'red accent-2');
  }
}

const modifyExcelFilesFun = async () => {
  console.log("modifyExcelFilesFun()...");
  console.log("id:",selectedId.value);
  let payload = {
    id: selectedId.value,                   // material table id
    //material_id: selectedOrderNum.value,    //工單編號
  };

  try {
    const modify_result = await modifyExcelFiles(payload);
    console.log("modify_result:", modify_result);
    if (modify_result.status) {
      console.log("modify_result.status:", modify_result.status);
      modify_boms.value = modify_result.bom;
      modify_file_name.value = modify_result.processedFiles;
      console.log("modify_boms:", modify_boms.value);
      //console.log("modify_file_name:", modify_file_name.value);
      //console.log("results:", modify_result.results);
      //console.log("message:", modify_result.message);

      editDialogBtnDisable.value = false;

      // 重新抓清單
      await listMaterials();

      // 操作「更新後的 DOM」, 如自動捲動/聚焦/量尺寸才需要
      await nextTick();

      showSnackbar(modify_result.message, 'green darken-1');
    } else {
      showSnackbar(modify_result.message, 'red accent-2');
    }

  } catch (error) {
    console.error("Error during execution:", error);
    showSnackbar("An error occurred.", 'red accent-2');
  }
};

// 改變拖曳功能
const toggleDrag = () => {
  panel_flag.value = !panel_flag.value
}

// 控制面板樣式，包括邊框顏色和層級 (z-index)
const panelStyle = computed(() => ({
  cursor: panel_flag.value ? 'move' : 'default',
  border: panel_flag.value ? '2px solid blue' : '2px solid transparent',
  zIndex: panel_flag.value ? 9999 : 1, // 當可拖曳時，將面板提升至最上層
}))

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};
/*
// 雙擊事件處理函式（箭頭函式）
const moveToUserFacets = (index) => {
  const item = allFacets.value.splice(index, 1)[0];
  userFacets.value.push(item);
};

const moveToAllFacets = (index) => {
  const item = userFacets.value.splice(index, 1)[0];
  allFacets.value.push(item);
};
*/

// 設定localStorage內容
const setAuthenticated = (isLogin) => {
  localStorage.setItem('Authenticated', isLogin)
};

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

//:deep(.v-data-table-footer__items-per-page) {
//  display: none;
//}

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

:deep(.v-picker__header) {
  display: none
}

:deep(.v-picker-title) {
  display: none
}

// 客製化 手推車/AGV切換按鍵
.button-container {
  position: relative;
  width: fit-content;     // 調整寬度以適應按鈕
  right: 150px;
  top: 0px;
}

.blue-text {
  color: #003171;   // 設置字體顏色為深藍色
  //color: red;
  font-weight: 700;
}

.facet-container {
  width: 330px;
}

.right {
  float: right;
}

.left {
  float: left;
}

p {
  clear: both;
  padding-top: 1em;
}

.facet-list {
  list-style-type: none;
  margin: 0;
  padding: 0;
  margin-right: 10px;
  background: #eee;
  padding: 5px;
  width: 143px;
  min-height: 1.5em;
  font-size: 0.85em;
}

.facet-list li {
  margin: 5px;
  padding: 5px;
  font-size: 1.2em;
  width: 120px;
}

.facet-list li.placeholder {
  height: 1.2em;
}

.facet {
  border: 1px solid #bbb;
  background-color: #fafafa;
  cursor: pointer;
}

.placeholder {
  border: 1px solid orange;
  background-color: #fffffd;
}

:deep(.v-date-picker-month__weekday) {
  font-weight: bold;
  visibility: hidden; /* 隱藏原始內容，但保留空間 */
  position: relative; /* 必須為 ::after 提供相對定位 */
}

/* 添加新的中文字符 */
:deep(.v-date-picker-month__weekday:nth-child(1))::after {
  content: '日';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(2))::after {
  content: '一';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(3))::after {
  content: '二';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(4))::after {
  content: '三';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}
:deep(.v-date-picker-month__weekday:nth-child(5))::after {
  content: '四';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}

:deep(.v-date-picker-month__weekday:nth-child(6))::after {
  content: '五';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}

:deep(.v-date-picker-month__weekday:nth-child(7))::after {
  content: '六';
  visibility: visible;
  position: absolute;
  top: 20;
  left: 0;
  right: 0;
  text-align: center;
}

.text-caption {
  margin-right: 8px;      // 與輸入框內容留出間距
  color: gray;       // 設定文字顏色
  right: -20px;
  position: relative;
  font-size: 16px !important;
  font-weight: 600;
  font-family: '微軟正黑體', sans-serif;
}

.modify_order_num {
  position: relative;
  top:0px;
  width: 220px;
  right: -20px;
}

:deep(.modify_order_num span) {
  color:#0D47A1
}

:deep(.modify_qty span) {
  color:#0D47A1
}

:deep(.modify_qty .v-input__control) {
  min-width: 60px;
  width: 60px;
}

.modify_date {
  position: relative;
  top:0px;
  width: 150px;
  right: 0px;
}

:deep(.modify_date .v-input__prepend) {
  margin-inline-end: 0;
}

:deep(i.mdi-calendar) {
  color: #F44336;
}
//.v-input--horizontal .v-input__prepend {
.custom-bordered-row {
  border: 2px solid #0D47A1;  // 設定邊框寬度與顏色
  border-radius: 8px;             // 可選: 為邊框添加圓角
  padding: 16px;
}

:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}

.warnning_btn {
  color: red;
}

.control-panel {
  position: absolute;
  top: 50px;
  left: 50px;
  padding: 20px;
  background-color: white;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
}

.control-panel.draggable {
  cursor: move;
}

:deep(.panel_position) {
  position: fixed;
  top: 80px;
  right: 30px;
  z-index: 230;
}

//:deep(.red-border .v-field) {
//  border: 1px solid red !important;
//  border-radius: 4px;

// 選單展開時每個 item 的字體
//:deep(.v-list-item-title) {
//:deep(.v-field .v-list-item-title) {
//  font-size: 16px !important;
//  font-family: Arial, sans-serif !important;
//  font-weight: bold !important;
//}

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
//===

.seperator h5 {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 1em;
}

//.seperator h5::before,
.seperator h5::after {
  content: "";
  //display: block;
  //flex-grow: 1;
  height: 2px;
  background: #ccc;
  flex: 0 0 620px;   // 不伸縮，固定 620px
  margin-left: 5px;
}

.seperator h5 span {
  padding: 0 2em;
}

.dropdown-label{
  cursor: pointer;
  user-select: none;
}

.dropdown-label:hover{
  text-decoration: underline;
}

.card-border-blue {
  border: 2px solid #0d47a1;
  border-radius: 12px;
}

.content-area{
  line-height: 1.6;
}

/* 下一頁：新內容從右進，舊內容往左出 */
.slide-next-enter-active,
.slide-next-leave-active{
  transition: transform .18s ease, opacity .18s ease;
}
.slide-next-enter-from{
  transform: translateX(14px);
  opacity: 0;
}
.slide-next-leave-to{
  transform: translateX(-14px);
  opacity: 0;
}

/* 上一頁：新內容從左進，舊內容往右出 */
.slide-prev-enter-active,
.slide-prev-leave-active{
  transition: transform .18s ease, opacity .18s ease;
}
.slide-prev-enter-from{
  transform: translateX(-14px);
  opacity: 0;
}
.slide-prev-leave-to{
  transform: translateX(14px);
  opacity: 0;
}

:deep(.order-no) {
  color: #1976d2;
  font-weight: 700;
}

:deep(.title-style) {
  color: #0d47a1;
  font-weight: 700;
  font-size: 20px;
}

// ✅ 這個才是真正的 v-menu 外層容器
:deep(.v-overlay__content.help-menu){
  width: 370px !important;
  min-width: 370px !important;
  max-width: 370px !important;
  overflow-x: hidden !important;   // ✅ 關掉水平捲軸
}

// ✅ 固定卡片尺寸 + 防溢出
:deep(.help-card) {
  width: 100%;
  min-height: 320px;

  display: flex;
  flex-direction: column;

  box-sizing: border-box;
  overflow: hidden; // 不要讓 footer 撐破外框

  overflow-x: hidden;
}

// ✅ 中間內容區：自動撐滿剩餘高度
.help-body{
  flex: 1;
  min-height: 0;     // 重要：讓內容可被限制高度
  overflow: auto;    // 內容太多就內部滾動，不影響 footer
  padding-right: 4px;// 避免 scrollbar 擠到字
  margin-left: 4px;

  overflow-x: hidden;   // ✅ 關鍵：把 translateX 超出的部分裁掉
  width: 100%;
}

:deep(.help-footer) {
  width: 100%;
  box-sizing: border-box;
  overflow-x: hidden;          // ✅ 不讓 footer 造成水平溢出

  display: flex;
  align-items: center;
  justify-content: center;     // ✅ 三者整組置中，不會靠右爆出去
  gap: 4px;                    // ✅ 間距
}

// ✅ 壓縮 Vuetify v-btn 的寬度/內距（scoped 必須 :deep 才打得到）
.help-btn:deep(.v-btn__content){
  white-space: nowrap;
}

.help-footer :deep(.v-btn){
  min-width: 52px !important;  // ✅ 預設通常 >= 64px，這裡再縮
  padding-inline: 6px !important;
}

// 頁碼不換行
.help-page-indicator{
  font-size: 12px;
  opacity: .75;
  white-space: nowrap;
  flex: 0 0 auto;
}

:deep(.fake-vbtn){
  display: inline-flex;
  align-items: center;
  gap: 6px;

  height: 28px;              // ✅ 固定高度
  padding: 0 10px;           // 左右內距，垂直由 height 控
  border-radius: 8px;
  box-sizing: border-box;

  font-size: 16px;
  font-weight: 400;
  font-family: 'cwTeXYen', sans-serif;

  user-select: none;
  cursor: default;          // ✅ 看起來是按鈕，但不提示可點
  white-space: nowrap;
}

// 模擬 Vuetify tonal
:deep(.fake-vbtn--tonal){
  background: rgba(63, 81, 181, .12);            // indigo 淡底
  border: 1px solid rgba(63, 81, 181, .35);
}

// 模擬 v-icon（用 mdi 字型)
:deep(.fake-vicon){
  font-size: 18px;
  line-height: 1;
  color: #1b5e20; // green-darken-3 類似色
}

:deep(.fake-vauto){
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;

  width: 110px;         // 可調整
  height: 32px;         // 看起來像 dense
  padding: 0 10px;

  border-radius: 10px;
  border: 1px solid rgba(0,0,0,.28);
  background: #fff;

  box-sizing: border-box;
  vertical-align: middle;

  user-select: none;
  cursor: default;      /* 不可點外觀 */
}

:deep(.fake-vauto__placeholder){
  flex: 1 1 auto;                  /* ✅ 撐滿 */
  min-width: 0;                    /* ✅ 才能 ellipsis */
  opacity: .7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.fake-vauto__icon){
  opacity: .7;
  flex: 0 0 auto;
  margin-left: 85px;               // ✅ 跟文字間距
}

:deep(.fake-vicon-bell) {
  display: inline-block;
  font-size: 16px;                 /* 對應 size="16" */
  line-height: 1;

  margin-left: 5px;              /* 你原本的 margin-left */
  margin-right: 8px;               /* class="mr-2" 約等於 8px */

  color: #81d4fa;                  /* light-blue lighten-3 類似色 */

  transition: opacity .3s ease, visibility .3s ease;
  opacity: 1;
  visibility: visible;

  vertical-align: text-top;
}

:deep(.employee-select .v-field input) {
  color: #1976d2 !important;
}

:deep(.employee-select .v-field input::placeholder) {
  color: #1976d2 !important;
  opacity: 1;
}
</style>
