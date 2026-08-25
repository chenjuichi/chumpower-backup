import os
import time
import datetime

from datetime import datetime

from flask import Blueprint, jsonify, request

import traceback

from sqlalchemy import inspect, and_, or_, func

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


"""
# 20260730版
@updateTableP.route('/updateAssembleProcessStepP', methods=['POST'])
def update_assemble_process_step_p():
  print("updateAssembleProcessStepP....")

  data = request.json

  if not data or 'id' not in data or 'assemble_id' not in data:
    return jsonify({"error": "Missing parameters 'id' or 'assemble_id'"}), 400

  material_id = data['id']
  assemble_id = data['assemble_id']
  return_value = False

  s = Session()

  material_record = s.query(P_Material).filter_by(id=material_id).first()
  if not material_record:
    return jsonify({"error": f"P_Material with id {material_id} not found"}), 404

  assemble_record = s.query(P_Assemble).filter_by(id=assemble_id, material_id=material_id).first()
  if not assemble_record:
    return jsonify({"error": f"P_Assemble with id {assemble_id} and material_id {material_id} not found"}), 404

  target_create_at = normalize_create_at(assemble_record.create_at)

  assemble_records = (s.query(P_Assemble)
    .filter(and_(P_Assemble.material_id == material_id, P_Assemble.create_at == target_create_at))
    .all()
  )

  # 如果同組至少有一筆，判斷是否全部都是 process_step_code=0
  all_process_step_zero = bool(assemble_records) and all(r.process_step_code == 0 for r in assemble_records)

  if all_process_step_zero:
    print(
        "updateAssembleProcessStepP, all_process_step_zero",
        all_process_step_zero
    )

    now_str = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    material_record.isAssembleStation3TakeOk = True

    # 同一批所有已完成的加工工序都轉成待送出
    for row in assemble_records:
        row.isAssembleStationShow = True
        row.isWarehouseStationShow = False
        row.isStockIn = True

        row.input_end_disable = True
        row.input_abnormal_disable = True

    # ========================================================
    # 重要：
    # 全部加工工序已完成時，關閉同批所有員工仍未結束的計時。
    #
    # 例如：
    # A 已按結束，但 B 的 P_Process.end_time 仍是 NULL，
    # 這裡必須一起關閉。
    # ========================================================
    assemble_ids = [
        int(row.id)
        for row in assemble_records
        if row.id is not None
    ]

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
            P_Process.has_started.is_(True)
        )
        .filter(
            or_(
                P_Process.end_time.is_(None),
                P_Process.end_time == ''
            )
        )
        .with_for_update()
        .all()
    )

    for log in other_active_logs:
        # 保留已累計時間，這裡只負責停止殘留計時
        log.end_time = now_str
        log.has_started = False
        log.is_pause = True

        if not log.str_elapsedActive_time:
            seconds = int(
                log.elapsedActive_time or 0
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

    return_value = True
  #
  else:
    print("updateAssembleProcessStepP , not all_process_step_zero")

    material_record.isAssembleStation3TakeOk = False
    assemble_record.isAssembleStationShow = False

    # 把同一批加工製程排好順序，找出『現在做的是第幾道』，然後抓『下一道製程』出來。

    # assemble.seq_num 越小 → 越前面的製程
    sorted_records = sorted(assemble_records, key=lambda r: r.seq_num)

    # 現在在哪一個製程
    current_index = next((i for i, r in enumerate(sorted_records) if r.id == assemble_id), None)

    print("current_index, current_index + 1, len(sorted_records:",current_index, current_index + 1, len(sorted_records))
    if current_index is not None and current_index + 1 < len(sorted_records):
      next_record = sorted_records[current_index + 1]
      print(f"next_assemble_id 已設為 {next_record.id}")

      next_record.completed_qty = 0

    return_value = False
  s.commit()

  return jsonify({
    'status': return_value
  })
"""


