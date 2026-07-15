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

  <!-- 待入庫 data table -->
  <v-data-table
    :headers="headers"
    :items="warehouses"
    :row-props="getRowProps"
    :search="search"
    fixed-header
    style="font-family: '微軟正黑體', sans-serif; margin-top:10px;"

    item-value="index"
    show-select
    :value="selectedItems"

    class="elevation-10 custom-table"
    :items-per-page-options="footerOptions"
    items-per-page="5"
    v-model:page="pagination.page"
    items-per-page-text="每頁的資料筆數"
  >
    <!-- 客製化 '選擇框' 欄位表頭 -->
    <template v-slot:header.data-table-select>
      <span class="custom-header">入庫</span>
    </template>

    <!-- 自定義每行的選擇框 -->
    <template v-slot:item.data-table-select="{ internalItem }">
      <v-checkbox-btn
        :model-value="isSelected(internalItem)"
        :disabled="!(internalItem.raw.allOk_qty != 0 && internalItem.raw.input_allOk_disable)"
        color="primary"
        @update:model-value="toggleSelect(internalItem)"
        :class="{ 'blue-text': internalItem.raw.input_allOk_disable }"
      />
    </template>

    <!-- 客製化 top 區域 -->
    <template v-slot:top>
      <v-card>
        <v-card-title class="warehouse-top-title">
          <!-- 第一行 -->
          <v-row align="center">
            <!-- 標題 -->
            <v-col cols="12" md="2" class="d-flex justify-start">
              <span class="warehouse-title-text">
                成品區入庫資訊
              </span>
            </v-col>
            <!-- 入庫即時紀錄查詢/入庫歷史紀錄查詢/入庫全部資料查詢 -->
            <v-col cols="12" md="4" class="d-flex justify-start" style="gap:5px;">
              <v-btn
                :disabled="1===1"
                variant="outlined"
                class="warehouse-top-btn"
                style="padding-left:5px; padding-right:5px;"
                @click="openWarehouseHistoryDialog('active')"
              >
                <v-icon start>mdi-format-list-checkbox</v-icon>
                入庫即時紀錄查詢
              </v-btn>
              <v-btn
                :disabled="1===1"
                color="blue-grey"
                variant="outlined"
                class="warehouse-top-btn"
                style="padding-left:5px; padding-right:5px;"
                @click="openArchiveHistoryDialog"
              >
                <v-icon start>mdi-database-search</v-icon>
                入庫歷史紀錄查詢
              </v-btn>

              <v-btn
                :disabled="1===1"
                variant="outlined"
                class="warehouse-top-btn"
                style="padding-left:5px; padding-right:5px;"
                @click="openWarehouseHistoryDialog('all')"
              >
                入庫全部資料查詢
              </v-btn>
            </v-col>
            <v-col cols="12" md="2"></v-col>
<!--


            <v-col cols="12" md="4" class="d-flex justify-end align-center" style="gap:5px;">
              <v-text-field
                v-model="search"
                label="資料搜尋"
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
                hide-details
                single-line

                class="warehouse-top-input"
              />
              <v-text-field
                v-model="bar_code"
                label="條碼"
                prepend-inner-icon="mdi-barcode"
                variant="outlined"
                hide-details
                single-line
                ref="barcodeInput"
                @keyup.enter="handleBarCode"

                class="warehouse-top-input warehouse-barcode-field"
              />
            </v-col>
