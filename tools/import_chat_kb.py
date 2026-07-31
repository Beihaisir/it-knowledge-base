# -*- coding: utf-8 -*-
"""
从企业微信聊天记录 JSON 提取 SS 系统运维知识 → 生成知识库条目

用法:
    python3 tools/import_chat_kb.py <聊天记录.json> [--dry-run]

功能:
    1. 扫描消息中的"问题"类消息（含报错/进不去/无法等关键词）
    2. 提取问题 → 查找后续 3 条内的解决方案回复
    3. 生成 <问题ID>.md 草稿（含来源、日期、原始对话引用）
    4. 草稿保存到 entries/pending/ 目录，人工确认后移入 entries/

不会自动覆盖正式条目，安全。
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PENDING_DIR = BASE_DIR / "entries" / "pending"
ASSETS_DIR = BASE_DIR / "entries" / "assets"

PROBLEM_RE = re.compile(
    r"(?:报错|进不去|打不开|登不上|登录不了|无反应|没反应|搜不到|查不到|找不到|"
    r"对不上|无法|什么情况|是什么原因|怎么回事|怎么处理|怎么办|不显示|看不到|"
    r"消失|丢失|少了|多了|错误|失败|卡住|超时|冻结|超发)"
)

EXPERT_NAMES = ("CP-SS苗洁总", "🍣寿司", "Q~Greninja🥕", "xanny")


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip()).strip("-")
    return (s or "entry")[:40]


def load_msgs(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("messages") or data.get("list") or []
    return [d for d in data if isinstance(d, dict)]


def extract_cases(msgs: list[dict]) -> list[dict]:
    """问题消息 + 后续专家解答 → 案例"""
    cases = []
    for i, m in enumerate(msgs):
        content = str(m.get("content") or "")
        if str(m.get("type")) != "1" or len(content) < 12:
            continue
        if not PROBLEM_RE.search(content):
            continue
        # 找后续 4 条内专家解答
        answers = []
        for j in range(i + 1, min(i + 5, len(msgs))):
            a = msgs[j]
            who = a.get("display_name") or ""
            ac = str(a.get("content") or "")
            if str(a.get("type")) != "1" or len(ac) < 8:
                continue
            answers.append((a.get("time", "")[11:16], who, ac))
            if any(e in who for e in EXPERT_NAMES):
                break
        if answers:
            cases.append({
                "date": m.get("time", "")[:10],
                "asker": m.get("display_name") or "?",
                "question": content,
                "answers": answers,
                "file": str(m.get("server_id") or ""),
            })
    return cases


def render_case(c: dict) -> str:
    title = c["question"].split("\n")[0][:42]
    q = c["question"].replace("\n", " ")[:500]
    lines = [
        "---",
        f"id: chat-{slugify(title)}",
        f"title: {title}",
        "category: ss-system",
        "tags: [SS系统, 群记录]",
        "keywords: []",
        "author: 群记录提取",
        f"created: {c['date']} 12:00",
        f"updated: {c['date']} 12:00",
        "views: 0",
        "---",
        "",
        "> 📌 来源：第三批推广-新SS上线群聊记录",
        "",
        f"## 问题",
        "",
        f"{q}",
        "",
        "## 解答",
        "",
    ]
    for t, who, ac in c["answers"]:
        lines.append(f"- **[{t}] {who}**：{ac.replace(chr(10), ' ')[:400]}")
    lines += [
        "",
        "## 参考",
        "",
        "- 该条目由聊天记录自动提取，建议人工核对后完善",
    ]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = Path(sys.argv[1])
    dry = "--dry-run" in sys.argv
    msgs = load_msgs(src)
    print(f"[*] 消息总数: {len(msgs)}")
    cases = extract_cases(msgs)
    print(f"[*] 提取到案例: {len(cases)}")
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    seen = set()
    for c in cases:
        fid = f"chat-{slugify(c['question'][:42])}"
        if fid in seen:
            continue
        seen.add(fid)
        out = PENDING_DIR / f"{fid}.md"
        if out.exists():
            continue
        if not dry:
            out.write_text(render_case(c), encoding="utf-8")
        written += 1
    print(f"[*] 生成草稿: {written} 个 (目录: {PENDING_DIR})")
    print("[*] 核对后移入 entries/ 即可发布；删除不要的草稿")


if __name__ == "__main__":
    main()
