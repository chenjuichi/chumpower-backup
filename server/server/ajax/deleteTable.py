import os
import sys
import argparse

from pathlib import Path

from datetime import datetime, timedelta

from typing import List

from flask import Blueprint, jsonify, request, current_app

from database.tables import User, Session
from database.tables import Material, Assemble, Product, Bom, Process, association_material_abnormal
from database.p_tables import P_Material, P_Assemble, P_Product, P_Bom, P_Process, p_association_material_abnormal
from database.tables import default_process_steps

import pymysql
from sqlalchemy import select, delete, update, exc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import or_

from .helper import sync_assemble_schedule_rows

import shutil

import traceback


deleteTable = Blueprint('deleteTable', __name__)


from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def mark_material_done_after_delete(session, material_id):
    material = session.query(Material).filter(Material.id == material_id).first()
    if not material:
        return False

    # 是否還有未完成排程
    unfinished = (
        session.query(Assemble.id)
        .outerjoin(Process, Process.assemble_id == Assemble.id)
        .filter(Assemble.material_id == material_id)
        .filter(Assemble.process_step_code > 0)
        .filter(Assemble.schedule_id.isnot(None))
        .filter(
            (Process.id.is_(None)) |
            (Process.end_time.is_(None)) |
            (Process.end_time == '')
        )
        .first()
    )

    if unfinished:
        return False

    # 走到這裡代表組裝/檢驗都沒有剩餘未完成排程
    material.isAssembleStation3TakeOk = True
    material.hasStarted = False
    material.startStatus = False
    material.isOpen = False
    material.isOpenEmpId = ''

    # 關鍵：一次把所有 Begin.vue 會顯示的 row 關掉
    session.query(Assemble).filter(
        Assemble.material_id == material_id
    ).update({
        Assemble.process_step_code: 0,
        Assemble.schedule_id: None,
        Assemble.isAssembleStationShow: False,
        Assemble.isWarehouseStationShow: False,
        Assemble.input_disable: True,
        Assemble.input_end_disable: True,
        Assemble.input_allOk_disable: True,
        Assemble.input_abnormal_disable: True,
        Assemble.show1_ok: 0,
        Assemble.show2_ok: 0,
        Assemble.show3_ok: 0,
    }, synchronize_session=False)

    session.flush()

    # 找最後一筆已完成報工，作為 End.vue 待送出代表列
    final_row = (
        session.query(Assemble)
        .join(Process, Process.assemble_id == Assemble.id)
        .filter(Assemble.material_id == material_id)
        .filter(Process.has_started.is_(True))
        .filter(Process.end_time.isnot(None))
        .filter(Process.end_time != '')
        .order_by(Process.end_time.desc(), Assemble.id.desc())
        .first()
    )

    if not final_row:
        final_row = (
            session.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .order_by(Assemble.id.desc())
            .first()
        )

    if final_row:
        final_row.process_step_code = 0
        final_row.schedule_id = None

        # 讓 ~End.vue 顯示可送出
        final_row.isAssembleStationShow = True
        final_row.isWarehouseStationShow = False

        final_row.input_disable = True
        final_row.input_end_disable = True
        final_row.input_allOk_disable = False
        final_row.input_abnormal_disable = True

        final_row.show1_ok = 0
        final_row.show2_ok = 9
        final_row.show3_ok = 0

    return True

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

        if not checked_ids:
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

        base.process_step_code = process_step_code
        base.input_disable = False
        base.input_end_disable = False
        base.input_allOk_disable = False
        base.input_abnormal_disable = False
        base.isAssembleStationShow = False
        base.isWarehouseStationShow = False
        base.show1_ok = material.show1_ok
        base.show2_ok = material.show2_ok
        base.show3_ok = material.show3_ok

        base_qty = (
            qty
            or material.delivery_qty
            or material.total_delivery_qty
            or material.material_qty
            or 0
        )

        base.must_receive_qty = base_qty
        base.ask_qty = base_qty
        base.total_ask_qty = base_qty
        base.must_receive_end_qty = base_qty

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


# ------------------------------------------------------------------


@deleteTable.route("/removeUser", methods=['POST'])
def remove_user():
    print("removeUser....")

    request_data = request.get_json()
    userID = request_data['ID']
    print("userID", userID, type(userID))
    s = Session()
    s.query(User).filter(User.emp_id == userID).update({'isRemoved': False})
    #s.commit()
    try:
      s.commit()
      print("Set data committed successfully")
    except pymysql.err.IntegrityError as e:
      print(f"IntegrityError: {e}")
      s.rollback()
    except exc.IntegrityError as e:
      print(f"SQLAlchemy IntegrityError: {e}")
      s.rollback()
    except Exception as e:
      print(f"Exception: {e}")
      s.rollback()

    s.close()

    return jsonify({
      'status': True,
    })

