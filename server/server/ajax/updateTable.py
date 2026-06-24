import os
import time
import datetime
from datetime import datetime as dt
import shutil
import pytz

from flask import Blueprint, jsonify, request, current_app

import traceback

import pymysql
#from sqlalchemy import exc
#from sqlalchemy import func
from sqlalchemy import distinct
from sqlalchemy import inspect, or_
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import cast, Integer

from database.tables import User, UserDelegate, Permission, Setting, Bom, Material, Assemble, AbnormalCause, Process, Product, Agv, Session
from database.tables import default_process_steps

from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from werkzeug.security import generate_password_hash

from operator import itemgetter, attrgetter

from .assemble_update_utils import (
    ALLOWED_FIELDS, FIELD_SCHEMAS,
    coerce_by_schema, serialize_assemble, now_str
)

from .helper import (
    release_b109_batch_to_b110,
    normalize_create_at,
    sync_assemble_schedule_rows,
)

updateTable = Blueprint('updateTable', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------

"""
def sync_assemble_schedule_rows(session, material_id, process_steps, qty=None):
    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        print("material not found:", material_id)
        return

    process_steps = process_steps or default_process_steps()

    all_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .all()
    )

    def get_base_by_work_num(work_num):
        for row in all_rows:
            if row.is_copied_from_id is None and (row.work_num or '').strip() == work_num:
                return row
        return None

    def get_any_template_base():
        for row in all_rows:
            if row.is_copied_from_id is None:
                return row
        return all_rows[0] if all_rows else None

    def build_base_row_from_template(template, work_num, process_step_code):
        new_base = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,
            seq_num=getattr(template, 'seq_num', 10) if template else 10,
            work_num=work_num,
            process_step_code=process_step_code,
            Incoming1_Abnormal=getattr(template, 'Incoming1_Abnormal', '') if template else '',
            must_receive_qty=getattr(template, 'must_receive_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            ask_qty=getattr(template, 'ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty=getattr(template, 'total_ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty_end=getattr(template, 'total_ask_qty_end', 0) if template else 0,
            must_receive_end_qty=getattr(template, 'must_receive_end_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            abnormal_qty=getattr(template, 'abnormal_qty', 0) if template else 0,
            user_id=getattr(template, 'user_id', material.isOpenEmpId) if template else material.isOpenEmpId,
            writer_id=getattr(template, 'writer_id', None) if template else None,
            write_date=getattr(template, 'write_date', None) if template else None,
            good_qty=getattr(template, 'good_qty', 0) if template else 0,
            total_good_qty=getattr(template, 'total_good_qty', 0) if template else 0,
            non_good_qty=getattr(template, 'non_good_qty', 0) if template else 0,
            meinh_qty=getattr(template, 'meinh_qty', 0) if template else 0,
            completed_qty=getattr(template, 'completed_qty', 0) if template else 0,
            total_completed_qty=getattr(template, 'total_completed_qty', 0) if template else 0,
            allOk_qty=getattr(template, 'allOk_qty', 0) if template else 0,
            reason=getattr(template, 'reason', '') if template else '',
            confirm_comment=getattr(template, 'confirm_comment', '') if template else '',
            is_assemble_ok=getattr(template, 'is_assemble_ok', 0) if template else 0,
            currentStartTime=None,
            currentEndTime=None,
            input_disable=getattr(template, 'input_disable', 1) if template else 1,
            input_end_disable=getattr(template, 'input_end_disable', 0) if template else 0,
            input_allOk_disable=getattr(template, 'input_allOk_disable', 0) if template else 0,
            input_abnormal_disable=getattr(template, 'input_abnormal_disable', 0) if template else 0,
            isAssembleStationShow=getattr(template, 'isAssembleStationShow', 0) if template else 0,
            isWarehouseStationShow=getattr(template, 'isWarehouseStationShow', 0) if template else 0,
            alarm_enable=getattr(template, 'alarm_enable', 1) if template else 1,
            alarm_message=getattr(template, 'alarm_message', '') if template else '',
            isAssembleFirstAlarm=getattr(template, 'isAssembleFirstAlarm', 1) if template else 1,
            isAssembleFirstAlarm_message=getattr(template, 'isAssembleFirstAlarm_message', '') if template else '',
            isAssembleFirstAlarm_qty=getattr(template, 'isAssembleFirstAlarm_qty', 0) if template else 0,
            whichStation=getattr(template, 'whichStation', material.whichStation) if template else material.whichStation,
            show1_ok=getattr(template, 'show1_ok', material.show1_ok) if template else material.show1_ok,
            show2_ok=getattr(template, 'show2_ok', material.show2_ok) if template else material.show2_ok,
            show3_ok=getattr(template, 'show3_ok', material.show3_ok) if template else material.show3_ok,
            schedule_id=None,
            is_copied_from_id=None
        )
        session.add(new_base)
        session.flush()
        return new_base

    def ensure_base_row(work_num, process_step_code, target_steps):
        if work_num == 'B109':
            process_type = 21
        elif work_num == 'B110':
            process_type = 22
        else:
            process_type = None

        completed_schedule_ids = set()

        if process_type:
            completed_schedule_ids = {
                int(r[0])
                for r in (
                    session.query(Assemble.schedule_id)
                    .join(Process, Process.assemble_id == Assemble.id)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == work_num)
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Process.process_type == process_type)
                    .filter(Process.has_started.is_(True))
                    .filter(Process.end_time.isnot(None))
                    .filter(Process.end_time != '')
                    .all()
                )
                if r[0] is not None
            }

        #checked_ids = [
        #    int(x.get('id'))
        #    for x in (target_steps or [])
        #    if (
        #        x.get('checked')
        #        and x.get('id') is not None
        #        and int(x.get('id')) not in completed_schedule_ids
        #    )
        #]
        #
        checked_ids = [
            int(x.get('id'))
            for x in (target_steps or [])
            if (
                x.get('checked')
                and not x.get('deleted', False)
                and x.get('id') is not None
                and int(x.get('id')) not in completed_schedule_ids
            )
        ]

        print("sync schedule:", material_id, work_num, checked_ids)
        #

        base = get_base_by_work_num(work_num)

        if not base and checked_ids:
            template = get_any_template_base()
            base = build_base_row_from_template(template, work_num, process_step_code)
            all_rows.append(base)

        if not base:
            return
        '''
        session.query(Assemble).filter(
            Assemble.is_copied_from_id == base.id
        ).delete(synchronize_session='fetch')
        '''
        #
        # ✅ 先清掉同 material + 同 work_num + 有 schedule_id 的舊排程列
        # 只保留 base row，避免 b1/b2/b3 舊 copied rows 殘留
        session.query(Assemble).filter(
            Assemble.material_id == material_id,
            Assemble.work_num == work_num,
            Assemble.id != base.id,
            Assemble.schedule_id.isnot(None),
            Assemble.reason != '異常返工'
        ).delete(synchronize_session='fetch')
        #

        '''
        if not checked_ids:
            base.schedule_id = None
            #base.process_step_code = 0
            base.isAssembleStationShow = False
            base.isWarehouseStationShow = False
            #base.input_disable = True
            #base.input_end_disable = True
            #base.input_allOk_disable = True
            #base.input_abnormal_disable = True
            #base.show1_ok = 0
            #base.show2_ok = 0
            #base.show3_ok = 0
            base.must_receive_qty = 0
            base.ask_qty = 0
            base.total_ask_qty = 0
            base.must_receive_end_qty = 0
            base.total_ask_qty_end = 0
            #
            base.process_step_code = process_step_code
            base.input_disable = False
            base.input_end_disable = False
            base.input_allOk_disable = False
            base.input_abnormal_disable = False

            # ⭐ 只選檢驗時，B110 也要能在 Begin 顯示
            base.isAssembleStationShow = True
            base.isWarehouseStationShow = False

            base.show1_ok = 1
            base.show2_ok = 5 if work_num == 'B110' else 3
            base.show3_ok = 5 if work_num == 'B110' else 3
            #
            return
        '''
        #
        if not checked_ids:
            # ⭐ 沒選此 work_num，只把這個 work_num 關掉
            base.schedule_id = None
            base.process_step_code = 0
            base.isAssembleStationShow = False
            base.isWarehouseStationShow = False
            base.input_disable = True
            base.input_end_disable = True
            base.input_allOk_disable = True
            base.input_abnormal_disable = True
            base.show1_ok = 0
            base.show2_ok = 0
            base.show3_ok = 0
            base.must_receive_qty = 0
            base.ask_qty = 0
            base.total_ask_qty = 0
            base.must_receive_end_qty = 0
            base.total_ask_qty_end = 0
            return
        #

        base.process_step_code = process_step_code
        base.input_disable = False
        base.input_end_disable = False
        base.input_allOk_disable = False
        base.input_abnormal_disable = False
        #
        #base.isAssembleStationShow = False
        # ⭐ 有選工序就要顯示，包含「只選檢驗 B110」
        base.isAssembleStationShow = True
        #

        base.isWarehouseStationShow = False
        #base.show1_ok = material.show1_ok
        #base.show2_ok = material.show2_ok
        #base.show3_ok = material.show3_ok
        #
        base.show1_ok = 1
        if work_num == 'B110':
            base.show2_ok = 5
            base.show3_ok = 5
        else:
            base.show2_ok = 3
            base.show3_ok = 3
        #

        #base_qty = (
        #    qty
        #    or material.delivery_qty
        #    or material.total_delivery_qty
        #    or material.material_qty
        #    or 0
        #)
        #
        base_qty = (
            qty
            or material.total_delivery_qty
            or material.delivery_qty
            or material.material_qty
            or 0
        )
        base_qty = int(base_qty or 0)
        #

        base.must_receive_qty = base_qty
        base.ask_qty = base_qty
        base.total_ask_qty = base_qty
        base.must_receive_end_qty = base_qty

        if qty is not None and qty != '':
          base.abnormal_qty = int(base_qty or 0)
          base.reason = '異常返工'

        base.schedule_id = checked_ids[0]

        for sid in checked_ids[1:]:
            new_row = Assemble(
                material_id=base.material_id,
                material_num=base.material_num,
                material_comment=base.material_comment,
                seq_num=base.seq_num,
                work_num=base.work_num,
                process_step_code=base.process_step_code,
                Incoming1_Abnormal=base.Incoming1_Abnormal,
                must_receive_qty=base.must_receive_qty,
                ask_qty=base.ask_qty,
                total_ask_qty=base.total_ask_qty,
                total_ask_qty_end=base.total_ask_qty_end,
                must_receive_end_qty=base.must_receive_end_qty,
                abnormal_qty=base.abnormal_qty,
                user_id=base.user_id,
                writer_id=base.writer_id,
                write_date=base.write_date,
                good_qty=base.good_qty,
                total_good_qty=base.total_good_qty,
                non_good_qty=base.non_good_qty,
                meinh_qty=base.meinh_qty,
                completed_qty=base.completed_qty,
                total_completed_qty=base.total_completed_qty,
                allOk_qty=base.allOk_qty,
                reason=base.reason,
                confirm_comment=base.confirm_comment,
                is_assemble_ok=base.is_assemble_ok,
                currentStartTime=None,
                currentEndTime=None,
                input_disable=base.input_disable,
                input_end_disable=base.input_end_disable,
                input_allOk_disable=base.input_allOk_disable,
                input_abnormal_disable=base.input_abnormal_disable,
                isAssembleStationShow=base.isAssembleStationShow,
                isWarehouseStationShow=base.isWarehouseStationShow,
                alarm_enable=base.alarm_enable,
                alarm_message=base.alarm_message,
                isAssembleFirstAlarm=base.isAssembleFirstAlarm,
                isAssembleFirstAlarm_message=base.isAssembleFirstAlarm_message,
                isAssembleFirstAlarm_qty=base.isAssembleFirstAlarm_qty,
                whichStation=base.whichStation,
                show1_ok=base.show1_ok,
                show2_ok=base.show2_ok,
                show3_ok=base.show3_ok,
                schedule_id=sid,
                is_copied_from_id=base.id
            )
            session.add(new_row)

    ensure_base_row(
        work_num='B109',
        process_step_code=3,
        target_steps=process_steps.get('assemble', [])
    )

    ensure_base_row(
        work_num='B110',
        process_step_code=2,
        target_steps=process_steps.get('check', [])
    )
"""


"""
# helper.py
def sync_assemble_schedule_rows(session, material_id, process_steps, qty=None):
    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        print("material not found:", material_id)
        return

    process_steps = process_steps or default_process_steps()

    all_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .all()
    )

    def get_base_by_work_num(work_num):
        for row in all_rows:
            if row.is_copied_from_id is None and (row.work_num or '').strip() == work_num:
                return row
        return None

    def get_any_template_base():
        for row in all_rows:
            if row.is_copied_from_id is None:
                return row
        return all_rows[0] if all_rows else None

    def build_base_row_from_template(template, work_num, process_step_code):
        new_base = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,
            seq_num=getattr(template, 'seq_num', 10) if template else 10,
            work_num=work_num,
            process_step_code=process_step_code,
            Incoming1_Abnormal=getattr(template, 'Incoming1_Abnormal', '') if template else '',
            must_receive_qty=getattr(template, 'must_receive_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            ask_qty=getattr(template, 'ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty=getattr(template, 'total_ask_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            total_ask_qty_end=getattr(template, 'total_ask_qty_end', 0) if template else 0,
            must_receive_end_qty=getattr(template, 'must_receive_end_qty', material.delivery_qty or 0) if template else (material.delivery_qty or 0),
            abnormal_qty=getattr(template, 'abnormal_qty', 0) if template else 0,
            user_id=getattr(template, 'user_id', material.isOpenEmpId) if template else material.isOpenEmpId,
            writer_id=getattr(template, 'writer_id', None) if template else None,
            write_date=getattr(template, 'write_date', None) if template else None,
            good_qty=getattr(template, 'good_qty', 0) if template else 0,
            total_good_qty=getattr(template, 'total_good_qty', 0) if template else 0,
            non_good_qty=getattr(template, 'non_good_qty', 0) if template else 0,
            meinh_qty=getattr(template, 'meinh_qty', 0) if template else 0,
            completed_qty=getattr(template, 'completed_qty', 0) if template else 0,
            total_completed_qty=getattr(template, 'total_completed_qty', 0) if template else 0,
            allOk_qty=getattr(template, 'allOk_qty', 0) if template else 0,
            reason='',
            confirm_comment=getattr(template, 'confirm_comment', '') if template else '',
            is_assemble_ok=getattr(template, 'is_assemble_ok', 0) if template else 0,
            currentStartTime=None,
            currentEndTime=None,
            input_disable=True,
            input_end_disable=True,
            input_allOk_disable=True,
            input_abnormal_disable=True,
            isAssembleStationShow=False,
            isWarehouseStationShow=False,
            alarm_enable=getattr(template, 'alarm_enable', 1) if template else 1,
            alarm_message=getattr(template, 'alarm_message', '') if template else '',
            isAssembleFirstAlarm=getattr(template, 'isAssembleFirstAlarm', 1) if template else 1,
            isAssembleFirstAlarm_message=getattr(template, 'isAssembleFirstAlarm_message', '') if template else '',
            isAssembleFirstAlarm_qty=getattr(template, 'isAssembleFirstAlarm_qty', 0) if template else 0,
            whichStation=getattr(template, 'whichStation', material.whichStation) if template else material.whichStation,
            show1_ok=0,
            show2_ok=0,
            show3_ok=0,
            schedule_id=None,
            is_copied_from_id=None
        )
        session.add(new_base)
        session.flush()
        return new_base

    def close_schedule_row(row):
        row.schedule_id = None
        row.process_step_code = 0
        row.isAssembleStationShow = False
        row.isWarehouseStationShow = False
        row.input_disable = True
        row.input_end_disable = True
        row.input_allOk_disable = True
        row.input_abnormal_disable = True
        row.show1_ok = 0
        row.show2_ok = 0
        row.show3_ok = 0
        row.must_receive_qty = 0
        row.ask_qty = 0
        row.total_ask_qty = 0
        row.must_receive_end_qty = 0
        row.total_ask_qty_end = 0
        row.currentStartTime = None
        row.currentEndTime = None

    def apply_schedule_row(row, sid, process_step_code, base_qty, work_num, base):
        row.schedule_id = sid
        row.process_step_code = process_step_code
        row.work_num = work_num
        row.material_num = base.material_num
        row.material_comment = base.material_comment
        row.seq_num = base.seq_num

        row.input_disable = False
        row.input_end_disable = False
        row.input_allOk_disable = False
        row.input_abnormal_disable = False

        row.isAssembleStationShow = True
        row.isWarehouseStationShow = False

        row.show1_ok = 1
        if work_num == "B110":
            row.show2_ok = 5
            row.show3_ok = 5
        else:
            row.show2_ok = 3
            row.show3_ok = 3

        row.must_receive_qty = base_qty
        row.ask_qty = base_qty
        row.total_ask_qty = base_qty
        row.must_receive_end_qty = base_qty

        if qty is not None and qty != '':
            row.abnormal_qty = int(base_qty or 0)
            row.reason = '異常返工'
        else:
            if row.reason == '異常返工':
                row.reason = ''

    def ensure_base_row(work_num, process_step_code, target_steps):
        if work_num == 'B109':
            process_type = 21
        elif work_num == 'B110':
            process_type = 22
        else:
            process_type = None

        completed_schedule_ids = set()

        if process_type:
            completed_schedule_ids = {
                int(r[0])
                for r in (
                    session.query(Assemble.schedule_id)
                    .join(Process, Process.assemble_id == Assemble.id)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == work_num)
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Process.process_type == process_type)
                    .filter(Process.has_started.is_(True))
                    .filter(Process.end_time.isnot(None))
                    .filter(Process.end_time != '')
                    .all()
                )
                if r[0] is not None
            }

        checked_ids = [
            int(x.get('id'))
            for x in (target_steps or [])
            if (
                x.get('checked')
                and not x.get('deleted', False)
                and x.get('id') is not None
                and int(x.get('id')) not in completed_schedule_ids
            )
        ]

        print("sync schedule:", material_id, work_num, checked_ids)

        base = get_base_by_work_num(work_num)

        if not base and checked_ids:
            template = get_any_template_base()
            base = build_base_row_from_template(template, work_num, process_step_code)
            all_rows.append(base)

        if not base:
            return

        base_qty = (
            qty
            or material.total_delivery_qty
            or material.delivery_qty
            or material.material_qty
            or 0
        )
        base_qty = int(base_qty or 0)

        schedule_rows = (
            session.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .filter(Assemble.work_num == work_num)
            .filter(or_(Assemble.reason.is_(None), Assemble.reason != '異常返工'))
            .order_by(Assemble.id)
            .all()
        )

        usable_rows = [base] + [r for r in schedule_rows if r.id != base.id]

        for idx, sid in enumerate(checked_ids):
            if idx < len(usable_rows):
                row = usable_rows[idx]
            else:
                row = Assemble(
                    material_id=base.material_id,
                    material_num=base.material_num,
                    material_comment=base.material_comment,
                    seq_num=base.seq_num,
                    work_num=base.work_num,
                    process_step_code=base.process_step_code,
                    Incoming1_Abnormal=base.Incoming1_Abnormal,
                    must_receive_qty=base.must_receive_qty,
                    ask_qty=base.ask_qty,
                    total_ask_qty=base.total_ask_qty,
                    total_ask_qty_end=base.total_ask_qty_end,
                    must_receive_end_qty=base.must_receive_end_qty,
                    abnormal_qty=base.abnormal_qty,
                    user_id=base.user_id,
                    writer_id=base.writer_id,
                    write_date=base.write_date,
                    good_qty=base.good_qty,
                    total_good_qty=base.total_good_qty,
                    non_good_qty=base.non_good_qty,
                    meinh_qty=base.meinh_qty,
                    completed_qty=base.completed_qty,
                    total_completed_qty=base.total_completed_qty,
                    allOk_qty=base.allOk_qty,
                    reason='',
                    confirm_comment=base.confirm_comment,
                    is_assemble_ok=base.is_assemble_ok,
                    currentStartTime=None,
                    currentEndTime=None,
                    input_disable=False,
                    input_end_disable=False,
                    input_allOk_disable=False,
                    input_abnormal_disable=False,
                    isAssembleStationShow=True,
                    isWarehouseStationShow=False,
                    alarm_enable=base.alarm_enable,
                    alarm_message=base.alarm_message,
                    isAssembleFirstAlarm=base.isAssembleFirstAlarm,
                    isAssembleFirstAlarm_message=base.isAssembleFirstAlarm_message,
                    isAssembleFirstAlarm_qty=base.isAssembleFirstAlarm_qty,
                    whichStation=base.whichStation,
                    show1_ok=1,
                    show2_ok=5 if work_num == "B110" else 3,
                    show3_ok=5 if work_num == "B110" else 3,
                    schedule_id=sid,
                    is_copied_from_id=base.id
                )
                session.add(row)
                session.flush()
                usable_rows.append(row)

            apply_schedule_row(row, sid, process_step_code, base_qty, work_num, base)

        for row in usable_rows[len(checked_ids):]:
            close_schedule_row(row)

    ensure_base_row(
        work_num='B109',
        process_step_code=3,
        target_steps=process_steps.get('assemble', [])
    )

    ensure_base_row(
        work_num='B110',
        process_step_code=2,
        target_steps=process_steps.get('check', [])
    )
"""


def parse_datetime_or_none(val):
    if val is None or str(val).strip() == "":
        return None

    txt = str(val).strip()

    # ISO 格式
    try:
        return dt.fromisoformat(txt.replace("Z", ""))
    except Exception:
        pass

    # 常見格式
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return dt.strptime(txt, fmt)
        except Exception:
            continue

    raise ValueError(f"無法解析日期時間格式: {txt}")


def _to_int_or_none(v):
  if v is None or v == "":
    return None
  try:
    return int(v)
  except (TypeError, ValueError):
    raise ValueError("必須是整數或空字串/Null")


def order_has_lack(session, order_num: str) -> bool:
    # 只要同一張訂單底下（包含 A1/A2/A3）任何 BOM.receive == False，就算缺料
    return (
        session.query(Bom.id)
        .join(Material, Bom.material_id == Material.id)
        .filter(Material.order_num == order_num)
        .filter(Bom.receive.is_(False))
        .limit(1)
        .count()
        > 0
    )


def refresh_root_shortage_note(session, order_num: str) -> None:
    root = (
        session.query(Material)
        .filter(Material.order_num == order_num)
        .filter(Material.is_copied_from_id.is_(None))  # root = A1
        .order_by(Material.id.asc())
        .first()
    )
    if not root:
        return

    has_lack = order_has_lack(session, order_num)
    root.shortage_note = "(缺料)" if has_lack else ""


def refresh_root_status(session, order_num: str) -> None:
    # 1) 找 root(A1)
    root = (
        session.query(Material)
        .filter(Material.order_num == order_num)
        .filter(Material.is_copied_from_id.is_(None))  # root = A1
        .order_by(Material.id.asc())
        .first()
    )
    if not root:
        return

    # 2) 找同訂單所有 material.id（含 A1/A2/A3）
    mids = [
        r[0] for r in (
            session.query(Material.id)
            .filter(Material.order_num == order_num)
            .all()
        )
    ]
    if not mids:
        return

    # 3) 統計 BOM 總數 / receive=True 數
    total_bom = (
        session.query(Bom.id)
        .filter(Bom.material_id.in_(mids))
        .count()
    )

    received_bom = (
        session.query(Bom.id)
        .filter(Bom.material_id.in_(mids))
        .filter(Bom.receive.is_(True))
        .count()
    )

    # 4) 決定是否還缺料
    #    - total_bom == 0：通常視為「仍未建 BOM」→ 你可視需求當缺料或不缺料
    all_received = (total_bom > 0 and total_bom == received_bom)

    # 5) 更新 root 欄位
    if all_received:
        root.shortage_note = ""
        root.isLackMaterial = 99
    else:
        root.shortage_note = "(缺料)"
        root.isLackMaterial = 0


def order_has_lack(s, order_num):
    return s.query(Bom)\
        .join(Material, Bom.material_id == Material.id)\
        .filter(Material.order_num == order_num)\
        .filter(Bom.receive.is_(False))\
        .first() is not None


def normalize_cause_message_list(cause_message_list):
    # 如果是 list → 保持不變
    if isinstance(cause_message_list, list):
        return cause_message_list

    # 如果是字串 → 轉為 list（以「、」或「,」或空白分隔都支援）
    if isinstance(cause_message_list, str):
        # 先去除空白
        cause_message_list = cause_message_list.strip()
        # 判斷分隔符號
        if "、" in cause_message_list:
            return [s.strip() for s in cause_message_list.split("、") if s.strip()]
        elif "," in cause_message_list:
            return [s.strip() for s in cause_message_list.split(",") if s.strip()]
        else:
            # 若沒分隔符號，就視為單一項
            return [cause_message_list]

    # 其他型態（例如 None 或數字）→ 回傳空 list
    return []


# 生成唯一檔案名稱的函式
def get_unique_filename(target_dir, filename, chip):
    base, ext = os.path.splitext(filename)  # 分離檔案名稱與副檔名
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(target_dir, unique_filename)):  # 檢查檔案是否已存在
      unique_filename = f"{base}_{chip}_{counter}{ext}"  # 為檔名新增後綴
      counter += 1
    return unique_filename



