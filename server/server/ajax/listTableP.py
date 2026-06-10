import math
import random
import re
from datetime import datetime, date, timedelta

import traceback

from datetime import datetime as dt
import time

from flask import Blueprint, jsonify, request, current_app

from database.tables import User, Session
from database.p_tables import P_Material, P_Assemble,  P_AbnormalCause, P_Process, P_Product, P_Part

from dotenv import dotenv_values

from collections import defaultdict

from sqlalchemy import func, or_, cast, Integer
from sqlalchemy.orm import selectinload, load_only
from sqlalchemy import distinct, case, select

listTableP = Blueprint('listTableP', __name__)


# ------------------------------------------------------------------


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
                    P_Assemble.input_disable,
                    P_Assemble.Incoming1_Abnormal,
                    P_Assemble.is_copied_from_id,
                    P_Assemble.create_at,
                    P_Assemble.isShowBomGif,
                    P_Assemble.isStockIn,
                    P_Assemble.isWarehouseStationShow,
                    P_Assemble.show2_ok,
                ),
                selectinload(P_Material._process).load_only(
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

        part_info_map = {}
        part_rows = (
            s.query(
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

            total_records = sum(
                1 for p in process_records
                if p.material_id == material_record.id and int(p.assemble_id or 0) != 0
            )

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

            proc_stat_map = {}

            for p in process_records:
                if p.material_id != material_record.id:
                    continue

                aid = int(p.assemble_id or 0)
                ptype = int(p.process_type or 0)

                if aid == 0 or ptype == 0:
                    continue

                # begin_time 有值，而且 end_time 是 NULL 或空字串，才算進行中/暫停中
                if (
                    not p.begin_time
                    or not str(p.begin_time).strip()
                    or (p.end_time is not None and str(p.end_time).strip() != '')
                ):
                    continue

                key = (aid, ptype)
                if key not in proc_stat_map:
                    proc_stat_map[key] = {
                        'count': 0,
                        'qty_sum': 0,
                        'last_proc_id': 0,
                        'last_user_id': '',
                        'is_pause': False,
                        'elapsedActive_time': 0,
                        'str_elapsedActive_time': '00:00:00',
                    }

                proc_stat_map[key]['count'] += 1
                proc_stat_map[key]['qty_sum'] += int(p.process_work_time_qty or 0)

                pid = int(p.id or 0)
                if pid >= proc_stat_map[key]['last_proc_id']:
                    proc_stat_map[key]['last_proc_id'] = pid
                    proc_stat_map[key]['last_user_id'] = p.user_id or ''
                    proc_stat_map[key]['is_pause'] = bool(p.is_pause)
                    proc_stat_map[key]['elapsedActive_time'] = int(p.elapsedActive_time or 0)
                    proc_stat_map[key]['str_elapsedActive_time'] = (
                        p.str_elapsedActive_time or '00:00:00'
                    )

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

                stat = proc_stat_map.get((int(assemble_record.id), show_code), {
                    'count': 0,
                    'qty_sum': 0,
                    'last_user_id': '',
                    'is_pause': False,
                    'elapsedActive_time': 0,
                    'str_elapsedActive_time': '00:00:00',
                })

                matched_count = int(stat.get('count') or 0)
                total_work_qty = int(stat.get('qty_sum') or 0)

                show_timer = matched_count > 0
                show_name = stat.get('last_user_id', '') if show_timer else ''

                a_statement = (
                    show_code != 0
                    and total_records != 0
                    and matched_count > 0
                    and total_work_qty >= int(material_record.delivery_qty or 0)
                )

                index += 1

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

                    'show_timer': show_timer,
                    'show_name': show_name,
                    'is_pause': bool(stat.get('is_pause', False)),
                    'elapsedActive_time': int(stat.get('elapsedActive_time') or 0),
                    'str_elapsedActive_time': stat.get('str_elapsedActive_time') or '00:00:00',

                    'isShowBomGif': assemble_record.isShowBomGif,
                    'process_step_code': assemble_record.process_step_code,

                    # 這裡只是顯示文字，不拿來判斷是否已入庫
                    'isStockIn': '' if assemble_record.isStockIn else ' [不入庫]',
                    'isWarehouseStationShow': bool(assemble_record.isWarehouseStationShow),

                    'assemble_process_num': int(assemble_record.show2_ok or 0),
                }

                _results.append(_object)

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
    #q = q.order_by(P_Material.order_num).limit(limit).offset(offset)

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
      total_process_records =len([p for p in process_records if ((p.material_id == record.id and p.has_started == 1 and p.begin_time != ''))])

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
        #'delivery_qty':record.delivery_qty,             #現況數量
        #'delivery_qty': int(stockin_total) if int(stockin_total) > 0 else record.delivery_qty,
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
        #s.close()
        return jsonify({'status': False, 'informations': []})

    temp_len = len(_results)
    #print("listInformations, 資料: ", _results)
    print("listInformationsP, 總數: ", temp_len)
    #if (temp_len == 0):
    #  return_value = False
    #else:
    # 根據 'order_num' 排序
    #_results = sorted(_results, key=lambda x: x['order_num'])

    # total_process_records != 0 的資料 → 排在前面, 其餘再依 order_num 排序
    _results = sorted(
      _results,
      key=lambda x: (x.get('total_process_records', 0) == 0, x['order_num'])
    )

    return jsonify({
      'status': True,
      'total': total,
      'informations': _results
    })



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
            total_process_records = len([p for p in process_records if (p.material_id == record.id and p.has_started == 1 and (p.begin_time or '') != '')])

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



