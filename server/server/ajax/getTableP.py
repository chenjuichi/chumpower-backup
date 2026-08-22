import random

from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import check_password_hash
from database.tables import User, Process, Session

from database.p_tables import P_Material, P_Assemble, P_Process, P_Part, P_Product

from sqlalchemy import and_, or_, not_, func, tuple_, literal, false, cast, case, Integer
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm import selectinload, load_only

from collections import defaultdict

from datetime import datetime, timezone, timedelta
from datetime import datetime as dt, time

from .helper import (
  parse_dt_maybe_aw,
  fmt_hhmmss,
)

from zoneinfo import ZoneInfo

getTableP = Blueprint('getTableP', __name__)

from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


TPE = ZoneInfo("Asia/Taipei")


# ------------------------------------------------------------------


"""
# 將 step code 轉成製程代號, 待確認
def map_pt_from_step_code(step_code: int) -> str:
    # 3 => 21（組裝）, 2 => 22（檢驗），其它 => 23（雷射）
    return '21' if step_code == 3 else '22' if step_code == 2 else '23'
"""


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

"""
def build_active_process_query_p(
      s,
      material_ids,
      process_types,
      include_paused=True,
      only_user_id=None,              # 可選的使用者過濾
      has_started=None,               # None=不過濾 / True=只要已開始 / False=只要未開始
      null_as_not_started=True,       # False 時才有用；True=把 NULL 視為「未開始」
  ):

      # include_paused:
      #     True  -> 只要未結束就算（含暫停）
      #     False -> 只算正在跑（不含暫停）
      # has_started:
      #     None  -> 不過濾
      #     True  -> 只要 has_started=True
      #     False -> 只要 has_started=False（可選擇是否把 NULL 視為未開始）

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
"""


# 20260730版
def build_active_process_query_p(
    s,
    material_ids,
    process_types,
    include_paused=True,
    only_user_id=None,
    has_started=None,
    null_as_not_started=True,
):

    # 加工線 active process 共用查詢。
    #
    # 唯一識別基礎：
    #     material_id
    #     assemble_id
    #     process_type
    #     user_id
    #
    # order_num 不參與 active process 判斷。

    material_ids = [
        int(v)
        for v in (material_ids or [])
        if v is not None
    ]

    process_types = [
        int(v)
        for v in (process_types or [])
        if v is not None
    ]

    q = s.query(P_Process)

    if not material_ids:
        return q.filter(false())

    if not process_types:
        return q.filter(false())

    q = (
        q
        .filter(
            P_Process.material_id.in_(
                material_ids
            )
        )
        .filter(
            P_Process.process_type.in_(
                process_types
            )
        )
        .filter(
            or_(
                P_Process.end_time.is_(None),
                func.trim(
                    P_Process.end_time
                ) == ''
            )
        )
    )

    if not include_paused:
        q = q.filter(
            or_(
                P_Process.is_pause.is_(False),
                P_Process.is_pause.is_(None),
            )
        )

    if only_user_id:
        q = q.filter(
            P_Process.user_id ==
            str(only_user_id).strip()
        )

    if has_started is True:
        q = q.filter(
            P_Process.has_started.is_(True)
        )

    elif has_started is False:
        if null_as_not_started:
            q = q.filter(
                or_(
                    P_Process.has_started.is_(False),
                    P_Process.has_started.is_(None),
                )
            )
        else:
            q = q.filter(
                P_Process.has_started.is_(False)
            )

    return q
#

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

    close_after = False
    if s is None:
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