@deleteTable.route('/removeMaterialsAndRelationTableByDeliveryDateRange', methods=['POST'])
def remove_materials_and_relation_table_by_delivery_date_range():
    print(">>> INLINE /removeMaterialsAndRelationTableByDeliveryDateRange")

    payload = request.get_json() or {}
    print(">>> payload:", payload)

    dp_range = payload.get("dpRange2") or payload.get("delivery_dates") or []
    delete_copies = bool(payload.get("delete_copies", True))
    print(">>> dp_range:", dp_range)
    print(">>> delete_copies:", delete_copies)

    def normalize_date_str(v):
        """
        將各種日期格式轉成 YYYY-MM-DD
        支援:
          - 2026-03-11
          - 2026/03/11
          - 2026-03-11 00:00:00
          - 2026/03/11 00:00:00
          - ISO 字串
        """
        if v is None:
            return None

        s = str(v).strip()
        if not s:
            return None

        s = s.replace('/', '-')
        s = s.replace('T', ' ')

        # 先取前 10 碼試試
        head10 = s[:10]
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass

        try:
            return datetime.strptime(head10, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            return None

    def expand_date_range(date_list):
        """
        若傳入 2 個日期，視為起訖區間(含頭含尾)
        若傳入多個日期，則逐一正規化後直接使用
        """
        cleaned = [normalize_date_str(x) for x in date_list if normalize_date_str(x)]
        cleaned = list(dict.fromkeys(cleaned))  # 去重但保序

        if len(cleaned) == 2:
            try:
                start_dt = datetime.strptime(cleaned[0], "%Y-%m-%d").date()
                end_dt = datetime.strptime(cleaned[1], "%Y-%m-%d").date()
                if start_dt > end_dt:
                    start_dt, end_dt = end_dt, start_dt

                result = []
                cur = start_dt
                while cur <= end_dt:
                    result.append(cur.strftime("%Y-%m-%d"))
                    cur += timedelta(days=1)
                return result
            except Exception:
                return cleaned

        return cleaned

    target_dates = expand_date_range(dp_range)
    print(">>> target_dates:", target_dates)

    if not target_dates:
        return jsonify({
            'status': False,
            'message': '沒有有效的交期日期'
        }), 400

    try:
        def find_descendant_material_ids(session, root_id: int):
            to_visit = [root_id]
            seen = {root_id}
            idx = 0
            while idx < len(to_visit):
                current = to_visit[idx]
                idx += 1
                rows = session.query(Material.id)\
                              .filter_by(is_copied_from_id=current)\
                              .all()
                for (child_id,) in rows:
                    if child_id not in seen:
                        seen.add(child_id)
                        to_visit.append(child_id)
            return to_visit

        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            # 1) 多對多表
            if association_material_abnormal is not None:
                session.execute(
                    association_material_abnormal.delete().where(
                        association_material_abnormal.c.material_id == material_id
                    )
                )

            # 2) process / product
            session.query(Process).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            if 'Product' in globals() and Product is not None:
                session.query(Product).filter_by(material_id=material_id)\
                      .delete(synchronize_session=False)

            # 3) ★ 先處理 assemble 的自我參照 FK
            assemble_ids = [
                aid for (aid,) in session.query(Assemble.id)
                                        .filter_by(material_id=material_id)
                                        .all()
            ]

            if assemble_ids:
                session.query(Assemble)\
                      .filter(Assemble.is_copied_from_id.in_(assemble_ids))\
                      .update({Assemble.is_copied_from_id: None}, synchronize_session=False)

            # 4) 再刪 assemble / bom
            session.query(Assemble).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            session.query(Bom).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            # 5) 不遞迴時，material copies 斷鏈
            if set_children_copies_null:
                session.query(Material)\
                      .filter_by(is_copied_from_id=material_id)\
                      .update({Material.is_copied_from_id: None}, synchronize_session=False)

            # 6) 刪 material
            session.query(Material).filter_by(id=material_id)\
                  .delete(synchronize_session=False)

        """
        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            if association_material_abnormal is not None:
                session.execute(
                    association_material_abnormal.delete().where(
                        association_material_abnormal.c.material_id == material_id
                    )
                )

            session.query(Process).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            if 'Product' in globals() and Product is not None:
                session.query(Product).filter_by(material_id=material_id)\
                       .delete(synchronize_session=False)

            session.query(Assemble).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            session.query(Bom).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            if set_children_copies_null:
                session.query(Material)\
                       .filter_by(is_copied_from_id=material_id)\
                       .update({Material.is_copied_from_id: None}, synchronize_session=False)

            session.query(Material).filter_by(id=material_id)\
                   .delete(synchronize_session=False)
        """

        with Session() as s:
            matched_rows = (
                s.query(Material.id, Material.material_delivery_date)
                 .filter(Material.material_delivery_date.in_(target_dates))
                 .all()
            )

        matched_ids = [row[0] for row in matched_rows]
        print(">>> matched_ids:", matched_ids)

        if not matched_ids:
            return jsonify({
                'status': True,
                'message': '查無符合交期的資料',
                'deleted_ids': [],
                'matched_dates': target_dates,
            }), 200

        deleted_roots = []
        deleted_all_ids = []

        if delete_copies:
            with Session() as s:
                with s.begin():
                    for mid in matched_ids:
                        if s.get(Material, mid) is None:
                            continue

                        ids = find_descendant_material_ids(s, mid)
                        for x in reversed(ids):
                            delete_one_material(s, x, set_children_copies_null=False)

                        deleted_roots.append(mid)
                        deleted_all_ids.extend(ids)
        else:
            with Session() as s:
                with s.begin():
                    for mid in matched_ids:
                        if s.get(Material, mid) is None:
                            continue
                        delete_one_material(s, mid, set_children_copies_null=True)
                        deleted_roots.append(mid)
                        deleted_all_ids.append(mid)

        deleted_all_ids = list(dict.fromkeys(deleted_all_ids))

        print(">>> deleted_roots:", deleted_roots)
        print(">>> deleted_all_ids:", deleted_all_ids)

        return jsonify({
            'status': True,
            'message': '依交期範圍刪除成功',
            'matched_dates': target_dates,
            'deleted_root_ids': deleted_roots,
            'deleted_ids': deleted_all_ids,
            'deleted_count': len(deleted_all_ids),
        }), 200

    except SQLAlchemyError as se:
        print(">>> SQLAlchemyError:", repr(se))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTableByDeliveryDateRange SQLA error")
        except Exception:
            pass
        return jsonify({
            'status': False,
            'message': str(se)
        }), 500

    except Exception as e:
        print(">>> ROUTE EXCEPTION:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTableByDeliveryDateRange exception")
        except Exception:
            pass
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500


@deleteTable.route('/removeMaterialsAndRelationTable', methods=['POST'])
def remove_materials_and_relation_table():
    print(">>> INLINE /removeMaterialsAndRelationTable")

    payload = request.get_json()
    print(">>> payload:", payload)

    mid = payload.get("material_id") or payload.get("id")
    mid = int(mid)
    print(">>> mid:", mid)

    # 預設 True（會連 copies 一起刪）
    delete_copies = bool(payload.get("delete_copies", True))
    print(">>> delete_copies:", delete_copies)

    try:
      # 先確認存在（用 get，避免任何 filter/filter_by 混淆）
        with Session() as s_chk:
            if s_chk.get(Material, mid) is None:
                print(">>> material not found -> False")
                return jsonify(False), 200

        # 找 copies 後代（含自身）— 僅用 filter_by(kw)
        def find_descendant_material_ids(session, root_id: int):
            to_visit = [root_id]
            seen = {root_id}
            idx = 0
            while idx < len(to_visit):
                current = to_visit[idx]
                idx += 1
                rows = session.query(Material.id)\
                              .filter_by(is_copied_from_id=current)\
                              .all()
                for (child_id,) in rows:
                    if child_id not in seen:
                        seen.add(child_id)
                        to_visit.append(child_id)
            return to_visit

        # 刪一筆（先子後母）— 全部改成 filter_by(kw) 寫法
        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            # 1) 多對多表
            if association_material_abnormal is not None:
                session.execute(
                    association_material_abnormal.delete().where(
                        association_material_abnormal.c.material_id == material_id
                    )
                )

            # 2) process / product
            session.query(Process).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            if 'Product' in globals() and Product is not None:
                session.query(Product).filter_by(material_id=material_id)\
                      .delete(synchronize_session=False)

            # 3) ★ 先處理 assemble 的自我參照 FK
            assemble_ids = [
                aid for (aid,) in session.query(Assemble.id)
                                        .filter_by(material_id=material_id)
                                        .all()
            ]

            if assemble_ids:
                session.query(Assemble)\
                      .filter(Assemble.is_copied_from_id.in_(assemble_ids))\
                      .update({Assemble.is_copied_from_id: None}, synchronize_session=False)

            # 4) 再刪 assemble / bom
            session.query(Assemble).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            session.query(Bom).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            # 5) 不遞迴時，material copies 斷鏈
            if set_children_copies_null:
                session.query(Material)\
                      .filter_by(is_copied_from_id=material_id)\
                      .update({Material.is_copied_from_id: None}, synchronize_session=False)

            # 6) 刪 material
            session.query(Material).filter_by(id=material_id)\
                  .delete(synchronize_session=False)
        """
        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            # 1) 多對多表（Table 物件）
            if association_material_abnormal is not None:
                session.execute(
                    association_material_abnormal.delete().where(
                        association_material_abnormal.c.material_id == material_id
                    )
                )

            # 2) 子表
            session.query(Process).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            if 'Product' in globals() and Product is not None:
                session.query(Product).filter_by(material_id=material_id)\
                       .delete(synchronize_session=False)

            session.query(Assemble).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            session.query(Bom).filter_by(material_id=material_id)\
                   .delete(synchronize_session=False)

            # 3) 不遞迴 → 把孩子的 is_copied_from_id 設回 NULL
            if set_children_copies_null:
                session.query(Material)\
                       .filter_by(is_copied_from_id=material_id)\
                       .update({Material.is_copied_from_id: None}, synchronize_session=False)

            # 4) 主表
            session.query(Material).filter_by(id=material_id)\
                   .delete(synchronize_session=False)
        """

        # 實際刪除（新 Session + 交易）
        if delete_copies:
            with Session() as s:
                with s.begin():
                    ids = find_descendant_material_ids(s, mid)
                    for x in reversed(ids):  # 由葉到根
                        delete_one_material(s, x, set_children_copies_null=False)
            print(">>> deleted (recursive):", list(reversed(ids)))
        else:
            with Session() as s:
                with s.begin():
                    delete_one_material(s, mid, set_children_copies_null=True)
            print(">>> deleted (single):", mid)

        return jsonify(True), 200

    except SQLAlchemyError as se:
        print(">>> SQLAlchemyError:", repr(se))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTable SQLA error")
        except Exception:
            pass
        return jsonify(False), 200
    except Exception as e:
        print(">>> ROUTE EXCEPTION:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTable exception")
        except Exception:
            pass
        return jsonify(False), 200


@deleteTable.route('/removeMaterialsAndRelationTableP', methods=['POST'])
def remove_materials_and_relation_table_p():
    print(">>> INLINE /removeMaterialsAndRelationTableP")

    payload = request.get_json()
    print(">>> payload:", payload)

    mid = payload.get("material_id") or payload.get("id")
    mid = int(mid)
    print(">>> mid:", mid)

    # 預設 True（會連 copies 一起刪）
    delete_copies = bool(payload.get("delete_copies", True))
    print(">>> delete_copies:", delete_copies)

    try:
      # 先確認存在（用 get，避免任何 filter/filter_by 混淆）
        with Session() as s_chk:
            if s_chk.get(P_Material, mid) is None:
                print(">>> p_material not found -> False")
                return jsonify(False), 200

        # 找 copies 後代（含自身）— 僅用 filter_by(kw)
        def find_descendant_material_ids(session, root_id: int):
            to_visit = [root_id]
            seen = {root_id}
            idx = 0
            while idx < len(to_visit):
                current = to_visit[idx]
                idx += 1
                rows = session.query(P_Material.id)\
                              .filter_by(is_copied_from_id=current)\
                              .all()
                for (child_id,) in rows:
                    if child_id not in seen:
                        seen.add(child_id)
                        to_visit.append(child_id)
            return to_visit

        # 刪一筆（先子後母）— 全部改成 filter_by(kw) 寫法
        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
          # 1) 多對多表
          if p_association_material_abnormal is not None:
              session.execute(
                  p_association_material_abnormal.delete().where(
                      p_association_material_abnormal.c.material_id == material_id
                  )
              )

          # 2) 子表：先刪 process / product
          session.query(P_Process).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

          session.query(P_Product).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

          # 3) ★ 先處理 P_Assemble 的 self FK
          #    找出這個 material 底下所有 assemble ids
          p_assemble_ids = [
              aid for (aid,) in session.query(P_Assemble.id)
                                      .filter_by(material_id=material_id)
                                      .all()
          ]

          #    若有其他 p_assemble 的 is_copied_from_id 指向它們，先設成 NULL
          if p_assemble_ids:
              session.query(P_Assemble)\
                    .filter(P_Assemble.is_copied_from_id.in_(p_assemble_ids))\
                    .update({P_Assemble.is_copied_from_id: None}, synchronize_session=False)

          # 4) 再刪 assemble / bom
          session.query(P_Assemble).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

          session.query(P_Bom).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

          # 5) 不遞迴刪 children 時，先把 child material 的來源斷開
          if set_children_copies_null:
              session.query(P_Material)\
                    .filter_by(is_copied_from_id=material_id)\
                    .update({P_Material.is_copied_from_id: None}, synchronize_session=False)

          # 6) 最後刪主表
          session.query(P_Material).filter_by(id=material_id)\
                .delete(synchronize_session=False)
        """
        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            # 1) 多對多表（Table 物件）
            if p_association_material_abnormal is not None:
                session.execute(
                    p_association_material_abnormal.delete().where(
                        p_association_material_abnormal.c.material_id == material_id
                    )
                )

            # 2) 子表
            session.query(P_Process).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            #if 'P_Product' in globals() and P_Product is not None:
            #    session.query(P_Product).filter_by(material_id=material_id)\
            #          .delete(synchronize_session=False)
            session.query(P_Product).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            session.query(P_Assemble).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            session.query(P_Bom).filter_by(material_id=material_id)\
                  .delete(synchronize_session=False)

            # 3) 不遞迴 → 把孩子的 is_copied_from_id 設回 NULL
            if set_children_copies_null:
                session.query(P_Material)\
                       .filter_by(is_copied_from_id=material_id)\
                       .update({P_Material.is_copied_from_id: None}, synchronize_session=False)

            # 4) 主表
            session.query(P_Material).filter_by(id=material_id)\
                   .delete(synchronize_session=False)
        """

        # 實際刪除（新 Session + 交易）
        if delete_copies:
            with Session() as s:
                with s.begin():
                    ids = find_descendant_material_ids(s, mid)
                    for x in reversed(ids):  # 由葉到根
                        delete_one_material(s, x, set_children_copies_null=False)
            print(">>> deleted (recursive):", list(reversed(ids)))
        else:
            with Session() as s:
                with s.begin():
                    delete_one_material(s, mid, set_children_copies_null=True)
            print(">>> deleted (single):", mid)

        return jsonify(True), 200

    except SQLAlchemyError as se:
        print(">>> SQLAlchemyError:", repr(se))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTableP SQLAlchemy error")
        except Exception:
            pass
        return jsonify(False), 200
    except Exception as e:
        print(">>> ROUTE EXCEPTION:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("removeMaterialsAndRelationTableP exception")
        except Exception:
            pass
        return jsonify(False), 200


@deleteTable.route("/moveServerFile", methods=["POST"])
def move_server_file():
    data = request.get_json(silent=True) or {}
    print("moveServerFile data:", data)
    filename = (data.get("filename") or "").strip()
    print("filename:", filename)

    # line 參數（預設 true）
    line = data.get("line", True)
    print("line:", line)

    # 轉成 bool（避免前端傳 "false" 變成 True）
    if isinstance(line, str):
        line = line.lower() == "true"

    if not filename:
        return jsonify({"ok": False, "msg": "filename 不可為空"}), 200  # 400

    # 禁止路徑攻擊
    if "/" in filename or "\\" in filename:
        return jsonify({"ok": False, "msg": "禁止傳入路徑"}), 200       # 400

    # -------- 取得目標資料夾 --------
    def get_out_dir(base_dir: str) -> str:
        p = Path(base_dir)
        name = p.name

        idx = name.find("_in")
        if idx == -1:
            raise ValueError(f"invalid folder name: {name}")

        prefix = name[:idx]
        return str(p.parent / f"{prefix}_out")

    _base_dir = current_app.config['baseDir']
    base_path = Path(_base_dir).resolve()

    # line = false → 改成 _in_p
    if not line:
        name = base_path.name
        if "_in" not in name:
            return jsonify({"ok": False, "msg": "資料夾名稱不包含 _in"}), 200     # 400

        new_name = name.replace("_in", "_in_p", 1)
        base_path = base_path.parent / new_name

    try:
        _target_dir = get_out_dir(_base_dir)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"取得目標目錄失敗: {str(e)}"}), 200  # 500

    print("來源:", _base_dir)
    print("目標:", _target_dir)

    # -------- 轉成 Path --------
    #base_path = Path(_base_dir).resolve()
    target_path = Path(_target_dir).resolve()

    # -------- 組來源檔案 --------
    src = (base_path / filename).resolve()

    # 安全檢查（防跳目錄）
    try:
        src.relative_to(base_path)
    except ValueError:
        return jsonify({"ok": False, "msg": "非法路徑"}), 200

    if not src.exists():
        return jsonify({"ok": False, "msg": "檔案不存在"}), 200 # 404

    if not src.is_file():
        return jsonify({"ok": False, "msg": "只允許檔案"}), 200 # 400

    # 副檔名限制
    allowed_ext = {".pdf", ".xlsx", ".xls", ".txt"}
    if src.suffix.lower() not in allowed_ext:
        return jsonify({"ok": False, "msg": "副檔名不允許"}), 400

    # -------- 建立目標路徑 --------
    dst = (target_path / filename).resolve()

    try:
        dst.relative_to(target_path)
    except ValueError:
        return jsonify({"ok": False, "msg": "目標路徑非法"}), 200 # 400

    # 建立目標資料夾
    target_path.mkdir(parents=True, exist_ok=True)

    # 防止覆蓋
    #if dst.exists():
    #    return jsonify({"ok": False, "msg": f"目標已存在同名檔案: {filename}"}), 400
    #
    # -------- 自動避免重複檔名 --------
    stem = src.stem
    suffix = src.suffix

    #dst = target_path / filename
    dst = (target_path / filename).resolve()

    counter = 1
    max_try = 1000
    while dst.exists() and counter < max_try:
        new_name = f"{stem}_{counter}{suffix}"
        #dst = target_path / new_name
        dst = (target_path / new_name).resolve()
        counter += 1

    if dst.exists():
      return jsonify({
          "ok": False,
          "msg": f"目標檔名重複太多，已嘗試到 _{max_try}: {filename}"
      }), 200   # 400

    try:
        dst.relative_to(target_path)
    except ValueError:
        return jsonify({"ok": False, "msg": "目標路徑非法"}), 200   # 400

    # -------- 執行移動 --------
    try:
        shutil.move(str(src), str(dst))
        return jsonify({
            "ok": True,
            "msg": f"已移動: {filename}",
            "from": str(src),
            "to": str(dst)
        })
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@deleteTable.route("/listServerFiles", methods=["POST"])
def list_server_files():
    data = request.get_json(silent=True) or {}

    # line 參數（預設 true）
    line = data.get("line", True)

    # 轉成 bool
    if isinstance(line, str):
        line = line.lower() == "true"

    _base_dir = current_app.config['baseDir']
    folder = Path(_base_dir).resolve()

    # line = false → 讀取 excel_in_p
    if not line:
        name = folder.name

        if "_in" not in name:
            return jsonify({"ok": False, "msg": "資料夾名稱不包含 _in"}), 400

        new_name = name.replace("_in", "_in_p", 1)
        folder = folder.parent / new_name

    print("listServerFiles 讀取目錄:", folder)

    if not folder.exists() or not folder.is_dir():
        return jsonify({
            "ok": False,
            "msg": f"資料夾不存在: {str(folder)}"
        }), 404

    try:
        files = []

        for p in folder.iterdir():
            if p.is_file():
                files.append({
                    "name": p.name,
                    "size": p.stat().st_size,
                    "suffix": p.suffix.lower(),
                })

        files.sort(key=lambda x: x["name"].lower())

        return jsonify({
            "ok": True,
            "files": files,
            "line": line,
            "folder": str(folder),
        })

    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


