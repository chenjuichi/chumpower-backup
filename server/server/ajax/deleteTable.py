import os
import sys
import argparse

from datetime import datetime, timedelta

from typing import List

from flask import Blueprint, jsonify, request, current_app

from database.tables import User, Session
from database.tables import Material, Assemble, Product, Bom, Process, association_material_abnormal
from database.p_tables import P_Material, P_Assemble, P_Product, P_Bom, P_Process, p_association_material_abnormal

import pymysql
from sqlalchemy import select, delete, update, exc
from sqlalchemy.exc import SQLAlchemyError

import traceback


deleteTable = Blueprint('deleteTable', __name__)


from log_util import setup_logger
logger = setup_logger(__name__)  # 每個模組用自己的名稱


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
