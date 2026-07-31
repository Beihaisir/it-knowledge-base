# -*- coding: utf-8 -*-
"""
渲染层：Markdown(文字/图片/链接) + 代码高亮 + Obsidian 风格图片

- 图片:  ![[assets/x.png]]  / ![](assets/x.png)  / ![alt](https://...)
- 附件卡片显示在正文末尾
- 本地图片以 base64 内嵌，保证任何部署环境都能显示
"""
from __future__ import annotations

import base64
import html
import re
from pathlib import Path

import streamlit as st

DATA_DIR = Path("entries")
PROJECT_ROOT = DATA_DIR.parent


def _resolve_asset(rel: str) -> Path:
    rel = rel.split("?")[0].lstrip("/")
    p = Path(rel)
    if p.parts and p.parts[0] == "assets":
        p = DATA_DIR / p
    return p


def _is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s))


def _mime_of(name: str) -> str:
    ext = Path(name).suffix.lower()
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


@st.cache_data(show_spinner=False)
def _img_b64(rel: str) -> str | None:
    """读取图片转 base64 data URI（带缓存）"""
    p = _resolve_asset(rel)
    if not p.exists():
        return None
    try:
        mime = _mime_of(p.name)
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    except Exception:
        return None


def show_image(rel: str, caption: str = "") -> None:
    rel = rel.strip()
    if _is_url(rel):
        st.image(rel, caption=caption or None, use_container_width=True)
        return
    b64 = _img_b64(rel)
    if b64:
        cap = (f"<div style='color:#64748b;font-size:12px;text-align:center;"
               f"margin-top:-10px'>{html.escape(caption)}</div>") if caption else ""
        st.markdown(
            f"<div style='text-align:center'><img src='{b64}' "
            f"style='max-width:100%;border-radius:8px;border:1px solid #e2e8f0'/></div>{cap}",
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"🖼 图片缺失：`{rel}`（可先推送到 GitHub 或上传 assets/）")


def _fenced_to_html(code: str, lang: str) -> str:
    """简单代码高亮：python/js/bash 关键字 + 字符串 + 注释"""
    esc = html.escape(code)
    esc = re.sub(r"(&quot;.*?&quot;|&#x27;.*?&#x27;)",
                 r'<span style="color:#a5d6a7">\1</span>', esc)
    esc = re.sub(r"(#.*)$", r'<span style="color:#90a4ae">\1</span>',
                 esc, flags=re.MULTILINE)
    if lang in ("python", "py"):
        kw = ("def|class|import|from|return|if|elif|else|for|while|try|except|"
              "finally|with|as|lambda|yield|raise|pass|break|continue|and|or|"
              "not|in|is|None|True|False|async|await|global|nonlocal|assert")
    elif lang in ("bash", "sh", "shell"):
        kw = ("if|then|fi|for|do|done|while|case|esac|function|echo|exit|"
              "export|local|return|source|sudo|apt|yum|systemctl|grep|awk|sed")
    elif lang in ("javascript", "js", "ts", "typescript"):
        kw = ("function|const|let|var|return|if|else|for|while|class|new|"
              "import|export|from|async|await|try|catch|switch|case|default")
    else:
        kw = ""
    if kw:
        esc = re.sub(rf"\b({kw})\b",
                     r'<span style="color:#64b5f6;font-weight:600">\1</span>',
                     esc)
    return esc


_LANG_LABEL = {"python": "PYTHON", "bash": "SHELL", "sh": "SHELL",
               "powershell": "POWERSHELL", "sql": "SQL", "yaml": "YAML",
               "json": "JSON", "javascript": "JS"}


def _code_block_html(code: str, lang: str) -> str:
    label = _LANG_LABEL.get(lang, (lang or "CODE").upper())
    return (
        '<div style="background:#0f172a;border:1px solid #334155;'
        'border-radius:10px;margin:14px 0;overflow:hidden;">'
        f'<div style="padding:6px 14px;background:#1e293b;color:#64748b;'
        f'font-size:12px;">{label}</div>'
        f'<pre style="margin:0;padding:14px 16px;overflow-x:auto;color:#e2e8f0;'
        f'font-size:14px;line-height:1.65;">{_fenced_to_html(code, lang)}</pre>'
        "</div>"
    )