"""
# 20260818版
# 20260813版
@updateTableP.route('/updateAssembleProcessStepP', methods=['POST'])
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

        # ----------------------------------------------------
        # 排序時將 seq_num 安全轉成整數
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # 尚未完成的工序：
        # process_step_code > 0
        # ----------------------------------------------------
        unfinished_records = [
            row
            for row in sorted_records
            if int(
                row.process_step_code or 0
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

        '''
        if all_process_step_zero:
            # =================================================
            # 全部工序完成，進入待送出
            # =================================================
            now_str = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            material_record.show2_ok = 5

            material_record\
                .isAssembleStation3TakeOk = True

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False

            for row in assemble_records:
                row.show2_ok = 5

                row.isAssembleStationShow = True
                row.isWarehouseStationShow = False
                row.isStockIn = True

                row.input_disable = True
                row.input_end_disable = True
                row.input_abnormal_disable = True

            assemble_ids = [
                int(row.id)
                for row in assemble_records
                if row.id is not None
            ]

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
        '''
        #
        if all_process_step_zero:
            print("updateAssembleProcessStepP, "
                "all_process_step_zero:",
                all_process_step_zero
            )

            now_str = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # ========================================================
            # 同批全部工序都已完成
            #
            # 只保留「最後一道工序」作為待送出代表列。
            # 前面已完成的加工工序全部隱藏。
            # ========================================================
            def seq_value(row):
                try:
                    return int(
                        str(row.seq_num or 0).strip()
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    return 0

            sorted_records = sorted(
                assemble_records,
                key=lambda row: (
                    seq_value(row),
                    int(row.id or 0),
                )
            )

            # 最後一道工序，例如：
            # B108-12 噴砂+磁震+鈍化
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

            # Material 進入待送出
            material_record.show2_ok = 5

            material_record\
                .isAssembleStation3TakeOk = True

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False

            # --------------------------------------------------------
            # 整張工單的完成數量統一顯示在最後一道工序
            #
            # 依你目前流程，每道工序完成量都是同一批應完成量，
            # 不可把兩道工序的 completed_qty 相加，
            # 否則 1020 + 1020 會變成 2040。
            # --------------------------------------------------------
            final_completed_qty = int(
                waiting_send_row.completed_qty
                or waiting_send_row.total_completed_qty
                or waiting_send_row.total_ask_qty_end
                or 0
            )

            final_total_completed_qty = int(
                waiting_send_row.total_completed_qty
                or waiting_send_row.total_ask_qty_end
                or waiting_send_row.completed_qty
                or 0
            )

            for row in assemble_records:
                is_waiting_send_row = (
                    int(row.id or 0) ==
                    waiting_send_id
                )

                # 所有工序都已完成
                row.process_step_code = 0
                row.show2_ok = 5

                row.input_disable = True
                row.input_end_disable = True
                row.input_abnormal_disable = True

                row.isWarehouseStationShow = False

                if is_waiting_send_row:
                    # 唯一待送出代表列
                    row.isAssembleStationShow = True
                    row.isStockIn = True

                    row.completed_qty = (
                        final_completed_qty
                    )

                    row.total_completed_qty = (
                        final_total_completed_qty
                    )

                    row.total_ask_qty_end = (
                        final_total_completed_qty
                    )
                else:
                    # 前面完成工序只保留歷史，不再顯示於 PEnd
                    row.isAssembleStationShow = False
                    row.isStockIn = False

            # ========================================================
            # 關閉同批所有員工殘留計時
            # ========================================================
            assemble_ids = [
                int(row.id)
                for row in assemble_records
                if row.id is not None
            ]

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
                    P_Process.has_started.is_(True)
                )
                .filter(
                    or_(
                        P_Process.end_time.is_(None),
                        P_Process.end_time == ''
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
                        log.elapsedActive_time or 0
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

            return_value = True
            next_assemble_id = 0

        # 20260813版
        else:
            # =================================================
            # 尚有下一道工序 / 尚有剩餘加工數量
            #
            # 重要：
            # 目前這筆若已有完成數量，
            # 必須保留在 PEnd 成為「待送出」。
            #
            # 例如：
            # 120 件，本次完成 38 件
            #
            # 已完成 38：
            #   留在 PEnd
            #   藍字
            #   待送出
            #
            # 剩餘數量：
            #   由 next_record 繼續進行加工
            # =================================================

            material_record.show2_ok = 3

            material_record.isAssembleStation3TakeOk = False

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False

            '''
            # -------------------------------------------------
            # 本次已完成的數量保留於 PEnd
            # -------------------------------------------------
            completed_qty = int(
                assemble_record.completed_qty
                or assemble_record.total_completed_qty
                or assemble_record.total_ask_qty_end
                or 0
            )

            if completed_qty > 0:
                # 已完成批次 → PEnd 待送出
                assemble_record.show2_ok = 5

                assemble_record.isAssembleStationShow = True
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True

                # 已完成總數量
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

            else:
                # 沒有完成數量才真的隱藏
                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False
            '''
        #
            # 20260818版
            # =================================================
            # 尚有下一道加工工序
            #
            # 目前工序只是「中間工序完成」，
            # 不能進入 PEnd 待送出。
            #
            # 只有全部加工工序完成後，
            # 才由 all_process_step_zero 分支建立 PEnd 待送出列。
            # =================================================

            material_record.show2_ok = 3
            material_record.isAssembleStation3TakeOk = False

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False


            # -------------------------------------------------
            # 目前工序已完成
            #
            # 保留完成數量做歷史資料，
            # 但不再顯示於 PBegin / PEnd。
            # -------------------------------------------------
            completed_qty = int(
                assemble_record.completed_qty
                or assemble_record.total_completed_qty
                or assemble_record.total_ask_qty_end
                or 0
            )

            assemble_record.isAssembleStationShow = False
            assemble_record.isWarehouseStationShow = False

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True

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


            # -------------------------------------------------
            # 第一筆尚未完成的工序 = 下一道加工工序
            # -------------------------------------------------
            next_record = unfinished_records[0]

            next_record.show2_ok = 3

            # 尚未開始，所以：
            # PBegin 要能看到
            # PEnd 不應看到
            next_record.isAssembleStationShow = False
            next_record.isWarehouseStationShow = False

            next_record.input_disable = False
            next_record.input_end_disable = False
            next_record.input_abnormal_disable = False

            next_record.completed_qty = 0

            next_record.total_completed_qty = int(
                next_record.total_completed_qty
                or 0
            )

            next_assemble_id = int(
                next_record.id
            )

            print(
                "下一道加工工序：",
                {
                    'assemble_id':
                        next_record.id,

                    'work_num':
                        next_record.work_num,

                    'process_step_code':
                        next_record.process_step_code,

                    'seq_num':
                        next_record.seq_num,
                }
            )
            #

            # 第一筆尚未完成的，就是下一道工序
            next_record = unfinished_records[0]
            '''
            next_record.show2_ok = 3

            next_record.isAssembleStationShow = False
            next_record.isWarehouseStationShow = False

            next_record.input_disable = False
            next_record.input_end_disable = False
            next_record.input_abnormal_disable = False

            # 下一道尚未開始，完成量維持 0
            next_record.completed_qty = 0
            next_record.total_completed_qty = (
                int(
                    next_record
                    .total_completed_qty
                    or 0
                )
            )
            '''
            # 20260818版
            # =================================================
            # 開放下一道加工工序
            #
            # 下一道尚未開始：
            #   PBegin：顯示
            #   PEnd：不顯示
            #
            # 上一道加工的完成量絕對不能帶到下一道。
            # =================================================

            material_record.show2_ok = 3
            material_record.hasStarted = False
            material_record.isOpen = False
            material_record.isOpenEmpId = ''

            next_record.show2_ok = 3

            next_record.isAssembleStationShow = False
            next_record.isWarehouseStationShow = False

            next_record.input_disable = False
            next_record.input_end_disable = False
            next_record.input_abnormal_disable = False

            # 下一道尚未加工，這三個一定從 0 開始
            next_record.completed_qty = 0
            next_record.total_completed_qty = 0
            next_record.total_ask_qty_end = 0

            next_assemble_id = int(
                next_record.id
            )

            print(
                "[updateAssembleProcessStepP] 下一道加工工序:",
                {
                    "material_id":
                        material_id,

                    "completed_assemble_id":
                        assemble_id,

                    "next_assemble_id":
                        next_record.id,

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
                }
            )
            #

            next_assemble_id = int(
                next_record.id
            )
            '''
            print(
                "下一道加工工序：",
                {
                    'assemble_id':
                        next_record.id,

                    'work_num':
                        next_record.work_num,

                    'process_step_code':
                        next_record
                        .process_step_code,

                    'seq_num':
                        next_record.seq_num,
                }
            )
            '''
        s.commit()

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
                int(material_record.show2_ok or 0),
        }), 200

    except Exception as error:
        s.rollback()

        logger.exception(
            "updateAssembleProcessStepP failed"
        )

        return jsonify({
            'status': False,
            'message': str(error),
        }), 500

    finally:
        s.close()
#
"""


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
            next_record.completed_qty = 0
            next_record.total_completed_qty = 0
            next_record.total_ask_qty_end = 0


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


