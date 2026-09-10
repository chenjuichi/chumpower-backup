import os
import time
import datetime

from datetime import datetime

from flask import Blueprint, jsonify, request

import traceback

from sqlalchemy import inspect, and_, or_, func
from sqlalchemy.orm import joinedload

from database.tables import Session

from database.p_tables import (
  P_Material,
  P_Assemble,
  P_Process,
  P_Product,
  P_Part,
)

from .helper import normalize_create_at

updateTableP = Blueprint('updateTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


# 20260909版
# 20260822版
# 20260818版
@updateTableP.route(
    '/updateAssembleProcessStepP',
    methods=['POST']
)
def update_assemble_process_step_p():
    print("updateAssembleProcessStepP....")

    data = (
        request.get_json(silent=True)
        or {}
    )

    try:
        material_id = int(
            data.get('id') or 0
        )

        assemble_id = int(
            data.get('assemble_id') or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            'status': False,
            'message':
                'id / assemble_id 格式錯誤',
        }), 400

    if (
        material_id <= 0
        or assemble_id <= 0
    ):
        return jsonify({
            'status': False,
            'message':
                '缺少 id / assemble_id',
        }), 400

    s = Session()

    try:
        # ============================================================
        # 1. 鎖定 Material
        # ============================================================
        material_record = (
            s.query(P_Material)
            .filter(
                P_Material.id ==
                material_id
            )
            .with_for_update()
            .first()
        )

        if not material_record:
            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Material：{material_id}',
            }), 404


        # ============================================================
        # 2. 鎖定目前完成的加工工序
        # ============================================================
        assemble_record = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.id ==
                assemble_id,

                P_Assemble.material_id ==
                material_id,
            )
            .with_for_update()
            .first()
        )

        if not assemble_record:
            return jsonify({
                'status': False,
                'message':
                    f'找不到 P_Assemble：{assemble_id}',
            }), 404


        # ============================================================
        # 3. 找同一批加工工序
        # ============================================================
        target_create_at = normalize_create_at(
            assemble_record.create_at
        )

        assemble_records = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id ==
                material_id,

                P_Assemble.create_at ==
                target_create_at,
            )
            .with_for_update()
            .all()
        )

        if not assemble_records:
            return jsonify({
                'status': False,
                'message':
                    '同批加工工序不存在',
            }), 404


        # ============================================================
        # 4. 工序排序
        # ============================================================
        def seq_value(row):
            try:
                return int(
                    str(
                        row.seq_num or 0
                    ).strip()
                )

            except (
                TypeError,
                ValueError,
            ):
                return 999999


        sorted_records = sorted(
            assemble_records,
            key=lambda row: (
                seq_value(row),
                int(row.id or 0),
            )
        )


        # ============================================================
        # 5. 尚未完成的加工工序
        #
        # process_step_code > 0
        # ============================================================
        unfinished_records = [
            row
            for row in sorted_records
            if int(
                row.process_step_code
                or 0
            ) > 0
        ]

        all_process_step_zero = (
            len(unfinished_records) == 0
        )

        print(
            '[updateAssembleProcessStepP]',
            {
                'material_id':
                    material_id,

                'assemble_id':
                    assemble_id,

                'all_completed':
                    all_process_step_zero,

                'unfinished_ids': [
                    int(row.id)
                    for row
                    in unfinished_records
                ],
            }
        )


        # ============================================================
        # 回傳用
        # ============================================================
        next_assemble_id = 0
        waiting_send_id = 0


        # ============================================================
        # 6A. 全部加工工序完成
        #
        # 只留下最後一道工序作為 PEnd「待送出」代表列。
        # ============================================================
        if all_process_step_zero:

            print(
                "updateAssembleProcessStepP, "
                "all_process_step_zero:",
                all_process_step_zero
            )

            now_str = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )


            # --------------------------------------------------------
            # 最後一道加工工序
            # --------------------------------------------------------
            waiting_send_row = (
                sorted_records[-1]
                if sorted_records
                else assemble_record
            )

            waiting_send_id = int(
                waiting_send_row.id or 0
            )

            print(
                "[updateAssembleProcessStepP] "
                "waiting_send_row:",
                {
                    "id":
                        waiting_send_row.id,

                    "seq_num":
                        waiting_send_row.seq_num,

                    "work_num":
                        waiting_send_row.work_num,
                }
            )


            # --------------------------------------------------------
            # Material 進入「待送出」
            # --------------------------------------------------------
            material_record.show2_ok = 5

            material_record\
                .isAssembleStation3TakeOk = True

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False


            # --------------------------------------------------------
            # 最後一道工序的完成數量
            #
            # 不可把不同加工工序的完成量相加。
            # --------------------------------------------------------
            final_completed_qty = int(
                waiting_send_row.completed_qty
                or
                waiting_send_row.total_completed_qty
                or
                waiting_send_row.total_ask_qty_end
                or 0
            )

            final_total_completed_qty = int(
                waiting_send_row.total_completed_qty
                or
                waiting_send_row.total_ask_qty_end
                or
                waiting_send_row.completed_qty
                or 0
            )


            # --------------------------------------------------------
            # 同批所有加工工序：
            #
            # 前面工序全部隱藏。
            # 最後一道才成為 PEnd 待送出代表列。
            # --------------------------------------------------------
            for row in assemble_records:

                is_waiting_send_row = (
                    int(row.id or 0)
                    ==
                    waiting_send_id
                )

                # 全部工序都已完成
                row.process_step_code = 0

                row.input_disable = True
                row.input_end_disable = True
                row.input_abnormal_disable = True

                row.isWarehouseStationShow = False

                '''
                if is_waiting_send_row:

                    # ================================================
                    # 最後一道：
                    # PEnd 待送出
                    # ================================================
                    row.show2_ok = 5

                    row.isAssembleStationShow = True

                    row.completed_qty = (
                        final_completed_qty
                    )

                    row.total_completed_qty = (
                        final_total_completed_qty
                    )
                '''
                # 20260822版
                if is_waiting_send_row:

                    row.isAssembleStationShow = True

                    # ========================================================
                    # 20260822
                    #
                    # 不要在「加工完成 / PEnd 待送出」時
                    # 強制修改 isStockIn。
                    #
                    # isStockIn 必須保留 Excel / 工序原始設定：
                    #
                    # B100-03
                    #   isStockIn=False
                    #   → 中間加工
                    #
                    # B108-26
                    #   isStockIn=True
                    #   → 最終需入庫
                    #
                    # 真正按送出時，
                    # sendProcessToWarehouse() 才依此欄位決定：
                    #
                    # False → 解鎖下一階段 PMaterial
                    # True  → Warehouse
                    # ========================================================

                    # row.isStockIn = True    # ← 刪掉 / 不可再設定

                    row.completed_qty = (
                        final_completed_qty
                    )

                    row.total_completed_qty = (
                        final_total_completed_qty
                    )

                    row.total_ask_qty_end = max(
                        int(
                            row.total_ask_qty_end
                            or 0
                        ),
                        final_completed_qty,
                        final_total_completed_qty,
                    )
                #
                    row.total_ask_qty_end = max(
                        int(
                            row.total_ask_qty_end
                            or 0
                        ),
                        final_completed_qty,
                        final_total_completed_qty,
                    )

                else:

                    # ================================================
                    # 前面已完成工序：
                    # PBegin / PEnd 都不顯示
                    # ================================================
                    row.show2_ok = 5

                    row.isAssembleStationShow = False


            # --------------------------------------------------------
            # 關閉同批殘留中的 active Process
            # --------------------------------------------------------
            assemble_ids = [
                int(row.id)
                for row in assemble_records
                if row.id is not None
            ]

            if assemble_ids:

                other_active_logs = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id ==
                        material_id
                    )
                    .filter(
                        P_Process.assemble_id.in_(
                            assemble_ids
                        )
                    )
                    .filter(
                        P_Process.has_started
                        .is_(True)
                    )
                    .filter(
                        or_(
                            P_Process.end_time
                            .is_(None),

                            P_Process.end_time ==
                            '',
                        )
                    )
                    .with_for_update()
                    .all()
                )

                for log in other_active_logs:

                    log.end_time = now_str
                    log.has_started = False
                    log.is_pause = True

                    if not log.str_elapsedActive_time:

                        seconds = int(
                            log.elapsedActive_time
                            or 0
                        )

                        hours, remain = divmod(
                            seconds,
                            3600
                        )

                        minutes, seconds = divmod(
                            remain,
                            60
                        )

                        log.str_elapsedActive_time = (
                            f"{hours:02d}:"
                            f"{minutes:02d}:"
                            f"{seconds:02d}"
                        )

            next_assemble_id = 0


        # ============================================================
        # 6B. 還有下一道加工工序
        #
        # 例如：
        #
        # B100-03 完成
        #     ↓
        # B108-26 回 PBegin
        #
        # B108-26 尚未按開始前：
        #     PBegin = 顯示
        #     PEnd   = 不顯示
        # ============================================================
        else:

            # --------------------------------------------------------
            # Material 回到「等待下一道加工」
            # --------------------------------------------------------
            material_record.show2_ok = 3

            material_record\
                .isAssembleStation3TakeOk = False

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False


            # --------------------------------------------------------
            # 目前這一道已完成
            #
            # 它只是「中間工序完成」，
            # 不能進 PEnd 待送出。
            # --------------------------------------------------------
            completed_qty = int(
                assemble_record.completed_qty
                or
                assemble_record.total_completed_qty
                or
                assemble_record.total_ask_qty_end
                or 0
            )

            if completed_qty > 0:

                assemble_record.total_completed_qty = max(
                    int(
                        assemble_record.total_completed_qty
                        or 0
                    ),
                    completed_qty
                )

                assemble_record.total_ask_qty_end = max(
                    int(
                        assemble_record.total_ask_qty_end
                        or 0
                    ),
                    completed_qty
                )


            # --------------------------------------------------------
            # 已完成的中間工序：
            #
            # PBegin 不顯示
            # PEnd   不顯示
            # --------------------------------------------------------
            assemble_record.show2_ok = 5

            assemble_record.isAssembleStationShow = False
            assemble_record.isWarehouseStationShow = False

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True


            # ========================================================
            # 找真正的下一道加工工序
            #
            # 特別排除目前剛完成的 assemble_record，
            # 避免它因資料更新時序又被自己選成 next_record。
            # ========================================================
            remaining_records = [
                row
                for row in unfinished_records
                if int(row.id or 0)
                !=
                int(assemble_record.id or 0)
            ]

            if not remaining_records:

                raise RuntimeError(
                    "all_process_step_zero=False，"
                    "但找不到下一道加工工序；"
                    f"material_id={material_id}, "
                    f"assemble_id={assemble_id}"
                )


            next_record = remaining_records[0]


            # ========================================================
            # 開放下一道加工工序
            #
            # 尚未開始：
            #
            # PBegin：顯示
            # PEnd：不顯示
            # ========================================================
            next_record.show2_ok = 3

            next_record.isAssembleStationShow = False
            next_record.isWarehouseStationShow = False

            next_record.input_disable = False
            next_record.input_end_disable = False
            next_record.input_abnormal_disable = False


            # --------------------------------------------------------
            # ★ 20260818 重要修正
            #
            # 下一道加工工序的完成量一定從 0 開始。
            #
            # 絕對不能繼承上一道：
            #
            # B100-03 completed = 2268
            #
            # 不可變成：
            #
            # B108-26 total_completed_qty = 2268
            #
            # 否則 PBegin 會誤判 B108-26 已經完成。
            # --------------------------------------------------------
            #next_record.completed_qty = 0
            #next_record.total_completed_qty = 0
            #next_record.total_ask_qty_end = 0
            #
            # 20260909版
            # ========================================================
            # 20260909
            #
            # 判斷 next_record 是否為「同一道工序的剩餘 child」
            #
            # 例如：
            #
            # parent：
            #   id = 219
            #   completed_qty = 100
            #
            # child：
            #   is_copied_from_id = 219
            #   must_receive_end_qty = 299
            #
            # 這種情況不是下一道加工工序，
            # 而是同一道工序繼續加工剩餘量。
            #
            # 因此：
            #
            # completed_qty = 0
            # total_completed_qty 必須保留 100
            # total_ask_qty_end 必須保留 100
            # ========================================================

            is_partial_child = (
                int(
                    next_record.is_copied_from_id
                    or 0
                )
                ==
                int(
                    assemble_record.id
                    or 0
                )
                and
                str(
                    next_record.work_num
                    or ''
                ).strip()
                ==
                str(
                    assemble_record.work_num
                    or ''
                ).strip()
                and
                str(
                    next_record.seq_num
                    or ''
                ).strip()
                ==
                str(
                    assemble_record.seq_num
                    or ''
                ).strip()
            )


            next_record.completed_qty = 0


            if is_partial_child:

                # 同一道工序的剩餘 child
                #
                # copyAssembleForDifferenceP 已經寫入：
                #
                # total_completed_qty = 100
                # total_ask_qty_end = 100
                #
                # 這裡不可歸零。

                next_record.total_completed_qty = max(
                    int(
                        next_record.total_completed_qty
                        or 0
                    ),
                    int(
                        assemble_record.completed_qty
                        or 0
                    ),
                )

                next_record.total_ask_qty_end = max(
                    int(
                        next_record.total_ask_qty_end
                        or 0
                    ),
                    int(
                        next_record.total_completed_qty
                        or 0
                    ),
                )

            else:

                # 真正的下一道加工工序
                #
                # 例如：
                # B100-03 → B108-26
                #
                # 完成量必須重新從 0 開始。

                next_record.total_completed_qty = 0
                next_record.total_ask_qty_end = 0
            #

            next_assemble_id = int(
                next_record.id
            )


            print(
                "[updateAssembleProcessStepP] "
                "下一道加工工序:",
                {
                    "material_id":
                        material_id,

                    "completed_assemble_id":
                        assemble_id,

                    "next_assemble_id":
                        next_record.id,

                    "seq_num":
                        next_record.seq_num,

                    "work_num":
                        next_record.work_num,

                    "process_step_code":
                        next_record.process_step_code,

                    "show2_ok":
                        next_record.show2_ok,

                    "completed_qty":
                        next_record.completed_qty,

                    "total_completed_qty":
                        next_record.total_completed_qty,

                    "total_ask_qty_end":
                        next_record.total_ask_qty_end,
                }
            )


        # ============================================================
        # 7. Commit
        # ============================================================
        s.commit()


        # ============================================================
        # 8. Response
        # ============================================================
        return jsonify({
            'status':
                all_process_step_zero,

            'all_steps_completed':
                all_process_step_zero,

            'material_id':
                material_id,

            'completed_assemble_id':
                assemble_id,

            'next_assemble_id':
                next_assemble_id,

            'waiting_send_assemble_id':
                (
                    waiting_send_id
                    if all_process_step_zero
                    else 0
                ),

            'material_show2_ok':
                int(
                    material_record.show2_ok
                    or 0
                ),
        }), 200


    except Exception as error:

        s.rollback()

        logger.exception(
            "updateAssembleProcessStepP failed"
        )

        return jsonify({
            'status': False,
            'message':
                str(error),
        }), 500


    finally:
        s.close()


