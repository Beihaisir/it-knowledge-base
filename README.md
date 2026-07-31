# 🦞 IT 问题知识库

一款轻量的 IT 团队知识库系统：**Streamlit 前端 + GitHub 即数据库**。
内容支持 **文字 / 图片 / 链接 / 代码块**，条目用 Markdown 存储，天然适合 PR 协作与版本回溯。

## 功能

| 模块 | 能力 |
|------|------|
| 🏠 知识库 | 全文搜索、分类筛选、排序（浏览量/时间/标题）、分页 |
| 📖 阅读页 | 标题 + 目录大纲 + 正文渲染（图片/链接/代码高亮）+ 附件下载 |
| ⚙️ 管理 | 新建/编辑/删除、图片上传图库、附件上传、实时预览、可选管理员密码 |
| 🐙 同步 | 单篇推送 / 全量推送 / 全量拉取（GitHub Contents API） |
| 💾 存储 | `entries/*.md`（YAML front matter）+ `entries/assets/` 图片 + `entries/attachments/` 附件 |
| 🛠 导入 | `tools/import_chat_kb.py` 从聊天记录 JSON 提取案例草稿 |

## 快速开始（本地）

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

打开 `http://localhost:8501`，默认带 6 篇示例条目。

## 部署到 Streamlit Community Cloud

1. 把本目录推到你的 GitHub 仓库（`entries/` 一起提交，作为初始内容）
2. <https://share.streamlit.io> → New app → 选仓库 → Main file 填 `app/app.py`
3. **（可选）** Settings → Secrets 添加：

```toml
[github]
token = "ghp_xxx"          # Personal Access Token，repo 权限
repo = "yourname/it-kb"    # 拥有内容读写权限的仓库
branch = "main"
entries_path = "entries"

admin_password = "改一个强密码"   # 留空则管理页免登录
```

4. Secrets 保存后 Reboot，编辑保存后点「保存并推送 GitHub」即可持久化

> 不配 GitHub 时也能跑，但 Streamlit Cloud 重启后本地改动会丢失，建议配置。

## 内置内容

- **IT 通用 6 篇**：Windows 上网 / Linux 磁盘 / 域密码 / VPN / MySQL / 钓鱼应急
- **SS 系统专题 14 篇**：从「第三批推广-新SS上线」群聊记录（1777 条）提炼，覆盖登录/打印/库存/地磅/SAP/GBM设定/权限/收货/合同等高频运维问题
- **原始素材**：`entries/attachments/第三批推广-新SS上线.json`（群聊完整记录，可在详情页下载）

## 仓库结构

```
it-knowledge-base/
├── app/
│   ├── app.py          # Streamlit 主界面（知识库 + 管理后台）
│   ├── storage.py      # 存储层：本地读写 + GitHub 同步
│   └── renderer.py     # 渲染层：Markdown + 图片 + 代码高亮
├── entries/            # ★ 这就是"数据库"
│   ├── *.md            # 条目（YAML front matter + Markdown 正文）
│   └── assets/         # 图片
├── requirements.txt
├── .streamlit/config.toml
└── README.md
```

## 条目格式

```markdown
---
id: windows-no-internet
title: Windows 无法上网排查指南
category: network
tags: [Windows, 网络]
keywords: [ipconfig, DNS]
author: Boss
created: 2026-07-31 09:00
updated: 2026-07-31 10:30
views: 15
attachment: assets/xxx.pdf      # 可选
---

## 正文
文字、**加粗**、[链接](https://example.com)

![[assets/demo.png|图片说明]]

```bash
ipconfig /flushdns
```
```

配图两种方式：
- `![[assets/xx.png]]`（推荐，本地/仓库图片）
- 直接粘贴 URL：`![alt](https://...jpg)`

## 协作流

- 小团队：直接「管理页 → 保存并推送 GitHub」
- 大团队：成员提 PR 改 `entries/`，合并后管理页「⬇️ 拉取仓库」刷新

🦞 由小龙虾出品 · 暗黑科技风