"""
def normalize_create_at(raw):
    '''
    把前端丟來的 create_at 正常化成 datetime 物件：
    - 若本來就是 datetime → 直接回傳
    - 若是 timestamp(int/float) → 轉成 datetime
    - 若是字串 → 嘗試用幾種格式解析（含 'Tue, 18 Nov 2025 13:11:52 GMT'）
    '''
    if raw is None:
        return None

    # 已經是 datetime.datetime，就直接用
    if isinstance(raw, dt):
        return raw

    # 若是 timestamp（秒或毫秒）
    if isinstance(raw, (int, float)):
        ts = raw / 1000.0 if raw > 10**10 else raw
        return dt.fromtimestamp(ts)

    # 若是字串
    if isinstance(raw, str):
        txt = raw.strip()
        if not txt:
            return None

        # 1) 先試 RFC 1123 / HTTP Date 格式: "Tue, 18 Nov 2025 13:11:52 GMT"
        try:
            # 注意：這個格式完全符合你 log 看到的字串
            return dt.strptime(txt, "%a, %d %b %Y %H:%M:%S GMT")
        except ValueError:
            pass

        # 2) 再試 ISO 格式（2025-11-18T13:11:52 或 2025-11-18 13:11:52）
        try:
            return dt.fromisoformat(txt.replace('Z', ''))
        except ValueError:
            pass

        # 3) 其它常見格式（看你 DB 實際有沒有用到）
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ):
            try:
                return dt.strptime(txt, fmt)
            except ValueError:
                continue

        # 4) 有小數秒的情況：2025-11-18 13:11:52.123456
        try:
            base, _, _ = txt.partition(".")
            return dt.strptime(base, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

        raise ValueError(f"無法解析 create_at 字串格式: {txt}")

    # 其它型態不支援
    raise TypeError(f"不支援的 create_at 型態: {type(raw)}")
"""


# ------------------------------------------------------------------


# update user's password from user table
@updateTable.route("/updatePassword", methods=['POST'])
def update_password():
    print("updatePassword....")

    request_data = request.get_json()
    userID = request_data['empID']
    newPassword = request_data['newPassword']

    s = Session()
    s.query(User).filter(User.emp_id == userID).update(
      {'password': generate_password_hash(newPassword, method='scrypt')}
    )

    s.commit()
    s.close()

    return jsonify({
      'status': True,
    })


# update user's setting from user table some data
"""
@updateTable.route("/updateSetting", methods=['POST'])
def update_setting():
    print("updateSetting....")

    request_data = request.get_json()
    #print("request_data:", request_data)

    userID = request_data['empID']
    new_isSee = request_data['seeIsOk']
    new_lastRoutingName = request_data['lastRoutingName']
    new_itemsPerPage = request_data['itemsPerPage']

    s = Session()
    # 修改user的設定資料
    _user = s.query(User).filter_by(emp_id = userID).first()
    if new_itemsPerPage != 0:
      s.query(Setting).filter(Setting.id == _user.setting_id).update(
        { 'items_per_page': new_itemsPerPage, 'lastRoutingName': new_lastRoutingName, 'isSee': new_isSee }
      )
    else:
      s.query(Setting).filter(Setting.id == _user.setting_id).update(
        { 'lastRoutingName': new_lastRoutingName, 'isSee': new_isSee }
      )

    s.query(User).filter(User.emp_id == userID).update({'isOnline': False})  # false:user已經登出(logout)

    s.commit()
    s.close()

    return jsonify({
      'status': True,
    })
"""


@updateTable.route("/updateSetting", methods=['POST'])
def update_setting():
    print("updateSetting.")

    request_data = request.get_json(silent=True) or {}

    userID = (request_data.get('empID') or '').strip()
    new_isSee = request_data.get('seeIsOk')
    new_lastRoutingName = request_data.get('lastRoutingName')
    new_itemsPerPage = request_data.get('itemsPerPage', 0)

    if not userID:
      return jsonify({
        'status': False,
        'message': '缺少 empID'
      }), 400

    s = Session()
    try:
      _user = s.query(User).filter_by(emp_id=userID).first()
      if not _user:
        return jsonify({
          'status': False,
          'message': f'找不到使用者: {userID}'
        }), 404

      if not _user.setting_id:
        return jsonify({
          'status': False,
          'message': f'使用者 {userID} 沒有 setting_id'
        }), 400

      update_data = {
        'lastRoutingName': new_lastRoutingName,
        'isSee': new_isSee,
      }

      try:
        items_per_page = int(new_itemsPerPage or 0)
      except Exception:
        items_per_page = 0

      if items_per_page != 0:
        update_data['items_per_page'] = items_per_page

      rows = s.query(Setting).filter(Setting.id == _user.setting_id).update(update_data)

      if rows == 0:
        return jsonify({
          'status': False,
          'message': f'找不到對應 Setting: {_user.setting_id}'
        }), 404

      s.query(User).filter(User.emp_id == userID).update({'isOnline': False})

      s.commit()

      return jsonify({
        'status': True,
        'message': '設定更新成功'
      })
    except Exception as e:
      s.rollback()
      current_app.logger.exception("update_setting failed")
      return jsonify({
        'status': False,
        'message': str(e)
      }), 500
    finally:
      s.close()


# from user table update some data by id
"""
@updateTable.route("/updateUser", methods=['POST'])
def update_user():
    print("updateUser.")

    request_data = request.get_json() or {}

    _emp_id = request_data.get('emp_id', '').strip()
    _emp_name = request_data.get('emp_name', '').strip()
    _dep_name = request_data.get('dep_name', '').strip()
    _emp_perm = request_data.get('emp_perm')
    _routingPriv = request_data.get('routingPriv', '')
    _password_reset = request_data.get('password_reset', 'no')

    # ===== 新增：請假 / 代理資料 =====
    _leave_start = request_data.get('leave_start')
    _leave_end = request_data.get('leave_end')
    _leave_type = request_data.get('leave_type')
    _delegate_emp_id = (request_data.get('delegate_emp_id') or '').strip()

    newPassword = 'a12345678'

    return_value = True
    if _emp_id == "" or _emp_name == "":
        return_value = False
        return jsonify({
            'status': False,
            'message': 'emp_id 或 emp_name 不可為空'
        }), 400

    s = Session()

    try:
        user = s.query(User).filter_by(emp_id=_emp_id).first()
        if not user:
            return jsonify({
                'status': False,
                'message': f'找不到使用者: {_emp_id}'
            }), 404

        if not user.isRemoved:
            return jsonify({
                'status': False,
                'message': f'使用者 {_emp_id} 已刪除或不可更新'
            }), 400

        # ===== 1) 更新 Permission =====
        try:
            _emp_perm = int(_emp_perm)
        except Exception:
            return jsonify({
                'status': False,
                'message': 'emp_perm 格式錯誤'
            }), 400

        _auth_name = (
            'member' if _emp_perm == 4 else
            ('staff' if _emp_perm == 3 else
             ('admin' if _emp_perm == 2 else
              ('system' if _emp_perm == 1 else 'member')))
        )

        s.query(Permission).filter(Permission.id == user.perm_id).update({
            "auth_code": _emp_perm,
            "auth_name": _auth_name
        })

        # ===== 2) 更新 Setting =====
        s.query(Setting).filter(Setting.id == user.setting_id).update({
            "routingPriv": _routingPriv
        })

        # ===== 3) 更新 User =====
        update_user_data = {
            "emp_name": _emp_name,
            "dep_name": _dep_name,
        }

        if _password_reset == 'yes':
            update_user_data["password"] = generate_password_hash(newPassword, method='scrypt')

        s.query(User).filter(User.emp_id == _emp_id).update(update_user_data)

        # ===== 4) 更新 / 新增 UserDelegate =====
        has_any_leave_field = any([_leave_start, _leave_end, _leave_type, _delegate_emp_id])
        leave_fully_set = all([_leave_start, _leave_end, _leave_type, _delegate_emp_id])

        if has_any_leave_field and not leave_fully_set:
            return jsonify({
                'status': False,
                'message': '請假資料需同時填寫：開始時間、結束時間、假別、代理人工號'
            }), 400


        if leave_fully_set:
            start_dt = parse_datetime_or_none(_leave_start)
            end_dt = parse_datetime_or_none(_leave_end)

            if start_dt is None or end_dt is None:
                return jsonify({
                    'status': False,
                    'message': '請假開始/結束日期時間不可為空'
                }), 400

            # 先確認代理人工號是否存在
            delegate_user = s.query(User).filter_by(emp_id=_delegate_emp_id).first()
            if not delegate_user:
                return jsonify({
                    'status': False,
                    'message': f'找不到代理人工號: {_delegate_emp_id}'
                }), 404

            # 找該員工最後一筆 UserDelegate
            delegate_row = (
                s.query(UserDelegate)
                .filter(UserDelegate.user_id == user.id)
                .order_by(UserDelegate.id.desc())
                .first()
            )

            if delegate_row:
                # 有資料就更新
                delegate_row.delegate_emp_id = _delegate_emp_id
                delegate_row.start_date = start_dt
                delegate_row.end_date = end_dt
                delegate_row.reason = _leave_type
            else:
                # 沒資料就新增
                new_delegate = UserDelegate(
                    user_id=user.id,
                    delegate_emp_id=_delegate_emp_id,
                    start_date=start_dt,
                    end_date=end_dt,
                    reason=_leave_type
                )
                s.add(new_delegate)

            # 可選：同步更新 user.is_user_delegate
            user.is_user_delegate = True

        s.commit()

        return jsonify({
            'status': True,
            'message': '更新成功'
        })

    except Exception as e:
        s.rollback()
        current_app.logger.exception("updateUser failed")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

    finally:
        s.close()
"""