# 20260824版
@updateTableP.route(
    "/updateAssembleMustReceiveQtyByMaterialIDP",
    methods=["POST"]
)
def update_assembleMustReceiveQty_by_MaterialID_p():
    print("updateAssembleMustReceiveQtyByMaterialIDP....")

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    print(
        "[updateAssembleMustReceiveQtyByMaterialIDP] request_data:",
        request_data
    )

    material_id = request_data.get(
        "material_id"
    )

    record_name = request_data.get(
        "record_name"
    )

    record_data = request_data.get(
        "record_data"
    )

    # ============================================================
    # 20260824
    #
    # 以下欄位代表 Excel 工序資料的作業數量(MEINH)，
    # PMaterial 送出流程不可透過此 API 修改。
    #
    # 例如：
    #
    # PMaterial.delivery_qty = 2000
    #
    # Excel MEINH = 540
    #
    # P_Assemble.must_receive_qty 必須保持 540。
    # ============================================================

    protected_fields = {
        "must_receive_qty",
        "must_receive_end_qty",
        "original_must_receive_end_qty",
    }

    if record_name in protected_fields:

        print(
            "[updateAssembleMustReceiveQtyByMaterialIDP] "
            "拒絕修改 MEINH 欄位:",
            {
                "material_id":
                    material_id,

                "record_name":
                    record_name,

                "record_data":
                    record_data,
            }
        )

        return jsonify({
            "status": False,
            "blocked": True,
            "msg": (
                f"{record_name} 為 Excel 工序 "
                "MEINH 保護欄位，不允許由 "
                "PMaterial 送出流程修改"
            )
        }), 400

    # ============================================================
    # 基本參數
    # ============================================================

    if not material_id:

        return jsonify({
            "status": False,
            "msg":
                "缺少 material_id"
        }), 400

    if not record_name:

        return jsonify({
            "status": False,
            "msg":
                "缺少 record_name"
        }), 400

    s = Session()

    try:

        # ========================================================
        # 檢查合法欄位
        # ========================================================

        valid_columns = [
            c.key
            for c
            in inspect(
                P_Assemble
            ).mapper.column_attrs
        ]

        if record_name not in valid_columns:

            return jsonify({
                "status": False,
                "msg":
                    (
                        f"'{record_name}' "
                        "不是 P_Assemble "
                        "表中的合法欄位"
                    )
            }), 400

        # ========================================================
        # 找 material 的所有 P_Assemble
        # ========================================================

        assemble_records = (
            s.query(
                P_Assemble
            )
            .filter(
                P_Assemble.material_id
                ==
                material_id
            )
            .all()
        )

        # ========================================================
        # 無工序加工單允許略過
        # ========================================================

        if not assemble_records:

            print(
                f"material_id={material_id} "
                "沒有 P_Assemble，略過更新。"
            )

            return jsonify({
                "status": True,
                "skipped": True,
                "updated_ids": [],
                "msg":
                    (
                        f"material_id={material_id} "
                        "沒有 P_Assemble，已略過"
                    )
            }), 200

        updated_ids = []

        # ========================================================
        # 更新一般欄位
        # ========================================================

        for record in assemble_records:

            print("[before generic update]", {
                    "id":
                        record.id,

                    "record_name":
                        record_name,

                    "old_value":
                        getattr(
                            record,
                            record_name,
                            None
                        ),

                    "new_value":
                        record_data,
                }
            )

            setattr(
                record,
                record_name,
                record_data
            )

            updated_ids.append(
                int(record.id)
            )

        s.commit()

        return jsonify({
            "status": True,
            "skipped": False,
            "updated_ids":
                updated_ids
        }), 200

    except Exception as e:

        s.rollback()

        traceback.print_exc()

        return jsonify({
            "status": False,
            "msg":
                str(e)
        }), 500

    finally:

        s.close()