"""
@deleteTable.route("/deleteAssembleScheduleRow", methods=["POST"])
def delete_assemble_schedule_row():
    print("deleteAssembleScheduleRow.")

    data = request.get_json(silent=True) or {}

    material_id = data.get("id")
    assemble_id = data.get("assemble_id")
    schedule_id = data.get("schedule_id")
    work_num = (data.get("work_num") or "").strip()

    s = Session()

    try:
        material = s.query(Material).filter(Material.id == material_id).first()
        if not material:
            return jsonify({"status": False, "msg": "material not found"})

        target = (
            s.query(Assemble)
             .filter(
                 Assemble.id == assemble_id,
                 Assemble.material_id == material_id
             )
             .first()
        )

        if not target:
            return jsonify({"status": False, "msg": "assemble row not found"})

        # 已開始/已完成的 row 不允許刪除
        used_process = (
            s.query(Process.id)
             .filter(
                 Process.material_id == material_id,
                 Process.assemble_id == assemble_id
             )
             .first()
        )

        if used_process:
            return jsonify({
                "status": False,
                "msg": "此工序已有報工紀錄，不可刪除"
            })

        try:
            schedule_id = int(schedule_id or target.schedule_id or 0)
        except Exception:
            schedule_id = 0

        if not schedule_id:
            return jsonify({"status": False, "msg": "missing schedule_id"})

        process_steps = material.process_steps or default_process_steps()

        if "B109" in work_num:
            mode = "assemble"
        elif "B110" in work_num:
            mode = "check"
        else:
            mode = None

        if not mode:
            return jsonify({"status": False, "msg": "unknown work_num"})

        #
        # ------------------------------------------------------------
        # 如果整張訂單目前只剩最後一個「未完成排程」，
        # 不允許刪除，避免 Begin.vue 無工序可顯示
        # ------------------------------------------------------------
        def get_process_type_by_work_num(work_num):
            if work_num == "B109":
                return 21   # 組裝
            if work_num == "B110":
                return 22   # 檢驗
            return None

        def is_step_completed(schedule_id, work_num):
            process_type = get_process_type_by_work_num(work_num)
            if not process_type:
                return False

            done = (
                s.query(Process.id)
                .join(Assemble, Process.assemble_id == Assemble.id)
                .filter(Assemble.material_id == material_id)
                .filter(Assemble.work_num == work_num)
                .filter(Assemble.schedule_id == schedule_id)
                .filter(Process.process_type == process_type)
                .filter(Process.has_started.is_(True))
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .first()
            )

            return done is not None

        remain_unfinished_steps = []

        for step in (process_steps.get("assemble") or []):
            if not step.get("checked"):
                continue

            sid = int(step.get("id") or 0)
            if sid and not is_step_completed(sid, "B109"):
                remain_unfinished_steps.append(("assemble", sid))

        for step in (process_steps.get("check") or []):
            if not step.get("checked"):
                continue

            sid = int(step.get("id") or 0)
            if sid and not is_step_completed(sid, "B110"):
                remain_unfinished_steps.append(("check", sid))

        '''
        # 如果目前只剩一個未完成製程，而且就是現在要刪的這個，禁止刪除
        if (
            len(remain_unfinished_steps) == 1
            and remain_unfinished_steps[0][1] == int(schedule_id or 0)
        ):
            return jsonify({
                "status": False,
                "code": "ONLY_ONE_PROCESS_LEFT",
                "msg": f"{material.order_num}訂單目前唯一製程不能刪除"
            })
        '''
        #
        # ------------------------------------------------------------
        # 只有「整張訂單原本就只有 1 個製程」時，才禁止刪除
        # 若前面已有完成製程，例如 a1/a2/a3/c1 已完成，只剩 c2，
        # 刪除 c2 應視為全部完成，允許刪除
        # ------------------------------------------------------------

        checked_total_steps = 0

        for step in (process_steps.get("assemble") or []):
            if step.get("checked") and not step.get("deleted", False):
                checked_total_steps += 1

        for step in (process_steps.get("check") or []):
            if step.get("checked") and not step.get("deleted", False):
                checked_total_steps += 1

        completed_total_steps = 0

        for step in (process_steps.get("assemble") or []):
            sid = int(step.get("id") or 0)
            if sid and is_step_completed(sid, "B109"):
                completed_total_steps += 1

        for step in (process_steps.get("check") or []):
            sid = int(step.get("id") or 0)
            if sid and is_step_completed(sid, "B110"):
                completed_total_steps += 1

        # 只剩最後一個未完成製程
        is_deleting_last_unfinished = (
            len(remain_unfinished_steps) == 1
            and remain_unfinished_steps[0][1] == int(schedule_id or 0)
        )

        # 真正不可刪除的情況：
        # 整張訂單目前沒有任何已完成製程，而且總製程數只有 1
        if (
            is_deleting_last_unfinished
            and completed_total_steps == 0
            and checked_total_steps <= 1
        ):
            return jsonify({
                "status": False,
                "code": "ONLY_ONE_PROCESS_LEFT",
                "msg": f"{material.order_num}訂單目前唯一製程不能刪除"
            })
        #

        # checkbox 改為不勾選
        found = False
        for step in process_steps.get(mode, []):
            try:
                sid = int(step.get("id") or 0)
            except Exception:
                sid = 0

            if sid == schedule_id:
                step["checked"] = False
                step["deleted"] = True
                found = True
                break

        if not found:
            return jsonify({
                "status": False,
                "msg": f"process_steps 找不到 schedule_id={schedule_id}"
            })
        #

        material.process_steps = process_steps

        # 這個 JSON 欄位雖然是同一個 Python object，
        # 但裡面的內容已經被修改了，
        # commit 時一定要 UPDATE DB。
        flag_modified(material, "process_steps")
        #
        #has_any_checked = any(
        #    bool(x.get("checked"))
        #    for x in (process_steps.get("assemble") or [])
        #) or any(
        #    bool(x.get("checked"))
        #    for x in (process_steps.get("check") or [])
        #)
        #
        #material.process_step_enable = bool(has_any_checked)
        #
        # ------------------------------------------------------------
        # 刪除排程前，先清掉同 mode 的未完成 assemble row
        # 避免 a1/a2/a3 重建後殘留或回跳
        # ------------------------------------------------------------
        target_work_num = "B109" if mode == "assemble" else "B110"

        rows_to_clear = (
            s.query(Assemble)
            .filter(Assemble.material_id == material_id)
            .filter(Assemble.work_num == target_work_num)
            .all()
        )

        for r in rows_to_clear:
            done_process = (
                s.query(Process.id)
                .filter(Process.material_id == material_id)
                .filter(Process.assemble_id == r.id)
                .filter(Process.has_started.is_(True))
                .filter(Process.end_time.isnot(None))
                .filter(Process.end_time != '')
                .first()
            )

            # 已完成的歷史 row 不動
            if done_process:
                continue

            # 未完成 row 全部清成不顯示
            r.schedule_id = None
            r.process_step_code = 0
            r.isAssembleStationShow = False
            r.isWarehouseStationShow = False
            r.input_disable = True
            r.input_end_disable = True
            r.input_allOk_disable = True
            r.input_abnormal_disable = True
            r.show1_ok = 0
            r.show2_ok = 0
            r.show3_ok = 0
        #

        # 重新同步 assemble rows
        sync_assemble_schedule_rows(
            session=s,
            material_id=material_id,
            process_steps=process_steps
        )

        # 關鍵：sync 內有 delete copied rows，所以先 flush
        s.flush()

        # 關鍵：清掉 session 內舊的 Assemble ORM 狀態，避免 StaleDataError
        s.expire_all()

        done_after_delete = mark_material_done_after_delete(s, material_id)

        # 如果刪除後已經進入完成待送出，代表不該再能新增/編輯工序
        #if done_after_delete:
        #    material.process_step_enable = False
        #
        if done_after_delete:
          # material 重新 query 一次，因為 expire_all() 後原物件可能已過期。
          material = s.query(Material).filter(Material.id == material_id).first()
          material.process_step_enable = False
        #

        s.commit()
        #

        return jsonify({
            "status": True,
            "process_steps": material.process_steps,
            "process_step_enable": material.process_step_enable,
            "msg": "deleted"
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            "status": False,
            "msg": str(e)
        })

    finally:
        s.close()
"""


