from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from database.tables import User, Process, Session

from database.p_tables import P_Material, P_Assemble, P_Process, P_Part

from sqlalchemy import and_, or_, not_, func, tuple_, literal, false, cast, case, Integer
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm import selectinload, load_only

from collections import defaultdict

from datetime import datetime, timezone, timedelta
from datetime import datetime as dt, time

from .helper import parse_dt_maybe_aw, fmt_hhmmss, pick_user_list

from zoneinfo import ZoneInfo

getTableP = Blueprint('getTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


TPE = ZoneInfo("Asia/Taipei")


# ------------------------------------------------------------------


# 將 step code 轉成製程代號, 待確認
def map_pt_from_step_code(step_code: int) -> str:
    # 3 => 21（組裝）, 2 => 22（檢驗），其它 => 23（雷射）
    return '21' if step_code == 3 else '22' if step_code == 2 else '23'


def active_count_map_by_material_multi_p(
    s,
    material_ids,
    process_types,
    include_paused=True,
    only_user_id=None,
    has_started=None,
    null_as_not_started=True,
):
    #
    # 回傳格式：
    # {
    #   "21": { "101": 2, "103": 1 },
    #   "22": { "101": 1 },
    #   "23": {}
    # }
    # include_paused: True → 只要未結束就算（包含暫停）
    #                  False → 只算「正在跑」（不含暫停）

    process_types = list(process_types)             # 確保是可迭代序列

    result = {str(pt): {} for pt in process_types}
    #print("active_count_map_by_material_multi_p(), result:", result)

    if not material_ids:
      return result

    q = build_active_process_query_p(
        s, material_ids, process_types,
        include_paused=include_paused,
        only_user_id=only_user_id,
        has_started=has_started,
        null_as_not_started=null_as_not_started,
    )

    rows = q.with_entities(P_Process.process_type, P_Process.material_id).all()

    for pt, mid in rows:
        pt_str, mid_str = str(pt), str(mid)
        result[pt_str][mid_str] = result[pt_str].get(mid_str, 0) + 1

    return result


def active_user_ids_by_material_multi_p(
    s,
    material_ids,
    process_types,
    include_paused=True,
    has_started=None,
    null_as_not_started=True,
    only_user_id=None,
    as_string=False,                # 預設 False（回 list）
    sep=', '
):
    result = {str(pt): {} for pt in process_types}
    #print("active_user_ids_by_material_multi_p(), result", result)

    if not material_ids:
        return result
    #print("active_user_ids_by_material_multi_p()....",only_user_id, include_paused,has_started,)

    q = build_active_process_query_p(
        s, material_ids, process_types,
        include_paused=include_paused,
        only_user_id=only_user_id,
        has_started=has_started,
        null_as_not_started=null_as_not_started,
    )

    rows = q.with_entities(
        P_Process.process_type,
        P_Process.material_id,
        P_Process.user_id
    ).all()
    #print("active_user_ids_by_material_multi_p(), rows:", rows)

    buckets = {}                  # (pt_str, mid_str) -> set(uids)
    for pt, mid, uid in rows:
        if uid is None:
            continue
        k = (str(pt), str(mid))
        buckets.setdefault(k, set()).add(str(uid))

    for (pt_str, mid_str), uids in buckets.items():
        ulist = sorted(uids)
        result[pt_str][mid_str] = sep.join(ulist) if as_string else ulist
    return result


def build_active_process_query_p(
      s,
      material_ids,
      process_types,
      include_paused=True,
      only_user_id=None,              # 可選的使用者過濾
      has_started=None,               # None=不過濾 / True=只要已開始 / False=只要未開始
      null_as_not_started=True,       # False 時才有用；True=把 NULL 視為「未開始」
  ):
      """
      include_paused:
          True  -> 只要未結束就算（含暫停）
          False -> 只算正在跑（不含暫停）
      has_started:
          None  -> 不過濾
          True  -> 只要 has_started=True
          False -> 只要 has_started=False（可選擇是否把 NULL 視為未開始）
      """
      q = (
          s.query(P_Process)
          .filter(P_Process.material_id.in_(material_ids))
          .filter(P_Process.process_type.in_(process_types))
          #.filter(P_Process.end_time.is_(None))   # 只算未結束
          .filter(
              or_(
                  Process.end_time.is_(None),
                  Process.end_time == ''
              )
          )
      )

      if not include_paused:
          q = q.filter(or_(P_Process.is_pause.is_(False), P_Process.is_pause.is_(None)))

      if only_user_id:
          q = q.filter(P_Process.user_id == only_user_id)

      # 處理 has_started 過濾
      if has_started is True:
          q = q.filter(P_Process.has_started.is_(True))
      elif has_started is False:
          if null_as_not_started:
              q = q.filter(or_(P_Process.has_started.is_(False), P_Process.has_started.is_(None)))
          else:
              q = q.filter(P_Process.has_started.is_(False))
      return q


def end_ok_flag_p(s, material_id: int, process_step_code: int) -> bool:

    # 等價於 getEndOkByMaterialIdAndStepCode 的 True/False 判斷，
    # 直接在伺服器內部呼叫，不走 HTTP。

    row = (
        s.query(P_Assemble)
         .filter(P_Assemble.material_id == material_id)
         .filter(P_Assemble.process_step_code == process_step_code)
         .first()
    )
    if not row:
        return False
    return True


# 待確認
def need_more_p_process_qty(k1: int, a1: int, t1: int, must_qty: int, s=None):

    # 回傳 (is_insufficient, process_total)
    # is_insufficient: True 表示加總 < must_qty；False 表示 >= must_qty
    # process_total  : 依條件加總後的數量（int）

    # 允許外部傳入 session；若沒傳就自行建立並在結尾關閉

    #print(k1, t1, must_qty)

    close_after = False
    if s is None:
        #from database.tables import Session  # 若你的檔名不同請調整
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



@getTableP.route("/getProcessesByOrderNumP", methods=['POST'])
def get_processes_by_order_num_p():
    print("getProcessesByOrderNumP....")

    request_data = request.get_json()
    _order_num = request_data['order_num']

    code_to_name = {
        1:  '領料',
        #19: '等待AGV(備料區)',
        #2:  'AGV運行(備料區->組裝區)',
        #23: '雷射',
        #21: '組裝',
        #22: '檢驗',
        #29: '等待AGV(組裝區)',
        #3:  'AGV運行(組裝區->成品區)',
        31: '成品入庫',
        5:  '堆高機運行(領料區->加工區)',
        6:  '堆高機運行(加工區->成品區)',
    }

    _results = []
    s = Session()

    part_info_map = {}
    step_to_part_code_map = {}
    for p in s.query(P_Part).all():
      code = (p.part_code or '').strip()
      if not code:
        continue
      step = int(p.process_step_code or 0)

      part_info_map[code] = {
        'comment': (p.part_comment or '').strip(),
        'process_step_code': step
      }

      # 反查：step_code -> part_code
      # 若同 step_code 有多筆，你可以決定要不要覆蓋
      if step and step not in step_to_part_code_map:
        step_to_part_code_map[step] = code
    # end for_loop

    material = s.query(P_Material).filter(P_Material.order_num == _order_num).first()
    if not material:
      s.close()
      return jsonify(success=False, message="order not found"), 404

    assemble_records = material._assemble

    work_qty = material.total_delivery_qty or 0
    now_tpe_aw = datetime.now(TPE).replace(microsecond=0)

    seq_num = 0
    for record in material._process:
        alarm_proc_record = [a for a in assemble_records if (a.material_id == record.material_id and a.id == record.assemble_id and record.has_started)]

        if alarm_proc_record:
            print("2.alarm_proc_record:", alarm_proc_record[0].process_step_code if alarm_proc_record else None)
        else:
            print("2.alarm_proc_record: None")

        if len(alarm_proc_record) == 1:
            alarm_msg_enable = alarm_proc_record[0].alarm_enable
            alarm_msg_isAssembleFirstAlarm = alarm_proc_record[0].isAssembleFirstAlarm
            if not alarm_msg_enable and not alarm_msg_isAssembleFirstAlarm:
              alarm_msg_string = (alarm_proc_record[0].alarm_message or '').strip()
            else:
              alarm_msg_string = ''

        else:
            alarm_msg_enable = True
            alarm_msg_isAssembleFirstAlarm = True
            alarm_msg_string = ''

            if (
              material.Incoming0_Abnormal != '' and
              record.end_time !='' and
              record.begin_time !='' and
              record.assemble_id==0 and
              record.process_type in [1, 5]
            ):
              alarm_msg_string = material.Incoming0_Abnormal

        # 跳過 begin_time 為 None、空字串、只有空白、或無效預設值的紀錄
        bt = (record.begin_time or "").strip()
        if (not bt or bt == "0000-00-00 00:00:00") and record.process_type not in {5, 6}:
            continue

        seq_num += 1

        status = code_to_name.get(record.process_type, '空白')
        show_code = 0

        if record.assemble_id != 0 and record.process_type not in {1, 5, 6, 31}:
          assm_list = [a for a in assemble_records if (a.material_id == record.material_id and a.id == record.assemble_id)]
          assm = assm_list[0] if assm_list else None

          if assm:
              # ✅ part_info_map 的 key 是 P_Part.part_code（字串，如 'B100-03'），不是 assemble.process_step_code
              key = (assm.work_num or '').strip()   # P_Assemble.work_num 是字串 :contentReference[oaicite:0]{index=0}
              part_info = part_info_map.get(key)

              if part_info:
                  status = part_info['comment']
                  show_code = part_info['process_step_code']
              else:
                  status = key or status   # 找不到就退回顯示 work_num
                  show_code = 0
          else:
              show_code = 0
        # end assemble_id_if

        # ✅ 先取得該筆 process 對應的 assemble（若 assemble_id=0 就是 None）
        assm = None
        if record.assemble_id and int(record.assemble_id) != 0:
            assm = next(
                (a for a in assemble_records
                if a.material_id == record.material_id and a.id == record.assemble_id),
                None
            )

        # 預設空字串
        abnormal_qty = ''
        completed_qty = ''
        # 只有真正加工製程才顯示數量
        if record.process_type not in {1, 5, 6, 31}:
          abnormal_qty = int(getattr(assm, "abnormal_qty", 0) or 0) if assm else 0
          completed_qty = int(getattr(assm, "completed_qty", 0) or 0) if assm else 0

        # ---- 使用者名稱附註（若有） ----
        name_core = (record.user_id or "").lstrip("0")

        if record.process_type in {1, 5, 6, 31}:
            user = s.query(User).filter_by(emp_id=record.user_id).first()
            emp_name = user.emp_name if user and getattr(user, "emp_name", None) else ""
            status = f"{status}({name_core}{emp_name})"

        # ---- 計算時長（非 5/6 流動段才算）----
        temp_period_time = ""
        work_time_str = ""
        single_std_time_str = ""
        #print("record.process_type:", record.process_type)
        if record.process_type not in {5, 6}:
            start_time = parse_dt_maybe_aw(record.begin_time)
            end_time   = parse_dt_maybe_aw(record.end_time)

            if show_code > 1000:
              status = part_info['comment']

            #print("status: ", status)
            single_std_time_str = ""  # 預設空字串

            # 1) 找到對應這筆製程的 part_code
            #    你的邏輯：p_process.process_type == p_part.process_step_code
            #    但 part_info_map 目前是用 part_code 當 key，所以要反查 step_code -> part_code
            step_code = int(record.process_type or 0)

            # 建議你在迴圈外先建一個 step_to_part_code_map（下面有完整寫法）
            part_code = step_to_part_code_map.get(step_code)  # 例如 'B102-1' 或 'B102-01'

            if part_code:
                # 2) 從 part_code 抽出前綴：B102
                #    支援 B102-1 / B102-01 / B102_01 都可
                prefix = str(part_code).strip().split('-', 1)[0].split('_', 1)[0]  # 'B102'

                # 3) 組出欄位名稱：sd_time_B102
                col_name = f"sd_time_{prefix}"

                # 4) 因為你已經確保 material.id == record.material_id（material._process 的關聯）
                #    直接從 material 動態取值
                val = getattr(material, col_name, None)
                single_std_time_str = "" if val in (None, "") else str(val)
            #print("single_std_time_str: ", single_std_time_str)

            if start_time:
                if end_time:
                    # 已結束：用結束時間 - 開始時間
                    total_seconds = int((end_time - start_time).total_seconds())
                else:
                    # 未結束：依目前狀態計算有效作業秒數
                    pause_total = int(record.pause_time or 0)

                    #if getattr(record, "is_pause", False) and record.pause_started_at:
                    if getattr(record, "is_pause", False) and getattr(record, "pause_started_at", None):
                        #ps_aw = attach_tpe(record.pause_started_at)
                        ps_aw = parse_dt_maybe_aw(record.pause_started_at)
                        if ps_aw:
                            #pause_total += max(0, int((now_tpe_aw - ps_aw).total_seconds()))
                            # 若 DB 時間不小心比現在還未來，多餘負值做保護
                            extra_pause = int((now_tpe_aw - ps_aw).total_seconds())
                            pause_total += max(0, extra_pause)
                        # end if
                    # end if

                    # 這裡兩邊皆為 aware
                    total_seconds = int((now_tpe_aw - start_time).total_seconds()) - pause_total

                total_seconds = max(0, total_seconds)
                time_diff_str_format = fmt_hhmmss(total_seconds)

                # 製程 1（領料）顯示 front-end 的 str_elapsedActive_time 優先
                if record.process_type == 1:
                    temp_period_time = record.str_elapsedActive_time or record.period_time or time_diff_str_format
                elif record.process_type == 31:
                    temp_period_time = ""  # 入庫不顯示
                else:
                    # 若 DB 已有 period_time 就沿用；否則用動態計算
                    temp_period_time = record.period_time or time_diff_str_format

                # 分/單件（只對 21/22/23/31 有意義，其它依你原本邏輯空白）
                if show_code > 1000 and work_qty > 0:
                    minutes_total = total_seconds // 60
                    work_time = round(minutes_total / work_qty, 1)
                    work_time_str = str(work_time)
                elif record.process_type == 31:
                    work_time_str = ""
            else:
                # 沒開始時間
                temp_period_time = record.period_time or ""
        # else: 5/6 不計時長

        # ✅ 取得該筆 process 對應的 assemble（同一筆）
        assm = None
        if record.assemble_id and int(record.assemble_id) != 0:
            assm = next((a for a in assemble_records if a.id == record.assemble_id), None)

        # ✅ 規則：
        # - 入庫數量：只有 process_type == 31 才顯示
        # - 廢品數量：若 0 則不顯示（空白）
        abnormal_qty = ''
        completed_qty = ''

        if assm:
            # 廢品：0 -> ''，>0 才顯示
            aq = int(getattr(assm, "abnormal_qty", 0) or 0)
            abnormal_qty = aq if aq > 0 else ''

            # 入庫：只在 31 顯示（你要顯示 0 還是空白？通常 0 也顯示沒意義）
            if record.process_type == 31:
                cq = int(getattr(assm, "completed_qty", 0) or 0)
                completed_qty = cq if cq != 0 else ''   # 若你想 0 也顯示就改成：completed_qty = cq

        _object = {
            'seq_num': seq_num,
            'id': material.id,
            'order_num': material.order_num,
            'process_work_time_qty': (
                record.process_work_time_qty
                if record.process_type not in {19, 29, 2, 3, 5, 6}
                else ''
            ),

            'abnormal_qty': abnormal_qty,
            'completed_qty': completed_qty,

            'sd_time_B100': material.sd_time_B100,
            'sd_time_B102': material.sd_time_B102,
            'sd_time_B103': material.sd_time_B103,
            'sd_time_B107': material.sd_time_B107,
            'sd_time_B108': material.sd_time_B108,
            'user_id': name_core,
            'begin_time': record.begin_time,
            'end_time': record.end_time if record.process_type != 31 else '',
            'period_time': temp_period_time if record.process_type != 1 else (record.str_elapsedActive_time or temp_period_time),
            'work_time': work_time_str if record.process_type != 31 else '',
            'single_std_time': single_std_time_str if record.process_type != 31 else '',
            'process_type': status,

            'normal_type': ' - 異常整修' if (not alarm_msg_enable and not alarm_msg_isAssembleFirstAlarm) else '',
            'user_comment': alarm_msg_string,

            'create_at': record.create_at,
        }
        _results.append(_object)

    s.close()

    # 依 create_at 排序
    _results = sorted(_results, key=lambda x: x['create_at'])
    '''
    # ✅ 追加：同一張加工工單(material_id)的報廢/入庫總數
    def _to_int(v, default=0):
        try:
            if v is None:
                return default
            return int(v)
        except Exception:
            return default

    scrap_qty_total = sum(_to_int(getattr(a, "abnormal_qty", 0), 0) for a in assemble_records if getattr(a, "material_id", None) == material.id)
    stockin_qty_total = sum(_to_int(getattr(a, "completed_qty", 0), 0) for a in assemble_records if getattr(a, "material_id", None) == material.id)
    '''

    #s.close()

    _results = sorted(_results, key=lambda x: x['create_at'])
    return jsonify({
      'processes': _results,
    })


"""
@getTableP.route("/getMaterialsAndAssemblesByUserP", methods=['POST'])
def get_materials_and_assembles_by_user_p():
    print("getMaterialsAndAssemblesByUserP....")

    request_data = request.get_json()
    _user_id = request_data['user_id']

    def get_str2_status(show2_ok):
        try:
            n = int(show2_ok)
        except Exception:
            n = 0
        if 0 <= n < len(str2):
            return str2[n]
        return str2[0]

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def _norm_end_time(x):
        if x is None:
            return None
        if isinstance(x, str):
            x = x.strip()
            if x == "" or x == "0000-00-00 00:00:00":
                return None
            return x
        return x


    str2 = ['未領料', '領料中', '領料完成', '等待加工作業', '加工作業進行中', '等待入庫作業', '入庫進行中', '入庫完成']


    s = Session()

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

    process_types = set()
    for info in part_info_map.values():
        step_code = info.get('process_step_code')
        if not step_code:
            continue
        process_types.add(int(step_code))

    #str2 = ['未領料', '領料中', '領料完成', '等待加工作業', '加工作業進行中', '等待入庫作業', '入庫進行中', '入庫完成']

    _objects = s.query(P_Material).all()
    material_ids_all = [m.id for m in _objects]

    #
    active_process_rows = (
        s.query(P_Process)
        .filter(P_Process.material_id.in_(material_ids_all))
        .filter(P_Process.user_id == _user_id)
        .filter(P_Process.has_started.is_(True))
        .filter(P_Process.begin_time.isnot(None))
        .filter(P_Process.begin_time != '')
        #.filter(P_Process.end_time.is_(None))
        .filter(
            or_(
                Process.end_time.is_(None),
                Process.end_time == ''
            )
        )
        .all()
    )

    active_process_map = {}
    for p in active_process_rows:
        key = (
            int(p.material_id or 0),
            int(p.assemble_id or 0),
            int(p.process_type or 0),
        )
        if key not in active_process_map or int(p.id) > int(active_process_map[key].id):
            active_process_map[key] = p
    #

    counts_by_type = active_count_map_by_material_multi_p(
        s, material_ids_all,
        process_types=process_types,
        include_paused=False,
        only_user_id=_user_id,
        has_started=True,
    )

    user_ids_by_type = active_user_ids_by_material_multi_p(
        s, material_ids_all,
        process_types=process_types,
        include_paused=True,
        only_user_id=_user_id,
        as_string=False,
        has_started=True,
    )

    processed_records = set()

    min_seqnum_assemble_id_by_material = {}
    for material_record in _objects:
        best = None
        best_seq = None
        for a in material_record._assemble:
            step = int(a.process_step_code or 0)
            if step == 0:
                continue
            seq = int(a.seq_num or 0)
            if best is None or seq < best_seq:
                best = a
                best_seq = seq
        if best is not None:
            min_seqnum_assemble_id_by_material[int(material_record.id)] = int(best.id)

    index = 0
    for material_record in _objects:    # for_loop_a
        assemble_records = material_record._assemble
        process_records = material_record._process

        for assemble_record in assemble_records:    # for_loop_b
            user_proc_records = [
                p for p in process_records
                if p.user_id == _user_id and (p.end_time is None or str(p.end_time).strip() != '')
            ]

            if assemble_record.process_step_code == 0 and not assemble_record.isAssembleStationShow:
                continue

            target_pt = assemble_record.process_step_code
            matched_count = 0
            if target_pt is not None:
                target_procs = [
                    p for p in process_records
                    if p.material_id == assemble_record.material_id
                    and p.assemble_id == assemble_record.id
                    and p.process_type == target_pt
                    and p.user_id == _user_id
                    and p.begin_time
                    and (p.end_time is None or str(p.end_time).strip() != '')
                ]
                matched_count = len(target_procs)

            if matched_count == 0 and not assemble_record.isAssembleStationShow:
                continue

            # ✅ 已入庫：End.vue 不顯示
            if bool(assemble_record.isStockIn):
                continue

            work_num_clean = (assemble_record.work_num or '').strip()
            part_info = part_info_map.get(work_num_clean)
            if not part_info:
                continue

            show_comment = part_info['comment']
            show_code = part_info['process_step_code']

            code = assemble_record.work_num[1:]
            format_name = show_comment
            order_num_id = material_record.id
            step_code = assemble_record.process_step_code

            keep_id = min_seqnum_assemble_id_by_material.get(int(assemble_record.material_id))
            step_enable = (step_code == keep_id)

            raw = getattr(material_record, "show2_ok", None)

            num = None
            try:
                num = int(raw)
            except Exception as e:
                print(
                    "❌ show2_ok parse failed",
                    "material_id:", material_record.id,
                    "order_num:", material_record.order_num,
                    "raw show2_ok:", raw,
                    "err:", repr(e),
                )
                num = -1

            print(
                "[DEBUG show2_ok]",
                "material_id:", material_record.id,
                "order_num:", material_record.order_num,
                "show2_ok:", material_record.show2_ok,
                "num:", num,
                "len(str2):", len(str2)
            )

            if 0 <= num < len(str2):
                temp_assemble_process_str = str2[num]
            else:
                print("❌ show2_ok OUT OF RANGE", "num:", num, "len(str2):", len(str2))
                temp_assemble_process_str = f"未知狀態({raw})"

            cleaned_comment = material_record.material_comment.strip() if material_record.material_comment else ''

            num = material_record.show2_ok
            temp_assemble_process_str = get_str2_status(num)

            temp_show2_ok = int(material_record.show2_ok or 0)
            temp_assemble_show2_ok = int(assemble_record.show2_ok or 0)

            if temp_show2_ok == 1 or temp_assemble_show2_ok == 1:
                temp_assemble_process_str = temp_assemble_process_str + (material_record.shortage_note or '')

            index += 1

            work_num = safe_str(assemble_record.work_num)
            code = work_num[1:] if len(work_num) >= 2 else work_num

            pt = show_code
            ok, process_total = need_more_p_process_qty(
                k1=assemble_record.material_id,
                a1=assemble_record.id,
                t1=pt,
                must_qty=assemble_record.must_receive_end_qty,
                s=s
            )

            r = next(
                (
                    p for p in user_proc_records
                    if p.material_id == assemble_record.material_id and p.process_type == pt
                ),
                None
            )

            #
            #def _norm_end_time(x):
            #    if x is None:
            #        return None
            #    if isinstance(x, str):
            #        x = x.strip()
            #        if x == "" or x == "0000-00-00 00:00:00":
            #            return None
            #        return x
            #    return x
            #

            user_receive_qty = int((getattr(r, "process_work_time_qty", 0) or 0))
            _end_time = _norm_end_time(getattr(r, "end_time", None))
            user_is_show_last_time = _end_time is not None
            user_last_time = getattr(r, "str_elapsedActive_time", "") if user_is_show_last_time else ""

            #
            ptype = int(map_pt_from_step_code(int(assemble_record.process_step_code or 0)))
            active_log = active_process_map.get((
                int(material_record.id or 0),
                int(assemble_record.id or 0),
                int(ptype or 0),
            ))

            if not active_log:
                continue
            #

            _object = {
                'index': index,
                'id': material_record.id,
                'order_num': material_record.order_num,
                'material_num': material_record.material_num,
                'req_qty': material_record.material_qty,
                'ask_qty': assemble_record.ask_qty,

                'assemble_work': format_name,
                'assemble_process': '' if (int(num) > 2 and not step_enable) else temp_assemble_process_str,
                'assemble_process_num': int(num),
                'assemble_id': assemble_record.id,

                #
                'process_id': active_log.id,
                'process_has_started': bool(active_log.has_started),
                'process_begin_time': active_log.begin_time,
                'process_is_pause': bool(active_log.is_pause),
                'process_elapsed_time': int(active_log.elapsedActive_time or 0),
                #

                'total_ask_qty_end': assemble_record.total_ask_qty_end,
                'process_step_code': assemble_record.process_step_code,

                'total_completed_qty': f"({assemble_record.total_completed_qty})",
                'total_completed_qty_num': process_total,

                'must_receive_end_qty': assemble_record.must_receive_end_qty,
                'abnormal_qty': assemble_record.abnormal_qty,
                'receive_qty': assemble_record.completed_qty,

                'delivery_date': material_record.material_delivery_date,
                'delivery_qty': material_record.delivery_qty,
                'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

                'total_assemble_qty': material_record.total_assemble_qty,

                'comment': cleaned_comment,
                'isAssembleAlarm': material_record.isAssembleAlarm,

                'isAssembleFirstAlarm': assemble_record.isAssembleFirstAlarm,
                'isAssembleFirstAlarm_qty': assemble_record.isAssembleFirstAlarm_qty,
                'alarm_enable': assemble_record.alarm_enable,

                'whichStation': material_record.whichStation,
                'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                'isLackMaterial': material_record.isLackMaterial,
                'shortage_note': material_record.shortage_note,

                'isAssembleStationShow': bool(assemble_record.isAssembleStationShow == 1),
                'currentStartTime': assemble_record.currentStartTime,
                'tooltipVisible': False,
                'abnormal_tooltipVisible': False,

                'input_end_disable': assemble_record.input_end_disable,
                'input_abnormal_disable': assemble_record.input_abnormal_disable,
                'alarm_enable': assemble_record.alarm_enable,

                'process_step_enable': step_enable,
                'code': code,

                'isShowLastTime': user_is_show_last_time,
                'last_time': user_last_time,

                'assemble_count': len(material_record._assemble),

                # ✅ 保留顯示字串，但另外加 bool 欄位供過濾
                'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                'isStockInDone': bool(assemble_record.isStockIn),

                'is_copied_from_id': assemble_record.is_copied_from_id,
                'create_at': assemble_record.create_at,
            }

            processed_records.add((order_num_id, format_name))
            _results.append(_object)
        # end for_loop_b
    # end for_loop_a
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

    all_zero_by_mid = {}
    for r in _results:
        mid = str(r['id'])
        code = int((r.get('process_step_code') or 0))
        if mid not in all_zero_by_mid:
            all_zero_by_mid[mid] = True
        if code != 0:
            all_zero_by_mid[mid] = False

        for material_id, total in record_sum:
            if r['id'] == material_id:
                r['total_completed_qty_num'] = total

    filtered_results = []
    for row in _results:
        mid = str(row['id'])

        # ✅ 已入庫不顯示
        if bool(row.get('isStockInDone')):
            continue

        if int(row.get('isAssembleStationShow') or 0) == 1 and all_zero_by_mid.get(mid, False):
            filtered_results.append(row)
            continue

        ptype = map_pt_from_step_code(int(row['process_step_code'] or 0))
        ulist = pick_user_list(user_ids_by_type, ptype, mid)
        if _user_id not in ulist:
            continue

        if not end_ok_flag_p(s, material_id=row['id'], process_step_code=int(row['process_step_code'] or 0)):
            continue

        filtered_results.append(row)

    # ✅ 這行原本漏掉了
    _results = filtered_results

    temp_len = len(_results)
    if temp_len == 0:
        return_value = False

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

    _results.sort(key=lambda x: x.get('id') or 0)
    _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

    def priority_key(row):
        end_dis = to_int(row.get('input_end_disable'), 0)
        abn_dis = to_int(row.get('input_abnormal_disable'), 0)
        return (end_dis, abn_dis)

    _results.sort(key=priority_key)

    s.close()

    return jsonify({
        'status': return_value,
        'materials_and_assembles_by_user': _results,
        'active_counts_all': counts_by_type,
        'active_user_ids_all': user_ids_by_type,
    })
"""


"""
@getTableP.route("/getMaterialsAndAssemblesByUserP", methods=['POST'])
def get_materials_and_assembles_by_user_p():
    print("getMaterialsAndAssemblesByUserP....")

    request_data = request.get_json()
    _user_id = request_data['user_id']

    def get_str2_status(show2_ok):
        try:
            n = int(show2_ok)
        except Exception:
            n = 0
        if 0 <= n < len(str2):
            return str2[n]
        return str2[0]

    def safe_str(v, default=''):
        try:
            return '' if v is None else str(v)
        except Exception:
            return default

    def _norm_end_time(x):
        if x is None:
            return None
        if isinstance(x, str):
            x = x.strip()
            if x == "" or x == "0000-00-00 00:00:00":
                return None
            return x
        return x


    str2 = ['未領料', '領料中', '領料完成', '等待加工作業', '加工作業進行中', '等待入庫作業', '入庫進行中', '入庫完成']


    s = Session()

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

    process_types = set()
    for info in part_info_map.values():
        step_code = info.get('process_step_code')
        if not step_code:
            continue
        process_types.add(int(step_code))

    #str2 = ['未領料', '領料中', '領料完成', '等待加工作業', '加工作業進行中', '等待入庫作業', '入庫進行中', '入庫完成']

    _objects = s.query(P_Material).all()
    material_ids_all = [m.id for m in _objects]

    #
    active_process_rows = (
        s.query(P_Process)
        .filter(P_Process.material_id.in_(material_ids_all))
        .filter(P_Process.user_id == _user_id)
        .filter(P_Process.has_started.is_(True))
        .filter(P_Process.begin_time.isnot(None))
        .filter(P_Process.begin_time != '')
        #.filter(P_Process.end_time.is_(None))
        .filter(
            or_(
                Process.end_time.is_(None),
                Process.end_time == ''
            )
        )
        .all()
    )

    active_process_map = {}
    for p in active_process_rows:
        key = (
            int(p.material_id or 0),
            int(p.assemble_id or 0),
            int(p.process_type or 0),
        )
        if key not in active_process_map or int(p.id) > int(active_process_map[key].id):
            active_process_map[key] = p
    #

    counts_by_type = active_count_map_by_material_multi_p(
        s, material_ids_all,
        process_types=process_types,
        include_paused=False,
        only_user_id=_user_id,
        has_started=True,
    )

    user_ids_by_type = active_user_ids_by_material_multi_p(
        s, material_ids_all,
        process_types=process_types,
        include_paused=True,
        only_user_id=_user_id,
        as_string=False,
        has_started=True,
    )

    processed_records = set()

    min_seqnum_assemble_id_by_material = {}
    for material_record in _objects:
        best = None
        best_seq = None
        for a in material_record._assemble:
            step = int(a.process_step_code or 0)
            if step == 0:
                continue
            seq = int(a.seq_num or 0)
            if best is None or seq < best_seq:
                best = a
                best_seq = seq
        if best is not None:
            min_seqnum_assemble_id_by_material[int(material_record.id)] = int(best.id)

    index = 0
    for material_record in _objects:    # for_loop_a
        assemble_records = material_record._assemble
        process_records = material_record._process

        for assemble_record in assemble_records:    # for_loop_b
            user_proc_records = [
                p for p in process_records
                if p.user_id == _user_id and (p.end_time is None or str(p.end_time).strip() != '')
            ]

            if assemble_record.process_step_code == 0 and not assemble_record.isAssembleStationShow:
                continue

            target_pt = assemble_record.process_step_code
            matched_count = 0
            if target_pt is not None:
                target_procs = [
                    p for p in process_records
                    if p.material_id == assemble_record.material_id
                    and p.assemble_id == assemble_record.id
                    and p.process_type == target_pt
                    and p.user_id == _user_id
                    and p.begin_time
                    and (p.end_time is None or str(p.end_time).strip() != '')
                ]
                matched_count = len(target_procs)

            if matched_count == 0 and not assemble_record.isAssembleStationShow:
                continue

            # ✅ 已入庫：End.vue 不顯示
            if bool(assemble_record.isStockIn):
                continue

            work_num_clean = (assemble_record.work_num or '').strip()
            part_info = part_info_map.get(work_num_clean)
            if not part_info:
                continue

            show_comment = part_info['comment']
            show_code = part_info['process_step_code']

            code = assemble_record.work_num[1:]
            format_name = show_comment
            order_num_id = material_record.id
            step_code = assemble_record.process_step_code

            keep_id = min_seqnum_assemble_id_by_material.get(int(assemble_record.material_id))
            step_enable = (step_code == keep_id)

            raw = getattr(material_record, "show2_ok", None)

            num = None
            try:
                num = int(raw)
            except Exception as e:
                print(
                    "❌ show2_ok parse failed",
                    "material_id:", material_record.id,
                    "order_num:", material_record.order_num,
                    "raw show2_ok:", raw,
                    "err:", repr(e),
                )
                num = -1

            print(
                "[DEBUG show2_ok]",
                "material_id:", material_record.id,
                "order_num:", material_record.order_num,
                "show2_ok:", material_record.show2_ok,
                "num:", num,
                "len(str2):", len(str2)
            )

            if 0 <= num < len(str2):
                temp_assemble_process_str = str2[num]
            else:
                print("❌ show2_ok OUT OF RANGE", "num:", num, "len(str2):", len(str2))
                temp_assemble_process_str = f"未知狀態({raw})"

            cleaned_comment = material_record.material_comment.strip() if material_record.material_comment else ''

            num = material_record.show2_ok
            temp_assemble_process_str = get_str2_status(num)

            temp_show2_ok = int(material_record.show2_ok or 0)
            temp_assemble_show2_ok = int(assemble_record.show2_ok or 0)

            if temp_show2_ok == 1 or temp_assemble_show2_ok == 1:
                temp_assemble_process_str = temp_assemble_process_str + (material_record.shortage_note or '')

            index += 1

            work_num = safe_str(assemble_record.work_num)
            code = work_num[1:] if len(work_num) >= 2 else work_num

            pt = show_code
            ok, process_total = need_more_p_process_qty(
                k1=assemble_record.material_id,
                a1=assemble_record.id,
                t1=pt,
                must_qty=assemble_record.must_receive_end_qty,
                s=s
            )

            r = next(
                (
                    p for p in user_proc_records
                    if p.material_id == assemble_record.material_id and p.process_type == pt
                ),
                None
            )

            #
            #def _norm_end_time(x):
            #    if x is None:
            #        return None
            #    if isinstance(x, str):
            #        x = x.strip()
            #        if x == "" or x == "0000-00-00 00:00:00":
            #            return None
            #        return x
            #    return x
            #

            user_receive_qty = int((getattr(r, "process_work_time_qty", 0) or 0))
            _end_time = _norm_end_time(getattr(r, "end_time", None))
            user_is_show_last_time = _end_time is not None
            user_last_time = getattr(r, "str_elapsedActive_time", "") if user_is_show_last_time else ""

            #
            ptype = int(map_pt_from_step_code(int(assemble_record.process_step_code or 0)))
            active_log = active_process_map.get((
                int(material_record.id or 0),
                int(assemble_record.id or 0),
                int(ptype or 0),
            ))

            if not active_log:
                continue
            #

            _object = {
                'index': index,
                'id': material_record.id,
                'order_num': material_record.order_num,
                'material_num': material_record.material_num,
                'req_qty': material_record.material_qty,
                'ask_qty': assemble_record.ask_qty,

                'assemble_work': format_name,
                'assemble_process': '' if (int(num) > 2 and not step_enable) else temp_assemble_process_str,
                'assemble_process_num': int(num),
                'assemble_id': assemble_record.id,

                #
                'process_id': active_log.id,
                'process_has_started': bool(active_log.has_started),
                'process_begin_time': active_log.begin_time,
                'process_is_pause': bool(active_log.is_pause),
                'process_elapsed_time': int(active_log.elapsedActive_time or 0),
                #

                'total_ask_qty_end': assemble_record.total_ask_qty_end,
                'process_step_code': assemble_record.process_step_code,

                'total_completed_qty': f"({assemble_record.total_completed_qty})",
                'total_completed_qty_num': process_total,

                'must_receive_end_qty': assemble_record.must_receive_end_qty,
                'abnormal_qty': assemble_record.abnormal_qty,
                'receive_qty': assemble_record.completed_qty,

                'delivery_date': material_record.material_delivery_date,
                'delivery_qty': material_record.delivery_qty,
                'abnormal_qty': assemble_record.isAssembleFirstAlarm_qty if code == '109' else assemble_record.abnormal_qty,

                'total_assemble_qty': material_record.total_assemble_qty,

                'comment': cleaned_comment,
                'isAssembleAlarm': material_record.isAssembleAlarm,

                'isAssembleFirstAlarm': assemble_record.isAssembleFirstAlarm,
                'isAssembleFirstAlarm_qty': assemble_record.isAssembleFirstAlarm_qty,
                'alarm_enable': assemble_record.alarm_enable,

                'whichStation': material_record.whichStation,
                'isAssembleStation3TakeOk': material_record.isAssembleStation3TakeOk,
                'isAssembleStation2TakeOk': material_record.isAssembleStation2TakeOk,
                'isAssembleStation1TakeOk': material_record.isAssembleStation1TakeOk,
                'isLackMaterial': material_record.isLackMaterial,
                'shortage_note': material_record.shortage_note,

                'isAssembleStationShow': bool(assemble_record.isAssembleStationShow == 1),
                'currentStartTime': assemble_record.currentStartTime,
                'tooltipVisible': False,
                'abnormal_tooltipVisible': False,

                'input_end_disable': assemble_record.input_end_disable,
                'input_abnormal_disable': assemble_record.input_abnormal_disable,
                'alarm_enable': assemble_record.alarm_enable,

                'process_step_enable': step_enable,
                'code': code,

                'isShowLastTime': user_is_show_last_time,
                'last_time': user_last_time,

                'assemble_count': len(material_record._assemble),

                # ✅ 保留顯示字串，但另外加 bool 欄位供過濾
                'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                'isStockInDone': bool(assemble_record.isStockIn),

                'is_copied_from_id': assemble_record.is_copied_from_id,
                'create_at': assemble_record.create_at,
            }

            processed_records.add((order_num_id, format_name))
            _results.append(_object)
        # end for_loop_b
    # end for_loop_a
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

    all_zero_by_mid = {}
    for r in _results:
        mid = str(r['id'])
        code = int((r.get('process_step_code') or 0))
        if mid not in all_zero_by_mid:
            all_zero_by_mid[mid] = True
        if code != 0:
            all_zero_by_mid[mid] = False

        for material_id, total in record_sum:
            if r['id'] == material_id:
                r['total_completed_qty_num'] = total

    filtered_results = []
    for row in _results:
        mid = str(row['id'])

        # ✅ 已入庫不顯示
        if bool(row.get('isStockInDone')):
            continue

        if int(row.get('isAssembleStationShow') or 0) == 1 and all_zero_by_mid.get(mid, False):
            filtered_results.append(row)
            continue

        ptype = map_pt_from_step_code(int(row['process_step_code'] or 0))
        ulist = pick_user_list(user_ids_by_type, ptype, mid)
        if _user_id not in ulist:
            continue

        if not end_ok_flag_p(s, material_id=row['id'], process_step_code=int(row['process_step_code'] or 0)):
            continue

        filtered_results.append(row)

    # ✅ 這行原本漏掉了
    _results = filtered_results

    temp_len = len(_results)
    if temp_len == 0:
        return_value = False

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

    _results.sort(key=lambda x: x.get('id') or 0)
    _results.sort(key=lambda x: x.get('create_at') or datetime.min, reverse=True)

    def priority_key(row):
        end_dis = to_int(row.get('input_end_disable'), 0)
        abn_dis = to_int(row.get('input_abnormal_disable'), 0)
        return (end_dis, abn_dis)

    _results.sort(key=priority_key)

    s.close()

    return jsonify({
        'status': return_value,
        'materials_and_assembles_by_user': _results,
        'active_counts_all': counts_by_type,
        'active_user_ids_all': user_ids_by_type,
    })
"""


@getTableP.route("/getCountMaterialsAndAssemblesByUserP", methods=['POST'])
def get_count_materials_and_assembles_by_user_p():
    print("getCountMaterialsAndAssemblesByUserP....")

    request_data = request.get_json()

    _user_id = request_data['user_id']

    s = Session()

    _objects = s.query(P_Material).all()
    material_ids_all = [m.id for m in _objects]

    counts_by_type = active_count_map_by_material_multi_p(
        s, material_ids_all,
        process_types=(21, 22, 23),
        include_paused=True,
        # only_user_id=None             # 全員
        only_user_id=_user_id,          # 只算該使用者本人（看你要哪種）
        has_started=True,               # 只找 has_started=True
    )

    total_active_records = sum(
        1 for m in counts_by_type.values() for c in m.values() if c > 0
    )
    print("total_active_records:", total_active_records)

    return jsonify({
      'end_count': total_active_records
    })



@getTableP.route("/getBomsP", methods=['POST'])
def get_boms_p():
  print("getBomsP....")

  request_data = request.get_json()
  #_order_num = request_data['order_num']
  _order_num = request_data.get('order_num')
  _id = request_data.get('id')

  return_value = True
  s = Session()

  # 檢查傳入的參數，選擇查詢條件
  material_record = None
  if _order_num is not None:  # 如果傳入了 order_num
    material_record = s.query(P_Material).filter_by(order_num=_order_num).first()
  elif _id is not None:       # 如果傳入了 id
    material_record = s.query(P_Material).filter_by(id=_id).first()

  boms = material_record._bom

  # 將 boms 轉換成字典格式返回，並篩選出 isPickOK 為 False 的項目
  results = [
    {
      'id': bom.id,
      'order_num': material_record.order_num,
      'seq_num': bom.seq_num,           # 項目編號
      'material_num': bom.material_num,     # 物料編號
      'mtl_comment': bom.material_comment,  # 物料說明
      'qty': bom.req_qty,                   # 數量
      'date': material_record.material_date,       # 日期
      'date_alarm': '',
      #'receive': bom.receive,               #領取
      'lack': bom.lack,                     #缺料
      'isPickOK': bom.isPickOK
    }
    for bom in boms if not bom.isPickOK
  ]

  s.close()

  temp_len = len(results)
  print("getBoms, 總數: ", temp_len)
  #print("getBoms: ", results)
  if (temp_len == 0):
    return_value = False

  return jsonify({
    'status': return_value,
    'boms': results
  })