-->

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

          <!-- 第二行 -->
          <v-row align="center">
            <v-col cols="12" md="2" class="d-flex justify-start"></v-col>
            <!-- 入庫登記 -->
            <v-col cols="12" md="4" class="d-flex justify-start">
            <!--
              <v-btn
                :disabled="c_isBlinking"
                ref="warehouseBtn"
                color="primary"
                variant="outlined"
                class="warehouse-top-btn"
                style="padding-left:5px; padding-right:5px;"
                @click="onClickWarehouseIn"
              >
                <v-icon start color="blue">
                  mdi-cart-plus
                </v-icon>
                <span>入庫登記</span>
              </v-btn>
            -->
              <AddToCartButton
                text="入庫登記"
                :disabled="c_isBlinking"
                style="padding-left:5px; padding-right:5px; position:relative; top:-2px;"
                @click="onClickWarehouseIn"
              />
            </v-col>

            <!-- 加工線已入庫封存-->
            <v-col cols="12" md="3" class="d-flex justify-start">

            </v-col>

            <!-- 組裝線已入庫封存-->
            <v-col cols="12" md="3" class="d-flex justify-start">
              <v-btn
                color="deep-purple"
                variant="outlined"
                :disabled="archiveLoading || stockinCount === 0"
                @click="archiveAllStockinAssemble"
              >
                <v-icon start>mdi-archive-arrow-down</v-icon>
                全部封存組裝線已入庫
              </v-btn>
            </v-col>
            <!-- 動畫-->
          <!--
            <v-col cols="12" md="6" class="warehouse-animation-col">
              <Transition name="warehouse-fade">
                <div
                  v-if="warehouseAnimationVisible"
                  class="warehouse-svg-wrapper"
                >
                  <WarehouseInAnimation
                    :start-x="-330"
                    :time-x="3"
                    :length-x="565"
                    :floor-x="-330"
                    :floor-width="590"
                  />
                </div>
              </Transition>
            </v-col>
          -->

          <!--測試用
            <v-col cols="12" md="6" class="d-flex justify-start">
              <AddToCartButton text="入庫登記0" @added="addCart" style="position:relative; top:-2px;" />
            </v-col>
          -->
          </v-row>
        </v-card-title>
      </v-card>
    </template>

    <!-- 客製化 '訂單數量' (req_qty) 欄位的表頭 -->
    <template v-slot:header.req_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">訂單</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '到庫數量' (delivery_qty) 欄位的表頭 -->
    <template v-slot:header.delivery_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">到庫</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 客製化 '應入庫總數量' (must_allOk_qty) 欄位的表頭 -->
    <template v-slot:header.must_allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">應入庫</div>
        <div>總數量</div>
      </div>
    </template>

    <!-- 客製化 '已入庫總數量' (total_allOk_qty) 欄位的表頭 -->
    <template v-slot:header.total_allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">已入庫</div>
        <div>總數量</div>
      </div>
    </template>

    <!-- 客製化 '入庫數量' (allOk_qty) 欄位的表頭 -->
    <template v-slot:header.allOk_qty="{ column }">
      <div style="text-align: center;">
        <div style="height:21px;">入庫</div>
        <div>數量</div>
      </div>
    </template>

    <!-- 自訂 index 欄位的資料欄位 -->
    <template v-slot:item.index="{ item }">
      <!-- 空白顯示 -->
    </template>

    <!-- 自訂 line 欄位的資料欄位 -->
    <template v-slot:item.line="{ item }">
      <span v-if="item.line == 'process'" style="color:blue; font-weight:600;">
        加工線
      </span>
      <span v-else  style="color:black; font-weight:600;">
        組裝線
      </span>
    </template>

    <!-- 自訂 '訂單編號' 欄位 -->
  <!--
    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: center;">
  -->
        <!--入庫數輸入完成-->
  <!--
        <div style="color: blue; margin-right: 20px;" v-if="item.input_allOk_disable">
          {{ item.order_num }}
        </div>
  -->
        <!--入庫數輸入尚未完成-->
  <!--
        <div style="margin-right: 20px;" v-else>
          {{ item.order_num }}
        </div>
      </div>
    </template>
  -->

    <template v-slot:item.order_num="{ item }">
      <div style="display: flex; align-items: center;">
        <div
          :style="{
            color: item.input_allOk_disable ? 'blue' : 'black',
            marginRight: '20px'
          }"
        >
          <div>{{ item.order_num }}</div>
          <!-- 加工線才顯示工序名稱 -->
          <div
            v-if="item.line === 'process'"
            style="color:#0000FF; font-size:12px; font-weight:400; line-height:1.1;"
          >
            {{ item.assemble_work }}
            <span
              v-if="item.isStockIn"
              style="color:#FF2C2C; font-weight:600;"
            >
              {{ item.isStockIn }}
            </span>
          </div>
        </div>
      </div>
    </template>

    <!-- 自訂 '說明' 欄位 -->
    <template v-slot:item.comment="{ item }">
      <div>
        <div style="
          text-align:left;
          color: #669999;
          font-size:12px;
          font-family:
          'Microsoft JhengHei',
          '微軟正黑體',
          'Noto Sans TC',
          sans-serif;
        ">
          {{ item.comment }}
        </div>
      </div>
    </template>

    <!-- 自訂 應入庫數量 欄位資料欄位 -->
    <template v-slot:item.must_allOk_qty="{ item }">
      <div style="display:flex; align-items:center; left:25px; position:relative;">
      <!--
        <v-icon
          v-if="!history"
          style="transition: opacity 0.3s ease, visibility 0.3s ease;  margin-left: -10px;"
          :style="{ opacity: (currentUser.perm == 1 || currentUser.perm == 2)  ? 1 : 0, visibility: (currentUser.perm == 1 || currentUser.perm == 2) ? 'visible' : 'hidden' }"
          @click="addAbnormalInMaterial(item)"
          size="16"
          class="mr-2"
          :color="item.Incoming2_Abnormal ? 'light-blue lighten-3':'red lighten-4'"
        >
          mdi-bell-plus
        </v-icon>
      -->
        <span style="margin-left: 15px;">
          <!--{{ item.must_allOk_qty }}-->
          {{ getRemainQty(item) }}
        </span>
      </div>
    </template>

    <!-- 自訂 '入庫數量' 輸入欄位 -->
    <template v-slot:item.allOk_qty="{ item }">
      <div style="position: relative; display: inline-block;">
        <v-text-field
          v-model="item.allOk_qty"
          dense
          hide-details
          style="max-width: 60px; text-align: center; z-index: 1;"
          :id="`allOkQtyID-${item.index}`"
          @keydown="handleKeyDown"
          @update:modelValue="(value) => { item.allOk_qty = value; checkQtyField(item); }"

          @update:focused="(focused) => checkTextEditField(focused, item)"
          @keyup.enter="updateItem2(item)"
          :disabled="item.input_allOk_disable"
          :style="{
            '--input-text-color': (item.isError || Number(item.allOk_qty) > 0) ? 'red' : 'black'
          }"
        />
        <span
          v-show="item.tooltipVisible"
          style="
            position: absolute;
            left: -200px;
            top: -15px;
            z-index: 2;
            background-color: transparent;
            padding: 0;
            min-width: 120px;
            white-space: nowrap;
            color:red;
            text-align: left;
            font-weight: 700;
            font-size: 12px;"
        >
          {{ over_qty_alarm }}
        </span>
      </div>
    <!--
      <div v-show="item.isAllOk" style=" position: relative; left: -20px; top: -5px; font-weight: 400; font-size: 10px;">
        入庫日期
      </div>
    -->
    </template>

    <!-- 自訂 data table 在沒有資料時, 畫面的顯示資訊 -->
    <template #no-data>
      <strong><span style="color: red;">目前沒有資料</span></strong>
    </template>
  </v-data-table>

  <!-- 已入庫即時紀錄 dialog -->
  <v-dialog
    v-model="historyDialog"
    max-width="100vw"
    scrollable
    content-class="warehouse-history-dialog"
  >
    <v-card class="warehouse-history-card">
      <v-card-title class="d-flex align-center justify-space-between">
        <span style="font-weight:700;">已入庫即時紀錄</span>

        <v-btn icon variant="text" @click="historyDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="warehouse-history-card-text">
        <div class="warehouse-history-table-wrap">
          <!-- 已入庫即時紀錄 data table -->
          <v-data-table
            v-model="archiveSelected"
            :headers="historyHeaders"
            :items="warehouse_history"
            item-value="archive_key"
            show-select
            return-object
            :search="historySearch"
            fixed-header
            height="calc(96vh - 120px)"
            class="elevation-3 warehouse-history-table history-table"

            :items-per-page-options="footerOptions"
            items-per-page="10"

          >

            <!-- dialog內, top 區域 -->
            <template v-slot:top>
              <div class="history-table-top">
                <!-- 搜尋框 -->
                <v-text-field
                  v-model="historySearch"
                  label="搜尋"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  hide-details
                  density="compact"
                  style="max-width:300px;"
                />

                <v-btn
                  color="deep-purple"
                  variant="flat"
                  :disabled="archiveSelected.length === 0 || archiveLoading"
                  @click="archiveDialog = true"
                >
                  <v-icon start>mdi-archive-arrow-down</v-icon>
                  封存已選資料
                </v-btn>

                <v-btn
                  color="blue-grey"
                  variant="outlined"
                  :disabled="archiveLoading"
                  @click="openArchiveBatchDialog"
                >
                  <v-icon start>mdi-history</v-icon>
                  封存批次
                </v-btn>

                <span style="color:#666; font-size:13px;">
                  已選 {{ archiveSelected.length }} 筆
                </span>
              </div>
            </template>

            <!-- 客製化 '已入庫總數量' 欄位的表頭 -->
            <template v-slot:header.total_allOk_qty="{ column }">
              <div
                style="
                  text-align:left;
                  line-height:1;
                  margin:0;
                  padding:0;
                  padding-left:0;
                  margin-left:0;
                "
              >
                <div style="margin:0; padding:0;">已入庫</div>
                <div style="margin:0; padding:0;">總數量</div>
              </div>
            </template>

            <!-- 自訂 封存 checkbox 表頭：全選 -->
            <template v-slot:header.data-table-select="{ allSelected, selectAll, someSelected }">
              <v-checkbox-btn
                :indeterminate="someSelected && !allSelected"
                :model-value="allSelected"
                color="deep-purple"
                @update:model-value="selectAll(!allSelected)"
              />
            </template>
          <!--
            <template v-slot:item.archive_select="{ item }">
              <v-checkbox-btn
                :model-value="isArchiveSelected(item)"
                color="deep-purple"
                @update:model-value="toggleArchiveSelected(item)"
              />
            </template>
          -->

            <!-- 自訂 line 欄位的資料欄位 -->
            <template v-slot:item.line="{ item }">
              <span v-if="item.line == 'process'" style="color:blue; font-weight:600;">
                加工線
              </span>
              <span v-else  style="color:black; font-weight:600;">
                組裝線
              </span>
            </template>

            <!-- 自訂 訂單編號 欄位的資料欄位 -->
            <template #item.order_num="{ item }">
              <span style="color:#1565c0; font-weight:700; white-space:normal; word-break:break-word;">
                {{ item?.order_num }}
              </span>
            </template>

            <!-- 自訂 入庫日期 欄位 -->
            <template #item.write_date="{ item }">
              <span>
                {{ String(item?.write_date || '').slice(0, 10) }}
              </span>
            </template>

            <template #no-data>
              <strong><span style="color:red;">目前沒有已入庫資料</span></strong>
            </template>
          </v-data-table>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- 確認封存 dialog -->
  <v-dialog v-model="archiveDialog" max-width="420">
    <v-card>
      <v-card-title style="font-weight:700;">
        確認封存
      </v-card-title>

      <v-card-text>
        確定要封存已選的
        <strong style="color:red;">{{ archiveSelected.length }}</strong>
        筆入庫歷史資料？
        <br />
        <span style="color:#666;">
          封存後會從正式資料表移到 archive 資料表。
        </span>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn variant="text" @click="archiveDialog = false">
          取消
        </v-btn>

        <v-btn
          color="deep-purple"
          variant="flat"
          :loading="archiveLoading"
          @click="confirmArchiveWarehouseOrders"
        >
          確定封存
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- 封存批次紀錄 dialog -->
  <v-dialog v-model="archiveBatchDialog" max-width="900">
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <span style="font-weight:700;">封存批次紀錄</span>

        <v-btn icon variant="text" @click="archiveBatchDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <!-- data table -->
        <v-data-table
          :headers="archiveBatchHeaders"
          :items="archiveBatches"
          fixed-header
          height="500"
          items-per-page="10"
        >
          <template v-slot:item.restored_at="{ item }">
            <span v-if="item.restored_at" style="color:green; font-weight:700;">
              {{ item.restored_at }}
            </span>
            <span v-else style="color:#999;">
              尚未還原
            </span>
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              size="small"
              color="orange"
              variant="flat"
              :disabled="!!item.restored_at"
              @click="confirmRestoreArchiveBatch(item)"
            >
              還原
            </v-btn>
          </template>

          <template #no-data>
            <strong><span style="color:red;">目前沒有封存批次</span></strong>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- 入庫歷史紀錄查詢 dialog -->
  <v-dialog
    v-model="archiveHistoryDialog"
    max-width="100vw"
    scrollable
  >
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <span style="font-weight:700;">入庫歷史紀錄查詢</span>

        <v-btn icon variant="text" @click="archiveHistoryDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
          <v-text-field
            v-model="archiveHistorySearch"
            label="搜尋訂單 / 物料 / 說明 / 批號"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            hide-details
            density="compact"
            style="max-width:360px;"
            @keyup.enter="reloadArchiveHistory"
          />

          <v-select
            v-model="archiveHistorySource"
            :items="archiveHistorySourceItems"
            label="查詢範圍"
            variant="outlined"
            hide-details
            density="compact"
            style="max-width:160px;"
            @update:model-value="reloadArchiveHistory"
          />

          <v-btn
            color="primary"
            variant="flat"
            :loading="archiveHistoryLoading"
            @click="reloadArchiveHistory"
          >
            <v-icon start>mdi-refresh</v-icon>
            查詢
          </v-btn>

          <v-btn
            color="orange"
            variant="flat"
            :disabled="restoreSelected.length === 0 || archiveHistoryLoading"
            @click="restoreConfirmDialog = true"
          >
            <v-icon start>mdi-restore</v-icon>
            還原已選資料
          </v-btn>

          <span style="color:#666; font-size:13px;">
            已選 {{ restoreSelected.length }} 筆
          </span>
        </div>

        <!-- 入庫歷史紀錄 data table -->
        <v-data-table
          :headers="archiveHistoryHeaders"
          :items="archiveHistoryRows"
          :loading="archiveHistoryLoading"
          fixed-header
          height="68vh"
          items-per-page="10"
          class="elevation-1"
        >

          <!--kk 客製化 '入庫數量' (total_allOk_qty) 欄位的表頭 -->
          <template v-slot:header.total_allOk_qty="{ column }">
            <div style="text-align:left;">
              <div style="height:21px;">入庫</div>
              <div>數量</div>
            </div>
          </template>

          <!--kk 客製化 '封存人員' (archived_by) 欄位的表頭 -->
          <template v-slot:header.archived_by="{ column }">
            <div style="text-align: center;">
              <div style="height:21px;">封存</div>
              <div>人員</div>
            </div>
          </template>

          <!--kk 客製化 '還原時間' (restored_at) 欄位的表頭 -->
          <template v-slot:header.restored_at="{ column }">
            <div style="text-align: center;">
              <div style="height:21px;">還原</div>
              <div>時間</div>
            </div>
          </template>

          <template v-slot:item.restore_select="{ item }">
            <v-checkbox-btn
              :model-value="isRestoreSelected(item)"
              :disabled="!(item.raw || item).can_restore"
              color="orange"
              @update:model-value="toggleRestoreSelected(item)"
            />
          </template>

          <template v-slot:item.line_name="{ item }">
            <v-chip
              size="small"
              :color="(item.raw || item).line === 'process' ? 'indigo' : 'green'"
              variant="flat"
            >
              {{ (item.raw || item).line_name }}
            </v-chip>
          </template>

          <!--kk 客製化 '還原時間' (restored_at) 欄位 -->
          <template v-slot:item.restored_at="{ item }">
            <span
              v-if="(item.raw || item).restored_at"
              style="color:green; font-weight:700;"
            >
              {{ (item.raw || item).restored_at }}
            </span>

            <span v-else style="color:#999;">
              尚未還原
            </span>
          </template>

          <template #no-data>
            <strong>
              <span style="color:red;">查無入庫歷史封存資料</span>
            </strong>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- 確認還原 dialog -->
  <v-dialog v-model="restoreConfirmDialog" max-width="430">
    <v-card>
      <v-card-title style="font-weight:700;">
        確認還原
      </v-card-title>

      <v-card-text>
        確定要還原已選的
        <strong style="color:red;">{{ restoreSelected.length }}</strong>
        筆入庫歷史資料？
        <br />
        <span style="color:#666;">
          還原後資料會回到正式資料表，封存表會保留紀錄並標記還原時間。
        </span>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn variant="text" @click="restoreConfirmDialog = false">
          取消
        </v-btn>

        <v-btn
          color="orange"
          variant="flat"
          :loading="archiveHistoryLoading"
          @click="confirmRestoreSelectedRows"
        >
          確定還原
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onMounted, onUnmounted, onBeforeMount, onBeforeUnmount, nextTick } from 'vue';

