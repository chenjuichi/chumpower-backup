# -*- coding: utf-8 -*-
"""
Blueprint: Delete Material & cascaded relations

Endpoints
---------
DELETE /api/materials/<id>?dry_run=0|1&delete_copies=0|1

Headers
-------
X-USER-ID: <your_user_id>    # 後端會用此值在 User 表查詢權限 (perm)，僅允許 {1,2}
# 若你已有 JWT / 自家認證 decorator，直接替換本檔的 `require_perms` 即可

Examples
--------
# 只看刪除影響範圍（不動資料）
curl -X DELETE "http://localhost:7010/api/materials/123?dry_run=1" -H "X-USER-ID: A001"

# 真的刪除（不遞迴刪除 copies）
curl -X DELETE "http://localhost:7010/api/materials/123" -H "X-USER-ID: A001"

# 真的刪除，且連帶刪除所有從此筆複製出去的 Material（遞迴）
curl -X DELETE "http://localhost:7010/api/materials/123?delete_copies=1" -H "X-USER-ID: A001"
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify
from functools import wraps
from typing import List, Set

from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import SQLAlchemyError

# --- Import your SQLAlchemy models & Session from tables.py ---
#   請確保本檔與 tables.py 在同一個模組可被匯入的路徑
from tables import Session, Material, Bom, Assemble, Process, User  # type: ignore

# 可選：專案若沒有以下物件，會自動跳過對應刪除步驟
try:
    from tables import Product  # type: ignore
except Exception:  # pragma: no cover
    Product = None

try:
    from tables import association_material_abnormal  # type: ignore
except Exception:  # pragma: no cover
    association_material_abnormal = None

bp = Blueprint("delete_material_api", __name__)

# ------------------------
# Permission integration
# ------------------------
def get_current_user(session) -> User | None:
    """最簡版：從 Header 讀 X-USER-ID，查 User 表。
    - 你的專案若已有 JWT / SSO，改用既有方法取使用者即可。
    """
    uid = request.headers.get("X-USER-ID")
    if not uid:
        return None
    return session.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()


def require_perms(allowed: Set[int] = {1, 2}):
    """允許 perm in allowed 的使用者呼叫端點。"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            s = Session()
            try:
                user = get_current_user(s)
                if not user:
                    return jsonify(success=False, error="UNAUTHENTICATED", message="缺少或無效的使用者識別 (X-USER-ID)"), 401
                if getattr(user, "perm", None) not in allowed:
                    return jsonify(success=False, error="FORBIDDEN", message="權限不足"), 403
                # 如需審計，可在這裡注入 request.current_user = user
                return fn(*args, **kwargs)
            finally:
                s.close()
        return wrapper
    return decorator


# ------------------------
# Helpers
# ------------------------
def find_descendant_material_ids(session, root_id: int) -> List[int]:
    """尋找所有 (transitively) is_copied_from_id 指向 root_id 的後代 Material.id，包含 root_id 本身。"""
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


def _count(session, stmt):
    return session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()


def summarize_related_counts(session, material_id: int) -> dict:
    """統計關聯數量（BOM / Assemble / Product / Process / M2M 連結 / copies）。"""
    bom_cnt = _count(session, select(Bom.id).where(Bom.material_id == material_id))
    asm_cnt = _count(session, select(Assemble.id).where(Assemble.material_id == material_id))
    proc_cnt = _count(session, select(Process.id).where(Process.material_id == material_id))

    prod_cnt = 0
    if Product is not None:
        prod_cnt = _count(session, select(Product.id).where(Product.material_id == material_id))

    m2m_cnt = 0
    if association_material_abnormal is not None:
        m2m_cnt = _count(
            session,
            select(association_material_abnormal.c.material_id).where(
                association_material_abnormal.c.material_id == material_id
            ),
        )

    copies_cnt = _count(session, select(Material.id).where(Material.is_copied_from_id == material_id))

    return {
        "bom": bom_cnt,
        "assemble": asm_cnt,
        "product": prod_cnt,
        "process": proc_cnt,
        "abnormal_links": m2m_cnt,
        "copies": copies_cnt,
    }


def delete_one_material(session, material_id: int, *, set_children_copies_null: bool) -> None:
    """刪除一筆 material 的所有關聯（children → parent）。"""
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

    # 3) 若不遞迴刪 copies，則解除它們對此筆的引用
    if set_children_copies_null:
        session.execute(
            update(Material)
            .where(Material.is_copied_from_id == material_id)
            .values(is_copied_from_id=None)
        )

    # 4) 刪主表
    session.execute(delete(Material).where(Material.id == material_id))


# ------------------------
# API Endpoint
# ------------------------
@bp.route("/materials/<int:material_id>", methods=["DELETE"])
@require_perms({1, 2})
def delete_material(material_id: int):
    """刪除指定 Material 與關聯資料。
    Query/Body 參數：
      - dry_run: 0|1  預覽刪除影響（不動資料）
      - delete_copies: 0|1  遞迴刪除該筆「複製出去」的所有後代 Material
    """
    # 支援 query string 與 JSON body 兩種傳值
    args = request.args or {}
    body = request.get_json(silent=True) or {}

    def as_bool(v, default=False):
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("1", "true", "yes", "y")

    dry_run = as_bool(args.get("dry_run", body.get("dry_run")), default=False)
    delete_copies = as_bool(args.get("delete_copies", body.get("delete_copies")), default=False)

    s = Session()
    try:
        mat = s.get(Material, material_id)
        if not mat:
            return jsonify(success=False, error="NOT_FOUND", message=f"找不到 Material.id={material_id}"), 404

        summary = summarize_related_counts(s, material_id)

        if dry_run:
            ids = find_descendant_material_ids(s, material_id) if delete_copies else [material_id]
            return jsonify(
                success=True,
                dry_run=True,
                material_id=material_id,
                will_delete_ids=(list(reversed(ids)) if delete_copies else ids),
                summary=summary,
            )

        try:
            if delete_copies:
                ids = find_descendant_material_ids(s, material_id)
                with s.begin():
                    for mid in reversed(ids):  # 由葉 → 根
                        delete_one_material(s, mid, set_children_copies_null=False)
                deleted_ids = list(reversed(ids))
            else:
                with s.begin():
                    delete_one_material(s, material_id, set_children_copies_null=True)
                deleted_ids = [material_id]

            return jsonify(
                success=True,
                deleted_ids=deleted_ids,
                summary=summary,
                message="刪除完成",
            )
        except SQLAlchemyError as se:
            s.rollback()
            return jsonify(success=False, error="DB_ERROR", message=str(se)), 500

    finally:
        s.close()
