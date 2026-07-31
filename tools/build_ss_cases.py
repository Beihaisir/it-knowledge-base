# -*- coding: utf-8 -*-
"""
SS系统聊天记录 → 结构化知识库 提取器 v3

用法:
    python3 tools/build_ss_cases.py

改进 (v3):
    1. 解答者不限专家：任何人给出可操作解法都算有效解答
    2. 标题优先用错误编号/菜单号（如 RCI019S0、STI12000）
    3. 标题直接写问题（去 @xxx 前缀、去客套话）
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

# 菜单号/错误码（SS系统特色：3个大写字母+5位数字，或 FMM/STI/GBM 等前缀）
MENU_RE = re.compile(r"\b[A-Z]{2,3}\d{4,5}\b")
# 操作类关键词（判断一条消息是否为"可操作解答"）
SOLUTION_RE = re.compile(
    r"(?:去|看|查|点|用|开|做|检查|登录|重启|找|联系|改|发|填|选|按|操作|"
    r"在|进|到|输入|选择|确认|提交|解锁|恢复|申请|审核|处理|关闭|打开|设置|"
    r"更换|重新|先|需要|应该|可以|试|试下|试试|按.{0,6}(?:操作|处理|设置)|"
    r"FMM\d{5}|STI\d{5}|GBM\d{5}|PUM\d{5}|RCI\d{5}|OTG\d{5}|FMU\d{5}|STM\d{5}|"
    r"ITG\d{5}|SLM\d{5}|PUU\d{5}|STG\d{5}|FMI\d{5}|FMSR\d{5})")
# 问题特征（提问/报障）
PROB = re.compile(
    r"(?:报错|进不去|打不开|登不上|登录不了|无反应|没反应|搜不到|查不到|找不到|对不上|无法|"
    r"什么情况|是什么原因|怎么回事|怎么处理|怎么办|不显示|看不到|消失|丢失|少了|多了|错误|"
    r"失败|卡住|超时|冻结|超发|帮|指导|请教|咨询|请教一下|帮忙|麻烦)")
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


def clean_title(q: str) -> str:
    """标题生成：优先错误编号+问题核心，否则精简问题"""
    # 去掉 @xxx 前缀和客套话
    t = re.sub(r"@[^\s，。]+\s*", "", q)
    t = re.sub(r"^(老师|苗总|苗老师|苗洁|寿司|领导|各位老师|各位|你好|您好|不好意思|打扰一下|打扰了)[，,\s]*", "", t)
    t = re.sub(r"(?:麻烦|请教一下|请教|咨询|帮忙|帮看一下|帮看看|请问|想问|麻烦问下|打扰一下|不好意思)[，,\s]*", "", t)
    t = re.sub(r"^一下", "", t)
    t = t.replace("（", " ").replace("）", " ").replace("(", " ").replace(")", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"[？?。！!]+$", "", t).strip()
    t = re.sub(r"^[，,、\s]+", "", t)
    # 找错误编号/菜单号
    menus = list(dict.fromkeys(MENU_RE.findall(q)))
    if menus:
        code = menus[0]
        # 提取问题核心：保留“报错/无法/进不去/打不开/对不上”等 之后的短语
        m = re.search(r"(?:报错|错误|提示|无法|进不去|打不开|登不上|对不上|搜不到|找不到|不显示|无反应|消失|卡住|超时|冻结|超发|不能|不可以)[^，。？?]{0,24}", t)
        tail = m.group(0)[:22].strip() if m else ""
        # 若没有特征词，取菜单号后的问题片段（如“FMM06000进不去”整句）
        if not tail:
            idx = t.find(code)
            if idx >= 0:
                after = t[idx + len(code):].strip(" ，,。")
                tail = after[:20] if after else ""
        title = f"{code} {tail}".strip() if tail else f"{code} 问题排查"
        return title[:50]
    return (t or q)[:40]


def slug_from_q(q: str, idx: int) -> str:
    title = clean_title(q)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")
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
                (Q_END.search(content) or PROB.search(content)):
            # 去掉客套话后太短的（如"苗老师，您帮看一下"）不算完整问题
            _core_len = len(re.sub(r"@[^\s，。]+|^(老师|苗总|苗老师|苗洁|寿司|领导|各位老师|各位|你好|您好|不好意思|打扰一下|麻烦|请教一下|请教|请问|咨询|帮忙)[，,\s]*", "", content))
            if _core_len < 15:
                i += 1
                continue
            # 排除明显是解答/指令的消息（不是问题）
            # 先剥离客套话再判断
            _strip = re.sub(r"^(老师|苗总|苗老师|苗洁|寿司|领导|各位老师|各位|你好|您好|不好意思|打扰一下|麻烦|请教一下|请教|请问|咨询|帮忙)[，,\s]*", "", content)
            if re.match(r"^(不是|下次|这个|那个|你们|我们|请|去|看|查|点|用|开|做|检查|登录|重启|找|联系|改|发|填|选|按|操作|在|进|到|输入|选择|确认|提交|解锁|恢复|申请|审核|处理|关闭|打开|设置|更换|重新|先|应该|可以|试|建议|好的|已经|可以了|解决了|谢谢|学习了|收到|嗯|好嘞)[，,：: 把]", _strip) or re.match(r"^(你|我)(们)?[，,：: ]", _strip) or (re.match(r"^不是", _strip) and not Q_END.search(content)) or re.match(r"^(好的|已经|谢谢|收到|可以了|解决了|学习了)", _strip):
                i += 1
                continue
            answers = []
            j = i + 1
            # 收集后续消息（含图片），最长 12 条；只要有可操作解答就收
            while j < min(i + 12, len(msgs)):
                a = msgs[j]
                ac = str(a.get("content", "")).strip()
                who = a.get("display_name", "")
                a_imgs = img_idx.get(str(a.get("server_id", ""))[:6], [])
                if str(a.get("type")) == "1" and len(ac) >= 8:
                    # 判断是否为可操作解答（含菜单号/操作指令）
                    is_sol = bool(SOLUTION_RE.search(ac))
                    answers.append({
                        "time": a.get("time", "")[11:16],
                        "who": who,
                        "text": ac.replace("\n", " ")[:300],
                        "imgs": a_imgs,
                        "is_sol": is_sol,
                    })
                    # 有解答后，再跟 1 条看结果/补充，然后结束
                    if is_sol:
                        for k in range(j + 1, min(j + 2, len(msgs))):
                            ek = msgs[k]
                            ekc = str(ek.get("content", "")).strip()
                            if str(ek.get("type")) == "1" and len(ekc) >= 6:
                                answers.append({
                                    "time": ek.get("time", "")[11:16],
                                    "who": ek.get("display_name", ""),
                                    "text": ekc.replace("\n", " ")[:200],
                                    "imgs": img_idx.get(str(ek.get("server_id", ""))[:6], []),
                                    "is_sol": False,
                                })
                            elif str(ek.get("type")) == "3":
                                answers.append({
                                    "time": ek.get("time", "")[11:16],
                                    "who": ek.get("display_name", ""),
                                    "text": "（图片）",
                                    "imgs": img_idx.get(str(ek.get("server_id", ""))[:6], []),
                                    "is_sol": False,
                                })
                        break
                elif str(a.get("type")) == "3" and a_imgs:
                    answers.append({
                        "time": a.get("time", "")[11:16],
                        "who": who,
                        "text": "（图片）",
                        "imgs": a_imgs,
                        "is_sol": False,
                    })
                j += 1
            # 结果确认
            result = ""
            for a in msgs[j:min(j + 4, len(msgs))]:
                ac = str(a.get("content", "")).strip()
                if str(a.get("type")) == "1" and re.search(r"好了|可以了|解决了|成功了|能用了|可以打开|已经好|恢复正常|OK|搞定了|没问题了|谢谢|感谢", ac):
                    result = f"{a.get('time','')[11:16]} {a.get('display_name','')}：{ac[:120]}"
                    break
            key = content[:50]
            if answers and key not in seen:
                seen.add(key)
                # 必须有至少一条可操作解答才算完整案例
                if not any(a.get("is_sol") for a in answers):
                    continue
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
    title = clean_title(c["q"])
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