@updateTable.route("/updateUser", methods=['POST'])
def update_user():
    print("updateUser.")

    request_data = request.get_json() or {}

    _emp_id = (request_data.get('emp_id') or '').strip()
    _emp_name = (request_data.get('emp_name') or '').strip()
    _dep_name = (request_data.get('dep_name') or '').strip()
    _emp_perm = request_data.get('emp_perm')
    _routingPriv = request_data.get('routingPriv', '')
    _password_reset = request_data.get('password_reset', 'no')

    # ===== 請假 / 代理資料 =====
    _leave_start = (request_data.get('leave_start') or '').strip()
    _leave_end = (request_data.get('leave_end') or '').strip()
    _leave_type = (request_data.get('leave_type') or '').strip()
    _delegate_emp_id = (request_data.get('delegate_emp_id') or '').strip()

    newPassword = 'a12345678'

    if _emp_id == "" or _emp_name == "":
        return jsonify({
            'status': False,
            'message': 'emp_id 或 emp_name 不可為空'
        }), 400

    s = Session()

    try:
        user = s.query(User).filter_by(emp_id=_emp_id).first()
        if not user:
            return jsonify({
                'status': False,
                'message': f'找不到使用者: {_emp_id}'
            }), 404

        if not user.isRemoved:
            return jsonify({
                'status': False,
                'message': f'使用者 {_emp_id} 已刪除或不可更新'
            }), 400

        try:
            _emp_perm = int(_emp_perm)
        except Exception:
            return jsonify({
                'status': False,
                'message': 'emp_perm 格式錯誤'
            }), 400

        _auth_name = (
            'member' if _emp_perm == 4 else
            ('staff' if _emp_perm == 3 else
             ('admin' if _emp_perm == 2 else
              ('system' if _emp_perm == 1 else 'member')))
        )

        # 1) 更新 Permission
        s.query(Permission).filter(Permission.id == user.perm_id).update({
            "auth_code": _emp_perm,
            "auth_name": _auth_name
        })

        print("使用者menu setting:", _routingPriv)
        # 2) 更新 Setting
        s.query(Setting).filter(Setting.id == user.setting_id).update({
            "routingPriv": _routingPriv
        })

        # 3) 更新 User
        update_user_data = {
            "emp_name": _emp_name,
            "dep_name": _dep_name,
        }

        if _password_reset == 'yes':
            update_user_data["password"] = generate_password_hash(newPassword, method='scrypt')

        s.query(User).filter(User.emp_id == _emp_id).update(update_user_data)

        # 4) 更新 / 新增 UserDelegate
        has_any_leave_field = any([_leave_start, _leave_end, _leave_type, _delegate_emp_id])
        leave_fully_set = all([_leave_start, _leave_end, _leave_type, _delegate_emp_id])

        if has_any_leave_field and not leave_fully_set:
            return jsonify({
                'status': False,
                'message': '請假資料需同時填寫：開始時間、結束時間、假別、代理人工號'
            }), 400

        if leave_fully_set:
            start_dt = parse_datetime_or_none(_leave_start)
            end_dt = parse_datetime_or_none(_leave_end)

            if start_dt is None or end_dt is None:
                return jsonify({
                    'status': False,
                    'message': '請假開始/結束日期時間不可為空'
                }), 400

            delegate_user = s.query(User).filter_by(emp_id=_delegate_emp_id).first()
            if not delegate_user:
                return jsonify({
                    'status': False,
                    'message': f'找不到代理人工號: {_delegate_emp_id}'
                }), 404

            delegate_row = (
                s.query(UserDelegate)
                .filter(UserDelegate.user_id == user.id)
                .order_by(UserDelegate.id.desc())
                .first()
            )

            if delegate_row:
                delegate_row.delegate_emp_id = _delegate_emp_id
                delegate_row.start_date = start_dt
                delegate_row.end_date = end_dt
                delegate_row.reason = _leave_type
            else:
                new_delegate = UserDelegate(
                    user_id=user.id,
                    delegate_emp_id=_delegate_emp_id,
                    start_date=start_dt,
                    end_date=end_dt,
                    reason=_leave_type
                )
                s.add(new_delegate)

            user.is_user_delegate = True
        else:
            user.is_user_delegate = False

        s.commit()

        return jsonify({
            'status': True,
            'message': '更新成功'
        })

    except Exception as e:
        s.rollback()
        current_app.logger.exception("updateUser failed")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

    finally:
        s.close()


@updateTable.route('/updateDelegate', methods=['POST'])
def terminate_active():
    print("updateDelegate....")

    data = request.json
    user_id = int(data['user_id'])
    end_date = datetime.fromisoformat(data['end_date'].replace('Z','')) if data.get('end_date') else datetime.now()

    s = Session()
    rows = s.query(UserDelegate).filter(
        UserDelegate.user_id == user_id,
        UserDelegate.start_date <= datetime.now(),
        (UserDelegate.end_date.is_(None)) | (UserDelegate.end_date >= datetime.now())
    ).all()
    for r in rows:
        r.end_date = end_date
    s.commit()
    return jsonify(success=True, affected=len(rows))


# from bom table update some data
@updateTable.route("/updateBoms", methods=['POST'])
def update_boms():
  print("updateBoms....")

  request_data = request.get_json()
  #print("request_data =", request_data, type(request_data))

  s = Session()
  return_value = True

  try:
      # 1️⃣ 把 request_data 統一轉成「list of dict」
      if isinstance(request_data, dict):
          bom_list = list(request_data.values())
      elif isinstance(request_data, list):
          bom_list = request_data
      else:
          bom_list = []
          print("updateBoms: unsupported payload type")

      #print("bom_list:", bom_list, "筆數:", len(bom_list))

      #print("bom_data:")
      for bom_data in bom_list:
          if not isinstance(bom_data, dict):
            continue
          bom_id = bom_data.get('id')
          if not bom_id:
            continue

          bom = s.query(Bom).get(bom_id)
          if not bom:
            print(f"updateBoms: Bom id={bom_id} not found")
            continue

          #print(bom_data)

          # 目前 dialog 主要在改的是 receive / lack / lack_bom_qty / isPickOK
          if 'receive' in bom_data:
              a=bom.receive
              b=bom_data['receive']
              c1=bom.seq_num
              if a != b:
                bom.receive = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.receive: b}, synchronize_session=False)

              #bom.receive = bom_data['receive']
          if 'lack' in bom_data:
              a=bom.lack
              b=bom_data['lack']
              c1=bom.seq_num
              if a != b:
                bom.lack = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.lack: b}, synchronize_session=False)
              #bom.lack = bom_data['lack']
          if 'lack_bom_qty' in bom_data:
              a=bom.lack_bom_qty
              b=bom_data['lack_bom_qty']
              c1=bom.seq_num
              if a != b:
                bom.lack_bom_qty = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.lack_bom_qty: b}, synchronize_session=False)
              #bom.lack_bom_qty = bom_data['lack_bom_qty']
          if 'isPickOK' in bom_data:
              a=bom.isPickOK
              b=bom_data['isPickOK']
              c1=bom.seq_num
              if a != b:
                bom.isPickOK = b
                s.query(Bom)\
                    .filter(Bom.seq_num == c1)\
                    .update({Bom.isPickOK: b}, synchronize_session=False)
              #bom.isPickOK = bom_data['isPickOK']

          # 如果還有其他欄位未來要改，也可以一併加上

      # 找出這次被更新的 BOM 屬於哪些訂單 →
      # 針對每張訂單，重新計算並更新 root  的 shortage_note

      # 把這次 request 裡「有 id 的 BOM」全部抓出來
      touched_bom_ids = [
        bd.get("id") for bd in bom_list
        if isinstance(bd, dict) and bd.get("id")
      ]

      if touched_bom_ids:
        order_nums = [
            x[0] for x in (
              s.query(Material.order_num)
              .join(Bom, Bom.material_id == Material.id)
              .filter(Bom.id.in_(touched_bom_ids))        # 只篩選這次被更新的 BOM
              .distinct()                                 # 避免同一張訂單被拿到多次
              .all()
            )
        ]

        # 對每一張被影響的訂單，重算缺料狀態
        for on in order_nums:
          # # 找出這張訂單的 root material（material.is_copied_from_id = NULL）
          #refresh_root_shortage_note(s, on)
          refresh_root_status(s, on)
      ###

      s.commit()

  except Exception as e:
    s.rollback()
    return_value = False
    print("Error in updateBoms:", e)

  finally:
    s.close()

  return jsonify({
      'status': return_value
  })


@updateTable.route("/updateBomsInMaterial", methods=['POST'])
def update_bom(material_id):
  data = request.json
  material_id = data.get("material_id")
  _bom_data = data.get("bom_data", [])

  s = Session()

  # 驗證 Material 是否存在
  material = s.query(Material).filter_by(id=material_id).first()
  if not material:
    return jsonify({"status": "error", "message": "Material ID not found"}), 404

  # 取得現有的 BOM 資料
  existing_bom = s.query(Bom).filter_by(material_id=material_id).all()
  existing_material_nums = {bom.material_num for bom in existing_bom}

  # 新增的 material_num
  new_entries = []
  for bom_entry in _bom_data:
    material_num = bom_entry.get("material_num")
    if material_num not in existing_material_nums:
      new_bom = Bom(
        material_id=material_id,
        material_num=material_num,
        seq_num=f"SEQ-{len(existing_bom) + len(new_entries) + 1}",  # 自動生成序號
        material_comment=f"Generated for {material_num}",
        req_qty=0
      )
      s.add(new_bom)
      s.flush()  # 提交後才能取得新 ID
      new_entries.append({
        "id": new_bom.id,
        "material_id": material_id,
        "material_num": material_num
      })

  # 提交到資料庫
  s.commit()

  return jsonify({
      "status": "success",
      "message": "BOM updated successfully",
      "new_entries": new_entries
  })


"""
@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
  print("updateAssembleProcessStep....")

  data = request.json

  if not data or 'id' not in data or 'assemble_id' not in data:
    return jsonify({"error": "Missing parameters 'id' or 'assemble_id'"}), 400

  material_id = data['id']
  assemble_id = data['assemble_id']
  return_value = False

  s = Session()

  material_record = s.query(Material).filter_by(id=material_id).first()

  if not material_record:
    return jsonify({"error": f"Material with id {material_id} not found"}), 404

  assemble_record = s.query(Assemble).filter_by(id=assemble_id, material_id=material_id).first()

  target_create_at = normalize_create_at(assemble_record.create_at)

  if not assemble_record:
    return jsonify({"error": f"Assemble with id {assemble_id} and material_id {material_id} not found"}), 404

  #assemble_records = material_record._assemble
  #assemble_records = s.query(Assemble).filter_by(material_id=material_id).all()
  assemble_records = (
    s.query(Assemble)
      .filter(
        and_(
          Assemble.material_id == material_id,
          Assemble.create_at == target_create_at
        )
      )
      .all()
  )



  #if not assemble_records:
  #  return jsonify({"message": f"No assemble records linked to material_id {material_id}"}), 200

  # 檢查 process_step_code 是否全部為 0
  #all_process_step_zero = all(record.process_step_code == 0 for record in assemble_records)


  # 只看 is_copied_from_id 與當前 assemble_record 相同的那一組
  same_group = [r for r in assemble_records
                if r.is_copied_from_id == assemble_record.is_copied_from_id]
                #if r.update_time == assemble_record.update_time]

  # 如果同組至少有一筆，判斷是否全部都是 step=0
  all_process_step_zero = bool(assemble_records) and all(r.process_step_code == 0 for r in assemble_records)

  # 如果條件滿足，更新 material 表
  if all_process_step_zero:
    print("updateAssembleProcessStep , all_process_step_zero", all_process_step_zero)

    material_record.isAssembleStation3TakeOk = True
    assemble_record.isAssembleStationShow = True
    return_value = True
    #return jsonify({"message": "Material updated successfully"}), 200
  else:
    print("updateAssembleProcessStep , not all_process_step_zero")

    material_record.isAssembleStation3TakeOk = False
    assemble_record.isAssembleStationShow = False

    sorted_records = sorted(assemble_records, key=lambda r: r.id)
    current_index = next((i for i, r in enumerate(sorted_records) if r.id == assemble_id), None)

    print("current_index, current_index + 1, len(sorted_records:",current_index, current_index + 1, len(sorted_records))
    if current_index is not None and current_index + 1 < len(sorted_records):
        next_record = sorted_records[current_index + 1]
        #material_record.next_assemble_id = next_record.id  # 設定到 material
        print(f"next_assemble_id 設為 {next_record.id}")

        # 2️⃣ 修改 next_assemble_id record 的 show2_ok = 5
        if next_record.process_step_code == 2:  #下一個程序為檢驗
          next_record.show2_ok = 5
          next_record.total_ask_qty_end = 1
        if next_record.process_step_code == 3:  #下一個程序為雷射
          next_record.show2_ok = 7
          next_record.total_ask_qty_end = 2

        #next_record.completed_qty = assemble_record.completed_qty
        next_record.completed_qty = 0
        print(f"更新 assemble id={next_record.id} 的 show2_ok 為 5")

    return_value = False
    #return jsonify({"message": "Not all process_step_code are zero"}), 200
  s.commit()

  return jsonify({
    'status': return_value
  })
"""


