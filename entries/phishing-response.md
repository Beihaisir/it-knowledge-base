---
id: phishing-response
title: 收到钓鱼邮件应急处理流程
category: security
tags:
- 安全
- 钓鱼邮件
- 应急响应
keywords:
- phishing
- 邮件头
- IOC
- 隔离
author: Boss
created: 2026-07-31 09:35
updated: 2026-07-31 09:55
views: 3
---

## ⚡ 黄金 5 分钟

1. **不要点任何链接/附件**，不要回复
2. 截图保存邮件原文（含完整时间、发件人）
3. 立即上报安全值班 / IT 群

## 技术处置

```powershell
# 导出完整邮件头（Outlook: 文件 → 属性）
# 重点字段：Return-Path、Received 链、Message-ID、X-Originating-IP
```

提取 IOC（Indicators of Compromise）：
- 发件域名、URL、附件 MD5/SHA256
- 到 [VirusTotal](https://www.virustotal.com/) 与 [微步在线](https://x.threatbook.com/) 查验

## 已点击/已输入密码怎么办

1. **断开网络**（拔网线/关 Wi-Fi），不关机
2. 立刻在**另一台干净设备**上修改可能泄露的密码
3. 全盘杀毒 + 检查开机启动项：

```powershell
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location
```

4. 有域环境的，通知管理员强制重置该账号域密码并吊销会话

## 预防

- 邮件网关开启 SPF / DKIM / DMARC 校验
- 定期钓鱼演练（如 [GoPhish](https://getgophish.com/)）

## 参考链接

- [CISA 钓鱼防范指南](https://www.cisa.gov/secure-our-world/recognize-and-report-phishing)
- [国家反诈中心](https://www.mps.gov.cn/)