"""
@deleteTable.route("/deleteAssembleScheduleRow", methods=["POST"])
def delete_assemble_schedule_row():
    print("deleteAssembleScheduleRow.")

    data = request.get_json() or {}
    material_id = data.get("id")
    assemble_id = data.get("assemble_id")
    schedule_id = int(data.get("schedule_id") or 0)
    work_num = (data.get("work_num") or "").strip()

    if not material_id or not schedule_id or not work_num:
        return jsonify({
            "status": False,
            "msg": "missing id / schedule_id / work_num"
        })

    s = Session()

    try:
        material = (
            s.query(Material)
             .filter(Material.id == material_id)
             .with_for_update()
             .first()
        )

        if not material:
            return jsonify({"status": False, "msg": "material not found"})

        process_steps = material.process_steps or default_process_steps()

        if work_num == "B109":
            group_key = "assemble"
        elif work_num == "B110":
            group_key = "check"
        else:
            return jsonify({"status": False, "msg": f"unsupported work_num={work_num}"})
        '''
        #group_key = "assemble" if work_num == "B109" else "check"

        # ✅ 重點：不是刪掉選項，只把 checked 改 false
        for step in process_steps.get(group_key, []):
            if int(step.get("id") or 0) == schedule_id:
                step["checked"] = False
                step.pop("deleted", None)

        # 另一組也清掉 deleted，避免舊資料污染 dialog
        for key in ("assemble", "check"):
            for step in process_steps.get(key, []):
                step.pop("deleted", None)

        material.process_steps = process_steps
        material.process_step_enable = True
        '''
        #
        # ✅ 重點：不是刪掉選項，只把 checked 改 false
        for step in process_steps.get(group_key, []):
            if int(step.get("id") or 0) == schedule_id:
                step["checked"] = False
                step.pop("deleted", None)

        # 另一組也清掉 deleted，避免舊資料污染 dialog
        for key in ("assemble", "check"):
            for step in process_steps.get(key, []):
                step.pop("deleted", None)

        material.process_steps = process_steps
        flag_modified(material, "process_steps")
        material.process_step_enable = True
        #

        # ✅ 重新依 checked 狀態同步 assemble rows
        sync_assemble_schedule_rows(
            session=s,
            material_id=material_id,
            process_steps=process_steps
        )

        s.commit()

        return jsonify({
            "status": True,
            "msg": "delete schedule ok",
            "process_steps": process_steps
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            "status": False,
            "msg": str(e)
        })

    finally:
        s.close()
"""