@updateTableP.route("/updateAssembleP", methods=['POST'])
def update_assemble_p():
    print("updateAssembleP....")

    request_data = request.get_json()

    _assemble_id = request_data['assemble_id']
    _record_name = request_data['record_name']

    if 'record_data' not in request_data:
        return jsonify({
            'status': False,
            'message': '缺少 record_data'
        }), 400

    _record_data = request_data['record_data']

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 查找對應的記錄
    assemble_record = s.query(P_Assemble).filter_by(id = _assemble_id).first()

    #
    if not assemble_record:
        s.close()

        return jsonify({
            'status': False,
            'message': '找不到加工工序資料'
        }), 404


    if hasattr(assemble_record,  _record_name):
        # --------------------------------------------------------
        # total_ask_qty 是工單實際領取數量，
        # 不能因多位員工共同開始而重複累加。
        # --------------------------------------------------------
        if _record_name == 'total_ask_qty':
            ask_qty = int(assemble_record.ask_qty or 0)

            incoming = int(
                _record_data or 0
            )

            current_total = int(
                assemble_record.total_ask_qty
                or 0
            )

            # 一般加工列，total_ask_qty 不得超過 ask_qty。
            if ask_qty > 0:
                _record_data = min(
                    max(
                        current_total,
                        incoming
                    ),
                    ask_qty
                )
            else:
                _record_data = max(
                    current_total,
                    incoming
                )

        setattr(
            assemble_record,
            _record_name,
            _record_data
        )

        # 再做一次資料庫端保險
        if (
            int(
                assemble_record.ask_qty or 0
            ) > 0
            and
            int(
                assemble_record.total_ask_qty
                or 0
            )
            >
            int(
                assemble_record.ask_qty or 0
            )
        ):
            assemble_record.total_ask_qty = (
                assemble_record.ask_qty
            )

        s.commit()
    #

    s.close()

    return jsonify({
      'status': return_value
    })


