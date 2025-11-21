# -*- coding: utf-8 -*-
# server/services/assemble_update_utils.py
from datetime import datetime

# ===== 型別轉換 =====
def coerce_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        vv = v.strip().lower()
        if vv in ("true", "t", "yes", "y", "1"):
            return True
        if vv in ("false", "f", "no", "n", "0", ""):
            return False
    return bool(v)

def coerce_int(v):
    try:
        return int(v)
    except Exception:
        return 0

def coerce_str(v, maxlen=None):
    if v is None:
        v = ""
    v = str(v)
    if maxlen is not None and len(v) > maxlen:
        v = v[:maxlen]
    return v

# ===== 可更新欄位白名單 =====
ALLOWED_FIELDS = {
    # int
    "process_step_code","must_receive_qty","ask_qty","total_ask_qty",
    "total_ask_qty_end","must_receive_end_qty","abnormal_qty",
    "good_qty","total_good_qty","non_good_qty","meinh_qty",
    "completed_qty","total_completed_qty","isAssembleFirstAlarm_qty",
    "whichStation","is_copied_from_id",
    # bool
    "is_assemble_ok","input_disable","input_end_disable","input_abnormal_disable",
    "isAssembleStationShow","isWarehouseStationShow","alarm_enable","isAssembleFirstAlarm",
    # str
    "material_num","material_comment","seq_num","work_num","Incoming1_Abnormal",
    "reason","confirm_comment","user_id","writer_id","write_date",
    "currentStartTime","currentEndTime","alarm_message",
    "isAssembleFirstAlarm_message","show1_ok","show2_ok","show3_ok",
    # 系統欄位（此 API 會自動覆寫）
    "update_time",
}

# ===== 欄位型別/長度 =====
FIELD_SCHEMAS = {
    # str
    "material_num": ("str", 20),
    "material_comment": ("str", 70),
    "seq_num": ("str", 20),
    "work_num": ("str", 20),
    "Incoming1_Abnormal": ("str", 30),
    "reason": ("str", 50),
    "confirm_comment": ("str", 70),
    "user_id": ("str", 8),
    "writer_id": ("str", 8),
    "write_date": ("str", 18),
    "currentStartTime": ("str", 30),
    "currentEndTime": ("str", 30),
    "alarm_message": ("str", 250),
    "isAssembleFirstAlarm_message": ("str", 100),
    "show1_ok": ("str", 20),
    "show2_ok": ("str", 20),
    "show3_ok": ("str", 20),
    "update_time": ("str", 30),
    # int
    "process_step_code": ("int", None),
    "must_receive_qty": ("int", None),
    "ask_qty": ("int", None),
    "total_ask_qty": ("int", None),
    "total_ask_qty_end": ("int", None),
    "must_receive_end_qty": ("int", None),
    "abnormal_qty": ("int", None),
    "good_qty": ("int", None),
    "total_good_qty": ("int", None),
    "non_good_qty": ("int", None),
    "meinh_qty": ("int", None),
    "completed_qty": ("int", None),
    "total_completed_qty": ("int", None),
    "isAssembleFirstAlarm_qty": ("int", None),
    "whichStation": ("int", None),
    "is_copied_from_id": ("int", None),
    # bool
    "is_assemble_ok": ("bool", None),
    "input_disable": ("bool", None),
    "input_end_disable": ("bool", None),
    "input_abnormal_disable": ("bool", None),
    "isAssembleStationShow": ("bool", None),
    "isWarehouseStationShow": ("bool", None),
    "alarm_enable": ("bool", None),
    "isAssembleFirstAlarm": ("bool", None),
}

def coerce_by_schema(field, value):
    kind, maxlen = FIELD_SCHEMAS.get(field, ("str", None))
    if kind == "int":
        return coerce_int(value)
    if kind == "bool":
        return coerce_bool(value)
    return coerce_str(value, maxlen)

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def serialize_assemble(obj):
    return {
        "id": obj.id,
        "material_id": obj.material_id,
        "process_step_code": obj.process_step_code,
        "must_receive_qty": obj.must_receive_qty,
        "ask_qty": obj.ask_qty,
        "total_ask_qty": obj.total_ask_qty,
        "total_ask_qty_end": obj.total_ask_qty_end,
        "must_receive_end_qty": obj.must_receive_end_qty,
        "abnormal_qty": obj.abnormal_qty,
        "good_qty": obj.good_qty,
        "total_good_qty": obj.total_good_qty,
        "non_good_qty": obj.non_good_qty,
        "meinh_qty": obj.meinh_qty,
        "completed_qty": obj.completed_qty,
        "total_completed_qty": obj.total_completed_qty,
        "is_assemble_ok": obj.is_assemble_ok,
        "input_disable": obj.input_disable,
        "input_end_disable": obj.input_end_disable,
        "input_abnormal_disable": obj.input_abnormal_disable,
        "isAssembleStationShow": obj.isAssembleStationShow,
        "isWarehouseStationShow": obj.isWarehouseStationShow,
        "alarm_enable": obj.alarm_enable,
        "alarm_message": obj.alarm_message,
        "isAssembleFirstAlarm": obj.isAssembleFirstAlarm,
        "isAssembleFirstAlarm_message": obj.isAssembleFirstAlarm_message,
        "isAssembleFirstAlarm_qty": obj.isAssembleFirstAlarm_qty,
        "whichStation": obj.whichStation,
        "show1_ok": obj.show1_ok,
        "show2_ok": obj.show2_ok,
        "show3_ok": obj.show3_ok,
        "currentStartTime": obj.currentStartTime,
        "currentEndTime": obj.currentEndTime,
        "user_id": obj.user_id,
        "writer_id": obj.writer_id,
        "write_date": obj.write_date,
        "update_time": obj.update_time,
        "create_at": obj.create_at.isoformat() if obj.create_at else None,
        "is_copied_from_id": obj.is_copied_from_id,
    }
