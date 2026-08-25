#import math
#import random
import re
from datetime import datetime, date, timedelta

import traceback

from datetime import datetime as dt
import time

from flask import Blueprint, jsonify, request, current_app

from database.tables import User, Session
from database.p_tables import P_Material, P_Assemble,  P_Process, P_Product, P_Part

#from dotenv import dotenv_values
#from collections import defaultdict

from sqlalchemy import func, or_, and_, cast, Integer
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy import distinct, case, select

import logging
logger = logging.getLogger(__name__)

listTableP = Blueprint('listTableP', __name__)


# ------------------------------------------------------------------


"""
# 20260805版
@listTableP.route("/listMaterialsAndAssemblesP", methods=['GET'])
def list_materials_and_assembles_p():
    print("listMaterialsAndAssemblesP....")

    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def norm_code(v):
        return (v or '').strip()

    s = Session()

    try:
        _objects = (
            s.query(P_Material)
            .filter(P_Material.move_by_process_type == 4)
            .filter(P_Material.isShow.is_(True))
            .filter(P_Material.isTakeOk.is_(True))
            .filter(P_Material.show1_ok == 2)
            # 3 = 已送到加工等待開始
            # 4 = 加工中 / 暫停中
            .filter(P_Material.show2_ok.in_(['3', '4']))
            .options(
                selectinload(P_Material._assemble).load_only(
                    P_Assemble.id,
                    P_Assemble.material_id,
                    P_Assemble.must_receive_qty,
                    P_Assemble.must_receive_end_qty,
                    P_Assemble.total_ask_qty,
                    P_Assemble.work_num,
                    P_Assemble.process_step_code,
                    P_Assemble.isSimultaneously,
                    P_Assemble.seq_num,
                    P_Assemble.currentStartTime,

                    #
                    P_Assemble.input_end_disable,
                    P_Assemble.input_abnormal_disable,
                    P_Assemble.isAssembleStationShow,
                    #

                    P_Assemble.input_disable,
                    P_Assemble.Incoming1_Abnormal,
                    P_Assemble.is_copied_from_id,
                    P_Assemble.create_at,
                    P_Assemble.isShowBomGif,
                    P_Assemble.isStockIn,
                    P_Assemble.isWarehouseStationShow,
                    P_Assemble.show2_ok,
                ),
                # 20260730版
                selectinload(P_Material._process).load_only(
                    P_Process.id,
                    P_Process.material_id,
                    P_Process.assemble_id,
                    P_Process.process_type,

                    # 必須載入，後面會用來判斷是否真正開始
                    P_Process.has_started,

                    P_Process.begin_time,
                    P_Process.end_time,
                    P_Process.process_work_time_qty,
                    P_Process.user_id,
                    P_Process.is_pause,
                    P_Process.elapsedActive_time,
                    P_Process.str_elapsedActive_time,
                ),
                #
            )
            .all()
        )

        if not _objects:
            return jsonify({
                'status': False,
                'materials_and_assembles': [],
                'assemble_active_users': [],
            })

        part_info_map = {}
        part_rows = (s.query(
                P_Part.part_code,
                P_Part.part_comment,
                P_Part.process_step_code
            ).all()
        )

        for part_code, part_comment, process_step_code in part_rows:
            code = norm_code(part_code)
            if not code:
                continue

            part_info_map[code] = {
                'comment': (part_comment or '').strip(),
                'process_step_code': int(process_step_code or 0),
            }

        index = 0

        for material_record in _objects:
            assemble_records = list(material_record._assemble or [])
            process_records = list(material_record._process or [])

            #total_records = sum(
            #    1 for p in process_records
            #    if p.material_id == material_record.id and int(p.assemble_id or 0) != 0
            #)

            keep_assemble_id = None
            keep_seq = None

            for a in assemble_records:
                step = int(a.process_step_code or 0)
                if step == 0:
                    continue

                if bool(a.isWarehouseStationShow):
                    continue

                seq = int(a.seq_num or 0)
                if keep_assemble_id is None or seq < keep_seq:
                    keep_assemble_id = int(a.id)
                    keep_seq = seq
            # end for loop

            proc_stat_map = {}

            # 20260730版
            for p in process_records:
                material_id = int(p.material_id or 0)
                assemble_id = int(p.assemble_id or 0)
                process_type = int(p.process_type or 0)

                if (
                    material_id <= 0
                    or assemble_id <= 0
                    or process_type <= 0
                ):
                    continue

                # 必須真正開始過
                if not bool(p.has_started):
                    continue

                # begin_time 必須有值
                if (
                    p.begin_time is None
                    or not str(
                        p.begin_time
                    ).strip()
                ):
                    continue

                # end_time 有內容表示已結束
                if (
                    p.end_time is not None
                    and str(
                        p.end_time
                    ).strip() != ''
                ):
                    continue

                key = (
                    material_id,
                    assemble_id,
                    process_type,
                )

                if key not in proc_stat_map:
                    proc_stat_map[key] = {
                        'count': 0,
                        'active_user_ids': set(),
                        'last_proc_id': 0,
                        'last_user_id': '',
                        'is_pause': True,
                        'elapsedActive_time': 0,
                        'str_elapsedActive_time':
                            '00:00:00',
                    }

                stat = proc_stat_map[key]

                stat['count'] += 1

                if p.user_id:
                    stat[
                        'active_user_ids'
                    ].add(
                        str(p.user_id).strip()
                    )

                process_id = int(
                    p.id or 0
                )

                if (
                    process_id >=
                    stat['last_proc_id']
                ):
                    stat['last_proc_id'] = process_id

                    stat['last_user_id'] = (
                        p.user_id or ''
                    )

                    stat['is_pause'] = bool(
                        p.is_pause
                    )

                    stat[
                        'elapsedActive_time'
                    ] = int(
                        p.elapsedActive_time or 0
                    )

                    stat[
                        'str_elapsedActive_time'
                    ] = (
                        p.str_elapsedActive_time
                        or '00:00:00'
                    )
            # end for loop

            cleaned_comment = safe_str(material_record.material_comment).strip()

            for assemble_record in assemble_records:
                # 已送倉庫的不顯示
                if bool(assemble_record.isWarehouseStationShow):
                    continue

                must_receive_qty = int(getattr(assemble_record, 'must_receive_qty', 0) or 0)
                if must_receive_qty <= 0:
                    continue

                step = int(assemble_record.process_step_code or 0)
                if step == 0:
                    continue

                is_simul = bool(assemble_record.isSimultaneously)
                if not is_simul and keep_assemble_id is not None:
                    if int(assemble_record.id) != int(keep_assemble_id):
                        continue

                work_num_clean = norm_code(assemble_record.work_num)
                part_info = part_info_map.get(work_num_clean, {
                    'comment': '',
                    'process_step_code': 0,
                })

                show_comment = part_info.get('comment', '')
                show_code = int(part_info.get('process_step_code', 0) or 0)

                # 20260730版
                # ============================================================
                # 加工計時狀態唯一 Key：
                #
                # material_id
                # assemble_id
                # process_type
                # ============================================================
                process_type = int(assemble_record.process_step_code or 0)

                stat_key = (
                    int(material_record.id or 0),
                    int(assemble_record.id or 0),
                    process_type,
                )

                process_stat = proc_stat_map.get(stat_key, {
                    'count': 0,
                    'active_user_ids': set(),
                    'last_proc_id': 0,
                    'last_user_id': '',
                    'is_pause': True,
                    'elapsedActive_time': 0,
                    'str_elapsedActive_time': '00:00:00',
                })

                # 所有正在這筆工序執行的人員
                active_user_ids = sorted(
                    str(user_id).strip()
                    for user_id in process_stat.get('active_user_ids', set())
                    if str(user_id or '').strip()
                )

                active_user_count = len(active_user_ids)

                # 只要有真正開始且尚未結束的 P_Process，
                # 就代表這列有人執行
                show_timer = (active_user_count > 0)

                show_name = (
                    str(process_stat.get('last_user_id', '') or '').strip()
                    if show_timer else ''
                )

                index += 1
                #

                _object = {
                    'index': index,
                    'row_key': f"{material_record.id}_{assemble_record.id}_{step}",
                    'is_running_row': bool(show_timer),

                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'assemble_work': show_comment,
                    'material_num': material_record.material_num,
                    'assemble_id': assemble_record.id,
                    'req_qty': material_record.material_qty,

                    'delivery_qty': material_record.delivery_qty,
                    'total_receive_qty': f"({getattr(assemble_record, 'total_ask_qty', 0)})",
                    'total_receive_qty_num': getattr(assemble_record, 'total_ask_qty', 0),

                    'must_receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'receive_qty': getattr(assemble_record, 'must_receive_qty', 0),
                    'must_receive_end_qty': assemble_record.must_receive_end_qty,

                    'delivery_date': material_record.material_delivery_date,
                    'comment': cleaned_comment,
                    'isTakeOk': material_record.isTakeOk,

                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,

                    'currentStartTime': getattr(assemble_record, 'currentStartTime', None),
                    'tooltipVisible': False,
                    'input_disable': getattr(assemble_record, 'input_disable', False),
                    'Incoming1_Abnormal': getattr(assemble_record, 'Incoming1_Abnormal', '') == '',
                    'is_copied_from_id': getattr(assemble_record, 'is_copied_from_id', None),
                    'create_at': assemble_record.create_at,

                    'isShowBomGif': assemble_record.isShowBomGif,
                    'process_step_code': assemble_record.process_step_code,

                    # 這裡只是顯示文字，不拿來判斷是否已入庫
                    'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    'isWarehouseStationShow': bool(assemble_record.isWarehouseStationShow),

                    'assemble_process_num': int(assemble_record.show2_ok or 0),

                    # 20260730 add
                    'row_key': (
                        f"{material_record.id}_"
                        f"{assemble_record.id}_"
                        f"{process_type}"
                    ),

                    'id': int(material_record.id),

                    'assemble_id': int(assemble_record.id),

                    'process_step_code': process_type,

                    'is_running_row': bool(show_timer),

                    #
                    'show_timer': bool(show_timer),

                    'show_name': show_name,

                    'is_pause': bool(process_stat.get('is_pause', True)),

                    'elapsedActive_time':
                        int(
                            process_stat.get(
                                'elapsedActive_time',
                                0
                            ) or 0
                        ),

                    'str_elapsedActive_time':
                        (
                            process_stat.get(
                                'str_elapsedActive_time'
                            )
                            or '00:00:00'
                        ),

                    'active_user_count': active_user_count,

                    'active_user_ids': active_user_ids,

                    'started_user_id': show_name,

                    'active_process_id':
                        int(
                            process_stat.get(
                                'last_proc_id',
                                0
                            ) or 0
                        ),

                    'active_is_pause':
                        bool(process_stat.get('is_pause', True)),
                    #
                }

                _results.append(_object)
            # en for loop
        _results.sort(
            key=lambda x: (
                0 if x.get('is_running_row') else 1,
                -(x.get('create_at').timestamp()) if x.get('create_at') else 0,
                x.get('id') or 0,
                x.get('assemble_id') or 0,
            )
        )

        print("listMaterialsAndAssemblesP, 總數:", len(_results))

        return jsonify({
            'status': bool(_results),
            'materials_and_assembles': _results or [],
            'assemble_active_users': _assemble_active_users or [],
        })

    except Exception as e:
        print("listMaterialsAndAssemblesP ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsAndAssemblesP failed")
        except Exception:
            pass

        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200

    finally:
        s.close()
"""


# 20260822版
def previous_process_handoff_done(
    session,
    material
):

    current_assembles = (
        session.query(P_Assemble)
        .filter(
            P_Assemble.material_id ==
            material.id
        )
        .all()
    )

    if not current_assembles:
        return True

    valid_current_seqs = [
        int(a.seq_num or 0)
        for a
        in current_assembles
        if int(a.seq_num or 0) > 0
    ]

    if not valid_current_seqs:
        return True

    current_seq = min(
        valid_current_seqs
    )

    # --------------------------------------------------------
    # 找同 order_num 的前一道加工
    # --------------------------------------------------------
    previous_rows = (
        session.query(
            P_Assemble,
            P_Material
        )
        .join(
            P_Material,
            P_Material.id ==
            P_Assemble.material_id
        )
        .filter(
            P_Material.order_num ==
            material.order_num
        )
        .filter(
            P_Material.id !=
            material.id
        )
        .all()
    )

    previous_rows = [
        (a, m)
        for a, m
        in previous_rows
        if int(a.seq_num or 0)
        <
        current_seq
    ]

    # 沒有前一道
    # → 正常第一階段，直接允許
    if not previous_rows:
        return True

    # --------------------------------------------------------
    # 取最接近目前工序的前一道
    # 50 → 60
    # --------------------------------------------------------
    previous_row, _ = max(
        previous_rows,
        key=lambda pair:
            int(pair[0].seq_num or 0)
    )

    # --------------------------------------------------------
    # 前一道必須：
    #
    # 已完成
    # 已從 PEnd 消失
    # 沒進 Warehouse
    # 且本來就是不入庫中間工序
    # --------------------------------------------------------
    return (
        int(
            previous_row.process_step_code
            or 0
        ) == 0

        and

        max(
            int(
                previous_row.completed_qty
                or 0
            ),
            int(
                previous_row.total_completed_qty
                or 0
            )
        ) > 0

        and

        not bool(
            previous_row
            .isAssembleStationShow
        )

        and

        not bool(
            previous_row
            .isWarehouseStationShow
        )

        and

        not bool(
            previous_row.isStockIn
        )
    )


