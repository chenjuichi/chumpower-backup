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