import LedLights from './LedLights.vue';
import DraggablePanel from './DraggablePanel.vue';
import WarehouseInAnimation from './WarehouseInAnimation.vue';
import AddToCartButton from './AddToCartButton.vue'

import warehouseSvg from '../assets/warehouseIn.svg'

import ConfirmDialog from "./confirmDialog";

import draggable from 'vuedraggable'
import { useRoute } from 'vue-router';

import { useRouter } from 'vue-router';
const router = useRouter();

import { myMixin } from '../mixins/common.js';
import { useSocketio } from '../mixins/SocketioService.js';

import { desserts2 }  from '../mixins/crud.js';
import { materials, boms, currentBoms, currentAGV, material_copy_id ,socket_server_ip, fileCount }  from '../mixins/crud.js';
import { warehouses, warehouse_history }  from '../mixins/crud.js';

import { setupGetBomsWatcher }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';

// 使用 apiOperation 函式來建立 API 請求
const readAllExcelFiles = apiOperation('get', '/readAllExcelFiles');
const deleteAssemblesWithNegativeGoodQty = apiOperation('get', '/deleteAssemblesWithNegativeGoodQty');
const countExcelFiles = apiOperation('get', '/countExcelFiles');

const listUsers2 = apiOperation('get', '/listUsers2');
const listProducts = apiOperation('get', '/listProducts');

const updateMaterial = apiOperation('post', '/updateMaterial');
const updateAssemble = apiOperation('post', '/updateAssemble');
const updateAGV = apiOperation('post', '/updateAGV');
const getWarehouseForAssembleByHistory = apiOperation('post', '/getWarehouseForAssembleByHistory');
const getWarehouseHistory = apiOperation('post', '/getWarehouseHistory');
const createProcess = apiOperation('post', '/createProcess');
const createProduct = apiOperation('post', '/createProduct');

const archiveWarehouseOrders = apiOperation('post', '/archiveWarehouseOrders');
const restoreWarehouseOrders = apiOperation('post', '/restoreWarehouseOrders');
const listArchiveBatches = apiOperation('post', '/listArchiveBatches');
const listWarehouseArchiveHistory = apiOperation('post', '/listWarehouseArchiveHistory');
const restoreWarehouseArchiveRows = apiOperation('post', '/restoreWarehouseArchiveRows');

const archiveAllStockinAssembleMaterials = apiOperation('post', '/archiveAllStockinAssembleMaterials');

//=== p_tables維護用 api ==
import { p_apiOperation }  from '../mixins/p_crud.js';

const createProcessP = p_apiOperation('post', '/createProcessP');
const createProductP = p_apiOperation('post', '/createProductP');
const updateAssembleP = p_apiOperation('post', '/updateAssembleP');
const updateMaterialP = p_apiOperation('post', '/updateMaterialP');

//=== component name ==
defineComponent({ name: 'WarehouseForAssemble' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===

const stockinCount = ref(0);

// 入庫對話框相關
const endTitle = ref('準備入庫');
const endMessage = ref('確定？');
const confirmRef = ref(null);

const warehouseAnimationVisible = ref(false);
//const warehouseAnimationVisible = ref(true);
const start_x = ref(-120);   // 起始位置(px)
const time_x = ref(10);       // 移動時間(秒)
const length_x = ref(820);   // 移動距離(px)

const warehouseBtn = ref(null)
const animationLeft = ref(0)

const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const panelX = ref(810);
const panelY = ref(11);
const activeColor = ref('green')  // 預設亮綠燈, 區域閒置
const panel_flag = ref(false)     // 允許拖曳的開關

const screenSizeInInches = ref(null);

const bar_code = ref('');
const barcodeInput = ref(null);

const editDialogBtnDisable = ref(true);

const fromDateMenu = ref(false);              // 日期menu 打開/關閉

const fromDateVal = ref('');

//# let intervalId = null;                        // 10分鐘, 倒數計時器

const route = useRoute();                     // Initialize router

const footerOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: -1, title: '全部' }
];

const headers = [
  { title: '  ', sortable: false, key: 'index', width: 0, class: 'hidden-column' },
  { title: '  ', sortable: false, key: 'line', width:80 },
  { title: '訂單編號', sortable: true, key: 'order_num', width:150 },
  { title: '物料編號', sortable: true, key: 'material_num', width:110 },
  { title: '訂單數量', sortable: false, key: 'req_qty', width:80 },
  { title: '說明', align: 'start', sortable: false, key: 'comment', width:320 },
  { title: '交期', align: 'center', sortable: false, key: 'date', width:120 },
  { title: '到庫數量', sortable: false, key: 'delivery_qty', width:80 },
  { title: '應入庫總數量', align: 'center', sortable: false, key: 'must_allOk_qty', width:90 },
  { title: '已入庫總數量', sortable: false, key: 'total_allOk_qty', width:90 },

  { title: '入庫數量', sortable: false, key: 'allOk_qty', width:80 },
];

const search = ref('');

const history = ref(false);

const historyDialog = ref(false);
const historySearch = ref('');

const archiveDialog = ref(false);
const archiveBatchDialog = ref(false);
const archiveBatches = ref([]);
const archiveLoading = ref(false);
const archiveSelected = ref([]);

const historyHeaders = [
  //{ title: '封存', sortable: false, key: 'archive_select', width: 48 },
  { title: '產線', sortable: false, key: 'line', width:60 },
  { title: '訂單編號', sortable: false, key: 'order_num', width:110 },
  { title: '物料編號', sortable: false, key: 'material_num', width: 110 },
  { title: '說明', sortable: false, key: 'comment', width: 200 },
  { title: '交期', sortable: false, key: 'date', width: 80 },
  { title: '已入庫總數量', sortable: false, key: 'total_allOk_qty', width: 50 },
  { title: '入庫人', sortable: false, key: 'user_id', width: 60 },
  { title: '入庫日期', sortable: false, key: 'write_date', width: 200 },
];

const archiveBatchHeaders = [
  { title: '封存批號', sortable: false, key: 'archive_batch_no', width: 180 },
  { title: '封存時間', sortable: false, key: 'archived_at', width: 160 },
  { title: '封存人員', sortable: false, key: 'archived_by', width: 100 },
  { title: '組裝線筆數', sortable: false, key: 'normal_count', width: 90 },
  { title: '加工線筆數', sortable: false, key: 'process_count', width: 90 },
  { title: '總筆數', sortable: false, key: 'total_count', width: 80 },
  { title: '還原時間', sortable: false, key: 'restored_at', width: 160 },
  { title: '操作', sortable: false, key: 'actions', width: 100 },
];

const archiveHistoryDialog = ref(false);
const archiveHistoryLoading = ref(false);
const archiveHistorySearch = ref('');
const archiveHistorySource = ref('not_restored');
const archiveHistoryRows = ref([]);
const restoreSelected = ref([]);
const restoreConfirmDialog = ref(false);