"""
@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
    print("updateAssembleProcessStep.")

    data = request.get_json(silent=True) or {}

    if 'id' not in data or 'assemble_id' not in data:
        return jsonify({
            "status": False,
            "message": "Missing parameters 'id' or 'assemble_id'"
        }), 400

    material_id = data['id']
    assemble_id = data['assemble_id']

    s = Session()
    try:
        material_record = s.query(Material).filter_by(id=material_id).first()
        if not material_record:
            return jsonify({
                "status": False,
                "message": f"Material with id {material_id} not found"
            }), 404

        assemble_record = s.query(Assemble).filter_by(id=assemble_id, material_id=material_id).first()
        if not assemble_record:
            return jsonify({
                "status": False,
                "message": f"Assemble with id {assemble_id} and material_id {material_id} not found"
            }), 404

        # 只處理同一 material 的所有 assemble
        assemble_records = (
            s.query(Assemble)
             .filter(Assemble.material_id == material_id)
             .all()
        )

        if not assemble_records:
            return jsonify({
                "status": False,
                "message": "No assemble rows found"
            }), 200

        #
        finished_work_num = (assemble_record.work_num or '').strip()
        finished_schedule_id = int(assemble_record.schedule_id or 0)
        #

        # ------------------------------------------------------------
        # 1) 只看 未完成(step > 0) 的 rows
        # ------------------------------------------------------------
        active_rows = []
        for r in assemble_records:
            try:
                step = int(r.process_step_code or 0)
            except Exception:
                step = 0

            if step > 0:
                active_rows.append(r)

        # 若全部都 0 -> material 完成
        '''
        if not active_rows:
            material_record.isAssembleStation3TakeOk = True
            #
            ## ✅ 最後完成後，保留在 End.vue 顯示
            #assemble_record.isAssembleStationShow = True
            #
            ## ✅ 進入等待入庫
            #assemble_record.isWarehouseStationShow = True
            #
            ## ✅ 狀態顯示：等待入庫作業
            #assemble_record.show2_ok = 10

            ## 先全部關掉，避免顯示錯的完成列
            #for r in assemble_records:
            #    r.isAssembleStationShow = False
            #
            ## ✅ 選一筆代表等待入庫的 B110
            ## 優先選應完成數量最大的 B110，例如 3377 = 950
            #final_row = (
            #    s.query(Assemble)
            #    .filter(Assemble.material_id == material_id)
            #    .filter(Assemble.work_num.like('%B110%'))
            #    .order_by(cast(Assemble.must_receive_end_qty, Integer).desc(),
            #              Assemble.id.desc()
            #    )
            #    .first()
            #)
            #
            #if final_row:
            #    # 報工完成後，仍留在 End.vue / 組裝結束狀態
            #
            #    final_row.isAssembleStationShow = True
            #    # 但還沒 AGV / 人工送出，所以不能進 Ware~.vue
            #    final_row.isWarehouseStationShow = False
            #    # 先不要設成 10「等待入庫作業」
            #    # 依你的流程，B110 結束通常可用 9：檢驗已結束
            #    #final_row.show2_ok = 10  # 等待入庫作業
            #    final_row.show2_ok = 9                  # 檢驗/組裝已完成，但尚未送入庫
            #    final_row.input_end_disable = True
            #
            # ------------------------------------------------------------
            # ✅ 不固定找 B110
            # 只找「這張工單目前有排程啟用的最後一筆 row」
            #
            # 支援：
            # 1) 只選 assemble mode：最後會是 B109 的最後一道
            # 2) 只選 check mode：最後會是 B110 的最後一道
            # 3) assemble + check 都選：最後通常會是 B110 的最後一道
            # ------------------------------------------------------------

            # 先全部關掉，避免多筆同時留在 End.vue
            for r in assemble_records:
                r.isAssembleStationShow = False

            # 只取這張工單真正有排程的列
            # schedule_id != None 代表是 +工序 產生/啟用的 row
            scheduled_rows = (
                s.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.schedule_id.isnot(None))
                .order_by(
                    Assemble.process_step_code.desc(),   # B109=3 先，B110=2 後面會由完成流程處理
                    Assemble.schedule_id.asc(),
                    Assemble.id.asc()
                )
                .all()
            )

            # 如果找不到 schedule row，就退回用目前完成的這筆
            final_row = None

            if scheduled_rows:
                # 只選 assemble 或只選 check 都可支援
                # 重點：不要固定 B110
                final_row = scheduled_rows[-1]
            else:
                final_row = assemble_record

            if final_row:
                # 按結束後，要留在 End.vue
                final_row.isAssembleStationShow = True

                # 還沒 AGV / 人工送出，不能進 Ware~.vue
                final_row.isWarehouseStationShow = False

                # 9 = 已完成，等待人工/AGV送出
                final_row.show2_ok = 9
                final_row.input_end_disable = True
            #

            s.commit()
            return jsonify({
                "status": True,
                "material_done": True,
                "released_next_group": False,
                "current_group_step": 0,
                "message": "material done"
            }), 200
        '''
        #
        if not active_rows:
            material_record.isAssembleStation3TakeOk = True

            # 先全部關掉，避免多筆同時留在 End.vue
            for r in assemble_records:
                r.isAssembleStationShow = False
                r.input_end_disable = True
                r.input_abnormal_disable = True

            # ⭐ 優先選最後一道 B110 檢驗 row 當「等待送出代表列」
            final_row = (
                s.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == 'B110')
                .filter(Assemble.schedule_id.isnot(None))
                .filter(Assemble.schedule_id > 0)
                .order_by(Assemble.id.desc())
                .first()
            )

            # 若沒有 B110，代表只排組裝，則用最後一筆 B109
            if not final_row:
                final_row = (
                    s.query(Assemble)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == 'B109')
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Assemble.schedule_id > 0)
                    .order_by(Assemble.id.desc())
                    .first()
                )

            if final_row:
                final_row.isAssembleStationShow = True
                final_row.isWarehouseStationShow = False

                # ⭐ 等待人工/AGV送出，不是入庫完成
                final_row.show1_ok = 1
                final_row.show2_ok = 9
                final_row.show3_ok = 9

                final_row.input_disable = True
                final_row.input_end_disable = True
                final_row.input_abnormal_disable = True
                final_row.input_allOk_disable = False

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "final_assemble_id": final_row.id if final_row else None,
                "message": "All process rows done, waiting send out"
            }), 200
        #

        #
        # ⭐ 組裝 B109 全部完成後，釋放全部 B110 檢驗工序
        if finished_work_num == 'B109':
            remaining_b109 = [
                r for r in assemble_records
                if (r.work_num or '').strip() == 'B109'
                and int(r.process_step_code or 0) > 0
                and int(r.schedule_id or 0) > 0
            ]

            if not remaining_b109:
                # 關掉所有 B109，避免 End.vue 繼續顯示已完成組裝
                for r in assemble_records:
                    if (r.work_num or '').strip() == 'B109':
                        r.isAssembleStationShow = False
                        r.input_end_disable = True
                        r.input_abnormal_disable = True

                # 開啟全部 B110，不只第一筆
                released = 0
                for r in assemble_records:
                    if (
                        (r.work_num or '').strip() == 'B110'
                        and int(r.process_step_code or 0) > 0
                        and int(r.schedule_id or 0) > 0
                    ):
                        r.isAssembleStationShow = True
                        r.isWarehouseStationShow = False
                        r.input_disable = False
                        r.input_end_disable = False
                        r.input_allOk_disable = False
                        r.input_abnormal_disable = False
                        r.show1_ok = 1
                        r.show2_ok = 5
                        r.show3_ok = 5
                        released += 1

                material_record.isAssembleStation3TakeOk = False

                s.commit()
                return jsonify({
                    "status": False,
                    "material_done": False,
                    "released_next_group": True,
                    "released_count": released,
                    "current_group_step": 2,
                    "message": "B109 done, released all B110 rows"
                }), 200
        #

        # ------------------------------------------------------------
        # 2) 找目前最高 step 群組（例如 3=B109）
        # ------------------------------------------------------------
        current_group_step = max(int(r.process_step_code or 0) for r in active_rows)

        current_group_rows = [
            r for r in active_rows
            if int(r.process_step_code or 0) == current_group_step
        ]

        # ------------------------------------------------------------
        # 3) 判斷目前群組是否已全部完成
        #    注意：因為這支通常是在某筆先被改成 step=0 後才呼叫，
        #    所以這裡重新抓 current_group_rows 即可
        # ------------------------------------------------------------
        # 若 current_group_rows 仍有資料，表示這個群組還沒全部歸 0
        # 例如：B109 還有 102/103 是 step=3
        if current_group_rows:
            material_record.isAssembleStation3TakeOk = False

            s.commit()
            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": False,
                "current_group_step": current_group_step,
                "message": "current group not finished yet"
            }), 200

        # 理論上跑不到這裡，因為 current_group_step 是從 active_rows 算的
        # 保底留著
        material_record.isAssembleStation3TakeOk = False
        s.commit()

        return jsonify({
            "status": False,
            "material_done": False,
            "released_next_group": False,
            "current_group_step": current_group_step,
            "message": "no state changed"
        }), 200

    except Exception as e:
        s.rollback()
        print("updateAssembleProcessStep error:", e)
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500
    finally:
        s.close()
"""

"""
@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
    print("updateAssembleProcessStep.")

    data = request.get_json(silent=True) or {}

    if 'id' not in data or 'assemble_id' not in data:
        return jsonify({
            "status": False,
            "message": "Missing parameters 'id' or 'assemble_id'"
        }), 400

    material_id = data['id']
    assemble_id = data['assemble_id']

    s = Session()
    try:
        material_record = s.query(Material).filter_by(id=material_id).first()
        if not material_record:
            return jsonify({
                "status": False,
                "message": f"Material with id {material_id} not found"
            }), 404

        assemble_record = (
            s.query(Assemble)
            .filter_by(id=assemble_id, material_id=material_id)
            .first()
        )
        if not assemble_record:
            return jsonify({
                "status": False,
                "message": f"Assemble with id {assemble_id} and material_id {material_id} not found"
            }), 404

        assemble_records = (
            s.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .all()
        )

        if not assemble_records:
            return jsonify({
                "status": False,
                "message": "No assemble rows found"
            }), 200

        finished_work_num = (assemble_record.work_num or '').strip()

        # ------------------------------------------------------------
        # 1) 取目前還沒完成的 assemble rows
        # ------------------------------------------------------------
        active_rows = []
        for r in assemble_records:
            try:
                step = int(r.process_step_code or 0)
            except Exception:
                step = 0

            if step > 0:
                active_rows.append(r)

        # ------------------------------------------------------------
        # 2) 若全部 assemble step 都完成，進入等待送出
        # ------------------------------------------------------------
        if not active_rows:
            material_record.isAssembleStation3TakeOk = True
            '''
            for r in assemble_records:
                r.isAssembleStationShow = False
                r.input_end_disable = True
                r.input_abnormal_disable = True
            '''
            #
            waiting_rows = []

            for r in assemble_records:
                r.input_end_disable = True
                r.input_abnormal_disable = True

                # 已完成且有完成數量的 B110，都要保留在 End.vue 等待送出
                if (
                    (r.work_num or '').strip() == 'B110'
                    and int(r.process_step_code or 0) == 0
                    and int(r.completed_qty or 0) > 0
                ):
                    r.isAssembleStationShow = True
                    r.isWarehouseStationShow = False
                    r.show1_ok = 1
                    r.show2_ok = 9
                    r.show3_ok = 9
                    r.input_disable = True
                    r.input_allOk_disable = False
                    waiting_rows.append(r)
                else:
                    r.isAssembleStationShow = False
            #

            final_row = (
                s.query(Assemble)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == 'B110')
                .filter(Assemble.schedule_id.isnot(None))
                .filter(Assemble.schedule_id > 0)
                .order_by(Assemble.id.desc())
                .first()
            )

            if not final_row:
                final_row = (
                    s.query(Assemble)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == 'B109')
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Assemble.schedule_id > 0)
                    .order_by(Assemble.id.desc())
                    .first()
                )

            if final_row:
                final_row.isAssembleStationShow = True
                final_row.isWarehouseStationShow = False

                final_row.show1_ok = 1
                final_row.show2_ok = 9
                final_row.show3_ok = 9

                final_row.input_disable = True
                final_row.input_end_disable = True
                final_row.input_abnormal_disable = True
                final_row.input_allOk_disable = False

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "final_assemble_id": final_row.id if final_row else None,
                "message": "All process rows done, waiting send out"
            }), 200

        '''
        # ------------------------------------------------------------
        # 3) 組裝 B109 全部完成後，才釋放 B110
        #    重點：
        #    - 不能只看 Assemble.process_step_code
        #    - 要先確認 Process 裡是否還有任何員工正在做 B109
        # ------------------------------------------------------------
        if finished_work_num == 'B109':

            b109_ids = [
                int(r.id)
                for r in assemble_records
                if (r.work_num or '').strip() == 'B109'
                and int(r.schedule_id or 0) > 0
            ]

            b109_active_process_count = 0
            if b109_ids:
                b109_active_process_count = (
                    s.query(Process.id)
                    .filter(Process.material_id == material_id)
                    .filter(Process.assemble_id.in_(b109_ids))
                    .filter(Process.process_type == 21)
                    .filter(Process.has_started.is_(True))
                    .filter(Process.end_time.is_(None))
                    .count()
                )

            if b109_active_process_count > 0:
                material_record.isAssembleStation3TakeOk = False

                s.commit()
                return jsonify({
                    "status": False,
                    "material_done": False,
                    "released_next_group": False,
                    "current_group_step": 3,
                    "active_process_count": b109_active_process_count,
                    "message": "B109 still has active process"
                }), 200

            remaining_b109 = [
                r for r in assemble_records
                if (r.work_num or '').strip() == 'B109'
                and int(r.process_step_code or 0) > 0
                and int(r.schedule_id or 0) > 0
            ]

            if not remaining_b109:
                for r in assemble_records:
                    if (r.work_num or '').strip() == 'B109':
                        r.isAssembleStationShow = False
                        r.input_end_disable = True
                        r.input_abnormal_disable = True

                released = 0
                for r in assemble_records:
                    if (
                        (r.work_num or '').strip() == 'B110'
                        and int(r.process_step_code or 0) > 0
                        and int(r.schedule_id or 0) > 0
                    ):
                        r.isAssembleStationShow = True
                        r.isWarehouseStationShow = False
                        r.input_disable = False
                        r.input_end_disable = False
                        r.input_allOk_disable = False
                        r.input_abnormal_disable = False
                        r.show1_ok = 1
                        r.show2_ok = 5
                        r.show3_ok = 5
                        released += 1

                material_record.isAssembleStation3TakeOk = False

                s.commit()
                return jsonify({
                    "status": False,
                    "material_done": False,
                    "released_next_group": True,
                    "released_count": released,
                    "current_group_step": 2,
                    "message": "B109 done, released all B110 rows"
                }), 200
        '''
        #
        if finished_work_num == 'B109':
            release_result = release_b109_batch_to_b110(
                session=s,
                material_id=material_id
            )

            print("release_b109_batch_to_b110:", release_result)

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": bool(release_result.get("released")),
                "released_count": release_result.get("release_qty", 0),
                "created_ids": release_result.get("created_ids", []),
                "current_group_step": 3,
                "message": release_result.get("message", "")
            }), 200
        #

        #
        # ------------------------------------------------------------
        # 3-1) B110 檢驗結束後，先讓「目前這筆」進入等待送出
        #      即使還有異常返工列未完成，也要保留在 End.vue
        # ------------------------------------------------------------
        if finished_work_num == 'B110':
            assemble_record.process_step_code = 0
            assemble_record.isAssembleStationShow = True
            assemble_record.isWarehouseStationShow = False

            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 9
            assemble_record.show3_ok = 9

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = False

            material_record.isAssembleStation3TakeOk = False

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "waiting_send": True,
                "current_assemble_id": assemble_record.id,
                "message": "B110 finished, current row waiting send"
            }), 200
        #

        # ------------------------------------------------------------
        # 4) 目前群組還沒全部完成
        # ------------------------------------------------------------
        current_group_step = max(int(r.process_step_code or 0) for r in active_rows)

        current_group_rows = [
            r for r in active_rows
            if int(r.process_step_code or 0) == current_group_step
        ]

        if current_group_rows:
            material_record.isAssembleStation3TakeOk = False

            s.commit()
            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": False,
                "current_group_step": current_group_step,
                "message": "current group not finished yet"
            }), 200

        material_record.isAssembleStation3TakeOk = False
        s.commit()

        return jsonify({
            "status": False,
            "material_done": False,
            "released_next_group": False,
            "current_group_step": current_group_step,
            "message": "no state changed"
        }), 200

    except Exception as e:
        s.rollback()
        print("updateAssembleProcessStep error:", e)
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()
"""


"""
@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
    print("updateAssembleProcessStep.")

    data = request.get_json(silent=True) or {}

    if 'id' not in data or 'assemble_id' not in data:
        return jsonify({
            "status": False,
            "message": "Missing parameters 'id' or 'assemble_id'"
        }), 400

    material_id = data['id']
    assemble_id = data['assemble_id']

    s = Session()
    try:
        material_record = s.query(Material).filter_by(id=material_id).first()
        if not material_record:
            return jsonify({
                "status": False,
                "message": f"Material with id {material_id} not found"
            }), 404

        assemble_record = (
            s.query(Assemble)
            .filter_by(id=assemble_id, material_id=material_id)
            .first()
        )
        if not assemble_record:
            return jsonify({
                "status": False,
                "message": f"Assemble with id {assemble_id} and material_id {material_id} not found"
            }), 404

        assemble_records = (
            s.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .all()
        )

        if not assemble_records:
            return jsonify({
                "status": False,
                "message": "No assemble rows found"
            }), 200

        finished_work_num = (assemble_record.work_num or '').strip()

        # ------------------------------------------------------------
        # 1) 取目前還沒完成的 assemble rows
        # ------------------------------------------------------------
        active_rows = []
        for r in assemble_records:
            try:
                step = int(r.process_step_code or 0)
            except Exception:
                step = 0

            if step > 0:
                active_rows.append(r)

        # ------------------------------------------------------------
        # 2) 若全部 assemble step 都完成，進入等待送出
        #    重點：
        #    - 正常 B110 完成 25 要保留
        #    - 異常 B110 完成 10 也要保留
        #    - 不要只保留最後一筆 final_row
        # ------------------------------------------------------------
        if not active_rows:
            material_record.isAssembleStation3TakeOk = True

            waiting_rows = []

            for r in assemble_records:
                work_num = (r.work_num or '').strip()
                step = int(r.process_step_code or 0)
                completed_qty = int(r.completed_qty or 0)

                r.input_end_disable = True
                r.input_abnormal_disable = True

                # 已完成且有完成數量的 B110，都要保留在 End.vue 等待送出
                if (
                    work_num == 'B110'
                    and step == 0
                    and completed_qty > 0
                ):
                    r.isAssembleStationShow = True
                    r.isWarehouseStationShow = False

                    r.show1_ok = 1
                    r.show2_ok = 9
                    r.show3_ok = 9

                    r.input_disable = True
                    r.input_end_disable = True
                    r.input_abnormal_disable = True
                    r.input_allOk_disable = False

                    waiting_rows.append(r)
                else:
                    r.isAssembleStationShow = False

            # 若沒有 B110，才找 B109 當 final row
            final_row = waiting_rows[-1] if waiting_rows else None

            if not final_row:
                final_row = (
                    s.query(Assemble)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == 'B109')
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Assemble.schedule_id > 0)
                    .order_by(Assemble.id.desc())
                    .first()
                )

                if final_row:
                    final_row.isAssembleStationShow = True
                    final_row.isWarehouseStationShow = False

                    final_row.show1_ok = 1
                    final_row.show2_ok = 9
                    final_row.show3_ok = 9

                    final_row.input_disable = True
                    final_row.input_end_disable = True
                    final_row.input_abnormal_disable = True
                    final_row.input_allOk_disable = False

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "final_assemble_id": final_row.id if final_row else None,
                "waiting_count": len(waiting_rows),
                "waiting_ids": [r.id for r in waiting_rows],
                "message": "All process rows done, waiting send out"
            }), 200

        # ------------------------------------------------------------
        # 3) 若 B109 完成，釋放 B110
        # ------------------------------------------------------------
        if finished_work_num == 'B109':
            release_result = release_b109_batch_to_b110(
                session=s,
                material_id=material_id
            )

            print("release_b109_batch_to_b110:", release_result)

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": bool(release_result.get("released")),
                "released_count": release_result.get("release_qty", 0),
                "created_ids": release_result.get("created_ids", []),
                "current_group_step": 3,
                "message": release_result.get("message", "")
            }), 200

        '''
        # ------------------------------------------------------------
        # 3-1) B110 檢驗結束後，先讓「目前這筆」進入等待送出
        #      即使還有異常返工列未完成，也要保留在 End.vue
        # ------------------------------------------------------------
        if finished_work_num == 'B110':
            assemble_record.process_step_code = 0
            assemble_record.isAssembleStationShow = True
            assemble_record.isWarehouseStationShow = False

            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 9
            assemble_record.show3_ok = 9

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = False

            material_record.isAssembleStation3TakeOk = False

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "waiting_send": True,
                "current_assemble_id": assemble_record.id,
                "message": "B110 finished, current row waiting send"
            }), 200
        '''
        #
        if finished_work_num == 'B110':
            # 若同一張工單還有其他 B110 工序未完成，
            # 目前這筆已結束的 b1 / b2 不可留在 End.vue
            remaining_b110 = [
                r for r in assemble_records
                if int(r.id) != int(assemble_record.id)
                and (r.work_num or '').strip() == 'B110'
                and int(r.process_step_code or 0) > 0
                and int(r.schedule_id or 0) > 0
            ]

            if remaining_b110:
                assemble_record.process_step_code = 0
                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False
                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = True
                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 7
                assemble_record.show3_ok = 7

                material_record.isAssembleStation3TakeOk = False

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "waiting_send": False,
                    "message": "B110 row finished, but other B110 rows still active"
                }), 200

            # 沒有其他 B110 未完成，代表檢驗全部完成，才顯示最後待送出列
            for r in assemble_records:
                r.isAssembleStationShow = False

            assemble_record.process_step_code = 0
            assemble_record.isAssembleStationShow = True
            assemble_record.isWarehouseStationShow = False

            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 9
            assemble_record.show3_ok = 9

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = False

            material_record.isAssembleStation3TakeOk = True

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "waiting_send": True,
                "current_assemble_id": assemble_record.id,
                "message": "All B110 rows done, waiting send"
            }), 200
        #

        # ------------------------------------------------------------
        # 4) 目前群組還沒全部完成
        # ------------------------------------------------------------
        current_group_step = max(int(r.process_step_code or 0) for r in active_rows)

        current_group_rows = [
            r for r in active_rows
            if int(r.process_step_code or 0) == current_group_step
        ]

        if current_group_rows:
            material_record.isAssembleStation3TakeOk = False

            s.commit()
            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": False,
                "current_group_step": current_group_step,
                "message": "current group not finished yet"
            }), 200

        material_record.isAssembleStation3TakeOk = False
        s.commit()

        return jsonify({
            "status": False,
            "material_done": False,
            "released_next_group": False,
            "current_group_step": current_group_step,
            "message": "no state changed"
        }), 200

    except Exception as e:
        s.rollback()
        print("updateAssembleProcessStep error:", e)
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()
"""