@updateTableP.route("/updateProcessDataByMaterialIDP", methods=['POST'])
def update_process_data_by_material_id_p():
    print("updateProcessDataByMaterialIDP....")

    request_data = request.get_json()

    _material_id = request_data.get('material_id')
    _seq = request_data.get('seq')
    _record_name1 = request_data.get('record_name1')
    _record_data1 = request_data.get('record_data1')

    s = Session()

    try:
        material = s.query(P_Material).get(_material_id)
        if not material:
            return jsonify({
                'status': False,
                'msg': 'Material not found'
            })

        target_process = (s.query(P_Process).filter(
                  P_Process.material_id == _material_id,
                  P_Process.assemble_id == 0,
                  P_Process.has_started == True,
                  P_Process.begin_time != '',
                  P_Process.end_time != '',)
                  .first())

        # 確保 _seq 不超過範圍
        if not target_process:
            return jsonify({
                'status': False,
                'msg': 'seq out of range'
            })

        # 取出對應的 Process
        print("target_process:", target_process)

        # 更新欄位
        if _record_name1 and _record_data1 is not None:
            setattr(target_process, _record_name1, _record_data1)

        s.commit()

        print("target_process:", target_process)
        print(f"更新成功!")
        return_value = True
    except Exception as e:
        s.rollback()
        print("更新失敗:", str(e))
        return_value = False

    return jsonify({
      'status': return_value
    })


@updateTableP.route("/previewProcessAbnormalQtyP",  methods=["POST"])
def preview_process_abnormal_qty_p():
    print("previewProcessAbnormalQtyP....")

    data = request.get_json(silent=True) or {}

    try:
        material_id = int(data.get("material_id") or 0)
        assemble_id = int(data.get("assemble_id") or 0)
        abnormal_qty = int(data.get("abnormal_qty") or 0)
    except (
        TypeError,
        ValueError,
    ):
        return jsonify({
            "status": False,
            "message": "數量格式不正確"
        }), 400

    if material_id <= 0:
        return jsonify({
            "status": False,
            "message": "material_id 不正確"
        }), 400

    if assemble_id <= 0:
        return jsonify({
            "status": False,
            "message": "assemble_id 不正確"
        }), 400

    if abnormal_qty < 0:
        return jsonify({
            "status": False,
            "message": "廢品數量不可小於 0"
        }), 400

    s = Session()

    try:
        row = (s.query(P_Assemble)
            .filter(
                P_Assemble.id ==
                assemble_id,

                P_Assemble.material_id ==
                material_id,
            )
            .first()
        )

        if not row:
            return jsonify({
                "status": False,
                "message": "找不到加工工序資料"
            }), 404

        original_qty = int(
            getattr(
                row,
                "original_must_receive_end_qty",
                0
            )
            or row.must_receive_end_qty
            or 0
        )

        completed_qty = int(
            row.total_completed_qty
            or row.total_ask_qty_end
            or 0
        )

        if original_qty <= 0:
            return jsonify({
                "status": False,
                "message": "原始應完成數量不正確"
            }), 400

        if (
            completed_qty +
            abnormal_qty >
            original_qty
        ):
            return jsonify({
                "status": False,
                "message":
                    "已完成數量與廢品數量不可超過原始應完成數量",

                "original_qty":
                    original_qty,

                "completed_qty":
                    completed_qty,

                "abnormal_qty":
                    abnormal_qty,
            }), 400

        preview_remaining_qty = max(
            original_qty -
            completed_qty -
            abnormal_qty,
            0
        )

        return jsonify({
            "status":
                True,

            "material_id":
                material_id,

            "assemble_id":
                assemble_id,

            "original_must_receive_end_qty":
                original_qty,

            "completed_qty":
                completed_qty,

            "abnormal_qty":
                abnormal_qty,

            "preview_remaining_qty":
                preview_remaining_qty,
        }), 200

    except Exception as error:
        s.rollback()

        logger.exception(
            "previewProcessAbnormalQtyP failed"
        )

        return jsonify({
            "status": False,
            "message": str(error)
        }), 500

    finally:
        s.close()