# 20260813版
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

        '''
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
        '''
        #
        materials = (
            s.query(P_Material)
            .filter(
                P_Material.move_by_process_type == 4
            )
            .filter(
                P_Material.isShow.is_(True)
            )
            .filter(
                P_Material.isTakeOk.is_(True)
            )

            # ------------------------------------------------------------
            # PEnd 不可只依 material.show1_ok / show2_ok 過濾
            #
            # 原因：
            # 部分完成後，例如 120 完成 38，
            # material 可能已因搬運流程變成：
            #
            #   show1_ok = 3
            #   show2_ok = 6
            #   show3_ok = 11
            #
            # 但 p_assemble 的 38 件仍然是合法的「待送出」資料，
            # 必須讓後面的 finished_process_rows 判斷。
            # ------------------------------------------------------------

            .all()
        )
        #

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

        # ------------------------------------------------------------
        # 已全部完工、仍留在加工區，等待送出的資料
        #
        # 注意：
        # 1. 完工後 P_Process.has_started 會變成 False
        # 2. 待送出時 isAssembleStationShow 必須是 True
        # 3. 尚未送至成品區時 isWarehouseStationShow 是 False
        # 4. 待送出資料不應限制只能看到目前員工自己的紀錄
        # ------------------------------------------------------------
        finished_process_rows = (
            s.query(P_Process)
            .join(
                P_Assemble,
                and_(
                    P_Assemble.id ==
                    P_Process.assemble_id,

                    P_Assemble.material_id ==
                    P_Process.material_id,
                )
            )
            .filter(
                P_Process.material_id.in_(
                    material_ids_all
                )
            )

            # 完工後 has_started 已經是 False，
            # 所以這裡不可再限制 has_started=True。
            .filter(
                P_Process.end_time.isnot(None)
            )
            .filter(
                P_Process.end_time != ''
            )

            # 已完成最後一道工序
            .filter(
                P_Assemble.process_step_code == 0
            )

            # 仍留在加工區，等待送出
            .filter(
                P_Assemble
                .isAssembleStationShow
                .is_(True)
            )

            # 尚未送到成品區
            .filter(or_(
                P_Assemble
                .isWarehouseStationShow
                .is_(False),

                P_Assemble
                .isWarehouseStationShow == 0,

                P_Assemble
                .isWarehouseStationShow
                .is_(None),
            ))

            # 加工完成狀態
            .filter(
                P_Assemble.show2_ok == 5
            )

            # 必須有完成數量
            .filter(
                func.coalesce(
                    P_Assemble.completed_qty,
                    0
                ) > 0
            )

            .order_by(
                P_Process.id.desc()
            )
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

                # ------------------------------------------------------------
                # 真正已送出加工區的判斷
                #
                # 待送出：
                #   isAssembleStationShow = True
                #   isWarehouseStationShow = False
                #
                # 已送出：
                #   isWarehouseStationShow = True
                # ------------------------------------------------------------
                already_sent_to_warehouse = (
                    to_bool01(
                        assemble_record
                        .isWarehouseStationShow
                    )
                )

                if already_sent_to_warehouse:
                    continue
                #

                if not active_log and not finished_log:
                    continue

                display_log = active_log or finished_log

                if not display_log:
                    continue

                display_user_id = safe_str(
                    getattr(
                        display_log,
                        "user_id",
                        ""
                    )
                ).strip()

                is_waiting_send = (
                    finished_log is not None
                    and
                    to_int(
                        assemble_record
                        .process_step_code,
                        0
                    ) == 0
                    and
                    to_bool01(
                        assemble_record
                        .isAssembleStationShow
                    )
                    and
                    not to_bool01(
                        assemble_record
                        .isWarehouseStationShow
                    )
                    and
                    to_int(
                        assemble_record.show2_ok,
                        0
                    ) == 5
                )

                # 進行中的資料只顯示目前員工
                if not is_waiting_send:
                    if not display_user_id:
                        continue

                    if (
                        display_user_id != _user_id
                        and
                        not display_user_id.startswith(
                            f"{_user_id} "
                        )
                    ):
                        continue
                # end if not is_waiting_send:

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

                # end try_except

                # ------------------------------------------------------------
                # 加工線「已完成總數量」統一來源
                #
                # 優先順序：
                # 1. total_completed_qty：正式累計欄位
                # 2. total_ask_qty_end：舊版加工線累計欄位
                # 3. completed_qty：本次完成量
                # 4. process_total：歷史 P_Process 加總結果
                #
                # 注意：
                # 完工後 P_Process.has_started 會被設為 False，
                # 因此 process_total 可能重新查到 0，不能作為第一順位。
                # ------------------------------------------------------------
                total_completed_qty_value = to_int(
                    getattr(
                        assemble_record,
                        "total_completed_qty",
                        0
                    ),
                    0
                )

                if total_completed_qty_value <= 0:
                    total_completed_qty_value = to_int(
                        getattr(
                            assemble_record,
                            "total_ask_qty_end",
                            0
                        ),
                        0
                    )

                if total_completed_qty_value <= 0:
                    total_completed_qty_value = to_int(
                        getattr(
                            assemble_record,
                            "completed_qty",
                            0
                        ),
                        0
                    )

                if total_completed_qty_value <= 0:
                    total_completed_qty_value = to_int(
                        process_total,
                        0
                    )

                _end_time = norm_end_time(
                    getattr(display_log, "end_time", None)
                )

                is_waiting_send = (
                    to_int(assemble_record.process_step_code, 0) == 0
                    and
                    to_bool01(assemble_record.isAssembleStationShow)
                    and
                    not to_bool01(assemble_record.isWarehouseStationShow)
                    and
                    to_int(assemble_record.show2_ok, 0) == 5
                )

                # 20260813版
                # ------------------------------------------------------------
                # PEnd「應完成總數量」顯示規則
                #
                # 情況 A：
                # 第一批完成，例如 120 -> 完成 38
                #
                #   完成列是原始列：
                #       is_copied_from_id = NULL
                #
                #   待送出時顯示原始總量：
                #       120
                #
                #
                # 情況 B：
                # 第二批以後，例如：
                #
                #   原始 120
                #   第一批完成 38
                #   第二批完成 20
                #   累計完成 58
                #   尚餘 62
                #
                #   此時待送出列本身是 copy row，
                #   且它已經有下一個剩餘 child row。
                #
                #   PEnd 應顯示 child.must_receive_end_qty = 62
                # ------------------------------------------------------------

                next_remaining_row = None

                if is_waiting_send:
                    next_remaining_row = (
                        s.query(P_Assemble)
                        .filter(
                            P_Assemble.material_id ==
                            material_record.id
                        )
                        .filter(
                            P_Assemble.is_copied_from_id ==
                            assemble_record.id
                        )
                        .filter(
                            P_Assemble.process_step_code > 0
                        )
                        .filter(
                            func.coalesce(
                                P_Assemble.completed_qty,
                                0
                            ) == 0
                        )
                        .filter(
                            func.coalesce(
                                P_Assemble.must_receive_end_qty,
                                0
                            ) > 0
                        )
                        .order_by(
                            P_Assemble.id.desc()
                        )
                        .first()
                    )


                if is_waiting_send:

                    # 第一批完成：
                    # root row，仍顯示原始工單總量 120
                    if not assemble_record.is_copied_from_id:

                        display_must_receive_end_qty = (
                            to_int(
                                material_record.material_qty,
                                0
                            )
                        )

                    # 第二批以後：
                    # 若已經產生下一個剩餘 row，
                    # 顯示真正剩餘數量，例如 62
                    elif next_remaining_row:

                        display_must_receive_end_qty = (
                            to_int(
                                next_remaining_row
                                .must_receive_end_qty,
                                0
                            )
                        )

                    else:
                        # 沒有下一筆代表已經沒有剩餘
                        display_must_receive_end_qty = (
                            to_int(
                                assemble_record
                                .must_receive_end_qty,
                                0
                            )
                        )

                else:
                    # 正在加工中的 row
                    display_must_receive_end_qty = (
                        to_int(
                            assemble_record
                            .must_receive_end_qty,
                            0
                        )
                    )
                #

                end_report_done = bool(is_waiting_send)

                user_is_show_last_time = _end_time is not None
                user_last_time = getattr(display_log, "str_elapsedActive_time", "") if user_is_show_last_time else ""
                '''
                # 20260813版 add
                # ------------------------------------------------------------
                # PEnd 顯示 / 計算用應完成數量
                #
                # 1. 原始加工列：
                #    應完成總量 = material.material_qty
                #    例如 120
                #
                # 2. 部分完成後建立的剩餘列：
                #    應完成總量 = 該剩餘列 must_receive_end_qty
                #    例如 82
                #
                # 3. 已完成待送出列：
                #    顯示原始工單總量，例如 120
                # ------------------------------------------------------------
                is_difference_row = (
                    to_int(
                        getattr(
                            assemble_record,
                            'is_copied_from_id',
                            0
                        ),
                        0
                    ) > 0
                    and
                    to_int(
                        assemble_record.total_completed_qty,
                        0
                    ) > 0
                )

                display_must_receive_end_qty = (
                    to_int(
                        material_record.material_qty,
                        0
                    )
                    if (
                        is_waiting_send
                        or not is_difference_row
                    )
                    else
                    to_int(
                        assemble_record.must_receive_end_qty,
                        0
                    )
                )
                '''
                #

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
                    #'ask_qty': assemble_record.ask_qty,
                    #
                    'ask_qty': max(
                        to_int(
                            assemble_record.ask_qty,
                            0
                        ),
                        to_int(
                            assemble_record.total_ask_qty,
                            0
                        ),
                        to_int(
                            material_record.material_qty,
                            0
                        ),
                    ),
                    #
                    'assemble_work': show_comment,
                    'assemble_process': '' if (temp_show2_ok > 2 and not step_enable) else temp_assemble_process_str,
                    'assemble_process_num': temp_show2_ok,
                    'total_ask_qty_end': assemble_record.total_ask_qty_end,
                    'process_step_code': assemble_record.process_step_code,
                    'must_receive_end_qty': assemble_record.must_receive_end_qty,
                    # 20260813版 add
                    'must_receive_end_qty':
                        assemble_record.must_receive_end_qty,

                    'display_must_receive_end_qty':
                        display_must_receive_end_qty,
                    #
                    #'receive_qty': assemble_record.completed_qty,
                    #'abnormal_qty': assemble_record.abnormal_qty,
                    #'total_completed_qty': f"({assemble_record.total_completed_qty})",
                    #'total_completed_qty_num': process_total,

                    'original_must_receive_end_qty':
                    to_int(
                        getattr(
                            assemble_record,
                            'original_must_receive_end_qty',
                            0
                        ),
                        0
                    ),

                    #
                    # 本次完成數量
                    'receive_qty':
                        to_int(
                            assemble_record.completed_qty,
                            0
                        ),

                    'abnormal_qty':
                        to_int(
                            assemble_record.abnormal_qty,
                            0
                        ),

                    # 已完成總數量：顯示文字
                    'total_completed_qty':
                        f"({total_completed_qty_value})",

                    # 已完成總數量：純數值
                    'total_completed_qty_num':
                        total_completed_qty_value,
                    #

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

                    #'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    #'isStockInDone': bool(assemble_record.isStockIn),
                    # 20260813版
                    # ------------------------------------------------------------
                    # [不入庫] 只適用於真正已完成、且明確不入庫的完成列。
                    #
                    # 尚在加工中的剩餘列：
                    #   process_step_code > 0
                    #   isStockIn = False
                    #
                    # 這是正常狀態，不可顯示 [不入庫]。
                    # ------------------------------------------------------------
                    'isStockIn':
                        (
                            ' [不入庫]'
                            if (
                                to_int(
                                    assemble_record.process_step_code,
                                    0
                                ) == 0
                                and
                                not bool(
                                    assemble_record.isStockIn
                                )
                            )
                            else ''
                        ),

                    'isStockInDone':
                        bool(
                            assemble_record.isStockIn
                        ),
                    #

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
            row_user_id = str(
                row.get("process_user_id") or "").strip()

            '''
            is_waiting_send = (
                to_int(row.get("process_step_code"), 0) == 0
                and
                to_bool01(row.get("isAssembleStationShow"))
                and
                not to_bool01(row.get("isWarehouseStationShow"))
                and
                to_int(row.get("assemble_process_num"), 0) == 5
            )
            '''
            # 20260813版
            is_waiting_send = (
                to_int(
                    row.get("process_step_code"),
                    0
                ) == 0
                and
                to_bool01(
                    row.get("isAssembleStationShow")
                )
                and
                not to_bool01(
                    row.get("isWarehouseStationShow")
                )
                and
                bool(
                    row.get("end_report_done")
                )
            )
            #

            # 待送出資料讓所有登入 PEnd 的員工看到
            if is_waiting_send:
                user_filtered_results.append(row)
                continue

            # 加工中的資料仍只顯示目前員工
            if not row_user_id:
                continue

            if (
                row_user_id != _user_id
                and
                not row_user_id.startswith(
                    f"{_user_id} "
                )
            ):
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


"""
# 20260813版
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
            #if record.process_type == 31:
            #    cq = int(getattr(assm, "completed_qty", 0) or 0)
            #    completed_qty = cq if cq != 0 else ''   # 若你想 0 也顯示就改成：completed_qty = cq

            # 20260813版
            # ------------------------------------------------------------
            # 入庫數量：
            #
            # process_type=31 時，
            # 必須使用 P_Process.process_work_time_qty。
            #
            # 不可使用 assm.completed_qty，
            # 因為一次勾選多批入庫時：
            #
            #   assemble 68 = 38
            #   assemble 70 = 50
            #   assemble 71 = 32
            #
            # 但同一次入庫已合併成：
            #
            #   P_Process(type=31)
            #   process_work_time_qty = 120
            #
            # 若再取 assm.completed_qty，
            # 就只會顯示最後綁定 assemble 的 32。
            # ------------------------------------------------------------
            if record.process_type == 31:

                cq = int(
                    getattr(
                        record,
                        "process_work_time_qty",
                        0
                    )
                    or 0
                )

                completed_qty = (
                    cq
                    if cq > 0
                    else ''
                )
            #

        _object = {
            'seq_num': seq_num,
            'id': material.id,
            'order_num': material.order_num,

            # 20260813版 add
            # --------------------------------------------------------
            # PInformation 排序用
            # --------------------------------------------------------
            'process_id':
                int(record.id or 0),

            'assemble_id':
                int(record.assemble_id or 0),

            'process_type_code':
                int(record.process_type or 0),
            #

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
    #_results = sorted(_results, key=lambda x: x['create_at'])
    #
    #_results = sorted(_results, key=lambda x: x['create_at'])
    # 20260813版
    # ============================================================
    # PInformation 詳情排序
    #
    # 目的：
    #
    # 同一個 assemble_id 的加工與送出搬運必須排在一起：
    #
    #   加工
    #   → 堆高機(加工區->成品區)
    #
    # 再進下一個 assemble_id。
    # ============================================================

    def process_sort_key(row):

        process_type = int(
            row.get(
                'process_type_code',
                0
            ) or 0
        )

        assemble_id = int(
            row.get(
                'assemble_id',
                0
            ) or 0
        )

        process_id = int(
            row.get(
                'process_id',
                0
            ) or 0
        )

        create_at = row.get(
            'create_at'
        )

        # --------------------------------------------------------
        # assemble_id > 0：
        # 分批加工相關 Process。
        #
        # 同一 assemble：
        #   加工先
        #   type=6 搬運後
        # --------------------------------------------------------
        if assemble_id > 0:

            if process_type == 6:
                sub_order = 90

            elif process_type == 31:
                sub_order = 100

            else:
                # 一般加工製程先排
                sub_order = 10

            return (
                1,
                assemble_id,
                sub_order,
                process_id,
            )

        # --------------------------------------------------------
        # assemble_id=0：
        # 例如領料、領料區->加工區等前置流程。
        # 保持時間排序。
        # --------------------------------------------------------
        return (
            0,
            create_at or datetime.min,
            process_id,
            0,
        )


    _results.sort(
        key=process_sort_key
    )


    # 重新編號
    for idx, row in enumerate(
        _results,
        start=1
    ):
        row['seq_num'] = idx
    #

    return jsonify({
      'processes': _results,
    })
"""

"""
# 20260815版
@getTableP.route(
    "/getProcessesByOrderNumP",
    methods=["POST"]
)
def get_processes_by_order_num_p():

    print("getProcessesByOrderNumP....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    order_num = str(
        request_data.get("order_num")
        or ""
    ).strip()

    if not order_num:
        return jsonify({
            "success": False,
            "message": "order_num is required",
            "processes": [],
        }), 400

    # ============================================================
    # 加工線特殊 Process Type
    #
    # 注意：
    #
    #   1 = 領料
    #   5 = 堆高機 領料區 -> 加工區
    #   6 = 堆高機 加工區 -> 成品區
    #
    # 其它：
    #
    #   100 / 99 / 98 / ... / 31 / ...
    #
    # 都可能是 P_Part.process_step_code。
    #
    # 特別注意：
    #
    #   process_type = 31
    #
    # 在加工線是：
    #
    #   B107-02
    #   主軸配件-分爪片
    #
    # 不是成品入庫。
    #
    # 真正入庫資料來源：
    #
    #   P_Product
    # ============================================================

    SPECIAL_PROCESS_TYPES = {
        1,
        5,
        6,
    }

    SPECIAL_PROCESS_NAMES = {
        1: "領料",
        5: "堆高機運行(領料區->加工區)",
        6: "堆高機運行(加工區->成品區)",
    }

    s = Session()

    try:

        # ========================================================
        # 共用小工具
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

        # ========================================================
        # employee 顯示名稱
        #
        # P_Process.user_id 有兩種資料：
        #
        #   01004005
        #
        # 或：
        #
        #   01004005 陳世玟
        #
        # ========================================================

        user_name_cache = {}

        def get_process_user_display(
            raw_user_id
        ):

            raw = safe_str(
                raw_user_id
            ).strip()

            if not raw:
                return ""

            # DB 已經帶姓名：
            #
            # 01004005 陳世玟
            if " " in raw:

                parts = raw.split(
                    None,
                    1
                )

                emp_id = (
                    parts[0]
                    if parts
                    else ""
                )

                emp_name = (
                    parts[1]
                    if len(parts) > 1
                    else ""
                )

                #return (
                #    f"{emp_id.lstrip('0')}"
                #    f" {emp_name}"
                #).strip()
                # 20260815版
                return (
                    f"{emp_id.lstrip('0')}"
                    f"{emp_name}"
                ).strip()
                #

            emp_id = raw

            if emp_id in user_name_cache:

                emp_name = (
                    user_name_cache[
                        emp_id
                    ]
                )

            else:

                user = (
                    s.query(User)
                    .filter_by(
                        emp_id=emp_id
                    )
                    .first()
                )

                emp_name = (
                    safe_str(
                        getattr(
                            user,
                            "emp_name",
                            ""
                        )
                    ).strip()
                    if user
                    else ""
                )

                user_name_cache[
                    emp_id
                ] = emp_name

            return (
                f"{emp_id.lstrip('0')}"
                f"{emp_name}"
            ).strip()

        # ========================================================
        # 1. 建立 P_Part mapping
        #
        # A:
        #   work_num
        #       -> P_Part
        #
        # B:
        #   process_step_code
        #       -> P_Part
        #
        # 例如：
        #
        #   B100-03 -> 98
        #   B107-02 -> 31
        # ========================================================

        part_by_code = {}
        part_by_step = {}

        part_rows = (
            s.query(P_Part)
            .all()
        )

        for p in part_rows:

            part_code = safe_str(
                p.part_code
            ).strip()

            step_code = to_int(
                p.process_step_code,
                0
            )

            if not part_code:
                continue

            info = {
                "part_code":
                    part_code,

                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    step_code,
            }

            part_by_code[
                part_code
            ] = info

            if step_code > 0:

                # 若 step_code 有重複，
                # 保留第一筆即可。
                part_by_step.setdefault(
                    step_code,
                    info
                )

        # ========================================================
        # 2. 同 order_num 所有 P_Material
        #
        # 舊版：
        #
        #   .first()
        #
        # 會造成：
        #
        # 121200006445
        #
        #   material_id = 16
        #   material_id = 50
        #
        # 只讀其中一筆。
        # ========================================================

        materials = (
            s.query(P_Material)
            .filter(
                P_Material.order_num
                ==
                order_num
            )
            .order_by(
                P_Material.id.asc()
            )
            .all()
        )

        if not materials:

            return jsonify({
                "success": False,
                "message":
                    "order not found",
                "processes": [],
            }), 404

        material_ids = [
            int(m.id)
            for m in materials
        ]

        # ========================================================
        # 3. 一次把真正入庫資料查出來
        # ========================================================

        product_rows = (
            s.query(P_Product)
            .filter(
                P_Product.material_id
                .in_(
                    material_ids
                )
            )
            .order_by(
                P_Product.create_at.asc(),
                P_Product.id.asc(),
            )
            .all()
        )

        products_by_material = {}

        for product in product_rows:

            mid = to_int(
                product.material_id,
                0
            )

            products_by_material.setdefault(
                mid,
                []
            ).append(
                product
            )

        # ========================================================
        # 4. 建立 Process Map
        #
        # 後面 P_Product.process_id 若需要找到原 Process，
        # 可直接使用。
        # ========================================================

        all_process_ids = [
            to_int(
                p.process_id,
                0
            )
            for p in product_rows
            if to_int(
                p.process_id,
                0
            ) > 0
        ]

        linked_process_map = {}

        if all_process_ids:

            linked_process_rows = (
                s.query(P_Process)
                .filter(
                    P_Process.id.in_(
                        all_process_ids
                    )
                )
                .all()
            )

            linked_process_map = {
                int(p.id): p
                for p
                in linked_process_rows
            }

        # ========================================================
        # 5. 最終回傳內容
        # ========================================================

        results = []

        now_tpe_aw = (
            datetime.now(TPE)
            .replace(
                microsecond=0
            )
        )

        # ========================================================
        # 6. 每個 material 分別處理
        # ========================================================

        for material in materials:

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

            # ----------------------------------------------------
            # assemble map
            # ----------------------------------------------------

            assemble_map = {
                to_int(a.id, 0): a
                for a
                in assemble_records
                if to_int(
                    a.id,
                    0
                ) > 0
            }

            # ----------------------------------------------------
            # 加工作業數量
            #
            # 原本用 total_delivery_qty。
            # 沒值時 fallback material_qty。
            # ----------------------------------------------------

            work_qty = to_int(
                getattr(
                    material,
                    "total_delivery_qty",
                    0
                ),
                0
            )

            if work_qty <= 0:

                work_qty = to_int(
                    getattr(
                        material,
                        "material_qty",
                        0
                    ),
                    0
                )

            # ----------------------------------------------------
            # Process 先按建立順序整理
            # ----------------------------------------------------

            process_records.sort(
                key=lambda p: (
                    getattr(
                        p,
                        "create_at",
                        None
                    )
                    or datetime.min,
                    to_int(
                        p.id,
                        0
                    )
                )
            )

            # ====================================================
            # A. P_Process
            # ====================================================

            for record in process_records:

                process_id = to_int(
                    record.id,
                    0
                )

                process_type = to_int(
                    record.process_type,
                    0
                )

                assemble_id = to_int(
                    record.assemble_id,
                    0
                )

                # 20260818版
                # ============================================================
                # 判斷是否為「真正搬運 Process」
                #
                # 注意：
                # process_type = 5 有兩種用途：
                #
                #   assemble_id = 0
                #       → 堆高機運行(領料區->加工區)
                #
                #   assemble_id > 0
                #       → 真正加工工序
                #         例如 B108-26 的 process_step_code = 5
                #
                # 所以不能再單獨用 process_type == 5 判定搬運。
                # ============================================================
                is_transport_process = (
                    process_type == 1
                    or process_type == 6
                    or (
                        process_type == 5
                        and assemble_id == 0
                    )
                )
                #

                # ------------------------------------------------
                # 舊 5 / 6 搬運紀錄可能沒有 begin_time。
                #
                # 一般加工若完全沒有 begin_time，
                # 代表沒有真正開始過，不顯示。
                # ------------------------------------------------

                begin_raw = safe_str(
                    record.begin_time
                ).strip()

                '''
                if (
                    (
                        not begin_raw
                        or
                        begin_raw
                        ==
                        "0000-00-00 00:00:00"
                    )
                    and
                    process_type
                    not in {
                        5,
                        6,
                    }
                ):
                    continue
                '''
                #
                if (
                    (
                        not begin_raw
                        or
                        begin_raw
                        ==
                        "0000-00-00 00:00:00"
                    )
                    and
                    not is_transport_process
                ):
                    continue
                #

                # ------------------------------------------------
                # 找對應 P_Assemble
                # ------------------------------------------------

                assm = None

                if assemble_id > 0:

                    assm = (
                        assemble_map.get(
                            assemble_id
                        )
                    )

                    # 防止異常關聯
                    if (
                        assm is not None
                        and
                        to_int(
                            assm.material_id,
                            0
                        )
                        !=
                        material_id
                    ):
                        assm = None

                # =================================================
                # Process 顯示名稱
                # =================================================

                status = ""

                part_info = None

                # -------------------------------------------------
                # 領料 / 搬運
                # -------------------------------------------------

                if (
                    process_type
                    in SPECIAL_PROCESS_TYPES
                ):

                    status = (
                        SPECIAL_PROCESS_NAMES
                        .get(
                            process_type,
                            f"Process({process_type})"
                        )
                    )

                # -------------------------------------------------
                # 一般加工
                #
                # 包含：
                #
                #   98 = B100-03
                #   31 = B107-02
                #
                # -------------------------------------------------

                else:

                    # 優先依 assemble.work_num
                    if assm is not None:

                        work_num = safe_str(
                            assm.work_num
                        ).strip()

                        if work_num:

                            part_info = (
                                part_by_code
                                .get(
                                    work_num
                                )
                            )

                    # fallback：
                    # 直接 process_type
                    # 對 P_Part.process_step_code
                    if part_info is None:

                        part_info = (
                            part_by_step
                            .get(
                                process_type
                            )
                        )

                    if part_info:

                        status = (
                            part_info.get(
                                "comment"
                            )
                            or
                            part_info.get(
                                "part_code"
                            )
                            or
                            f"加工({process_type})"
                        )

                    elif assm is not None:

                        status = safe_str(
                            assm.work_num
                        ).strip()

                        if not status:

                            status = (
                                f"加工({process_type})"
                            )

                    else:

                        status = (
                            f"加工({process_type})"
                        )

                '''
                # =================================================
                # 領料 / 搬運後面加人員
                # =================================================

                if (
                    process_type
                    in SPECIAL_PROCESS_TYPES
                ):

                    display_user = (
                        get_process_user_display(
                            record.user_id
                        )
                    )

                    if display_user:

                        status = (
                            f"{status}"
                            f"({display_user})"
                        )
                '''
                # 20260815版
                # =================================================
                # 所有 Process 後面加操作人員
                #
                # 包含：
                #
                #   領料
                #   搬運
                #   一般加工
                #
                # 例如：
                #
                #   主軸配件-分爪片(1004005陳世玟)
                #   加工(一)-精車(1004005陳世玟)
                # =================================================

                display_user = (
                    get_process_user_display(
                        record.user_id
                    )
                )

                if display_user:

                    status = (
                        f"{status}"
                        f"({display_user})"
                    )
                #

                # =================================================
                # 異常資訊
                # =================================================

                alarm_msg_enable = True
                alarm_msg_is_first = True
                alarm_msg_string = ""

                if assm is not None:

                    alarm_msg_enable = bool(
                        getattr(
                            assm,
                            "alarm_enable",
                            True
                        )
                    )

                    alarm_msg_is_first = bool(
                        getattr(
                            assm,
                            "isAssembleFirstAlarm",
                            True
                        )
                    )

                    if (
                        not alarm_msg_enable
                        and
                        not alarm_msg_is_first
                    ):

                        alarm_msg_string = (
                            safe_str(
                                getattr(
                                    assm,
                                    "alarm_message",
                                    ""
                                )
                            )
                            .strip()
                        )

                else:

                    incoming0 = safe_str(
                        getattr(
                            material,
                            "Incoming0_Abnormal",
                            ""
                        )
                    ).strip()

                    if (
                        incoming0
                        and
                        process_type
                        in {
                            1,
                            5,
                        }
                    ):

                        alarm_msg_string = (
                            incoming0
                        )

                # =================================================
                # 廢品數量
                # =================================================

                abnormal_qty = ""

                if (
                    assm is not None
                    and
                    process_type
                    not in SPECIAL_PROCESS_TYPES
                ):

                    aq = to_int(
                        getattr(
                            assm,
                            "abnormal_qty",
                            0
                        ),
                        0
                    )

                    if aq > 0:
                        abnormal_qty = aq

                # =================================================
                # 時間
                # =================================================

                temp_period_time = ""
                work_time_str = ""
                single_std_time_str = ""

                if (
                    process_type
                    not in {
                        5,
                        6,
                    }
                ):

                    start_time = (
                        parse_dt_maybe_aw(
                            record.begin_time
                        )
                    )

                    end_time = (
                        parse_dt_maybe_aw(
                            record.end_time
                        )
                    )

                    total_seconds = None

                    if start_time:

                        # -----------------------------------------
                        # 已完成
                        # -----------------------------------------

                        if end_time:

                            total_seconds = int(
                                (
                                    end_time
                                    -
                                    start_time
                                )
                                .total_seconds()
                            )

                        # -----------------------------------------
                        # 還在跑
                        # -----------------------------------------

                        else:

                            pause_total = (
                                to_int(
                                    getattr(
                                        record,
                                        "pause_time",
                                        0
                                    ),
                                    0
                                )
                            )

                            if (
                                bool(
                                    getattr(
                                        record,
                                        "is_pause",
                                        False
                                    )
                                )
                                and
                                getattr(
                                    record,
                                    "pause_started_at",
                                    None
                                )
                            ):

                                ps_aw = (
                                    parse_dt_maybe_aw(
                                        record
                                        .pause_started_at
                                    )
                                )

                                if ps_aw:

                                    extra_pause = int(
                                        (
                                            now_tpe_aw
                                            -
                                            ps_aw
                                        )
                                        .total_seconds()
                                    )

                                    pause_total += max(
                                        0,
                                        extra_pause
                                    )

                            total_seconds = int(
                                (
                                    now_tpe_aw
                                    -
                                    start_time
                                )
                                .total_seconds()
                            ) - pause_total

                        total_seconds = max(
                            0,
                            total_seconds
                        )

                        calculated_period = (
                            fmt_hhmmss(
                                total_seconds
                            )
                        )

                        if process_type == 1:

                            temp_period_time = (
                                safe_str(
                                    getattr(
                                        record,
                                        "str_elapsedActive_time",
                                        ""
                                    )
                                )
                                or
                                safe_str(
                                    getattr(
                                        record,
                                        "period_time",
                                        ""
                                    )
                                )
                                or
                                calculated_period
                            )

                        else:

                            temp_period_time = (
                                safe_str(
                                    getattr(
                                        record,
                                        "period_time",
                                        ""
                                    )
                                )
                                or
                                calculated_period
                            )

                        # -----------------------------------------
                        # 實際工時 分/PCS
                        #
                        # 只對真正加工製程計算
                        # -----------------------------------------

                        if (
                            process_type
                            not in SPECIAL_PROCESS_TYPES
                            and
                            work_qty > 0
                        ):

                            minutes_total = (
                                total_seconds
                                / 60.0
                            )

                            work_time = round(
                                minutes_total
                                /
                                work_qty,
                                2
                            )

                            work_time_str = (
                                str(
                                    work_time
                                )
                            )

                    else:

                        temp_period_time = (
                            safe_str(
                                getattr(
                                    record,
                                    "period_time",
                                    ""
                                )
                            )
                        )

                # =================================================
                # 單件標工
                #
                # P_Part:
                #
                #   B100-03
                #
                # ↓
                #
                # P_Material:
                #
                #   sd_time_B100
                # =================================================

                if (
                    process_type
                    not in SPECIAL_PROCESS_TYPES
                ):

                    std_info = (
                        part_info
                        or
                        part_by_step.get(
                            process_type
                        )
                    )

                    if std_info:

                        part_code = safe_str(
                            std_info.get(
                                "part_code"
                            )
                        ).strip()

                        if part_code:

                            prefix = (
                                part_code
                                .split(
                                    "-",
                                    1
                                )[0]
                                .split(
                                    "_",
                                    1
                                )[0]
                            )

                            col_name = (
                                f"sd_time_{prefix}"
                            )

                            std_value = (
                                getattr(
                                    material,
                                    col_name,
                                    None
                                )
                            )

                            if (
                                std_value
                                not in {
                                    None,
                                    "",
                                }
                            ):

                                single_std_time_str = (
                                    str(
                                        std_value
                                    )
                                )

                # =================================================
                # Process 數量
                #
                # 搬運不顯示。
                # =================================================

                if (
                    process_type
                    in {
                        5,
                        6,
                    }
                ):

                    process_work_time_qty = ""

                else:

                    qty_value = (
                        getattr(
                            record,
                            "process_work_time_qty",
                            None
                        )
                    )

                    process_work_time_qty = (
                        qty_value
                        if qty_value is not None
                        else ""
                    )

                # =================================================
                # 一般 Process 不再拿 completed_qty
                # 當成「入庫數量」。
                #
                # 入庫數量只由 P_Product 提供。
                # =================================================

                completed_qty = ""

                # =================================================
                # assemble 排序序號
                # =================================================

                assemble_seq = 0

                if assm is not None:

                    assemble_seq = (
                        to_int(
                            getattr(
                                assm,
                                "seq_num",
                                0
                            ),
                            0
                        )
                    )

                # =================================================
                # stage
                #
                # material 內排序：
                #
                # 0  領料
                # 1  領料區->加工區
                # 10 加工
                # 90 加工區->成品區
                # 100 入庫
                # =================================================

                if process_type == 1:
                    stage = 0

                elif process_type == 5:
                    stage = 1

                elif process_type == 6:
                    stage = 90

                else:
                    stage = 10

                # =================================================
                # Process row
                # =================================================

                results.append({

                    "seq_num":
                        0,

                    "id":
                        material_id,

                    "material_id":
                        material_id,

                    "order_num":
                        material.order_num,

                    "process_id":
                        process_id,

                    "assemble_id":
                        assemble_id,

                    "process_type_code":
                        process_type,

                    "process_work_time_qty":
                        process_work_time_qty,

                    "abnormal_qty":
                        abnormal_qty,

                    # 入庫欄位：
                    # Process 一律空
                    "completed_qty":
                        completed_qty,

                    "sd_time_B100":
                        getattr(
                            material,
                            "sd_time_B100",
                            None
                        ),

                    "sd_time_B102":
                        getattr(
                            material,
                            "sd_time_B102",
                            None
                        ),

                    "sd_time_B103":
                        getattr(
                            material,
                            "sd_time_B103",
                            None
                        ),

                    "sd_time_B107":
                        getattr(
                            material,
                            "sd_time_B107",
                            None
                        ),

                    "sd_time_B108":
                        getattr(
                            material,
                            "sd_time_B108",
                            None
                        ),

                    "user_id":
                        safe_str(
                            record.user_id
                        ),

                    "begin_time":
                        record.begin_time
                        or "",

                    "end_time":
                        record.end_time
                        or "",

                    "period_time":
                        temp_period_time,

                    "work_time":
                        work_time_str,

                    "single_std_time":
                        single_std_time_str,

                    "process_type":
                        status,

                    "normal_type":
                        (
                            " - 異常整修"
                            if (
                                not
                                alarm_msg_enable
                                and
                                not
                                alarm_msg_is_first
                            )
                            else
                            ""
                        ),

                    "user_comment":
                        alarm_msg_string,

                    "create_at":
                        record.create_at,

                    # ---------------------------------------------
                    # 以下只供後端排序
                    # 最後會 pop
                    # ---------------------------------------------

                    "_material_id":
                        material_id,

                    "_stage":
                        stage,

                    "_assemble_seq":
                        assemble_seq,

                    # 20260815 add
                    # 同 seq_num 的拆批仍要依 assemble_id 分組
                    "_assemble_id_sort":
                        assemble_id,

                    "_sort_id":
                        process_id,
                })

            # ====================================================
            # B. P_Product
            #
            # 真正成品入庫
            # ====================================================

            material_products = (
                products_by_material
                .get(
                    material_id,
                    []
                )
            )

            for product in material_products:

                product_id = to_int(
                    product.id,
                    0
                )

                linked_process_id = (
                    to_int(
                        product.process_id,
                        0
                    )
                )

                linked_process = (
                    linked_process_map
                    .get(
                        linked_process_id
                    )
                )

                # ------------------------------------------------
                # P_Product 沒有 user_id。
                #
                # 所以不能把 linked_process.user_id
                # 說成「入庫人員」。
                #
                # 此版只顯示：
                #
                #   成品入庫
                #
                # 不虛構：
                #
                #   成品入庫(1004005陳世玟)
                #
                # ------------------------------------------------

                stockin_status = (
                    "成品入庫"
                )

                # 20260815版 add
                stockin_user_display = (
                    get_process_user_display(
                        getattr(
                            product,
                            "user_id",
                            ""
                        )
                    )
                )

                if stockin_user_display:

                    stockin_status = (
                        f"成品入庫"
                        f"({stockin_user_display})"
                    )
                #

                # ------------------------------------------------
                # 入庫數量
                #
                # 優先：
                #
                #   allOk_qty
                #
                # fallback：
                #
                #   good_qty
                #   delivery_qty
                # ------------------------------------------------

                stockin_qty = (
                    to_int(
                        product.allOk_qty,
                        0
                    )
                )

                if stockin_qty <= 0:

                    stockin_qty = (
                        to_int(
                            product.good_qty,
                            0
                        )
                    )

                if stockin_qty <= 0:

                    stockin_qty = (
                        to_int(
                            product.delivery_qty,
                            0
                        )
                    )

                # ------------------------------------------------
                # product.process_id 若能對應到 P_Process，
                # 只用來補 assemble_id 做資料關聯，
                # 不用它假裝入庫人員。
                # ------------------------------------------------

                product_assemble_id = 0
                product_assemble_seq = 0

                if linked_process is not None:

                    product_assemble_id = (
                        to_int(
                            linked_process
                            .assemble_id,
                            0
                        )
                    )

                    linked_assm = (
                        assemble_map.get(
                            product_assemble_id
                        )
                    )

                    if linked_assm is not None:

                        product_assemble_seq = (
                            to_int(
                                getattr(
                                    linked_assm,
                                    "seq_num",
                                    0
                                ),
                                0
                            )
                        )

                '''
                # ------------------------------------------------
                # P_Product.create_at 是目前唯一可確認
                # 的真正入庫紀錄時間。
                #
                # 前端欄位：
                #
                #   開始時間
                #
                # 先顯示在 begin_time。
                # ------------------------------------------------

                stockin_time = (
                    product.create_at
                    or ""
                )
                '''

                '''
                # ------------------------------------------------
                # 成品入庫「開始時間」
                #
                # 顯示該次入庫所對應加工 Process 的開始時間，
                # 格式與一般加工列一致。
                #
                # 例如：
                #
                #   P_Product.process_id = 14
                #   P_Process.id         = 14
                #   begin_time           = 2026-07-31 09:29:42
                #
                # 若找不到 linked_process，
                # 才 fallback 到 product.create_at。
                # ------------------------------------------------

                stockin_time = ""

                if linked_process is not None:

                    stockin_time = (
                        linked_process.begin_time
                        or ""
                    )

                if not stockin_time:

                    stockin_time = (
                        product.create_at
                        or ""
                    )
                '''
                #
                # ------------------------------------------------
                # 成品入庫「開始時間」
                #
                # 優先：
                # 1. P_Product.process_id 對應的 P_Process.begin_time
                #
                # 若該 process 是後來建立的空白/樣板 Process，
                # 則再找同：
                #
                #   material_id
                #   assemble_id
                #   process_type
                #
                # 中真正已執行、具有 begin_time 的 Process。
                #
                # 最後才 fallback P_Product.create_at。
                # ------------------------------------------------

                stockin_time = ""

                # ------------------------------------------------
                # 1. P_Product.process_id 直接對應
                # ------------------------------------------------
                if linked_process is not None:

                    stockin_time = safe_str(
                        linked_process.begin_time
                    ).strip()


                # ------------------------------------------------
                # 2. linked process 沒有 begin_time
                #
                # 例如：
                #
                # 121200006501
                #
                # P_Product.process_id = 12
                #
                # P_Process 12：
                #   material_id  = 8
                #   assemble_id  = 8
                #   process_type = 98
                #   begin_time   = NULL
                #
                # 真正加工完成的是 P_Process 9。
                # ------------------------------------------------
                if (
                    not stockin_time
                    and
                    linked_process is not None
                ):

                    linked_material_id = to_int(
                        linked_process.material_id,
                        0
                    )

                    linked_assemble_id = to_int(
                        linked_process.assemble_id,
                        0
                    )

                    linked_process_type = to_int(
                        linked_process.process_type,
                        0
                    )

                    real_process = (
                        s.query(P_Process)
                        .filter(
                            P_Process.material_id
                            ==
                            linked_material_id
                        )
                        .filter(
                            P_Process.assemble_id
                            ==
                            linked_assemble_id
                        )
                        .filter(
                            P_Process.process_type
                            ==
                            linked_process_type
                        )
                        .filter(
                            P_Process.begin_time.isnot(None)
                        )
                        .filter(
                            P_Process.begin_time != ""
                        )
                        .filter(
                            P_Process.end_time.isnot(None)
                        )
                        .filter(
                            P_Process.end_time != ""
                        )
                        .order_by(
                            P_Process.id.desc()
                        )
                        .first()
                    )

                    if real_process is not None:

                        stockin_time = safe_str(
                            real_process.begin_time
                        ).strip()


                # ------------------------------------------------
                # 3. 最後 fallback P_Product.create_at
                #
                # 同時轉成 yyyy-mm-dd HH:MM:SS，
                # 避免 Flask jsonify 顯示：
                #
                # Tue, 11 Aug 2026 08:31:31 GMT
                # ------------------------------------------------
                if not stockin_time:

                    product_time = getattr(
                        product,
                        "create_at",
                        None
                    )

                    if isinstance(
                        product_time,
                        datetime
                    ):

                        stockin_time = (
                            product_time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        )

                    else:

                        stockin_time = safe_str(
                            product_time
                        ).strip()
                #

                results.append({

                    "seq_num":
                        0,

                    "id":
                        material_id,

                    "material_id":
                        material_id,

                    "order_num":
                        material.order_num,

                    # product row 沒有真正 P_Process id
                    "process_id":
                        0,

                    "product_id":
                        product_id,

                    "assemble_id":
                        product_assemble_id,

                    # 0 代表不是 P_Process type
                    "process_type_code":
                        0,

                    # 數量欄不顯示
                    "process_work_time_qty":
                        "",

                    "abnormal_qty":
                        "",

                    # 前端「入庫數量」欄位
                    "completed_qty":
                        (
                            stockin_qty
                            if stockin_qty > 0
                            else ""
                        ),

                    "sd_time_B100":
                        getattr(
                            material,
                            "sd_time_B100",
                            None
                        ),

                    "sd_time_B102":
                        getattr(
                            material,
                            "sd_time_B102",
                            None
                        ),

                    "sd_time_B103":
                        getattr(
                            material,
                            "sd_time_B103",
                            None
                        ),

                    "sd_time_B107":
                        getattr(
                            material,
                            "sd_time_B107",
                            None
                        ),

                    "sd_time_B108":
                        getattr(
                            material,
                            "sd_time_B108",
                            None
                        ),

                    "user_id":
                        "",

                    "begin_time":
                        stockin_time,

                    "end_time":
                        "",

                    "period_time":
                        "",

                    "work_time":
                        "",

                    "single_std_time":
                        "",

                    "process_type":
                        stockin_status,

                    "normal_type":
                        "",

                    "user_comment":
                        "",

                    "create_at":
                        product.create_at,

                    # ---------------------------------------------
                    # 入庫永遠排在同 material 最後
                    # ---------------------------------------------

                    "_material_id":
                        material_id,

                    "_stage":
                        100,

                    "_assemble_seq":
                        product_assemble_seq,

                    # 20260815 add
                    "_assemble_id_sort":
                        product_assemble_id,


                    "_sort_id":
                        product_id,
                })

        '''
        # ========================================================
        # 7. 最終排序
        #
        # 先依 material_id 分批，
        # 再依 stage。
        #
        # 例如：
        #
        # material 16：
        #
        #   加工
        #   ↓
        #   搬運
        #   ↓
        #   入庫
        #
        # material 50：
        #
        #   加工
        #   ↓
        #   搬運
        #   ↓
        #   入庫（若真的有 P_Product）
        # ========================================================

        results.sort(
            key=lambda row: (

                to_int(
                    row.get(
                        "_material_id"
                    ),
                    0
                ),

                to_int(
                    row.get(
                        "_stage"
                    ),
                    0
                ),

                to_int(
                    row.get(
                        "_assemble_seq"
                    ),
                    0
                ),

                (
                    row.get(
                        "create_at"
                    )
                    or
                    datetime.min
                ),

                to_int(
                    row.get(
                        "_sort_id"
                    ),
                    0
                ),
            )
        )
        '''
        #
        # ========================================================
        # 7. 最終排序
        #
        # 正確順序：
        #
        # material
        #   ↓
        # 工序 seq
        #   ↓
        # 同工序拆批 assemble_id
        #   ↓
        # 加工
        #   ↓
        # 搬運
        #   ↓
        # 入庫
        #
        # 例如 121200006710 / material 52：
        #
        # assemble 57
        #   加工76
        #   搬運
        #   入庫76
        #
        # assemble 77
        #   加工72
        #   搬運
        #
        # assemble 78
        #   加工中68
        #
        # ========================================================

        def detail_sort_key(row):

            material_id = to_int(
                row.get(
                    "_material_id"
                ),
                0
            )

            stage = to_int(
                row.get(
                    "_stage"
                ),
                0
            )

            assemble_seq = to_int(
                row.get(
                    "_assemble_seq"
                ),
                0
            )

            assemble_id_sort = to_int(
                row.get(
                    "_assemble_id_sort"
                ),
                0
            )

            create_at = (
                row.get(
                    "create_at"
                )
                or
                datetime.min
            )

            sort_id = to_int(
                row.get(
                    "_sort_id"
                ),
                0
            )

            # ----------------------------------------------------
            # 領料 / 領料區->加工區
            #
            # assemble_id 通常為 0，
            # 必須留在正式加工批次之前。
            # ----------------------------------------------------

            if stage < 10:

                return (
                    material_id,
                    0,
                    create_at,
                    stage,
                    sort_id,
                )

            # ----------------------------------------------------
            # 正式加工批次
            #
            # 最重要：
            #
            #   assemble_seq
            #   assemble_id
            #
            # 必須排在 stage 前面。
            #
            # 才會：
            #
            #   加工77
            #   搬運77
            #   →
            #   加工78
            #
            # 而不是：
            #
            #   加工77
            #   加工78
            #   搬運77
            # ----------------------------------------------------

            return (
                material_id,
                1,

                assemble_seq,

                assemble_id_sort,

                stage,

                create_at,

                sort_id,
            )


        results.sort(
            key=detail_sort_key
        )
        #

        # ========================================================
        # 8. 移除後端排序欄位
        #    並重新編 seq_num
        # ========================================================

        for index, row in enumerate(
            results,
            start=1
        ):

            row[
                "seq_num"
            ] = index

            row.pop(
                "_material_id",
                None
            )

            row.pop(
                "_stage",
                None
            )

            row.pop(
                "_assemble_seq",
                None
            )

            row.pop(
                "_sort_id",
                None
            )
            # 20260815版 add
            row.pop(
                "_assemble_id_sort",
                None
            )

        print(
            "getProcessesByOrderNumP:",
            order_num,
            "material_ids:",
            material_ids,
            "process/product rows:",
            len(results)
        )

        return jsonify({
            "success": True,
            "processes": results,
        })

    except Exception as e:

        print(
            "getProcessesByOrderNumP ERROR:",
            repr(e)
        )

        logger.exception(
            "getProcessesByOrderNumP failed"
        )

        return jsonify({
            "success": False,
            "message": str(e),
            "processes": [],
        }), 500

    finally:

        s.close()
"""


# 20260820版
# 20260818版
@getTableP.route("/getProcessesByOrderNumP", methods=["POST"])
def get_processes_by_order_num_p():
    print("getProcessesByOrderNumP....")

    request_data = (
        request.get_json(silent=True)
        or {}
    )

    order_num = str(
        request_data.get("order_num")
        or ""
    ).strip()

    if not order_num:
        return jsonify({
            "success": False,
            "message": "order_num is required",
            "processes": [],
        }), 400

    # ============================================================
    # 加工線特殊 Process Type
    #
    # 注意：
    #
    #   1 = 領料
    #   5 = 堆高機 領料區 -> 加工區
    #   6 = 堆高機 加工區 -> 成品區
    #
    # 其它：
    #
    #   100 / 99 / 98 / ... / 31 / ...
    #
    # 都可能是 P_Part.process_step_code。
    #
    # 特別注意：
    #
    #   process_type = 31
    #
    # 在加工線是：
    #
    #   B107-02
    #   主軸配件-分爪片
    #
    # 不是成品入庫。
    #
    # 真正入庫資料來源：
    #
    #   P_Product
    # ============================================================

    SPECIAL_PROCESS_TYPES = {
        1,
        5,
        6,
    }

    SPECIAL_PROCESS_NAMES = {
        1: "領料",
        5: "堆高機運行(領料區->加工區)",
        6: "堆高機運行(加工區->成品區)",
    }

    s = Session()

    try:

        # ========================================================
        # 共用小工具
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

        # ========================================================
        # employee 顯示名稱
        #
        # P_Process.user_id 有兩種資料：
        #
        #   01004005
        #
        # 或：
        #
        #   01004005 陳世玟
        #
        # ========================================================

        user_name_cache = {}

        def get_process_user_display(
            raw_user_id
        ):

            raw = safe_str(
                raw_user_id
            ).strip()

            if not raw:
                return ""

            # DB 已經帶姓名：
            #
            # 01004005 陳世玟
            if " " in raw:

                parts = raw.split(
                    None,
                    1
                )

                emp_id = (
                    parts[0]
                    if parts
                    else ""
                )

                emp_name = (
                    parts[1]
                    if len(parts) > 1
                    else ""
                )

                #return (
                #    f"{emp_id.lstrip('0')}"
                #    f" {emp_name}"
                #).strip()
                # 20260815版
                return (
                    f"{emp_id.lstrip('0')}"
                    f"{emp_name}"
                ).strip()
                #

            emp_id = raw

            if emp_id in user_name_cache:

                emp_name = (
                    user_name_cache[
                        emp_id
                    ]
                )

            else:

                user = (
                    s.query(User)
                    .filter_by(
                        emp_id=emp_id
                    )
                    .first()
                )

                emp_name = (
                    safe_str(
                        getattr(
                            user,
                            "emp_name",
                            ""
                        )
                    ).strip()
                    if user
                    else ""
                )

                user_name_cache[
                    emp_id
                ] = emp_name

            return (
                f"{emp_id.lstrip('0')}"
                f"{emp_name}"
            ).strip()

        # ========================================================
        # 1. 建立 P_Part mapping
        #
        # A:
        #   work_num
        #       -> P_Part
        #
        # B:
        #   process_step_code
        #       -> P_Part
        #
        # 例如：
        #
        #   B100-03 -> 98
        #   B107-02 -> 31
        # ========================================================

        part_by_code = {}
        part_by_step = {}

        part_rows = (
            s.query(P_Part)
            .all()
        )

        for p in part_rows:

            part_code = safe_str(
                p.part_code
            ).strip()

            step_code = to_int(
                p.process_step_code,
                0
            )

            if not part_code:
                continue

            info = {
                "part_code":
                    part_code,

                "comment":
                    safe_str(
                        p.part_comment
                    ).strip(),

                "process_step_code":
                    step_code,
            }

            part_by_code[
                part_code
            ] = info

            if step_code > 0:

                # 若 step_code 有重複，
                # 保留第一筆即可。
                part_by_step.setdefault(
                    step_code,
                    info
                )

        # ========================================================
        # 2. 同 order_num 所有 P_Material
        #
        # 舊版：
        #
        #   .first()
        #
        # 會造成：
        #
        # 121200006445
        #
        #   material_id = 16
        #   material_id = 50
        #
        # 只讀其中一筆。
        # ========================================================

        materials = (
            s.query(P_Material)
            .filter(
                P_Material.order_num
                ==
                order_num
            )
            .order_by(
                P_Material.id.asc()
            )
            .all()
        )

        if not materials:

            return jsonify({
                "success": False,
                "message":
                    "order not found",
                "processes": [],
            }), 404

        material_ids = [
            int(m.id)
            for m in materials
        ]

        # ========================================================
        # 3. 一次把真正入庫資料查出來
        # ========================================================

        product_rows = (
            s.query(P_Product)
            .filter(
                P_Product.material_id
                .in_(
                    material_ids
                )
            )
            .order_by(
                P_Product.create_at.asc(),
                P_Product.id.asc(),
            )
            .all()
        )

        products_by_material = {}

        for product in product_rows:

            mid = to_int(
                product.material_id,
                0
            )

            products_by_material.setdefault(
                mid,
                []
            ).append(
                product
            )

        # ========================================================
        # 4. 建立 Process Map
        #
        # 後面 P_Product.process_id 若需要找到原 Process，
        # 可直接使用。
        # ========================================================

        all_process_ids = [
            to_int(
                p.process_id,
                0
            )
            for p in product_rows
            if to_int(
                p.process_id,
                0
            ) > 0
        ]

        linked_process_map = {}

        if all_process_ids:

            linked_process_rows = (
                s.query(P_Process)
                .filter(
                    P_Process.id.in_(
                        all_process_ids
                    )
                )
                .all()
            )

            linked_process_map = {
                int(p.id): p
                for p
                in linked_process_rows
            }

        # ========================================================
        # 5. 最終回傳內容
        # ========================================================

        results = []

        now_tpe_aw = (
            datetime.now(TPE)
            .replace(
                microsecond=0
            )
        )

        # ========================================================
        # 6. 每個 material 分別處理
        # ========================================================

        for material in materials:

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

            # ----------------------------------------------------
            # assemble map
            # ----------------------------------------------------

            assemble_map = {
                to_int(a.id, 0): a
                for a
                in assemble_records
                if to_int(
                    a.id,
                    0
                ) > 0
            }

            # ----------------------------------------------------
            # 加工作業數量
            #
            # 原本用 total_delivery_qty。
            # 沒值時 fallback material_qty。
            # ----------------------------------------------------

            work_qty = to_int(
                getattr(
                    material,
                    "total_delivery_qty",
                    0
                ),
                0
            )

            if work_qty <= 0:

                work_qty = to_int(
                    getattr(
                        material,
                        "material_qty",
                        0
                    ),
                    0
                )

            # ----------------------------------------------------
            # Process 先按建立順序整理
            # ----------------------------------------------------

            process_records.sort(
                key=lambda p: (
                    getattr(
                        p,
                        "create_at",
                        None
                    )
                    or datetime.min,
                    to_int(
                        p.id,
                        0
                    )
                )
            )

            # ====================================================
            # A. P_Process
            # ====================================================

            for record in process_records:

                process_id = to_int(
                    record.id,
                    0
                )

                process_type = to_int(
                    record.process_type,
                    0
                )

                assemble_id = to_int(
                    record.assemble_id,
                    0
                )

                # ====================================================
                # 20260818版
                # 判斷是否為「真正領料 / 搬運 Process」
                #
                # type=5 有撞碼：
                #
                #   type=5 + assemble_id=0
                #       -> 堆高機：領料區 -> 加工區
                #
                #   type=5 + assemble_id>0
                #       -> 真正加工工序
                #          例如 B108-26
                #
                # type=6 目前系統固定代表：
                #       堆高機：加工區 -> 成品區
                #
                # 注意：目前既有 type=6 搬運紀錄可能仍帶 assemble_id，
                # 所以 type=6 不能加 assemble_id == 0。
                # ====================================================
                is_transport_process = (
                    process_type == 1
                    or process_type == 6
                    or (
                        process_type == 5
                        and assemble_id == 0
                    )
                )

                # 20260815版
                # ====================================================
                # 不領料加工單
                #
                # 加工線判斷「是否需要領料」應看：
                #
                #     P_Material.isBom
                #
                # isBom = 0：
                #     不領料
                #
                # isBom = 1：
                #     有 BOM / 需要領料流程
                #
                # 注意：
                # isTakeOk 不能拿來判斷是否「不領料」，
                # 因為不領料工單自動過站後 isTakeOk 也會是 True。
                #
                # 例如 121200006701：
                #
                # material_id=2
                # material_id=23
                #
                # 兩筆：
                #     isBom    = 0
                #     isTakeOk = 1
                #
                # DB 雖殘留自動過站的 type=1 / type=5，
                # PInformation 不應顯示。
                # ====================================================

                is_no_pick_material = (
                    not bool(
                        getattr(
                            material,
                            "isBom",
                            False
                        )
                    )
                )

                if (
                    is_no_pick_material
                    and
                    (
                        process_type == 1
                        or (
                            process_type == 5
                            and assemble_id == 0
                        )
                    )
                ):
                    continue
                #

                # ------------------------------------------------
                # 舊 5 / 6 搬運紀錄可能沒有 begin_time。
                #
                # 一般加工若完全沒有 begin_time，
                # 代表沒有真正開始過，不顯示。
                # ------------------------------------------------

                begin_raw = safe_str(
                    record.begin_time
                ).strip()

                if (
                    (
                        not begin_raw
                        or
                        begin_raw
                        ==
                        "0000-00-00 00:00:00"
                    )
                    and
                    not is_transport_process
                ):
                    continue

                # ------------------------------------------------
                # 找對應 P_Assemble
                # ------------------------------------------------

                assm = None

                if assemble_id > 0:

                    assm = (
                        assemble_map.get(
                            assemble_id
                        )
                    )

                    # 防止異常關聯
                    if (
                        assm is not None
                        and
                        to_int(
                            assm.material_id,
                            0
                        )
                        !=
                        material_id
                    ):
                        assm = None

                # =================================================
                # Process 顯示名稱
                # =================================================

                status = ""

                part_info = None

                # -------------------------------------------------
                # 領料 / 搬運
                # -------------------------------------------------

                if is_transport_process:

                    status = (
                        SPECIAL_PROCESS_NAMES
                        .get(
                            process_type,
                            f"Process({process_type})"
                        )
                    )

                # -------------------------------------------------
                # 一般加工
                #
                # 包含：
                #
                #   98 = B100-03
                #   31 = B107-02
                #
                # -------------------------------------------------

                else:

                    # 優先依 assemble.work_num
                    if assm is not None:

                        work_num = safe_str(
                            assm.work_num
                        ).strip()

                        if work_num:

                            part_info = (
                                part_by_code
                                .get(
                                    work_num
                                )
                            )

                    # fallback：
                    # 直接 process_type
                    # 對 P_Part.process_step_code
                    if part_info is None:

                        part_info = (
                            part_by_step
                            .get(
                                process_type
                            )
                        )

                    if part_info:

                        status = (
                            part_info.get(
                                "comment"
                            )
                            or
                            part_info.get(
                                "part_code"
                            )
                            or
                            f"加工({process_type})"
                        )

                    elif assm is not None:

                        status = safe_str(
                            assm.work_num
                        ).strip()

                        if not status:

                            status = (
                                f"加工({process_type})"
                            )

                    else:

                        status = (
                            f"加工({process_type})"
                        )

                '''
                # =================================================
                # 領料 / 搬運後面加人員
                # =================================================

                if (
                    process_type
                    in SPECIAL_PROCESS_TYPES
                ):

                    display_user = (
                        get_process_user_display(
                            record.user_id
                        )
                    )

                    if display_user:

                        status = (
                            f"{status}"
                            f"({display_user})"
                        )
                '''
                # 20260815版
                # =================================================
                # 所有 Process 後面加操作人員
                #
                # 包含：
                #
                #   領料
                #   搬運
                #   一般加工
                #
                # 例如：
                #
                #   主軸配件-分爪片(1004005陳世玟)
                #   加工(一)-精車(1004005陳世玟)
                # =================================================

                display_user = (
                    get_process_user_display(
                        record.user_id
                    )
                )

                if display_user:

                    status = (
                        f"{status}"
                        f"({display_user})"
                    )
                #

                # =================================================
                # 異常資訊
                # =================================================

                alarm_msg_enable = True
                alarm_msg_is_first = True
                alarm_msg_string = ""

                if assm is not None:

                    alarm_msg_enable = bool(
                        getattr(
                            assm,
                            "alarm_enable",
                            True
                        )
                    )

                    alarm_msg_is_first = bool(
                        getattr(
                            assm,
                            "isAssembleFirstAlarm",
                            True
                        )
                    )

                    if (
                        not alarm_msg_enable
                        and
                        not alarm_msg_is_first
                    ):

                        alarm_msg_string = (
                            safe_str(
                                getattr(
                                    assm,
                                    "alarm_message",
                                    ""
                                )
                            )
                            .strip()
                        )

                else:

                    incoming0 = safe_str(
                        getattr(
                            material,
                            "Incoming0_Abnormal",
                            ""
                        )
                    ).strip()

                    if (
                        incoming0
                        and
                        (
                            process_type == 1
                            or (
                                process_type == 5
                                and assemble_id == 0
                            )
                        )
                    ):

                        alarm_msg_string = (
                            incoming0
                        )

                # =================================================
                # 廢品數量
                # =================================================

                abnormal_qty = ""

                if (
                    assm is not None
                    and
                    not is_transport_process
                ):

                    aq = to_int(
                        getattr(
                            assm,
                            "abnormal_qty",
                            0
                        ),
                        0
                    )

                    if aq > 0:
                        abnormal_qty = aq

                # =================================================
                # 時間
                # =================================================

                temp_period_time = ""
                work_time_str = ""
                single_std_time_str = ""

                if not is_transport_process:

                    start_time = (
                        parse_dt_maybe_aw(
                            record.begin_time
                        )
                    )

                    end_time = (
                        parse_dt_maybe_aw(
                            record.end_time
                        )
                    )

                    total_seconds = None

                    '''
                    if start_time:

                        # -----------------------------------------
                        # 已完成
                        # -----------------------------------------

                        if end_time:

                            total_seconds = int(
                                (
                                    end_time
                                    -
                                    start_time
                                )
                                .total_seconds()
                            )

                        # -----------------------------------------
                        # 還在跑
                        # -----------------------------------------

                        else:

                            pause_total = (
                                to_int(
                                    getattr(
                                        record,
                                        "pause_time",
                                        0
                                    ),
                                    0
                                )
                            )

                            if (
                                bool(
                                    getattr(
                                        record,
                                        "is_pause",
                                        False
                                    )
                                )
                                and
                                getattr(
                                    record,
                                    "pause_started_at",
                                    None
                                )
                            ):

                                ps_aw = (
                                    parse_dt_maybe_aw(
                                        record
                                        .pause_started_at
                                    )
                                )

                                if ps_aw:

                                    extra_pause = int(
                                        (
                                            now_tpe_aw
                                            -
                                            ps_aw
                                        )
                                        .total_seconds()
                                    )

                                    pause_total += max(
                                        0,
                                        extra_pause
                                    )

                            total_seconds = int(
                                (
                                    now_tpe_aw
                                    -
                                    start_time
                                )
                                .total_seconds()
                            ) - pause_total

                        total_seconds = max(
                            0,
                            total_seconds
                        )

                        calculated_period = (
                            fmt_hhmmss(
                                total_seconds
                            )
                        )

                        if process_type == 1:

                            temp_period_time = (
                                safe_str(
                                    getattr(
                                        record,
                                        "str_elapsedActive_time",
                                        ""
                                    )
                                )
                                or
                                safe_str(
                                    getattr(
                                        record,
                                        "period_time",
                                        ""
                                    )
                                )
                                or
                                calculated_period
                            )

                        else:

                            temp_period_time = (
                                safe_str(
                                    getattr(
                                        record,
                                        "period_time",
                                        ""
                                    )
                                )
                                or
                                calculated_period
                            )

                        # -----------------------------------------
                        # 實際工時 分/PCS
                        #
                        # 只對真正加工製程計算
                        # -----------------------------------------

                        if (
                            not is_transport_process
                            and
                            work_qty > 0
                        ):

                            minutes_total = (
                                total_seconds
                                / 60.0
                            )

                            work_time = round(
                                minutes_total
                                /
                                work_qty,
                                2
                            )

                            work_time_str = (
                                str(
                                    work_time
                                )
                            )

                    else:

                        temp_period_time = (
                            safe_str(
                                getattr(
                                    record,
                                    "period_time",
                                    ""
                                )
                            )
                        )
                    '''
                    # 20260820版
                    if start_time:
                        if end_time:
                            # ============================================================
                            # 20260820 修正
                            # 已結束的加工製程：
                            #
                            # 不可直接使用：
                            #     end_time - begin_time
                            #
                            # 因為其中包含：
                            #     暫停時間
                            #     下班時間
                            #     週末跨日時間
                            #
                            # P_Process.elapsedActive_time 已經是實際有效加工秒數，
                            # PInformation 應以此欄位為準。
                            # ============================================================

                            total_seconds = int(
                                getattr(
                                    record,
                                    "elapsedActive_time",
                                    0
                                )
                                or 0
                            )

                            # ------------------------------------------------------------
                            # 舊資料保護：
                            # 若 elapsedActive_time 沒有資料，
                            # 才 fallback 回 end_time - begin_time
                            # ------------------------------------------------------------
                            if total_seconds <= 0:
                                total_seconds = int(
                                    (end_time - start_time).total_seconds()
                                )

                        else:
                            # ============================================================
                            # 尚未結束：
                            # 目前時間 - 開始時間 - 暫停時間
                            # ============================================================

                            pause_total = int(
                                getattr(
                                    record,
                                    "pause_time",
                                    0
                                )
                                or 0
                            )

                            if (
                                getattr(record, "is_pause", False)
                                and
                                getattr(
                                    record,
                                    "pause_started_at",
                                    None
                                )
                            ):
                                ps_aw = parse_dt_maybe_aw(
                                    record.pause_started_at
                                )

                                if ps_aw:
                                    extra_pause = int(
                                        (
                                            now_tpe_aw
                                            -
                                            ps_aw
                                        ).total_seconds()
                                    )

                                    pause_total += max(
                                        0,
                                        extra_pause
                                    )

                            total_seconds = int(
                                (
                                    now_tpe_aw
                                    -
                                    start_time
                                ).total_seconds()
                            ) - pause_total


                        total_seconds = max(
                            0,
                            total_seconds
                        )

                        # ================================================================
                        # 實際耗時
                        # ================================================================

                        time_diff_str_format = fmt_hhmmss(
                            total_seconds
                        )


                        if record.process_type == 1:

                            temp_period_time = (
                                record.str_elapsedActive_time
                                or
                                record.period_time
                                or
                                time_diff_str_format
                            )
                        # 20260820版 remove
                        #elif record.process_type == 31:
                        #
                        #    temp_period_time = ""

                        else:
                            # ============================================================
                            # 20260820 修正
                            #
                            # 加工製程的「實際耗時」必須跟 total_seconds
                            # 使用相同的有效工時來源。
                            #
                            # 不再優先使用舊的 period_time，
                            # 避免 period_time 仍保存 end-begin 的跨日時間。
                            # ============================================================

                            temp_period_time = time_diff_str_format

                        '''
                        # ================================================================
                        # 實際工時（分 / PCS）
                        #
                        # 公式：
                        #
                        #     有效加工秒數
                        #     ----------------
                        #       60 × 加工數量
                        #
                        # ================================================================

                        if (
                            show_code > 1000
                            and
                            work_qty > 0
                        ):

                            work_time = round(
                                total_seconds
                                /
                                60.0
                                /
                                work_qty,
                                2
                            )

                            work_time_str = str(
                                work_time
                            )

                        elif record.process_type == 31:

                            work_time_str = ""


                        else:

                            # 沒有開始時間
                            temp_period_time = (
                                record.period_time
                                or ""
                            )
                        '''

                        # 20260820版
                        # ================================================================
                        # 20260820
                        # 實際工時（分 / PCS）
                        #
                        # 優先使用：
                        #     P_Process.process_work_time_qty
                        #
                        # 因為加工單可能拆批，例如：
                        #
                        #     第1批 = 47 pcs
                        #     第2批 = 95 pcs
                        #
                        # 不可直接使用整張 material 的 total_delivery_qty。
                        #
                        # 公式：
                        #
                        #     elapsedActive_time
                        #     ------------------
                        #       60 × 本批加工數量
                        # ================================================================

                        process_qty = to_int(
                            getattr(
                                record,
                                "process_work_time_qty",
                                0
                            ),
                            0
                        )

                        # 舊資料沒有 process_work_time_qty 時，
                        # 才 fallback 使用 material 層級的 work_qty。
                        if process_qty <= 0:
                            process_qty = work_qty

                        if (
                            not is_transport_process
                            and
                            process_qty > 0
                        ):
                            work_time = round(
                                total_seconds
                                /
                                60.0
                                /
                                process_qty,
                                2
                            )

                            work_time_str = str(
                                work_time
                            )

                        else:
                            work_time_str = ""
                    #

                # =================================================
                # 單件標工
                #
                # P_Part:
                #
                #   B100-03
                #
                # ↓
                #
                # P_Material:
                #
                #   sd_time_B100
                # =================================================

                if not is_transport_process:

                    std_info = (
                        part_info
                        or
                        part_by_step.get(
                            process_type
                        )
                    )

                    if std_info:

                        part_code = safe_str(
                            std_info.get(
                                "part_code"
                            )
                        ).strip()

                        if part_code:

                            prefix = (
                                part_code
                                .split(
                                    "-",
                                    1
                                )[0]
                                .split(
                                    "_",
                                    1
                                )[0]
                            )

                            col_name = (
                                f"sd_time_{prefix}"
                            )

                            std_value = (
                                getattr(
                                    material,
                                    col_name,
                                    None
                                )
                            )

                            if (
                                std_value
                                not in {
                                    None,
                                    "",
                                }
                            ):

                                single_std_time_str = (
                                    str(
                                        std_value
                                    )
                                )

                # =================================================
                # Process 數量
                #
                # 搬運不顯示。
                # =================================================

                if is_transport_process:

                    process_work_time_qty = ""

                else:

                    qty_value = (
                        getattr(
                            record,
                            "process_work_time_qty",
                            None
                        )
                    )

                    process_work_time_qty = (
                        qty_value
                        if qty_value is not None
                        else ""
                    )

                # =================================================
                # 一般 Process 不再拿 completed_qty
                # 當成「入庫數量」。
                #
                # 入庫數量只由 P_Product 提供。
                # =================================================

                completed_qty = ""

                # =================================================
                # assemble 排序序號
                # =================================================

                assemble_seq = 0

                if assm is not None:

                    assemble_seq = (
                        to_int(
                            getattr(
                                assm,
                                "seq_num",
                                0
                            ),
                            0
                        )
                    )

                # =================================================
                # stage
                #
                # material 內排序：
                #
                # 0  領料
                # 1  領料區->加工區
                # 10 加工
                # 90 加工區->成品區
                # 100 入庫
                # =================================================

                if process_type == 1:
                    stage = 0

                elif (
                    process_type == 5
                    and assemble_id == 0
                ):
                    stage = 1

                elif process_type == 6:
                    stage = 90

                else:
                    # 包含 type=5 + assemble_id>0 的真正加工工序
                    stage = 10

                # =================================================
                # Process row
                # =================================================

                results.append({

                    "seq_num":
                        0,

                    "id":
                        material_id,

                    "material_id":
                        material_id,

                    "order_num":
                        material.order_num,

                    "process_id":
                        process_id,

                    "assemble_id":
                        assemble_id,

                    "process_type_code":
                        process_type,

                    "process_work_time_qty":
                        process_work_time_qty,

                    "abnormal_qty":
                        abnormal_qty,

                    # 入庫欄位：
                    # Process 一律空
                    "completed_qty":
                        completed_qty,

                    "sd_time_B100":
                        getattr(
                            material,
                            "sd_time_B100",
                            None
                        ),

                    "sd_time_B102":
                        getattr(
                            material,
                            "sd_time_B102",
                            None
                        ),

                    "sd_time_B103":
                        getattr(
                            material,
                            "sd_time_B103",
                            None
                        ),

                    "sd_time_B107":
                        getattr(
                            material,
                            "sd_time_B107",
                            None
                        ),

                    "sd_time_B108":
                        getattr(
                            material,
                            "sd_time_B108",
                            None
                        ),

                    "user_id":
                        safe_str(
                            record.user_id
                        ),

                    "begin_time":
                        record.begin_time
                        or "",

                    "end_time":
                        record.end_time
                        or "",

                    "period_time":
                        temp_period_time,

                    "work_time":
                        work_time_str,

                    "single_std_time":
                        single_std_time_str,

                    "process_type":
                        status,

                    "normal_type":
                        (
                            " - 異常整修"
                            if (
                                not
                                alarm_msg_enable
                                and
                                not
                                alarm_msg_is_first
                            )
                            else
                            ""
                        ),

                    "user_comment":
                        alarm_msg_string,

                    "create_at":
                        record.create_at,

                    # ---------------------------------------------
                    # 以下只供後端排序
                    # 最後會 pop
                    # ---------------------------------------------

                    "_material_id":
                        material_id,

                    "_stage":
                        stage,

                    "_assemble_seq":
                        assemble_seq,

                    # 20260815 add
                    # 同 seq_num 的拆批仍要依 assemble_id 分組
                    "_assemble_id_sort":
                        assemble_id,

                    "_sort_id":
                        process_id,
                })

            # ====================================================
            # B. P_Product
            #
            # 真正成品入庫
            # ====================================================

            material_products = (
                products_by_material
                .get(
                    material_id,
                    []
                )
            )

            for product in material_products:

                product_id = to_int(
                    product.id,
                    0
                )

                linked_process_id = (
                    to_int(
                        product.process_id,
                        0
                    )
                )

                linked_process = (
                    linked_process_map
                    .get(
                        linked_process_id
                    )
                )

                # ------------------------------------------------
                # P_Product 沒有 user_id。
                #
                # 所以不能把 linked_process.user_id
                # 說成「入庫人員」。
                #
                # 此版只顯示：
                #
                #   成品入庫
                #
                # 不虛構：
                #
                #   成品入庫(1004005陳世玟)
                #
                # ------------------------------------------------

                stockin_status = (
                    "成品入庫"
                )

                # 20260815版 add
                stockin_user_display = (
                    get_process_user_display(
                        getattr(
                            product,
                            "user_id",
                            ""
                        )
                    )
                )

                if stockin_user_display:

                    stockin_status = (
                        f"成品入庫"
                        f"({stockin_user_display})"
                    )
                #

                # ------------------------------------------------
                # 入庫數量
                #
                # 優先：
                #
                #   allOk_qty
                #
                # fallback：
                #
                #   good_qty
                #   delivery_qty
                # ------------------------------------------------

                stockin_qty = (
                    to_int(
                        product.allOk_qty,
                        0
                    )
                )

                if stockin_qty <= 0:

                    stockin_qty = (
                        to_int(
                            product.good_qty,
                            0
                        )
                    )

                if stockin_qty <= 0:

                    stockin_qty = (
                        to_int(
                            product.delivery_qty,
                            0
                        )
                    )

                # ------------------------------------------------
                # product.process_id 若能對應到 P_Process，
                # 只用來補 assemble_id 做資料關聯，
                # 不用它假裝入庫人員。
                # ------------------------------------------------

                product_assemble_id = 0
                product_assemble_seq = 0

                if linked_process is not None:

                    product_assemble_id = (
                        to_int(
                            linked_process
                            .assemble_id,
                            0
                        )
                    )

                    linked_assm = (
                        assemble_map.get(
                            product_assemble_id
                        )
                    )

                    if linked_assm is not None:

                        product_assemble_seq = (
                            to_int(
                                getattr(
                                    linked_assm,
                                    "seq_num",
                                    0
                                ),
                                0
                            )
                        )

                '''
                # ------------------------------------------------
                # P_Product.create_at 是目前唯一可確認
                # 的真正入庫紀錄時間。
                #
                # 前端欄位：
                #
                #   開始時間
                #
                # 先顯示在 begin_time。
                # ------------------------------------------------

                stockin_time = (
                    product.create_at
                    or ""
                )
                '''

                '''
                # ------------------------------------------------
                # 成品入庫「開始時間」
                #
                # 顯示該次入庫所對應加工 Process 的開始時間，
                # 格式與一般加工列一致。
                #
                # 例如：
                #
                #   P_Product.process_id = 14
                #   P_Process.id         = 14
                #   begin_time           = 2026-07-31 09:29:42
                #
                # 若找不到 linked_process，
                # 才 fallback 到 product.create_at。
                # ------------------------------------------------

                stockin_time = ""

                if linked_process is not None:

                    stockin_time = (
                        linked_process.begin_time
                        or ""
                    )

                if not stockin_time:

                    stockin_time = (
                        product.create_at
                        or ""
                    )
                '''
                #
                # ------------------------------------------------
                # 成品入庫「開始時間」
                #
                # 優先：
                # 1. P_Product.process_id 對應的 P_Process.begin_time
                #
                # 若該 process 是後來建立的空白/樣板 Process，
                # 則再找同：
                #
                #   material_id
                #   assemble_id
                #   process_type
                #
                # 中真正已執行、具有 begin_time 的 Process。
                #
                # 最後才 fallback P_Product.create_at。
                # ------------------------------------------------

                stockin_time = ""

                # ------------------------------------------------
                # 1. P_Product.process_id 直接對應
                # ------------------------------------------------
                if linked_process is not None:

                    stockin_time = safe_str(
                        linked_process.begin_time
                    ).strip()


                # ------------------------------------------------
                # 2. linked process 沒有 begin_time
                #
                # 例如：
                #
                # 121200006501
                #
                # P_Product.process_id = 12
                #
                # P_Process 12：
                #   material_id  = 8
                #   assemble_id  = 8
                #   process_type = 98
                #   begin_time   = NULL
                #
                # 真正加工完成的是 P_Process 9。
                # ------------------------------------------------
                if (
                    not stockin_time
                    and
                    linked_process is not None
                ):

                    linked_material_id = to_int(
                        linked_process.material_id,
                        0
                    )

                    linked_assemble_id = to_int(
                        linked_process.assemble_id,
                        0
                    )

                    linked_process_type = to_int(
                        linked_process.process_type,
                        0
                    )

                    real_process = (
                        s.query(P_Process)
                        .filter(
                            P_Process.material_id
                            ==
                            linked_material_id
                        )
                        .filter(
                            P_Process.assemble_id
                            ==
                            linked_assemble_id
                        )
                        .filter(
                            P_Process.process_type
                            ==
                            linked_process_type
                        )
                        .filter(
                            P_Process.begin_time.isnot(None)
                        )
                        .filter(
                            P_Process.begin_time != ""
                        )
                        .filter(
                            P_Process.end_time.isnot(None)
                        )
                        .filter(
                            P_Process.end_time != ""
                        )
                        .order_by(
                            P_Process.id.desc()
                        )
                        .first()
                    )

                    if real_process is not None:

                        stockin_time = safe_str(
                            real_process.begin_time
                        ).strip()


                # ------------------------------------------------
                # 3. 最後 fallback P_Product.create_at
                #
                # 同時轉成 yyyy-mm-dd HH:MM:SS，
                # 避免 Flask jsonify 顯示：
                #
                # Tue, 11 Aug 2026 08:31:31 GMT
                # ------------------------------------------------
                if not stockin_time:

                    product_time = getattr(
                        product,
                        "create_at",
                        None
                    )

                    if isinstance(
                        product_time,
                        datetime
                    ):

                        stockin_time = (
                            product_time.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        )

                    else:

                        stockin_time = safe_str(
                            product_time
                        ).strip()
                #

                results.append({

                    "seq_num":
                        0,

                    "id":
                        material_id,

                    "material_id":
                        material_id,

                    "order_num":
                        material.order_num,

                    # product row 沒有真正 P_Process id
                    "process_id":
                        0,

                    "product_id":
                        product_id,

                    "assemble_id":
                        product_assemble_id,

                    # 0 代表不是 P_Process type
                    "process_type_code":
                        0,

                    # 數量欄不顯示
                    "process_work_time_qty":
                        "",

                    "abnormal_qty":
                        "",

                    # 前端「入庫數量」欄位
                    "completed_qty":
                        (
                            stockin_qty
                            if stockin_qty > 0
                            else ""
                        ),

                    "sd_time_B100":
                        getattr(
                            material,
                            "sd_time_B100",
                            None
                        ),

                    "sd_time_B102":
                        getattr(
                            material,
                            "sd_time_B102",
                            None
                        ),

                    "sd_time_B103":
                        getattr(
                            material,
                            "sd_time_B103",
                            None
                        ),

                    "sd_time_B107":
                        getattr(
                            material,
                            "sd_time_B107",
                            None
                        ),

                    "sd_time_B108":
                        getattr(
                            material,
                            "sd_time_B108",
                            None
                        ),

                    "user_id":
                        "",

                    "begin_time":
                        stockin_time,

                    "end_time":
                        "",

                    "period_time":
                        "",

                    "work_time":
                        "",

                    "single_std_time":
                        "",

                    "process_type":
                        stockin_status,

                    "normal_type":
                        "",

                    "user_comment":
                        "",

                    "create_at":
                        product.create_at,

                    # ---------------------------------------------
                    # 入庫永遠排在同 material 最後
                    # ---------------------------------------------

                    "_material_id":
                        material_id,

                    "_stage":
                        100,

                    "_assemble_seq":
                        product_assemble_seq,

                    # 20260815 add
                    "_assemble_id_sort":
                        product_assemble_id,


                    "_sort_id":
                        product_id,
                })

        '''
        # ========================================================
        # 7. 最終排序
        #
        # 先依 material_id 分批，
        # 再依 stage。
        #
        # 例如：
        #
        # material 16：
        #
        #   加工
        #   ↓
        #   搬運
        #   ↓
        #   入庫
        #
        # material 50：
        #
        #   加工
        #   ↓
        #   搬運
        #   ↓
        #   入庫（若真的有 P_Product）
        # ========================================================

        results.sort(
            key=lambda row: (

                to_int(
                    row.get(
                        "_material_id"
                    ),
                    0
                ),

                to_int(
                    row.get(
                        "_stage"
                    ),
                    0
                ),

                to_int(
                    row.get(
                        "_assemble_seq"
                    ),
                    0
                ),

                (
                    row.get(
                        "create_at"
                    )
                    or
                    datetime.min
                ),

                to_int(
                    row.get(
                        "_sort_id"
                    ),
                    0
                ),
            )
        )
        '''
        #
        # ========================================================
        # 7. 最終排序
        #
        # 正確順序：
        #
        # material
        #   ↓
        # 工序 seq
        #   ↓
        # 同工序拆批 assemble_id
        #   ↓
        # 加工
        #   ↓
        # 搬運
        #   ↓
        # 入庫
        #
        # 例如 121200006710 / material 52：
        #
        # assemble 57
        #   加工76
        #   搬運
        #   入庫76
        #
        # assemble 77
        #   加工72
        #   搬運
        #
        # assemble 78
        #   加工中68
        #
        # ========================================================
        '''
        def detail_sort_key(row):

            material_id = to_int(
                row.get(
                    "_material_id"
                ),
                0
            )

            stage = to_int(
                row.get(
                    "_stage"
                ),
                0
            )

            assemble_seq = to_int(
                row.get(
                    "_assemble_seq"
                ),
                0
            )

            assemble_id_sort = to_int(
                row.get(
                    "_assemble_id_sort"
                ),
                0
            )

            create_at = (
                row.get(
                    "create_at"
                )
                or
                datetime.min
            )

            sort_id = to_int(
                row.get(
                    "_sort_id"
                ),
                0
            )

            # ----------------------------------------------------
            # 領料 / 領料區->加工區
            #
            # assemble_id 通常為 0，
            # 必須留在正式加工批次之前。
            # ----------------------------------------------------

            if stage < 10:

                return (
                    material_id,
                    0,
                    create_at,
                    stage,
                    sort_id,
                )

            # ----------------------------------------------------
            # 正式加工批次
            #
            # 最重要：
            #
            #   assemble_seq
            #   assemble_id
            #
            # 必須排在 stage 前面。
            #
            # 才會：
            #
            #   加工77
            #   搬運77
            #   →
            #   加工78
            #
            # 而不是：
            #
            #   加工77
            #   加工78
            #   搬運77
            # ----------------------------------------------------

            return (
                material_id,
                1,

                assemble_seq,

                assemble_id_sort,

                stage,

                create_at,

                sort_id,
            )
        '''
        # 20260818版
        def detail_sort_key(row):

            material_id = to_int(
                row.get(
                    "_material_id"
                ),
                0
            )

            stage = to_int(
                row.get(
                    "_stage"
                ),
                0
            )

            assemble_seq = to_int(
                row.get(
                    "_assemble_seq"
                ),
                0
            )

            assemble_id_sort = to_int(
                row.get(
                    "_assemble_id_sort"
                ),
                0
            )

            create_at = (
                row.get(
                    "create_at"
                )
                or datetime.min
            )

            sort_id = to_int(
                row.get(
                    "_sort_id"
                ),
                0
            )


            # ========================================================
            # 1. 領料 / 領料區 -> 加工區
            #
            # 永遠排在加工以前
            # ========================================================
            if stage < 10:

                return (
                    material_id,
                    0,
                    create_at,
                    stage,
                    sort_id,
                )


            # ========================================================
            # 2. 成品入庫
            #
            # ★ 一定排在該 material 所有加工 / 搬運之後
            #
            # 不可再使用 assemble_seq 排在前面，
            # 因為某些 P_Product 可能：
            #
            #   assemble_seq = 0
            #
            # 如果先比 assemble_seq，
            # 成品入庫反而會跑到第一筆。
            # ========================================================
            if stage >= 100:

                return (
                    material_id,
                    2,
                    create_at,
                    sort_id,
                    0,
                )


            # ========================================================
            # 3. 正式加工 / 加工區 -> 成品區搬運
            #
            # 順序：
            #
            # assemble seq
            # ↓
            # assemble id
            # ↓
            # 加工 stage=10
            # ↓
            # 搬運 stage=90
            # ========================================================
            return (
                material_id,
                1,

                assemble_seq,

                assemble_id_sort,

                stage,

                create_at,

                sort_id,
            )
        #


        results.sort(
            key=detail_sort_key
        )
        #

        # ========================================================
        # 8. 移除後端排序欄位
        #    並重新編 seq_num
        # ========================================================

        for index, row in enumerate(
            results,
            start=1
        ):

            row[
                "seq_num"
            ] = index

            row.pop(
                "_material_id",
                None
            )

            row.pop(
                "_stage",
                None
            )

            row.pop(
                "_assemble_seq",
                None
            )

            row.pop(
                "_sort_id",
                None
            )
            # 20260815版 add
            row.pop(
                "_assemble_id_sort",
                None
            )

        print(
            "getProcessesByOrderNumP:",
            order_num,
            "material_ids:",
            material_ids,
            "process/product rows:",
            len(results)
        )

        return jsonify({
            "success": True,
            "processes": results,
        })

    except Exception as e:

        print(
            "getProcessesByOrderNumP ERROR:",
            repr(e)
        )

        logger.exception(
            "getProcessesByOrderNumP failed"
        )

        return jsonify({
            "success": False,
            "message": str(e),
            "processes": [],
        }), 500

    finally:

        s.close()


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


@getTableP.route("/getUsersDepsProcessesP", methods=['POST'])
def get_users_deps_processes_p():
    print("getUsersDepsProcessesP....")

    _user_results = []
    return_value = True
    raw_select = 0
    """
    if request.method == 'GET':
        # 從 query 取
        raw_select = request.args.get('select', 0)
    else:
    """
        # 從 JSON 取
    #data = request.get_json(silent=True) or {}
    data = request.get_json()

    raw_select = data.get('select', 0)

    try:
        # 取得 select 參數（0, 1, 3, 7），預設 0
        raw_select = request.args.get('select', '0')
        try:
            select_days = int(raw_select)
        except ValueError:
            select_days = 0

        # 只允許 0,1,3,7，其它當 0
        if select_days not in (0, 1, 3, 7):
            select_days = 0

        today = dt.now().date()

        if select_days <= 0:
            # select = 0 → 只算今天
            start_day = today
            end_day = today
        else:
            # select = 1/3/7 → 算「前 N 天」，不含今天
            # 例如 select=3：今天 11/23，範圍是 11/20 ~ 11/22
            start_day = today - timedelta(days=select_days)
            end_day = today - timedelta(days=1)

        start_str = f"{start_day.strftime('%Y-%m-%d')} 00:00:00"
        end_str   = f"{end_day.strftime('%Y-%m-%d')} 23:59:59"
        #print(f"計算區間: select={select_days}, {start_str} ~ {end_str}")

        s = Session()

        _objects = s.query(User).all()
        users = [u.__dict__ for u in _objects]
        index=0
        for user in users:
          # 依你原本邏輯：只留下 isRemoved == True 的使用者
          if user['isRemoved'] == False:
              continue

          emp_id = user['emp_id']

          # 計算這段日期內的 elapsedActive_time 總和
          total_elapsed = (
              s.query(func.coalesce(func.sum(P_Process.elapsedActive_time), 0))
              .filter(
                  P_Process.user_id == emp_id,
                  P_Process.begin_time != '',
                  P_Process.end_time != '',
                  P_Process.begin_time >= start_str,
                  P_Process.begin_time <= end_str,
                  P_Process.end_time >= start_str,
                  P_Process.end_time <= end_str,
              )
              .scalar()
          ) or 0

          total_elapsed = int(total_elapsed)
          #print("total_elapsed:", total_elapsed)
          # 轉成 hh:mm:ss 文字
          h = total_elapsed // 3600
          m = (total_elapsed % 3600) // 60
          sec = total_elapsed % 60
          total_str = f"{h:02d}:{m:02d}:{sec:02d}"
          index = index + 1
          _user_object = {
            'id': index,
            'emp_id': emp_id,
            'emp_name': user['emp_name'],
            'dep_name': user['dep_name'].split('-', 1)[1],

            'workHours': total_str,
            'online': random.randint(0, 2),
          }

          _user_results.append(_user_object)
        # end for_loop

        temp_len = len(_user_results)
        print("getUsersDepsProcessesP, 總數: ", temp_len)

        return jsonify({
          'status': return_value,
          'users_and_deps_and_process': _user_results,
        })

    except Exception as e:
      s.rollback()
      print("list_users_deps_processes_p error:", e)
      return jsonify({
        'status': False,
        'error': str(e),
      })
    finally:
      s.close()

