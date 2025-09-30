import os
import sys
import argparse
from typing import List

from flask import Blueprint, jsonify, request, current_app

from database.tables import User, Session
from database.tables import Material, Assemble, Product, Bom, Process, association_material_abnormal

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


#@deleteTable.route('/removeMaterialsAndRelationTable', methods=['POST'], endpoint='removeMaterialsAndRelationTable')
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