# 20260824版
# ================================================================
# PMaterial 領料完成 / 送出後：
#
# a = PMaterial 實際領料數量 delivery_qty
#
# process_qty =
# Excel「工序」工作表的「作業數量 (MEINH)」
# 優先讀：
#   original_must_receive_end_qty
# 次選：
#   must_receive_end_qty
#
# PBegin：
#
#   領料數量     = a
#   應領取數量   = b
#
#   b = min(a, process_qty)
#
# 例如：
#
# process_qty = 540
#
# a = 500
#   → b = 500
#
# a = 540
#   → b = 540
#
# a = 2000
#   → b = 540
#
# 注意：
#
# must_receive_end_qty
# original_must_receive_end_qty
#
# 都是 Excel MEINH 原始值，不可被 delivery_qty 覆蓋。
# ================================================================
@updateTableP.route("/updateAssmbleDataByMaterialIDP", methods=["POST"])
def update_assemble_data_by_material_id_p():
    print("updateAssmbleDataByMaterialIDP....")

    request_data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    print(
        "[updateAssmbleDataByMaterialIDP] request_data:",
        request_data
    )

    # ============================================================
    # 1. Request
    # ============================================================

    material_id_raw = request_data.get(
        "material_id"
    )

    delivery_qty_raw = request_data.get(
        "delivery_qty"
    )

    record_name1 = request_data.get(
        "record_name1"
    )

    record_data1 = request_data.get(
        "record_data1"
    )

    record_name2 = request_data.get(
        "record_name2"
    )

    record_data2 = request_data.get(
        "record_data2"
    )

    record_name3 = request_data.get(
        "record_name3"
    )

    record_data3 = request_data.get(
        "record_data3"
    )

    record_name4 = request_data.get(
        "record_name4"
    )

    record_data4 = request_data.get(
        "record_data4"
    )

    # ============================================================
    # 2. 型別檢查
    # ============================================================

    try:

        material_id = int(
            material_id_raw or 0
        )

        delivery_qty = int(
            delivery_qty_raw or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return jsonify({
            "status": False,
            "message":
                "material_id / delivery_qty 格式錯誤"
        }), 400

    if material_id <= 0:

        return jsonify({
            "status": False,
            "message":
                "material_id 必須大於 0"
        }), 400

    if delivery_qty <= 0:

        return jsonify({
            "status": False,
            "message":
                "領料數量必須大於 0"
        }), 400

    s = Session()

    try:

        # ========================================================
        # 3. 鎖定 P_Material
        # ========================================================

        material = (
            s.query(P_Material)
            .filter(
                P_Material.id
                ==
                material_id
            )
            .with_for_update()
            .one_or_none()
        )

        if material is None:

            s.rollback()

            return jsonify({
                "status": False,
                "message":
                    f"找不到 P_Material id={material_id}"
            }), 404

        material_qty = int(
            material.material_qty or 0
        )

        # ========================================================
        # 4. PMaterial 領料量不可超過工單數量
        #
        # 這裡仍然是用 material_qty，
        # 不使用 MEINH 當 PMaterial 輸入上限。
        # ========================================================

        if (
            material_qty > 0
            and
            delivery_qty > material_qty
        ):

            s.rollback()

            return jsonify({
                "status": False,
                "message":
                    (
                        f"領料數量 {delivery_qty} "
                        f"不可大於訂單數量 "
                        f"{material_qty}"
                    )
            }), 400

        # ========================================================
        # 5. 保存 PMaterial 實際領料數量
        # ========================================================

        material.delivery_qty = (
            delivery_qty
        )

        # ========================================================
        # 6. 找尚未完成的 P_Assemble
        # ========================================================

        assemble_records = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id
                ==
                material_id
            )
            .filter(
                P_Assemble.process_step_code
                >
                0
            )
            .order_by(
                P_Assemble.seq_num.asc(),
                P_Assemble.id.asc()
            )
            .with_for_update()
            .all()
        )

        print(
            "[updateAssmbleDataByMaterialIDP] "
            "assemble count:",
            len(assemble_records)
        )

        if not assemble_records:

            s.rollback()

            return jsonify({
                "status": False,
                "message":
                    (
                        "找不到尚未完成的 "
                        "P_Assemble，"
                        f"material_id={material_id}"
                    )
            }), 404

        updated_ids = []

        qty_results = []

        # ========================================================
        # 7. 同步數量
        #
        # a = delivery_qty
        #
        # process_qty =
        #   original_must_receive_end_qty
        #   or must_receive_end_qty
        #
        # b = min(a, process_qty)
        # ========================================================

        for asm in assemble_records:

            # ----------------------------------------------------
            # Excel MEINH
            # ----------------------------------------------------

            process_qty = int(
                getattr(
                    asm,
                    "original_must_receive_end_qty",
                    0
                )
                or
                getattr(
                    asm,
                    "must_receive_end_qty",
                    0
                )
                or 0
            )

            # ----------------------------------------------------
            # 舊資料保護
            #
            # 理論上 process_qty 一定要有。
            # 若沒有，就暫時以 delivery_qty 避免變 0。
            # ----------------------------------------------------

            if process_qty <= 0:

                process_qty = int(
                    delivery_qty or 0
                )

                print(
                    "[WARN] MEINH 為 0，"
                    "暫以 delivery_qty 作 fallback:",
                    {
                        "material_id":
                            material_id,

                        "assemble_id":
                            asm.id,

                        "delivery_qty":
                            delivery_qty,
                    }
                )

            # ----------------------------------------------------
            # PBegin 應領取數量 b
            #
            # b = min(a, process_qty)
            # ----------------------------------------------------

            begin_must_receive_qty = min(
                int(delivery_qty or 0),
                int(process_qty or 0)
            )

            print(
                "[before qty update]",
                {
                    "material_id":
                        material_id,

                    "assemble_id":
                        asm.id,

                    "work_num":
                        asm.work_num,

                    "delivery_qty_a":
                        delivery_qty,

                    "process_qty_MEINH":
                        process_qty,

                    "old_must_receive_qty":
                        asm.must_receive_qty,

                    "must_receive_end_qty":
                        asm.must_receive_end_qty,

                    "original_must_receive_end_qty":
                        getattr(
                            asm,
                            "original_must_receive_end_qty",
                            None
                        ),
                }
            )

            # ====================================================
            # 實際領料
            # ====================================================

            asm.ask_qty = (
                delivery_qty
            )

            asm.total_ask_qty = (
                delivery_qty
            )

            # ====================================================
            # PBegin 應領取數量
            #
            # b = min(a, MEINH)
            # ====================================================

            asm.must_receive_qty = (
                begin_must_receive_qty
            )

            # ====================================================
            # 絕對不要改 Excel MEINH
            # ====================================================

            # asm.must_receive_end_qty
            #
            # asm.original_must_receive_end_qty

            # ====================================================
            # 8. 原本動態狀態欄位
            # ====================================================

            if (
                record_name1
                and
                record_data1 is not None
                and
                hasattr(
                    asm,
                    record_name1
                )
            ):

                setattr(
                    asm,
                    record_name1,
                    record_data1
                )

            if (
                record_name2
                and
                record_data2 is not None
                and
                hasattr(
                    asm,
                    record_name2
                )
            ):

                setattr(
                    asm,
                    record_name2,
                    record_data2
                )

            if (
                record_name3
                and
                record_data3 is not None
                and
                hasattr(
                    asm,
                    record_name3
                )
            ):

                setattr(
                    asm,
                    record_name3,
                    record_data3
                )

            if (
                record_name4
                and
                record_data4 is not None
                and
                hasattr(
                    asm,
                    record_name4
                )
            ):

                setattr(
                    asm,
                    record_name4,
                    record_data4
                )

            updated_ids.append(
                int(asm.id)
            )

            qty_results.append({
                "assemble_id":
                    int(asm.id),

                "work_num":
                    str(
                        asm.work_num or ""
                    ),

                "delivery_qty_a":
                    int(delivery_qty),

                "process_qty":
                    int(process_qty),

                "must_receive_qty_b":
                    int(
                        begin_must_receive_qty
                    ),
            })

            print(
                "[after qty update]",
                {
                    "assemble_id":
                        asm.id,

                    "delivery_qty_a":
                        delivery_qty,

                    "process_qty_MEINH":
                        process_qty,

                    "must_receive_qty_b":
                        asm.must_receive_qty,

                    "ask_qty":
                        asm.ask_qty,

                    "total_ask_qty":
                        asm.total_ask_qty,

                    "must_receive_end_qty":
                        asm.must_receive_end_qty,

                    "original_must_receive_end_qty":
                        getattr(
                            asm,
                            "original_must_receive_end_qty",
                            None
                        ),
                }
            )

        # ========================================================
        # 9. Commit
        # ========================================================

        s.commit()

        # ========================================================
        # 10. Commit 後確認
        # ========================================================

        check_rows = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id
                ==
                material_id
            )
            .order_by(
                P_Assemble.id.asc()
            )
            .all()
        )

        for row in check_rows:

            print("[after commit]", {
                    "id":
                        row.id,

                    "work_num":
                        row.work_num,

                    "must_receive_qty":
                        row.must_receive_qty,

                    "ask_qty":
                        row.ask_qty,

                    "total_ask_qty":
                        row.total_ask_qty,

                    "must_receive_end_qty":
                        row.must_receive_end_qty,

                    "original_must_receive_end_qty":
                        getattr(
                            row,
                            "original_must_receive_end_qty",
                            None
                        ),
                }
            )

        print("[updateAssmbleDataByMaterialIDP] OK:", {
                "material_id":
                    material_id,

                "order_num":
                    material.order_num,

                "material_qty":
                    material_qty,

                "delivery_qty":
                    delivery_qty,

                "updated_assemble_ids":
                    updated_ids,

                "qty_results":
                    qty_results,
            }
        )

        return jsonify({
            "status": True,

            "message":
                "PMaterial 領料數量同步完成",

            "material_id":
                material_id,

            "order_num":
                material.order_num,

            "delivery_qty":
                delivery_qty,

            "updated_assemble_ids":
                updated_ids,

            "qty_results":
                qty_results,
        }), 200

    except Exception as e:

        s.rollback()

        print("updateAssmbleDataByMaterialIDP Error:", repr(e))

        traceback.print_exc()

        return jsonify({
            "status": False,
            "message":
                str(e)
        }), 500

    finally:

        s.close()