@updateTable.route('/updateAssembleProcessStep', methods=['POST'])
def update_assemble_process_step():
    print("updateAssembleProcessStep.")

    data = request.get_json(silent=True) or {}

    if 'id' not in data or 'assemble_id' not in data:
        return jsonify({
            "status": False,
            "message": "Missing parameters 'id' or 'assemble_id'"
        }), 400

    material_id = data['id']
    assemble_id = data['assemble_id']

    s = Session()

    try:
        material_record = s.query(Material).filter_by(id=material_id).first()
        if not material_record:
            return jsonify({
                "status": False,
                "message": f"Material with id {material_id} not found"
            }), 404

        assemble_record = (
            s.query(Assemble)
            .filter_by(id=assemble_id, material_id=material_id)
            .first()
        )
        if not assemble_record:
            return jsonify({
                "status": False,
                "message": f"Assemble with id {assemble_id} and material_id {material_id} not found"
            }), 404

        assemble_records = (
            s.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .all()
        )

        if not assemble_records:
            return jsonify({
                "status": False,
                "message": "No assemble rows found"
            }), 200

        finished_work_num = (assemble_record.work_num or '').strip()

        # ------------------------------------------------------------
        # 1) 取目前還沒完成的 assemble rows
        # ------------------------------------------------------------
        active_rows = []
        for r in assemble_records:
            try:
                step = int(r.process_step_code or 0)
            except Exception:
                step = 0

            if step > 0:
                active_rows.append(r)

        # ------------------------------------------------------------
        # 2) 若全部 assemble step 都完成，進入等待送出
        # ------------------------------------------------------------
        if not active_rows:
            material_record.isAssembleStation3TakeOk = True

            waiting_rows = []

            for r in assemble_records:
                work_num = (r.work_num or '').strip()
                step = int(r.process_step_code or 0)
                completed_qty = int(r.completed_qty or 0)

                r.input_end_disable = True
                r.input_abnormal_disable = True

                # 已完成且有完成數量的 B110，都保留在 End.vue 等待送出
                if (
                    work_num == 'B110'
                    and step == 0
                    and completed_qty > 0
                ):
                    r.isAssembleStationShow = True
                    r.isWarehouseStationShow = False

                    r.show1_ok = 1
                    r.show2_ok = 9
                    r.show3_ok = 9

                    r.input_disable = True
                    r.input_end_disable = True
                    r.input_abnormal_disable = True
                    r.input_allOk_disable = False

                    waiting_rows.append(r)
                else:
                    r.isAssembleStationShow = False

            final_row = waiting_rows[-1] if waiting_rows else None

            # 若沒有 B110，代表只做 B109，才找 B109 當等待送出列
            if not final_row:
                final_row = (
                    s.query(Assemble)
                    .filter(Assemble.material_id == material_id)
                    .filter(Assemble.work_num == 'B109')
                    .filter(Assemble.schedule_id.isnot(None))
                    .filter(Assemble.schedule_id > 0)
                    .order_by(Assemble.id.desc())
                    .first()
                )

                if final_row:
                    final_row.isAssembleStationShow = True
                    final_row.isWarehouseStationShow = False

                    final_row.show1_ok = 1
                    final_row.show2_ok = 9
                    final_row.show3_ok = 9

                    final_row.input_disable = True
                    final_row.input_end_disable = True
                    final_row.input_abnormal_disable = True
                    final_row.input_allOk_disable = False

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "final_assemble_id": final_row.id if final_row else None,
                "waiting_count": len(waiting_rows),
                "waiting_ids": [r.id for r in waiting_rows],
                "message": "All process rows done, waiting send out"
            }), 200

        # ------------------------------------------------------------
        # 3) 若 B109 完成
        #    重點：
        #    - 若還有其他 B109 未完成，例如 a1[組裝]-異常，
        #      不可釋放 B110
        #    - 等所有 B109 都完成後，才釋放 B110
        # ------------------------------------------------------------
        if finished_work_num == 'B109':
            remaining_b109 = [
                r for r in assemble_records
                if int(r.id) != int(assemble_record.id)
                and (r.work_num or '').strip() == 'B109'
                and int(r.process_step_code or 0) > 0
                and int(r.schedule_id or 0) > 0
            ]

            if remaining_b109:
                # 原 a1 已完成，關掉它，不再顯示
                assemble_record.process_step_code = 0
                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = True

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 7
                assemble_record.show3_ok = 7

                # 保留 a1[組裝]-異常 顯示在 Begin / End
                for r in remaining_b109:
                    r.isAssembleStationShow = True
                    r.isWarehouseStationShow = False

                    r.input_disable = False
                    r.input_end_disable = False
                    r.input_abnormal_disable = False
                    r.input_allOk_disable = False

                    r.show1_ok = 1
                    r.show2_ok = 3
                    r.show3_ok = 3

                material_record.isAssembleStation3TakeOk = False

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "released_next_group": False,
                    "remaining_b109_count": len(remaining_b109),
                    "message": "B109 row finished, but rework B109 still active"
                }), 200

            # 沒有其他 B109 未完成，才釋放 B110
            release_result = release_b109_batch_to_b110(
                session=s,
                material_id=material_id
            )

            print("release_b109_batch_to_b110:", release_result)

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": bool(release_result.get("released")),
                "released_count": release_result.get("release_qty", 0),
                "created_ids": release_result.get("created_ids", []),
                "current_group_step": 3,
                "message": release_result.get("message", "")
            }), 200

        # ------------------------------------------------------------
        # 4) 若 B110 完成
        # ------------------------------------------------------------
        if finished_work_num == 'B110':
            remaining_b110 = [
                r for r in assemble_records
                if int(r.id) != int(assemble_record.id)
                and (r.work_num or '').strip() == 'B110'
                and int(r.process_step_code or 0) > 0
                and int(r.schedule_id or 0) > 0
            ]

            if remaining_b110:
                assemble_record.process_step_code = 0
                assemble_record.isAssembleStationShow = False
                assemble_record.isWarehouseStationShow = False

                assemble_record.input_disable = True
                assemble_record.input_end_disable = True
                assemble_record.input_abnormal_disable = True
                assemble_record.input_allOk_disable = True

                assemble_record.show1_ok = 1
                assemble_record.show2_ok = 7
                assemble_record.show3_ok = 7

                material_record.isAssembleStation3TakeOk = False

                s.commit()

                return jsonify({
                    "status": False,
                    "material_done": False,
                    "waiting_send": False,
                    "message": "B110 row finished, but other B110 rows still active"
                }), 200

            # 沒有其他 B110 未完成，代表檢驗全部完成
            for r in assemble_records:
                r.isAssembleStationShow = False

            assemble_record.process_step_code = 0
            assemble_record.isAssembleStationShow = True
            assemble_record.isWarehouseStationShow = False

            assemble_record.show1_ok = 1
            assemble_record.show2_ok = 9
            assemble_record.show3_ok = 9

            assemble_record.input_disable = True
            assemble_record.input_end_disable = True
            assemble_record.input_abnormal_disable = True
            assemble_record.input_allOk_disable = False

            material_record.isAssembleStation3TakeOk = True

            s.commit()

            return jsonify({
                "status": True,
                "material_done": True,
                "waiting_send": True,
                "current_assemble_id": assemble_record.id,
                "message": "All B110 rows done, waiting send"
            }), 200

        # ------------------------------------------------------------
        # 5) 目前群組還沒全部完成
        # ------------------------------------------------------------
        current_group_step = max(int(r.process_step_code or 0) for r in active_rows)

        current_group_rows = [
            r for r in active_rows
            if int(r.process_step_code or 0) == current_group_step
        ]

        if current_group_rows:
            material_record.isAssembleStation3TakeOk = False

            s.commit()

            return jsonify({
                "status": False,
                "material_done": False,
                "released_next_group": False,
                "current_group_step": current_group_step,
                "message": "current group not finished yet"
            }), 200

        material_record.isAssembleStation3TakeOk = False
        s.commit()

        return jsonify({
            "status": False,
            "material_done": False,
            "released_next_group": False,
            "current_group_step": current_group_step,
            "message": "no state changed"
        }), 200

    except Exception as e:
        s.rollback()
        print("updateAssembleProcessStep error:", e)
        return jsonify({
            "status": False,
            "message": str(e)
        }), 500

    finally:
        s.close()


@updateTable.route('/sendAssembleToWarehouse', methods=['POST'])
def send_assemble_to_warehouse():
    print("sendAssembleToWarehouse.")

    data = request.get_json(silent=True) or {}
    material_id = data.get('id')
    assemble_id = data.get('assemble_id')
    mode = data.get('mode', 'manual')  # agv / manual

    if not material_id:
        return jsonify({
            "status": False,
            "message": "缺少 material id"
        }), 400

    s = Session()
    try:
        material = s.query(Material).filter(Material.id == material_id).first()
        if not material:
            return jsonify({
                "status": False,
                "message": f"找不到 material id={material_id}"
            }), 404

        if assemble_id:
            target = (
                s.query(Assemble)
                 .filter(Assemble.id == assemble_id)
                 .filter(Assemble.material_id == material_id)
                 .first()
            )
        else:
            target = (
                s.query(Assemble)
                 .filter(Assemble.material_id == material_id)
                 .filter(Assemble.work_num.like('%B110%'))
                 .order_by(
                     cast(Assemble.must_receive_end_qty, Integer).desc(),
                     Assemble.id.desc()
                 )
                 .first()
            )

        if not target:
            return jsonify({
                "status": False,
                "message": "找不到可送入庫的 assemble row"
            }), 404

        # 先關掉同 material 其他入庫顯示，避免同工單多筆出現在 Ware~.vue
        s.query(Assemble).filter(
            Assemble.material_id == material_id
        ).update({
            Assemble.isWarehouseStationShow: False
        }, synchronize_session=False)

        # 只有按 AGV / 人工送出時，才打開 Ware~.vue 顯示
        target.isWarehouseStationShow = True
        target.isAssembleStationShow = False
        target.show2_ok = 10  # 等待入庫作業

        # 紀錄運送方式：True=自，False=人
        material.move_by_automatic_or_manual_2 = True if mode == 'agv' else False
        material.whichStation = 3
        material.show3_ok = 11  # 等待入庫作業

        '''
        #
        # ------------------------------------------------------------
        # AGV 防重：
        # 同一張工單 material_id 只允許一組 29/3 紀錄
        # ------------------------------------------------------------
        if mode == 'agv':
            exists_agv = (
                s.query(Process.id)
                 .filter(Process.material_id == material_id)
                 .filter(Process.process_type.in_([29, 3]))
                 .first()
            )

            if not exists_agv:
                now_str_value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                wait_agv_proc = Process(
                    material_id=material_id,
                    assemble_id=target.id,
                    has_started=True,
                    user_id='AGV',
                    begin_time=now_str_value,
                    end_time=now_str_value,
                    period_time='00:00:00',
                    elapsedActive_time=0,
                    str_elapsedActive_time='00:00:00',
                    is_pause=True,
                    process_type=29,
                    process_work_time_qty=0,
                )
                s.add(wait_agv_proc)

                agv_run_proc = Process(
                    material_id=material_id,
                    assemble_id=target.id,
                    has_started=True,
                    user_id='AGV',
                    begin_time=now_str_value,
                    end_time=now_str_value,
                    period_time='00:00:00',
                    elapsedActive_time=0,
                    str_elapsedActive_time='00:00:00',
                    is_pause=True,
                    process_type=3,
                    process_work_time_qty=0,
                )
                s.add(agv_run_proc)
        #
        '''

        s.commit()

        return jsonify({
            "status": True,
            "message": "已送到成品區，Ware~.vue 可顯示",
            "assemble_id": target.id
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


@updateTable.route('/sendProcessToWarehouse', methods=['POST'])
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

        row.isAssembleStationShow = False
        row.isWarehouseStationShow = True
        row.isStockIn = True

        material.move_by_automatic_or_manual_2 = True if mode == 'agv' else False
        material.whichStation = 3
        material.show2_ok = 6   # 等待入庫作業
        material.show3_ok = 11  # 等待入庫作業 / 成品區

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
@updateTable.route('/updateAssembleProcessStepP', methods=['POST'])
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
"""


@updateTable.route("/updateModifyMaterialAndBoms", methods=['POST'])
def update_modify_material_and_Boms():
  print("updateModifyMaterialAndBoms....")

  data = request.json
  _id = data.get("id")
  _date = data.get("date")
  _qty = data.get("qty")
  #_fileName = data.get("file_name")
  #_bom_data = data.get("bom_data", [])
  #print("bom_data:", _bom_data)

  return_value = True

  update_data = {}
  if _date is not None:
      update_data["material_delivery_date"] = _date #訂單日期
  if _qty is not None:
      update_data["material_qty"] = _qty            #需求數量(訂單數量)
      update_data["total_delivery_qty"] = _qty      #應備數量
  s = Session()

  if update_data:
    rows_updated = s.query(Material).filter(Material.id == _id).update(update_data)

  if rows_updated == 0:
    return_value = False
    raise ValueError("Update failed: no rows affected")

  s.commit()
  '''
  # 取得現有的 BOM 資料
  existing_bom = s.query(Bom).filter_by(material_id = _id).all()
  existing_materials = {bom.material_num for bom in existing_bom}

  for bom_entry in _bom_data:
    material_num = bom_entry.get("material_num")
    if material_num not in existing_materials:
      print("bom_entry:",bom_entry)
      new_bom = Bom(
        material_id = _id,
        material_num = material_num,
        seq_num = bom_entry.get("seq_num"),
        material_comment = bom_entry.get("mtl_comment"),
        req_qty = bom_entry.get("qty"),
        start_date = _date
      )
      s.add(new_bom)

  s.commit()
  '''
  s.close()
  '''
  # 在程式的移動檔案邏輯中使用
  try:
    if return_value:
      _base_dir = current_app.config['baseDir']
      _modify_dir = _base_dir.replace("_in", "_modify")
      _target_dir = _base_dir.replace("_in", "_out")
      _path = _modify_dir + '\\' + _fileName
      print("file_name:", _fileName)

      unique_filename = get_unique_filename(_target_dir, _fileName, "mdf")  # 生成唯一檔案名稱
      unique_target_path = os.path.join(_target_dir, unique_filename)  # 獲取完整目標路徑
      shutil.move(_path, unique_target_path)  # 移動檔案到目標路徑
      print(f"檔案 {_path} 已成功移動到 {unique_target_path}")
  except PermissionError as e:
    print(f"無法移動文件 {_path}，因為它仍然被佔用: {e}")
  except Exception as e:
    print(f"移動檔案時發生錯誤: {e}")
'''
  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateModifyMaterialAndBomsP", methods=['POST'])
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


@updateTable.route("/updateAssmbleDataByMaterialID", methods=['POST'])
def update_assemble_data_by_material_id():
  print("updateAssmbleDataByMaterialID....")

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
      assemble_records = s.query(Assemble).filter(
          Assemble.material_id == _material_id,
          Assemble.must_receive_qty == _delivery_qty
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
      print(f"更新成功，共 {len(assemble_records)} 筆資料")
      return_value = True
      #return
  except Exception as e:
      s.rollback()
      print("更新失敗:", str(e))
      return_value = False
      #return

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateAssmbleDataByMaterialIDP", methods=['POST'])
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


@updateTable.route("/updateProcessDataByMaterialID", methods=['POST'])
def update_process_data_by_material_id():
  print("updateProcessDataByMaterialID....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _seq = request_data.get('seq')
  _record_name1 = request_data.get('record_name1')
  _record_data1 = request_data.get('record_data1')
  #print("material_id, seq, record_name1, record_data1:", _material_id, _seq, _record_name1, _record_data1)

  s = Session()

  try:
    material = s.query(Material).get(_material_id)
    #print("step1")
    if not material:
      return jsonify({'status': False, 'msg': 'Material not found'})
    #print("step2")

    target_process = (s.query(Process).filter(
      Process.material_id == _material_id,
      Process.assemble_id == 0,
      Process.has_started == True,
      Process.begin_time != '',
      Process.end_time != '',)
      .first())

    # 確保 _seq 不超過範圍
    #if _seq < 0 or _seq > len(material._process):
    if not target_process:
      return jsonify({'status': False, 'msg': 'seq out of range'})

    #print("step3")

    # 更新欄位
    if _record_name1 and _record_data1 is not None:
      setattr(target_process, _record_name1, _record_data1)
    #print("step4")

    # 提交更新
    s.commit()
    #print("target_process:", target_process)
    print(f"更新成功!")
    return_value = True
  except Exception as e:
    s.rollback()
    print("更新失敗:", str(e))
    return_value = False

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataByMaterialIDP", methods=['POST'])
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


@updateTable.route("/updateAssembleMustReceiveQtyByAssembleID", methods=['POST'])
def update_assemble_must_receive_qty_by_assemble_id():
    print("updateAssembleMustReceiveQtyByAssembleID....")

    request_data = request.get_json()
    _id = request_data.get('assemble_id')
    #_must_receive_qty = request_data['must_receive_qty']
    #_completed_qty = request_data['completed_qty']

    return_value = True  # true: 資料正確,
    s = Session()

    # 1. 先找出該筆資料
    target = s.query(Assemble).filter(Assemble.id == _id).first()

    if not target:
      print(f"找不到 id={ _id } 的資料")
      return_value = False
      return

    material_id = target.material_id
    must_receive_qty = target.must_receive_qty

    # 2. 查找符合條件的其他資料
    matching_records = s.query(Assemble).filter(
      Assemble.material_id == material_id,
      Assemble.must_receive_qty == must_receive_qty,
      Assemble.process_step_code != 0
    ).all()

    print(f"符合條件的筆數: { len(matching_records) }")

    # 3. 更新符合條件的 must_receive_qty
    for record in matching_records:
      print(f"更新 id={ record.id } 的 must_receive_qty: { record.must_receive_qty } -> { target.completed_qty }")
      record.must_receive_qty = target.completed_qty

    s.commit()

    print("更新完成")

    return jsonify({
      'status': return_value
    })


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialID", methods=['POST'])
def update_assembleMustReceiveQty_by_MaterialID():
  print("updateAssembleMustReceiveQtyByMaterialID....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']
  #print("_order_num, _id, _record_name, _record_data:", _material_id, _record_name, _record_data)

  return_value = True  # true: 資料正確,
  s = Session()

  # 確認 record_name 是 Assemble 的合法欄位
  valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
  if _record_name not in valid_columns:
    return_value = False
    raise ValueError(f"'{ _record_name }' 不是 Assemble 表中的合法欄位")

  # 查詢所有 material_id 相符的 Assemble 記錄
  assemble_records = s.query(Assemble).filter_by(material_id = _material_id).all()
  '''
  assemble_records = (s.query(Assemble).filter(and_(
            Assemble.material_id == _material_id,
            Assemble.must_receive_qty == 0
        )
    )
    .all()
  )
  '''
  if not assemble_records:
    return_value = False
    raise ValueError(f"No Assemble records found for material_id { _material_id }")

  updated_ids = []
  for record in assemble_records:
    setattr(record, _record_name, _record_data)  # 動態設欄位
    updated_ids.append(record.id)

  s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


"""updateTablep
@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDP", methods=['POST'])
def update_assembleMustReceiveQty_by_MaterialID_p():
  print("updateAssembleMustReceiveQtyByMaterialIDP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _material_id = request_data.get('material_id')
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']
  #print("_order_num, _id, _record_name, _record_data:", _material_id, _record_name, _record_data)

  return_value = True  # true: 資料正確,
  s = Session()

  # 確認 record_name 是 Assemble 的合法欄位
  valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
  if _record_name not in valid_columns:
    return_value = False
    raise ValueError(f"'{ _record_name }' 不是 P_Assemble 表中的合法欄位")

  # 查詢所有 material_id 相符的 Assemble 記錄
  assemble_records = s.query(P_Assemble).filter_by(material_id = _material_id).all()

  if not assemble_records:
    return_value = False
    raise ValueError(f"No P_Assemble records found for material_id { _material_id }")

  updated_ids = []
  for record in assemble_records:
    setattr(record, _record_name, _record_data)  # 動態設欄位
    updated_ids.append(record.id)

  s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })
"""


"""
@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDate", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDate....")

    request_data = request.get_json()
    #print("request_data", request_data)

    _material_id   = request_data.get('material_id')
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data['record_name']
    _record_data   = request_data['record_data']

    #print("_material_id, _record_name, _record_data:", _material_id, _record_name, _record_data)
    #print("raw create_at type:", type(_raw_create_at), "value:", _raw_create_at)

    return_value = True
    s = Session()

    try:
        # 1) 檢查欄位是否合法
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return_value = False
            raise ValueError(f"'{_record_name}' 不是 Assemble 表中的合法欄位")

        # 2) 正常化 create_at
        if _raw_create_at is None:
            return_value = False
            raise ValueError("缺少 create_at 參數")

        target_create_at = normalize_create_at(_raw_create_at)
        print("normalized create_at:", target_create_at, "type:", type(target_create_at))

        # 3) 查出同 material_id + 同 create_at 的那一批資料
        assemble_records = (
            s.query(Assemble)
             .filter(
                and_(
                    Assemble.material_id == _material_id,
                    Assemble.create_at == target_create_at
                )
             )
             .all()
        )

        if not assemble_records:
            return_value = False
            raise ValueError(
                f"No Assemble records found for material_id={_material_id} and create_at={_raw_create_at}"
            )

        updated_ids = []
        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated assemble ids:", updated_ids)

        s.commit()

    except Exception as e:
        s.rollback()
        print("update_assembleMustReceiveQty_by_materialID_and_date error:", e)
        raise
    finally:
        s.close()

    return jsonify({
        'status': return_value
    })
