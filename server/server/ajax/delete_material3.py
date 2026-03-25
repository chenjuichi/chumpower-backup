"""
提供函式呼叫：delete_material(material_id: int, delete_copies: bool=False) -> (bool, dict)

- 不需要 dry-run
- 不需要輸入確認
- 以「開新 Session → 開交易」的方式執行刪除，避免 nested transaction 問題
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict, Any

from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import SQLAlchemyError


# 確保可匯入到 tables.py（server/database）
THIS_DIR = Path(__file__).resolve().parent        # .../server/ajax
PROJECT_ROOT = THIS_DIR.parent                    # .../server
DB_DIR = PROJECT_ROOT / "database"                # .../server/database

for p in (THIS_DIR, PROJECT_ROOT, DB_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


# 模型匯入（雙重備援）
Session = Material = Bom = Assemble = Process = None  # type: ignore
Product = None
association_material_abnormal = None

try:
    from server.database.x_tables import Session, Material, Bom, Assemble, Process  # type: ignore
    try:
        from server.database.x_tables import Product  # type: ignore
    except Exception:
        Product = None
    try:
        from server.database.x_tables import association_material_abnormal  # type: ignore
    except Exception:
        association_material_abnormal = None
except Exception:
    try:
        from tables import Session, Material, Bom, Assemble, Process  # type: ignore
        try:
            from tables import Product  # type: ignore
        except Exception:
            Product = None
        try:
            from tables import association_material_abnormal  # type: ignore
        except Exception:
            association_material_abnormal = None
    except Exception as e:
        raise ImportError(f"無法匯入 tables.py：{e}")


def find_descendant_material_ids(session, root_id: int) -> List[int]:
    """尋找 is_copied_from_id 後代（含自身）。"""
    to_visit = [root_id]
    seen = {root_id}
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


def _count_table(session, table, *criterion) -> int:
    return session.execute(
        select(func.count()).select_from(table).where(*criterion)
    ).scalar_one()


def summarize_related_counts(session, material_id: int) -> Dict[str, int]:
    bom_cnt = _count_table(session, Bom,      Bom.material_id == material_id)
    asm_cnt = _count_table(session, Assemble, Assemble.material_id == material_id)
    proc_cnt = _count_table(session, Process, Process.material_id == material_id)

    prod_cnt = 0
    if Product is not None:
        prod_cnt = _count_table(session, Product, Product.material_id == material_id)

    m2m_cnt = 0
    if association_material_abnormal is not None:
        m2m_cnt = session.execute(
            select(func.count())
            .select_from(association_material_abnormal)
            .where(association_material_abnormal.c.material_id == material_id)
        ).scalar_one()

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
    """刪除 material 的所有關聯（children→parent）。"""
    # 1) 多對多連結
    if association_material_abnormal is not None:
        session.execute(
            delete(association_material_abnormal).where(
                association_material_abnormal.c.material_id == material_id
            )
        )
    # 2) 子表
    session.execute(delete(Process).where(Process.material_id == material_id))
    if Product is not None:
        session.execute(delete(Product).where(Product.material_id == material_id))
    session.execute(delete(Assemble).where(Assemble.material_id == material_id))
    session.execute(delete(Bom).where(Bom.material_id == material_id))

    # 3) 若不遞迴刪 copies，解除引用
    if set_children_copies_null:
        session.execute(
            update(Material)
            .where(Material.is_copied_from_id == material_id)
            .values(is_copied_from_id=None)
        )

    # 4) 主表
    session.execute(delete(Material).where(Material.id == material_id))


def delete_material(material_id: int, *, delete_copies: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """刪除指定 material_id 及其關聯資料。回傳 (success, result_dict)"""
    # 先檢查存在與摘要（使用短 session）
    print("delete_material3, delete_material()")

    with Session() as s_chk:
        mat = s_chk.get(Material, material_id)
        if not mat:
            return False, {"error": f"找不到 Material.id={material_id}"}
        summary = summarize_related_counts(s_chk, material_id)

    # 真正刪除（新 Session + 交易）
    try:
        print("delete_copies:", delete_copies)
        if delete_copies:
            with Session() as s:
                with s.begin():
                    ids = find_descendant_material_ids(s, material_id)
                    for mid in reversed(ids):  # 葉 → 根
                        delete_one_material(s, mid, set_children_copies_null=False)
            return True, {"deleted_ids": list(reversed(ids)), "summary": summary}
        else:
            with Session() as s:
                with s.begin():
                    delete_one_material(s, material_id, set_children_copies_null=True)
            return True, {"deleted_ids": [material_id], "summary": summary}
    except SQLAlchemyError as se:
        return False, {"error": str(se)}


if __name__ == "__main__":
    # 簡單 CLI：不做 dry-run / 不做確認
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int)
    parser.add_argument("--delete-copies", action="store_true")
    args = parser.parse_args()

    ok, res = delete_material(args.id, delete_copies=args.delete_copies)
    if ok:
        print("🗑️ 刪除完成：", res.get("deleted_ids"))
        sys.exit(0)
    else:
        print("❌ 刪除失敗：", res.get("error"))
        sys.exit(2)
