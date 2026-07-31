# -*- coding: utf-8 -*-
"""
🦞 IT 问题知识库 — Streamlit 应用

启动：streamlit run app/app.py
数据库：GitHub 仓库（Markdown + YAML front matter），本地缓存于 entries/
内容：文字 / 图片(![[assets/x.png]]) / 链接 / 代码块，全部支持
"""
from __future__ import annotations

import datetime
import html
import os
import re
import sys
from pathlib import Path

import pytz
import streamlit as st

_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from app import storage, renderer  # noqa: E402

DEFAULT_CATEGORIES = storage._DEFAULT_CATEGORIES  # noqa: SLF001
PAGE_SIZE = 10


def _now_local() -> str:
    return datetime.datetime.now(
        pytz.timezone(os.environ.get("KB_TZ", "Asia/Shanghai"))
    ).strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------ 初始化 / 样式
st.set_page_config(page_title="IT 问题知识库", page_icon="🦞",
                   layout="wide", initial_sidebar_state="expanded")

_CSS = """
<style>
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#071022,#0b1220); }
[data-testid="stSidebar"] * { color:#e2e8f0; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
[data-testid="stSidebar"] textarea { background:#0f172a!important;color:#e2e8f0!important;border:1px solid #334155!important; }
[data-testid="stSidebar"] .stButton button { background:#00b4d8;color:#001018;border:none;font-weight:600;border-radius:8px; }
[data-testid="stSidebar"] .stButton button:hover { background:#00e5ff; }
.kb-title { font-size:26px;font-weight:800;color:#7dd3fc;letter-spacing:1px; }
.kb-sub { color:#64748b;font-size:12px;margin-top:-6px; }
.kb-card { background:#ffffff;border:1px solid #e2e8f0;border-left:4px solid #00b4d8;border-radius:10px;padding:8px 16px;margin:10px 0; }
.kb-meta { color:#64748b;font-size:12px; }
.kb-cat { display:inline-block;background:#e0f2fe;color:#0369a1;font-size:11px;padding:1px 8px;border-radius:10px;margin-right:6px; }
.kb-tag { display:inline-block;background:#f1f5f9;color:#475569;font-size:11px;padding:1px 8px;border-radius:10px;margin-right:4px; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------- 查询参数
params = st.query_params
page = params.get("p", "kb")
entry_q = params.get("e", "")


def go_kb():
    st.query_params.update({"p": "kb"})
    st.query_params.pop("e", None)


def go_detail(eid: str):
    st.query_params.update({"p": "detail", "e": eid})


def go_admin(eid: str = ""):
    st.query_params.update({"p": "admin"})
    if eid:
        st.query_params.update({"e": eid})
    else:
        st.query_params.pop("e", None)


# ------------------------------------------------------------ 侧边栏
with st.sidebar:
    st.markdown('<div class="kb-title">🦞 IT 知识库</div>', unsafe_allow_html=True)
    st.markdown('<div class="kb-sub">GitHub 即数据库 · 文字 / 图片 / 链接</div>',
                unsafe_allow_html=True)
    st.divider()

    entries_all = storage.load_entries()

    search_kw = st.text_input("🔍 搜索", placeholder="标题 / 标签 / 关键词 / 正文…")

    cats_all = []
    for e in entries_all:
        c = e.get("category") or "其他"
        if c not in cats_all:
            cats_all.append(c)
    cat_opt = ["全部"] + cats_all
    sel_cat = st.selectbox("📂 分类", cat_opt,
                           index=cat_opt.index(params.get("c", "全部"))
                           if params.get("c", "全部") in cat_opt else 0)

    # 标签筛选（从当前分类的条目提取）
    tag_pool = []
    for e in entries_all:
        if sel_cat == "全部" or (e.get("category") or "其他") == sel_cat:
            tag_pool.extend(e.get("tags", []))
    tag_pool = list(dict.fromkeys(tag_pool))
    sel_tags = set(st.multiselect("🏷 标签筛选", tag_pool,
                                  placeholder="选择标签…") or [])

    sort_by = st.selectbox("↕ 排序",
                           ["最近更新", "浏览最多", "标题 A→Z", "创建时间"])

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("🏠 知识库", width="stretch"):
        go_kb(); st.rerun()
    if c2.button("⚙️ 管理", width="stretch"):
        go_admin(); st.rerun()

    st.divider()
    total_v = sum(e.get("views", 0) for e in entries_all)
    st.markdown(
        f"📚 **{len(entries_all)}** 篇 · 👁 **{total_v}** 次浏览"
        f'<br><span class="kb-meta">本地 {_now_local()}</span>',
        unsafe_allow_html=True)
    gh = storage.gh_cfg()
    st.caption(f"🐙 GitHub: `{gh['repo']}`" if gh else "🐙 GitHub 同步未配置")


# ------------------------------------------------------------ 公共函数
def filter_entries(entries: list) -> list:
    kw = search_kw.strip().lower()
    out = list(entries)
    if sel_cat != "全部":
        out = [e for e in out if (e.get("category") or "其他") == sel_cat]
    if sel_tags:
        out = [e for e in out if sel_tags.issubset(set(e.get("tags", [])))]
    if kw:
        terms = [t for t in re.split(r"[\s,，、]+", kw) if t]
        def hit(e):
            title = e.get("title", "").lower()
            tags = " ".join(e.get("tags", [])).lower()
            kws = " ".join(e.get("keywords", [])).lower()
            body = e.get("body", "")[:3000].lower()
            # 全部关键词都命中才算
            for t in terms:
                if t in title or t in tags or t in kws:
                    continue
                if t not in body:
                    return False
            return True
        out = [e for e in out if hit(e)]
    if sort_by == "最近更新":
        out.sort(key=lambda e: (e.get("updated") or e.get("created") or ""),
                 reverse=True)
    elif sort_by == "浏览最多":
        out.sort(key=lambda e: e.get("views", 0), reverse=True)
    elif sort_by == "标题 A→Z":
        out.sort(key=lambda e: e.get("title", ""))
    else:
        out.sort(key=lambda e: e.get("created") or "", reverse=True)
    return out


def _retry(seconds: float):
    import time
    time.sleep(seconds)
    st.rerun()


# ------------------------------------------------------------ 页面：详情
def render_detail(eid: str):
    e = storage.get_entry(eid)
    if not e:
        st.error("条目不存在或已被删除")
        if st.button("返回列表"):
            go_kb(); st.rerun()
        return

    if st.session_state.get("viewed") != eid:
        e["views"] = int(e.get("views", 0)) + 1
        storage.save_entry(e)
        st.session_state["viewed"] = eid

    c1, c2, _ = st.columns([1, 1, 6])
    if c1.button("← 返回", width="stretch"):
        go_kb(); st.rerun()
    if c2.button("✏️ 编辑", width="stretch"):
        go_admin(eid); st.rerun()

    st.markdown(f"## {e['title']}")
    st.markdown(
        f'<span class="kb-cat">{e.get("category") or "其他"}</span>'
        + "".join(f'<span class="kb-tag">#{t}</span>' for t in e.get("tags", []))
        + f'<br><span class="kb-meta">👤 {e.get("author", "-")} · 🕒 更新 {e.get("updated", "-")} · 👁 {e.get("views", 0)} 次 · ID {eid}</span>',
        unsafe_allow_html=True)
    st.divider()

    col_main, col_toc = st.columns([3, 1])
    with col_main:
        renderer.render_content(e.get("body", ""), e.get("attachment"), "detail")
    with col_toc:
        toc = renderer.toc_from_body(e.get("body", ""))
        if toc:
            st.markdown("**📑 目录**")
            for lv, t in toc[:12]:
                st.markdown(f"{'&nbsp;' * 4 * (lv - 1)}- {t}",
                            unsafe_allow_html=True)

    # 相关文章推荐（同分类/同标签）
    st.divider()
    st.markdown("**🔗 相关文章**")
    related = []
    my_tags = set(e.get("tags", []))
    for other in entries_all:
        if other["id"] == eid:
            continue
        score = 0
        if other.get("category") == e.get("category"):
            score += 1
        score += len(my_tags & set(other.get("tags", [])))
        if score > 0:
            related.append((score, other))
    related.sort(key=lambda x: -x[0])
    if related:
        cols = st.columns(min(4, len(related[:4])))
        for i, (score, r) in enumerate(related[:4]):
            with cols[i]:
                st.markdown(
                    f'<div class="kb-card" style="padding:6px 10px;margin:4px 0;">'
                    f'<b style="font-size:13px;">{r["title"][:24]}</b><br>'
                    f'<span class="kb-meta">👁 {r.get("views", 0)} · {r.get("updated") or r.get("created", "-")[:10]}</span></div>',
                    unsafe_allow_html=True)
                if st.button("阅读", key=f"rel_{r['id']}", width="stretch"):
                    go_detail(r["id"]); st.rerun()
    else:
        st.caption("暂无相关文章")


def _entry_summary(e: dict, n: int = 90) -> str:
    """从正文提取摘要（去 markdown 标记）"""
    body = e.get("body", "")
    body = re.sub(r"!\[\[[^\]]+\]\]", "", body)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"[#>*`\[\]]", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:n]


# ------------------------------------------------------------ 页面：知识库列表
def render_kb():
    entry_id = params.get("e", "")
    if entry_id and storage.get_entry(entry_id):
        render_detail(entry_id)
        return

    entries = filter_entries(entries_all)
    st.markdown(
        f"**共 {len(entries)} 篇**"
        + (f"（搜索「{search_kw}」）" if search_kw.strip() else "")
        + (f"（分类：{sel_cat}）" if sel_cat != "全部" else "")
        + (f"（标签：{'、'.join(sorted(sel_tags))}）" if sel_tags else ""))
    if not entries:
        st.info("没有匹配的条目。换个关键词，或到「⚙️ 管理」新建一篇。")
        return

    pg = int(st.session_state.get("pg", 1))
    import math
    total_pages = max(1, math.ceil(len(entries) / PAGE_SIZE))
    pg = min(pg, total_pages)
    page_entries = entries[(pg - 1) * PAGE_SIZE: pg * PAGE_SIZE]

    for e in page_entries:
        with st.container():
            hl, hb = st.columns([6, 1])
            with hl:
                summ = _entry_summary(e)
                st.markdown(
                    f'<div class="kb-card"><b style="font-size:16px;">{e["title"]}</b><br>'
                    f'<span class="kb-cat">{e.get("category") or "其他"}</span>'
                    + "".join(f'<span class="kb-tag">#{t}</span>' for t in e.get("tags", [])[:4])
                    + (f'<br><span class="kb-meta">{html.escape(summ)}…</span>' if summ else "")
                    + f'<br><span class="kb-meta">👁 {e.get("views", 0)} · 🕒 {e.get("updated") or e.get("created", "-")}</span></div>',
                    unsafe_allow_html=True)
            with hb:
                st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
                if st.button("查看详情", key=f"open_{e['id']}",
                             width="stretch"):
                    go_detail(e["id"]); st.rerun()

    if total_pages > 1:
        p1, p2, p3 = st.columns([1, 2, 1])
        if p1.button("◀ 上一页", disabled=pg <= 1):
            st.session_state["pg"] = pg - 1; st.rerun()
        p2.markdown(f"<center class='kb-meta'>第 {pg} / {total_pages} 页</center>",
                    unsafe_allow_html=True)
        if p3.button("下一页 ▶", disabled=pg >= total_pages):
            st.session_state["pg"] = pg + 1; st.rerun()


# ------------------------------------------------------------ 页面：管理
def _to_csv_line(items) -> str:
    return ", ".join(i.strip() for i in items if str(i).strip())


def render_admin():
    st.header("⚙️ 知识库管理")

    # 管理员可选密码
    try:
        admin_pw = st.secrets.get("admin_password", "")
    except Exception:
        admin_pw = ""
    if admin_pw and st.session_state.get("admin_ok") is not True:
        with st.form("login"):
            st.subheader("🔐 管理员登录")
            pwd = st.text_input("管理密码", type="password")
            if st.form_submit_button("登录"):
                if pwd == admin_pw:
                    st.session_state["admin_ok"] = True
                    st.rerun()
                else:
                    st.error("密码错误")
        st.stop()

    entries = storage.load_entries(force=False)
    by_id = {e["id"]: e for e in entries}
    opts = ["➕ 新建条目"] + [f"{e['title']}（{e['id']}）" for e in entries]
    cur_id = params.get("e", "")
    default_i = 0
    if cur_id and cur_id in by_id:
        default_i = entries.index(by_id[cur_id]) + 1
    sel = st.selectbox("选择条目", opts, index=default_i)
    cur = by_id[cur_id] if (sel != opts[0] and cur_id in by_id) else None
    if sel != opts[0] and cur is None:
        m = re.search(r"（(.+)）$", sel)
        cur = by_id.get(m.group(1)) if m else None

    with st.form("edit", clear_on_submit=False):
        st.subheader("✏️ 编辑" if cur else "🆕 新建条目")
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("标题 *", value=cur["title"] if cur else "")
            exist_cats = list(dict.fromkeys(
                [e.get("category") for e in entries if e.get("category")]
                + DEFAULT_CATEGORIES))
            cat = st.selectbox(
                "分类 *", exist_cats,
                index=exist_cats.index(cur.get("category"))
                if cur and cur.get("category") in exist_cats else 0)
            tags = st.text_input("标签（逗号分隔）",
                                 value=_to_csv_line(cur.get("tags", [])) if cur else "")
        with c2:
            author = st.text_input("作者",
                                   value=cur.get("author", "") if cur else "Boss")
            keywords = st.text_input(
                "搜索关键词（逗号分隔，不展示）",
                value=_to_csv_line(cur.get("keywords", [])) if cur else "")
            attachment = st.text_input("附件（attachments/xxx、assets/xxx 或 URL，可空）",
                                       value=cur.get("attachment") or "" if cur else "")

        preview = st.toggle("👁 实时预览", value=True)
        c_body, c_prev = st.columns(2)
        with c_body:
            body = st.text_area(
                "正文（Markdown）*",
                value=cur.get("body", "") if cur else "",
                height=430,
                placeholder=(
                    "## 现象\n…\n## 排查\n1. 报错截图：![[assets/err.png]]\n"
                    "2. 参考：<https://learn.microsoft.com/>\n"
                    "```powershell\nipconfig /flushdns\n```"))
        if preview:
            with c_prev:
                renderer.render_content(body, None, "preview")

        imgs = st.file_uploader(
            "🖼 上传配图（可多选）",
            type=["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp"],
            accept_multiple_files=True)

        atch = st.file_uploader(
            "📎 上传附件（PDF/Excel/JSON/压缩包等，可多选）",
            type=None,
            accept_multiple_files=True)

        c_save, c_push, _ = st.columns([1, 1, 4])
        btn_save = c_save.form_submit_button("💾 保存", width="stretch")
        btn_save_push = c_push.form_submit_button("💾➕🐙 保存并推送 GitHub",
                                                  width="stretch")

    if btn_save or btn_save_push:
        if not title.strip():
            st.error("标题不能为空"); st.stop()
        if not body.strip():
            st.error("正文不能为空"); st.stop()
        eid = (cur["id"] if cur else None) or storage.slugify(title)
        now = _now_local()
        entry = {
            "id": eid, "title": title.strip(), "category": cat,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
            "author": author.strip() or "系统",
            "attachment": attachment.strip() or None,
            "created": (cur or {}).get("created") or now,
            "updated": now, "views": int((cur or {}).get("views", 0)),
            "body": body,
        }
        storage.save_entry(entry)
        for f in imgs or []:
            rel = storage.save_asset_file(f.name, f.getvalue())
            st.toast(f"🖼 已保存配图 {rel}", icon="🖼")
        for f in atch or []:
            rel = storage.save_attachment_file(f.name, f.getvalue())
            st.toast(f"📎 已保存附件 {rel}", icon="📎")
        st.success(f"✅ 已保存：{entry['title']}（{eid}）")
        if btn_save_push:
            ok, msg = storage.push_entry_to_github(eid)
            (st.success if ok else st.warning)(f"GitHub：{msg}")
        go_kb(); _retry(0.3)

    # ---- 操作区
    st.divider()
    st.subheader("🗂 条目操作")
    a, b, c = st.columns(3)
    with a:
        del_opts = ["- 选择要删除的条目 -"] + [f"{e['title']}（{e['id']}）" for e in entries]
        dsel = st.selectbox("删除条目", del_opts, label_visibility="collapsed")
        if dsel != del_opts[0]:
            with st.popover("🗑 确认删除？", width="stretch"):
                st.warning("删除后不可恢复！" + ("（不影响 GitHub 上的副本）" if gh_cfg() else ""))
                dc1, dc2 = st.columns(2)
                if dc1.button("❌ 取消", width="stretch"):
                    st.rerun()
                if dc2.button("🗑 确认删除", width="stretch"):
                    m = re.search(r"（(.+)）$", dsel)
                    if m:
                        storage.delete_entry(m.group(1))
                        if storage.gh_cfg():
                            ok, msg = storage.remove_entry_from_github(m.group(1))
                            st.toast(f"GitHub：{msg}",
                                     icon="✅" if ok else "⚠️")
                        st.success("已删除"); _retry(0.3)

    with b:
        st.markdown("**🖼 图库**（assets/）")
        assets = storage.list_assets()
        if not assets:
            st.caption("暂无配图。编辑条目时上传，或放入 entries/assets/。")
        else:
            pick = st.selectbox("选择图片", assets)
            p = storage.DATA_DIR / "assets" / pick
            st.image(str(p), width="stretch")
            st.code(f"![[{pick}]]  或  <img src=\"assets/{pick}\">", language="markdown")
        st.markdown("**📎 附件库**（attachments/）")
        atts = storage.list_attachments()
        if not atts:
            st.caption("暂无附件。编辑条目时上传，或放入 entries/attachments/。")
        else:
            apick = st.selectbox("选择附件", atts, key="att_pick")
            ap = storage.DATA_DIR / "attachments" / apick
            st.caption(f"{apick}（{ap.stat().st_size / 1024:.0f} KB）")
            st.code(f"attachment: attachments/{apick}", language="yaml")

    with c:
        st.markdown("**🐙 GitHub 同步**")
        if storage.gh_cfg():
            cc1, cc2 = st.columns(2)
            if cc1.button("⬆️ 推送全部", width="stretch"):
                with st.spinner("推送中…"):
                    ok, fail, msg = storage.push_all_to_github()
                (st.success if fail == 0 else st.warning)(msg)
            if cc2.button("⬇️ 拉取仓库", width="stretch"):
                with st.spinner("拉取中…"):
                    n, msg = storage.pull_all_from_github()
                st.success(msg); _retry(0.5)
            st.caption("配置：`.streamlit/secrets.toml` → `[github]` token/repo/branch")
        else:
            st.info("未配置 GitHub。填写 `.streamlit/secrets.toml` 后重启即可启用：\n"
                    "```toml\n[github]\ntoken=\"ghp_...\"\nrepo=\"you/it-kb\"\nbranch=\"main\"\n```")


def gh_cfg():
    return storage.gh_cfg()


# ------------------------------------------------------------ 路由
if page == "detail":
    render_detail(entry_q)
elif page == "admin":
    render_admin()
else:
    render_kb()