"""
@updateTableP.route("/updateAssembleMustReceiveQtyByMaterialIDP", methods=['POST'])
def update_assembleMustReceiveQty_by_MaterialID_p():
    print("updateAssembleMustReceiveQtyByMaterialIDP....")

    request_data = request.get_json() or {}

    _material_id = request_data.get('material_id')
    _record_name = request_data.get('record_name')
    _record_data = request_data.get('record_data')

    s = Session()

    try:
        if not _material_id:
            return jsonify({
                'status': False,
                'msg': '缺少 material_id'
            }), 400

        if not _record_name:
            return jsonify({
                'status': False,
                'msg': '缺少 record_name'
            }), 400

        # ✅ 這裡要檢查 P_Assemble，不要檢查 Assemble
        valid_columns = [c.key for c in inspect(P_Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f"'{_record_name}' 不是 P_Assemble 表中的合法欄位"
            }), 400

        assemble_records = (
            s.query(P_Assemble)
            .filter(P_Assemble.material_id == _material_id)
            .all()
        )

        # ✅ 無工序加工單允許沒有 P_Assemble，不要丟 500
        if not assemble_records:
            print(f"material_id={_material_id} 沒有 P_Assemble，略過更新。")
            return jsonify({
                'status': True,
                'skipped': True,
                'updated_ids': [],
                'msg': f'material_id={_material_id} 沒有 P_Assemble，已略過'
            })

        updated_ids = []
        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        s.commit()

        return jsonify({
            'status': True,
            'skipped': False,
            'updated_ids': updated_ids
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            'status': False,
            'msg': str(e)
        }), 500

    finally:
        s.close()
"""


