from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from database.tables import Session
from database.p_tables import P_Material, P_Assemble, P_Process, P_Part, P_AbnormalCause

from sqlalchemy import and_, or_, not_, func, tuple_, literal, false, cast, case, Integer
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm import selectinload, load_only

from collections import defaultdict

from datetime import datetime, timezone, timedelta
from datetime import datetime as dt, time

from zoneinfo import ZoneInfo

getTableP = Blueprint('getTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


# ------------------------------------------------------------------


def need_more_p_process_qty(k1: int, a1: int, t1: int, must_qty: int, s=None):
    #print("need_more_process_qty()...")

    """
    回傳 (is_insufficient, process_total)
    is_insufficient: True 表示加總 < must_qty；False 表示 >= must_qty
    process_total  : 依條件加總後的數量（int）
    """
    # 允許外部傳入 session；若沒傳就自行建立並在結尾關閉

    #print(k1, t1, must_qty)

    close_after = False
    if s is None:
        from database.tables import Session  # 若你的檔名不同請調整
        s = Session()
        close_after = True

    try:
        # end_time 欄位在你的 schema 是 String(30)，因此除了 not NULL，也一併排除空字串
        total = (
            s.query(func.coalesce(func.sum(P_Process.process_work_time_qty), 0))
             .filter(P_Process.material_id == k1)
             .filter(P_Process.assemble_id == a1)
             .filter(P_Process.process_type == t1)
             .filter(P_Process.has_started.is_(True))
             .filter(P_Process.end_time.isnot(None))
             .filter(P_Process.end_time != '')
             .scalar()
        ) or 0

        total = int(total)
        #print("total, must_qty:", total, must_qty)
        return (total < int(must_qty), total)
    finally:
        if close_after:
            s.close()


# ------------------------------------------------------------------


@getTableP.route("/getMaterialsAndAssemblesByUserP", methods=['POST'])
def get_materials_and_assembles_by_user_p():
    print("getMaterialsAndAssemblesByUserP....")

    request_data = request.get_json() or {}
    _user_id = (request_data.get('user_id') or '').strip()

    str2 = ['未領料', '領料中', '領料完成', '等待加工作業', '加工作業進行中', '等待入庫作業', '入庫進行中', '入庫完成']

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def get_str2_status(show2_ok):
        try:
            n = int(show2_ok or 0)
        except Exception:
            n = 0
        if 0 <= n < len(str2):
            return str2[n]
        return str2[0]

    def norm_end_time(x):
        if x is None:
            return None
        if isinstance(x, str):
            x = x.strip()
            if x == "" or x == "0000-00-00 00:00:00":
                return None
            return x
        return x

    def to_bool01(v):
        try:
            return int(v or 0) == 1
        except Exception:
            return bool(v) is True

    def to_int(v, default=0):
        try:
            if v is None:
                return default
            if isinstance(v, bool):
                return int(v)
            s1 = str(v).strip()
            if s1 == "":
                return default
            return int(float(s1))
        except Exception:
            return default

    def priority_key(row):
        end_dis = to_int(row.get('input_end_disable'), 0)
        abn_dis = to_int(row.get('input_abnormal_disable'), 0)
        return (end_dis, abn_dis)

    s = Session()

    try:
        _results = []
        return_value = True

        part_info_map = {}

        for p in s.query(P_Part).all():
            code = (p.part_code or '').strip()
            if not code:
                continue

            part_info_map[code] = {
                'comment': (p.part_comment or '').strip(),
                'process_step_code': int(p.process_step_code or 0)
            }

        materials = (
            s.query(P_Material)
            .filter(P_Material.move_by_process_type == 4)
            .filter(P_Material.isShow.is_(True))
            .filter(P_Material.isTakeOk.is_(True))

            # 第 4 項：後端先限制加工線狀態
            .filter(P_Material.show1_ok == 2)
            .filter(P_Material.show2_ok.in_([3, 4, 5]))

            .all()
        )

        material_ids_all = [m.id for m in materials]

        if not material_ids_all:
            return jsonify({
                'status': False,
                'materials_and_assembles_by_user': [],
                'active_counts_all': {},
                'active_user_ids_all': {},
            })

        active_process_rows = (
            s.query(P_Process)
            .join(
                P_Assemble,
                and_(
                    P_Assemble.id == P_Process.assemble_id,
                    P_Assemble.material_id == P_Process.material_id,
                )
            )
            .filter(P_Process.material_id.in_(material_ids_all))
            .filter(
                or_(
                    P_Process.user_id == _user_id,
                    P_Process.user_id.like(f"{_user_id} %")
                )
            )
            .filter(P_Process.has_started.is_(True))
            .filter(P_Process.begin_time.isnot(None))
            .filter(P_Process.begin_time != '')
            .filter(or_(P_Process.end_time.is_(None), P_Process.end_time == ''))

            # 第 5 項：active 也要排除已送出 / 已進入入庫端
            .filter(or_(
                P_Assemble.isAssembleStationShow.is_(False),
                P_Assemble.isAssembleStationShow == 0,
                P_Assemble.isAssembleStationShow.is_(None),
            ))
            .filter(or_(
                P_Assemble.isWarehouseStationShow.is_(False),
                P_Assemble.isWarehouseStationShow == 0,
                P_Assemble.isWarehouseStationShow.is_(None),
            ))

            .all()
        )

        active_process_map = {}

        for p in active_process_rows:
            key = (
                int(p.material_id or 0),
                int(p.assemble_id or 0)
            )

            if key not in active_process_map or int(p.id) > int(active_process_map[key].id):
                active_process_map[key] = p

        finished_process_rows = (
            s.query(P_Process)
            .join(
                P_Assemble,
                and_(
                    P_Assemble.id == P_Process.assemble_id,
                    P_Assemble.material_id == P_Process.material_id,
                )
            )
            .filter(P_Process.material_id.in_(material_ids_all))
            .filter(
                or_(
                    P_Process.user_id == _user_id,
                    P_Process.user_id.like(f"{_user_id} %")
                )
            )
            .filter(P_Process.has_started.is_(True))
            .filter(P_Process.end_time.isnot(None))
            .filter(P_Process.end_time != '')

            # 第 5 項：已送出到待入庫 / 已進入入庫端，不帶進 ProcessEnd
            .filter(or_(
                P_Assemble.isAssembleStationShow.is_(False),
                P_Assemble.isAssembleStationShow == 0,
                P_Assemble.isAssembleStationShow.is_(None),
            ))
            .filter(or_(
                P_Assemble.isWarehouseStationShow.is_(False),
                P_Assemble.isWarehouseStationShow == 0,
                P_Assemble.isWarehouseStationShow.is_(None),
            ))

            # 只抓「已完工等待送出」
            .filter(P_Assemble.process_step_code == 0)

            .all()
        )

        finished_process_map = {}

        for p in finished_process_rows:
            key = (
                int(p.material_id or 0),
                int(p.assemble_id or 0)
            )

            if key not in finished_process_map or int(p.id) > int(finished_process_map[key].id):
                finished_process_map[key] = p

        counts_by_type = {}
        user_ids_by_type = {}

        min_seqnum_assemble_id_by_material = {}

        for material_record in materials:
            best = None
            best_seq = None

            for a in material_record._assemble:
                step = to_int(a.process_step_code, 0)

                if step == 0:
                    continue

                seq = to_int(a.seq_num, 0)

                if best is None or seq < best_seq:
                    best = a
                    best_seq = seq

            if best is not None:
                min_seqnum_assemble_id_by_material[int(material_record.id)] = int(best.id)

        index = 0

        for material_record in materials:
            for assemble_record in material_record._assemble:

                key = (
                    int(material_record.id or 0),
                    int(assemble_record.id or 0),
                )

                active_log = active_process_map.get(key)
                finished_log = finished_process_map.get(key)

                # 第 5 項：主迴圈再次嚴格排除
                already_sent_to_warehouse = (
                    to_bool01(assemble_record.isAssembleStationShow)
                    or to_bool01(assemble_record.isWarehouseStationShow)
                )

                if already_sent_to_warehouse:
                    continue

                if not active_log and not finished_log:
                    continue

                display_log = active_log or finished_log

                if not display_log:
                    continue

                display_user_id = safe_str(getattr(display_log, "user_id", "")).strip()

                if not display_user_id:
                    continue

                if display_user_id != _user_id and not display_user_id.startswith(f"{_user_id} "):
                    continue

                work_num_clean = (assemble_record.work_num or '').strip()
                part_info = part_info_map.get(work_num_clean)

                if not part_info:
                    print(
                        "skip: p_part not found",
                        "material_id:", material_record.id,
                        "assemble_id:", assemble_record.id,
                        "work_num:", work_num_clean
                    )
                    continue

                show_comment = part_info['comment']
                show_code = int(part_info['process_step_code'] or 0)

                work_num = safe_str(assemble_record.work_num)
                code = work_num[1:] if len(work_num) >= 2 else work_num

                keep_id = min_seqnum_assemble_id_by_material.get(int(assemble_record.material_id))
                step_enable = (int(assemble_record.id) == int(keep_id or 0))

                temp_show2_ok = to_int(material_record.show2_ok, 0)
                temp_assemble_show2_ok = to_int(assemble_record.show2_ok, 0)

                temp_assemble_process_str = get_str2_status(material_record.show2_ok)

                if temp_show2_ok == 1 or temp_assemble_show2_ok == 1:
                    temp_assemble_process_str += (material_record.shortage_note or '')

                cleaned_comment = material_record.material_comment.strip() if material_record.material_comment else ''

                try:
                    ok, process_total = need_more_p_process_qty(
                        k1=assemble_record.material_id,
                        a1=assemble_record.id,
                        t1=int(display_log.process_type or show_code or 0),
                        must_qty=assemble_record.must_receive_end_qty,
                        s=s
                    )
                except Exception as e:
                    print("need_more_p_process_qty failed:", repr(e))
                    process_total = 0

                _end_time = norm_end_time(getattr(display_log, "end_time", None))

                end_report_done = bool(_end_time is not None and not already_sent_to_warehouse)

                user_is_show_last_time = _end_time is not None
                user_last_time = getattr(display_log, "str_elapsedActive_time", "") if user_is_show_last_time else ""

                index += 1

                _object = {
                    'index': index,

                    'id': material_record.id,
                    'order_num': material_record.order_num,
                    'material_num': material_record.material_num,
                    'req_qty': material_record.material_qty,
                    'delivery_date': material_record.material_delivery_date,
                    'delivery_qty': material_record.delivery_qty,
                    'total_assemble_qty': material_record.total_assemble_qty,
                    'comment': cleaned_comment,

                    'assemble_id': assemble_record.id,
                    'ask_qty': assemble_record.ask_qty,
                    'assemble_work': show_comment,
                    'assemble_process': '' if (temp_show2_ok > 2 and not step_enable) else temp_assemble_process_str,
                    'assemble_process_num': temp_show2_ok,
                    'total_ask_qty_end': assemble_record.total_ask_qty_end,
                    'process_step_code': assemble_record.process_step_code,
                    'must_receive_end_qty': assemble_record.must_receive_end_qty,
                    'receive_qty': assemble_record.completed_qty,
                    'abnormal_qty': assemble_record.abnormal_qty,
                    'total_completed_qty': f"({assemble_record.total_completed_qty})",
                    'total_completed_qty_num': process_total,

                    'process_id': display_log.id,
                    'process_user_id': display_user_id,
                    'user_id': display_user_id,
                    'show_name': display_user_id,

                    'process_type': int(display_log.process_type or 0),
                    'process_has_started': bool(display_log.has_started),
                    'process_begin_time': display_log.begin_time,
                    'process_end_time': display_log.end_time,
                    'process_is_pause': bool(display_log.is_pause),
                    'process_elapsed_time': int(display_log.elapsedActive_time or 0),

                    'elapsed_time': int(display_log.elapsedActive_time or 0),
                    'elapsedActive_time': int(display_log.elapsedActive_time or 0),
                    'str_elapsedActive_time': display_log.str_elapsedActive_time,

                    'whichStation': material_record.whichStation,
                    'isAssembleAlarm': material_record.isAssembleAlarm,
                    'isAssembleFirstAlarm': assemble_record.isAssembleFirstAlarm,
                    'isAssembleFirstAlarm_qty': assemble_record.isAssembleFirstAlarm_qty,
                    'alarm_enable': assemble_record.alarm_enable,

                    'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                    'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                    'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                    'isLackMaterial': material_record.isLackMaterial,
                    'shortage_note': material_record.shortage_note,

                    'isAssembleStationShow': bool(assemble_record.isAssembleStationShow),
                    'db_isAssembleStationShow': bool(assemble_record.isAssembleStationShow),
                    'isWarehouseStationShow': bool(assemble_record.isWarehouseStationShow),
                    'db_isWarehouseStationShow': bool(assemble_record.isWarehouseStationShow),

                    'end_report_done': end_report_done,

                    'currentStartTime': assemble_record.currentStartTime,

                    'input_end_disable': assemble_record.input_end_disable,
                    'input_abnormal_disable': assemble_record.input_abnormal_disable,
                    'process_step_enable': step_enable,

                    'tooltipVisible': False,
                    'abnormal_tooltipVisible': False,

                    'code': code,
                    'isShowLastTime': user_is_show_last_time,
                    'last_time': user_last_time,
                    'assemble_count': len(material_record._assemble),

                    'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    'isStockInDone': bool(assemble_record.isStockIn),

                    'is_copied_from_id': assemble_record.is_copied_from_id,
                    'create_at': assemble_record.create_at,
                }

                _results.append(_object)

        record_sum = (
            s.query(
                P_Assemble.material_id,
                func.coalesce(func.sum(cast(P_Assemble.completed_qty, Integer)), 0).label("sum_completed_qty")
            )
            .filter(P_Assemble.isAssembleStationShow == 1)
            .group_by(P_Assemble.material_id)
            .order_by(P_Assemble.material_id)
            .all()
        )

        sum_map = {int(material_id): int(total or 0) for material_id, total in record_sum}

        for r in _results:
            mid = int(r['id'])
            r['material_completed_sum'] = sum_map.get(mid, 0)

        user_filtered_results = []

        for row in _results:
            row_user_id = str(row.get("process_user_id") or "").strip()

            if not row_user_id:
                continue

            if row_user_id != _user_id and not row_user_id.startswith(f"{_user_id} "):
                continue

            user_filtered_results.append(row)

        _results = user_filtered_results

        _results.sort(key=lambda x: x.get('id') or 0)
        _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)
        _results.sort(key=priority_key)

        if len(_results) == 0:
            return_value = False

        print("getMaterialsAndAssemblesByUserP result count:", len(_results))

        return jsonify({
            'status': return_value,
            'materials_and_assembles_by_user': _results,
            'active_counts_all': counts_by_type,
            'active_user_ids_all': user_ids_by_type,
        })

    except Exception as e:
        s.rollback()
        print("getMaterialsAndAssemblesByUserP ERROR:", repr(e))
        logger.exception("getMaterialsAndAssemblesByUserP failed")
        return jsonify({
            'status': False,
            'message': str(e),
            'materials_and_assembles_by_user': [],
            'active_counts_all': {},
            'active_user_ids_all': {},
        }), 500

    finally:
        s.close()