@deleteTable.route("/deleteAssembleScheduleRow", methods=["POST"])
def delete_assemble_schedule_row():
    print("deleteAssembleScheduleRow.")

    data = request.get_json() or {}
    material_id = data.get("id")
    schedule_id = int(data.get("schedule_id") or 0)
    work_num = (data.get("work_num") or "").strip()

    if not material_id or not schedule_id or not work_num:
        return jsonify({
            "status": False,
            "msg": "missing id / schedule_id / work_num"
        })

    s = Session()

    try:
        material = (
            s.query(Material)
             .filter(Material.id == material_id)
             .with_for_update()
             .first()
        )

        if not material:
            return jsonify({"status": False, "msg": "material not found"})

        process_steps = material.process_steps or default_process_steps()

        if work_num == "B109":
            group_key = "assemble"
        elif work_num == "B110":
            group_key = "check"
        else:
            return jsonify({"status": False, "msg": f"unsupported work_num={work_num}"})

        # ✅ dialog 選項保留，只取消勾選
        for step in process_steps.get(group_key, []):
            if int(step.get("id") or 0) == schedule_id:
                step["checked"] = False
                step.pop("deleted", None)

        for key in ("assemble", "check"):
            for step in process_steps.get(key, []):
                step.pop("deleted", None)

        material.process_steps = process_steps
        material.process_step_enable = True
        flag_modified(material, "process_steps")

        # ✅ 只關閉被刪除的那個工序 row，不重新 sync 全部
        rows = (
            s.query(Assemble)
             .filter(Assemble.material_id == material_id)
             .filter(Assemble.work_num == work_num)
             .filter(Assemble.schedule_id == schedule_id)
             .filter(or_(Assemble.reason.is_(None), Assemble.reason != "異常返工"))
             .all()
        )

        for row in rows:
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

        s.commit()

        return jsonify({
            "status": True,
            "msg": "delete schedule ok",
            "process_steps": process_steps,
            "closed_rows": len(rows)
        })

    except Exception as e:
        s.rollback()
        traceback.print_exc()
        return jsonify({
            "status": False,
            "msg": str(e)
        })

    finally:
        s.close()


