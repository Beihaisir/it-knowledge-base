# -*- coding: utf-8 -*-
"""
SS系统聊天记录 → 结构化知识库 提取器 v2

用法:
    python3 tools/build_ss_cases.py

输入: 第三批推广-新SS上线(55977802012@chatroom)/ 文件夹
      (第三批推广-新SS上线.json + image/ 图片目录 + file/ 文件目录)
输出: entries/ss-cases/*.md  (问题-解决方法-结果 三段式, 含图片)
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path("/mnt/e/xiaolongxia-share/第三批推广-新SS上线(55977802012@chatroom)")
OUT_DIR = BASE_DIR / "entries" / "ss-cases"
ASSETS_DIR = BASE_DIR / "entries" / "assets" / "ss-cases"

EXPERT = {"CP-SS苗洁总", "🍣寿司", "Q~Greninja🥕", "xanny", "Qp", "毫克", "芳"}
PROB = re.compile(
    r"(?:报错|进不去|打不开|登不上|登录不了|无反应|没反应|搜不到|查不到|找不到|对不上|无法|"
    r"什么情况|是什么原因|怎么回事|怎么处理|怎么办|不显示|看不到|消失|丢失|少了|多了|错误|"
    r"失败|卡住|超时|冻结|超发|帮|指导|请教|咨询)")
Q_END = re.compile(r"[？?]$")


def build_image_index() -> dict:
    """server_id前6位 → 图片文件路径列表"""
    idx = {}
    img_root = SRC_DIR / "image"
    if not img_root.is_dir():
        return idx
    for month_dir in sorted(img_root.iterdir()):
        if not month_dir.is_dir():
            continue
        for f in month_dir.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                # 跳过缩略图 _t.jpg
                if f.stem.endswith("_t"):
                    continue
                parts = f.stem.split("_")
                if len(parts) >= 3:
                    idx.setdefault(parts[2], []).append(str(f))
    return idx


def load_msgs() -> list[dict]:
    data = json.loads((SRC_DIR / "第三批推广-新SS上线.json").read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def topic_of(q: str) -> str:
    pairs = [
        ("库存", r"库存|余额|对不上|负数|重量对不上|重打包"),
        ("打印", r"打印|打印机|打出来|发货单打印"),
        ("登录", r"登录|进不去|登不|账号|密码|解锁|延期|账期"),
        ("地磅", r"地磅|过磅|磅重|磅单|过磅取不到|二磅"),
        ("SAP", r"SAP|信审|发送|接口|发送SAP"),
        ("合同", r"合同|开单|订单|采购单|报价|价税|税率"),
        ("权限", r"权限|角色|企业微信"),
        ("收货", r"收货|入库|出库|发货|退货|让步接收|品检|过磅"),
        ("GBM", r"GBM|设定|MDM|代码|主数据|客户设定|档案|产品代码|料号"),
        ("结账", r"结账|结转|月末|重打包|成本"),
        ("报表", r"报表|统计表|日报表|汇总"),
        ("远程", r"远程|VPN"),
    ]
    for name, pat in pairs:
        if re.search(pat, q, re.I):
            return name
    return "其他"


def slug_from_q(q: str, idx: int) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", q[:36]).strip("-")
    return f"ss-{s or 'case'}-{idx:03d}"


def build_cases() -> list[dict]:
    msgs = load_msgs()
    img_idx = build_image_index()
    print(f"[*] 消息 {len(msgs)} 条, 图片索引 {sum(len(v) for v in img_idx.values())} 张")
    cases = []
    seen = set()
    i = 0
    while i < len(msgs):
        m = msgs[i]
        content = str(m.get("content", "")).strip()
        who_m = m.get("display_name", "")
        if str(m.get("type")) == "1" and len(content) >= 12 and \
                who_m not in EXPERT and \
                (Q_END.search(content) or PROB.search(content)):
            answers = []
            j = i + 1
            # 收集从问题到解答结束的所有消息（含图片），最长 12 条
            while j < min(i + 12, len(msgs)):
                a = msgs[j]
                ac = str(a.get("content", "")).strip()
                who = a.get("display_name", "")
                a_imgs = img_idx.get(str(a.get("server_id", ""))[:6], [])
                if str(a.get("type")) == "1" and len(ac) >= 8:
                    answers.append({
                        "time": a.get("time", "")[11:16],
                        "who": who,
                        "text": ac.replace("\n", " ")[:300],
                        "imgs": a_imgs,
                    })
                    if who in EXPERT and ac:
                        # 专家解答后，再跟 2 条看结果确认/补充
                        for k in range(j + 1, min(j + 3, len(msgs))):
                            ek = msgs[k]
                            ekc = str(ek.get("content", "")).strip()
                            if str(ek.get("type")) == "1" and len(ekc) >= 6:
                                answers.append({
                                    "time": ek.get("time", "")[11:16],
                                    "who": ek.get("display_name", ""),
                                    "text": ekc.replace("\n", " ")[:200],
                                    "imgs": img_idx.get(str(ek.get("server_id", ""))[:6], []),
                                })
                            elif str(ek.get("type")) == "3":
                                answers.append({
                                    "time": ek.get("time", "")[11:16],
                                    "who": ek.get("display_name", ""),
                                    "text": "（图片）",
                                    "imgs": img_idx.get(str(ek.get("server_id", ""))[:6], []),
                                })
                        break
                elif str(a.get("type")) == "3" and a_imgs:
                    answers.append({
                        "time": a.get("time", "")[11:16],
                        "who": who,
                        "text": "（图片）",
                        "imgs": a_imgs,
                    })
                j += 1
            # 结果确认：在解答后再找 3 条内是否有"好了/可以了/解决了"
            result = ""
            for a in msgs[j:min(j + 4, len(msgs))]:
                ac = str(a.get("content", "")).strip()
                if str(a.get("type")) == "1" and re.search(r"好了|可以了|解决了|成功了|能用了|可以打开|已经好|恢复正常|OK|搞定了|没问题了|谢谢", ac):
                    result = f"{a.get('time','')[11:16]} {a.get('display_name','')}：{ac[:120]}"
                    break
            key = content[:50]
            if answers and key not in seen:
                seen.add(key)
                q_imgs = img_idx.get(str(m.get("server_id", ""))[:6], [])
                cases.append({
                    "idx": len(cases) + 1,
                    "date": m.get("time", "")[:10],
                    "time": m.get("time", "")[11:16],
                    "asker": m.get("display_name", "?"),
                    "q": content.replace("\n", " ")[:400],
                    "q_imgs": q_imgs,
                    "answers": answers,
                    "result": result,
                })
        i += 1
    return cases


def render_case(c: dict) -> tuple[str, str]:
    """返回 (文件名, markdown内容)"""
    title = c["q"][:40]
    # YAML 安全：title 可能以 @/#/特殊字符开头，必须加引号
    safe_title = json.dumps(title, ensure_ascii=False)
    lines = [
        "---",
        f"id: {slug_from_q(c['q'], c['idx'])}",
        f"title: {safe_title}",
        "category: ss-system",
        f"tags: [SS系统, {topic_of(c['q'])}, 实战案例]",
        "keywords: []",
        f"author: 群记录提炼（{c['asker']}）",
        f"created: {c['date']} {c['time']}",
        f"updated: {c['date']} {c['time']}",
        "views: 0",
        "---",
        "",
        f"> 📌 来源：第三批推广-新SS上线群聊 · {c['date']} {c['time']} · {c['asker']}",
        "",
        "## 问题",
        "",
        f"{c['q']}",
        "",
    ]
    for img in c["q_imgs"]:
        rel = copy_image(img)
        if rel:
            lines.append(f"![[{rel}|问题截图]]")
            lines.append("")
    lines.append("## 解决方法")
    lines.append("")
    for a in c["answers"]:
        lines.append(f"**[{a['time']}] {a['who']}**：{a['text']}")
        lines.append("")
        for img in a["imgs"]:
            rel = copy_image(img)
            if rel:
                lines.append(f"![[{rel}|处理截图]]")
                lines.append("")
    if not c["answers"]:
        lines.append("（专家解答见群记录原文，可下载附件回溯）")
        lines.append("")
    lines.append("## 结果")
    lines.append("")
    if c.get("result"):
        lines.append(f"- ✅ {c['result']}")
    else:
        lines.append(f"- 群内讨论确认：{c['date']} 的问题已按上述方案处理（完整上下文见群记录原文）")
    lines.append("- 如需完整上下文，请下载「群记录索引」条目附件")
    lines.append("")
    return f"{slug_from_q(c['q'], c['idx'])}.md", "\n".join(lines)


def copy_image(rel: str) -> str | None:
    """把图片从源目录复制到 entries/assets/ss-cases/, 返回站内相对路径"""
    src = SRC_DIR / rel
    if not src.is_file():
        return None
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    dst = ASSETS_DIR / src.name
    if not dst.exists():
        shutil.copy2(src, dst)
    return f"assets/ss-cases/{src.name}"


def main() -> None:
    cases = build_cases()
    print(f"[*] 完整案例: {len(cases)}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for c in cases:
        fname, content = render_case(c)
        out = OUT_DIR / fname
        if out.exists():
            continue
        out.write_text(content, encoding="utf-8")
        n += 1
    print(f"[*] 写入条目: {n} 个 → {OUT_DIR}")
    print(f"[*] 复制图片: {len(list(ASSETS_DIR.glob('*')) if ASSETS_DIR.exists() else [])} 张 → {ASSETS_DIR}")


if __name__ == "__main__":
    main()