"""

@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDate", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDate....")

    request_data = request.get_json() or {}

    _material_id   = request_data.get('material_id')
    _assemble_id   = request_data.get('assemble_id')   # ✅ 新增
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data.get('record_name')
    _record_data   = request_data.get('record_data')

    return_value = True
    s = Session()

    try:
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{_record_name} 不是 Assemble 合法欄位'
            })

        query = s.query(Assemble).filter(Assemble.material_id == _material_id)

        # ✅ 有 assemble_id 時，只更新單筆，避免 3378 的 50 被 3377 的 950 蓋掉
        if _assemble_id is not None and _assemble_id != '':
            query = query.filter(Assemble.id == _assemble_id)

        # ✅ 沒 assemble_id 才走舊邏輯：material_id + create_at
        else:
            if _raw_create_at is None:
                return jsonify({
                    'status': False,
                    'msg': '缺少 assemble_id 或 create_at'
                })

            target_create_at = normalize_create_at(_raw_create_at)
            query = query.filter(Assemble.create_at == target_create_at)

        assemble_records = query.all()

        if not assemble_records:
            return jsonify({
                'status': False,
                'msg': f'No Assemble records found, material_id={_material_id}, assemble_id={_assemble_id}, create_at={_raw_create_at}'
            })

        updated_ids = []

        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated assemble ids:", updated_ids)

        s.commit()

        return jsonify({
            'status': True,
            'updated_ids': updated_ids
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("update_assembleMustReceiveQty_by_materialID_and_date error:", e)
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


"""
@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDateP", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date_p():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDateP....")

    request_data = request.get_json()
    #print("request_data", request_data)

    _material_id   = request_data.get('material_id')
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data['record_name']
    _record_data   = request_data['record_data']

    #print("_material_id, _record_name, _record_data:", _material_id, _record_name, _record_data)
    #print("raw create_at type:", type(_raw_create_at), "value:", _raw_create_at)

    return_value = True
    s = Session()

    try:
        # 1) 檢查欄位是否合法
        valid_columns = [c.key for c in inspect(P_Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return_value = False
            raise ValueError(f"'{_record_name}' 不是 P_Assemble 表中的合法欄位")

        # 2) 正常化 create_at
        if _raw_create_at is None:
            return_value = False
            raise ValueError("缺少 create_at 參數")

        target_create_at = normalize_create_at(_raw_create_at)
        print("normalized create_at:", target_create_at, "type:", type(target_create_at))

        # 3) 查出同 material_id + 同 create_at 的那一批資料
        assemble_records = (
            s.query(P_Assemble)
             .filter(
                and_(
                    P_Assemble.material_id == _material_id,
                    P_Assemble.create_at == target_create_at
                )
             )
             .all()
        )

        if not assemble_records:
            return_value = False
            raise ValueError(
                f"No P_Assemble records found for material_id={_material_id} and create_at={_raw_create_at}"
            )

        updated_ids = []
        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated p assemble ids:", updated_ids)

        s.commit()

    except Exception as e:
        s.rollback()
        print("update_assembleMustReceiveQty_by_materialID_and_date_p error:", e)
        raise
    finally:
        s.close()

    return jsonify({
        'status': return_value
    })
"""


@updateTable.route("/updateAssembleMustReceiveQtyByMaterialIDAndDateP", methods=['POST'])
def update_assembleMustReceiveQty_by_materialID_and_date_p():
    print("updateAssembleMustReceiveQtyByMaterialIDAndDateP....")

    request_data = request.get_json() or {}

    _material_id   = request_data.get('material_id')
    _assemble_id   = request_data.get('assemble_id')   # ✅ 新增
    _raw_create_at = request_data.get('create_at')
    _record_name   = request_data.get('record_name')
    _record_data   = request_data.get('record_data')

    s = Session()

    try:
        valid_columns = [c.key for c in inspect(P_Assemble).mapper.column_attrs]
        if _record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{_record_name} 不是 P_Assemble 合法欄位'
            })

        query = s.query(P_Assemble).filter(P_Assemble.material_id == _material_id)

        # ✅ 有 assemble_id：只更新單筆 P_Assemble
        if _assemble_id is not None and _assemble_id != '':
            query = query.filter(P_Assemble.id == _assemble_id)

        # ✅ 沒 assemble_id：維持舊邏輯，更新同 material_id + create_at 那一批
        else:
            if _raw_create_at is None:
                return jsonify({
                    'status': False,
                    'msg': '缺少 assemble_id 或 create_at'
                })

            target_create_at = normalize_create_at(_raw_create_at)
            query = query.filter(P_Assemble.create_at == target_create_at)

        assemble_records = query.all()

        if not assemble_records:
            return jsonify({
                'status': False,
                'msg': f'No P_Assemble records found, material_id={_material_id}, assemble_id={_assemble_id}, create_at={_raw_create_at}'
            })

        updated_ids = []

        for record in assemble_records:
            setattr(record, _record_name, _record_data)
            updated_ids.append(record.id)

        print("updated p assemble ids:", updated_ids)

        s.commit()

        return jsonify({
            'status': True,
            'updated_ids': updated_ids
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("update_assembleMustReceiveQty_by_materialID_and_date_p error:", e)
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


@updateTable.route("/updateMaterialFields", methods=['POST'])
def update_material_fields():
    data = request.get_json(silent=True) or {}
    mid = data.get("id")
    fields = data.get("fields") or {}
    if not mid or not isinstance(fields, dict) or not fields:
        return jsonify(success=False, message="id / fields 缺失"), 400

    # 允許更新哪些欄位（白名單）
    ALLOWED = {
        "isOpen", "isOpenEmpId", "hasStarted", "startStatus",
        # 需要的話把其他欄位加進來
    }
    BOOLS = {"isOpen", "hasStarted", "startStatus"}

    # 過濾＋型別歸一化
    patch = {}
    for k, v in fields.items():
        if k not in ALLOWED:
            continue
        if k in BOOLS:
            patch[k] = bool(v)
        else:
            patch[k] = v if v is not None else ""

    if not patch:
        return jsonify(success=False, message="無可更新欄位"), 400

    s = Session()
    try:
        # 行鎖避免併發踩踏
        mat = (
            s.query(Material)
             .filter(Material.id == mid)
             .with_for_update()
             .one_or_none()
        )
        if not mat:
            return jsonify(success=False, message="material not found"), 404

        for k, v in patch.items():
            setattr(mat, k, v)

        s.commit()
        return jsonify(success=True, id=mid, updated=patch)
    except Exception as e:
        s.rollback()
        print("update_material_fields failed:", e)  # 或用 logger
        return jsonify(success=False, message="internal error"), 500
    finally:
        s.close()


"""
def sync_assemble_schedule_rows(session, material_id, process_steps):
  #
  #依 material_id 對應的 assemble 紀錄，根據 process_steps 同步 schedule_id 複製列
  #規則：
  #- B109 -> 使用 process_steps['assemble']
  #- B110 -> 使用 process_steps['check']
  #- 每個 work_num 群組保留 1 筆原始紀錄
  #- 其餘 schedule_id 用複製列表示
  #
  #s = Session()

  #assembles = (
  #  s.query(Assemble)
  #  .filter(Assemble.material_id == material_id)
  #  .order_by(Assemble.id.asc())
  #  .all()
  #)

  # 只抓主列
  assembles = (
      session.query(Assemble)
      .filter(
          Assemble.material_id == material_id,
          Assemble.is_copied_from_id.is_(None)
      )
      .all()
  )

  if not assembles:
    return
    #session.close()
    #return jsonify({
    #  'status': False
    #})

  for base in assembles:      # for_loop_a
    ## 只處理主列，避免複製列再被拿來展開
    #if base.is_copied_from_id is not None:
    #  continue

    work_num = (base.work_num or '').strip()

    if 'B109' in work_num:
      target_steps = process_steps.get('assemble', [])
    elif 'B110' in work_num:
      target_steps = process_steps.get('check', [])
    else:
      continue

    checked_ids = [
      int(x.get('id'))
      for x in target_steps
      if x.get('checked') and x.get('id') is not None
    ]

    # 取出這個 base 對應的複製列
    copied_rows = (
      session.query(Assemble)
      .filter(
        Assemble.material_id == base.material_id,
        Assemble.work_num == base.work_num,
        Assemble.is_copied_from_id == base.material_id
      )
      #.order_by(Assemble.id.asc())
      .all()
    )

    existing_copy_ids = {
      int(r.schedule_id): r
      for r in copied_rows
      if r.schedule_id is not None
    }

    # -------------------------
    # 1. 沒有任何勾選
    # -------------------------
    if not checked_ids:
      base.schedule_id = None

      for row in copied_rows:
        session.delete(row)

      continue

    # -------------------------
    # 2. 主列保留第一個 checked id
    # -------------------------
    base_schedule_id = checked_ids[0]
    base.schedule_id = base_schedule_id

    # 其餘要存在於 copied rows
    desired_copy_ids = set(checked_ids[1:])
    existing_copy_id_set = set(existing_copy_ids.keys())

    # -------------------------
    # 3. 刪除不需要的 copied rows
    # -------------------------
    for sid in (existing_copy_id_set - desired_copy_ids):
      session.delete(existing_copy_ids[sid])

    # -------------------------
    # 4. 新增缺少的 copied rows
    # -------------------------
    for sid in (desired_copy_ids - existing_copy_id_set):   # for_loop_b
      new_row = Assemble(
        material_id=base.material_id,
        material_num=base.material_num,
        material_comment=base.material_comment,
        seq_num=base.seq_num,
        work_num=base.work_num,
        process_step_code=base.process_step_code,

        Incoming1_Abnormal=base.Incoming1_Abnormal,
        must_receive_qty=base.must_receive_qty,

        ask_qty=base.ask_qty,
        total_ask_qty=base.total_ask_qty,
        total_ask_qty_end=base.total_ask_qty_end,

        must_receive_end_qty=base.must_receive_end_qty,
        abnormal_qty=base.abnormal_qty,

        user_id=base.user_id,
        writer_id=base.writer_id,
        write_date=base.write_date,

        good_qty=base.good_qty,
        total_good_qty=base.total_good_qty,
        non_good_qty=base.non_good_qty,

        meinh_qty=base.meinh_qty,

        completed_qty=base.completed_qty,
        total_completed_qty=base.total_completed_qty,
        allOk_qty=base.allOk_qty,

        reason=base.reason,
        confirm_comment=base.confirm_comment,
        is_assemble_ok=base.is_assemble_ok,

        currentStartTime=None,
        currentEndTime=None,

        input_disable=base.input_disable,
        input_end_disable=base.input_end_disable,
        input_allOk_disable=base.input_allOk_disable,
        input_abnormal_disable=base.input_abnormal_disable,

        isAssembleStationShow=base.isAssembleStationShow,
        isWarehouseStationShow=base.isWarehouseStationShow,

        alarm_enable=base.alarm_enable,
        alarm_message=base.alarm_message,

        isAssembleFirstAlarm=base.isAssembleFirstAlarm,
        isAssembleFirstAlarm_message=base.isAssembleFirstAlarm_message,
        isAssembleFirstAlarm_qty=base.isAssembleFirstAlarm_qty,

        whichStation=base.whichStation,
        show1_ok=base.show1_ok,
        show2_ok=base.show2_ok,
        show3_ok=base.show3_ok,

        schedule_id=sid,

        is_copied_from_id = base.id
      )
      session.add(new_row)
    # end for_loop_b
  # end for_loop_a

  #session.close()
  #return jsonify({
  #  'status': True,
  #})
"""

"""
def sync_assemble_schedule_rows(session, material_id, process_steps):

    bases = (
        session.query(Assemble)
        .filter(
            Assemble.material_id == material_id,
            Assemble.is_copied_from_id.is_(None),
            Assemble.material_num.isnot(None),
            Assemble.seq_num.isnot(None)
        )
        .all()
    )

    if not bases:
      print("no valid base rows")
      return

    for base in bases:
        print("BASE:", base.id, base.work_num, base.material_num, base.seq_num)

        #if not base.material_num or base.seq_num is None:
        #    print("skip invalid base:", base.id)
        #    continue

        work_num = (base.work_num or '').strip()

        if 'B109' in work_num:
            target_steps = process_steps.get('assemble', [])
        elif 'B110' in work_num:
            target_steps = process_steps.get('check', [])
        else:
            continue

        checked_ids = [
            int(x.get('id'))
            for x in target_steps
            if x.get('checked') and x.get('id') is not None
        ]

        # 🔥 1️⃣ 先刪掉所有 copied rows（關鍵）
        session.query(Assemble).filter(
            #Assemble.material_id == base.material_id,
            #Assemble.work_num == base.work_num,
            Assemble.is_copied_from_id == base.id
        ).delete(synchronize_session=False)

        if not checked_ids:
            base.schedule_id = None
            continue

        # 🔥 2️⃣ 主列
        base.schedule_id = checked_ids[0]

        # 🔥 3️⃣ 重新建立 copied rows
        for sid in checked_ids[1:]:
            new_row = Assemble(
              material_id=base.material_id,
              material_num=base.material_num,
              material_comment=base.material_comment,
              seq_num=base.seq_num,
              work_num=base.work_num,
              process_step_code=base.process_step_code,

              Incoming1_Abnormal=base.Incoming1_Abnormal,
              must_receive_qty=base.must_receive_qty,

              ask_qty=base.ask_qty,
              total_ask_qty=base.total_ask_qty,
              total_ask_qty_end=base.total_ask_qty_end,

              must_receive_end_qty=base.must_receive_end_qty,
              abnormal_qty=base.abnormal_qty,

              user_id=base.user_id,
              writer_id=base.writer_id,
              write_date=base.write_date,

              good_qty=base.good_qty,
              total_good_qty=base.total_good_qty,
              non_good_qty=base.non_good_qty,

              meinh_qty=base.meinh_qty,

              completed_qty=base.completed_qty,
              total_completed_qty=base.total_completed_qty,
              allOk_qty=base.allOk_qty,

              reason=base.reason,
              confirm_comment=base.confirm_comment,
              is_assemble_ok=base.is_assemble_ok,

              currentStartTime=None,
              currentEndTime=None,

              input_disable=base.input_disable,
              input_end_disable=base.input_end_disable,
              input_allOk_disable=base.input_allOk_disable,
              input_abnormal_disable=base.input_abnormal_disable,

              isAssembleStationShow=base.isAssembleStationShow,
              isWarehouseStationShow=base.isWarehouseStationShow,

              alarm_enable=base.alarm_enable,
              alarm_message=base.alarm_message,

              isAssembleFirstAlarm=base.isAssembleFirstAlarm,
              isAssembleFirstAlarm_message=base.isAssembleFirstAlarm_message,
              isAssembleFirstAlarm_qty=base.isAssembleFirstAlarm_qty,

              whichStation=base.whichStation,
              show1_ok=base.show1_ok,
              show2_ok=base.show2_ok,
              show3_ok=base.show3_ok,

              schedule_id=sid,

              is_copied_from_id = base.id
            )
            session.add(new_row)
"""


@updateTable.route("/updateAssembleScheduleRows", methods=['POST'])
def update_assemble_schedule_rows():
    print("updateAssembleScheduleRows....")

    request_data = request.get_json()
    material_id = request_data.get('id')
    process_steps = request_data.get('process_steps') or {}

    abnormal_qty = request_data.get('abnormal_qty', None)
    #print("process_steps:", process_steps)

    s = Session()

    try:
        material = s.query(Material).filter_by(id=material_id).first()

        if not material:
            return jsonify({'status': False, 'msg': 'material not found'})

        # -------------------------
        # 1️⃣ 更新 process_steps
        # -------------------------
        normalized_process_steps = {
            'assemble': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('assemble') or [])
            ],
            'check': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('check') or [])
            ]
        }

        print("normalized_process_steps:", normalized_process_steps)

        material.process_steps = normalized_process_steps

        material.process_step_enable = True

        # -------------------------
        # 2️⃣ 同步 assemble rows
        # -------------------------
        # ✅ 有傳 abnormal_qty，而且不是空值，才帶 qty
        if abnormal_qty is not None and abnormal_qty != '':
            sync_assemble_schedule_rows(
                session=s,
                material_id=material_id,
                process_steps=normalized_process_steps,
                qty=abnormal_qty
            )
        else:
            sync_assemble_schedule_rows(
                session=s,
                material_id=material_id,
                process_steps=normalized_process_steps
            )

        #
        # 關鍵：sync 內有 delete copied rows，所以先 flush
        s.flush()

        # 關鍵：清掉 session 內舊的 Assemble ORM 狀態，避免 StaleDataError
        s.expire_all()

        # 重新抓 material，避免 expire_all 後物件狀態舊
        material = s.query(Material).filter(Material.id == material_id).first()
        if material:
            # material 重新 query 一次，因為 expire_all() 後原物件可能已過期。
            material.process_steps = normalized_process_steps
            material.process_step_enable = True
        #

        # -------------------------
        # 3️⃣ commit
        # -------------------------
        s.commit()

        return jsonify({
           'status': True,
           'process_steps': material.process_steps,
           'msg': 'ok!'
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("updateAssembleScheduleRows ERROR:", repr(e))
        return jsonify({
           'status': False,
           'msg': str(e),
        })
    finally:
        s.close()


def add_assemble_schedule_rows_by_abnormal(session, material_id, process_steps, qty):
    print("add_assemble_schedule_rows_by_abnormal....")
    print("material_id:", material_id)
    print("qty:", qty)

    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise Exception(f"material not found: {material_id}")

    try:
        target_qty = int(qty or 0)
    except Exception:
        target_qty = 0

    if target_qty <= 0:
        raise Exception("abnormal_qty must > 0")

    all_rows = (
        session.query(Assemble)
        .filter(Assemble.material_id == material_id)
        .all()
    )

    def get_any_template_row():
        # 優先找主列
        for row in all_rows:
            if row.is_copied_from_id is None:
                return row

        return all_rows[0] if all_rows else None

    def create_row_from_template(template, work_num, process_step_code, schedule_id, copied_from_id=None, reason_text=''):
        new_row = Assemble(
            material_id=material.id,
            material_num=material.material_num,
            material_comment=material.material_comment,
            seq_num=getattr(template, 'seq_num', 10) if template else 10,

            work_num=work_num,
            process_step_code=process_step_code,
            schedule_id=schedule_id,
            is_copied_from_id=copied_from_id,

            Incoming1_Abnormal=getattr(template, 'Incoming1_Abnormal', '') if template else '',

            # ✅ 異常返工數量
            must_receive_qty=target_qty,
            ask_qty=target_qty,
            total_ask_qty=target_qty,
            #total_ask_qty_end=0,
            must_receive_end_qty=target_qty,
            #reason=reason_text,

            #abnormal_qty=0,
            # 異常返工數量
            abnormal_qty=target_qty,

            user_id=getattr(template, 'user_id', material.isOpenEmpId) if template else material.isOpenEmpId,
            writer_id=None,
            write_date=None,

            good_qty=0,
            total_good_qty=0,
            non_good_qty=0,
            meinh_qty=0,

            completed_qty=0,
            total_completed_qty=0,
            allOk_qty=0,

            #reason='',
            #
            reason='異常返工',
            #
            confirm_comment='',
            is_assemble_ok=0,

            currentStartTime=None,
            currentEndTime=None,

            input_disable=1,
            input_end_disable=0,
            input_allOk_disable=0,
            input_abnormal_disable=0,

            isAssembleStationShow=getattr(template, 'isAssembleStationShow', 0) if template else 0,
            isWarehouseStationShow=getattr(template, 'isWarehouseStationShow', 0) if template else 0,

            alarm_enable=1,
            alarm_message='',

            isAssembleFirstAlarm=1,
            isAssembleFirstAlarm_message='',
            isAssembleFirstAlarm_qty=0,

            whichStation=getattr(template, 'whichStation', material.whichStation) if template else material.whichStation,
            show1_ok=getattr(template, 'show1_ok', material.show1_ok) if template else material.show1_ok,
            show2_ok=getattr(template, 'show2_ok', material.show2_ok) if template else material.show2_ok,
            show3_ok=getattr(template, 'show3_ok', material.show3_ok) if template else material.show3_ok,
        )

        session.add(new_row)
        session.flush()
        return new_row

    def add_group_rows(work_num, process_step_code, target_steps):
        checked_ids = [
            int(x.get('id'))
            for x in (target_steps or [])
            if x.get('checked') and x.get('id') is not None
        ]

        if not checked_ids:
            print(f"{work_num} no checked steps, skip")
            return []

        template = get_any_template_row()
        created_rows = []

        # 第一個 checked step 建主列
        base = create_row_from_template(
            template=template,
            work_num=work_num,
            process_step_code=process_step_code,
            schedule_id=checked_ids[0],
            copied_from_id=None,
            #target_qty=abnormal_qty,
            reason_text='異常返工',
        )

        created_rows.append(base)

        # 其餘 checked step 建 copied rows
        for sid in checked_ids[1:]:
            copied = create_row_from_template(
                template=base,
                work_num=work_num,
                process_step_code=process_step_code,
                schedule_id=sid,
                copied_from_id=base.id,
                reason_text='異常返工',
            )
            created_rows.append(copied)

        print(
            f"created abnormal schedule rows: "
            f"material_id={material_id}, work_num={work_num}, count={len(created_rows)}"
        )

        return created_rows

    created = []

    # B109 = 組裝
    created += add_group_rows(
        work_num='B109',
        process_step_code=3,
        target_steps=process_steps.get('assemble', [])
    )

    # B110 = 檢驗
    created += add_group_rows(
        work_num='B110',
        process_step_code=2,
        target_steps=process_steps.get('check', [])
    )

    return created


@updateTable.route("/addAssembleScheduleRows", methods=['POST'])
def add_assemble_schedule_rows():
    print("addAssembleScheduleRows....")

    request_data = request.get_json() or {}

    material_id = request_data.get('id')
    process_steps = request_data.get('process_steps') or {}
    abnormal_qty = request_data.get('abnormal_qty', None)

    s = Session()

    try:
        if not material_id:
            return jsonify({'status': False, 'msg': 'missing material id'})

        if abnormal_qty is None or abnormal_qty == '':
            return jsonify({'status': False, 'msg': 'missing abnormal_qty'})

        normalized_process_steps = {
            'assemble': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('assemble') or [])
            ],
            'check': [
                {
                    'id': int(x.get('id')) if x.get('id') is not None else None,
                    'name': x.get('name', ''),
                    'checked': bool(x.get('checked'))
                }
                for x in (process_steps.get('check') or [])
            ]
        }

        #print("normalized_process_steps:", normalized_process_steps)
        #print("abnormal_qty:", abnormal_qty)

        created_rows = add_assemble_schedule_rows_by_abnormal(
            session=s,
            material_id=material_id,
            process_steps=normalized_process_steps,
            qty=abnormal_qty
        )

        s.commit()

        return jsonify({
            'status': True,
            'msg': 'add assemble schedule rows ok',
            'created_count': len(created_rows),
            'created_ids': [row.id for row in created_rows]
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        print("addAssembleScheduleRows ERROR:", repr(e))
        return jsonify({
            'status': False,
            'msg': str(e)
        })

    finally:
        s.close()


@updateTable.route("/updateAssembleFieldByAssembleID", methods=['POST'])
def update_assemble_field_by_assemble_id():
    print("updateAssembleFieldByAssembleID....")

    request_data = request.get_json() or {}
    assemble_id = request_data.get('assemble_id')
    record_name = request_data.get('record_name')
    record_data = request_data.get('record_data')

    if not assemble_id:
        return jsonify({'status': False, 'msg': 'missing assemble_id'})

    s = Session()

    try:
        valid_columns = [c.key for c in inspect(Assemble).mapper.column_attrs]
        if record_name not in valid_columns:
            return jsonify({
                'status': False,
                'msg': f'{record_name} 不是 Assemble 合法欄位'
            })

        asm = s.query(Assemble).filter(Assemble.id == assemble_id).first()
        if not asm:
            return jsonify({
                'status': False,
                'msg': f'assemble_id={assemble_id} not found'
            })

        setattr(asm, record_name, record_data)

        s.commit()

        return jsonify({
            'status': True,
            'assemble_id': assemble_id,
            'record_name': record_name,
            'record_data': record_data
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({'status': False, 'msg': str(e)})

    finally:
        s.close()


"""
# from material table update some data by id or orde_num
@updateTable.route("/updateMaterial", methods=['POST'])
def update_material():
    print("updateMaterial....")

    request_data = request.get_json()
    #print("request_data", request_data)
    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']
    #print("_order_num, _id, _record_name, _record_data:", _order_num, _id, _record_name, _record_data)

    return_value = True  # true: 資料正確, 註冊成功
    s = Session()

    # 查找對應的記錄
    #material_record = s.query(Material).filter_by(order_num = _order_num).first()

    # 檢查傳入的參數，選擇查詢條件
    material_record = None
    if _order_num is not None:  # 如果傳入了 order_num
        material_record = s.query(Material).filter_by(order_num=_order_num).first()
    elif _id is not None:  # 如果傳入了 id
        material_record = s.query(Material).filter_by(id=_id).first()

    if material_record is None:
      return_value = False
    else:
      # 動態設置欄位值
      if hasattr(material_record, _record_name):

        # +工序按鍵狀態
        #if _record_name == 'process_step_enable':
        if _record_name in ['process_step_enable', 'merge_enabled']:
            if isinstance(_record_data, str):
                v = _record_data.strip().lower()
                if v in ['1', 'true', 'yes', 'y', 'on']:
                    _record_data = True
                elif v in ['0', 'false', 'no', 'n', 'off', '']:
                    _record_data = False
            else:
                _record_data = bool(_record_data)

        setattr(material_record, _record_name, _record_data)
        s.commit()

    '''
    try:
      # 查找對應的記錄
      material_record = s.query(Material).filter_by(order_num = _order_num).first()

      # 動態設置欄位值
      if hasattr(material_record, _record_name):
          setattr(material_record, _record_name, _record_data)
          s.commit()
          #print(f"Updated {material_record} with {_record_name} = {_record_data}")
      else:
          #print(f"Field {_record_name} does not exist in Material.")
          return_value = False

    except Exception as e:
        s.rollback()
        print(f"Error: {e}")
        return_value = False
    '''
    s.commit()
    s.close()

    return jsonify({
      'status': return_value
    })
"""


@updateTable.route("/updateMaterial", methods=['POST'])
def update_material():
    print("updateMaterial....")

    request_data = request.get_json() or {}

    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data.get('record_name')
    _record_data = request_data.get('record_data')

    s = Session()

    try:
        material_record = None

        if _id is not None:
            material_record = s.query(Material).filter_by(id=_id).first()
        elif _order_num is not None:
            material_record = s.query(Material).filter_by(order_num=_order_num).first()

        if material_record is None:
            return jsonify({'status': False, 'message': 'Material not found'})

        if not hasattr(material_record, _record_name):
            return jsonify({'status': False, 'message': f'欄位不存在: {_record_name}'})

        # boolean 欄位轉型
        if _record_name in ['process_step_enable', 'merge_enabled']:
            if isinstance(_record_data, str):
                v = _record_data.strip().lower()
                if v in ['1', 'true', 'yes', 'y', 'on']:
                    _record_data = True
                elif v in ['0', 'false', 'no', 'n', 'off', '']:
                    _record_data = False
            else:
                _record_data = bool(_record_data)

        setattr(material_record, _record_name, _record_data)

        s.commit()

        return jsonify({'status': True})

    except Exception as e:
        s.rollback()
        print("updateMaterial error:", e)
        return jsonify({'status': False, 'message': str(e)})

    finally:
        s.close()


@updateTable.route("/updateMaterialP", methods=['POST'])
def update_material_p():
    print("updateMaterialP....")

    request_data = request.get_json()
    #print("request_data", request_data)
    _order_num = request_data.get('order_num')
    _id = request_data.get('id')
    _record_name = request_data['record_name']
    _record_data = request_data['record_data']
    #print("_order_num, _id, _record_name, _record_data:", _order_num, _id, _record_name, _record_data)

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
      if hasattr(material_record, _record_name):
        setattr(material_record, _record_name, _record_data)
        s.commit()

    s.close()

    return jsonify({
      'status': return_value
    })


# from material table update some data by id
@updateTable.route("/updateAssemble", methods=['POST'])
def update_assemble():
  print("updateAssemble....")

  request_data = request.get_json()
  #print("request_data", request_data)
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
  assemble_record = s.query(Assemble).filter_by(id = _assemble_id).first()

  # 動態設置欄位值
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# from material table update some data by id
@updateTable.route("/updateAssembleP", methods=['POST'])
def update_assemble_p():
  print("updateAssembleP....")

  request_data = request.get_json()
  #print("request_data", request_data)
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
  if hasattr(assemble_record, _record_name):
    setattr(assemble_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# from material table update some data by id
@updateTable.route("/updateProcessData", methods=['POST'])
def update_process_data():
  print("updateProcessData....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  #print("_record_name:", _record_name)

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


@updateTable.route("/updateProcessDataP", methods=['POST'])
def update_process_data_p():
  print("updateProcessDataP....")

  request_data = request.get_json()
  #print("request_data", request_data)
  _process_id = request_data['process_id']
  _record_name = request_data['record_name']
  _record_data = request_data['record_data']

  return_value = True  # true: 資料正確, 註冊成功
  s = Session()

  # 查找對應的記錄
  process_record = s.query(P_Process).filter_by(id = _process_id).first()

  # 動態設置欄位值
  if hasattr(process_record, _record_name):
    setattr(process_record, _record_name, _record_data)
    s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# from material table update some data by id
@updateTable.route("/updateMaterialRecord", methods=['POST'])
def update_material_record():
  print("updateMaterialRecord....")

  request_data = request.get_json()

  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  _show1_ok = request_data['show1_ok']
  _show2_ok = request_data['show2_ok']
  _show3_ok = request_data['show3_ok']
  _whichStation = request_data['whichStation']

  s = Session()

  if _order_num is not None:  # 如果傳入了 order_num
    s.query(Material).filter(Material.order_num == _order_num).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      "whichStation": _whichStation,
    })
  elif _id is not None:  # 如果傳入了 id
    s.query(Material).filter(Material.id == _id).update({
      "show1_ok": _show1_ok,
      "show2_ok": _show2_ok,
      "show3_ok": _show3_ok,
      "whichStation": _whichStation,
    })

  s.commit()

  s.close()

  return jsonify({
    'status': True
  })


@updateTable.route("/updateMaterialRecordP", methods=['POST'])
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


# from reagent table update some data by id
@updateTable.route("/updatePermissions", methods=['POST'])
def update_permissions():
  print("updatePermissions....")

  request_data = request.get_json()

  _id = request_data['perm_empID']

  _system = request_data['perm_checkboxForSystem']
  _admin = request_data['perm_checkboxForAdmin']
  _member = request_data['perm_checkboxForMember']

  return_value = True  # true: 資料正確, 註冊成功
  if _id == "":
      return_value = False  # false: 資料不完全 註冊失敗

  s = Session()
  if return_value:
      # 以最高權限寫入資料庫
      if _member:
          _p_id = 4
      if _admin:
          _p_id = 3
      if _system:
          _p_id = 2

      s.query(User).filter(User.emp_id == _id).update(
          {"perm_id": _p_id})

      s.commit()

  s.close()

  return jsonify({
    'status': return_value
  })


# create agv data table
@updateTable.route("/updateAGV", methods=['POST'])
def update_agv():
  print("updateAGV....")

  request_data = request.get_json()

  _id = request_data['id']
  _status = request_data['status']
  _station =  request_data['station']

  s = Session()

  s.query(Agv).filter(Agv.id == _id).update({
    "status": _status,
    "station": _station
  })

  s.commit()

  s.close()

  return jsonify({
    'status': True
  })


"""
@updateTable.route("/updateAssembleAlarmMessage", methods=["POST"])
def update_assemble_alarm_message():
    print("updateAssembleAlarmMessage....")

    data = request.get_json()

    assemble_id = data.get("assemble_id")
    #print("assemble_id:", assemble_id)
    cause_message_list = data.get("cause_message")  # 前端預期傳 list 或字串
    #print("cause_message_list:", cause_message_list)
    cause_user = data.get("cause_user")
    #print("cause_user:", cause_user)

    s = Session()

    try:
        # 1) 先抓本尊那筆 assemble
        assemble_record = s.query(Assemble).get(assemble_id)
        pre_assemble_record = s.query(Assemble).get(assemble_id-1)
        if not assemble_record or not pre_assemble_record:
            s.close()
            return jsonify({"status": False, "message": "Assemble record not found"}), 404

        # 2) 把 cause_message_list 轉成要存進 String(250) 的字串
        #    - 若是 list: 用 "、" 接起來
        #    - 若是字串: 直接用
        #    - 其他型態: 強制轉字串
        if isinstance(cause_message_list, list):
            alarm_message_str = "、".join(str(x).strip() for x in cause_message_list if str(x).strip())
        elif isinstance(cause_message_list, str):
            alarm_message_str = cause_message_list.strip()
        else:
            alarm_message_str = str(cause_message_list or "").strip()

        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # 3) 更新本尊那筆
        assemble_record.alarm_message = alarm_message_str
        #assemble_record.alarm_message = ''
        assemble_record.writer_id = cause_user
        assemble_record.write_date = now_str
        assemble_record.isAssembleFirstAlarm = True
        assemble_record.alarm_enable = False

        # 4) 同步到所有「從這筆複製出去」的資料
        #    透過 model 上設定的 backref: copied_to
        #    copied_to = 所有 is_copied_from_id = assemble_record.id 的子筆數
        for child in assemble_record.copied_to:
          print("child.id:", child.id)
          # 只更新 user_id 有值的子筆數
          if child.user_id and str(child.user_id).strip() != "":
              child.alarm_message = alarm_message_str
              child.writer_id = cause_user
              child.write_date = now_str
              child.isAssembleFirstAlarm = False
              child.alarm_enable = False

        for child in pre_assemble_record.copied_to:
          print("child.id:", child.id)
          # 只更新 user_id 有值的子筆數
          if child.user_id and str(child.user_id).strip() != "":
              child.alarm_message = alarm_message_str
              child.writer_id = cause_user
              child.write_date = now_str
              child.isAssembleFirstAlarm = False
              child.alarm_enable = False

        # 如果沒有用 backref，也可以用下面這種查詢方式 (擇一即可)
        # children = (
        #     s.query(Assemble)
        #      .filter(Assemble.is_copied_from_id == assemble_id)
        #      .all()
        # )
        # for child in children:
        #     child.alarm_message = alarm_message_str
        #     child.writer_id = cause_user
        #     child.write_date = now_str

        s.commit()

        return jsonify({
            "status": True,
            "message": "Alarm message updated successfully"
        })

    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "message": str(e)}), 500

    finally:
        s.close()