# 20260824版
@updateTableP.route(
    "/updateAssembleMustReceiveQtyByMaterialIDP",
    methods=["POST"]
)
def update_assembleMustReceiveQty_by_MaterialID_p():

    print(
        "updateAssembleMustReceiveQtyByMaterialIDP...."
    )

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

            print(
                "[before generic update]",
                {
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

  #print("_record_name:", _record_name)

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  assemble_record = s.query(P_Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  '''
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()
  '''
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
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  #print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
      material = s.query(P_Material).get(_material_id)
      #print("step1")
      if not material:
        return jsonify({'status': False, 'msg': 'Material not found'})
      #print("step2")

      target_process = (s.query(P_Process).filter(
                P_Process.material_id == _material_id,
                P_Process.assemble_id == 0,
                P_Process.has_started == True,
                P_Process.begin_time != '',
                P_Process.end_time != '',)
                .first())

      # 確保 _seq 不超過範圍
      #temp_len = len(material._process)
      #if _seq < 0 or _seq > temp_len:
      if not target_process:
        #print("step2-0 ")
        return jsonify({'status': False, 'msg': 'seq out of range'})

      #print("step3")

      # 取出對應的 Process
      #target_process = material._process[_seq-1]
      print("target_process:", target_process)
      # 更新欄位
      if _record_name1 and _record_data1 is not None:
        setattr(target_process, _record_name1, _record_data1)
      #print("step4")

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


"""
@updateTableP.route("/updateAssmbleDataByMaterialIDP", methods=['POST'])
def update_assemble_data_by_material_id_p():
  print("updateAssmbleDataByMaterialIDP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _delivery_qty = request_data.get('delivery_qty')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  _record_name2 = request_data.get('record_name2')
  _record_data2 = request_data.get('record_data2')
  _record_name3 = request_data.get('record_name3')
  _record_data3 = request_data.get('record_data3')
  _record_name4 = request_data.get('record_name4')
  _record_data4 = request_data.get('record_data4')

  #return_value = True  # true: 資料正確,
  s = Session()

  try:
      # 查詢所有符合條件的紀錄
      assemble_records = s.query(P_Assemble).filter(
          P_Assemble.material_id == _material_id,
          P_Assemble.must_receive_qty == _delivery_qty
      ).all()

      # 動態設定欄位
      for asm in assemble_records:
        if _record_name1 and _record_data1 is not None:
          setattr(asm, _record_name1, _record_data1)
        if _record_name2 and _record_data2 is not None:
          setattr(asm, _record_name2, _record_data2)
        if _record_name3 and _record_data3 is not None:
          setattr(asm, _record_name3, _record_data3)
        if _record_name4 and _record_data4 is not None:
          setattr(asm, _record_name4, _record_data4)

      # 提交更新
      s.commit()
      print(f"更新P_Assemble table成功，共 {len(assemble_records)} 筆資料")
      return_value = True
      #return
  except Exception as e:
      s.rollback()
      print("更新P_Assemble table失敗:", str(e))
      return_value = False
      #return

  return jsonify({
    'status': return_value
  })
"""


"""
# 20260824版
# ================================================================
# PMaterial 領料完成後，同步本批領料數量到：
#
# P_Material.delivery_qty
#
# P_Assemble：
#   must_receive_qty
#   ask_qty
#   total_ask_qty
#   must_receive_end_qty
#   original_must_receive_end_qty
#
# 重要：
# 不可以再用：
#
#   P_Assemble.must_receive_qty == delivery_qty
#
# 當查詢條件。
#
# 因為 P_Assemble 是 Excel 匯入時建立，
# must_receive_qty 很可能還是整張訂單數量，例如：
#
#   訂單量 = 2000
#   本次領料 = 500
#
# 此時舊條件：
#
#   must_receive_qty == 500
#
# 根本找不到原本 must_receive_qty=2000 的 P_Assemble。
# ================================================================

@updateTableP.route(
    "/updateAssmbleDataByMaterialIDP",
    methods=["POST"]
)
def update_assemble_data_by_material_id_p():

    print("updateAssmbleDataByMaterialIDP....")
    '''
    request_data = request.get_json(
        silent=True
    ) or {}

    print(
        "[updateAssmbleDataByMaterialIDP] request_data:",
        request_data
    )
    print(
        "[updateAssmbleDataByMaterialIDP] parsed:",
        {
            "material_id_raw": material_id_raw,
            "delivery_qty_raw": delivery_qty_raw,
        }
    )

    material_id_raw = request_data.get(
        "material_id"
    )

    delivery_qty_raw = request_data.get(
        "delivery_qty"
    )

    # ------------------------------------------------------------
    # 原本 API 支援的動態欄位，繼續保留
    # ------------------------------------------------------------

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
    '''
    #
    request_data = request.get_json(
        silent=True
    ) or {}

    print(
        "[updateAssmbleDataByMaterialIDP] request_data:",
        request_data
    )

    # ------------------------------------------------------------
    # 先取得參數
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # 取得之後才能 print
    # ------------------------------------------------------------

    print(
        "[updateAssmbleDataByMaterialIDP] parsed:",
        {
            "material_id_raw":
                material_id_raw,

            "delivery_qty_raw":
                delivery_qty_raw,

            "record_name1":
                record_name1,

            "record_data1":
                record_data1,

            "record_name2":
                record_name2,

            "record_data2":
                record_data2,
        }
    )
    #

    # ------------------------------------------------------------
    # 參數檢查
    # ------------------------------------------------------------

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
        # 1. 鎖定 P_Material
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

        # ========================================================
        # 2. 檢查領料數量
        #
        # 不可超過整張工單需求數量。
        # ========================================================

        material_qty = int(
            material.material_qty or 0
        )

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
                        f"不可大於訂單數量 {material_qty}"
                    )
            }), 400

        # ========================================================
        # 3. 永久保存「本批實際領料數量」
        #
        # 例如：
        #
        # material_qty       = 2000
        # total_delivery_qty = 2000
        # delivery_qty       = 500
        #
        # 不可以再把 delivery_qty 清成 0。
        # ========================================================

        material.delivery_qty = (
            delivery_qty
        )

        # ========================================================
        # 4. 找目前這個 material 的加工工序
        #
        # ★ 修正重點：
        #
        # 舊：
        #
        # P_Assemble.material_id == material_id
        # AND
        # P_Assemble.must_receive_qty == delivery_qty
        #
        # 新：
        #
        # 只依 material_id 找。
        #
        # 並排除：
        #   已經完成 process_step_code=0
        #   已送 Warehouse 的資料
        #
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
            .filter(
                P_Assemble.isWarehouseStationShow
                .is_(False)
            )
            .order_by(
                P_Assemble.seq_num.asc(),
                P_Assemble.id.asc()
            )
            .with_for_update()
            .all()
        )

        if not assemble_records:

            s.rollback()

            return jsonify({
                "status": False,
                "message":
                    (
                        "找不到尚未完成的 "
                        f"P_Assemble，material_id={material_id}"
                    )
            }), 404

        # ========================================================
        # 5. 本批領料數量同步到所有尚未加工完成的工序
        #
        # 999900006684：
        #
        # 原本：
        # must_receive_qty = 2000
        # ask_qty          = 0
        #
        # 領料 500 後：
        #
        # must_receive_qty = 500
        # ask_qty          = 500
        # total_ask_qty    = 500
        #
        # PBegin 就會正確顯示：
        #
        # 領料數量   500
        # 應領取數量 500
        # ========================================================

        updated_ids = []

        for asm in assemble_records:

            asm.must_receive_qty = (
                delivery_qty
            )

            asm.ask_qty = (
                delivery_qty
            )

            asm.total_ask_qty = (
                delivery_qty
            )

            # 尚未開始 End 報工前，
            # 應完成量就是本批投入數量。
            asm.must_receive_end_qty = (
                delivery_qty
            )

            # 若 table 有此欄位，也一起保存原始投入量
            if hasattr(
                asm,
                "original_must_receive_end_qty"
            ):
                asm.original_must_receive_end_qty = (
                    delivery_qty
                )

            # ----------------------------------------------------
            # 原 API 動態欄位仍保留
            # ----------------------------------------------------

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

        # ========================================================
        # 6. commit
        # ========================================================

        s.commit()

        print(
            "[updateAssmbleDataByMaterialIDP]",
            {
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
            }
        )

        return jsonify({
            "status": True,
            "message":
                "本批領料數量已同步",

            "material_id":
                material_id,

            "delivery_qty":
                delivery_qty,

            "updated_assemble_ids":
                updated_ids,
        }), 200

    except Exception as e:

        s.rollback()

        print(
            "updateAssmbleDataByMaterialIDP Error:",
            repr(e)
        )

        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:

        s.close()
"""


"""
# 20260824版
# ================================================================
# 加工線 PMaterial 領料完成後：
#
#   P_Material.delivery_qty
#
# 同步到尚未完成的 P_Assemble：
#
#   must_receive_qty
#   ask_qty
#   total_ask_qty
#   must_receive_end_qty
#   original_must_receive_end_qty（若有）
#
# 例：
#
# 訂單數量 material_qty = 2000
# 本批實際領料 delivery_qty = 500
#
# PBegin 應顯示：
#
#   領料數量     500
#   應領取數量   500
#
# 注意：
# 不可再使用：
#
#   P_Assemble.must_receive_qty == delivery_qty
#
# 當查詢條件。
# ================================================================

@updateTableP.route(
    "/updateAssmbleDataByMaterialIDP",
    methods=["POST"]
)
def update_assemble_data_by_material_id_p():

    print(
        "updateAssmbleDataByMaterialIDP...."
    )

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
    # 1. 取得 request
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

    print(
        "[updateAssmbleDataByMaterialIDP] parsed:",
        {
            "material_id_raw":
                material_id_raw,

            "delivery_qty_raw":
                delivery_qty_raw,

            "record_name1":
                record_name1,

            "record_data1":
                record_data1,

            "record_name2":
                record_name2,

            "record_data2":
                record_data2,
        }
    )

    # ============================================================
    # 2. 參數型別
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
                    (
                        "找不到 P_Material，"
                        f"id={material_id}"
                    )
            }), 404

        material_qty = int(
            material.material_qty
            or 0
        )

        # ========================================================
        # 4. 本批領料不可超過整張工單
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
        # 5. 保存本批領料數量
        #
        # 例如：
        #
        # material_qty = 2000
        # delivery_qty = 500
        #
        # material_qty 保留 2000
        # delivery_qty 改為 500
        # ========================================================

        material.delivery_qty = (
            delivery_qty
        )

        # ========================================================
        # 6. 找尚未完成的加工列
        #
        # ★ 這裡是本次主要修正
        #
        # 不再：
        #
        #   must_receive_qty == delivery_qty
        #
        # 也先不加：
        #
        #   isWarehouseStationShow.is_(False)
        #
        # 避免舊資料 NULL 被排除。
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

        # ========================================================
        # 7. 同步本批領料量到 P_Assemble
        # ========================================================

        for asm in assemble_records:

            print(
                "[before update]",
                {
                    "id":
                        asm.id,

                    "material_id":
                        asm.material_id,

                    "work_num":
                        asm.work_num,

                    "process_step_code":
                        asm.process_step_code,

                    "must_receive_qty":
                        asm.must_receive_qty,

                    "ask_qty":
                        asm.ask_qty,

                    "total_ask_qty":
                        asm.total_ask_qty,

                    "must_receive_end_qty":
                        asm.must_receive_end_qty,
                }
            )

            # ----------------------------------------------------
            # 本批數量
            # ----------------------------------------------------

            #asm.must_receive_qty = (
            #    delivery_qty
            #)

            asm.ask_qty = (
                delivery_qty
            )

            asm.total_ask_qty = (
                delivery_qty
            )

            #asm.must_receive_end_qty = (
            #    delivery_qty
            #)

            # ----------------------------------------------------
            # 若 ORM model 有此欄位，就一起同步
            # ----------------------------------------------------
            # 20240824版 remove
            #if hasattr(
            #    asm,
            #    "original_must_receive_end_qty"
            #):
            #
            #    asm.original_must_receive_end_qty = (
            #        delivery_qty
            #    )

            # ====================================================
            # 8. 保留原 API 的動態欄位更新
            #
            # 你目前前端會送：
            #
            # record_name1 = show1_ok
            # record_data1 = 2
            #
            # record_name2 = show2_ok
            # record_data2 = 3
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

            print(
                "[after update]",
                {
                    "id":
                        asm.id,

                    "must_receive_qty":
                        asm.must_receive_qty,

                    "ask_qty":
                        asm.ask_qty,

                    "total_ask_qty":
                        asm.total_ask_qty,

                    "must_receive_end_qty":
                        asm.must_receive_end_qty,
                }
            )

        # ========================================================
        # 9. commit
        # ========================================================

        s.commit()

        # ========================================================
        # 10. commit 後再次查 DB
        #
        # 測試階段建議保留。
        # 確定正常後可以刪掉這段 print。
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

            print(
                "[after commit]",
                {
                    "id":
                        row.id,

                    "work_num":
                        row.work_num,

                    "process_step_code":
                        row.process_step_code,

                    "must_receive_qty":
                        row.must_receive_qty,

                    "ask_qty":
                        row.ask_qty,

                    "total_ask_qty":
                        row.total_ask_qty,

                    "must_receive_end_qty":
                        row.must_receive_end_qty,
                }
            )

        print(
            "[updateAssmbleDataByMaterialIDP] OK:",
            {
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
            }
        )

        return jsonify({
            "status": True,

            "message":
                "本批領料數量同步完成",

            "material_id":
                material_id,

            "order_num":
                material.order_num,

            "delivery_qty":
                delivery_qty,

            "updated_assemble_ids":
                updated_ids,
        }), 200

    except Exception as e:

        s.rollback()

        print(
            "updateAssmbleDataByMaterialIDP Error:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "message":
                str(e)
        }), 500

    finally:

        s.close()
"""


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

@updateTableP.route(
    "/updateAssmbleDataByMaterialIDP",
    methods=["POST"]
)
def update_assemble_data_by_material_id_p():

    print(
        "updateAssmbleDataByMaterialIDP...."
    )

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

            print(
                "[after commit]",
                {
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

        print(
            "[updateAssmbleDataByMaterialIDP] OK:",
            {
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

        print(
            "updateAssmbleDataByMaterialIDP Error:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "message":
                str(e)
        }), 500

    finally:

        s.close()


"""
# 20260813版
@updateTableP.route('/sendProcessToWarehouse', methods=['POST'])
def send_process_to_warehouse():
    print("sendProcessToWarehouse.")

    data = request.get_json(silent=True) or {}
    material_id = data.get('id')
    assemble_id = data.get('assemble_id')
    mode = data.get('mode', 'manual')

    if not material_id or not assemble_id:
        return jsonify({
            "status": False,
            "message": "缺少 id 或 assemble_id"
        }), 400

    s = Session()
    try:
        material = s.query(P_Material).filter(P_Material.id == material_id).first()
        row = (
            s.query(P_Assemble)
             .filter(P_Assemble.id == assemble_id)
             .filter(P_Assemble.material_id == material_id)
             .first()
        )

        if not material or not row:
            return jsonify({
                "status": False,
                "message": "找不到 P_Material 或 P_Assemble"
            }), 404

        # 同一張加工工單只保留一筆進 Ware
        s.query(P_Assemble).filter(
            P_Assemble.material_id == material_id
        ).update({
            P_Assemble.isWarehouseStationShow: False
        }, synchronize_session=False)

        '''
        row.isAssembleStationShow = False
        row.isWarehouseStationShow = True
        row.isStockIn = True

        material.move_by_automatic_or_manual_2 = True if mode == 'agv' else False
        material.whichStation = 3
        material.show2_ok = 6   # 等待入庫作業
        material.show3_ok = 11  # 等待入庫作業 / 成品區
        '''
        # 20260813版
        # ------------------------------------------------------------
        # 本次只送出指定 assemble。
        # 不能因為送出部分完成量，就把整張 material 移到成品區。
        # ------------------------------------------------------------
        row.isAssembleStationShow = False
        row.isWarehouseStationShow = True
        row.isStockIn = True

        material.move_by_automatic_or_manual_2 = (
            True if mode == 'agv'
            else False
        )

        # ------------------------------------------------------------
        # 查詢同 material 是否仍有尚未完成的加工列
        # ------------------------------------------------------------
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
            .first()
        )

        if remaining_row:
            # ========================================================
            # 部分完成，例如 120 -> 已完成 38，仍有 82
            #
            # 只有 38 送 Warehouse。
            # 整張 material 仍然留在加工站。
            # ========================================================
            material.whichStation = 2
            material.show1_ok = 2
            material.show2_ok = 4
            material.show3_ok = str(
                remaining_row.process_step_code
                or 0
            )

            material.isAssembleStation3TakeOk = False

            # 剩餘列重新顯示於加工端
            remaining_row.isAssembleStationShow = False
            remaining_row.isWarehouseStationShow = False

            remaining_row.input_disable = False
            remaining_row.input_end_disable = False
            remaining_row.input_abnormal_disable = False

        else:
            # ========================================================
            # 全部加工量真的都完成了
            # 才能把整張工單送到成品區
            # ========================================================
            material.whichStation = 3
            material.show2_ok = 6
            material.show3_ok = 11
        #

        s.commit()

        return jsonify({
            "status": True,
            "message": "加工件已送到成品區，可在 Ware~.vue 顯示"
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()
"""


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
            remaining_row.isAssembleStationShow = False
            remaining_row.isWarehouseStationShow = False

            remaining_row.isStockIn = False

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
    #if _order_num is not None:  # 如果傳入了 order_num
    #    material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
    #elif _id is not None:  # 如果傳入了 id
    #    material_record = s.query(P_Material).filter_by(id=_id).first()
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



