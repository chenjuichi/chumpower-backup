#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete a Material (and its related rows) by id.

Usage:
  python delete_material.py 123
  python delete_material.py 123 --dry-run
  python delete_material.py 123 --delete-copies   # also delete Materials copied from this one (transitively)
  python delete_material.py 123 --force           # skip confirmation

Notes:
- Place this script in the same folder as your `tables.py` (or ensure it's on PYTHONPATH).
- Deletion order respects foreign keys (children first, then parent).
"""

import sys
import os
import argparse
from typing import List
from pathlib import Path

# Make sure tables.py is importable from either current folder or ./database
THIS_DIR = Path(__file__).resolve().parent
DB_DIR   = THIS_DIR / "database"
for _p in (THIS_DIR, DB_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError

# Import models & session from your project
try:
    from database.tables import (
        Session,
        Material,
        Bom,
        Assemble,
        Product,
        Process,
        association_material_abnormal,
    )
except Exception as e:
    print("❌ 無法匯入 tables.py，請確認此腳本與 tables.py 位於同一資料夾，或調整 PYTHONPATH。")
    print(f"Import error: {e}")
    sys.exit(2)


def find_descendant_material_ids(session, root_id: int) -> List[int]:
    """
    尋找所有 (transitively) is_copied_from_id 指向 root_id 的後代 Material.id
    回傳包含 root_id 的列表（去重）。
    """
    to_visit = [root_id]
    seen = set([root_id])
    idx = 0
    while idx < len(to_visit):
        current = to_visit[idx]
        idx += 1
        rows = session.execute(
            select(Material.id).where(Material.is_copied_from_id == current)
        ).scalars().all()
        for mid in rows:
            if mid not in seen:
                seen.add(mid)
                to_visit.append(mid)
    return to_visit


def summarize_related_counts(session, material_id: int) -> dict:
    """統計關聯資料數量（僅主線：Bom / Assemble / Product / Process / M2M 連結）。"""
    bom_cnt = session.execute(select(Bom.id).where(Bom.material_id == material_id)).rowcount
    # rowcount is None for SELECT on many DBs; fallback by fetching all ids
    if bom_cnt is None:
        bom_cnt = len(session.execute(select(Bom.id).where(Bom.material_id == material_id)).all())

    asm_cnt = session.execute(select(Assemble.id).where(Assemble.material_id == material_id)).rowcount
    if asm_cnt is None:
        asm_cnt = len(session.execute(select(Assemble.id).where(Assemble.material_id == material_id)).all())

    prod_cnt = session.execute(select(Product.id).where(Product.material_id == material_id)).rowcount
    if prod_cnt is None:
        prod_cnt = len(session.execute(select(Product.id).where(Product.material_id == material_id)).all())

    proc_cnt = session.execute(select(Process.id).where(Process.material_id == material_id)).rowcount
    if proc_cnt is None:
        proc_cnt = len(session.execute(select(Process.id).where(Process.material_id == material_id)).all())

    m2m_cnt = len(session.execute(
        select(association_material_abnormal.c.material_id).where(
            association_material_abnormal.c.material_id == material_id
        )
    ).all())

    copies_cnt = len(session.execute(
        select(Material.id).where(Material.is_copied_from_id == material_id)
    ).scalars().all())

    return {
        "bom": bom_cnt,
        "assemble": asm_cnt,
        "product": prod_cnt,
        "process": proc_cnt,
        "abnormal_links": m2m_cnt,
        "copies": copies_cnt,
    }


def delete_one_material(session, material_id: int, *, set_children_copies_null: bool) -> None:
    """
    實際執行刪除一筆 material_id 的所有關聯（children→parent）。
    若 set_children_copies_null=True，會把其他 Material 對此筆的 is_copied_from_id 設為 NULL（不刪它們）。
    """
    # 1) 先刪多對多連結
    session.execute(
        delete(association_material_abnormal).where(
            association_material_abnormal.c.material_id == material_id
        )
    )
    # 2) 刪子表
    session.execute(delete(Process).where(Process.material_id == material_id))
    session.execute(delete(Product).where(Product.material_id == material_id))
    session.execute(delete(Assemble).where(Assemble.material_id == material_id))
    session.execute(delete(Bom).where(Bom.material_id == material_id))

    # 3) 如果不連帶刪「被複製出去」的同宗資料，就把它們的 is_copied_from_id 設回 NULL，避免外鍵卡住
    if set_children_copies_null:
        session.execute(
            update(Material)
            .where(Material.is_copied_from_id == material_id)
            .values(is_copied_from_id=None)
        )

    # 4) 刪主表
    session.execute(delete(Material).where(Material.id == material_id))


def main():
    parser = argparse.ArgumentParser(description="刪除指定 Material 及其關聯資料")
    parser.add_argument("id", type=int, help="Material.id")
    parser.add_argument(
        "--delete-copies",
        action="store_true",
        help="同時刪除所有從此筆複製出去的 Material（遞迴刪除）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只顯示將被刪除的概況，不實際刪除",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="跳過刪除前的確認提示",
    )
    args = parser.parse_args()

    session = Session()

    try:
        mat = session.get(Material, args.id)
        if not mat:
            print(f"⚠️ 找不到 Material.id={args.id}")
            sys.exit(1)

        # 概況
        print(f"將處理 Material.id={args.id}, order_num={getattr(mat, 'order_num', None)}, material_num={getattr(mat, 'material_num', None)}")
        counts = summarize_related_counts(session, args.id)
        print(f"- 關聯數量: BOM={counts['bom']}, Assemble={counts['assemble']}, Product={counts['product']}, Process={counts['process']}, M2M_links={counts['abnormal_links']}, Copies(out)={counts['copies']}")

        # 是否連帶刪掉複製出去的同宗資料
        delete_id_list = [args.id]
        if args.delete_copies:
            delete_id_list = find_descendant_material_ids(session, args.id)
            # 由葉→根刪除，避免外鍵依賴
            delete_id_list = list(dict.fromkeys(delete_id_list))  # 去重但保順序
            print(f"- 將遞迴刪除以下 Material.id（由葉到根）: {delete_id_list}")
        else:
            print("- 不刪除 'copied_to' 同宗資料（若存在），會把它們的 is_copied_from_id 設為 NULL")

        if args.dry_run:
            print("✅ Dry-run 模式：不進行任何刪除。")
            session.rollback()
            sys.exit(0)

        if not args.force:
            ans = input("確定要刪除嗎？(yes/NO): ").strip().lower()
            if ans not in ("y", "yes"):
                print("已取消。")
                session.rollback()
                sys.exit(0)

        # 真正刪除
        try:
            # 在一個交易中處理所有目標 id
            with session.begin():
                if args.delete_copies:
                    # 先刪葉子，再刪根（由列表尾端開始）
                    for mid in reversed(delete_id_list):
                        delete_one_material(session, mid, set_children_copies_null=False)
                else:
                    # 僅刪指定 id，並把其他 child copies 設為 NULL
                    delete_one_material(session, args.id, set_children_copies_null=True)

            print("🗑️ 刪除完成。")
        except SQLAlchemyError as se:
            session.rollback()
            print(f"❌ 刪除失敗（已回滾）: {se}")
            sys.exit(2)

    finally:
        session.close()


if __name__ == "__main__":
    main()
