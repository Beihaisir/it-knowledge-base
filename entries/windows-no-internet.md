---
id: windows-no-internet
title: Windows 无法上网排查指南
category: desktop
tags:
- Windows
- 网络
- 故障排查
keywords:
- ipconfig
- ping
- DNS
- 网卡
- 代理
author: Boss
created: 2026-07-31 09:00
updated: 2026-07-31 10:30
views: 16
---

## 现象

电脑提示“无 Internet 连接”或网页打不开，但微信/QQ 在线。

![[assets/network-layers.svg|分层排查：从物理层到应用层逐项定位]]

## 快速诊断命令

```powershell
ipconfig /all
ping 网关地址
ping 114.114.114.114
nslookup www.baidu.com
```

## 排查步骤

1. **看网卡状态**：是否禁用、驱动感叹号；`ipconfig /all` 看是否拿到 IP
2. **拿到 169.254.x.x** → DHCP 失败，尝试

```powershell
ipconfig /release
ipconfig /renew
```

3. **能 ping 通网关和 114.114.114.114，但域名打不开** → DNS 问题：

```powershell
ipconfig /flushdns
netsh winsock reset
```

并把 DNS 改为 `223.5.5.5` / `119.29.29.29`

4. **微信能用、浏览器不行** → 检查代理：设置 → 网络 → 代理，关闭不明代理；或以管理员执行

```powershell
netsh winhttp reset proxy
```

5. **仍然不通** → 重置网络栈（需重启）：

```powershell
netsh int ip reset
```

## 参考资料

- [Microsoft 网络重置官方说明](https://support.microsoft.com/zh-cn/windows/)
- [TCP/IP 排错速查](https://learn.microsoft.com/zh-cn/troubleshoot/windows-server/networking/)

> 经验：90% 的“无法上网”最终落在 DNS / 代理 / 网卡驱动三件事上。