def render_content(body: str | None, attachment: str | None = None,
                   location: str = "detail") -> None:
    """主渲染入口：正文 + 代码 + 图片 + 链接 + 附件卡片"""
    if not body:
        st.info("（暂无正文）")
        return

    # ![[assets/x.png|caption]] —— 先抽出来占位
    wiki_imgs: list[str] = []

    def _wiki(m):
        inner = (m.group(1) or m.group(2) or "").strip()
        parts = inner.split("|", 1)
        src, cap = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")
        if not re.match(r"^(https?://|assets/|[^/]+\.(png|jpe?g|gif|webp|svg|bmp)$)",
                        src, re.I):
            return f"`{src}`"
        token = f"\n\nKBWIKIIMG{len(wiki_imgs)}\n\n"
        wiki_imgs.append(f"{src}\t{cap}")
        return token

    body = re.sub(r"!\[\[([^\]]+)\]\]", _wiki, body)
    body = re.sub(r"(?<!!)\[\[([^\]]+)\]\]", _wiki, body)

    code_blocks: list[str] = []

    def _fence(m):
        lang = (m.group(1) or "").strip().lower()
        code_blocks.append(_code_block_html(m.group(2) or "", lang))
        return f"\n\nKBCODE{len(code_blocks) - 1}\n\n"

    body = re.sub(r"```(\w*)\n(.*?)```", _fence, body, flags=re.DOTALL)

    def _md_img(m):
        alt, src = m.group(1) or "", m.group(2) or ""
        if not _is_url(src):
            token = f"\n\nKBWIKIIMG{len(wiki_imgs)}\n\n"
            wiki_imgs.append(f"{src}\t{alt}")
            return token
        return m.group(0)

    body = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", _md_img, body)
    body = re.sub(r"KBWIKIIMG(\d+)", r"\n\nKBWIKIIMG\1\n\n", body)

    for chunk in re.split(r"(KBWIKIIMG\d+|KBCODE\d+)", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        mw, mc = re.fullmatch(r"KBWIKIIMG(\d+)", chunk), re.fullmatch(r"KBCODE(\d+)", chunk)
        if mw:
            src, cap = wiki_imgs[int(mw.group(1))].split("\t", 1)
            show_image(src, cap)
        elif mc:
            st.markdown(code_blocks[int(mc.group(1))], unsafe_allow_html=True)
        else:
            st.markdown(chunk, unsafe_allow_html=False)

    if attachment and location == "detail":
        # 本地附件 → 下载按钮；URL → 链接
        rel = attachment.lstrip("/")
        local = None
        if rel.startswith("attachments/"):
            local = PROJECT_ROOT / rel
        elif rel.startswith("assets/"):
            local = DATA_DIR / rel
        elif not rel.startswith(("http://", "https://")):
            local = PROJECT_ROOT / rel
        if local is not None and local.is_file():
            st.download_button(
                "📎 下载附件",
                data=local.read_bytes(),
                file_name=local.name,
                mime="application/octet-stream",
                use_container_width=False,
            )
            st.caption(f"附件：`{rel}`（{local.stat().st_size / 1024:.0f} KB）")
        elif local is not None:
            st.warning(f"📎 附件缺失：`{rel}`（可先推送到 GitHub 或上传）")
        else:
            st.markdown(
                f'<div style="border:1px dashed #00b4d8;border-radius:8px;'
                f'padding:10px;margin-top:14px;color:#7dd3fc;">'
                f'📎 附件：<a href="{html.escape(attachment)}" target="_blank">打开链接</a></div>',
                unsafe_allow_html=True,
            )


def toc_from_body(body: str) -> list[tuple[int, str]]:
    return [(len(m.group(1)), m.group(2).strip())
            for m in re.finditer(r"^(#{1,3})\s+(.+)$", body or "", re.MULTILINE)]
