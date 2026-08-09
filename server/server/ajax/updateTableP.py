import os
import time
import datetime

from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

import traceback

from sqlalchemy import inspect, and_, or_

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


# 20260805版
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
        #
        else:
            # =================================================
            # 尚有下一道工序
            # =================================================
            material_record.show2_ok = 3

            material_record\
                .isAssembleStation3TakeOk = False

            material_record.isOpen = False
            material_record.isOpenEmpId = ''
            material_record.hasStarted = False

            # 目前已完成工序不可再出現在 Begin / End
            assemble_record.show2_ok = 5
            assemble_record.isAssembleStationShow = False
            assemble_record.isWarehouseStationShow = False

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True

            # 第一筆尚未完成的，就是下一道工序
            next_record = unfinished_records[0]

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
                        next_record
                        .process_step_code,

                    'seq_num':
                        next_record.seq_num,
                }
            )

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