const archiveSelectedWarehouseRows = ref([]);
const restoreDialog = ref(false);

const archiveHistorySourceItems = [
  { title: '尚未還原', value: 'not_restored' },
  { title: '已還原', value: 'restored' },
  { title: '全部', value: 'all' },
];

const archiveHistoryHeaders = [
  { title: '還原', key: 'restore_select', sortable: false, width: 60 },
  { title: '序', key: 'index', sortable: false, width: 60 },
  { title: '產線', key: 'line_name', sortable: false, width: 90 },
  { title: '封存批號', key: 'archive_batch_no', sortable: false, width: 170 },
  { title: '訂單編號', key: 'order_num', sortable: false, width: 150 },
  { title: '物料編號', key: 'material_num', sortable: false, width: 160 },
  { title: '說明', key: 'comment', sortable: false, width: 260 },
  { title: '入庫數量', key: 'total_allOk_qty', sortable: false, width: 100 },
  { title: '封存時間', key: 'archived_at', sortable: false, width: 160 },
  { title: '封存人員', key: 'archived_by', sortable: false, width: 100 },
  { title: '還原時間', key: 'restored_at', sortable: false, width: 160 },
];

const selectedItems = ref([]); // 儲存選擇的項目 (基於 id)

const app_user = 'user_chumpower';
const clientAppName = 'WarehouseForAssemble';

const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, app_user, clientAppName);

const over_qty_alarm = ref('');

const currentUser = ref({});
const componentKey = ref(0)       // key 值用於強制重新渲染

const pagination = reactive({
  itemsPerPage: 5,                // 預設值, rows/per page
  page: 1
});

const abnormalDialogBtnDisable = ref(true);
const abnormalDialog = ref(false);
const abnormalDialog_order_num = ref('');
const abnormalDialog_delivery_qty = ref('');
const abnormalDialog_must_receive_qty = ref('');
const abnormalDialog_new_must_receive_qty = ref('');
const abnormalDialog_message = ref('');
const abnormalDialog_display = ref(true);

const abnormalDialog_record = ref(null);

//=== watch ===
setupGetBomsWatcher();

// 監視 selectedItems 的變化，並將其儲存到 localStorage
watch(selectedItems, (newItems) => {
  console.log("watch(), newItems:", newItems)
  localStorage.setItem('selectedItems', JSON.stringify(newItems));
  },
  { deep: true }
);

// 監視 history 的變化，並將其儲存到 localStorage
watch(history, (newItems) => {
  console.log("watch(), newItems:", newItems)
  localStorage.setItem('history', JSON.stringify(newItems));
  },
  { deep: true }
);

// 當輸入滿 12 碼，就自動處理條碼
watch(bar_code, (newVal) => {
  if (newVal.length === 12) {
    handleBarCode();
  }
})

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