# 20260815版
@listTableP.route(
    "/listMaterialsAndAssemblesP",
    methods=['GET']
)
def list_materials_and_assembles_p():

    print("listMaterialsAndAssemblesP....")

    _results = []
    _assemble_active_users = []

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def norm_code(v):
        return (v or '').strip()

    s = Session()

    try:

        # ============================================================
        # 1. 判斷是否仍存在「下一道尚未完成加工工序」
        #
        # 用途：
        #
        # 一般：
        #   show2_ok = 3 → 等待加工
        #   show2_ok = 4 → 加工中
        #
        # 特殊情況：
        #   show2_ok = 5
        #
        # 但若仍存在：
        #
        #   process_step_code > 0
        #   completed_qty < must_receive_end_qty
        #
        # 代表前一道已完成，但下一道尚未做，
        # 此 material 仍必須回到 PBegin。
        #
        # 例如：
        #   121200006714
        #
        #   B107-01 已完成
        #   B108-12 尚未加工
        # ============================================================

        pending_step_exists = (
            s.query(P_Assemble.id)
            .filter(
                P_Assemble.material_id
                ==
                P_Material.id
            )
            .filter(
                P_Assemble.process_step_code
                >
                0
            )
            .filter(
                func.coalesce(
                    P_Assemble.must_receive_end_qty,
                    P_Assemble.must_receive_qty,
                    0
                )
                >
                0
            )
            .filter(
                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                )
                <
                func.coalesce(
                    P_Assemble.must_receive_end_qty,
                    P_Assemble.must_receive_qty,
                    0
                )
            )
            .exists()
        )

        # ============================================================
        # 2. PBegin Material query
        # ============================================================

        _objects = (
            s.query(P_Material)

            .filter(
                P_Material.move_by_process_type
                ==
                4
            )

            .filter(
                P_Material.isShow.is_(True)
            )

            .filter(
                P_Material.isTakeOk.is_(True)
            )

            .filter(
                P_Material.show1_ok
                ==
                2
            )

            # --------------------------------------------------------
            # 原本只抓：
            #
            #   3 = 等待加工
            #   4 = 加工中 / 暫停
            #
            # 現在補：
            #
            #   5 + 還有下一道未完成工序
            # --------------------------------------------------------

            .filter(
                or_(
                    P_Material.show2_ok.in_(
                        ['3', '4']
                    ),

                    and_(
                        P_Material.show2_ok
                        ==
                        '5',

                        pending_step_exists
                    )
                )
            )

            .options(

                selectinload(
                    P_Material._assemble
                ).load_only(
                    P_Assemble.id,
                    P_Assemble.material_id,

                    P_Assemble.must_receive_qty,
                    # 20260824版 add
                    P_Assemble.ask_qty,
                    #
                    P_Assemble.must_receive_end_qty,
                    P_Assemble.total_ask_qty,

                    # 需要用來判斷是否真正完成
                    P_Assemble.completed_qty,
                    P_Assemble.total_completed_qty,

                    P_Assemble.work_num,
                    P_Assemble.process_step_code,
                    P_Assemble.isSimultaneously,
                    P_Assemble.seq_num,

                    P_Assemble.currentStartTime,
                    P_Assemble.input_disable,
                    P_Assemble.Incoming1_Abnormal,

                    P_Assemble.is_copied_from_id,
                    P_Assemble.create_at,

                    P_Assemble.isShowBomGif,
                    P_Assemble.isStockIn,

                    P_Assemble.isAssembleStationShow,
                    P_Assemble.isWarehouseStationShow,

                    P_Assemble.show2_ok,
                ),

                selectinload(
                    P_Material._process
                ).load_only(
                    P_Process.id,
                    P_Process.material_id,
                    P_Process.assemble_id,
                    P_Process.process_type,

                    P_Process.begin_time,
                    P_Process.end_time,

                    P_Process.process_work_time_qty,
                    P_Process.user_id,

                    P_Process.is_pause,
                    P_Process.elapsedActive_time,
                    P_Process.str_elapsedActive_time,
                ),
            )

            .all()
        )

        if not _objects:

            return jsonify({
                'status': False,
                'materials_and_assembles': [],
                'assemble_active_users': [],
            })

        # ============================================================
        # 3. P_Part map
        # ============================================================

        part_info_map = {}

        part_rows = (
            s.query(
                P_Part.part_code,
                P_Part.part_comment,
                P_Part.process_step_code
            )
            .all()
        )

        for (
            part_code,
            part_comment,
            process_step_code
        ) in part_rows:

            code = norm_code(
                part_code
            )

            if not code:
                continue

            part_info_map[
                code
            ] = {
                'comment':
                    (
                        part_comment
                        or ''
                    ).strip(),

                'process_step_code':
                    int(
                        process_step_code
                        or 0
                    ),
            }

        index = 0

        # ============================================================
        # 4. 每個 material
        # ============================================================

        for material_record in _objects:

            assemble_records = list(
                material_record._assemble
                or []
            )

            process_records = list(
                material_record._process
                or []
            )

            # --------------------------------------------------------
            # 有多少 Process 曾經建立
            # --------------------------------------------------------

            total_records = sum(
                1
                for p
                in process_records
                if (
                    p.material_id
                    ==
                    material_record.id

                    and

                    int(
                        p.assemble_id
                        or 0
                    )
                    != 0
                )
            )

            # ========================================================
            # 5. 找真正的「下一道未完成工序」
            #
            # 非同步工序只顯示 seq_num 最前的一道。
            #
            # 過濾：
            #
            #   step == 0
            #   已送 Warehouse
            #   已完成
            # ========================================================

            keep_assemble_id = None
            keep_seq = None

            for a in assemble_records:

                step = int(
                    a.process_step_code
                    or 0
                )

                # 已完成轉 step=0
                if step == 0:
                    continue

                # 已經送到 Warehouse
                if bool(
                    a.isWarehouseStationShow
                ):
                    continue

                must_end_qty = int(
                    getattr(
                        a,
                        'must_receive_end_qty',
                        0
                    )
                    or
                    getattr(
                        a,
                        'must_receive_qty',
                        0
                    )
                    or 0
                )

                completed_qty = max(
                    int(
                        getattr(
                            a,
                            'completed_qty',
                            0
                        )
                        or 0
                    ),

                    int(
                        getattr(
                            a,
                            'total_completed_qty',
                            0
                        )
                        or 0
                    ),
                )

                # ----------------------------------------------------
                # 已真正完成的舊工序，不應再次當成下一工序
                # ----------------------------------------------------

                if (
                    must_end_qty > 0
                    and
                    completed_qty
                    >=
                    must_end_qty
                ):
                    continue

                try:
                    seq = int(
                        a.seq_num
                        or 0
                    )
                except Exception:
                    seq = 999999

                if (
                    keep_assemble_id
                    is None

                    or

                    seq
                    <
                    keep_seq
                ):
                    keep_assemble_id = int(
                        a.id
                    )

                    keep_seq = seq

            # ========================================================
            # 6. Active process map
            #
            # 只算：
            #
            # begin_time 有值
            # end_time 為 NULL / 空
            # ========================================================

            proc_stat_map = {}

            for p in process_records:

                if (
                    p.material_id
                    !=
                    material_record.id
                ):
                    continue

                aid = int(
                    p.assemble_id
                    or 0
                )

                ptype = int(
                    p.process_type
                    or 0
                )

                if (
                    aid == 0
                    or
                    ptype == 0
                ):
                    continue

                # ----------------------------------------------------
                # 必須是 active process
                # ----------------------------------------------------

                if (
                    not p.begin_time

                    or

                    not str(
                        p.begin_time
                    ).strip()

                    or

                    (
                        p.end_time
                        is not None

                        and

                        str(
                            p.end_time
                        ).strip()
                        != ''
                    )
                ):
                    continue

                key = (
                    aid,
                    ptype
                )

                if key not in proc_stat_map:

                    proc_stat_map[
                        key
                    ] = {
                        'count': 0,
                        'qty_sum': 0,

                        'last_proc_id': 0,
                        'last_user_id': '',

                        'is_pause': False,

                        'elapsedActive_time': 0,
                        'str_elapsedActive_time':
                            '00:00:00',
                    }

                proc_stat_map[
                    key
                ]['count'] += 1

                proc_stat_map[
                    key
                ]['qty_sum'] += int(
                    p.process_work_time_qty
                    or 0
                )

                pid = int(
                    p.id
                    or 0
                )

                if (
                    pid
                    >=
                    proc_stat_map[
                        key
                    ]['last_proc_id']
                ):

                    proc_stat_map[
                        key
                    ]['last_proc_id'] = pid

                    proc_stat_map[
                        key
                    ]['last_user_id'] = (
                        p.user_id
                        or ''
                    )

                    proc_stat_map[
                        key
                    ]['is_pause'] = bool(
                        p.is_pause
                    )

                    proc_stat_map[
                        key
                    ]['elapsedActive_time'] = int(
                        p.elapsedActive_time
                        or 0
                    )

                    proc_stat_map[
                        key
                    ]['str_elapsedActive_time'] = (
                        p.str_elapsedActive_time
                        or
                        '00:00:00'
                    )

            cleaned_comment = safe_str(
                material_record.material_comment
            ).strip()

            # ========================================================
            # 7. Assemble rows
            # ========================================================

            for assemble_record in assemble_records:

                # ----------------------------------------------------
                # 已送 Warehouse，不顯示在 PBegin
                # ----------------------------------------------------

                if bool(
                    assemble_record
                    .isWarehouseStationShow
                ):
                    continue

                must_receive_qty = int(
                    getattr(
                        assemble_record,
                        'must_receive_qty',
                        0
                    )
                    or 0
                )

                if must_receive_qty <= 0:
                    continue

                step = int(
                    assemble_record
                    .process_step_code
                    or 0
                )

                if step == 0:
                    continue

                # ----------------------------------------------------
                # 再保護一次：
                # 已完成的舊工序不顯示
                # ----------------------------------------------------

                must_end_qty = int(
                    getattr(
                        assemble_record,
                        'must_receive_end_qty',
                        0
                    )
                    or
                    must_receive_qty
                    or 0
                )

                completed_qty = max(
                    int(
                        getattr(
                            assemble_record,
                            'completed_qty',
                            0
                        )
                        or 0
                    ),

                    int(
                        getattr(
                            assemble_record,
                            'total_completed_qty',
                            0
                        )
                        or 0
                    ),
                )

                if (
                    must_end_qty > 0
                    and
                    completed_qty
                    >=
                    must_end_qty
                ):
                    continue

                # ----------------------------------------------------
                # 非同步工序：
                # 只顯示最前面的下一道
                # ----------------------------------------------------

                is_simul = bool(
                    assemble_record
                    .isSimultaneously
                )

                if (
                    not is_simul
                    and
                    keep_assemble_id
                    is not None
                ):

                    if (
                        int(
                            assemble_record.id
                        )
                        !=
                        int(
                            keep_assemble_id
                        )
                    ):
                        continue

                # ====================================================
                # 8. 工序名稱
                # ====================================================

                work_num_clean = norm_code(
                    assemble_record.work_num
                )

                part_info = (
                    part_info_map.get(
                        work_num_clean,
                        {
                            'comment': '',
                            'process_step_code': 0,
                        }
                    )
                )

                show_comment = (
                    part_info.get(
                        'comment',
                        ''
                    )
                )

                show_code = int(
                    part_info.get(
                        'process_step_code',
                        0
                    )
                    or 0
                )

                # ====================================================
                # 9. 此工序目前是否有人執行
                # ====================================================

                stat = (
                    proc_stat_map.get(
                        (
                            int(
                                assemble_record.id
                            ),
                            show_code
                        ),
                        {
                            'count': 0,
                            'qty_sum': 0,
                            'last_user_id': '',
                            'is_pause': False,
                            'elapsedActive_time': 0,
                            'str_elapsedActive_time':
                                '00:00:00',
                        }
                    )
                )

                matched_count = int(
                    stat.get(
                        'count'
                    )
                    or 0
                )

                total_work_qty = int(
                    stat.get(
                        'qty_sum'
                    )
                    or 0
                )

                show_timer = (
                    matched_count
                    >
                    0
                )

                show_name = (
                    stat.get(
                        'last_user_id',
                        ''
                    )
                    if show_timer
                    else ''
                )

                # ----------------------------------------------------
                # 原本判斷保留
                # ----------------------------------------------------

                a_statement = (
                    show_code != 0

                    and

                    total_records != 0

                    and

                    matched_count > 0

                    and

                    total_work_qty
                    >=
                    int(
                        material_record
                        .delivery_qty
                        or 0
                    )
                )

                index += 1

                # ====================================================
                # 10. 回傳資料
                # ====================================================

                _object = {

                    'index':
                        index,

                    'row_key':
                        (
                            f"{material_record.id}_"
                            f"{assemble_record.id}_"
                            f"{step}"
                        ),

                    'is_running_row':
                        bool(
                            show_timer
                        ),

                    'id':
                        material_record.id,

                    'order_num':
                        material_record.order_num,

                    'assemble_work':
                        show_comment,

                    'material_num':
                        material_record.material_num,

                    'assemble_id':
                        assemble_record.id,

                    'req_qty':
                        material_record.material_qty,

                    'delivery_qty':
                        material_record.delivery_qty,

                    'total_receive_qty':
                        (
                            f"("
                            f"{getattr(assemble_record, 'total_ask_qty', 0)}"
                            f")"
                        ),

                    'total_receive_qty_num':
                        getattr(
                            assemble_record,
                            'total_ask_qty',
                            0
                        ),

                    #'must_receive_qty':
                    #    getattr(
                    #        assemble_record,
                    #        'must_receive_qty',
                    #        0
                    #    ),

                    #'receive_qty':
                    #    getattr(
                    #        assemble_record,
                    #        'must_receive_qty',
                    #        0
                    #    ),
                    # 20260824版
                    #'receive_qty':
                    #    getattr(
                    #        assemble_record,
                    #        'ask_qty',
                    #        0
                    #    ),
                    #

                    'must_receive_end_qty':
                        assemble_record
                        .must_receive_end_qty,

                    # 20260824版
                    'must_receive_qty':
                        int(
                            getattr(
                                assemble_record,
                                'must_receive_qty',
                                0
                            ) or 0
                        ),

                    'receive_qty':
                        int(
                            getattr(
                                assemble_record,
                                'ask_qty',
                                0
                            ) or 0
                        ),
                    #

                    'delivery_date':
                        material_record
                        .material_delivery_date,

                    'comment':
                        cleaned_comment,

                    'isTakeOk':
                        material_record.isTakeOk,

                    'isAssembleStation1TakeOk':
                        material_record
                        .isAssembleStation1TakeOk,

                    'isAssembleStation2TakeOk':
                        material_record
                        .isAssembleStation2TakeOk,

                    'isAssembleStation3TakeOk':
                        material_record
                        .isAssembleStation3TakeOk,

                    'currentStartTime':
                        getattr(
                            assemble_record,
                            'currentStartTime',
                            None
                        ),

                    'tooltipVisible':
                        False,

                    'input_disable':
                        getattr(
                            assemble_record,
                            'input_disable',
                            False
                        ),

                    'Incoming1_Abnormal':
                        (
                            getattr(
                                assemble_record,
                                'Incoming1_Abnormal',
                                ''
                            )
                            ==
                            ''
                        ),

                    'is_copied_from_id':
                        getattr(
                            assemble_record,
                            'is_copied_from_id',
                            None
                        ),

                    'create_at':
                        assemble_record
                        .create_at,

                    'show_timer':
                        show_timer,

                    'show_name':
                        show_name,

                    'is_pause':
                        bool(
                            stat.get(
                                'is_pause',
                                False
                            )
                        ),

                    'elapsedActive_time':
                        int(
                            stat.get(
                                'elapsedActive_time'
                            )
                            or 0
                        ),

                    'str_elapsedActive_time':
                        (
                            stat.get(
                                'str_elapsedActive_time'
                            )
                            or
                            '00:00:00'
                        ),

                    'isShowBomGif':
                        assemble_record
                        .isShowBomGif,

                    'process_step_code':
                        assemble_record
                        .process_step_code,

                    # -----------------------------------------------
                    # 只是畫面顯示「不入庫」
                    # 不拿來決定 Begin 是否顯示
                    # -----------------------------------------------

                    'isStockIn':
                        (
                            ''
                            if assemble_record
                            .isStockIn
                            else
                            ' [不入庫]'
                        ),

                    'isWarehouseStationShow':
                        bool(
                            assemble_record
                            .isWarehouseStationShow
                        ),

                    'assemble_process_num':
                        int(
                            assemble_record
                            .show2_ok
                            or 0
                        ),
                }

                _results.append(
                    _object
                )

        # test
        # ============================================================
        # DEBUG：確認後端到底回幾筆
        # ============================================================

        print("========== PBegin RESULT DEBUG ==========")

        for row in _results:
            print(
                "order_num=",
                row.get("order_num"),
                "material_id=",
                row.get("id"),
                "assemble_id=",
                row.get("assemble_id"),
                "step=",
                row.get("process_step_code"),
                "row_key=",
                row.get("row_key"),
            )

        print(
            "PBegin result count =",
            len(_results)
        )

        print("=========================================")
        #

        # ============================================================
        # 11. 排序
        # ============================================================

        _results.sort(
            key=lambda x: (
                0
                if x.get(
                    'is_running_row'
                )
                else 1,

                -(
                    x.get(
                        'create_at'
                    ).timestamp()
                )
                if x.get(
                    'create_at'
                )
                else 0,

                x.get(
                    'id'
                )
                or 0,

                x.get(
                    'assemble_id'
                )
                or 0,
            )
        )

        print(
            "listMaterialsAndAssemblesP, 總數:",
            len(
                _results
            )
        )

        return jsonify({
            'status':
                bool(
                    _results
                ),

            'materials_and_assembles':
                _results
                or [],

            'assemble_active_users':
                _assemble_active_users
                or [],
        })

    except Exception as e:

        print(
            "listMaterialsAndAssemblesP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        try:

            current_app.logger.exception(
                "listMaterialsAndAssemblesP failed"
            )

        except Exception:
            pass

        return jsonify({
            'status': False,
            'materials_and_assembles': [],
            'assemble_active_users': [],
        }), 200

    finally:

        s.close()



"""
# 20260813版
@listTableP.route("/listInformationsP", methods=['GET'])
def list_informations_p():
    print("listInformationsP....")

    #false: 全部顯示
    #true: 只顯示未完成
    only_unfinished = request.args.get("only_unfinished", "0") in ("1", "true", "True")
    print('\033[42m' + 'only_unfinished:' + '\033[0m',   only_unfinished)

    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))

    s = Session()

    _results = []
    return_value = True
    str1=['領料站', '加工站', '成品站']
    #      0        1         2            3              4                5               6              7            8
    str2=['未領料', '領料中', '領料已完成', '等待加工作業', '加工作業進行中', '加工作業已完成', '等待入庫作業', '入庫進行中', '入庫完成']

    # ✅ 彙總：每個 material_id 的 廢品（p_assemble）
    asm_scrap = (
        s.query(
            P_Assemble.material_id.label("mid"),
            func.coalesce(func.sum(P_Assemble.abnormal_qty), 0).label("scrap_qty"),
        )
        .group_by(P_Assemble.material_id)
        .subquery()
    )

    # ✅ 彙總：每個 material_id 的 入庫（現況數量：p_product.allOk_qty）
    prd_stockin = (
        s.query(
            P_Product.material_id.label("mid"),
            func.coalesce(func.sum(P_Product.allOk_qty), 0).label("stockin_qty"),
        )
        .group_by(P_Product.material_id)
        .subquery()
    )

    # ✅ 統一查詢：永遠回 (P_Material, scrap_qty, stockin_qty)
    q = (
        s.query(
            P_Material,
            func.coalesce(asm_scrap.c.scrap_qty, 0).label("scrap_qty"),
            func.coalesce(prd_stockin.c.stockin_qty, 0).label("stockin_qty"),
        )
        .outerjoin(asm_scrap, asm_scrap.c.mid == P_Material.id)
        .outerjoin(prd_stockin, prd_stockin.c.mid == P_Material.id)
    )

    # ✅ switchValue=ON：只顯示未完成
    if only_unfinished:
        q = q.filter(
            func.coalesce(P_Material.material_qty, 0) !=
            (func.coalesce(asm_scrap.c.scrap_qty, 0) + func.coalesce(prd_stockin.c.stockin_qty, 0))
        )

    total = q.count()  # ✅ 總筆數（給前端算總頁數）

    _objects = q.all()

    def norm_code(x: str) -> str:
      return (x or "").strip().upper().replace(" ", "")

    # 把 B102KL-01 / B102KT-01 這種轉成 B102-01 的 alias
    # 規則：^(B\d{3})[A-Z]*-(\d+)$  =>  B102KL-01 -> B102-01
    def alias_code(x: str) -> str:
      x = norm_code(x)
      m = re.match(r'^(B\d{3})[A-Z]*-(\d+)$', x)
      if not m:
        return x
      return f"{m.group(1)}-{m.group(2)}"

    part_info_map = {}
    for p in s.query(P_Part).all():
      code_raw = (p.part_code or "")
      code = norm_code(code_raw)
      if not code:
        continue

      info = {
          "comment": (p.part_comment or "").strip(),
          "process_step_code": int(p.process_step_code or 0),
      }

      # 1) 原始 key：B102KL-01
      part_info_map[code] = info

      # 2) alias key：B102-01（讓 work_num=B102-01 也查得到）
      akey = alias_code(code)
      part_info_map.setdefault(akey, info)

    for record, scrap_qty, stockin_qty in _objects:
      assemble_records = record._assemble   # 存取與該 Material 物件關聯的所有 Assemble 物件

      process_records = record._process
      #total_process_records =len([p for p in process_records if ((p.material_id == record.id and p.has_started == 1 and p.begin_time != ''))])
      # 20260813版
      # ------------------------------------------------------------
      # Information「詳情」只要曾經有有效 Process 紀錄就應可查看。
      #
      # 不可限制 has_started == 1，
      # 因為加工完成後 has_started 會變 False。
      # ------------------------------------------------------------
      total_process_records = len([
          p
          for p in process_records
          if (
              int(p.material_id or 0)
              ==
              int(record.id or 0)
              and
              str(
                  p.begin_time or ''
              ).strip() != ''
          )
      ])
      #


      cleaned_comment = record.material_comment.strip()  # 刪除 material_comment 字串前後的空白

      raw = getattr(record, "show2_ok", None)
      num = -1
      try:
        num = int(raw)
      except Exception as e:
        print("❌ show2_ok parse failed",
              "material_id:", record.id,
              "order_num:", record.order_num,
              "raw:", raw,
              "err:", repr(e))
        num = -1

      # ✅ 兼容兩種：0-based(0~8) / 1-based(1~9)
      if 0 <= num < len(str2):
          temp_show2_ok_str = str2[num]
      elif 1 <= num <= len(str2):
          temp_show2_ok_str = str2[num - 1]
      else:
          print("❌ show2_ok OUT OF RANGE", "num:", num, "len(str2):", len(str2))
          temp_show2_ok_str = f"未知狀態({raw})"

      temp_show2_ok = num  # 後面 if temp_show2_ok == 5 ... 才不會用到舊值

      if (temp_show2_ok == 1):
        user = s.query(User).filter_by(emp_id=record.isOpenEmpId).first()
        temp_name=''
        if user:
          temp_name = '(' + user.emp_name + ')'
        temp_show2_ok_str = temp_show2_ok_str + temp_name

      temp_show2_ok_str = re.sub(r'\b00\b', '00', temp_show2_ok_str)

      # 處理 show3_ok 的情況
      show3_ok_val = int(record.show3_ok)
      show_comment =''

      if (record.isBom) or (not record.isBom and record.isTakeOk and record.isShow):
        if record._assemble:
          valid_assembles = [
              a for a in record._assemble
              if (a.work_num not in (None,'','0') and a.seq_num is not None and str(a.seq_num).isdigit())
          ]

          if valid_assembles:   # if_loop_b
            min_assemble_record = min(
              valid_assembles,
              key=lambda a: int(a.seq_num)
            )

            show3_ok = (min_assemble_record.work_num or "").strip()

            key = norm_code(show3_ok)
            part_info = part_info_map.get(key)
            if not part_info:
              # 再試一次 alias（萬一 work_num 反而帶 KL/KT 之類）
              part_info = part_info_map.get(alias_code(key))

            if part_info:
              show_comment = part_info.get("comment", "")
            else:
              show_comment = ""
              print(f"[DEBUG show3_ok] miss, work_num={show3_ok}, key={key}")

          # end if_loop_b

      stockin_total = int(stockin_qty or 0)

      def _to_int(v, default=0):
          try:
              if v is None:
                  return default
              return int(v)
          except Exception:
              return default

      # ✅ 若尚未入庫(stockin_total=0)，現況數量改用「扣報廢後的良品量」
      # p_assemble 第一筆 must_receive_end_qty=190，第二筆 abnormal_qty=10 → 現況要顯示 190
      net_good_qty = 0
      for a in assemble_records:
          net_good_qty = max(net_good_qty, _to_int(getattr(a, "must_receive_end_qty", 0), 0))
          # 資料中已有 total_ask_qty_end=190，保留當 fallback
          if net_good_qty == 0:
              net_good_qty = max(net_good_qty, _to_int(getattr(a, "total_ask_qty_end", 0), 0))

      delivery_qty = int(stockin_total) if int(stockin_total) > 0 else (net_good_qty if net_good_qty > 0 else _to_int(record.delivery_qty, 0))

      _object = {
        'id': record.id,                                #訂單編號的table id
        'order_num': record.order_num,                  #訂單編號
        'material_num': record.material_num,            #物料編號
        'isTakeOk': record.isTakeOk,
        'whichStation': record.whichStation,
        'req_qty': record.material_qty,                 #需求數量
        'delivery_date':record.material_delivery_date,  #交期
        'delivery_qty': delivery_qty,
        'comment': cleaned_comment,                     #說明
        'show1_ok' : str1[int(record.show1_ok) - 1],    #現況進度(上面文字說明)
        'show2_ok' : temp_show2_ok_str,                 #現況進度(下面文字說明)
        'show3_ok' : show_comment if temp_show2_ok_str != '入庫完成' else '入庫完成',                      #現況備註(加工製程)
        'isOpenEmpId': record.isOpenEmpId,
        'total_process_records': total_process_records,
      }

      _results.append(_object)

    s.close()

    if not _objects:
        print("⚠️ 沒有資料")
        return jsonify({'status': False, 'informations': []})

    temp_len = len(_results)

    print("listInformationsP, 總數: ", temp_len)

    _results = sorted(
      _results,
      key=lambda x: (x.get('total_process_records', 0) == 0, x['order_num'])
    )

    return jsonify({
      'status': True,
      'total': total,
      'informations': _results
    })
"""


"""
# 20260814版
# ================================================================
# PInformation
#
# 改為：
#
#   同 order_num 多個 P_Material
#       ↓
#   後端統一彙總
#       ↓
#   一張訂單只回傳一筆
#
# 例如：
#
# 121200006445
#
# material_id=16
#   完成 250
#   入庫 250
#
# material_id=50
#   完成 246
#   入庫 0
#
# 整單：
#
#   已完成 = 496
#   已入庫 = 250
#
#   show2_ok = 等待入庫作業
#   show3_ok = 已入庫 250 / 已完成 496
#
# ================================================================

@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    # ------------------------------------------------------------
    # false：全部顯示
    # true ：只顯示未完成
    #
    # 注意：
    # 新版不能在 SQL Material level 就先 filter，
    # 必須 group order_num 後才能判定整張訂單是否完成。
    # ------------------------------------------------------------

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    try:
        limit = int(
            request.args.get(
                "limit",
                20
            )
        )
    except Exception:
        limit = 20

    try:
        offset = int(
            request.args.get(
                "offset",
                0
            )
        )
    except Exception:
        offset = 0

    limit = max(
        1,
        min(
            limit,
            2000
        )
    )

    offset = max(
        0,
        offset
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default

        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default

        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )

        # --------------------------------------------------------
        # B102KL-01
        # B102KT-01
        #
        # ↓
        #
        # B102-01
        # --------------------------------------------------------

        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )

        # ========================================================
        # 狀態
        #
        # P_Material.show2_ok：
        #
        # 0 未領料
        # 1 領料中
        # 2 領料已完成
        # 3 等待加工作業
        # 4 加工作業進行中
        # 5 加工作業已完成
        # 6 等待入庫作業
        # 7 入庫進行中
        # 8 入庫完成
        # ========================================================

        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "加工作業已完成",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }

        def status_text(
            status_code
        ):

            return (
                STATUS_TEXT.get(
                    to_int(
                        status_code,
                        -1
                    ),
                    f"未知狀態({status_code})"
                )
            )

        # ========================================================
        # show1 / 站別
        #
        # 不再直接拿某一個 material.show1_ok，
        # 而由整張訂單狀態推導。
        # ========================================================

        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"

        # ========================================================
        # 1. P_Part mapping
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            raw_code = safe_str(
                p.part_code
            )

            code = norm_code(
                raw_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            # 原始
            part_info_map[
                code
            ] = info

            # alias
            part_info_map.setdefault(
                alias_code(code),
                info
            )

        # ========================================================
        # 2. 每個 material 的報廢數量
        # ========================================================

        scrap_rows = (
            s.query(
                P_Assemble.material_id,
                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in scrap_rows
        }

        # ========================================================
        # 3. 每個 material 的真正入庫數量
        #
        # P_Product 是真正入庫來源。
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,
                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in stockin_rows
        }

        # ========================================================
        # 4. 一次取得所有 Material
        #
        # 不能先做 only_unfinished filter，
        # 因為現在未完成是 order_num aggregate level。
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })

        # ========================================================
        # 5. 依 order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )

        results = []

        # ========================================================
        # 6. 每張工單進行彙總
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue

            # ----------------------------------------------------
            # 找代表資料。
            #
            # 優先 root：
            #
            # is_copied_from_id IS NULL
            #
            # 再以最小 id。
            #
            # 代表資料只負責：
            #
            # material_num
            # material_comment
            # material_qty
            # delivery_date
            #
            # 狀態與數量絕對不由它單獨決定。
            # ----------------------------------------------------

            representative = sorted(
                group_materials,
                key=lambda m: (
                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]

            # ----------------------------------------------------
            # 整張訂單統計
            # ----------------------------------------------------

            total_stockin = 0
            total_completed = 0
            total_scrap = 0
            total_process_records = 0

            material_summaries = []

            # ====================================================
            # 6-1. 每個 material / 每個批次先算自己的狀態
            # ====================================================
            '''
            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )

                assemble_records = list(
                    material._assemble
                    or []
                )

                process_records = list(
                    material._process
                    or []
                )
            '''
            # 20260814版
            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )

                # -------------------------------------------------
                # PInformation 使用 DB 真實歷史資料，
                # 不依賴 relationship cache。
                # -------------------------------------------------

                assemble_records = (
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

                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )
            #

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )

                material_scrap = (
                    scrap_map.get(
                        material_id,
                        0
                    )
                )

                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )

                # =================================================
                # 此 material 有效 Process 數
                #
                # 詳情按鈕需要。
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id
                        and
                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]

                total_process_records += (
                    len(
                        valid_processes
                    )
                )

                # =================================================
                # 此批「完成數量」
                #
                # 重要：
                #
                # 不可 sum 所有 P_Process.process_work_time_qty。
                #
                # 因為同一批可能經過：
                #
                #   B100
                #   B102
                #   B107
                #
                # 每一站都是 250，
                #
                # sum 會變成：
                #
                #   250 + 250 + 250 = 750
                #
                # 這是錯的。
                #
                # 所以一個 material 只取「最大完成量」。
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = (
                        to_int(
                            p.process_type,
                            0
                        )
                    )

                    # 領料 / 搬運不是加工完成量
                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    # 必須是真正有完成的加工紀錄
                    if (
                        not safe_str(
                            p.begin_time
                        ).strip()
                    ):
                        continue

                    if (
                        not safe_str(
                            p.end_time
                        ).strip()
                    ):
                        continue

                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )

                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )

                '''
                # ------------------------------------------------
                # Assemble fallback
                # ------------------------------------------------

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_completed_qty = max(
                        assemble_completed_qty,

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "must_receive_end_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_ask_qty_end",
                                0
                            ),
                            0
                        ),
                    )
                '''

                '''
                # =================================================
                # Assemble 真正完成數量
                #
                # 注意：
                #
                # 只能使用真正「已完成」欄位：
                #
                #   completed_qty
                #   total_completed_qty
                #
                # 不可使用：
                #
                #   must_receive_end_qty
                #   total_ask_qty_end
                #
                # 因為它們是應完成量 / 應加工量，
                # 不是實際已完成量。
                #
                # 例如：
                #
                # 121200006702 / material_id=57
                #
                #   must_receive_end_qty = 100
                #   completed_qty        = 0
                #
                # 而 Process 還在加工：
                #
                #   begin_time = 2026-08-13 09:00:39
                #   end_time   = NULL
                #   qty        = 0
                #
                # 所以 completed 必須仍為 0。
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    row_completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )

                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )
                '''
                # 20260814版
                # =================================================
                # Assemble fallback 完成數量
                #
                # 非常重要：
                #
                # 只有真正「結束列」：
                #
                #     process_step_code == 0
                #
                # 才能把 completed_qty / total_completed_qty
                # 當成已完成數量。
                #
                # 尚在加工中的：
                #
                #     process_step_code > 0
                #
                # 即使 completed_qty / total_completed_qty
                # 因舊資料、預填或同步問題有數值，
                # 也不能算入 PInformation 的「已完成」。
                #
                # 例如：
                #
                # 121200006702
                # material_id=57
                # assemble_id=64
                #
                # process_step_code = 98
                # P_Process:
                #   begin_time = 2026-08-13 09:00:39
                #   end_time   = NULL
                #   qty        = 0
                #
                # 所以目前已完成必須為 0。
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    # -------------------------------------------------
                    # 尚在加工中的工序，不可拿來當「已完成」fallback
                    # -------------------------------------------------
                    if assemble_step != 0:
                        continue

                    row_completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )

                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )
                #

                # ------------------------------------------------
                # 此批真正完成量
                #
                # 入庫數量本身也代表至少完成過這麼多，
                # 所以一起 max，避免舊資料 Process 遺失。
                # ------------------------------------------------

                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )

                total_completed += (
                    material_completed
                )

                # =================================================
                # 是否有正在加工的 Process
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = (
                        to_int(
                            p.process_type,
                            0
                        )
                    )

                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )

                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )

                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = (
                            True
                        )

                        break

                # =================================================
                # 此批 batch status
                #
                # 優先使用實際資料修正 show2_ok。
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )

                # ------------------------------------------------
                # A. 還有人正在加工
                # ------------------------------------------------

                if has_active_process:

                    batch_status = 4

                # ------------------------------------------------
                # B. 已有完成量，但尚未全部入庫
                #
                # 若 DB 明確是入庫進行中 7，
                # 保留 7。
                # 否則為等待入庫 6。
                # ------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:
                        batch_status = 7
                    else:
                        batch_status = 6

                # ------------------------------------------------
                # C. 此批完成量全部已入庫
                # ------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8

                # ------------------------------------------------
                # D. 尚無完成量
                #
                # 使用原 show2_ok。
                # ------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )

                material_summaries.append({
                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,
                })

            # ====================================================
            # 6-2. 整張 order_num 的狀態
            #
            # 原則：
            #
            # 「最未完成的一批」決定整張訂單現況。
            #
            # 例如：
            #
            # batch A = 8 入庫完成
            # batch B = 6 等待入庫
            #
            # 整張 = 6 等待入庫
            #
            # batch A = 8
            # batch B = 4 加工中
            #
            # 整張 = 4 加工中
            # ====================================================

            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )
                for item
                in material_summaries
            ]

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )

            # ====================================================
            # 安全修正：
            #
            # 只要整單已有完成量，但：
            #
            #   入庫量 < 完成量
            #
            # 而且沒有更前段（0~5）的批次，
            #
            # 就必須是等待/進行入庫，
            # 絕不能顯示「入庫完成」。
            # ====================================================

            if (
                total_completed > 0
                and
                total_stockin
                <
                total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:
                    order_status = 7
                else:
                    order_status = 6

            # ====================================================
            # 全部 batch 都完成入庫才是 8
            # ====================================================

            all_batches_stockin_done = bool(
                material_summaries
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0
                    and
                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )
                )
                for item
                in material_summaries
            )

            if all_batches_stockin_done:

                order_status = 8

            # ====================================================
            # 6-3. only_unfinished
            #
            # 現在一定要在 order aggregate 後判斷。
            # ====================================================

            if (
                only_unfinished
                and
                order_status == 8
            ):
                continue

            '''
            # ====================================================
            # 6-4. show3 現況備註
            #
            # 只要已有完成量，
            # 就顯示：
            #
            #   已入庫 250 / 已完成 496
            #
            # 這是目前建議的主要顯示方式。
            # ====================================================

            if total_completed > 0:

                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / "
                    f"已完成 {total_completed}"
                )

            else:
            '''
            # 20260814版
            # ====================================================
            # 6-4. show3 現況備註
            #
            # 顯示原則：
            #
            # 0~5：
            #   尚處於領料 / 加工階段
            #   → 顯示目前加工製程
            #
            # 6~8：
            #   已進入成品 / 入庫階段
            #   → 才顯示：
            #
            #       已入庫 X / 已完成 Y
            #
            # 這樣可避免：
            #
            # 121200006702
            #   order_status = 4
            #   還在加工
            #
            # 卻錯誤顯示：
            #   已入庫 0 / 已完成 100
            # ====================================================

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / "
                    f"已完成 {total_completed}"
                )

            else:
            #

                # ------------------------------------------------
                # 還沒有任何完成量時，
                # 維持舊邏輯：
                # 找目前最前面的加工製程名稱。
                # ------------------------------------------------

                show3_text = ""

                # 先找目前決定 order_status 的 material
                status_materials = [
                    item
                    for item
                    in material_summaries
                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        ==
                        order_status
                    )
                ]

                if not status_materials:
                    status_materials = (
                        material_summaries
                    )

                for item in status_materials:

                    material = item[
                        "material"
                    ]

                    valid_assembles = [
                        a
                        for a
                        in (
                            material._assemble
                            or []
                        )
                        if (
                            safe_str(
                                a.work_num
                            ).strip()
                            not in (
                                "",
                                "0",
                            )
                            and
                            safe_str(
                                a.seq_num
                            ).strip()
                            .isdigit()
                        )
                    ]

                    if not valid_assembles:
                        continue

                    min_assemble = min(
                        valid_assembles,
                        key=lambda a:
                            to_int(
                                a.seq_num,
                                999999
                            )
                    )

                    work_num = safe_str(
                        min_assemble.work_num
                    ).strip()

                    key = norm_code(
                        work_num
                    )

                    part_info = (
                        part_info_map.get(
                            key
                        )
                        or
                        part_info_map.get(
                            alias_code(key)
                        )
                    )

                    if part_info:

                        show3_text = safe_str(
                            part_info.get(
                                "comment"
                            )
                        ).strip()

                    else:

                        show3_text = (
                            work_num
                        )

                    if show3_text:
                        break

            # ====================================================
            # 6-5. 領料中人員
            #
            # 若整單狀態是 1，
            # 優先找該批 isOpenEmpId。
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue

                    m = item[
                        "material"
                    ]

                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )

                    if display_open_emp_id:
                        break

            # ====================================================
            # 6-6. 現況數量 delivery_qty
            #
            # 新版定義：
            #
            # 已有入庫：
            #   顯示已入庫數
            #
            # 尚未入庫但已有完成：
            #   顯示已完成數
            #
            # 都沒有：
            #   fallback 舊 delivery_qty
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )

            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )

            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )

            # ====================================================
            # 6-7. 建立整單唯一 row
            # ====================================================

            result = {

                # ------------------------------------------------
                # id：
                # 保留 representative material id，
                # 避免前端既有邏輯突然沒有 id。
                # ------------------------------------------------
                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                # ------------------------------------------------
                # 站別
                # ------------------------------------------------

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                # ------------------------------------------------
                # 原始訂單需求量
                #
                # 不跨 material 相加，
                # 因為 copy material 通常仍保存整張訂單 qty。
                # ------------------------------------------------

                "req_qty":
                    to_int(
                        representative.material_qty,
                        0
                    ),

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative
                        .material_comment
                    ).strip(),

                # ------------------------------------------------
                # 現況
                # ------------------------------------------------

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                # ------------------------------------------------
                # Information 詳情按鍵用
                # ------------------------------------------------

                "total_process_records":
                    total_process_records,

                # ------------------------------------------------
                # 新增：
                # 前端之後若要另外做欄位可直接使用。
                # ------------------------------------------------

                "material_count":
                    len(
                        group_materials
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,
            }

            results.append(
                result
            )

        # ========================================================
        # 7. 排序
        #
        # 有 Process 的優先。
        # 再依 order_num。
        # ========================================================

        results.sort(
            key=lambda x: (
                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    == 0
                ),
                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )

        # ========================================================
        # 8. total 已經是「工單數」
        #
        # 不再是 material 數。
        # ========================================================

        total = len(
            results
        )

        # ========================================================
        # 9. pagination
        #
        # 一定要在 group order_num 後再切頁，
        # 否則同一 order 的 materials 可能被分到不同頁。
        # ========================================================

        page_results = (
            results[
                offset:
                offset + limit
            ]
        )

        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(page_results)
        )

        # --------------------------------------------------------
        # Debug：
        # 方便你現在測 121200006445。
        # --------------------------------------------------------

        for row in page_results:

            if (
                row.get(
                    "order_num"
                )
                ==
                "121200006445"
            ):

                print(
                    "[PInformation DEBUG]",
                    row.get(
                        "order_num"
                    ),
                    "material_ids=",
                    row.get(
                        "material_ids"
                    ),
                    "completed=",
                    row.get(
                        "completed_total"
                    ),
                    "stockin=",
                    row.get(
                        "stockin_total"
                    ),
                    "remaining=",
                    row.get(
                        "remaining_stockin_qty"
                    ),
                    "status=",
                    row.get(
                        "show2_ok"
                    ),
                    "show3=",
                    row.get(
                        "show3_ok"
                    ),
                )

        return jsonify({
            "status":
                True,

            "total":
                total,

            "informations":
                page_results,
        })

    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        logger.exception(
            "listInformationsP failed"
        )

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500

    finally:

        s.close()
"""


"""
# 20260815版
# ================================================================
# PInformation
#
# 主要規則：
#
# 1. 同 order_num 多個 P_Material -> 合併成一筆
#
# 2. 已完成量：
#    - 優先使用「有 begin_time + end_time」的 P_Process
#    - 同 material 多道工序不可相加，只取最大完成量
#    - P_Assemble fallback 只允許 process_step_code == 0
#
# 3. 入庫量：
#    - P_Product.allOk_qty
#
# 4. 廢品量：
#    - P_Assemble.abnormal_qty
#    - P_Product.non_good_qty
#    - 為避免同一廢品重複記錄，兩來源取 max，不相加
#
# 5. show3_ok：
#
#    加工階段：
#        加工(一)-精車
#
#    入庫階段，無廢品：
#        已入庫 250 / 已完成 496
#
#    真正有廢品：
#        已入庫 107 / 廢品 3 / 訂單 110
#
#    訂單量有差額、但 DB 沒有廢品：
#        已入庫 107 / 已完成 107 / 訂單 110（差異 3）
#
# ================================================================

@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    try:
        limit = int(
            request.args.get(
                "limit",
                20
            )
        )
    except Exception:
        limit = 20

    try:
        offset = int(
            request.args.get(
                "offset",
                0
            )
        )
    except Exception:
        offset = 0

    limit = max(
        1,
        min(
            limit,
            2000
        )
    )

    offset = max(
        0,
        offset
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default

        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default

        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )

        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )

        # ========================================================
        # 狀態
        # ========================================================
        '''
        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "加工作業已完成",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }
        '''
        # 20260815版
        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",

            # 加工完成，但仍停在 PEnd
            5: "等待送出",

            # 已送到成品區 / Warehouse
            6: "等待入庫作業",

            7: "入庫進行中",
            8: "入庫完成",
        }
        #

        def status_text(
            status_code
        ):

            return STATUS_TEXT.get(
                to_int(
                    status_code,
                    -1
                ),
                f"未知狀態({status_code})"
            )

        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"

        # ========================================================
        # 1. P_Part 製程名稱 map
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            code = norm_code(
                p.part_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            part_info_map[
                code
            ] = info

            part_info_map.setdefault(
                alias_code(code),
                info
            )

        # ========================================================
        # 2. P_Assemble 廢品
        # ========================================================

        asm_scrap_rows = (
            s.query(
                P_Assemble.material_id,

                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        asm_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in asm_scrap_rows
        }

        # ========================================================
        # 3. P_Product 入庫量
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in stockin_rows
        }

        # ========================================================
        # 4. P_Product 廢品
        #
        # 不與 P_Assemble.abnormal_qty 直接相加，
        # 避免同一批廢品重複計算。
        # ========================================================

        product_scrap_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.non_good_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in product_scrap_rows
        }

        # ========================================================
        # 5. 所有 Material
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })

        # ========================================================
        # 6. order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )

        results = []

        # ========================================================
        # 7. 每張訂單彙總
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue

            # ----------------------------------------------------
            # root material 優先當代表資料
            # ----------------------------------------------------

            representative = sorted(
                group_materials,
                key=lambda m: (
                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]

            req_qty = to_int(
                representative.material_qty,
                0
            )

            total_stockin = 0
            total_completed = 0
            total_scrap = 0
            total_process_records = 0

            material_summaries = []

            # show3 加工製程 fallback
            current_process_comment = ""

            # ====================================================
            # 7-1. 每個 material
            # ====================================================

            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )

                # ------------------------------------------------
                # 直接 query DB，
                # 不依賴 relationship cache
                # ------------------------------------------------

                assemble_records = (
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

                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )

                # ------------------------------------------------
                # 入庫量
                # ------------------------------------------------

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )

                # ------------------------------------------------
                # 廢品量
                #
                # 兩來源可能是同一批異常資料，
                # 使用 max 避免 double count。
                # ------------------------------------------------

                assemble_scrap = (
                    asm_scrap_map.get(
                        material_id,
                        0
                    )
                )

                product_scrap = (
                    product_scrap_map.get(
                        material_id,
                        0
                    )
                )

                material_scrap = max(
                    assemble_scrap,
                    product_scrap,
                    0,
                )

                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )

                # =================================================
                # 詳情按鈕 Process count
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id
                        and
                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]

                total_process_records += (
                    len(
                        valid_processes
                    )
                )

                # =================================================
                # 真正 Process 完成量
                #
                # 同 material 多製程不能相加，
                # 取最大完成良品量。
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = (
                        to_int(
                            p.process_type,
                            0
                        )
                    )

                    # 領料、搬運不算加工完成量
                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    # 必須真正開始且真正結束
                    if (
                        not safe_str(
                            p.begin_time
                        ).strip()
                    ):
                        continue

                    if (
                        not safe_str(
                            p.end_time
                        ).strip()
                    ):
                        continue

                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )

                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )

                # =================================================
                # P_Assemble fallback
                #
                # 只有 process_step_code == 0
                # 才能算已完成。
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    if assemble_step != 0:
                        continue

                    row_completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )

                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )

                # =================================================
                # 此 material 已完成「良品」量
                # =================================================

                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )

                total_completed += (
                    material_completed
                )

                # =================================================
                # Active Process
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = (
                        to_int(
                            p.process_type,
                            0
                        )
                    )

                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )

                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )

                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = True
                        break

                # =================================================
                # 找目前製程名稱
                # =================================================

                if not current_process_comment:

                    valid_assembles = [
                        a
                        for a
                        in assemble_records
                        if (
                            safe_str(
                                a.work_num
                            ).strip()
                            not in (
                                "",
                                "0",
                            )
                            and
                            to_int(
                                a.process_step_code,
                                0
                            ) > 0
                        )
                    ]

                    if valid_assembles:

                        min_assemble = min(
                            valid_assembles,
                            key=lambda a:
                                to_int(
                                    a.seq_num,
                                    999999
                                )
                        )

                        work_num = safe_str(
                            min_assemble.work_num
                        ).strip()

                        key = norm_code(
                            work_num
                        )

                        part_info = (
                            part_info_map.get(
                                key
                            )
                            or
                            part_info_map.get(
                                alias_code(key)
                            )
                        )

                        if part_info:

                            current_process_comment = (
                                safe_str(
                                    part_info.get(
                                        "comment"
                                    )
                                ).strip()
                            )

                        else:

                            current_process_comment = (
                                work_num
                            )
                '''
                # =================================================
                # material 狀態
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )

                # 20260815版
                # =================================================
                # 是否仍在 PEnd 等待送出
                #
                # 條件：
                #
                # process_step_code == 0
                # completed_qty > 0
                # isAssembleStationShow = True
                # isWarehouseStationShow = False
                #
                # 代表：
                #   加工已完成
                #   但尚未按「送出」
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(getattr(a, "process_step_code", -1), -1) == 0
                        and
                        to_int(getattr(a, "completed_qty", 0), 0) > 0
                        and
                        bool(getattr(a, "isAssembleStationShow", False))
                        and
                        not bool(getattr(a, "isWarehouseStationShow", False))
                    )
                    for a in assemble_records
                )

                # =================================================
                # 是否已真正送到 Warehouse
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )
                    for a in assemble_records
                )

                # -------------------------------------------------
                # A. 還在加工
                # -------------------------------------------------

                if has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # B. 加工完成，但仍留在 PEnd 等待送出
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # C. 已到 Warehouse，但尚未全部入庫
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:
                        batch_status = 7
                    else:
                        batch_status = 6


                # -------------------------------------------------
                # D. 此批完成量全部已入庫
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # E. 其它沿用 DB 狀態
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )
                #

                # -------------------------------------------------
                # C. 已完成良品都已入庫
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8

                # -------------------------------------------------
                # D. 尚未完成
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )
                '''
                # 20260815版
                # =================================================
                # material 狀態
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )

                # =================================================
                # 是否仍在 PEnd 等待送出
                #
                # 條件：
                #
                #   process_step_code == 0
                #   completed_qty > 0
                #   isAssembleStationShow = True
                #   isWarehouseStationShow = False
                #
                # 代表：
                #
                #   加工已完成
                #   但尚未按「送出」
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(
                            getattr(
                                a,
                                "process_step_code",
                                -1
                            ),
                            -1
                        ) == 0

                        and

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ) > 0

                        and

                        bool(
                            getattr(
                                a,
                                "isAssembleStationShow",
                                False
                            )
                        )

                        and

                        not bool(
                            getattr(
                                a,
                                "isWarehouseStationShow",
                                False
                            )
                        )
                    )
                    for a in assemble_records
                )

                # =================================================
                # 是否已真正送到 Warehouse
                #
                # isWarehouseStationShow=True
                # 才代表已送離 PEnd、進入成品區。
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )
                    for a in assemble_records
                )

                # =================================================
                # Batch Status 判斷
                #
                # 優先順序：
                #
                # 4 加工作業進行中
                # 5 等待送出
                # 6 等待入庫作業
                # 7 入庫進行中
                # 8 入庫完成
                # =================================================

                # -------------------------------------------------
                # A. 還有真正 active 的加工 Process
                # -------------------------------------------------

                if has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # B. 加工完成，但仍停在 PEnd
                #
                # 尚未送往 Warehouse。
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # C. 已到 Warehouse，但尚未全部入庫
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    # DB 若已明確標示入庫進行中，
                    # 保留 7。
                    if raw_status == 7:

                        batch_status = 7

                    else:

                        batch_status = 6


                # -------------------------------------------------
                # D. 已完成量已全部入庫
                #
                # 注意：
                # 即使 Warehouse flag 因舊資料不完整，
                # 只要真的已有入庫量且已達完成量，
                # 仍可視為入庫完成。
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # E. 其它狀況沿用 DB 狀態
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )


                material_summaries.append({

                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,

                    # 建議一起留下，
                    # 後面 debug / order aggregate 很好用。
                    "has_waiting_send":
                        has_waiting_send,

                    "has_arrived_warehouse":
                        has_arrived_warehouse,

                    # 20260815版 add
                    # ------------------------------------------------
                    # 用來判斷是否只是空 root / template material
                    # ------------------------------------------------

                    "assemble_count":
                        len(
                            assemble_records
                        ),

                    "process_count":
                        len(
                            process_records
                        ),

                    "product_count":
                        1
                        if material_stockin > 0
                        else 0,
                    #
                })
                #
                '''
                material_summaries.append({
                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,
                })
                '''
            # ====================================================
            # 7-2. 整張訂單 status
            #
            # 最未完成的一批決定整單。
            # ====================================================
            '''
            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )
                for item
                in material_summaries
            ]
            '''
            # 20260815版
            # ====================================================
            # 有效批次
            #
            # 同 order_num 可能殘留一筆 root / 空白 material：
            #
            #   沒有 Assemble
            #   沒有 Process
            #   沒有 Product
            #   completed = 0
            #   stockin = 0
            #
            # 如果同訂單已經有其它真正執行過的 material，
            # 這種空 root 不應參與 order_status 判斷。
            #
            # 例如 121200006711：
            #
            # material 7  → 空 root
            # material 13 → 完成/入庫 47
            # material 32 → 完成/入庫 95
            #
            # batch_statuses 應為：
            #
            #   [8, 8]
            #
            # 而不是：
            #
            #   [3, 8, 8]
            # ====================================================

            effective_material_summaries = [
                item
                for item in material_summaries
                if (
                    to_int(
                        item.get(
                            "assemble_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "process_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "product_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    ) > 0

                    or

                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )
                )
            ]


            # ----------------------------------------------------
            # 若同訂單完全沒有任何有效批次，
            # 才 fallback 使用所有 material。
            #
            # 避免一般「尚未開始加工」的新訂單被整張排掉。
            # ----------------------------------------------------

            status_source = (
                effective_material_summaries
                if effective_material_summaries
                else material_summaries
            )


            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )
                for item in status_source
            ]
            #

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )

            # ----------------------------------------------------
            # 入庫量不足於「完成良品量」
            # 不可以顯示入庫完成
            # ----------------------------------------------------

            if (
                total_completed > 0
                and
                total_stockin
                <
                total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:
                    order_status = 7
                else:
                    order_status = 6

            '''
            # ====================================================
            # 所有 material 良品完成量均已入庫
            # ====================================================

            all_batches_stockin_done = bool(
                material_summaries
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0
                    and
                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )
                )
                for item
                in material_summaries
            )

            if all_batches_stockin_done:

                order_status = 8
            '''
            # 20260815版
            # ====================================================
            # 全部 batch 真正完成入庫
            #
            # 除了：
            #
            #   stockin_qty >= completed_qty
            #
            # 還必須確認該 batch 已不在：
            #
            #   status = 4 加工中
            #   status = 5 等待送出
            #
            # 避免舊 P_Product / 殘留入庫資料，
            # 把仍停在 PEnd 的工單誤判為入庫完成。
            # ====================================================

            all_batches_stockin_done = bool(
                material_summaries
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    and

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )

                    and

                    not bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    and

                    to_int(
                        item.get(
                            "status"
                        ),
                        0
                    ) >= 6
                )
                for item in material_summaries
            )

            if all_batches_stockin_done:

                order_status = 8
            #

            # ====================================================
            # 7-3. 單一 material 訂單的資料完整性檢查
            #
            # 多 material / 分批單不能拿 root material_qty
            # 直接與目前批次累計比較。
            # ====================================================

            is_single_material_order = (
                len(
                    group_materials
                )
                == 1
            )

            accounted_total = (
                total_stockin
                +
                total_scrap
            )

            unexplained_difference = 0

            if (
                is_single_material_order
                and
                req_qty > 0
            ):

                unexplained_difference = max(
                    0,
                    req_qty
                    -
                    accounted_total
                )

            # ====================================================
            # 7-4. only unfinished
            #
            # 即使 DB 狀態是 8，
            # 若單一 material 尚有無法解釋的差額，
            # 仍保留在「未完成」查詢，方便查資料問題。
            # ====================================================

            if only_unfinished:

                if (
                    order_status == 8
                    and
                    unexplained_difference == 0
                ):
                    continue

            # ====================================================
            # 7-5. show3 現況備註
            # ====================================================

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                # ------------------------------------------------
                # 單一 material：
                # 可安全與原訂單數量比較
                # ------------------------------------------------

                if (
                    is_single_material_order
                    and
                    req_qty > 0
                ):

                    # 真正有廢品
                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 訂單 {req_qty}"
                        )

                        if unexplained_difference > 0:

                            show3_text += (
                                f"（差異 "
                                f"{unexplained_difference}）"
                            )

                    # 沒有廢品，
                    # 但訂單量與實際資料對不起來
                    elif unexplained_difference > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                            f" / 訂單 {req_qty}"
                            f"（差異 "
                            f"{unexplained_difference}）"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )

                # ------------------------------------------------
                # 多 material / 分批訂單
                #
                # 不與 root material_qty 比較。
                # ------------------------------------------------

                else:

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 已完成 {total_completed}"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )

            # 20260815版
            else:

                # ------------------------------------------------
                # PEnd 等待送出
                # ------------------------------------------------
                if (
                    order_status == 5
                    and
                    total_completed > 0
                ):

                    show3_text = (
                        f"已完成 {total_completed}"
                        f" / 等待送出"
                    )

                # ------------------------------------------------
                # 尚在領料 / 加工階段
                # ------------------------------------------------
                else:

                    show3_text = (
                        current_process_comment
                        or ""
                    )
            #

            # ====================================================
            # 領料中員工
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue

                    m = item[
                        "material"
                    ]

                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )

                    if display_open_emp_id:
                        break

            # ====================================================
            # 現況數量
            #
            # 現況數量 = 良品
            #
            # 廢品不應混進現況良品數。
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )

            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )

            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )

            # ====================================================
            # 回傳
            # ====================================================

            result = {

                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                "req_qty":
                    req_qty,

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative.material_comment
                    ).strip(),

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                "total_process_records":
                    total_process_records,

                # -----------------------------------------------
                # 彙總資料
                # -----------------------------------------------

                "material_count":
                    len(
                        group_materials
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "accounted_total":
                    accounted_total,

                "unexplained_difference":
                    unexplained_difference,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,
            }

            results.append(
                result
            )

        # ========================================================
        # 8. 排序
        # ========================================================

        results.sort(
            key=lambda x: (
                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    == 0
                ),
                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )

        # ========================================================
        # 9. pagination
        # ========================================================

        total = len(
            results
        )

        page_results = results[
            offset:
            offset + limit
        ]

        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(page_results)
        )

        return jsonify({
            "status": True,
            "total": total,
            "informations": page_results,
        })

    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500

    finally:

        s.close()
"""


"""
# ================================================================
# 20260815 最終整合版
# PInformation
#
# 規則：
#
# 1. 同 order_num 多個 P_Material 合併成一筆
#
# 2. 已完成良品量：
#    - 優先使用已真正結束的 P_Process
#    - 同 material 多加工工序不相加，只取最大值
#    - P_Assemble fallback 只允許 process_step_code == 0
#
# 3. 狀態優先順序：
#
#    4 加工作業進行中
#    3 尚有下一道加工工序
#    5 PEnd 等待送出
#    6 Warehouse 等待入庫
#    7 入庫進行中
#    8 入庫完成
#
# 4. 空 root / template material：
#    若同 order_num 已有真正執行批次，
#    沒 Assemble / Process / Product 的 root
#    不參與 batch_statuses。
#
# 5. show3：
#
#    等待加工但已有部分完成：
#      已入庫 142 / 已完成 142 / 訂單 1000（待加工 858）
#
#    等待送出：
#      已完成 100 / 等待送出
#
#    等待入庫：
#      已入庫 0 / 已完成 100
#
#    入庫完成：
#      已入庫 100 / 已完成 100
#
# ================================================================

@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    try:
        limit = int(
            request.args.get(
                "limit",
                20
            )
        )
    except Exception:
        limit = 20

    try:
        offset = int(
            request.args.get(
                "offset",
                0
            )
        )
    except Exception:
        offset = 0

    limit = max(
        1,
        min(
            limit,
            2000
        )
    )

    offset = max(
        0,
        offset
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default

        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default

        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )

        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )

        # ========================================================
        # 狀態
        # ========================================================

        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "等待送出",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }

        def status_text(
            status_code
        ):

            return STATUS_TEXT.get(
                to_int(
                    status_code,
                    -1
                ),
                f"未知狀態({status_code})"
            )

        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"

        # ========================================================
        # 1. P_Part 製程名稱 map
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            code = norm_code(
                p.part_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            part_info_map[
                code
            ] = info

            part_info_map.setdefault(
                alias_code(code),
                info
            )

        # ========================================================
        # 2. P_Assemble 廢品
        # ========================================================

        asm_scrap_rows = (
            s.query(
                P_Assemble.material_id,

                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        asm_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in asm_scrap_rows
        }

        # ========================================================
        # 3. P_Product 入庫量
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in stockin_rows
        }

        # ========================================================
        # 4. P_Product 廢品
        # ========================================================

        product_scrap_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.non_good_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)
            for mid, qty
            in product_scrap_rows
        }

        # ========================================================
        # 5. P_Product count
        #
        # 用來判斷 material 是否只是空 root。
        # ========================================================

        product_count_rows = (
            s.query(
                P_Product.material_id,
                func.count(
                    P_Product.id
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_count_map = {
            to_int(mid, 0):
                to_int(cnt, 0)
            for mid, cnt
            in product_count_rows
        }

        # ========================================================
        # 6. 所有 P_Material
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })

        # ========================================================
        # 7. order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )

        results = []

        # ========================================================
        # 8. 每張訂單
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue

            # ----------------------------------------------------
            # 代表 material
            # ----------------------------------------------------

            representative = sorted(
                group_materials,
                key=lambda m: (
                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]

            req_qty = to_int(
                representative.material_qty,
                0
            )

            total_stockin = 0
            total_completed = 0
            total_scrap = 0
            total_process_records = 0

            material_summaries = []

            # 尚未完成的目前加工工序名稱
            current_process_comment = ""

            # ====================================================
            # 8-1. 每個 material
            # ====================================================

            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )

                # ------------------------------------------------
                # 直接 query DB
                # ------------------------------------------------

                assemble_records = (
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

                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )

                # ------------------------------------------------
                # 入庫
                # ------------------------------------------------

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )

                # ------------------------------------------------
                # 廢品
                # ------------------------------------------------

                assemble_scrap = (
                    asm_scrap_map.get(
                        material_id,
                        0
                    )
                )

                product_scrap = (
                    product_scrap_map.get(
                        material_id,
                        0
                    )
                )

                # 同一批異常可能同時記在兩表
                # 使用 max 避免 double count
                material_scrap = max(
                    assemble_scrap,
                    product_scrap,
                    0,
                )

                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )

                # =================================================
                # Process count
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id

                        and

                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]

                total_process_records += (
                    len(
                        valid_processes
                    )
                )

                # =================================================
                # Process 完成良品量
                #
                # 同 material 多工序不可相加。
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )

                    # 領料 / 搬運不算加工完成
                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    # 必須真的開始
                    if not safe_str(
                        p.begin_time
                    ).strip():
                        continue

                    # 必須真的結束
                    if not safe_str(
                        p.end_time
                    ).strip():
                        continue

                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )

                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )

                # =================================================
                # P_Assemble fallback
                #
                # 只有 process_step_code == 0
                # 才當成真正已完成列。
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    if assemble_step != 0:
                        continue

                    row_completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )

                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )

                # =================================================
                # material 已完成良品量
                # =================================================

                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )

                total_completed += (
                    material_completed
                )

                # =================================================
                # Active Process
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )

                    if process_type in {
                        1,
                        5,
                        6,
                    }:
                        continue

                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )

                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )

                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = True
                        break

                # =================================================
                # 20260815
                # 是否仍存在下一道未完成加工工序
                #
                # 這是 121200006714 的核心修正。
                #
                # 例如：
                #
                # B107-01 已完成
                # B108-12 step=19 尚未完成
                #
                # 此時不能：
                #
                #   raw_status=5
                #   → 等待送出
                #
                # 而必須：
                #
                #   → 等待加工作業
                # =================================================

                pending_assemble_rows = []

                for a in assemble_records:

                    step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    if step <= 0:
                        continue

                    # 20260815版 add
                    # -------------------------------------------------
                    # 排除已完成工序衍生出的歷史 / 分量複製列
                    #
                    # 這類 row：
                    #
                    #   is_copied_from_id != NULL
                    #   show2_ok = 0
                    #
                    # 不代表目前真正的下一道加工工序。
                    #
                    # 例如 121200006711：
                    #
                    #   assemble 30 / step 59 / copied_from 13
                    #   assemble 46 / step 59 / copied_from 35
                    #
                    # 不可把它們判成等待加工。
                    # -------------------------------------------------

                    if (
                        getattr(
                            a,
                            "is_copied_from_id",
                            None
                        ) is not None

                        and

                        to_int(
                            getattr(
                                a,
                                "show2_ok",
                                0
                            ),
                            0
                        ) == 0
                    ):
                        continue
                    #

                    # 已送 Warehouse 的列不可能是下一加工工序
                    if bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    ):
                        continue

                    must_end_qty = to_int(
                        getattr(
                            a,
                            "must_receive_end_qty",
                            0
                        ),
                        0
                    )

                    if must_end_qty <= 0:

                        must_end_qty = to_int(
                            getattr(
                                a,
                                "must_receive_qty",
                                0
                            ),
                            0
                        )

                    completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )

                    # must_end_qty 有效時，
                    # 完成量已達需求則不算 pending
                    if (
                        must_end_qty > 0
                        and
                        completed_qty
                        >=
                        must_end_qty
                    ):
                        continue

                    pending_assemble_rows.append(
                        a
                    )

                has_pending_process_step = bool(
                    pending_assemble_rows
                )

                # =================================================
                # 找「真正下一道」製程名稱
                # =================================================

                if (
                    not current_process_comment
                    and
                    pending_assemble_rows
                ):

                    min_assemble = min(
                        pending_assemble_rows,
                        key=lambda a:
                            to_int(
                                getattr(
                                    a,
                                    "seq_num",
                                    999999
                                ),
                                999999
                            )
                    )

                    work_num = safe_str(
                        min_assemble.work_num
                    ).strip()

                    key = norm_code(
                        work_num
                    )

                    part_info = (
                        part_info_map.get(
                            key
                        )
                        or
                        part_info_map.get(
                            alias_code(
                                key
                            )
                        )
                    )

                    if part_info:

                        current_process_comment = (
                            safe_str(
                                part_info.get(
                                    "comment"
                                )
                            ).strip()
                        )

                    else:

                        current_process_comment = (
                            work_num
                        )

                # =================================================
                # Material status
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )

                # =================================================
                # 是否正在 PEnd 等待送出
                #
                # 必須是真的：
                #
                # step=0
                # completed>0
                # isAssembleStationShow=True
                # isWarehouseStationShow=False
                #
                # 不能只看 raw_status=5。
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(
                            getattr(
                                a,
                                "process_step_code",
                                -1
                            ),
                            -1
                        ) == 0

                        and

                        max(
                            to_int(
                                getattr(
                                    a,
                                    "completed_qty",
                                    0
                                ),
                                0
                            ),
                            to_int(
                                getattr(
                                    a,
                                    "total_completed_qty",
                                    0
                                ),
                                0
                            ),
                        ) > 0

                        and

                        bool(
                            getattr(
                                a,
                                "isAssembleStationShow",
                                False
                            )
                        )

                        and

                        not bool(
                            getattr(
                                a,
                                "isWarehouseStationShow",
                                False
                            )
                        )
                    )
                    for a
                    in assemble_records
                )

                # =================================================
                # 是否已真正到 Warehouse
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )
                    for a
                    in assemble_records
                )

                # =================================================
                # Batch Status
                #
                # 優先順序非常重要：
                #
                # 4 active
                # 3 下一加工工序
                # 5 PEnd 待送出
                # 6/7 Warehouse
                # 8 入庫完成
                # =================================================

                # -------------------------------------------------
                # A. 正在加工
                # -------------------------------------------------

                if has_active_process:

                    batch_status = 4

                # -------------------------------------------------
                # B. 還有下一道工序
                #
                # 一定要放在 has_waiting_send 前面。
                # -------------------------------------------------

                elif has_pending_process_step:

                    batch_status = 3

                # -------------------------------------------------
                # C. 所有加工完成，真正 PEnd 待送出
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5

                # -------------------------------------------------
                # D. 已到 Warehouse，尚未全部入庫
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:
                        batch_status = 7
                    else:
                        batch_status = 6

                # -------------------------------------------------
                # E. 已完成良品全部入庫
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8

                # -------------------------------------------------
                # F. 其它才 fallback DB raw_status
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )

                # =================================================
                # Material summary
                # =================================================

                material_summaries.append({

                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,

                    "has_pending_process_step":
                        has_pending_process_step,

                    "has_waiting_send":
                        has_waiting_send,

                    "has_arrived_warehouse":
                        has_arrived_warehouse,

                    # ---------------------------------------------
                    # 用來辨識空 root / template
                    # ---------------------------------------------

                    "assemble_count":
                        len(
                            assemble_records
                        ),

                    "process_count":
                        len(
                            process_records
                        ),

                    "product_count":
                        product_count_map.get(
                            material_id,
                            0
                        ),
                })

            # ====================================================
            # 8-2. 排除空 root / template material
            #
            # 例如：
            #
            # 121200006711
            #
            # material 7:
            # assemble=0
            # process=0
            # product=0
            #
            # material 13 / 32：
            # 有真正加工與入庫
            #
            # 所以 material 7 不應用 show2_ok=3
            # 把整張 order 拉回 3。
            # ====================================================

            effective_material_summaries = [
                item
                for item
                in material_summaries
                if (
                    to_int(
                        item.get(
                            "assemble_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "process_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "product_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    ) > 0

                    or

                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_arrived_warehouse",
                            False
                        )
                    )
                )
            ]

            # 若完全沒有有效批次，
            # 才使用所有 material。
            status_source = (
                effective_material_summaries
                if effective_material_summaries
                else material_summaries
            )

            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )
                for item
                in status_source
            ]

            # ====================================================
            # 8-3. 整張 order 狀態
            # ====================================================

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )

            # ----------------------------------------------------
            # 若任一有效 batch 還有下一道加工，
            # 整張 order 不可顯示等待送出 / 入庫。
            #
            # 這可再次保護 121200006714。
            # ----------------------------------------------------

            if any(
                bool(
                    item.get(
                        "has_pending_process_step",
                        False
                    )
                )
                for item
                in status_source
            ):

                if not any(
                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )
                    for item
                    in status_source
                ):

                    order_status = min(
                        order_status,
                        3
                    )

            # ----------------------------------------------------
            # 入庫量不足完成量，
            # 不能顯示入庫完成。
            # ----------------------------------------------------

            if (
                total_completed > 0
                and
                total_stockin
                <
                total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:
                    order_status = 7
                else:
                    order_status = 6

            # ====================================================
            # 全部「有效 batch」真正完成入庫
            #
            # 注意：
            # 此處使用 status_source，
            # 不使用 material_summaries，
            # 避免空 root 破壞判斷。
            # ====================================================

            all_batches_stockin_done = bool(
                status_source
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    and

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )

                    and

                    not bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    and

                    to_int(
                        item.get(
                            "status"
                        ),
                        0
                    ) >= 6
                )
                for item
                in status_source
            )

            if all_batches_stockin_done:

                order_status = 8
            '''
            # ====================================================
            # 8-4. 空 root + 尚未達訂單需求量
            #
            # 例如 121200006711：
            #
            # root material 7 是空資料
            #
            # 有效批次：
            # 47 + 95 = 142
            #
            # 訂單 = 1000
            #
            # 即使 13 / 32 都已入庫，
            # 整張 order 仍不能叫「入庫完成」。
            #
            # 注意：
            # 只在確實有「被排除的空 root」時啟用，
            # 避免干擾一般多 material 分批單。
            # ====================================================

            has_excluded_empty_root = (
                len(
                    status_source
                )
                <
                len(
                    material_summaries
                )
            )

            accounted_completed_qty = (
                total_completed
                +
                total_scrap
            )

            if (
                has_excluded_empty_root
                and
                req_qty > 0
                and
                accounted_completed_qty
                <
                req_qty
                and
                order_status == 8
            ):

                order_status = 3
            '''
            # ====================================================
            # 8-5. 單一 material 資料完整性
            # ====================================================

            is_single_material_order = (
                len(
                    group_materials
                )
                == 1
            )

            accounted_total = (
                total_stockin
                +
                total_scrap
            )

            unexplained_difference = 0

            if (
                is_single_material_order
                and
                req_qty > 0
            ):

                unexplained_difference = max(
                    0,
                    req_qty
                    -
                    accounted_total
                )

            # ====================================================
            # 8-6. only unfinished
            # ====================================================
            # 20260816版remove
            '''
            if only_unfinished:

                if (
                    order_status == 8
                    and
                    unexplained_difference == 0
                ):
                    continue
            '''
            # ====================================================
            # 8-7. show3 現況備註
            # ====================================================

            # ----------------------------------------------------
            # Warehouse / 入庫階段
            # ----------------------------------------------------

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                # -----------------------------------------------
                # 單一 material
                # -----------------------------------------------

                if (
                    is_single_material_order
                    and
                    req_qty > 0
                ):

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 訂單 {req_qty}"
                        )

                        if unexplained_difference > 0:

                            show3_text += (
                                f"（差異 "
                                f"{unexplained_difference}）"
                            )

                    elif unexplained_difference > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                            f" / 訂單 {req_qty}"
                            f"（差異 "
                            f"{unexplained_difference}）"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )

                # -----------------------------------------------
                # 多 material / 分批
                # -----------------------------------------------

                else:

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 已完成 {total_completed}"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )

            # ----------------------------------------------------
            # PEnd 等待送出
            # ----------------------------------------------------

            elif (
                order_status == 5
                and
                total_completed > 0
            ):

                show3_text = (
                    f"已完成 {total_completed}"
                    f" / 等待送出"
                )

            # ----------------------------------------------------
            # 尚在加工階段，
            # 但同 order 已有部分完成/入庫
            #
            # 例如 121200006711：
            #
            # 已入庫 142
            # 已完成 142
            # 訂單 1000
            # 待加工 858
            # ----------------------------------------------------

            elif (
                order_status <= 4
                and
                total_completed > 0
                and
                req_qty > 0
            ):

                remaining_qty = max(
                    0,
                    req_qty
                    -
                    total_completed
                    -
                    total_scrap
                )

                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / 已完成 {total_completed}"
                    f" / 訂單 {req_qty}"
                )

                if total_scrap > 0:

                    show3_text += (
                        f" / 廢品 {total_scrap}"
                    )

                if remaining_qty > 0:

                    show3_text += (
                        f"（待加工 "
                        f"{remaining_qty}）"
                    )

            # ----------------------------------------------------
            # 一般等待加工 / 加工中
            # ----------------------------------------------------

            else:

                show3_text = (
                    current_process_comment
                    or ""
                )

            # ====================================================
            # 8-8. 領料中員工
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue

                    m = item[
                        "material"
                    ]

                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )

                    if display_open_emp_id:
                        break

            # ====================================================
            # 8-9. 現況數量
            #
            # 現況數量只顯示良品，
            # 不把廢品混進去。
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )

            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )

            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )

            # ====================================================
            # 8-10. 回傳
            # ====================================================

            result = {

                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                "req_qty":
                    req_qty,

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative.material_comment
                    ).strip(),

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                "total_process_records":
                    total_process_records,

                # -----------------------------------------------
                # 彙總資訊
                # -----------------------------------------------

                "material_count":
                    len(
                        group_materials
                    ),

                "effective_material_count":
                    len(
                        status_source
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "accounted_total":
                    accounted_total,

                "unexplained_difference":
                    unexplained_difference,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "remaining_process_qty":
                    max(
                        0,
                        req_qty
                        -
                        total_completed
                        -
                        total_scrap
                    )
                    if req_qty > 0
                    else 0,

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,

                "has_pending_process_step":
                    any(
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),

                "has_waiting_send":
                    any(
                        bool(
                            item.get(
                                "has_waiting_send",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),
            }

            results.append(
                result
            )

        # ========================================================
        # 9. 排序
        # ========================================================

        results.sort(
            key=lambda x: (
                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    == 0
                ),

                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )

        '''
        # ========================================================
        # 10. pagination
        # ========================================================

        total = len(
            results
        )

        page_results = results[
            offset:
            offset + limit
        ]
        '''
        # 20260816版
        # ========================================================
        # 10. pagination
        #
        # 20260816：
        # PInformation 前端目前沒有完整配合 server-side
        # pagination，先全部回傳，避免新訂單因 limit=20 消失。
        # ========================================================

        total = len(
            results
        )

        page_results = results
        #

        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(
                page_results
            )
        )

        return jsonify({
            "status": True,
            "total": total,
            "informations": page_results,
        })

    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500

    finally:

        s.close()
"""


# 20260817版
"""
@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default


        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default


        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )


        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )


        # ========================================================
        # 狀態
        # ========================================================

        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "等待送出",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }


        def status_text(
            status_code
        ):

            return STATUS_TEXT.get(
                to_int(
                    status_code,
                    -1
                ),
                f"未知狀態({status_code})"
            )


        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"


        # ========================================================
        # 1. P_Part 製程名稱
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            code = norm_code(
                p.part_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            part_info_map[
                code
            ] = info

            part_info_map.setdefault(
                alias_code(
                    code
                ),
                info
            )


        # ========================================================
        # 2. P_Assemble 廢品
        # ========================================================

        asm_scrap_rows = (
            s.query(
                P_Assemble.material_id,

                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        asm_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in asm_scrap_rows
        }


        # ========================================================
        # 3. P_Product 入庫量
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in stockin_rows
        }


        # ========================================================
        # 4. P_Product 廢品
        # ========================================================

        product_scrap_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.non_good_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in product_scrap_rows
        }


        # ========================================================
        # 5. P_Product count
        #
        # 判斷空 root / template 用
        # ========================================================

        product_count_rows = (
            s.query(
                P_Product.material_id,

                func.count(
                    P_Product.id
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_count_map = {
            to_int(mid, 0):
                to_int(cnt, 0)

            for mid, cnt
            in product_count_rows
        }


        # ========================================================
        # 6. 所有 P_Material
        #
        # 不做 pagination
        # 不在 material level 過濾完成單
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })


        # ========================================================
        # 7. order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )


        results = []


        # ========================================================
        # 8. 每張訂單
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue


            # ----------------------------------------------------
            # 代表 material
            # ----------------------------------------------------

            representative = sorted(
                group_materials,
                key=lambda m: (

                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]


            req_qty = to_int(
                representative.material_qty,
                0
            )


            total_stockin = 0
            total_completed = 0
            total_scrap = 0
            total_process_records = 0

            material_summaries = []

            current_process_comment = ""


            # ====================================================
            # 8-1. 每個 material
            # ====================================================

            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )


                # ------------------------------------------------
                # DB 真實資料
                # ------------------------------------------------

                assemble_records = (
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


                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )


                # =================================================
                # 入庫
                # =================================================

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )


                # =================================================
                # 廢品
                # =================================================

                assemble_scrap = (
                    asm_scrap_map.get(
                        material_id,
                        0
                    )
                )

                product_scrap = (
                    product_scrap_map.get(
                        material_id,
                        0
                    )
                )

                # 同一異常可能寫入兩表
                # 避免 double count
                material_scrap = max(
                    assemble_scrap,
                    product_scrap,
                    0,
                )

                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )


                # =================================================
                # Information 詳情按鈕
                #
                # 仍維持：
                #
                # 必須真的有 P_Process.begin_time
                #
                # 999900... 測試單沒有 Process，
                # 詳情按鈕維持 disabled。
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id

                        and

                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]

                total_process_records += (
                    len(
                        valid_processes
                    )
                )


                # =================================================
                # Process 完成良品量
                #
                # 同一 material 多工序：
                #
                # 不 sum
                # 取最大值
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )

                    # ---------------------------------------------
                    # 領料 / 搬運不算加工完成量
                    # ---------------------------------------------

                    if process_type in {
                        1,
                        2,
                        3,
                        5,
                        6,
                        19,
                        29,
                        31,
                    }:
                        continue


                    # 必須真正開始
                    if not safe_str(
                        p.begin_time
                    ).strip():
                        continue


                    # 必須真正結束
                    if not safe_str(
                        p.end_time
                    ).strip():
                        continue


                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )


                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )


                # =================================================
                # Assemble fallback
                #
                # 只有 step == 0 才算真正完成
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    if assemble_step != 0:
                        continue


                    row_completed_qty = max(
                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )


                # =================================================
                # material 真正完成良品量
                # =================================================

                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )

                total_completed += (
                    material_completed
                )


                # =================================================
                # 是否有正在加工的 Process
                #
                # 只認真正加工製程。
                #
                # 搬運 / 領料 / 入庫不算「加工中」。
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )

                    if process_type in {
                        1,
                        2,
                        3,
                        5,
                        6,
                        19,
                        29,
                        31,
                    }:
                        continue


                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )

                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )


                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = True
                        break


                # =================================================
                # 尚有真正未完成加工工序
                # =================================================

                pending_assemble_rows = []

                for a in assemble_records:

                    step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )

                    if step <= 0:
                        continue


                    # ---------------------------------------------
                    # 排除歷史 / 分量複製列
                    #
                    # 121200006711：
                    #
                    # copied_from != NULL
                    # show2_ok = 0
                    #
                    # 不應視為下一加工工序
                    # ---------------------------------------------

                    if (
                        getattr(
                            a,
                            "is_copied_from_id",
                            None
                        ) is not None

                        and

                        to_int(
                            getattr(
                                a,
                                "show2_ok",
                                0
                            ),
                            0
                        ) == 0
                    ):
                        continue


                    # 已送 Warehouse
                    if bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    ):
                        continue


                    must_end_qty = to_int(
                        getattr(
                            a,
                            "must_receive_end_qty",
                            0
                        ),
                        0
                    )

                    if must_end_qty <= 0:

                        must_end_qty = to_int(
                            getattr(
                                a,
                                "must_receive_qty",
                                0
                            ),
                            0
                        )


                    completed_qty = max(

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    if (
                        must_end_qty > 0
                        and
                        completed_qty
                        >=
                        must_end_qty
                    ):
                        continue


                    pending_assemble_rows.append(
                        a
                    )


                has_pending_process_step = bool(
                    pending_assemble_rows
                )


                # =================================================
                # 找真正下一道工序名稱
                # =================================================

                if (
                    not current_process_comment
                    and
                    pending_assemble_rows
                ):

                    min_assemble = min(
                        pending_assemble_rows,
                        key=lambda a:
                            to_int(
                                getattr(
                                    a,
                                    "seq_num",
                                    999999
                                ),
                                999999
                            )
                    )


                    work_num = safe_str(
                        min_assemble.work_num
                    ).strip()


                    key = norm_code(
                        work_num
                    )


                    part_info = (
                        part_info_map.get(
                            key
                        )
                        or
                        part_info_map.get(
                            alias_code(
                                key
                            )
                        )
                    )


                    if part_info:

                        current_process_comment = (
                            safe_str(
                                part_info.get(
                                    "comment"
                                )
                            ).strip()
                        )

                    else:

                        current_process_comment = (
                            work_num
                        )


                # =================================================
                # Material 原始 status
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )


                # =================================================
                # 20260817
                #
                # 是否真的已經離開領料區
                #
                # 重要：
                #
                # P_Assemble 可以預先建立。
                #
                # 所以：
                #
                #   有 P_Assemble
                #
                # 不代表：
                #
                #   已經到了加工站
                #
                # =================================================

                '''
                # -------------------------------------------------
                # 領料 Process 完成
                #
                # process_type = 1
                # -------------------------------------------------

                has_prepare_done = any(
                    (
                        to_int(
                            getattr(
                                p,
                                "process_type",
                                0
                            ),
                            0
                        ) == 1

                        and

                        bool(
                            safe_str(
                                getattr(
                                    p,
                                    "end_time",
                                    ""
                                )
                            ).strip()
                        )
                    )
                    for p
                    in process_records
                )


                # -------------------------------------------------
                # 領料區 -> 加工區 搬運完成
                #
                # 2 = AGV
                # 5 = 堆高機
                # -------------------------------------------------

                has_prepare_to_process_move = any(
                    (
                        to_int(
                            getattr(
                                p,
                                "process_type",
                                0
                            ),
                            0
                        ) in {
                            2,
                            5,
                        }

                        and

                        bool(
                            safe_str(
                                getattr(
                                    p,
                                    "end_time",
                                    ""
                                )
                            ).strip()
                        )
                    )
                    for p
                    in process_records
                )


                # -------------------------------------------------
                # 是否已經真正有加工 Process
                #
                # 某些舊資料可能缺搬運 Process，
                # 但加工已真正開始/完成。
                #
                # 這種不能硬拉回領料站。
                # -------------------------------------------------

                has_any_real_processing = any(
                    (
                        to_int(
                            getattr(
                                p,
                                "process_type",
                                0
                            ),
                            0
                        )
                        not in {
                            1,
                            2,
                            3,
                            5,
                            6,
                            19,
                            29,
                            31,
                        }

                        and

                        bool(
                            safe_str(
                                getattr(
                                    p,
                                    "begin_time",
                                    ""
                                )
                            ).strip()
                        )
                    )
                    for p
                    in process_records
                )


                # -------------------------------------------------
                # 是否仍停留在領料階段
                #
                # 必須同時：
                #
                # 1. 沒完成領料區->加工區搬運
                # 2. 沒有任何真正加工 Process
                #
                # has_prepare_done 本身不代表已到加工區。
                # -------------------------------------------------

                is_still_prepare_stage = (
                    not has_prepare_to_process_move
                    and
                    not has_any_real_processing
                )
                '''

                #
                # =================================================
                # 20260817 修正版
                # 是否已具備 PBegin 加工作業資格
                #
                # 重要：
                #
                # 加工線有兩種流程：
                #
                # 1. 正常領料
                #    領料 → 送出 → PBegin
                #
                # 2. 不領料
                #    系統直接 enable 送出 → PBegin
                #
                # 所以不能要求一定存在：
                #
                #   P_Process type=1 / 2 / 5
                #
                # 才認定已到加工區。
                #
                # 應與 PBegin 的 Material 狀態一致。
                # =================================================

                material_is_take_ok = bool(
                    getattr(
                        material,
                        "isTakeOk",
                        False
                    )
                )

                material_is_show = bool(
                    getattr(
                        material,
                        "isShow",
                        False
                    )
                )

                material_show1 = to_int(
                    getattr(
                        material,
                        "show1_ok",
                        0
                    ),
                    0
                )

                # -------------------------------------------------
                # 已經具備進 PBegin 的資格
                #
                # show1_ok = 2
                # isTakeOk = True
                # isShow   = True
                # show2_ok >= 3
                #
                # 例如：
                #
                # 999900006241
                # 999900006728
                # 999900006747
                #
                # 已在 PBegin 顯示，
                # 所以 PInformation 應維持：
                #
                #   等待加工作業
                # -------------------------------------------------

                has_entered_process_stage = (
                    material_is_take_ok
                    and
                    material_is_show
                    and
                    material_show1 == 2
                    and
                    raw_status >= 3
                )

                # -------------------------------------------------
                # 尚未進入加工階段
                # -------------------------------------------------

                is_still_prepare_stage = (
                    not has_entered_process_stage
                )
                #

                # =================================================
                # PEnd 等待送出
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(
                            getattr(
                                a,
                                "process_step_code",
                                -1
                            ),
                            -1
                        ) == 0

                        and

                        max(
                            to_int(
                                getattr(
                                    a,
                                    "completed_qty",
                                    0
                                ),
                                0
                            ),

                            to_int(
                                getattr(
                                    a,
                                    "total_completed_qty",
                                    0
                                ),
                                0
                            ),
                        ) > 0

                        and

                        bool(
                            getattr(
                                a,
                                "isAssembleStationShow",
                                False
                            )
                        )

                        and

                        not bool(
                            getattr(
                                a,
                                "isWarehouseStationShow",
                                False
                            )
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # 已真正到 Warehouse
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # Batch Status
                #
                # 優先順序：
                #
                # 領料
                # ↓
                # 加工 active
                # ↓
                # 下一道加工
                # ↓
                # PEnd
                # ↓
                # Warehouse
                # ↓
                # 入庫
                # =================================================

                '''
                # -------------------------------------------------
                # A. 尚未真正離開領料區
                # -------------------------------------------------

                if is_still_prepare_stage:

                    # raw 0
                    if raw_status <= 0:

                        batch_status = 0


                    # raw 1
                    elif raw_status == 1:

                        batch_status = 1


                    # 已有領料完成證據
                    elif has_prepare_done:

                        batch_status = 2


                    # -------------------------------------------------
                    # 像 999900006728：
                    #
                    # DB raw_status 雖然錯誤為 3，
                    # 又已先產生 P_Assemble，
                    #
                    # 但：
                    #
                    # 沒搬運到加工區
                    # 沒真正加工 Process
                    #
                    # 所以最多是「領料已完成」。
                    # -------------------------------------------------

                    else:

                        batch_status = 2


                # -------------------------------------------------
                # B. 真正正在加工
                # -------------------------------------------------

                elif has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # C. 有下一道加工
                # -------------------------------------------------

                elif has_pending_process_step:

                    batch_status = 3
                '''
                #
                # -------------------------------------------------
                # A. 尚未進入 PBegin
                # -------------------------------------------------

                if is_still_prepare_stage:

                    if raw_status <= 0:

                        batch_status = 0

                    elif raw_status == 1:

                        batch_status = 1

                    else:

                        batch_status = 2


                # -------------------------------------------------
                # B. 已有真正 active 加工
                # -------------------------------------------------

                elif has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # C. 已具備 PBegin 資格，等待加工
                #
                # 這裡特別保護：
                #
                # raw_status = 3
                #
                # 即使沒有 P_Process，
                # 只要 material 狀態已經允許進 PBegin，
                # 就是「等待加工作業」。
                # -------------------------------------------------

                elif (
                    has_entered_process_stage
                    and
                    raw_status == 3
                ):

                    batch_status = 3


                # -------------------------------------------------
                # D. 還有真正下一道加工
                # -------------------------------------------------

                elif has_pending_process_step:

                    batch_status = 3


                # -------------------------------------------------
                # E. PEnd 真正等待送出
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # F. Warehouse
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:

                        batch_status = 7

                    else:

                        batch_status = 6


                # -------------------------------------------------
                # G. 已全部入庫
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # H. fallback
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )
                #

                '''
                # -------------------------------------------------
                # D. PEnd 真正等待送出
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # E. Warehouse
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:

                        batch_status = 7

                    else:

                        batch_status = 6


                # -------------------------------------------------
                # F. 已全部入庫
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # G. fallback
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )
                '''

                # =================================================
                # summary
                # =================================================

                material_summaries.append({

                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,

                    "has_pending_process_step":
                        has_pending_process_step,

                    "has_waiting_send":
                        has_waiting_send,

                    "has_arrived_warehouse":
                        has_arrived_warehouse,

                    # 20260817
                    "is_still_prepare_stage":
                        is_still_prepare_stage,

                    "has_prepare_done":
                        has_prepare_done,

                    "has_prepare_to_process_move":
                        has_prepare_to_process_move,

                    "assemble_count":
                        len(
                            assemble_records
                        ),

                    "process_count":
                        len(
                            process_records
                        ),

                    "product_count":
                        product_count_map.get(
                            material_id,
                            0
                        ),
                })


            # ====================================================
            # 8-2. 排除空 root
            # ====================================================

            effective_material_summaries = [
                item
                for item
                in material_summaries

                if (
                    to_int(
                        item.get(
                            "assemble_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "process_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "product_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    ) > 0

                    or

                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_arrived_warehouse",
                            False
                        )
                    )
                )
            ]


            status_source = (
                effective_material_summaries
                if effective_material_summaries
                else material_summaries
            )


            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )

                for item
                in status_source
            ]


            # ====================================================
            # 8-3. 整單狀態
            # ====================================================

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )


            # ----------------------------------------------------
            # 只要還有領料階段 batch，
            # 整張 order 不可被 pending P_Assemble 拉成 3。
            # ----------------------------------------------------

            if any(
                bool(
                    item.get(
                        "is_still_prepare_stage",
                        False
                    )
                )
                for item
                in status_source
            ):

                prepare_statuses = [
                    to_int(
                        item.get(
                            "status"
                        ),
                        2
                    )

                    for item
                    in status_source

                    if bool(
                        item.get(
                            "is_still_prepare_stage",
                            False
                        )
                    )
                ]

                if prepare_statuses:

                    order_status = min(
                        order_status,
                        min(
                            prepare_statuses
                        )
                    )


            # ----------------------------------------------------
            # 真正有下一道加工
            #
            # 但必須不是領料階段。
            # ----------------------------------------------------

            if any(
                (
                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "is_still_prepare_stage",
                            False
                        )
                    )
                )

                for item
                in status_source
            ):

                if not any(
                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    for item
                    in status_source
                ):

                    order_status = min(
                        order_status,
                        3
                    )


            # ====================================================
            # 入庫安全判斷
            # ====================================================

            if (
                total_completed > 0
                and
                total_stockin
                <
                total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:

                    order_status = 7

                else:

                    order_status = 6


            # ====================================================
            # 全部有效 batch 都已入庫
            # ====================================================

            all_batches_stockin_done = bool(
                status_source
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    and

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )

                    and

                    not bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    and

                    not (
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )
                        and
                        not bool(
                            item.get(
                                "is_still_prepare_stage",
                                False
                            )
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    and

                    to_int(
                        item.get(
                            "status"
                        ),
                        0
                    ) >= 6
                )

                for item
                in status_source
            )


            if all_batches_stockin_done:

                order_status = 8


            # ====================================================
            # 單一 material 差異
            # ====================================================

            is_single_material_order = (
                len(
                    group_materials
                )
                ==
                1
            )


            accounted_total = (
                total_stockin
                +
                total_scrap
            )


            unexplained_difference = 0

            if (
                is_single_material_order
                and
                req_qty > 0
            ):

                unexplained_difference = max(
                    0,
                    req_qty
                    -
                    accounted_total
                )


            # ====================================================
            # 目前 PInformation 全部顯示
            #
            # 不再因 only_unfinished 移除 status=8
            # ====================================================

            # if (
            #     only_unfinished
            #     and
            #     order_status == 8
            # ):
            #     continue


            # ====================================================
            # 8-7. show3
            # ====================================================


            # ----------------------------------------------------
            # Warehouse / 入庫
            # ----------------------------------------------------

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                if (
                    is_single_material_order
                    and
                    req_qty > 0
                ):

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 訂單 {req_qty}"
                        )

                        if unexplained_difference > 0:

                            show3_text += (
                                f"（差異 "
                                f"{unexplained_difference}）"
                            )


                    elif unexplained_difference > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                            f" / 訂單 {req_qty}"
                            f"（差異 "
                            f"{unexplained_difference}）"
                        )


                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


                else:

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 已完成 {total_completed}"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


            # ----------------------------------------------------
            # PEnd 等待送出
            # ----------------------------------------------------

            elif (
                order_status == 5
                and
                total_completed > 0
            ):

                show3_text = (
                    f"已完成 {total_completed}"
                    f" / 等待送出"
                )


            # ----------------------------------------------------
            # 領料階段
            #
            # 20260817：
            #
            # 不提前顯示加工名稱。
            # ----------------------------------------------------

            elif order_status <= 2:

                show3_text = ""


            # ----------------------------------------------------
            # 加工階段已有部分完成
            # ----------------------------------------------------

            elif (
                order_status <= 4
                and
                total_completed > 0
                and
                req_qty > 0
            ):

                remaining_qty = max(
                    0,
                    req_qty
                    -
                    total_completed
                    -
                    total_scrap
                )


                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / 已完成 {total_completed}"
                    f" / 訂單 {req_qty}"
                )


                if total_scrap > 0:

                    show3_text += (
                        f" / 廢品 {total_scrap}"
                    )


                if remaining_qty > 0:

                    show3_text += (
                        f"（待加工 "
                        f"{remaining_qty}）"
                    )


            # ----------------------------------------------------
            # 一般等待加工 / 加工中
            # ----------------------------------------------------

            else:

                show3_text = (
                    current_process_comment
                    or ""
                )


            # ====================================================
            # 領料中人員
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue


                    m = item[
                        "material"
                    ]


                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )


                    if display_open_emp_id:
                        break


            # ====================================================
            # 現況數量
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )


            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )


            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )


            # ====================================================
            # 回傳
            # ====================================================

            result = {

                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )

                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )

                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                "req_qty":
                    req_qty,

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative.material_comment
                    ).strip(),

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                "total_process_records":
                    total_process_records,

                "material_count":
                    len(
                        group_materials
                    ),

                "effective_material_count":
                    len(
                        status_source
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )

                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "accounted_total":
                    accounted_total,

                "unexplained_difference":
                    unexplained_difference,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "remaining_process_qty":
                    max(
                        0,
                        req_qty
                        -
                        total_completed
                        -
                        total_scrap
                    )
                    if req_qty > 0
                    else 0,

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,

                "has_pending_process_step":
                    any(
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )

                        for item
                        in status_source
                    ),

                "has_waiting_send":
                    any(
                        bool(
                            item.get(
                                "has_waiting_send",
                                False
                            )
                        )

                        for item
                        in status_source
                    ),

                # 20260817 debug / 前端日後可用
                "is_still_prepare_stage":
                    any(
                        bool(
                            item.get(
                                "is_still_prepare_stage",
                                False
                            )
                        )

                        for item
                        in status_source
                    ),
            }


            results.append(
                result
            )


        # ========================================================
        # 9. 排序
        # ========================================================

        results.sort(
            key=lambda x: (

                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    ==
                    0
                ),

                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )


        # ========================================================
        # 10. 不限制筆數
        #
        # 20260816：
        #
        # 不再：
        #
        # results[offset:offset + limit]
        #
        # 直接全部回傳。
        # ========================================================

        total = len(
            results
        )

        page_results = (
            results
        )


        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(
                page_results
            )
        )


        return jsonify({
            "status": True,
            "total": total,
            "informations": page_results,
        })


    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500


    finally:

        s.close()
"""


"""
# 20260817 clean version
@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default


        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default


        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )


        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )


        # ========================================================
        # 狀態
        # ========================================================

        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "等待送出",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }


        def status_text(
            status_code
        ):

            return STATUS_TEXT.get(
                to_int(
                    status_code,
                    -1
                ),
                f"未知狀態({status_code})"
            )


        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"


        # ========================================================
        # 1. P_Part 製程名稱
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            code = norm_code(
                p.part_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            part_info_map[
                code
            ] = info

            part_info_map.setdefault(
                alias_code(
                    code
                ),
                info
            )


        # ========================================================
        # 2. P_Assemble 廢品
        # ========================================================

        asm_scrap_rows = (
            s.query(
                P_Assemble.material_id,

                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        asm_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in asm_scrap_rows
        }


        # ========================================================
        # 3. P_Product 入庫量
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in stockin_rows
        }


        # ========================================================
        # 4. P_Product 廢品
        # ========================================================

        product_scrap_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.non_good_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in product_scrap_rows
        }


        # ========================================================
        # 5. P_Product count
        # ========================================================

        product_count_rows = (
            s.query(
                P_Product.material_id,

                func.count(
                    P_Product.id
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_count_map = {
            to_int(mid, 0):
                to_int(cnt, 0)

            for mid, cnt
            in product_count_rows
        }


        # ========================================================
        # 6. 所有 P_Material
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })


        # ========================================================
        # 7. order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )


        results = []


        # ========================================================
        # 8. 每張訂單
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue


            representative = sorted(
                group_materials,
                key=lambda m: (

                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]


            req_qty = to_int(
                representative.material_qty,
                0
            )


            total_stockin = 0
            total_completed = 0

            # 廠內加工產生的廢品
            total_scrap = 0

            # 外部加工送進廠內前已存在的廢料
            total_external_scrap = 0

            total_process_records = 0

            material_summaries = []

            current_process_comment = ""


            # ====================================================
            # 8-1. 每個 material
            # ====================================================

            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )


                assemble_records = (
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

                '''
                # =================================================
                # 外部加工既有廢料
                #
                # 適用：
                #   不領料 / 外部加工後直接送廠內加工
                #
                # Excel：
                #
                #   訂單數量 = material_qty
                #   工序 MEINH = original_must_receive_end_qty
                #
                # 差額即為送入廠內前已存在的外部加工廢料。
                #
                # 例如：
                #
                #   999900006747
                #
                #   material_qty = 350
                #   MEINH         = 349
                #
                #   外部加工廢料 = 1
                # =================================================

                external_scrap_qty = 0

                for a in assemble_records:

                    original_end_qty = to_int(
                        getattr(
                            a,
                            "original_must_receive_end_qty",
                            0
                        ),
                        0
                    )

                    if original_end_qty <= 0:
                        continue

                    external_scrap_qty = max(
                        external_scrap_qty,

                        max(
                            0,
                            to_int(
                                material.material_qty,
                                0
                            )
                            -
                            original_end_qty
                        )
                    )
                '''
                #
                # =================================================
                # 外部加工既有廢料
                #
                # 不再用：
                #
                # material_qty - MEINH
                #
                # 推算。
                #
                # 改成直接讀 Excel 匯入 P_Material 的真實欄位。
                # =================================================

                external_scrap_qty = max(
                    0,
                    to_int(
                        getattr(
                            material,
                            "external_scrap_qty",
                            0
                        ),
                        0
                    )
                )
                #

                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )


                # =================================================
                # 入庫 / 廢品
                # =================================================

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )


                assemble_scrap = (
                    asm_scrap_map.get(
                        material_id,
                        0
                    )
                )


                product_scrap = (
                    product_scrap_map.get(
                        material_id,
                        0
                    )
                )


                material_scrap = max(
                    assemble_scrap,
                    product_scrap,
                    0,
                )


                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )

                # 外部加工送進廠內前既有廢料
                total_external_scrap += (
                    external_scrap_qty
                )

                # =================================================
                # Information 詳情按鍵
                #
                # 有真正 Process.begin_time 才 enable
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id

                        and

                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]


                total_process_records += (
                    len(
                        valid_processes
                    )
                )


                # =================================================
                # Process 完成良品量
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )


                    # ---------------------------------------------
                    # 非加工 Process 排除
                    # ---------------------------------------------

                    if process_type in {
                        1,
                        2,
                        3,
                        5,
                        6,
                        19,
                        29,
                        31,
                    }:
                        continue


                    if not safe_str(
                        p.begin_time
                    ).strip():
                        continue


                    if not safe_str(
                        p.end_time
                    ).strip():
                        continue


                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )


                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )


                # =================================================
                # Assemble fallback
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )


                    # 只有真正結束列
                    if assemble_step != 0:
                        continue


                    row_completed_qty = max(

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )


                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )


                total_completed += (
                    material_completed
                )


                # =================================================
                # Active 加工 Process
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )


                    if process_type in {
                        1,
                        2,
                        3,
                        5,
                        6,
                        19,
                        29,
                        31,
                    }:
                        continue


                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )


                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )


                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = True
                        break


                # =================================================
                # Pending 加工工序
                # =================================================

                pending_assemble_rows = []

                for a in assemble_records:

                    step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )


                    if step <= 0:
                        continue


                    # ---------------------------------------------
                    # 排除歷史複製列
                    # ---------------------------------------------

                    if (
                        getattr(
                            a,
                            "is_copied_from_id",
                            None
                        ) is not None

                        and

                        to_int(
                            getattr(
                                a,
                                "show2_ok",
                                0
                            ),
                            0
                        ) == 0
                    ):
                        continue


                    if bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    ):
                        continue


                    must_end_qty = to_int(
                        getattr(
                            a,
                            "must_receive_end_qty",
                            0
                        ),
                        0
                    )


                    if must_end_qty <= 0:

                        must_end_qty = to_int(
                            getattr(
                                a,
                                "must_receive_qty",
                                0
                            ),
                            0
                        )


                    completed_qty = max(

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    if (
                        must_end_qty > 0
                        and
                        completed_qty >= must_end_qty
                    ):
                        continue


                    pending_assemble_rows.append(
                        a
                    )


                has_pending_process_step = bool(
                    pending_assemble_rows
                )


                # =================================================
                # 下一道工序名稱
                # =================================================

                if (
                    not current_process_comment
                    and
                    pending_assemble_rows
                ):

                    min_assemble = min(
                        pending_assemble_rows,
                        key=lambda a:
                            to_int(
                                getattr(
                                    a,
                                    "seq_num",
                                    999999
                                ),
                                999999
                            )
                    )


                    work_num = safe_str(
                        min_assemble.work_num
                    ).strip()


                    key = norm_code(
                        work_num
                    )


                    part_info = (
                        part_info_map.get(
                            key
                        )
                        or
                        part_info_map.get(
                            alias_code(
                                key
                            )
                        )
                    )


                    if part_info:

                        current_process_comment = (
                            safe_str(
                                part_info.get(
                                    "comment"
                                )
                            ).strip()
                        )

                    else:

                        current_process_comment = (
                            work_num
                        )


                # =================================================
                # Material 原始狀態
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )


                # =================================================
                # 是否已具備 PBegin 資格
                #
                # 與 PBegin Material 狀態一致：
                #
                # isTakeOk = True
                # isShow   = True
                # show1_ok = 2
                # show2_ok >= 3
                #
                # 支援：
                #
                # 正常領料
                # 不領料直接送出
                # =================================================

                material_is_take_ok = bool(
                    getattr(
                        material,
                        "isTakeOk",
                        False
                    )
                )


                material_is_show = bool(
                    getattr(
                        material,
                        "isShow",
                        False
                    )
                )


                material_show1 = to_int(
                    getattr(
                        material,
                        "show1_ok",
                        0
                    ),
                    0
                )

                '''
                has_entered_process_stage = (
                    material_is_take_ok
                    and
                    material_is_show
                    and
                    material_show1 == 2
                    and
                    raw_status >= 3
                )
                '''
                # 20260817版
                # =================================================
                # 是否已進入加工/後續流程
                #
                # show1_ok:
                #   2 = 加工站
                #   3 = 成品站
                #
                # 所以不能只限定 == 2。
                # 已到成品站的舊工單也明顯早已離開領料區。
                # =================================================

                has_entered_process_stage = (
                    material_is_take_ok
                    and
                    material_is_show
                    and
                    material_show1 >= 2
                    and
                    raw_status >= 3
                )
                #


                is_still_prepare_stage = (
                    not has_entered_process_stage
                )


                # =================================================
                # PEnd 待送出
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(
                            getattr(
                                a,
                                "process_step_code",
                                -1
                            ),
                            -1
                        ) == 0

                        and

                        max(
                            to_int(
                                getattr(
                                    a,
                                    "completed_qty",
                                    0
                                ),
                                0
                            ),

                            to_int(
                                getattr(
                                    a,
                                    "total_completed_qty",
                                    0
                                ),
                                0
                            ),
                        ) > 0

                        and

                        bool(
                            getattr(
                                a,
                                "isAssembleStationShow",
                                False
                            )
                        )

                        and

                        not bool(
                            getattr(
                                a,
                                "isWarehouseStationShow",
                                False
                            )
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # Warehouse
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # Batch Status
                #
                # 順序：
                #
                # prepare
                # active
                # waiting PBegin
                # next process
                # PEnd
                # Warehouse
                # stockin
                # =================================================

                # -------------------------------------------------
                # A. 尚未進入 PBegin
                # -------------------------------------------------

                if is_still_prepare_stage:

                    if raw_status <= 0:

                        batch_status = 0

                    elif raw_status == 1:

                        batch_status = 1

                    else:

                        batch_status = 2


                # -------------------------------------------------
                # B. 真正加工中
                # -------------------------------------------------

                elif has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # C. 已經具備 PBegin 資格，等待加工
                # -------------------------------------------------

                elif (
                    has_entered_process_stage
                    and
                    raw_status == 3
                ):

                    batch_status = 3


                # -------------------------------------------------
                # D. 尚有下一道加工
                # -------------------------------------------------

                elif has_pending_process_step:

                    batch_status = 3


                # -------------------------------------------------
                # E. PEnd 待送出
                # -------------------------------------------------

                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # F. Warehouse
                # -------------------------------------------------

                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin < material_completed
                ):

                    if raw_status == 7:

                        batch_status = 7

                    else:

                        batch_status = 6


                # -------------------------------------------------
                # G. 入庫完成
                # -------------------------------------------------

                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin >= material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # H. fallback
                # -------------------------------------------------

                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )


                # =================================================
                # summary
                # =================================================

                material_summaries.append({

                    "material":
                        material,

                    "material_id":
                        material_id,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,

                    "has_active_process":
                        has_active_process,

                    "has_pending_process_step":
                        has_pending_process_step,

                    "has_waiting_send":
                        has_waiting_send,

                    "has_arrived_warehouse":
                        has_arrived_warehouse,

                    "has_entered_process_stage":
                        has_entered_process_stage,

                    "is_still_prepare_stage":
                        is_still_prepare_stage,

                    "assemble_count":
                        len(
                            assemble_records
                        ),

                    "process_count":
                        len(
                            process_records
                        ),

                    "product_count":
                        product_count_map.get(
                            material_id,
                            0
                        ),

                    "external_scrap_qty":
                        external_scrap_qty,
                })


            # ====================================================
            # 8-2. 排除空 root
            # ====================================================

            effective_material_summaries = [
                item
                for item
                in material_summaries

                if (
                    to_int(
                        item.get(
                            "assemble_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "process_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "product_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    ) > 0

                    or

                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_arrived_warehouse",
                            False
                        )
                    )
                )
            ]


            status_source = (
                effective_material_summaries
                if effective_material_summaries
                else material_summaries
            )


            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )

                for item
                in status_source
            ]


            # ====================================================
            # 8-3. 整單狀態
            # ====================================================

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )


            # ----------------------------------------------------
            # 真正還在領料的 batch
            # ----------------------------------------------------

            prepare_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    2
                )

                for item
                in status_source

                if bool(
                    item.get(
                        "is_still_prepare_stage",
                        False
                    )
                )
            ]


            if prepare_statuses:

                order_status = min(
                    order_status,
                    min(
                        prepare_statuses
                    )
                )


            # ----------------------------------------------------
            # 真正已進加工流程，且有下一道工序
            # ----------------------------------------------------

            if any(
                (
                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    and

                    bool(
                        item.get(
                            "has_entered_process_stage",
                            False
                        )
                    )
                )

                for item
                in status_source
            ):

                if not any(
                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    for item
                    in status_source
                ):

                    order_status = min(
                        order_status,
                        3
                    )


            # ====================================================
            # 入庫安全判斷
            # ====================================================

            if (
                total_completed > 0
                and
                total_stockin < total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:

                    order_status = 7

                else:

                    order_status = 6


            # ====================================================
            # 全部 batch 入庫完成
            # ====================================================

            all_batches_stockin_done = bool(
                status_source
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    and

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )

                    and

                    not bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    and

                    not (
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )

                        and

                        bool(
                            item.get(
                                "has_entered_process_stage",
                                False
                            )
                        )
                    )

                    and

                    to_int(
                        item.get(
                            "status"
                        ),
                        0
                    ) >= 6
                )

                for item
                in status_source
            )


            if all_batches_stockin_done:

                order_status = 8


            # ====================================================
            # 單一 material 差異
            # ====================================================

            is_single_material_order = (
                len(
                    group_materials
                )
                ==
                1
            )


            #accounted_total = (
            #    total_stockin
            #    +
            #    total_scrap
            #)
            #
            accounted_total = (
                total_stockin
                +
                total_scrap
                +
                total_external_scrap
            )
            #

            unexplained_difference = 0


            if (
                is_single_material_order
                and
                req_qty > 0
            ):

                unexplained_difference = max(
                    0,
                    req_qty
                    -
                    accounted_total
                )


            # ====================================================
            # show3
            # ====================================================

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                if (
                    is_single_material_order
                    and
                    req_qty > 0
                ):

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 訂單 {req_qty}"
                        )


                        if unexplained_difference > 0:

                            show3_text += (
                                f"（差異 "
                                f"{unexplained_difference}）"
                            )


                    elif unexplained_difference > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                            f" / 訂單 {req_qty}"
                            f"（差異 "
                            f"{unexplained_difference}）"
                        )


                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


                else:

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 已完成 {total_completed}"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


            elif (
                order_status == 5
                and
                total_completed > 0
            ):

                show3_text = (
                    f"已完成 {total_completed}"
                    f" / 等待送出"
                )


            # ----------------------------------------------------
            # 真正領料階段才不顯示加工名稱
            # ----------------------------------------------------

            elif order_status <= 2:

                show3_text = ""


            elif (
                order_status <= 4
                and
                total_completed > 0
                and
                req_qty > 0
            ):

                remaining_qty = max(
                    0,
                    req_qty
                    -
                    total_completed
                    -
                    total_scrap
                )


                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / 已完成 {total_completed}"
                    f" / 訂單 {req_qty}"
                )


                if total_scrap > 0:

                    show3_text += (
                        f" / 廢品 {total_scrap}"
                    )


                if remaining_qty > 0:

                    show3_text += (
                        f"（待加工 "
                        f"{remaining_qty}）"
                    )

            #
            else:

                show3_text = (
                    current_process_comment
                    or ""
                )

                if total_external_scrap > 0:

                    if show3_text:

                        show3_text += (
                            f" / 外部加工廢品 "
                            f"{total_external_scrap}"
                        )

                    else:

                        show3_text = (
                            f"外部加工廢品 "
                            f"{total_external_scrap}"
                        )
            #


            # ====================================================
            # 領料中人員
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue


                    m = item[
                        "material"
                    ]


                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )


                    if display_open_emp_id:
                        break


            # ====================================================
            # 現況數量
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )


            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )


            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )


            # ====================================================
            # 回傳
            # ====================================================

            result = {

                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                "req_qty":
                    req_qty,

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative.material_comment
                    ).strip(),

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                "total_process_records":
                    total_process_records,

                "material_count":
                    len(
                        group_materials
                    ),

                "effective_material_count":
                    len(
                        status_source
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "accounted_total":
                    accounted_total,

                "unexplained_difference":
                    unexplained_difference,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "remaining_process_qty":
                    max(
                        0,
                        req_qty
                        -
                        total_completed
                        -
                        total_scrap
                    )
                    if req_qty > 0
                    else 0,

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,

                "has_pending_process_step":
                    any(
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),

                "has_waiting_send":
                    any(
                        bool(
                            item.get(
                                "has_waiting_send",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),
            }


            results.append(
                result
            )


        # ========================================================
        # 9. 排序
        # ========================================================

        results.sort(
            key=lambda x: (

                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    ==
                    0
                ),

                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )


        # ========================================================
        # 10. 不限制筆數
        # ========================================================

        total = len(
            results
        )

        page_results = (
            results
        )


        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(
                page_results
            )
        )


        return jsonify({
            "status": True,
            "total": total,
            "informations": page_results,
        })


    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500


    finally:

        s.close()
"""


# 20260821版
# 20260819版 clean version
@listTableP.route(
    "/listInformationsP",
    methods=["GET"]
)
def list_informations_p():

    print("listInformationsP....")

    only_unfinished = (
        request.args.get(
            "only_unfinished",
            "0"
        )
        in (
            "1",
            "true",
            "True",
        )
    )

    print(
        '\033[42m'
        + 'only_unfinished:'
        + '\033[0m',
        only_unfinished
    )

    s = Session()

    try:

        # ========================================================
        # 共用工具
        # ========================================================

        def to_int(
            value,
            default=0
        ):
            try:

                if value is None:
                    return default

                if isinstance(
                    value,
                    bool
                ):
                    return int(value)

                value = str(
                    value
                ).strip()

                if value == "":
                    return default

                return int(
                    float(value)
                )

            except Exception:
                return default


        def safe_str(
            value,
            default=""
        ):
            try:

                if value is None:
                    return default

                return str(value)

            except Exception:
                return default


        def norm_code(
            value
        ):

            return (
                safe_str(value)
                .strip()
                .upper()
                .replace(
                    " ",
                    ""
                )
            )


        def alias_code(
            value
        ):

            value = norm_code(
                value
            )

            m = re.match(
                r'^(B\d{3})[A-Z]*-(\d+)$',
                value
            )

            if not m:
                return value

            return (
                f"{m.group(1)}-"
                f"{m.group(2)}"
            )


        # ========================================================
        # 狀態
        # ========================================================

        STATUS_TEXT = {
            0: "未領料",
            1: "領料中",
            2: "領料已完成",
            3: "等待加工作業",
            4: "加工作業進行中",
            5: "等待送出",
            6: "等待入庫作業",
            7: "入庫進行中",
            8: "入庫完成",
        }


        def status_text(
            status_code
        ):

            return STATUS_TEXT.get(
                to_int(
                    status_code,
                    -1
                ),
                f"未知狀態({status_code})"
            )


        def station_from_status(
            status_code
        ):

            status_code = to_int(
                status_code,
                0
            )

            if status_code <= 2:
                return "領料站"

            if status_code <= 5:
                return "加工站"

            return "成品站"


        # ========================================================
        # 20260819
        # P_Process 是否屬於「非加工」流程
        #
        # process_type = 5 有撞碼：
        #   type=5 + assemble_id=0  -> 堆高機：領料區 -> 加工區
        #   type=5 + assemble_id>0  -> 真正加工工序，例如 B108-26
        #
        # type=6 目前固定代表：
        #   堆高機：加工區 -> 成品區
        # ========================================================

        def is_non_work_process(
            process_type,
            assemble_id
        ):

            process_type = to_int(
                process_type,
                0
            )

            assemble_id = to_int(
                assemble_id,
                0
            )

            if process_type in {
                1,
                2,
                3,
                6,
                19,
                29,
                31,
            }:
                return True

            if (
                process_type == 5
                and
                assemble_id == 0
            ):
                return True

            return False

        # ========================================================
        # 1. P_Part 製程名稱
        # ========================================================

        part_info_map = {}

        for p in (
            s.query(P_Part)
            .all()
        ):

            code = norm_code(
                p.part_code
            )

            if not code:
                continue

            info = {
                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    to_int(
                        p.process_step_code,
                        0
                    ),
            }

            part_info_map[
                code
            ] = info

            part_info_map.setdefault(
                alias_code(
                    code
                ),
                info
            )


        # ========================================================
        # 2. P_Assemble 廢品
        # ========================================================

        asm_scrap_rows = (
            s.query(
                P_Assemble.material_id,

                func.coalesce(
                    func.sum(
                        P_Assemble.abnormal_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Assemble.material_id
            )
            .all()
        )

        asm_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in asm_scrap_rows
        }


        # ========================================================
        # 3. P_Product 入庫量
        # ========================================================

        stockin_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.allOk_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        stockin_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in stockin_rows
        }


        # ========================================================
        # 4. P_Product 廢品
        # ========================================================

        product_scrap_rows = (
            s.query(
                P_Product.material_id,

                func.coalesce(
                    func.sum(
                        P_Product.non_good_qty
                    ),
                    0
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_scrap_map = {
            to_int(mid, 0):
                to_int(qty, 0)

            for mid, qty
            in product_scrap_rows
        }


        # ========================================================
        # 5. P_Product count
        # ========================================================

        product_count_rows = (
            s.query(
                P_Product.material_id,

                func.count(
                    P_Product.id
                )
            )
            .group_by(
                P_Product.material_id
            )
            .all()
        )

        product_count_map = {
            to_int(mid, 0):
                to_int(cnt, 0)

            for mid, cnt
            in product_count_rows
        }


        # ========================================================
        # 6. 所有 P_Material
        # ========================================================

        materials = (
            s.query(P_Material)
            .order_by(
                P_Material.order_num.asc(),
                P_Material.id.asc(),
            )
            .all()
        )

        if not materials:

            return jsonify({
                "status": False,
                "total": 0,
                "informations": [],
            })


        # ========================================================
        # 7. order_num 分組
        # ========================================================

        order_groups = {}

        for material in materials:

            order_num = safe_str(
                material.order_num
            ).strip()

            if not order_num:
                continue

            order_groups.setdefault(
                order_num,
                []
            ).append(
                material
            )


        results = []


        # ========================================================
        # 8. 每張訂單
        # ========================================================

        for (
            order_num,
            group_materials
        ) in order_groups.items():

            if not group_materials:
                continue


            representative = sorted(
                group_materials,
                key=lambda m: (

                    0
                    if getattr(
                        m,
                        "is_copied_from_id",
                        None
                    ) is None
                    else 1,

                    to_int(
                        m.id,
                        0
                    ),
                )
            )[0]


            req_qty = to_int(
                representative.material_qty,
                0
            )


            total_stockin = 0
            total_completed = 0

            # 廠內加工產生的廢品
            total_scrap = 0

            # 外部加工送進廠內前已存在的廢料
            total_external_scrap = 0

            total_process_records = 0

            material_summaries = []

            current_process_comment = ""


            # ====================================================
            # 8-1. 每個 material
            # ====================================================

            for material in group_materials:

                material_id = to_int(
                    material.id,
                    0
                )


                assemble_records = (
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

                '''
                # =================================================
                # 外部加工既有廢料
                #
                # 適用：
                #   不領料 / 外部加工後直接送廠內加工
                #
                # Excel：
                #
                #   訂單數量 = material_qty
                #   工序 MEINH = original_must_receive_end_qty
                #
                # 差額即為送入廠內前已存在的外部加工廢料。
                #
                # 例如：
                #
                #   999900006747
                #
                #   material_qty = 350
                #   MEINH         = 349
                #
                #   外部加工廢料 = 1
                # =================================================

                external_scrap_qty = 0

                for a in assemble_records:

                    original_end_qty = to_int(
                        getattr(
                            a,
                            "original_must_receive_end_qty",
                            0
                        ),
                        0
                    )

                    if original_end_qty <= 0:
                        continue

                    external_scrap_qty = max(
                        external_scrap_qty,

                        max(
                            0,
                            to_int(
                                material.material_qty,
                                0
                            )
                            -
                            original_end_qty
                        )
                    )
                '''
                #
                # =================================================
                # 外部加工既有廢料
                #
                # 不再用：
                #
                # material_qty - MEINH
                #
                # 推算。
                #
                # 改成直接讀 Excel 匯入 P_Material 的真實欄位。
                # =================================================

                external_scrap_qty = max(
                    0,
                    to_int(
                        getattr(
                            material,
                            "external_scrap_qty",
                            0
                        ),
                        0
                    )
                )
                #

                process_records = (
                    s.query(P_Process)
                    .filter(
                        P_Process.material_id
                        ==
                        material_id
                    )
                    .order_by(
                        P_Process.id.asc()
                    )
                    .all()
                )


                # =================================================
                # 入庫 / 廢品
                # =================================================

                material_stockin = (
                    stockin_map.get(
                        material_id,
                        0
                    )
                )


                assemble_scrap = (
                    asm_scrap_map.get(
                        material_id,
                        0
                    )
                )


                product_scrap = (
                    product_scrap_map.get(
                        material_id,
                        0
                    )
                )


                material_scrap = max(
                    assemble_scrap,
                    product_scrap,
                    0,
                )


                total_stockin += (
                    material_stockin
                )

                total_scrap += (
                    material_scrap
                )

                # 外部加工送進廠內前既有廢料
                total_external_scrap += (
                    external_scrap_qty
                )

                # =================================================
                # Information 詳情按鍵
                #
                # 有真正 Process.begin_time 才 enable
                # =================================================

                valid_processes = [
                    p
                    for p
                    in process_records
                    if (
                        to_int(
                            p.material_id,
                            0
                        )
                        ==
                        material_id

                        and

                        safe_str(
                            p.begin_time
                        ).strip()
                        != ""
                    )
                ]


                total_process_records += (
                    len(
                        valid_processes
                    )
                )


                # =================================================
                # Process 完成良品量
                # =================================================

                process_completed_qty = 0

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )


                    # ---------------------------------------------
                    # 非加工 Process 排除
                    # ---------------------------------------------

                    if is_non_work_process(
                        process_type,
                        getattr(
                            p,
                            "assemble_id",
                            0
                        )
                    ):
                        continue


                    if not safe_str(
                        p.begin_time
                    ).strip():
                        continue


                    if not safe_str(
                        p.end_time
                    ).strip():
                        continue


                    qty = to_int(
                        getattr(
                            p,
                            "process_work_time_qty",
                            0
                        ),
                        0
                    )


                    process_completed_qty = max(
                        process_completed_qty,
                        qty
                    )


                # =================================================
                # Assemble fallback
                # =================================================

                assemble_completed_qty = 0

                for a in assemble_records:

                    assemble_step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )


                    # 只有真正結束列
                    if assemble_step != 0:
                        continue


                    row_completed_qty = max(

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    assemble_completed_qty = max(
                        assemble_completed_qty,
                        row_completed_qty
                    )


                material_completed = max(
                    process_completed_qty,
                    assemble_completed_qty,
                    material_stockin,
                    0,
                )


                # 20260819：
                # 訂單層 completed 改在 material_summaries 完成後彙總。
                # 避免串接工序：
                # B100 2268 + B108 2268 被誤算成 4536。


                # =================================================
                # Active 加工 Process
                # =================================================

                has_active_process = False

                for p in process_records:

                    process_type = to_int(
                        p.process_type,
                        0
                    )


                    if is_non_work_process(
                        process_type,
                        getattr(
                            p,
                            "assemble_id",
                            0
                        )
                    ):
                        continue


                    has_begin = bool(
                        safe_str(
                            p.begin_time
                        ).strip()
                    )


                    has_end = bool(
                        safe_str(
                            p.end_time
                        ).strip()
                    )


                    if (
                        has_begin
                        and
                        not has_end
                        and
                        bool(
                            getattr(
                                p,
                                "has_started",
                                False
                            )
                        )
                    ):

                        has_active_process = True
                        break


                # =================================================
                # Pending 加工工序
                # =================================================

                pending_assemble_rows = []

                for a in assemble_records:

                    step = to_int(
                        getattr(
                            a,
                            "process_step_code",
                            0
                        ),
                        0
                    )


                    if step <= 0:
                        continue


                    # ---------------------------------------------
                    # 排除歷史複製列
                    # ---------------------------------------------

                    if (
                        getattr(
                            a,
                            "is_copied_from_id",
                            None
                        ) is not None

                        and

                        to_int(
                            getattr(
                                a,
                                "show2_ok",
                                0
                            ),
                            0
                        ) == 0
                    ):
                        continue


                    if bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    ):
                        continue


                    must_end_qty = to_int(
                        getattr(
                            a,
                            "must_receive_end_qty",
                            0
                        ),
                        0
                    )


                    if must_end_qty <= 0:

                        must_end_qty = to_int(
                            getattr(
                                a,
                                "must_receive_qty",
                                0
                            ),
                            0
                        )


                    completed_qty = max(

                        to_int(
                            getattr(
                                a,
                                "completed_qty",
                                0
                            ),
                            0
                        ),

                        to_int(
                            getattr(
                                a,
                                "total_completed_qty",
                                0
                            ),
                            0
                        ),
                    )


                    if (
                        must_end_qty > 0
                        and
                        completed_qty >= must_end_qty
                    ):
                        continue


                    pending_assemble_rows.append(
                        a
                    )


                has_pending_process_step = bool(
                    pending_assemble_rows
                )


                # =================================================
                # 下一道工序名稱
                # =================================================

                if (
                    not current_process_comment
                    and
                    pending_assemble_rows
                ):

                    min_assemble = min(
                        pending_assemble_rows,
                        key=lambda a:
                            to_int(
                                getattr(
                                    a,
                                    "seq_num",
                                    999999
                                ),
                                999999
                            )
                    )


                    work_num = safe_str(
                        min_assemble.work_num
                    ).strip()


                    key = norm_code(
                        work_num
                    )


                    part_info = (
                        part_info_map.get(
                            key
                        )
                        or
                        part_info_map.get(
                            alias_code(
                                key
                            )
                        )
                    )


                    if part_info:

                        current_process_comment = (
                            safe_str(
                                part_info.get(
                                    "comment"
                                )
                            ).strip()
                        )

                    else:

                        current_process_comment = (
                            work_num
                        )


                # =================================================
                # Material 原始狀態
                # =================================================

                raw_status = to_int(
                    getattr(
                        material,
                        "show2_ok",
                        0
                    ),
                    0
                )


                # =================================================
                # 是否已具備 PBegin 資格
                #
                # 與 PBegin Material 狀態一致：
                #
                # isTakeOk = True
                # isShow   = True
                # show1_ok = 2
                # show2_ok >= 3
                #
                # 支援：
                #
                # 正常領料
                # 不領料直接送出
                # =================================================

                material_is_take_ok = bool(
                    getattr(
                        material,
                        "isTakeOk",
                        False
                    )
                )


                material_is_show = bool(
                    getattr(
                        material,
                        "isShow",
                        False
                    )
                )


                material_show1 = to_int(
                    getattr(
                        material,
                        "show1_ok",
                        0
                    ),
                    0
                )

                '''
                has_entered_process_stage = (
                    material_is_take_ok
                    and
                    material_is_show
                    and
                    material_show1 == 2
                    and
                    raw_status >= 3
                )
                '''
                # 20260817版
                # =================================================
                # 是否已進入加工/後續流程
                #
                # show1_ok:
                #   2 = 加工站
                #   3 = 成品站
                #
                # 所以不能只限定 == 2。
                # 已到成品站的舊工單也明顯早已離開領料區。
                # =================================================

                has_entered_process_stage = (
                    material_is_take_ok
                    and
                    material_is_show
                    and
                    material_show1 >= 2
                    and
                    raw_status >= 3
                )
                #


                is_still_prepare_stage = (
                    not has_entered_process_stage
                )


                # =================================================
                # PEnd 待送出
                # =================================================

                has_waiting_send = any(
                    (
                        to_int(
                            getattr(
                                a,
                                "process_step_code",
                                -1
                            ),
                            -1
                        ) == 0

                        and

                        max(
                            to_int(
                                getattr(
                                    a,
                                    "completed_qty",
                                    0
                                ),
                                0
                            ),

                            to_int(
                                getattr(
                                    a,
                                    "total_completed_qty",
                                    0
                                ),
                                0
                            ),
                        ) > 0

                        and

                        bool(
                            getattr(
                                a,
                                "isAssembleStationShow",
                                False
                            )
                        )

                        and

                        not bool(
                            getattr(
                                a,
                                "isWarehouseStationShow",
                                False
                            )
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # Warehouse
                # =================================================

                has_arrived_warehouse = any(
                    bool(
                        getattr(
                            a,
                            "isWarehouseStationShow",
                            False
                        )
                    )

                    for a
                    in assemble_records
                )


                # =================================================
                # Batch Status
                #
                # 順序：
                #
                # prepare
                # active
                # waiting PBegin
                # next process
                # PEnd
                # Warehouse
                # stockin
                # =================================================

                #
                # =================================================
                # 20260819版
                # Batch Status
                #
                # 正確優先順序：
                #
                # 1. 尚未進加工
                # 2. 真正加工中
                # 3. PEnd 等待送出
                # 4. Warehouse 等待入庫
                # 5. 已入庫完成
                # 6. 等待下一道加工
                # 7. 等待 PBegin
                # 8. fallback
                #
                # 非常重要：
                #
                # Warehouse 狀態必須優先於 raw_status == 3。
                #
                # 否則：
                #
                # show2_ok = 3
                # +
                # isWarehouseStationShow = True
                #
                # 仍會被誤判成「等待加工作業」。
                # =================================================


                # -------------------------------------------------
                # A. 尚未真正進入加工流程
                # -------------------------------------------------
                if is_still_prepare_stage:

                    if raw_status <= 0:

                        batch_status = 0

                    elif raw_status == 1:

                        batch_status = 1

                    else:

                        batch_status = 2


                # -------------------------------------------------
                # B. 真正加工中
                # -------------------------------------------------
                elif has_active_process:

                    batch_status = 4


                # -------------------------------------------------
                # C. PEnd 已完成，等待送出
                # -------------------------------------------------
                elif has_waiting_send:

                    batch_status = 5


                # -------------------------------------------------
                # D. 已經送到 Warehouse，
                #    但尚未全部入庫
                # -------------------------------------------------
                elif (
                    has_arrived_warehouse
                    and
                    material_completed > 0
                    and
                    material_stockin
                    <
                    material_completed
                ):

                    if raw_status == 7:

                        batch_status = 7

                    else:

                        batch_status = 6


                # -------------------------------------------------
                # E. 已真正入庫完成
                # -------------------------------------------------
                elif (
                    material_completed > 0
                    and
                    material_stockin > 0
                    and
                    material_stockin
                    >=
                    material_completed
                ):

                    batch_status = 8


                # -------------------------------------------------
                # F. 尚有下一道加工工序
                # -------------------------------------------------
                elif has_pending_process_step:

                    batch_status = 3


                # -------------------------------------------------
                # G. 已具備 PBegin 資格，
                #    等待加工
                # -------------------------------------------------
                elif (
                    has_entered_process_stage
                    and
                    raw_status == 3
                ):

                    batch_status = 3


                # -------------------------------------------------
                # H. fallback
                # -------------------------------------------------
                else:

                    batch_status = max(
                        0,
                        min(
                            raw_status,
                            8
                        )
                    )
                #

                # =================================================
                # 20260819
                # 這個 material 是否代表「最終需入庫」工序
                # =================================================

                requires_stockin = any(
                    bool(
                        getattr(
                            a,
                            "isStockIn",
                            False
                        )
                    )
                    for a
                    in assemble_records
                )


                # =================================================
                # summary
                # =================================================

                material_summaries.append({

                    "material":
                        material,

                    "material_id":
                        material_id,

                    "requires_stockin":
                        requires_stockin,

                    "completed_qty":
                        material_completed,

                    "stockin_qty":
                        material_stockin,

                    "scrap_qty":
                        material_scrap,

                    "status":
                        batch_status,
                    '''
                    #
                    # =================================================
                    # 此 material 是否包含「最後需要入庫」的加工工序
                    #
                    # B100-03 isStockIn=False
                    #   → 中間工序
                    #
                    # B108-26 isStockIn=True
                    #   → 最終輸出工序
                    # =================================================
                    "requires_stockin":
                        any(
                            bool(
                                getattr(
                                    a,
                                    "isStockIn",
                                    False
                                )
                            )
                            for a
                            in assemble_records
                        ),
                    #
                    '''

                    "has_active_process":
                        has_active_process,

                    "has_pending_process_step":
                        has_pending_process_step,

                    "has_waiting_send":
                        has_waiting_send,

                    "has_arrived_warehouse":
                        has_arrived_warehouse,

                    "has_entered_process_stage":
                        has_entered_process_stage,

                    "is_still_prepare_stage":
                        is_still_prepare_stage,

                    "assemble_count":
                        len(
                            assemble_records
                        ),

                    "process_count":
                        len(
                            process_records
                        ),

                    "product_count":
                        product_count_map.get(
                            material_id,
                            0
                        ),

                    "external_scrap_qty":
                        external_scrap_qty,
                })


            # ====================================================
            # 8-2. 排除空 root
            # ====================================================

            effective_material_summaries = [
                item
                for item
                in material_summaries

                if (
                    to_int(
                        item.get(
                            "assemble_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "process_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "product_count"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    or

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    ) > 0

                    or

                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    or

                    bool(
                        item.get(
                            "has_arrived_warehouse",
                            False
                        )
                    )
                )
            ]


            base_status_source = (
                effective_material_summaries
                if effective_material_summaries
                else material_summaries
            )


            # ====================================================
            # 20260819
            # 同 order_num、多 material 的串接工序修正
            #
            # 例：
            #   material A / B100 / isStockIn=False
            #   material B / B108 / isStockIn=True
            #
            # A、B 是同一批產品的前後工序，不是兩批產品。
            # ====================================================

            final_output_summaries = [
                item
                for item
                in base_status_source
                if bool(
                    item.get(
                        "requires_stockin",
                        False
                    )
                )
            ]


            def is_completed_intermediate(
                item
            ):

                if bool(
                    item.get(
                        "requires_stockin",
                        False
                    )
                ):
                    return False

                if to_int(
                    item.get(
                        "completed_qty"
                    ),
                    0
                ) <= 0:
                    return False

                if bool(
                    item.get(
                        "has_active_process",
                        False
                    )
                ):
                    return False

                if bool(
                    item.get(
                        "has_pending_process_step",
                        False
                    )
                ):
                    return False

                if bool(
                    item.get(
                        "has_waiting_send",
                        False
                    )
                ):
                    return False

                return True

            '''
            status_source = [
                item
                for item
                in base_status_source
                if not is_completed_intermediate(
                    item
                )
            ]

            if not status_source:

                status_source = (
                    final_output_summaries
                    if final_output_summaries
                    else base_status_source
                )
            '''
            #
            # ====================================================
            # 整張訂單的狀態來源
            #
            # 若已有明確「最終需入庫」material：
            #
            #   狀態完全由最終輸出 material 決定。
            #
            # 前段 B100 仍保留於 Information 詳情，
            # 但不再影響整單目前進度。
            # ====================================================
            '''
            if final_output_summaries:

                status_source = (
                    final_output_summaries
                )

            else:

                status_source = [
                    item
                    for item
                    in base_status_source
                    if not is_completed_intermediate(
                        item
                    )
                ]

                if not status_source:

                    status_source = (
                        base_status_source
                    )
            '''
            # 20260821版
            # ====================================================
            # 整張訂單狀態來源
            #
            # 原則：
            #
            # 1. 只要任何 material 還有真正 active Process，
            #    整張訂單必須反映該 active material。
            #
            # 2. 沒有 active Process 時，
            #    若存在最終需入庫 material，
            #    才由 final_output_summaries 決定目前狀態。
            #
            # 3. 避免前段工序明明還在加工，
            #    卻因 final_output material 尚未開始，
            #    被顯示成「等待加工作業」。
            # ====================================================
            '''
            active_summaries = [
                item
                for item
                in base_status_source
                if bool(
                    item.get(
                        "has_active_process",
                        False
                    )
                )
            ]
            '''
            #
            # ====================================================
            # 20260821
            # Active material
            #
            # 不再二次依賴 has_active_process。
            #
            # 前面每個 material 已經完成 Batch Status 判斷：
            #
            #     batch_status = 4
            #
            # 就代表該 material 有真正 active 的加工 Process。
            #
            # 直接使用 status == 4 最穩定。
            # ====================================================

            active_summaries = [
                item
                for item
                in base_status_source
                if to_int(
                    item.get(
                        "status"
                    ),
                    0
                ) == 4
            ]
            #

            # ----------------------------------------------------
            # A. 有真正加工中的 Process
            #
            # active 優先權最高。
            # ----------------------------------------------------
            if active_summaries:

                status_source = (
                    active_summaries
                )


            # ----------------------------------------------------
            # B. 沒有 active，
            #    才由最終輸出 material 決定整單狀態
            # ----------------------------------------------------
            elif final_output_summaries:

                status_source = (
                    final_output_summaries
                )


            # ----------------------------------------------------
            # C. 沒有 final output，
            #    使用一般有效 material
            # ----------------------------------------------------
            else:

                status_source = [
                    item
                    for item
                    in base_status_source
                    if not is_completed_intermediate(
                        item
                    )
                ]

                if not status_source:

                    status_source = (
                        base_status_source
                    )
            #


            # ----------------------------------------------------
            # 訂單層「已完成 / 已入庫」數量來源
            #
            # 有 requires_stockin=True：
            #   只統計最終輸出 material。
            #
            # 若有多個 requires_stockin=True：
            #   視為真正分批最終輸出，仍正常相加。
            # ----------------------------------------------------

            quantity_source = (
                final_output_summaries
                if final_output_summaries
                else base_status_source
            )


            total_completed = sum(
                max(
                    0,
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )
                )
                for item
                in quantity_source
            )


            total_stockin = sum(
                max(
                    0,
                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                )
                for item
                in quantity_source
            )


            batch_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                )

                for item
                in status_source
            ]

            #
            # ====================================================
            # 20260821 DEBUG
            # 121200006845 現況進度追蹤
            # ====================================================
            if order_num == "121200006845":

                print(
                    "\n"
                    "=========================================="
                )

                print(
                    "DEBUG PInformation:",
                    order_num
                )

                print(
                    "group_material_ids:",
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ]
                )

                print(
                    "material_summaries:"
                )

                for x in material_summaries:

                    print({
                        "material_id":
                            x.get(
                                "material_id"
                            ),

                        "status":
                            x.get(
                                "status"
                            ),

                        "has_active_process":
                            x.get(
                                "has_active_process"
                            ),

                        "has_pending_process_step":
                            x.get(
                                "has_pending_process_step"
                            ),

                        "has_entered_process_stage":
                            x.get(
                                "has_entered_process_stage"
                            ),

                        "requires_stockin":
                            x.get(
                                "requires_stockin"
                            ),

                        "completed_qty":
                            x.get(
                                "completed_qty"
                            ),

                        "stockin_qty":
                            x.get(
                                "stockin_qty"
                            ),
                    })

                print(
                    "active_summaries:",
                    [
                        {
                            "material_id":
                                x.get(
                                    "material_id"
                                ),

                            "status":
                                x.get(
                                    "status"
                                ),
                        }
                        for x
                        in active_summaries
                    ]
                )

                print(
                    "final_output_summaries:",
                    [
                        {
                            "material_id":
                                x.get(
                                    "material_id"
                                ),

                            "status":
                                x.get(
                                    "status"
                                ),
                        }
                        for x
                        in final_output_summaries
                    ]
                )

                print(
                    "status_source:",
                    [
                        {
                            "material_id":
                                x.get(
                                    "material_id"
                                ),

                            "status":
                                x.get(
                                    "status"
                                ),

                            "active":
                                x.get(
                                    "has_active_process"
                                ),
                        }
                        for x
                        in status_source
                    ]
                )

                print(
                    "batch_statuses:",
                    batch_statuses
                )

                print(
                    "=========================================="
                    "\n"
                )
            #

            # ====================================================
            # 8-3. 整單狀態
            # ====================================================

            if batch_statuses:

                order_status = min(
                    batch_statuses
                )

            else:

                order_status = to_int(
                    getattr(
                        representative,
                        "show2_ok",
                        0
                    ),
                    0
                )


            # ----------------------------------------------------
            # 真正還在領料的 batch
            # ----------------------------------------------------

            prepare_statuses = [
                to_int(
                    item.get(
                        "status"
                    ),
                    2
                )

                for item
                in status_source

                if bool(
                    item.get(
                        "is_still_prepare_stage",
                        False
                    )
                )
            ]


            if prepare_statuses:

                order_status = min(
                    order_status,
                    min(
                        prepare_statuses
                    )
                )


            # ----------------------------------------------------
            # 真正已進加工流程，且有下一道工序
            # ----------------------------------------------------
            '''
            if any(
                (
                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    and

                    bool(
                        item.get(
                            "has_entered_process_stage",
                            False
                        )
                    )
                )

                for item
                in status_source
            ):

                if not any(
                    bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    for item
                    in status_source
                ):

                    order_status = min(
                        order_status,
                        3
                    )
            '''
            #
            # ----------------------------------------------------
            # 真正已進加工流程，且仍有待加工工序
            #
            # 注意：
            # status == 4 已代表目前有 active Process，
            # 不可再被 pending 工序壓回 status=3。
            # ----------------------------------------------------

            has_order_active = any(
                to_int(
                    item.get(
                        "status"
                    ),
                    0
                ) == 4

                for item
                in status_source
            )


            has_order_pending = any(
                (
                    bool(
                        item.get(
                            "has_pending_process_step",
                            False
                        )
                    )

                    and

                    bool(
                        item.get(
                            "has_entered_process_stage",
                            False
                        )
                    )
                )

                for item
                in status_source
            )


            if (
                has_order_pending
                and
                not has_order_active
            ):

                order_status = min(
                    order_status,
                    3
                )
            #

            # ====================================================
            # 入庫安全判斷
            # ====================================================

            if (
                total_completed > 0
                and
                total_stockin < total_completed
                and
                order_status >= 6
            ):

                if 7 in batch_statuses:

                    order_status = 7

                else:

                    order_status = 6


            # ====================================================
            # 全部 batch 入庫完成
            # ====================================================

            all_batches_stockin_done = bool(
                status_source
            ) and all(
                (
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    ) > 0

                    and

                    to_int(
                        item.get(
                            "stockin_qty"
                        ),
                        0
                    )
                    >=
                    to_int(
                        item.get(
                            "completed_qty"
                        ),
                        0
                    )

                    and

                    not bool(
                        item.get(
                            "has_active_process",
                            False
                        )
                    )

                    and

                    not bool(
                        item.get(
                            "has_waiting_send",
                            False
                        )
                    )

                    and

                    not (
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )

                        and

                        bool(
                            item.get(
                                "has_entered_process_stage",
                                False
                            )
                        )
                    )

                    and

                    to_int(
                        item.get(
                            "status"
                        ),
                        0
                    ) >= 6
                )

                for item
                in (
                    final_output_summaries
                    if final_output_summaries
                    else status_source
                )
            )


            if all_batches_stockin_done:

                order_status = 8


            # ====================================================
            # 單一 material 差異
            # ====================================================

            is_single_material_order = (
                len(
                    group_materials
                )
                ==
                1
            )


            # 20260819：
            # 多 material，但只有一個最終入庫 material，
            # 視為單一產出鏈。
            is_single_output_chain = (
                len(
                    final_output_summaries
                )
                ==
                1
            )


            #accounted_total = (
            #    total_stockin
            #    +
            #    total_scrap
            #)
            #
            accounted_total = (
                total_stockin
                +
                total_scrap
                +
                total_external_scrap
            )
            #

            unexplained_difference = 0


            if (
                is_single_material_order
                and
                req_qty > 0
            ):

                unexplained_difference = max(
                    0,
                    req_qty
                    -
                    accounted_total
                )


            # ====================================================
            # show3
            # ====================================================

            if (
                order_status >= 6
                and
                total_completed > 0
            ):

                # 20260819：
                # 多 material 串接工序、只有一個最終入庫 material。
                # 顯示訂單總量，但不把前段工序 completed 重複相加。
                if (
                    not is_single_material_order
                    and
                    is_single_output_chain
                    and
                    req_qty > 0
                ):

                    show3_text = (
                        f"已入庫 {total_stockin}"
                        f" / 已完成 {total_completed}"
                        f" / 訂單 {req_qty}"
                    )

                    if total_scrap > 0:

                        show3_text += (
                            f" / 廢品 {total_scrap}"
                        )


                elif (
                    is_single_material_order
                    and
                    req_qty > 0
                ):

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 訂單 {req_qty}"
                        )


                        if unexplained_difference > 0:

                            show3_text += (
                                f"（差異 "
                                f"{unexplained_difference}）"
                            )


                    elif unexplained_difference > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                            f" / 訂單 {req_qty}"
                            f"（差異 "
                            f"{unexplained_difference}）"
                        )


                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


                else:

                    if total_scrap > 0:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 廢品 {total_scrap}"
                            f" / 已完成 {total_completed}"
                        )

                    else:

                        show3_text = (
                            f"已入庫 {total_stockin}"
                            f" / 已完成 {total_completed}"
                        )


            elif (
                order_status == 5
                and
                total_completed > 0
            ):

                show3_text = (
                    f"已完成 {total_completed}"
                    f" / 等待送出"
                )


            # ----------------------------------------------------
            # 真正領料階段才不顯示加工名稱
            # ----------------------------------------------------

            elif order_status <= 2:

                show3_text = ""


            elif (
                order_status <= 4
                and
                total_completed > 0
                and
                req_qty > 0
            ):

                remaining_qty = max(
                    0,
                    req_qty
                    -
                    total_completed
                    -
                    total_scrap
                )


                show3_text = (
                    f"已入庫 {total_stockin}"
                    f" / 已完成 {total_completed}"
                    f" / 訂單 {req_qty}"
                )


                if total_scrap > 0:

                    show3_text += (
                        f" / 廢品 {total_scrap}"
                    )


                if remaining_qty > 0:

                    show3_text += (
                        f"（待加工 "
                        f"{remaining_qty}）"
                    )

            #
            else:

                show3_text = (
                    current_process_comment
                    or ""
                )

                if total_external_scrap > 0:

                    if show3_text:

                        show3_text += (
                            f" / 外部加工廢品 "
                            f"{total_external_scrap}"
                        )

                    else:

                        show3_text = (
                            f"外部加工廢品 "
                            f"{total_external_scrap}"
                        )
            #


            # ====================================================
            # 領料中人員
            # ====================================================

            display_open_emp_id = ""

            if order_status == 1:

                for item in material_summaries:

                    if (
                        to_int(
                            item.get(
                                "status"
                            ),
                            -1
                        )
                        != 1
                    ):
                        continue


                    m = item[
                        "material"
                    ]


                    display_open_emp_id = (
                        safe_str(
                            getattr(
                                m,
                                "isOpenEmpId",
                                ""
                            )
                        ).strip()
                    )


                    if display_open_emp_id:
                        break


            # ====================================================
            # 現況數量
            # ====================================================

            if total_stockin > 0:

                display_delivery_qty = (
                    total_stockin
                )


            elif total_completed > 0:

                display_delivery_qty = (
                    total_completed
                )


            else:

                display_delivery_qty = (
                    to_int(
                        getattr(
                            representative,
                            "delivery_qty",
                            0
                        ),
                        0
                    )
                )

            #
            # ====================================================
            # DEBUG：確認 API 最後真正回傳什麼
            # ====================================================
            if order_num == "121200006845":

                print(
                    "FINAL DEBUG:",
                    order_num,
                    "order_status=",
                    order_status,
                    "show2_ok=",
                    status_text(
                        order_status
                    )
                )
            #

            # ====================================================
            # 回傳
            # ====================================================

            result = {

                "id":
                    to_int(
                        representative.id,
                        0
                    ),

                "order_num":
                    order_num,

                "material_num":
                    safe_str(
                        representative.material_num
                    ),

                "isTakeOk":
                    any(
                        bool(
                            getattr(
                                m,
                                "isTakeOk",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "isShow":
                    any(
                        bool(
                            getattr(
                                m,
                                "isShow",
                                False
                            )
                        )
                        for m
                        in group_materials
                    ),

                "is_copied_from_id":
                    getattr(
                        representative,
                        "is_copied_from_id",
                        None
                    ),

                "whichStation":
                    to_int(
                        getattr(
                            representative,
                            "whichStation",
                            0
                        ),
                        0
                    ),

                "req_qty":
                    req_qty,

                "delivery_date":
                    getattr(
                        representative,
                        "material_delivery_date",
                        None
                    ),

                "delivery_qty":
                    display_delivery_qty,

                "comment":
                    safe_str(
                        representative.material_comment
                    ).strip(),

                "show1_ok":
                    station_from_status(
                        order_status
                    ),

                "show2_ok":
                    status_text(
                        order_status
                    ),

                "show3_ok":
                    show3_text,

                "isOpenEmpId":
                    display_open_emp_id,

                "total_process_records":
                    total_process_records,

                "material_count":
                    len(
                        group_materials
                    ),

                "effective_material_count":
                    len(
                        status_source
                    ),

                "material_ids":
                    [
                        to_int(
                            m.id,
                            0
                        )
                        for m
                        in group_materials
                    ],

                "completed_total":
                    total_completed,

                "stockin_total":
                    total_stockin,

                "scrap_total":
                    total_scrap,

                "accounted_total":
                    accounted_total,

                "unexplained_difference":
                    unexplained_difference,

                "remaining_stockin_qty":
                    max(
                        0,
                        total_completed
                        -
                        total_stockin
                    ),

                "remaining_process_qty":
                    max(
                        0,
                        req_qty
                        -
                        total_completed
                        -
                        total_scrap
                    )
                    if req_qty > 0
                    else 0,

                "order_status_code":
                    order_status,

                "all_batches_stockin_done":
                    all_batches_stockin_done,

                "has_pending_process_step":
                    any(
                        bool(
                            item.get(
                                "has_pending_process_step",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),

                "has_waiting_send":
                    any(
                        bool(
                            item.get(
                                "has_waiting_send",
                                False
                            )
                        )
                        for item
                        in status_source
                    ),
            }


            results.append(
                result
            )


        # ========================================================
        # 9. 排序
        # ========================================================

        results.sort(
            key=lambda x: (

                (
                    to_int(
                        x.get(
                            "total_process_records"
                        ),
                        0
                    )
                    ==
                    0
                ),

                safe_str(
                    x.get(
                        "order_num"
                    )
                ),
            )
        )


        # ========================================================
        # 10. 不限制筆數
        # ========================================================

        total = len(
            results
        )

        page_results = (
            results
        )


        print(
            "listInformationsP:",
            "order total=",
            total,
            "return=",
            len(
                page_results
            )
        )


        return jsonify({
            "status": True,
            "total": total,
            "informations": page_results,
        })


    except Exception as e:

        print(
            "listInformationsP ERROR:",
            repr(e)
        )

        traceback.print_exc()

        return jsonify({
            "status": False,
            "total": 0,
            "message": str(e),
            "informations": [],
        }), 500


    finally:

        s.close()


# 20260813版
@listTableP.route("/listInformationsPFiltered", methods=["POST"])
def list_informations_p_filtered():
    print("listInformationsPFiltered....")

    payload = request.get_json(silent=True) or {}
    start_date = (payload.get("start_date") or "").strip()
    end_date   = (payload.get("end_date") or "").strip()
    order_nums = payload.get("order_nums") or []
    order_wildcard = (payload.get("order_wildcard") or "").strip()
    unfinished_only = bool(payload.get("unfinished_only", False))
    limit = int(payload.get("limit") or 2000)

    s = Session()
    try:
        # ✅ 同工單去重：只留每個 order_num 最大 id 的那筆
        latest_id_sq = (
            s.query(func.max(P_Material.id).label("id"))
             .group_by(P_Material.order_num)
             .subquery()
        )

        q = s.query(P_Material).filter(P_Material.id.in_(latest_id_sq))

        # ✅ 日期範圍
        # 你 DB 欄位是 material_delivery_date（date/datetime）
        # 這裡用字串 YYYY-MM-DD 轉 date
        def _to_date(x):
            try:
                return datetime.datetime.strptime(x, "%Y-%m-%d").date()
            except Exception:
                return None

        sd = _to_date(start_date) if start_date else None
        ed = _to_date(end_date) if end_date else None
        if sd and ed:
            q = q.filter(P_Material.material_delivery_date >= sd)\
                 .filter(P_Material.material_delivery_date <= ed)

        # ✅ 工單清單（多選優先）
        if isinstance(order_nums, list) and len(order_nums) > 0:
            q = q.filter(P_Material.order_num.in_(order_nums))
        else:
            # ✅ 萬用字元：* ? → LIKE
            if order_wildcard:
                def wildcard_to_like(p: str) -> str:
                    esc = "\\"
                    p = p.replace(esc, esc + esc)
                    p = p.replace("%", esc + "%").replace("_", esc + "_")
                    p = p.replace("*", "%").replace("?", "_")
                    return p

                like_pat = wildcard_to_like(order_wildcard)
                q = q.filter(P_Material.order_num.like(like_pat, escape="\\"))

        # ✅ 入庫總數（p_product）
        stockin_sq = (
            s.query(
                P_Product.material_id.label("mid"),
                func.coalesce(func.sum(P_Product.allOk_qty), 0).label("stockin_total")
            )
            .group_by(P_Product.material_id)
            .subquery()
        )

        q = q.outerjoin(stockin_sq, stockin_sq.c.mid == P_Material.id)

        # ✅ 只顯示未完成（入庫量 < 訂單量）
        if unfinished_only:
            q = q.filter(func.coalesce(stockin_sq.c.stockin_total, 0) < func.coalesce(P_Material.material_qty, 0))

        # ✅ 上限
        q = q.order_by(P_Material.order_num).limit(limit)

        rows = q.all()

        # ===== 以下：維持原 listInformationsP 的回傳格式（只針對 rows 迭代）=====
        _results = []
        return_value = True
        str1 = ['領料站', '加工站', '成品站']
        str2 = ['未領料', '領料中', '領料已完成', '等待加工作業', '加工作業進行中', '加工作業已完成', '等待入庫作業', '入庫進行中', '入庫完成']

        # part map（你原本那套 그대로）
        def norm_code(x: str) -> str:
            return (x or "").strip().upper().replace(" ", "")

        def alias_code(x: str) -> str:
            x = norm_code(x)
            m = re.match(r'^(B\d{3})[A-Z]*-(\d+)$', x)
            if not m:
                return x
            return f"{m.group(1)}-{m.group(2)}"

        part_info_map = {}
        for p in s.query(P_Part).all():
            code = norm_code(p.part_code or "")
            if not code:
                continue
            info = {"comment": (p.part_comment or "").strip(),
                    "process_step_code": int(p.process_step_code or 0)}
            part_info_map[code] = info
            part_info_map.setdefault(alias_code(code), info)

        def _to_int(v, default=0):
            try:
                if v is None:
                    return default
                return int(v)
            except Exception:
                return default

        for record in rows:
            assemble_records = record._assemble
            process_records = record._process
            #total_process_records = len([p for p in process_records if (p.material_id == record.id and p.has_started == 1 and (p.begin_time or '') != '')])
            # 20260813版
            # ------------------------------------------------------------
            # Information「詳情」只要曾經有有效 Process 紀錄就應可查看。
            #
            # 不可限制 has_started == 1，
            # 因為加工完成後 has_started 會變 False。
            # ------------------------------------------------------------
            total_process_records = len([
                p
                for p in process_records
                if (
                    int(p.material_id or 0)
                    ==
                    int(record.id or 0)
                    and
                    str(
                        p.begin_time or ''
                    ).strip() != ''
                )
            ])
            #

            cleaned_comment = (record.material_comment or "").strip()

            raw = getattr(record, "show2_ok", None)
            try:
                num = int(raw)
            except Exception:
                num = -1

            if 0 <= num < len(str2):
                temp_show2_ok_str = str2[num]
            elif 1 <= num <= len(str2):
                temp_show2_ok_str = str2[num - 1]
            else:
                temp_show2_ok_str = f"未知狀態({raw})"

            if num == 1:
                user = s.query(User).filter_by(emp_id=record.isOpenEmpId).first()
                if user and getattr(user, "emp_name", None):
                    temp_show2_ok_str += f"({user.emp_name})"

            # show3_ok（最小 seq 的工序 comment）
            show_comment = ""
            try:
                show3_ok_val = int(record.show3_ok or 0)
            except Exception:
                show3_ok_val = 0

            if record.isBom or (not record.isBom and record.isTakeOk and record.isShow):
                if record._assemble:
                    valid_assembles = [
                        a for a in record._assemble
                        if (a.work_num not in (None, '', '0') and a.seq_num is not None and str(a.seq_num).isdigit())
                    ]
                    if valid_assembles:
                        min_a = min(valid_assembles, key=lambda a: int(a.seq_num))
                        key = norm_code((min_a.work_num or "").strip())
                        part_info = part_info_map.get(key) or part_info_map.get(alias_code(key))
                        show_comment = (part_info.get("comment", "") if part_info else "")

            # stockin_total
            stockin_total = (
                s.query(func.coalesce(func.sum(P_Product.allOk_qty), 0))
                 .filter(P_Product.material_id == record.id)
                 .scalar()
            ) or 0

            net_good_qty = 0
            for a in assemble_records:
                net_good_qty = max(net_good_qty, _to_int(getattr(a, "must_receive_end_qty", 0), 0))
                if net_good_qty == 0:
                    net_good_qty = max(net_good_qty, _to_int(getattr(a, "total_ask_qty_end", 0), 0))

            delivery_qty = int(stockin_total) if int(stockin_total) > 0 else (net_good_qty if net_good_qty > 0 else _to_int(record.delivery_qty, 0))

            _results.append({
                'id': record.id,
                'order_num': record.order_num,
                'material_num': record.material_num,
                'isTakeOk': record.isTakeOk,
                'whichStation': record.whichStation,
                'req_qty': record.material_qty,
                'delivery_date': record.material_delivery_date,
                'delivery_qty': delivery_qty,
                'comment': cleaned_comment,
                'show1_ok': str1[int(record.show1_ok) - 1] if str(record.show1_ok).isdigit() and 1 <= int(record.show1_ok) <= len(str1) else '',
                'show2_ok': temp_show2_ok_str,
                'show3_ok': show_comment,
                'isOpenEmpId': record.isOpenEmpId,
                'total_process_records': total_process_records,
            })

        if len(_results) == 0:
            return_value = False

        return jsonify({'status': return_value, 'informations': _results})

    finally:
        s.close()


# 20260823版
# 20260822版
@listTableP.route("/listMaterialsP", methods=['GET'])
def list_materials_p():
    print("listMaterialsP....")

    s = Session()
    try:
        return_value = True
        _results = []

        rows = (
            s.query(
                P_Material.id,
                P_Material.order_num,
                P_Material.material_num,
                P_Material.material_qty,
                P_Material.delivery_qty,
                P_Material.total_delivery_qty,
                P_Material.input_disable,
                P_Material.material_date,
                P_Material.material_delivery_date,
                P_Material.shortage_note,
                P_Material.material_comment,

                P_Material.isOpen,
                P_Material.isOpenEmpId,
                P_Material.hasStarted,
                P_Material.startStatus,

                P_Material.isBom,
                P_Material.isTakeOk,
                P_Material.isBatchFeeding,
                P_Material.isShow,
                P_Material.whichStation,
                P_Material.show1_ok,
                P_Material.show2_ok,
                P_Material.show3_ok,
                P_Material.Incoming0_Abnormal,
                P_Material.is_copied_from_id,
            )
            .filter(P_Material.move_by_process_type == 4)
            .filter(P_Material.isShow.is_(False))
            .all()
        )

        '''
        print("len:", len(rows))

        for row in rows:
            cleaned_comment = (row.material_comment or '').strip()

            _object = {
                'id': row.id,
                'order_num': row.order_num,                         # 訂單編號
                'material_num': row.material_num,                   # 物料編號
                'req_qty': row.material_qty,                        # 需求數量(訂單數量)
                'delivery_qty': row.delivery_qty,                   # 備料數量
                'total_delivery_qty': row.total_delivery_qty,       # 應備數量
                'input_disable': row.input_disable,
                'date': row.material_date,                          # 建立日期
                'delivery_date': row.material_delivery_date,        # 交期
                'shortage_note': row.shortage_note,                 # 缺料註記
                'comment': cleaned_comment,                         # 說明

                'isOpen': row.isOpen,
                'isOpenEmpId': row.isOpenEmpId,
                'hasStarted': row.hasStarted,
                'startStatus': row.startStatus,

                'isBom': row.isBom,

                'isTakeOk': row.isTakeOk,
                'isBatchFeeding': row.isBatchFeeding,
                'isShow': row.isShow,
                'whichStation': row.whichStation,
                'show1_ok': row.show1_ok,
                'show2_ok': row.show2_ok,
                'show3_ok': row.show3_ok,
                'Incoming0_Abnormal': (row.Incoming0_Abnormal == ''),
                'Incoming0_Abnormal_message': row.Incoming0_Abnormal,
                'is_copied': bool(row.is_copied_from_id and row.is_copied_from_id > 0),
            }

            _results.append(_object)
        '''
        # 20260822版
        print("len:", len(rows))

        for row in rows:
            '''
            # ========================================================
            # 20260822
            # 同訂單「前後段加工」交棒限制
            #
            # 有 BOM 的後段加工 Material，
            # 必須等前一道加工：
            #
            #   1. 已完成
            #   2. 已從 PEnd 按送出
            #   3. 沒有進 Warehouse
            #   4. 前一道本身為不入庫工序
            #
            # 才允許出現在 PMaterial。
            #
            # 例如：
            #
            # 888800006241
            #
            # material A
            #   seq=50
            #   B100-03
            #   isBom=False
            #   isStockIn=False
            #
            #       ↓ PBegin
            #       ↓ PEnd
            #       ↓ 按送出
            #
            # material B
            #   seq=60
            #   B108-26
            #   isBom=True
            #
            # 此時才可在 PMaterial 顯示。
            # ========================================================

            if bool(
                getattr(
                    row,
                    "isBom",
                    False
                )
            ):

                if not previous_process_handoff_done(
                    s,
                    row
                ):
                    continue
            '''
            #
            # ========================================================
            # 20260823
            # 不論有沒有 BOM，
            # 只要同 order_num 存在前一道較小 seq 工序，
            # 就必須等前一道 PEnd 完成並送出後才放行。
            #
            # 第一段工序沒有前一道，
            # previous_process_handoff_done() 會直接回 True。
            # ========================================================

            if not previous_process_handoff_done(
                s,
                row
            ):
                continue
            #

            cleaned_comment = (
                row.material_comment
                or ''
            ).strip()

            _object = {
                'id': row.id,
                'order_num': row.order_num,                         # 訂單編號
                'material_num': row.material_num,                   # 物料編號
                'req_qty': row.material_qty,                        # 需求數量(訂單數量)
                'delivery_qty': row.delivery_qty,                   # 備料數量
                'total_delivery_qty': row.total_delivery_qty,       # 應備數量
                'input_disable': row.input_disable,
                'date': row.material_date,                          # 建立日期
                'delivery_date': row.material_delivery_date,        # 交期
                'shortage_note': row.shortage_note,                 # 缺料註記
                'comment': cleaned_comment,                         # 說明

                'isOpen': row.isOpen,
                'isOpenEmpId': row.isOpenEmpId,
                'hasStarted': row.hasStarted,
                'startStatus': row.startStatus,

                'isBom': row.isBom,

                'isTakeOk': row.isTakeOk,
                'isBatchFeeding': row.isBatchFeeding,
                'isShow': row.isShow,
                'whichStation': row.whichStation,
                'show1_ok': row.show1_ok,
                'show2_ok': row.show2_ok,
                'show3_ok': row.show3_ok,
                'Incoming0_Abnormal': (row.Incoming0_Abnormal == ''),
                'Incoming0_Abnormal_message': row.Incoming0_Abnormal,
                'is_copied': bool(row.is_copied_from_id and row.is_copied_from_id > 0),
            }

            _results.append(_object)
        #

        temp_len = len(_results)
        print("listMaterialsP, 總數: ", temp_len)

        if temp_len == 0:
            return_value = False

        # 根據 order_num 升序，再根據 isTakeOk 排序（True 會排前面）
        _results.sort(key=lambda x: (x['order_num'] or '', not bool(x['isTakeOk'])))

        return jsonify({
            'status': return_value,
            'materials': _results
        })

    except Exception as e:
        #import traceback
        print("listMaterialsP ERROR:", repr(e))
        traceback.print_exc()
        try:
            current_app.logger.exception("listMaterialsP failed")
        except Exception:
            pass
        return jsonify({
            'status': False,
            'materials': []
        }), 200

    finally:
        s.close()