"""


@updateTable.route("/updateAssembleAlarmMessage", methods=["POST"])
def update_assemble_alarm_message():
    print("updateAssembleAlarmMessage....")

    data = request.get_json(silent=True) or {}

    assemble_id = data.get("assemble_id")
    #alarm_message = (data.get("alarm_message") or "").strip()
    raw_message = data.get("alarm_message", None)

    if raw_message is None:
        raw_message = data.get("cause_message", "")

    if isinstance(raw_message, list):
        alarm_message = "、".join(str(x).strip() for x in raw_message if str(x).strip())
    else:
        alarm_message = str(raw_message or "").strip()

    if not assemble_id:
        return jsonify({
            "status": False,
            "message": "assemble_id 不可為空"
        }), 400

    s = Session()

    try:
        assemble = (
            s.query(Assemble)
            .filter(Assemble.id == assemble_id)
            .first()
        )

        if not assemble:
            return jsonify({
                "status": False,
                "message": "找不到 Assemble"
            }), 404

        # --------------------------------------------------
        # 1. 更新來源列
        # --------------------------------------------------
        assemble.alarm_enable = False
        assemble.alarm_message = alarm_message
        assemble.confirm_comment = alarm_message
        assemble.Incoming1_Abnormal = alarm_message

        # --------------------------------------------------
        # 2. 找第一層返工列(B109)
        # --------------------------------------------------
        level1_ids = [
            r.id
            for r in (
                s.query(Assemble)
                .filter(Assemble.is_copied_from_id == assemble.id)
                .all()
            )
        ]

        # --------------------------------------------------
        # 3. 更新所有返工列(B109、B110...)
        # --------------------------------------------------
        rework_rows = (
            s.query(Assemble)
            .filter(
                Assemble.material_id == assemble.material_id
            )
            .filter(
                Assemble.reason == "異常返工"
            )
            .filter(
                or_(
                    Assemble.is_copied_from_id == assemble.id,
                    Assemble.is_copied_from_id.in_(level1_ids) if level1_ids else False
                )
            )
            .all()
        )

        for row in rework_rows:
            row.alarm_message = alarm_message
            row.confirm_comment = alarm_message
            row.Incoming1_Abnormal = alarm_message

        s.commit()

        return jsonify({
            "status": True,
            "message": "異常原因已更新",
            "update_count": len(rework_rows) + 1
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


@updateTable.route("/updateBomXorReceive", methods=["POST"])
def update_bom_xor_receive():
    print("updateBomXorReceive....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")
    print("copied_id", copied_id)

    s = Session()

    # 找到複製資料
    copied_material = s.query(Material).options(joinedload(Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied material or missing source ID"}), 400
    print("copied_material:",copied_material)

    # 找到原始資料
    source_material = s.query(Material).options(joinedload(Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source material not found"}), 404
    print("source_material:",source_material)

    # 條件限制：兩者其中之一 isLackMaterial 必須為 0 才繼續
    if source_material.isLackMaterial != 0 and copied_material.isLackMaterial != 0:
        return jsonify({"message": "No update required, neither material has isLackMaterial == 0"}), 200

    # 建立 dict 以 seq_num 為 key 對應 receive
    source_boms = {bom.seq_num: bom for bom in source_material._bom}
    copied_boms = {bom.seq_num: bom for bom in copied_material._bom}
    #print("source_boms:",source_boms)
    #print("copied_boms:",copied_boms)

    updated = False
    for seq_num, source_bom in source_boms.items():
        if seq_num in copied_boms:
            copied_bom = copied_boms[seq_num]
            xor_result = int(source_bom.receive) ^ int(copied_bom.receive)
            if xor_result == 1:
                source_bom.receive = True  # 將缺料清除
                source_material.isLackMaterial = 99
                #source_material.show2_ok = 3        # 等待組裝作業
                copied_material.isLackMaterial = 0
                updated = True
            #else:
            #    source_material.isLackMaterial = 0
            #    updated = True

    if updated:
        ###
        refresh_root_shortage_note(s, source_material.order_num)
        ###
        s.commit()

    s.close()

    return jsonify({
      'status': True,
      'message': "Updated successfully."
    })


@updateTable.route("/updateBomXorReceiveP", methods=["POST"])
def update_bom_xor_receive_p():
    print("updateBomXorReceiveP....")

    data = request.get_json()
    copied_id = data.get("copied_material_id")
    #print("copied_id", copied_id)

    s = Session()

    # 找到複製資料
    copied_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_id).first()
    if not copied_material or not copied_material.is_copied_from_id:
        return jsonify({"error": "Invalid copied p_material table or missing source ID"}), 400
    #print("copied_material:",copied_material)

    # 找到原始資料
    source_material = s.query(P_Material).options(joinedload(P_Material._bom)).filter_by(id=copied_material.is_copied_from_id).first()
    if not source_material:
        return jsonify({"error": "Source p_material not found"}), 404
    #print("source p_material:",source_material)

    # 條件限制：兩者其中之一 isLackMaterial 必須為 0 才繼續
    if source_material.isLackMaterial != 0 and copied_material.isLackMaterial != 0:
        return jsonify({"message": "No update required, neither material has isLackMaterial == 0"}), 200

    # 建立 dict 以 seq_num 為 key 對應 receive
    source_boms = {bom.seq_num: bom for bom in source_material._bom}
    copied_boms = {bom.seq_num: bom for bom in copied_material._bom}
    #print("source_boms:",source_boms)
    #print("copied_boms:",copied_boms)

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


@updateTable.route("/updateProduct", methods=["POST"])
def update_product():
    print("updateProduct....")

    s = Session()
    try:
        data = request.get_json(silent=True) or {}
        items = data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return jsonify({"ok": False, "error": "items 必須為非空陣列"}), 400

        # 取出所有 material_id
        try:
            mids = [int(it["material_id"]) for it in items if "material_id" in it]
        except (KeyError, TypeError, ValueError):
            return jsonify({"ok": False, "error": "每筆必須含 material_id（整數）"}), 400

        # 檢查 material 是否存在
        exist_mid = set(x[0] for x in s.query(Material.id).filter(Material.id.in_(mids)).all())
        not_found = [mid for mid in mids if mid not in exist_mid]
        if not_found:
            return jsonify({"ok": False, "error": f"找不到 material_id: {not_found}"}), 400

        # 先抓現有的 Product（假設一個 material_id 對應一筆 Product）
        exist_products = s.query(Product).filter(Product.material_id.in_(mids)).all()
        by_mid = {p.material_id: p for p in exist_products}

        # 處理每筆
        for it in items:
            mid = int(it["material_id"])
            p = by_mid.get(mid)
            if p is None:
                p = Product(
                    material_id   = mid,
                    delivery_qty  = 0,
                    assemble_qty  = 0,
                    allOk_qty     = 0,
                    good_qty      = 0,
                    non_good_qty  = 0,
                    reason        = None,
                    confirm_comment = None,
                )
                s.add(p)
                by_mid[mid] = p

            # ---- 1) 累加欄位 ----
            for f in ("allOk_qty", "good_qty", "non_good_qty"):
                if f in it:
                    inc = _to_int_or_none(it.get(f))
                    if inc is not None:
                        setattr(p, f, (getattr(p, f) or 0) + inc)

            # ---- 2) 直接覆寫欄位（有帶才動）----
            if "delivery_qty" in it:
                v = _to_int_or_none(it.get("delivery_qty"))
                if v is not None:
                    p.delivery_qty = v

            if "assemble_qty" in it:
                v = _to_int_or_none(it.get("assemble_qty"))
                if v is not None:
                    p.assemble_qty = v

            if "reason" in it:
                # 字串允許清空；要清空就傳 ""；不帶就不動
                rv = it.get("reason")
                p.reason = ("" if rv == "" else (str(rv) if rv is not None else p.reason))

            if "confirm_comment" in it:
                cv = it.get("confirm_comment")
                p.confirm_comment = ("" if cv == "" else (str(cv) if cv is not None else p.confirm_comment))

        s.commit()

        # 組回傳
        out = []
        for mid, p in by_mid.items():
            if mid in exist_mid:  # 只回這次有動到的 mids
                out.append({
                    "id": getattr(p, "id", None),
                    "material_id": p.material_id,
                    "delivery_qty": p.delivery_qty,
                    "assemble_qty": p.assemble_qty,
                    "allOk_qty": p.allOk_qty,
                    "good_qty": p.good_qty,
                    "non_good_qty": p.non_good_qty,
                    "reason": p.reason,
                    "confirm_comment": p.confirm_comment,
                })
        return jsonify({"ok": True, "updated": len(out), "items": out}), 200

    except ValueError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 400
    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        s.close()


@updateTable.route("/updateAssembleTableData", methods=["POST"])
def update_assemble_table_data():
    print("updateAssembleTableData....")

    s = Session()
    try:
        data = request.get_json(force=True) or {}
        assemble_id = data.get("assemble_id")
        if not assemble_id:
            return jsonify({"status": False, "message": "assemble_id 為必填"}), 400

        patch = data.get("patch")
        if patch is None:
            patch = {k: v for k, v in data.items() if k != "assemble_id"}
        if not isinstance(patch, dict) or not patch:
            return jsonify({"status": False, "message": "沒有可更新欄位"}), 400

        obj = s.query(Assemble).get(int(assemble_id))
        if not obj:
            return jsonify({"status": False, "message": f"Assemble id={assemble_id} 不存在"}), 404

        before = serialize_assemble(obj)

        updated, ignored = [], []
        for k, v in patch.items():
            if k not in ALLOWED_FIELDS:
                ignored.append(k); continue
            setattr(obj, k, coerce_by_schema(k, v))
            updated.append(k)

        # 統一由後端覆寫 update_time
        obj.update_time = now_str()
        if "update_time" not in updated:
            updated.append("update_time")

        # 可選：驗證 is_copied_from_id
        if "is_copied_from_id" in updated and obj.is_copied_from_id:
            exists = s.query(Assemble.id).filter(Assemble.id == obj.is_copied_from_id).first()
            if not exists:
                obj.is_copied_from_id = None
                updated.remove("is_copied_from_id")
                ignored.append("is_copied_from_id(不存在的來源 id)")

        s.commit(); s.refresh(obj)
        after = serialize_assemble(obj)

        return jsonify({
            "status": True, "id": obj.id,
            "updated": sorted(updated), "ignored_fields": ignored,
            "before": before, "after": after
        }), 200

    except SQLAlchemyError as e:
        s.rollback()
        return jsonify({"status": False, "message": f"資料庫錯誤: {str(e)}"}), 500
    except Exception as e:
        s.rollback()
        return jsonify({"status": False, "message": f"伺服器錯誤: {str(e)}"}), 500
    finally:
        s.close()