const containerStyle = computed(() => ({
bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

// 顯示格式化日期
const formattedDate = computed(() => {
return fromDateVal.value ? fromDateVal.value.toISOString().split('T')[0] : ''; // 自動格式化
});

const isAllArchiveSelected = computed(() => {
  return warehouse_history.value.length > 0 &&
    archiveSelected.value.length === warehouse_history.value.length
})

const isSomeArchiveSelected = computed(() => {
  return archiveSelected.value.length > 0 &&
    archiveSelected.value.length < warehouse_history.value.length
})

const toggleArchiveSelectAll = (checked) => {
  archiveSelected.value = checked ? [...warehouse_history.value] : []
}
//=== mounted ===
onMounted(async () => {
  console.log("MaterialListForAssem.vue, mounted()...");

  //+++
  const dpi = window.devicePixelRatio;
  const widthInPx = screen.width;
  const heightInPx = screen.height;

  // 實驗推估：假設密度為 96 DPI（一般桌機）
  //const dpiEstimate = 96 * dpi;
  const dpiEstimate = 96;

  const widthInInches = widthInPx / dpiEstimate;
  const heightInInches = heightInPx / dpiEstimate;

  const diagonalInches = Math.sqrt(
    widthInInches ** 2 + heightInInches ** 2
  ).toFixed(1);

  screenSizeInInches.value = diagonalInches;

  console.log(`估算螢幕尺寸約為：${diagonalInches} 吋`);

  if (screenSizeInInches.value != null) {
    panelX.value = screenSizeInInches.value > 20 ? 1290 : 810;
    panelY.value = screenSizeInInches.value > 20 ? 11 : 11;
  }
  //+++

  // 阻止直接後退，但保留 Vue Router 的 state
  window.history.replaceState(window.history.state, '', document.URL);
  window.addEventListener('popstate', handlePopState);

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

  if (currentUser.value?.empID) {
  //if (currentUser.value) {
    currentUser.value.setting_items_per_page = pagination.itemsPerPage;
    currentUser.value.setting_lastRoutingName = routeName.value;

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }

  console.log("currentUser:", currentUser.value);
  //

  // 從 localStorage 中恢復 selectedItems
  let savedItems = localStorage.getItem('selectedItems');
  if (savedItems) {
    selectedItems.value = JSON.parse(savedItems);
  }

  // 從 localStorage 中恢復 history
  savedItems = localStorage.getItem('history');
  if (savedItems) {
    history.value = JSON.parse(savedItems);
  }

  updateAnimationPosition()

  window.addEventListener('resize', updateAnimationPosition)

  // 自動 focus
  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }

  //處理socket連線
  console.log('等待socket連線...');
  try {
    await setupSocketConnection();

    socket.value.on('station3_loading_ready', async(data) => {

      activeColor.value='yellow';  // 物料進站
    });

    socket.value.on('station3_agv_begin', async () => {
      activeColor.value='SeaGreen';     // 物料出站
    })

    socket.value.on('station1_agv_end', async (data) => {
      activeColor.value='DarkOrange';   // 物料送達組裝區
    })

    socket.value.on('station3_agv_ready', async () => {
      activeColor.value='blue';         // 機器人進入成品區
    })

    socket.value.on('triggerLogout', async (data) => {
      console.log("收到 triggerLogout 強迫登出訊息，empID:", data.empID, "目前 empID:", currentUser.value.empID);

      if (data.empID && data.empID === currentUser.value.empID) {
        console.log("本裝置符合 empID，執行強制登出流程");

        let payload = {
          itemsPerPage: 0,
          seeIsOk: '0',
          lastRoutingName: 'Main',
          empID: userData.empID,
        };

        try {
          await updateSetting(payload);
        } finally {
          localStorage.setItem('Authenticated', false);
          removelocalStorage();

          const resolvedRoute = router.resolve({ name: 'LoginRegister' });
          const path = resolvedRoute.href;
          console.log('triggerLogout socket...', path)
          router.replace({ path });
        }
      } else {
        console.log("本裝置 empID 不符，忽略此 triggerLogout");
      }
    });

    socket.value?.on('warehouse-stock-in', onHandleWarehouseStockIn);
    socket.value?.on('assemble-delivered-callForklift', onHandleWarehouseStockIn);
    socket.value?.on('assemble-delivered-callAGV', onHandleWarehouseStockIn);

  } catch (error) {
    console.error('Socket連線失敗:', error);
  }
});

//=== mounted ===
onBeforeUnmount(() => {

  socket.value?.off('warehouse-stock-in', onHandleWarehouseStockIn);
  socket.value?.off('assemble-delivered-callForklift', onHandleWarehouseStockIn);
  socket.value?.off('assemble-delivered-callAGV', onHandleWarehouseStockIn);

})

//=== unmounted ===
onUnmounted(() => {   // 清除計時器（當元件卸載時
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('resize', updateAnimationPosition)
});

//=== created ===
onBeforeMount(() => {
console.log("Employer, created()...")

pagination.itemsPerPage = currentUser.value.setting_items_per_page;

initAxios();
initialize();
});

//=== method ===

// 剩餘應入庫量
const getRemainQty = (row) => {
  const delivery = Number(row.delivery_qty) || 0;          // 到庫數量
  const stocked  = Number(row.total_allOk_qty) || 0;       // 已入庫總數量
  return Math.max(0, delivery - stocked);                  // 剩餘應入庫量
};

const setActive2 = async (value) => {
  history.value = value;       // 設置當前活動按鈕

  if (history.value) {
    await toggleHistory();
  } else {
    await getWarehouseForAssembleByHistoryFun();
  }
}

const initialize = async () => {
  try {
    console.log("initialize()...");

    // 使用 async/await 等待 API 請求完成，確保順序正確
    //await listWarehouseForAssemble();
    await getWarehouseForAssembleByHistoryFun();

    await listUsers2();

    await setActive2(false);
  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

const handlePopState = () => {
  // 重新把這一筆 entry 的 state 改回 Router 給的 state
  window.history.replaceState(window.history.state, '', document.URL);

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const handleBarCode = () => {
  if (bar_code.value.length !== 12) {
    console.warn('條碼長度不正確')
    return
  }

  console.log('處理條碼：', bar_code.value)
  let myBarcode = materials_and_assembles_by_user.value.find(m => m.order_num == bar_code.value);

  // 在這裡做條碼比對、查詢、上傳等邏輯
  if (myBarcode) {
    console.log('找到條碼對應項目:', myBarcode.id);

    // focus到對應項目的欄位
    focusItemField(myBarcode);
  } else {
    showSnackbar('找不到對應條碼資料！', 'red accent-2');
    console.warn('找不到對應條碼資料!')
  }
}

const toggleHistory = async () => {
  const myData = await listProducts();

  const items = Array.isArray(myData?.items)
  ? myData.items
  : Array.isArray(myData)                         // 萬一你的 listProducts 直接回傳 array
    ? myData
    : [];

  warehouses.value = items;
};

const getWarehouseForAssembleByHistoryFun = async () => {
  let payload = {
    history_flag: history.value,
  };
  await getWarehouseForAssembleByHistory(payload);
  //
  const items = Array.isArray(warehouses.value)
  ? warehouses.value
  : [];

  warehouses.value = items.map(row => ({
    ...row,
    allOk_qty: 0,              // 進畫面時一律顯示 0，讓使用者自行輸入
    tooltipVisible: false,
    isError: false,
  }));
  //
}

const getRowProps = (item, index) => {
  // 偶數列與奇數列高度不同
  const backgroundColor = item.index % 2 === 0 ? '#ffffff' : '#edf2f4';

  return { style: { backgroundColor, }, };
};

// 定義一個延遲函數
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const checkQtyField = (item) => {
  // 將輸入值轉換為數字，並確保是有效的數字，否則設為 0

  const mustQty  = Number(item.must_allOk_qty) || 0;  // 應入庫數量
  const maxQty = Number(item.delivery_qty) || 0;      // 到庫數量
  const inputQty = Number(item.allOk_qty) || 0;       // 入庫數量（目前輸入）
  const total_allOk_qty = Number(item.total_allOk_qty) || 0;

  // 檢查是否超過需求數量
  //if ((inputQty + total_allOk_qty) > mustQty) {
  if ((inputQty + total_allOk_qty) > maxQty) {
    over_qty_alarm.value = '入庫數量與已入庫總數量的和太大!';
    item.tooltipVisible = true;

    setTimeout(() => {
      item.tooltipVisible = false;    // 3秒後隱藏 Tooltip
    }, 3000);
  } else {
    item.tooltipVisible = false;
    item.isError = false;
    over_qty_alarm.value = '';        // 清除警告
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

  // 檢查輸入的長度是否超過5，及輸入數字小於10000, 阻止多餘的輸入
  if (inputValue.length > 5 && inputValue < 10000) {
    event.preventDefault();
    return;
  }

  // 偵測是否按下 Enter 鍵
  if (event.key === 'Enter' || event.keyCode === 13) {
    console.log('Return key pressed');
    // 如果需要，這裡可以執行其他操作，或進行額外的驗證
  }

  editDialogBtnDisable.value = false;
};

const isSelected = (item) => {
  // 安全檢查，確保 item 和 item.columns 存在
  if (!item || !item.columns || typeof item.columns.index === 'undefined') {
    return false; // 預設未被選中
  }

  return selectedItems.value.includes(item.columns.index); // 根據 columns.id 檢查是否被選中
};

const toggleSelect = (item) => {
  console.log("1.selectedItems.value:",selectedItems.value)

  const index = selectedItems.value.indexOf(item.columns.index);
  if (index === -1) {
    selectedItems.value.push(item.columns.index); // 若未選中，則添加 columns.id
  } else {
    selectedItems.value.splice(index, 1);         // 若已選中，則移除 columns.id
  }
  console.log("2.selectedItems.value:",selectedItems.value)
};

const checkTextEditField = (focused, item) => {
  if (!focused) {
    console.log("checkTextEditField(): 失去焦點");
  } else {
    console.log("checkTextEditField(): 獲得焦點");
  }
};

const addAbnormalInMaterial = (item) => {
  console.log("addAbnormalInMaterial(),", item);

  abnormalDialog_record.value = warehouses.value.find(m => m.index == item.index);

  abnormalDialogBtnDisable.value = true;
  abnormalDialog_order_num.value = item.order_num;
  abnormalDialog_delivery_qty.value = item.delivery_qty;
  abnormalDialog_new_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_must_receive_qty.value = item.must_allOk_qty;
  abnormalDialog_display.value = item.Incoming2_Abnormal;

  abnormalDialog.value = true;
}

const pick = (line, normalFn, processFn) => (line === 'process' ? processFn : normalFn)

const updateItem2 = async (item) => {
  console.log("updateItem2(),", item);

  let allOk_qty = 0;

  // 檢查是否輸入了空白或 0
  if (!item.allOk_qty || Number(item.allOk_qty) === 0) {
    //allOk_qty = Number(item.delivery_qty) || 0;
    allOk_qty = getRemainQty(item);   // 改用剩餘應入庫量
  } else {
    allOk_qty = Number(item.allOk_qty) || 0;
  }

  const targetIndex = warehouses.value.findIndex((kk) => kk.index === item.index);

  let current_assemble_id = warehouses.value[targetIndex].assemble_id
  let current_material_id = warehouses.value[targetIndex].id

  const updateAssem = pick(item.line, updateAssemble, updateAssembleP)
  const updateMat   = pick(item.line, updateMaterial, updateMaterialP)

  let payload = {};
  payload = {
    assemble_id: current_assemble_id,
    record_name: 'input_allOk_disable',
    record_data: true,
  };
  await updateAssem(payload)

  payload = {
    assemble_id: current_assemble_id,
    record_name: 'allOk_qty',
    record_data: allOk_qty,
  };
  await updateAssem(payload);

  payload = {
    id: current_material_id,
    record_name: 'show2_ok',
    record_data: 7             // 設為 7，入庫進行中
  };
  await updateMat(payload);

  payload = {
    id: current_material_id,
    record_name: 'show3_ok',
    record_data: 7             // 設為 7，入庫進行中
  };
  await updateMat(payload);

  // 用 Vue 的方式確保觸發響應式更新
  warehouses.value[targetIndex] = {
    ...warehouses.value[targetIndex],
    allOk_qty: allOk_qty,
    isError: true,                    // 輸入數值正確後，重置 數字 為 紅色
    input_allOk_disable: true,
  };

  if (barcodeInput.value) {
    barcodeInput.value.focus();
  }
};

/*
const calculatePeriodTime = (start, end) => {     // 計算兩個時間之間的間隔，並以 hh:mm:ss 格式返回
  const diffMs = end - start;                     // 差異時間（毫秒）
  const diffSeconds = Math.floor(diffMs / 1000);  // 轉換為秒

  const hours = Math.floor(diffSeconds / 3600);
  const minutes = Math.floor((diffSeconds % 3600) / 60);
  const seconds = diffSeconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};
*/
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

/*
const onClickWarehouseIn = async () => {
  console.log("onClickWarehouseIn...")

  const selectedIds = Array.isArray(selectedItems.value) ? [...new Set(selectedItems.value)] : [];

  if (selectedIds.length === 0) {
    showSnackbar('請選擇入庫的工單!', 'red accent-2');
    return;
  }

  try {
    let successCount = 0;

    for (const id of selectedIds) {
      const targetIndex = warehouses.value.findIndex((kk) => kk.index === id);
      if (targetIndex === -1) continue;

      const row = warehouses.value[targetIndex];

      const current_material_id = row.id;
      const current_assemble_id = row.assemble_id;

      const current_process_id = row.process_id;

      // ✅ 1) 應入庫良品數（已扣掉 abnormal_qty）
      //    優先：must_receive_end_qty / total_ask_qty_end
      const current_must_qty = Number(
        row.must_receive_end_qty ?? row.total_ask_qty_end ?? row.must_allOk_qty ?? 0
      );

      // 已入庫總數
      const current_total_qty = Number(row.total_allOk_qty ?? 0);

      const current_line = String(row.line || '').trim().toLowerCase(); // 'process' / 'assemble'
      const updateAssem = pick(current_line, updateAssemble, updateAssembleP);
      const updateMat   = pick(current_line, updateMaterial, updateMaterialP);

      // ✅ 2) 本次入庫量 d2：沒輸入或為 0 → 預設用到庫數量
      let d2 = 0;
      if (!row.allOk_qty || Number(row.allOk_qty) === 0) {
        //d2 = Number(row.delivery_qty) || 0;
        d2 = getRemainQty(row);
      } else {
        d2 = Number(row.allOk_qty) || 0;
      }

      // qty=0 不允許
      if (d2 <= 0) {
        showSnackbar('入庫數量不可為 0', 'red accent-2');
        continue;
      }

      // ✅ 3) 用良品 must 計算差額（允許分批入庫）
      const new_total = current_total_qty + d2;
      const is_done = (current_must_qty > 0) ? (new_total >= current_must_qty) : false;

      console.log("[WAREHOUSE] must=", current_must_qty, "old_total=", current_total_qty, "d2=", d2, "new_total=", new_total, "done=", is_done);

      // ======================================
      // A) 先寫入庫流程：建立 process(31) + product
      // ======================================
      const nowStr = formatDateTime(new Date());
      const createProc = (current_line === 'process') ? createProcessP : createProcess;
      const createProd = (current_line === 'process') ? createProductP : createProduct;

      const productPayload = {
        material_id: current_material_id,
        assemble_id: current_assemble_id,
        process_id: current_process_id,
        user_id: currentUser.value?.empID ?? '',
        line_difference: (current_line === 'process') ? 1 : 0,

        // ✅ 不送 process_id，讓後端 createProductP 自己補 31
        // process_id: 0,

        allOk_qty: d2,
        good_qty: d2,
        non_good_qty: 0,
        delivery_qty: Number(row.delivery_qty) || 0,
        assemble_qty: 0,
      };
      await createProd(productPayload);

      // ======================================
      // B) 更新 Assemble / Material 狀態
      // ======================================

      // 先把本次入庫量寫回 assemble.allOk_qty（供你畫面/報表用）
      await updateAssem({
        assemble_id: current_assemble_id,
        record_name: 'allOk_qty',
        record_data: d2,
      });

      // 未完成：保持可入庫（不要鎖住）
      if (!is_done) {
        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: false,
        });

        // 更新前端：累計加上去、清空輸入框
        warehouses.value[targetIndex] = {
          ...warehouses.value[targetIndex],
          total_allOk_qty: new_total,
          allOk_qty: 0,
          input_allOk_disable: false,
        };

        // ✅ 分批入庫時不要 continue/不要移除，保留讓你下次再入庫
        continue;
      }

      // ✅ 完成：才標記入庫完成 / isStockIn，並讓等待清單不再顯示
      await updateMat({
        id: current_material_id,
        record_name: 'show2_ok',
        record_data: current_line === 'process' ? 8 : 12,
      });
      await updateMat({
        id: current_material_id,
        record_name: 'show3_ok',
        record_data: current_line === 'process' ? 8 : 13,
      });

      await updateAssem({
        assemble_id: current_assemble_id,
        record_name: 'input_allOk_disable',
        record_data: true,
      });
      await updateAssem({
        assemble_id: current_assemble_id,
        record_name: 'isWarehouseStationShow',
        record_data: true,
      });
      await updateAssem({
        assemble_id: current_assemble_id,
        record_name: 'isStockIn',
        record_data: true,
      });

      // 更新前端並移除該筆（完成就不該再出現在等待清單）
      warehouses.value.splice(targetIndex, 1);

      successCount++;
    }


    // 成功至少一筆才更新 AGV 狀態（在成品區、ready）
    if (successCount > 0) {
      await updateAGV({
        id: 1,
        status: 0,        // ready
        station: 3,       // 在成品區
      });
    }

    await delay(3000);    // 延遲 3 秒

    // 清理選取與歷史
    selectedItems.value = [];
    if (localStorage.getItem('selectedItems'))
      localStorage.removeItem('selectedItems');

    history.value = false;
    if (localStorage.getItem('history'))
      localStorage.removeItem('history');
  } catch (err) {
    console.error('入庫流程發生例外：', err);
    showSnackbar('入庫流程執行失敗，請稍後再試', 'red accent-2');
  }
  //待待
  //window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
};
*/

const updateAnimationPosition = () => {
  if (!warehouseBtn.value?.$el)
    return

  const rect = warehouseBtn.value.$el.getBoundingClientRect();

  animationLeft.value = rect.right + 10;
}

// 20260709版
const onClickWarehouseIn = async () => {

  updateAnimationPosition();

  console.log("onClickWarehouseIn...");

  const selectedIds = Array.isArray(selectedItems.value)
    ? [...new Set(selectedItems.value)]
    : [];

  if (selectedIds.length === 0) {
    showSnackbar('請選擇入庫的工單!', 'red accent-2');
    return;
  }

  warehouseAnimationVisible.value = true;

  try {
    let successCount = 0;

    for (const id of selectedIds) {
      const targetIndex = warehouses.value.findIndex((kk) => kk.index === id);
      if (targetIndex === -1) continue;

      const row = warehouses.value[targetIndex];

      const current_material_id = row.id;
      const current_assemble_id = row.assemble_id;
      const current_process_id = row.process_id;

      const current_must_qty = Number(
        row.must_receive_end_qty ?? row.total_ask_qty_end ?? row.must_allOk_qty ?? 0
      );

      const current_total_qty = Number(row.total_allOk_qty ?? 0);

      const current_line = String(row.line || '').trim().toLowerCase();
      const updateAssem = pick(current_line, updateAssemble, updateAssembleP);
      const updateMat   = pick(current_line, updateMaterial, updateMaterialP);
      const createProd  = (current_line === 'process') ? createProductP : createProduct;

      let d2 = 0;

      if (!row.allOk_qty || Number(row.allOk_qty) === 0) {
        d2 = getRemainQty(row);
      } else {
        d2 = Number(row.allOk_qty) || 0;
      }

      if (d2 <= 0) {
        showSnackbar('入庫數量不可為 0', 'red accent-2');
        continue;
      }

      console.log("已入庫, 數量:", d2)

      const new_total = current_total_qty + d2;
      const is_done = (current_must_qty > 0) ? (new_total >= current_must_qty) : false;

      console.log("[WAREHOUSE] must=", current_must_qty, "old_total=", current_total_qty, "d2=", d2, "new_total=", new_total, "done=", is_done);

      const productPayload = {
        material_id: current_material_id,
        assemble_id: current_assemble_id,
        process_id: current_process_id,
        user_id: currentUser.value?.empID ?? '',
        line_difference: (current_line === 'process') ? 1 : 0,
        allOk_qty: d2,
        good_qty: d2,
        non_good_qty: 0,
        delivery_qty: Number(row.delivery_qty) || 0,
        assemble_qty: 0,
      };

      const resp = await createProd(productPayload);
      if (!resp?.status) {
        throw new Error(resp?.error || 'createProduct/createProductP failed');
      }

      // 前端同步更新本次輸入值
      await updateAssem({
        assemble_id: current_assemble_id,
        record_name: 'allOk_qty',
        //record_data: d2,
        record_data: new_total,
      });

      if (!is_done) {
        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: false,
        });
      /*
      } else {
        await updateMat({
          id: current_material_id,
          record_name: 'show2_ok',
          record_data: current_line === 'process' ? 8 : 12,
        });

        await updateMat({
          id: current_material_id,
          record_name: 'show3_ok',
          record_data: current_line === 'process' ? 8 : 13,
        });

        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: true,
        });

        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'isWarehouseStationShow',
          //record_data: true,
          record_data: false,
        });

        if (current_line === 'process') {
          await updateAssem({
            assemble_id: current_assemble_id,
            record_name: 'isStockIn',
            record_data: true,
          });
        }
      }
      */
      //
      } else {
        // ------------------------------------------------------------
        // 入庫完成：material 狀態補完整，避免 Information 還顯示組裝已結束
        // ------------------------------------------------------------
        if (current_line === 'assemble') {
          await updateMat({
            id: current_material_id,
            record_name: 'show1_ok',
            record_data: 3,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'show2_ok',
            record_data: 12,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'show3_ok',
            record_data: 13,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'whichStation',
            record_data: 3,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'isAssembleStationShow',
            record_data: false,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'isAssembleStation3TakeOk',
            record_data: true,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'isAllOk',
            record_data: true,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'allOk_qty',
            //record_data: d2,
            record_data: new_total,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'total_allOk_qty',
            record_data: new_total,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'material_stockin_date',
            record_data: formatDateTime(new Date()),
          });
        } else {
          await updateMat({
            id: current_material_id,
            record_name: 'show2_ok',
            record_data: 8,
          });

          await updateMat({
            id: current_material_id,
            record_name: 'show3_ok',
            record_data: 8,
          });
        }

        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'input_allOk_disable',
          record_data: true,
        });

        await updateAssem({
          assemble_id: current_assemble_id,
          record_name: 'isWarehouseStationShow',
          record_data: false,
        });

        if (current_line === 'process') {
          await updateAssem({
            assemble_id: current_assemble_id,
            record_name: 'isStockIn',
            record_data: true,
          });
        }
      }
      //

      successCount++;
    }
    // end for loop

    if (successCount > 0) {
      await updateAGV({
        id: 1,
        status: 0,
        station: 3,
      });
    }

    await delay(500);

    selectedItems.value = [];
    if (localStorage.getItem('selectedItems')) {
      localStorage.removeItem('selectedItems');
    }

    history.value = false;
    if (localStorage.getItem('history')) {
      localStorage.removeItem('history');
    }

    // ✅ 關鍵：入庫後直接重抓，不靠前端手動 splice
    await getWarehouseForAssembleByHistoryFun();

    socket.value?.emit('warehouse-stock-in', {
      reason: 'stockin',
      source: 'WarehouseForAssemble',
    })

    showSnackbar('入庫登記完成!', 'green accent-3');
  } catch (err) {
    console.error('入庫流程發生例外：', err);
    showSnackbar('入庫流程執行失敗，請稍後再試', 'red accent-2');
  } finally {
    setTimeout(() => {
      warehouseAnimationVisible.value = false;
    }, 800);
  }
};

// 改變拖曳功能
//const toggleDrag = () => {
//  panel_flag.value = !panel_flag.value
//}

// 控制面板樣式，包括邊框顏色和層級 (z-index)
//const panelStyle = computed(() => ({
//  cursor: panel_flag.value ? 'move' : 'default',
//  border: panel_flag.value ? '2px solid blue' : '2px solid transparent',
//  zIndex: panel_flag.value ? 9999 : 1, // 當可拖曳時，將面板提升至最上層
//}))

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};

const openWarehouseHistoryDialog = async (source = 'active') => {
  try {
    // 清空之前勾選
    clearArchiveSelected();

    await getWarehouseHistory({
      source, // active / archive / all
    });

    normalizeWarehouseHistoryRows();

    historyDialog.value = true;
  } catch (err) {
    console.error('openWarehouseHistoryDialog error:', err);
    showSnackbar('入庫紀錄查詢失敗', 'error');
  }
};

// ===
const archiveKeyOf = (row) => {
  return `${row.line || 'assemble'}:${row.id}`;
};

const isArchiveSelected = (item) => {
  const row = item.raw || item;
  const key = archiveKeyOf(row);

  return archiveSelected.value.some(x => archiveKeyOf(x) === key);
};

const toggleArchiveSelected = (item) => {
  const row = item.raw || item;
  const key = archiveKeyOf(row);

  const index = archiveSelected.value.findIndex(x => archiveKeyOf(x) === key);

  if (index >= 0) {
    archiveSelected.value.splice(index, 1);
  } else {
    archiveSelected.value.push({
      id: row.id,
      material_id: row.id,
      order_num: row.order_num,
      material_num: row.material_num,
      line: row.line || 'assemble',
      total_allOk_qty: row.total_allOk_qty,
      delivery_qty: row.delivery_qty,
      assemble_id: row.assemble_id,
    });
  }
};

const clearArchiveSelected = () => {
  archiveSelected.value = [];
};

/*
const confirmArchiveWarehouseOrders = async () => {
  if (archiveSelected.value.length === 0) {
    showSnackbar('請先選擇要封存的入庫歷史資料!', 'red accent-2');
    return;
  }

  archiveLoading.value = true;

  try {
    const payload = {
      rows: archiveSelected.value,
      archived_by: currentUser.value?.emp_id || currentUser.value?.emp_name || 'system',
    };

    const res = await archiveWarehouseOrders(payload);

    if (res && res.success === false) {
      showSnackbar(res.error || '封存失敗', 'red accent-2');
      return;
    }

    showSnackbar(`封存完成，批號：${res?.archive_batch_no || ''}`, 'green');

    archiveDialog.value = false;
    clearArchiveSelected();

    await getWarehouseHistoryFun();

  } catch (error) {
    console.error('confirmArchiveWarehouseOrders ERROR:', error);
    showSnackbar('封存失敗，請查看 console / 後端 log', 'red accent-2');
  } finally {
    archiveLoading.value = false;
  }
};
*/
const confirmArchiveWarehouseOrders = async () => {
  if (archiveSelected.value.length === 0) {
    showSnackbar('請先選擇要封存的已入庫即時資料!', 'red accent-2');
    return;
  }

  archiveLoading.value = true;

  try {
    const payload = {
      rows: archiveSelected.value.map(x => ({
        id: x.id,

        // 後端用 line 判斷要刪 material 還是 p_material
        line:
          x.line ||
          x.line_key ||
          x.work_line ||
          (
            String(x.source_table || '').includes('加工') ||
            String(x.source || '').includes('加工') ||
            String(x.table_name || '').includes('p_')
              ? 'process'
              : 'assemble'
          ),
      })),

      archived_by:
        currentUser.value?.emp_id ||
        currentUser.value?.emp_name ||
        'system',
    };

    console.log('archiveWarehouseOrders payload:', payload);

    const res = await archiveWarehouseOrders(payload);

    if (res && res.success === false) {
      showSnackbar(res.error || '封存失敗', 'red accent-2');
      return;
    }

    showSnackbar(`封存完成，批號：${res?.archive_batch_no || ''}`, 'green');

    archiveDialog.value = false;
    clearArchiveSelected();

    await getWarehouseHistoryFun();

  } catch (error) {
    console.error('confirmArchiveWarehouseOrders ERROR:', error);
    showSnackbar('封存失敗，請查看 console / 後端 log', 'red accent-2');
  } finally {
    archiveLoading.value = false;
  }
};

const getWarehouseHistoryFun = async () => {
  try {
    await getWarehouseHistory({});

    normalizeWarehouseHistoryRows();

    const items = Array.isArray(warehouse_history.value)
      ? warehouse_history.value
      : [];

    warehouse_history.value = items.map((row, idx) => ({
      ...row,
      index: idx + 1,
      line: row.line || 'assemble',
    }));

  } catch (error) {
    console.error('getWarehouseHistoryFun ERROR:', error);
    showSnackbar('讀取入庫歷史失敗', 'red accent-2');
  }
};

const normalizeWarehouseHistoryRows = () => {
  console.log('warehouse_history:', warehouse_history.value)

  const items = Array.isArray(warehouse_history.value)
    ? warehouse_history.value
    : []

  warehouse_history.value = items.map((row, idx) => {
    const line = row.line || 'assemble'
    const id = row.id || row.material_id || row.assemble_id || row.p_material_id

    return {
      ...row,
      id,
      index: idx + 1,
      line,
      archive_key: `${line}-${id || row.order_num}-${row.write_date || idx}`,
    }
  })
}

const openArchiveBatchDialog = async () => {
  archiveBatchDialog.value = true;
  await reloadArchiveBatches();
};

const reloadArchiveBatches = async () => {
  archiveLoading.value = true;

  try {
    const res = await listArchiveBatches({});

    if (res && res.success === false) {
      showSnackbar(res.error || '讀取封存批次失敗', 'red accent-2');
      archiveBatches.value = [];
      return;
    }

    archiveBatches.value = Array.isArray(res?.data) ? res.data : [];

  } catch (error) {
    console.error('reloadArchiveBatches ERROR:', error);
    showSnackbar('讀取封存批次失敗', 'red accent-2');
  } finally {
    archiveLoading.value = false;
  }
};

const confirmRestoreArchiveBatch = async (item) => {
  const ok = window.confirm(`確定還原封存批次？\n${item.archive_batch_no}`);

  if (!ok) return;

  archiveLoading.value = true;

  try {
    const payload = {
      archive_batch_no: item.archive_batch_no,
      restored_by: currentUser.value?.emp_id || currentUser.value?.emp_name || 'system',
    };

    const res = await restoreWarehouseOrders(payload);

    if (res && res.success === false) {
      showSnackbar(res.error || '還原失敗', 'red accent-2');
      return;
    }

    showSnackbar('還原完成', 'green');

    await reloadArchiveBatches();
    await getWarehouseHistoryFun();

  } catch (error) {
    console.error('confirmRestoreArchiveBatch ERROR:', error);
    showSnackbar('還原失敗，請查看 console / 後端 log', 'red accent-2');
  } finally {
    archiveLoading.value = false;
  }
};

const restoreKeyOf = (row) => {
  return `${row.line || 'assemble'}:${row.archive_batch_no}:${row.id}`;
};

const isRestoreSelected = (item) => {
  const row = item.raw || item;
  const key = restoreKeyOf(row);

  return restoreSelected.value.some(x => restoreKeyOf(x) === key);
};

const toggleRestoreSelected = (item) => {
  const row = item.raw || item;

  if (!row.can_restore) {
    showSnackbar('此資料已還原，不能重複選取!', 'red accent-2');
    return;
  }

  const key = restoreKeyOf(row);
  const idx = restoreSelected.value.findIndex(x => restoreKeyOf(x) === key);

  if (idx >= 0) {
    restoreSelected.value.splice(idx, 1);
  } else {
    restoreSelected.value.push({
      id: row.id,
      material_id: row.material_id || row.id,
      line: row.line || 'assemble',
      archive_batch_no: row.archive_batch_no,
      order_num: row.order_num,
      material_num: row.material_num,
    });
  }
};

const clearRestoreSelected = () => {
  restoreSelected.value = [];
};

const openArchiveHistoryDialog = async () => {
  archiveHistoryDialog.value = true;
  clearRestoreSelected();
  await reloadArchiveHistory();
};

const reloadArchiveHistory = async () => {
  archiveHistoryLoading.value = true;

  try {
    const res = await listWarehouseArchiveHistory({
      source: archiveHistorySource.value,
      keyword: archiveHistorySearch.value,
    });

    if (res && res.success === false) {
      showSnackbar(res.error || '讀取入庫歷史封存資料失敗', 'red accent-2');
      archiveHistoryRows.value = [];
      return;
    }

    archiveHistoryRows.value = Array.isArray(res?.data)
      ? res.data
      : [];

    clearRestoreSelected();

  } catch (error) {
    console.error('reloadArchiveHistory ERROR:', error);
    showSnackbar('讀取入庫歷史封存資料失敗', 'red accent-2');
  } finally {
    archiveHistoryLoading.value = false;
  }
};

const confirmRestoreSelectedRows = async () => {
  if (restoreSelected.value.length === 0) {
    showSnackbar('請先選擇要還原的資料!', 'red accent-2');
    return;
  }

  archiveHistoryLoading.value = true;

  try {
    const res = await restoreWarehouseArchiveRows({
      rows: restoreSelected.value,
      restored_by: currentUser.value?.emp_id || currentUser.value?.emp_name || 'system',
    });

    if (res && res.success === false) {
      showSnackbar(res.error || '還原失敗', 'red accent-2');
      return;
    }

    showSnackbar('還原完成', 'green');

    restoreConfirmDialog.value = false;
    clearRestoreSelected();

    await reloadArchiveHistory();

    // 如果你的入庫待處理表也要同步刷新，可打開這行
    // await loadWarehouses();

  } catch (error) {
    console.error('confirmRestoreSelectedRows ERROR:', error);
    showSnackbar('還原失敗，請查看 console / 後端 log', 'red accent-2');
  } finally {
    archiveHistoryLoading.value = false;
  }
};

const openRestoreDialog = () => {
  if (archiveSelectedWarehouseRows.value.length === 0) {
    showSnackbar('請先選擇要還原的資料!', 'red accent-2');
    return;
  }

  restoreDialog.value = true;
};

const addCart = () => {
  console.log('入庫完成')
}

const archiveAllStockinAssemble = async () => {
  try {
    const res = await archiveAllStockinAssembleMaterials({
      archived_by: currentUser.value?.empID || 'system',
    })

    if (res.success) {
      showSnackbar(`組裝線已入庫資料已全部封存，共 ${res.count} 筆`, 'success')

      await getStockinCount()
      await getWarehouseHistory({ source: 'active' })
      normalizeWarehouseHistoryRows()
    } else {
      showSnackbar(res.error || '全部封存失敗', 'error')
    }
  } catch (err) {
    console.error('archiveAllStockinAssemble ERROR:', err)
    showSnackbar('全部封存失敗', 'error')
  }
}

const getStockinCount = async () => {
  try {
    const res = await getInformationStatusCounts()

    if (res.data?.success) {
      stockinCount.value = res.data.stockin_count || 0
    } else {
      stockinCount.value = 0
    }
  } catch (err) {
    console.error('getStockinCount ERROR:', err)
    stockinCount.value = 0
  }
}
/*
const onHandleWarehouseStockIn = async (payload) => {
  console.log("[Warehouse refresh]", payload)

  history.value = false

  await delay(300)
  await getWarehouseForAssembleByHistoryFun()
}
*/
const onHandleWarehouseStockIn = async (payload) => {
  console.log("[Warehouse refresh]", payload)

  history.value = false

  await delay(500)
  await getWarehouseForAssembleByHistoryFun()

  await delay(1000)
  await getWarehouseForAssembleByHistoryFun()
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
  top:10px;
  position: relative;
  font-size: 24px;
  font-weight: 600;
  font-family:
  "Microsoft JhengHei",
  "微軟正黑體",
  "Noto Sans TC",
  sans-serif;
  //font-family: 'cwTeXYen', sans-serif;
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
  border-radius:5px !important;
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
  width: fit-content;     // 可調整寬度以適應按鈕

  right: 100px;
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
  margin-right:10px;
  background: #eee;
  padding:5px;
  width: 143px;
  min-height: 1.5em;
  font-size: 0.85em;
}

.facet-list li {
  margin:5px;
  padding:5px;
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

/*
:deep(i.mdi-barcode) {
  color: #000000;
  font-weight: 600;
  font-size: 36px;
  position: relative;
  left: 15px;
}
*/

//.v-input--horizontal .v-input__prepend {
.custom-bordered-row {
  border: 2px solid #0D47A1; /* 設定邊框寬度與顏色 */
  border-radius: 8px;        /* 可選: 為邊框添加圓角 */
  padding: 16px;
}

.hidden-column {
  display: none;
}

:deep(.top_find_field .v-input__control) {
  position: relative;
  left: 50px;
  top:10px;
}

:deep(.v-table__wrapper > table > thead th:nth-child(3)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(3)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(4)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(4)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(5)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(5)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(6)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(6)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > thead th:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(7)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(8)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(9)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}
:deep(.v-table__wrapper > table > thead th:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.v-table__wrapper > table > tbody td:nth-child(10)) {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

:deep(.warehouse-history-dialog) {
  height: 96vh !important;
  max-height: 96vh !important;
}

:deep(.warehouse-history-dialog .v-overlay__content) {
  height: 96vh !important;
  max-height: 96vh !important;
}

.warehouse-history-card {
  height: 96vh !important;
  max-height: 96vh !important;
  display: flex;
  flex-direction: column;
}

//.warehouse-history-card-text {
//  flex: 1;
//  overflow: hidden;
//  padding-bottom: 0;
//}

.warehouse-top-title {
  font-weight: 700;
  padding: 16px;
  padding-bottom: 0px;
  //padding-top: 0px;
}

.warehouse-title-text {
  font-size: 22px;
  font-weight: 700;
}

.warehouse-top-btn {
  height: 40px;
  font-weight: 700;
  white-space: nowrap;
}

.warehouse-top-input {
  max-width: 320px;
}

.warehouse-top-input :deep(.v-field) {
  height: 22px !important;
}

.warehouse-top-input :deep(.v-field__input) {
  min-height: 22px !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  align-items: center;
}

//===
//.warehouse-history-table-wrap {
//  width: 100%;
//  max-width: 100%;
//  overflow-x: auto !important;
//}

//.warehouse-history-table {
//  min-width: 1300px;
//}

//.warehouse-history-table :deep(.v-table__wrapper) {
//  overflow-x: auto !important;
//}

.warehouse-history-table :deep(table) {
  min-width: 1300px !important;
  table-layout: fixed !important;
}
//===
:deep(.warehouse-history-table .v-table__wrapper > table > thead > tr > th.v-data-table__th) {
  background-color: #85aef2;
}

//&&

.warehouse-svg {
  width: 300px;
  height: 80px;
  display: block;
  overflow: visible;
  background: transparent;
}

.fade-enter-active,
.fade-leave-active {
  transition: all .3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.warehouse-svg-wrapper {
  width: 300px;
  height: 80px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: visible;
}

.warehouse-svg {
  width: 300px;
  height: 80px;
  display: block;
  overflow: visible;
}

/* 淡入淡出 */
.warehouse-fade-enter-active {
  transition: opacity 0.8s ease, transform 0.8s ease;
}

.warehouse-fade-leave-active {
  transition: opacity 1.2s ease, transform 1.2s ease;
}

.warehouse-fade-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.85);
}

.warehouse-fade-enter-to {
  opacity: 1;
  transform: translateX(0) scale(1);
}

.warehouse-fade-leave-from {
  opacity: 1;
  transform: translateX(0) scale(1);
}

.warehouse-fade-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.85);
}

