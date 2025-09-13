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
- Place this script in the same folder as your `tables.py`, or under `server/` while `tables.py` is in `server/database/`.
- This version uses a READ session for inspection and a fresh WRITE session for deletion, to avoid
  "A transaction is already begun on this Session." in SQLAlchemy 1.4/2.0.
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

from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import SQLAlchemyError

# Import models & session from your project, with fallbacks
try:
    # 1) simple import (tables.py on sys.path)
    from database.tables import (
        Session,
        Material,
        Bom,
        Assemble,
        Process,
    )
    try:
        from database.tables import Product  # optional
    except Exception:
        Product = None
    try:
        from database.tables import association_material_abnormal  # optional m2m
    except Exception:
        association_material_abnormal = None

except Exception:
    try:
        # 2) package-style import: database/tables.py
        from database.tables import (
            Session,
            Material,
            Bom,
            Assemble,
            Process,
        )
        try:
            from database.tables import Product  # optional
        except Exception:
            Product = None
        try:
            from database.tables import association_material_abnormal  # optional
        except Exception:
            association_material_abnormal = None
    except Exception as e:
        print("❌ 無法匯入 tables.py，請確認路徑：", file=sys.stderr)
        print("   - 期待路徑：<project>/server/database/tables.py", file=sys.stderr)
        print("   - 嘗試過的匯入：'tables' 與 'database.tables'", file=sys.stderr)
        print("   - 當前 sys.path：", file=sys.stderr)
        for i, pth in enumerate(sys.path):
            print(f"     {i}: {pth}", file=sys.stderr)
        print(f"Import error: {e}", file=sys.stderr)
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


def _count_table(session, table, *criterion):
    return session.execute(
        select(func.count()).select_from(table).where(*criterion)
    ).scalar_one()


def summarize_related_counts(session, material_id: int) -> dict:
    """統計關聯資料數量（BOM / Assemble / Product / Process / M2M / copies）。"""
    bom_cnt = _count_table(session, Bom,        Bom.material_id == material_id)
    asm_cnt = _count_table(session, Assemble,   Assemble.material_id == material_id)
    proc_cnt = _count_table(session, Process,   Process.material_id == material_id)

    prod_cnt = 0
    try:
        if Product is not None:
            prod_cnt = _count_table(session, Product, Product.material_id == material_id)
    except NameError:
        prod_cnt = 0

    m2m_cnt = 0
    try:
        if association_material_abnormal is not None:
            m2m_cnt = session.execute(
                select(func.count())
                .select_from(association_material_abnormal)
                .where(association_material_abnormal.c.material_id == material_id)
            ).scalar_one()
    except NameError:
        m2m_cnt = 0

    copies_cnt = _count_table(session, Material, Material.is_copied_from_id == material_id)

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
    if association_material_abnormal is not None:
        session.execute(
            delete(association_material_abnormal).where(
                association_material_abnormal.c.material_id == material_id
            )
        )
    # 2) 刪子表
    session.execute(delete(Process).where(Process.material_id == material_id))
    if Product is not None:
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

    # ---- Read-only session for inspection / confirmation ----
    s_read = Session()
    try:
        mat = s_read.get(Material, args.id)
        if not mat:
            print(f"⚠️ 找不到 Material.id={args.id}")
            return 1

        print(f"將處理 Material.id={args.id}, order_num={getattr(mat, 'order_num', None)}, material_num={getattr(mat, 'material_num', None)}")
        counts = summarize_related_counts(s_read, args.id)
        print(f"- 關聯數量: BOM={counts['bom']}, Assemble={counts['assemble']}, Product={counts['product']}, Process={counts['process']}, M2M_links={counts['abnormal_links']}, Copies(out)={counts['copies']}")

        if args.delete_copies:
            print("- 將遞迴刪除所有 'copied_to' 後代")
        else:
            print("- 不刪除 'copied_to' 同宗資料（若存在），會把它們的 is_copied_from_id 設為 NULL")

        if args.dry_run:
            ids = find_descendant_material_ids(s_read, args.id) if args.delete_copies else [args.id]
            print("✅ Dry-run 模式：不進行任何刪除。將受影響的 Material.id：", list(reversed(ids)) if args.delete_copies else ids)
            return 0
    finally:
        s_read.close()

    if not args.force:
        ans = input("確定要刪除嗎？(yes/NO): ").strip().lower()
        if ans not in ("y", "yes"):
            print("已取消。")
            return 0

    # ---- Write session in a single transaction (fresh session) ----
    try:
        if args.delete_copies:
            '''
            with Session.begin() as s:
                ids = find_descendant_material_ids(s, args.id)
                for mid in reversed(ids):  # 由葉 → 根
                    delete_one_material(s, mid, set_children_copies_null=False)
            print("🗑️ 刪除完成。Deleted ids:", list(reversed(ids)))
            '''

            # 遞迴刪 copies 的版本
            try:
                with Session() as s:
                    with s.begin():
                        ids = find_descendant_material_ids(s, args.id)
                        for mid in reversed(ids):  # 由葉 → 根
                            delete_one_material(s, mid, set_children_copies_null=False)
                print("🗑️ 刪除完成。Deleted ids:", list(reversed(ids)))
            except SQLAlchemyError as se:
                print(f"❌ 刪除失敗（已回滾）: {se}")

        else:
            '''
            with Session.begin() as s:
                delete_one_material(s, args.id, set_children_copies_null=True)
            print("🗑️ 刪除完成。Deleted ids:", [args.id])
            '''

            try:
                with Session() as s:
                    with s.begin():
                        delete_one_material(s, args.id, set_children_copies_null=True)
                print("🗑️ 刪除完成。Deleted ids:", [args.id])
            except SQLAlchemyError as se:
                print(f"❌ 刪除失敗（已回滾）: {se}")

        return 0
    except SQLAlchemyError as se:
        print(f"❌ 刪除失敗（已回滾）: {se}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
