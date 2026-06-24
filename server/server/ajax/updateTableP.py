import os
import time
import datetime
from datetime import datetime as dt
import shutil
import pytz

from flask import Blueprint, jsonify, request, current_app

import traceback

from sqlalchemy import inspect, and_

from database.tables import Session

from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from .helper import normalize_create_at

updateTableP = Blueprint('updateTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------



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

  # 如果條件滿足，更新 material 表
  if all_process_step_zero:
    print("updateAssembleProcessStepP , all_process_step_zero", all_process_step_zero)

    material_record.isAssembleStation3TakeOk = True
    assemble_record.isAssembleStationShow = True

    ## ✅ 完工 → 進倉儲等待入庫
    #assemble_record.isWarehouseStationShow = True
    #assemble_record.isStockIn = False   # 尚未入庫（等待入庫清單要看這個）
    #
    # 加工結束後，仍留在 ~ProcessEnd.vue
    # 不可直接進 Ware~.vue
    assemble_record.isAssembleStationShow = True
    assemble_record.isWarehouseStationShow = False

    # 這個表示「需要入庫」，但尚未送到成品區
    assemble_record.isStockIn = True
    #

    return_value = True
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