.warehouse-animation-col {
  position: relative;
  height: 80px;
  overflow: visible;
}

.warehouse-svg-wrapper {
  position: absolute;

  margin-left: -280px;

  top: 50%;

  transform: translateY(-50%);

  width: 300px;

  height: 80px;

  pointer-events: none;

  z-index: 10;

  overflow: visible;
}

.warehouse-svg {
  width: 300px;

  height: 80px;

  display: block;
}

/* 淡入淡出 */

.warehouse-fade-enter-active {
  transition:
    opacity 0.6s ease,
    transform 0.6s ease;
}

.warehouse-fade-leave-active {
  transition:
    opacity 1s ease,
    transform 1s ease;
}

.warehouse-fade-enter-from {
  opacity: 0;

  transform:
    translateY(-50%)
    translateX(80px)
    scale(0.85);
}

.warehouse-fade-enter-to {
  opacity: 1;

  transform:
    translateY(-50%)
    translateX(0)
    scale(1);
}

.warehouse-fade-leave-from {
  opacity: 1;

  transform:
    translateY(-50%)
    translateX(0)
    scale(1);
}

.warehouse-fade-leave-to {
  opacity: 0;

  transform:
    translateY(-50%)
    translateX(80px)
    scale(0.85);
}

.warehouse-barcode-field {
  min-width: 160px;
}