# 20260908版
# 20260822版
# 20260813版
@updateTableP.route('/sendProcessToWarehouse', methods=['POST'])
def send_process_to_warehouse():
    print("sendProcessToWarehouse.")

    data = request.get_json(silent=True) or {}

    material_id = data.get('id')
    assemble_id = data.get('assemble_id')
    mode = data.get('mode', 'manual')

    user_id = str(
        data.get('user_id') or ''
    ).strip()

    try:
        process_type = int(
            data.get('process_type') or 0
        )
    except (TypeError, ValueError):
        process_type = 0

    if not material_id or not assemble_id:
        return jsonify({
            "status": False,
            "message": "缺少 id 或 assemble_id"
        }), 400

    try:
        material_id = int(material_id)
        assemble_id = int(assemble_id)
    except (TypeError, ValueError):
        return jsonify({
            "status": False,
            "message": "id / assemble_id 格式錯誤"
        }), 400

    s = Session()

    try:
        # ============================================================
        # 1. 鎖定 material
        # ============================================================
        material = (
            s.query(P_Material)
            .filter(
                P_Material.id == material_id
            )
            .with_for_update()
            .one_or_none()
        )

        row = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.id == assemble_id
            )
            .filter(
                P_Assemble.material_id == material_id
            )
            .with_for_update()
            .one_or_none()
        )

        if not material or not row:
            s.rollback()

            return jsonify({
                "status": False,
                "message":
                    "找不到 P_Material 或 P_Assemble"
            }), 404

        print(
            "[sendProcessToWarehouse]",
            {
                "material_id": material_id,
                "assemble_id": assemble_id,
                "order_num": material.order_num,
                "completed_qty":
                    int(row.completed_qty or 0),
                "total_completed_qty":
                    int(row.total_completed_qty or 0),
                "user_id": user_id,
                "process_type": process_type,
            }
        )

        # 20260822版
        completed_qty = max(
            int(row.completed_qty or 0),
            int(row.total_completed_qty or 0),
            int(row.total_ask_qty_end or 0),
        )

        if completed_qty <= 0:

            s.rollback()

            return jsonify({
                "status": False,
                "message": "此加工工序尚未完成，不能送出"
            }), 400
        #

        #
        # ============================================================
        # 20260822
        # 中間加工 / 最終加工分流
        #
        # isStockIn=False
        #   → 中間加工，例如 B100-03
        #   → 不進 Warehouse
        #   → 完成後交棒給下一個 material 的 PMaterial
        #
        # isStockIn=True
        #   → 最終加工，例如 B108-26
        #   → 送 Warehouse 等待入庫
        # ============================================================

        requires_stockin = bool(
            getattr(
                row,
                "isStockIn",
                False
            )
        )


        # ============================================================
        # 中間加工工序
        #
        # 例如：
        #
        # B100-03 / seq=50
        # isStockIn=False
        #
        # PEnd 按送出後：
        #
        #   PEnd      → 消失
        #   Warehouse → 不顯示
        #   PMaterial → 下一道 B108-26 才可開始領料
        # ============================================================

        if not requires_stockin:

            row.isAssembleStationShow = False
            row.isWarehouseStationShow = False

            # 保持原始工序屬性
            row.isStockIn = False

            row.input_disable = True
            row.input_end_disable = True
            row.input_abnormal_disable = True


            # --------------------------------------------------------
            # 前段加工已完成，
            # 但尚未到成品站。
            # --------------------------------------------------------

            material.whichStation = 2

            material.show1_ok = 2
            material.show2_ok = 5

            material.isOpen = False
            material.isOpenEmpId = ''

            material.hasStarted = False
            material.startStatus = False

            material.isAssembleStation3TakeOk = False


            s.commit()


            return jsonify({
                "status": True,

                "message":
                    "前段加工已完成，"
                    "下一階段可進行領料",

                "material_id":
                    material_id,

                "sent_assemble_id":
                    row.id,

                "handoff_to_next_material":
                    True,

                "has_remaining":
                    False,

                "completed_total":
                    completed_qty,

            }), 200
        #

        # ============================================================
        # 2. 本次只送出指定完成列
        #
        # 不可以把同 material 其他剩餘加工列一起改成 Warehouse。
        # ============================================================
        row.isAssembleStationShow = False
        row.isWarehouseStationShow = True

        # 注意：
        # 這裡只是「送到成品區等待入庫」，
        # 若你的 isStockIn 定義是真正完成入庫，
        # 建議此處應為 False。
        #
        # 目前先延續你原系統習慣。
        row.isStockIn = True

        row.input_disable = True
        row.input_end_disable = True
        row.input_abnormal_disable = True

        material.move_by_automatic_or_manual_2 = (
            True
            if mode == 'agv'
            else False
        )

        # ============================================================
        # 3. 找這次部分完成所建立的「剩餘列」
        #
        # 優先：
        #   is_copied_from_id == 本次完成 row.id
        #
        # 例如：
        #   id=68 完成 38
        #   id=70 剩餘 82
        #   id70.is_copied_from_id = 68
        # ============================================================
        remaining_row = (
            s.query(P_Assemble)
            .filter(
                P_Assemble.material_id ==
                material_id
            )
            .filter(
                P_Assemble.is_copied_from_id ==
                row.id
            )
            .filter(
                P_Assemble.process_step_code > 0
            )
            .filter(
                func.coalesce(
                    P_Assemble.must_receive_end_qty,
                    0
                ) > 0
            )
            .filter(
                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                ) == 0
            )
            .order_by(
                P_Assemble.id.desc()
            )
            .with_for_update()
            .first()
        )

        # ------------------------------------------------------------
        # 相容舊資料：
        # 若 is_copied_from_id 沒有正確建立，
        # 再找同 material 其他尚未完成列。
        # ------------------------------------------------------------
        if remaining_row is None:
            remaining_row = (
                s.query(P_Assemble)
                .filter(
                    P_Assemble.material_id ==
                    material_id
                )
                .filter(
                    P_Assemble.id != row.id
                )
                .filter(
                    P_Assemble.process_step_code > 0
                )
                .filter(
                    func.coalesce(
                        P_Assemble.must_receive_end_qty,
                        0
                    ) > 0
                )
                .filter(
                    func.coalesce(
                        P_Assemble.completed_qty,
                        0
                    ) == 0
                )
                .order_by(
                    P_Assemble.id.asc()
                )
                .with_for_update()
                .first()
            )

        # ============================================================
        # 4. 還有剩餘數量
        #
        # 例如：
        #   原始 120
        #   已完成 38
        #   剩餘 82
        #
        # 結果：
        #   38 -> Warehouse
        #   82 -> PEnd 繼續加工
        # ============================================================
        if remaining_row:

            completed_total = max(
                int(
                    row.total_completed_qty
                    or 0
                ),
                int(
                    row.completed_qty
                    or 0
                ),
            )

            print(
                "[sendProcessToWarehouse] remaining row:",
                {
                    "remaining_id":
                        remaining_row.id,
                    "remain_qty":
                        remaining_row.must_receive_end_qty,
                    "completed_total":
                        completed_total,
                }
            )

            # --------------------------------------------------------
            # Material 仍留在加工站
            # --------------------------------------------------------
            material.whichStation = 2

            material.show1_ok = 2
            material.show2_ok = 4

            material.show3_ok = str(
                remaining_row.process_step_code
                or 0
            )

            material.isAssembleStation3TakeOk = False

            material.isOpen = False
            material.isOpenEmpId = ''

            # 有新的 active process 時會再設 True
            material.hasStarted = False
            material.startStatus = False

            # --------------------------------------------------------
            # 剩餘列：
            #
            # 本次完成數量 = 0
            # 累計已完成量 = 38
            # --------------------------------------------------------
            remaining_row.completed_qty = 0

            remaining_row.total_completed_qty = max(
                int(
                    remaining_row.total_completed_qty
                    or 0
                ),
                completed_total
            )

            remaining_row.total_ask_qty_end = max(
                int(
                    remaining_row.total_ask_qty_end
                    or 0
                ),
                completed_total
            )

            # 剩餘列可繼續輸入
            remaining_row.input_disable = False
            remaining_row.input_end_disable = False
            remaining_row.input_abnormal_disable = False

            # active Process 顯示於 PEnd，
            # 所以這裡不用設成待送出。
            #remaining_row.isAssembleStationShow = False
            #remaining_row.isWarehouseStationShow = False
            #
            #remaining_row.isStockIn = False
            #
            # 20260908版
            # active Process 顯示於 PEnd，
            # 所以這裡不用設成待送出。
            remaining_row.isAssembleStationShow = False
            remaining_row.isWarehouseStationShow = False

            # 20260908
            # 剩餘加工列必須保留原工序的入庫屬性。
            #
            # Excel 作業短文若以 Z 開頭：
            #   原 row.isStockIn = True
            #   remaining row 也必須維持 True
            #
            # 否則分批完成後，下一批在 PEnd 會誤顯示「不入庫」。
            remaining_row.isStockIn = row.isStockIn
            #

            # --------------------------------------------------------
            # 5. 建立剩餘列的 active P_Process
            #
            # 讓 PEnd：
            #   完成數量=0 enable
            #   Timer 繼續計時
            # --------------------------------------------------------
            if (
                user_id
                and process_type > 0
            ):
                existing_active = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id ==
                        material_id
                    )
                    .filter(
                        P_Process.assemble_id ==
                        remaining_row.id
                    )
                    .filter(
                        P_Process.process_type ==
                        process_type
                    )
                    .filter(
                        P_Process.user_id ==
                        user_id
                    )
                    .filter(
                        P_Process.has_started.is_(
                            True
                        )
                    )
                    .filter(
                        or_(
                            P_Process.end_time.is_(
                                None
                            ),
                            P_Process.end_time == ''
                        )
                    )
                    .order_by(
                        P_Process.id.desc()
                    )
                    .first()
                )

                if not existing_active:
                    now_str = (
                        datetime.now()
                        .strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

                    new_process = P_Process(
                        material_id=material_id,

                        assemble_id=
                            remaining_row.id,

                        has_started=True,

                        user_id=user_id,

                        process_type=
                            process_type,

                        begin_time=
                            now_str,

                        end_time=None,

                        period_time='',

                        elapsedActive_time=0,

                        str_elapsedActive_time=
                            '00:00:00',

                        is_pause=False,

                        pause_started_at=None,

                        process_work_time_qty=0,

                        normal_work_time=0,
                    )

                    s.add(new_process)
                    s.flush()

                    print(
                        "[sendProcessToWarehouse] "
                        "new remaining active process:",
                        {
                            "process_id":
                                new_process.id,
                            "assemble_id":
                                remaining_row.id,
                            "user_id":
                                user_id,
                            "process_type":
                                process_type,
                        }
                    )

                # Material 有進行中的加工
                material.hasStarted = True
                material.startStatus = True

            else:
                print(
                    "[sendProcessToWarehouse] "
                    "WARNING: remaining row exists, "
                    "but user_id/process_type missing:",
                    {
                        "user_id":
                            user_id,
                        "process_type":
                            process_type,
                    }
                )

            message = (
                "本批已送到成品區，"
                "剩餘加工數量已重新開放"
            )

        # ============================================================
        # 6. 沒有剩餘數量
        #
        # 只有這種情況才能整張 Material 進成品區。
        # ============================================================
        else:
            material.whichStation = 3

            material.show1_ok = 3
            material.show2_ok = 6
            material.show3_ok = 11

            material.isOpen = False
            material.isOpenEmpId = ''
            material.hasStarted = False
            material.startStatus = False

            message = (
                "加工件已全部送到成品區，"
                "可在 Warehouse 顯示"
            )

        # ============================================================
        # 7. Commit
        # ============================================================
        s.commit()

        return jsonify({
            "status": True,
            "message": message,

            "material_id":
                material_id,

            "sent_assemble_id":
                row.id,

            "remaining_assemble_id":
                (
                    remaining_row.id
                    if remaining_row
                    else 0
                ),

            "has_remaining":
                bool(remaining_row),

            "completed_total":
                int(
                    row.total_completed_qty
                    or row.completed_qty
                    or 0
                ),
        }), 200

    except Exception as e:
        s.rollback()

        traceback.print_exc()

        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


@updateTableP.route("/updateMaterialP", methods=['POST'])
def update_material_p():
    print("updateMaterialP....")

    request_data = request.get_json()

    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 檢查傳入的參數，選擇查詢條件
    material_record = None

    #
    if _id is not None:
        material_record = s.query(P_Material).filter_by(id=_id).first()
    elif _order_num is not None:
        material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
    #

    if material_record is None:
      return_value = False
    else:
      # 動態設置欄位值
      #if hasattr(material_record, _record_name):
      #  setattr(material_record, _record_name, _record_data)
      #  s.commit()
      #
      # 20260824版
      if hasattr(
          material_record,
          _record_name
      ):

          # ============================================
          # 20260824
          # 數量欄位統一轉 int
          # ============================================

          qty_fields = {
              "delivery_qty",
              "total_delivery_qty",
              "material_qty",
              "assemble_qty",
              "total_assemble_qty",
              "allOk_qty",
              "total_allOk_qty",
          }

          if _record_name in qty_fields:

              try:
                  _record_data = int(
                      _record_data or 0
                  )

              except (
                  TypeError,
                  ValueError,
              ):

                  s.rollback()

                  return jsonify({
                      "status": False,
                      "message":
                          f"{_record_name} 必須為整數"
                  }), 400

          setattr(
              material_record,
              _record_name,
              _record_data
          )

          s.commit()
      #

    s.close()

    return jsonify({
      'status': return_value
    })


@updateTableP.route("/updateMaterialRecordP", methods=['POST'])
def update_material_record_p():
    print("updateMaterialRecordP....")

    request_data = request.get_json()

    _order_num = request_data.get('order_num')
    _id = request_data.get('id')

    _show1_ok = request_data['show1_ok']
    _show2_ok = request_data['show2_ok']
    _show3_ok = request_data['show3_ok']
    #_whichStation = request_data['whichStation']

    s = Session()

    if _order_num is not None:  # 如果傳入了 order_num
      s.query(P_Material).filter(P_Material.order_num == _order_num).update({
        "show1_ok": _show1_ok,
        "show2_ok": _show2_ok,
        "show3_ok": _show3_ok,
        #"whichStation": _whichStation,
      })
    elif _id is not None:  # 如果傳入了 id
      s.query(P_Material).filter(P_Material.id == _id).update({
        "show1_ok": _show1_ok,
        "show2_ok": _show2_ok,
        "show3_ok": _show3_ok,
        #"whichStation": _whichStation,
      })

    s.commit()

    s.close()

    return jsonify({
      'status': True
    })


@updateTableP.route("/updateBomXorReceiveP", methods=["POST"])
def update_bom_xor_receive_p():
    print("updateBomXorReceiveP....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")

    s = Session()

    # 找到複製資料
    copied_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied p_material table or missing source ID"}), 400

    # 找到原始資料
    source_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source p_material not found"}), 404

    # 條件限制：兩者其中之一 isLackMaterial 必須為 0 才繼續
    if source_material.isLackMaterial != 0 and copied_material.isLackMaterial != 0:
        return jsonify({"message": "No update required, neither material has isLackMaterial == 0"}), 200

    # 建立 dict 以 seq_num 為 key 對應 receive
    source_boms = {bom.seq_num: bom for bom in source_material._bom}
    copied_boms = {bom.seq_num: bom for bom in copied_material._bom}

    updated = False
    for seq_num, source_bom in source_boms.items():
        if seq_num in copied_boms:
            copied_bom = copied_boms[seq_num]
            xor_result = int(source_bom.receive) ^ int(copied_bom.receive)
            if xor_result == 1:
                source_bom.receive = True  #          將缺料清除
                source_material.isLackMaterial = 99
                copied_material.isLackMaterial = 0
                updated = True

    if updated:
        s.commit()

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })


@updateTableP.route("/updateModifyMaterialAndBomsP", methods=['POST'])
def update_modify_material_and_Boms_p():
    print("updateModifyMaterialAndBoms....")

    data = request.json
    _id = data.get("id")
    _date = data.get("date")
    _qty = data.get("qty")

    return_value = True

    update_data = {}
    if _date is not None:
        update_data["material_delivery_date"] = _date   #訂單日期

    if _qty is not None:
        update_data["material_qty"] = _qty              #需求數量(訂單數量)
        update_data["total_delivery_qty"] = _qty        #應備數量

    s = Session()

    if update_data:
        rows_updated = s.query(P_Material).filter(P_Material.id == _id).update(update_data)

    if rows_updated == 0:
        return_value = False
        raise ValueError("Update failed: no rows affected")

    s.commit()

    s.close()

    return jsonify({
      'status': return_value
    })