@deleteTable.route('/removeMaterialsAndRelationTablePByDeliveryDateRange', methods=['POST'])
def remove_materials_and_relation_table_p_by_delivery_date_range():
    print(">>> INLINE /removeMaterialsAndRelationTablePByDeliveryDateRange")

    payload = request.get_json() or {}
    print(">>> payload:", payload)

    dp_range = payload.get("dpRange2") or payload.get("delivery_dates") or []
    delete_copies = bool(payload.get("delete_copies", True))

    def normalize_date_str(v):
        if v is None:
            return None

        s = str(v).strip()
        if not s:
            return None

        s = s.replace('/', '-').replace('T', ' ')
        head10 = s[:10]

        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            except Exception:
                pass

        try:
            return datetime.strptime(head10, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            return None

    def expand_date_range(date_list):
        cleaned = [normalize_date_str(x) for x in date_list if normalize_date_str(x)]
        cleaned = list(dict.fromkeys(cleaned))

        if len(cleaned) == 2:
            start_dt = datetime.strptime(cleaned[0], "%Y-%m-%d").date()
            end_dt = datetime.strptime(cleaned[1], "%Y-%m-%d").date()

            if start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            result = []
            cur = start_dt
            while cur <= end_dt:
                result.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)

            return result

        return cleaned

    target_dates = expand_date_range(dp_range)
    print(">>> target_dates:", target_dates)

    if not target_dates:
        return jsonify({
            'status': False,
            'message': '沒有有效的交期日期'
        }), 400

    try:
        def find_descendant_material_ids(session, root_id: int):
            to_visit = [root_id]
            seen = {root_id}
            idx = 0

            while idx < len(to_visit):
                current = to_visit[idx]
                idx += 1

                rows = (
                    session.query(P_Material.id)
                    .filter_by(is_copied_from_id=current)
                    .all()
                )

                for (child_id,) in rows:
                    if child_id not in seen:
                        seen.add(child_id)
                        to_visit.append(child_id)

            return to_visit

        def delete_one_material(session, material_id: int, *, set_children_copies_null: bool):
            # 1. 多對多異常關聯表
            if p_association_material_abnormal is not None:
                session.execute(
                    p_association_material_abnormal.delete().where(
                        p_association_material_abnormal.c.material_id == material_id
                    )
                )

            # 2. 先刪子表
            session.query(P_Process).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

            session.query(P_Product).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

            # 3. 先斷開 p_assemble 自我 FK
            p_assemble_ids = [
                aid for (aid,) in
                session.query(P_Assemble.id)
                .filter_by(material_id=material_id)
                .all()
            ]

            if p_assemble_ids:
                session.query(P_Assemble)\
                    .filter(P_Assemble.is_copied_from_id.in_(p_assemble_ids))\
                    .update(
                        {P_Assemble.is_copied_from_id: None},
                        synchronize_session=False
                    )

            # 4. 再刪 assemble / bom
            session.query(P_Assemble).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

            session.query(P_Bom).filter_by(material_id=material_id)\
                .delete(synchronize_session=False)

            # 5. 若不遞迴刪 copy，則把子 material 來源斷開
            if set_children_copies_null:
                session.query(P_Material)\
                    .filter_by(is_copied_from_id=material_id)\
                    .update(
                        {P_Material.is_copied_from_id: None},
                        synchronize_session=False
                    )

            # 6. 最後刪主表
            session.query(P_Material).filter_by(id=material_id)\
                .delete(synchronize_session=False)

        with Session() as s:
            matched_rows = (
                s.query(P_Material.id, P_Material.material_delivery_date)
                .filter(P_Material.move_by_process_type == 4)             #針對加工線的工單
                .filter(P_Material.material_delivery_date.in_(target_dates))
                .all()
            )

        matched_ids = [row[0] for row in matched_rows]
        print(">>> matched_ids:", matched_ids)

        if not matched_ids:
            return jsonify({
                'status': True,
                'message': '沒有查到符合交期的加工線資料',
                'matched_dates': target_dates,
                'deleted_ids': [],
                'deleted_count': 0,
            }), 200

        deleted_roots = []
        deleted_all_ids = []

        if delete_copies:
            with Session() as s:
                with s.begin():
                    for mid in matched_ids:
                        if s.get(P_Material, mid) is None:
                            continue

                        ids = find_descendant_material_ids(s, mid)

                        for x in reversed(ids):
                            delete_one_material(
                                s,
                                x,
                                set_children_copies_null=False
                            )

                        deleted_roots.append(mid)
                        deleted_all_ids.extend(ids)
        else:
            with Session() as s:
                with s.begin():
                    for mid in matched_ids:
                        if s.get(P_Material, mid) is None:
                            continue

                        delete_one_material(
                            s,
                            mid,
                            set_children_copies_null=True
                        )

                        deleted_roots.append(mid)
                        deleted_all_ids.append(mid)

        deleted_all_ids = list(dict.fromkeys(deleted_all_ids))

        return jsonify({
            'status': True,
            'message': '加工線依交期範圍刪除成功',
            'matched_dates': target_dates,
            'deleted_root_ids': deleted_roots,
            'deleted_ids': deleted_all_ids,
            'deleted_count': len(deleted_all_ids),
        }), 200

    except SQLAlchemyError as se:
        traceback.print_exc()
        current_app.logger.exception(
            "removeMaterialsAndRelationTablePByDeliveryDateRange SQLAlchemy error"
        )
        return jsonify({
            'status': False,
            'message': str(se)
        }), 500

    except Exception as e:
        traceback.print_exc()
        current_app.logger.exception(
            "removeMaterialsAndRelationTablePByDeliveryDateRange exception"
        )
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