.warehouse-barcode-field :deep(.v-field__input) {
  min-height: 40px;
  padding-top: 0;
  padding-bottom: 0;
}
//
/*
.warehouse-barcode-field :deep(.v-field__prepend-inner) {
  padding-inline-start: 8px !important;
  padding-inline-end: 4px !important;
  align-items: center !important;
}

.warehouse-barcode-field :deep(.mdi-barcode) {
  font-size: 22px !important;
  position: static !important;
  left: auto !important;
  color: #000 !important;
}

.warehouse-barcode-field :deep(.v-field__input) {
  padding-inline-start: 4px !important;
}
*/

.history-table {
  overflow-x: hidden;
}

.history-table-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  max-width: 100%;
  overflow-x: hidden;
}

//.warehouse-history-table-wrap {
//  width: 100%;
//  max-width: 100%;
//  overflow-x: hidden;
//}

//.warehouse-history-table :deep(.v-table__wrapper) {
//  overflow-x: hidden !important;
//}

//==
.warehouse-history-table-wrap {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

.warehouse-history-table {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box;
}

.warehouse-history-table :deep(.v-table__wrapper) {
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: hidden !important;
}

.warehouse-history-card-text {
  overflow-x: hidden;
}

.toolbar-row {
  display: flex;
  align-items: center;

  flex-wrap: nowrap;
  min-width: 0 !important;
  overflow-x: hidden !important;
  overflow-y: hidden !important;
  gap: 16px;
}

.toolbar-row .v-col {
  min-width: 0 !important;
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

.barcode-input :deep(.v-field__input) {
  padding-left: 12px;
}

.barcode-input :deep(.v-label) {
  margin-left: 30px;
}

</style>
