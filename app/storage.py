# -*- coding: utf-8 -*-
"""
存储层：本地磁盘读写为主，可选同步到 GitHub（GitHub 即数据库）

知识库目录约定（仓库结构）：
    entries/           —— 条目正文，Markdown 文件（内含 YAML front matter）
    entries/index.json —— 索引缓存（可选，缺失时自动重建）
    entries/assets/    —— 图片资源，用 ![[assets/xxx.png]] 在正文中引用
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import re
import time
from pathlib import Path

import pytz
import requests
import streamlit as st
import yaml

DATA_DIR = Path(os.environ.get("KB_DATA_DIR", "entries"))
INDEX_CACHE = DATA_DIR / "index.json"

_DEFAULT_CATEGORIES = [
    "network", "server", "desktop", "security",
    "database", "cloud", "software", "other",
    "ss-system",
]

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


# ---------------------------------------------------------------- base/meta
def _tz_now() -> str:
    tz = pytz.timezone(os.environ.get("KB_TZ", "Asia/Shanghai"))
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")


def slugify(text: str) -> str:
    """以中文为主的标题保留中文字符，其余转小写连字符。"""
    s = text.strip().lower()
    s = re.sub(r"[^0-9a-z一-鿿]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or f"entry-{int(time.time())}"


def parse_entry_text(text: str, default_id: str, file_path: Path | None = None) -> dict:
    """解析带 front matter 的 Markdown 文本 -> 条目字典"""
    meta, body = {}, text
    m = FRONT_MATTER_RE.match(text)
    if m:
        meta_str = m.group(1)
        try:
            meta = yaml.safe_load(meta_str) or {}
        except Exception:
            # YAML 失败（如 title 以 @ 开头）→ 降级：逐行解析 key: value
            meta = {}
            for line in meta_str.splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition(":")
                    k, v = k.strip(), v.strip()
                    if not k:
                        continue
                    if v.startswith("[") and v.endswith("]"):
                        v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                    elif v in ("true", "false"):
                        v = v == "true"
                    elif v.isdigit():
                        v = int(v)
                    meta[k] = v
        body = m.group(2)
    eid = str(meta.get("id") or default_id)
    return {
        "id": eid,
        "title": str(meta.get("title") or eid),
        "category": str(meta.get("category") or "other"),
        "tags": [str(t) for t in (meta.get("tags") or [])],
        "keywords": [str(k) for k in (meta.get("keywords") or [])],
        "author": str(meta.get("author") or ""),
        "attachment": meta.get("attachment"),
        "created": str(meta.get("created") or ""),
        "updated": str(meta.get("updated") or ""),
        "views": int(meta.get("views") or 0),
        "body": body,
        "path": (file_path or DATA_DIR.joinpath(f"{eid}.md")).as_posix(),
    }


def serialize_entry(entry: dict) -> str:
    meta = {
        "id": entry["id"],
        "title": entry["title"],
        "category": entry["category"],
        "tags": entry.get("tags", []),
        "keywords": entry.get("keywords", []),
        "author": entry.get("author", ""),
        "created": entry.get("created", ""),
        "updated": entry.get("updated", ""),
        "views": int(entry.get("views", 0)),
    }
    if entry.get("attachment"):
        meta["attachment"] = entry["attachment"]
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)
    return f"---\n{fm}---\n\n{entry.get('body', '')}"


def entry_index(entry: dict) -> dict:
    return {k: entry[k] for k in
            ("id", "title", "category", "tags", "keywords", "author",
             "created", "updated", "views", "path")}


# ------------------------------------------------------------------ 本地 IO
def _read_index_cache() -> list | None:
    try:
        if INDEX_CACHE.exists():
            data = json.loads(INDEX_CACHE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    return None


def _write_index_cache(entries: list) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_CACHE.write_text(
            json.dumps([entry_index(e) for e in entries],
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
    except Exception:
        pass


def _scan_from_disk(limit: int = 2000) -> list:
    entries = []
    if not DATA_DIR.exists():
        return entries
    for p in sorted(DATA_DIR.rglob("*.md")):
        # 跳过非条目目录（如 pending/ 草稿）
        if "pending" in p.parts:
            continue
        try:
            entries.append(parse_entry_text(
                p.read_text(encoding="utf-8"), p.stem, p))
            if len(entries) >= limit:
                break
        except Exception:
            continue
    entries.sort(key=lambda e: (e.get("updated") or e.get("created") or ""),
                 reverse=True)
    return entries


def _dedupe(entries: list) -> list:
    seen, out = set(), []
    for e in entries:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return out


def load_entries(force: bool = False, limit: int = 2000) -> list:
    cache = [] if force else _read_index_cache()
    if cache:
        keep = {c["id"] for c in cache}
        recent = _scan_from_disk(limit=60)
        merged = {e["id"]: e for e in cache}
        for e in recent:
            merged[e["id"]] = e
        entries = [e for e in merged.values() if e["id"] in keep or e in recent]
        return _dedupe(entries)
    entries = _scan_from_disk(limit=limit)
    if entries:
        _write_index_cache(entries)
    return entries


def get_entry(entry_id: str) -> dict | None:
    # 1. 根目录直查
    p = DATA_DIR / f"{entry_id}.md"
    if p.exists():
        try:
            return parse_entry_text(p.read_text(encoding="utf-8"), entry_id, p)
        except Exception:
            pass
    # 2. 全盘搜索（含子目录）
    if DATA_DIR.exists():
        for p in DATA_DIR.rglob(f"{entry_id}.md"):
            if "pending" in p.parts:
                continue
            try:
                return parse_entry_text(p.read_text(encoding="utf-8"), entry_id, p)
            except Exception:
                continue
    # 3. 从索引找 path 再读磁盘（保证 body 完整）
    try:
        for e in load_entries():
            if e["id"] == entry_id:
                fp = Path(e.get("path") or "")
                if fp.is_file():
                    return parse_entry_text(fp.read_text(encoding="utf-8"), entry_id, fp)
                return e
    except Exception:
        pass
    return None


def save_entry(entry: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # 优先使用条目自带路径（支持子目录），否则根目录
    p = Path(entry.get("path") or DATA_DIR.joinpath(f"{entry['id']}.md"))
    if not str(p).startswith(str(DATA_DIR.resolve())):
        p = DATA_DIR / f"{entry['id']}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(serialize_entry(entry), encoding="utf-8")
    st.cache_data.clear()


def delete_entry(entry_id: str) -> None:
    # 全目录搜索（含子目录）
    if DATA_DIR.exists():
        for p in DATA_DIR.rglob(f"{entry_id}.md"):
            if "pending" in p.parts:
                continue
            try:
                p.unlink()
            except Exception:
                pass
    st.cache_data.clear()


def list_assets() -> list[str]:
    adir = DATA_DIR / "assets"
    if not adir.exists():
        return []
    return sorted(p.name for p in adir.iterdir() if p.is_file())


def list_attachments() -> list[str]:
    adir = DATA_DIR / "attachments"
    if not adir.exists():
        return []
    return sorted(p.name for p in adir.iterdir() if p.is_file())


def save_attachment_file(name: str, data: bytes) -> str:
    safe = re.sub(r"[^\w.\-一-鿿]", "_", name)
    adir = DATA_DIR / "attachments"
    adir.mkdir(parents=True, exist_ok=True)
    (adir / safe).write_bytes(data)
    return f"attachments/{safe}"


def save_asset_file(name: str, data: bytes) -> str:
    safe = re.sub(r"[^\w.\-一-鿿]", "_", name)
    adir = DATA_DIR / "assets"
    adir.mkdir(parents=True, exist_ok=True)
    (adir / safe).write_bytes(data)
    return f"assets/{safe}"


# --------------------------------------------------------------- GitHub 同步
def gh_cfg() -> dict | None:
    try:
        c = dict(st.secrets.get("github", {}))
    except Exception:
        c = {}
    if c.get("token") and c.get("repo"):
        return c
    tok = os.environ.get("GITHUB_TOKEN")
    rep = os.environ.get("GITHUB_REPO")
    if tok and rep:
        return {
            "token": tok, "repo": rep,
            "branch": os.environ.get("GITHUB_BRANCH", "main"),
            "entries_path": os.environ.get("GITHUB_ENTRIES_PATH", "entries"),
        }
    return None


def _gh_headers(cfg: dict) -> dict:
    return {
        "Authorization": f"token {cfg['token']}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _gh_url(cfg: dict, path: str) -> str:
    return f"https://api.github.com/repos/{cfg['repo']}/contents/{path.lstrip('/')}"


def _gh_put(cfg: dict, gh_path: str, content: bytes, message: str,
            expect_file: str | None = None) -> None:
    """创建或更新 GitHub 文件；sha 冲突时自动重试一次"""
    r = requests.put(
        _gh_url(cfg, gh_path),
        headers=_gh_headers(cfg),
        json={
            "message": message,
            "content": base64.b64encode(content).decode(),
            "branch": cfg.get("branch", "main"),
        },
        timeout=30,
    )
    if r.status_code == 422 and expect_file:
        cur = requests.get(_gh_url(cfg, gh_path), headers=_gh_headers(cfg),
                           timeout=15)
        if cur.status_code == 200:
            requests.put(
                _gh_url(cfg, gh_path),
                headers=_gh_headers(cfg),
                json={
                    "message": message,
                    "content": base64.b64encode(content).decode(),
                    "sha": cur.json()["sha"],
                    "branch": cfg.get("branch", "main"),
                },
                timeout=30,
            ).raise_for_status()
            return
    r.raise_for_status()


def _gh_delete(cfg: dict, gh_path: str, message: str) -> None:
    cur = requests.get(_gh_url(cfg, gh_path), headers=_gh_headers(cfg),
                       timeout=15)
    if cur.status_code == 404:
        return
    cur.raise_for_status()
    requests.request(
        "DELETE", _gh_url(cfg, gh_path),
        headers=_gh_headers(cfg),
        json={
            "message": message,
            "sha": cur.json()["sha"],
            "branch": cfg.get("branch", "main"),
        },
        timeout=30,
    ).raise_for_status()


def push_entry_to_github(entry_id: str, with_assets: bool = True) -> tuple[bool, str]:
    cfg = gh_cfg()
    if not cfg:
        return False, "未配置 GitHub（secrets.toml 的 [github] 段）"
    entry = get_entry(entry_id)
    if not entry:
        return False, f"本地不存在条目 {entry_id}"
    base = cfg.get("entries_path", "entries").strip("/")
    try:
        _gh_put(
            cfg, f"{base}/{entry_id}.md",
            serialize_entry(entry).encode("utf-8"),
            f"docs(kb): update {entry_id} [{entry.get('updated', '')}]",
            expect_file=f"{entry_id}.md",
        )
        if with_assets:
            assets = re.findall(r"!\[\[[^\]|]*?(assets/[^\]|\s]+)[^\]]*\]\]",
                                entry.get("body", ""))
            if entry.get("attachment"):
                assets.append(entry["attachment"])
            pushed = set()
            for rel in dict.fromkeys(assets):
                if rel in pushed:
                    continue
                rel = rel.lstrip("/")
                if rel.startswith("assets/"):
                    local = DATA_DIR / rel
                elif rel.startswith("attachments/"):
                    local = DATA_DIR.parent / rel
                else:
                    local = DATA_DIR.parent / rel
                if local.is_file():
                    _gh_put(
                        cfg, f"{base}/{rel}", local.read_bytes(),
                        f"assets(kb): {rel}", expect_file=rel,
                    )
                    pushed.add(rel)
        return True, "已推送到 GitHub"
    except Exception as e:
        return False, f"GitHub 推送失败：{e}"


def push_all_to_github() -> tuple[int, int, str]:
    cfg = gh_cfg()
    if not cfg:
        return 0, 0, "未配置 GitHub"
    ok = fail = 0
    base = cfg.get("entries_path", "entries").strip("/")
    entries = load_entries(force=True)
    for e in entries:
        try:
            _gh_put(
                cfg, f"{base}/{e['id']}.md",
                serialize_entry(e).encode("utf-8"),
                f"docs(kb): update {e['id']}",
                expect_file=f"{e['id']}.md",
            )
            ok += 1
        except Exception:
            fail += 1
    try:
        _write_index_cache(entries)
        _gh_put(
            cfg, f"{base}/index.json",
            INDEX_CACHE.read_bytes(),
            "chore(kb): rebuild index",
            expect_file="index.json",
        )
    except Exception:
        pass
    adir = DATA_DIR / "assets"
    if adir.exists():
        for p in adir.iterdir():
            if p.is_file():
                try:
                    _gh_put(cfg, f"{base}/assets/{p.name}", p.read_bytes(),
                            f"assets(kb): {p.name}", expect_file=p.name)
                except Exception:
                    fail += 1
    return ok, fail, f"完成：成功 {ok}，失败 {fail}"


def pull_all_from_github() -> tuple[int, str]:
    cfg = gh_cfg()
    if not cfg:
        return 0, "未配置 GitHub"
    base = cfg.get("entries_path", "entries").strip("/")
    try:
        r = requests.get(_gh_url(cfg, base), headers=_gh_headers(cfg),
                         timeout=20)
        r.raise_for_status()
        items = r.json()
        if isinstance(items, dict):
            items = [items]
    except Exception as e:
        return 0, f"读取仓库失败：{e}"
    n = 0
    for it in items:
        if it.get("type") != "file" or not it.get("name", "").endswith(".md"):
            continue
        try:
            fr = requests.get(it["url"], headers=_gh_headers(cfg), timeout=20)
            fr.raise_for_status()
            content = base64.b64decode(fr.json()["content"])
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            (DATA_DIR / it["name"]).write_bytes(content)
            n += 1
        except Exception:
            continue
    st.cache_data.clear()
    if n:
        _write_index_cache(_scan_from_disk())
    return n, f"拉取完成：{n} 个条目"


def remove_entry_from_github(entry_id: str) -> tuple[bool, str]:
    cfg = gh_cfg()
    if not cfg:
        return False, "未配置 GitHub"
    base = cfg.get("entries_path", "entries").strip("/")
    try:
        _gh_delete(cfg, f"{base}/{entry_id}.md", f"docs(kb): remove {entry_id}")
        return True, "已删除"
    except Exception as e:
        return False, f"删除失败：{e}"
