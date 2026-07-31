---
id: vpn-connect-fail
title: VPN 连接失败排查
category: network
tags: [VPN, 远程办公, 防火墙]
keywords: [OpenVPN, WireGuard, 619, 809, MTU, NAT]
author: Boss
created: 2026-07-31 09:25
updated: 2026-07-31 10:05
views: 4
---

## 分步排查

1. **确认服务端还活着**

```bash
ping vpn.company.com
telnet vpn.company.com 1194   # OpenVPN UDP 则用 nc -u 测试
```

2. **看客户端报错代码**

| 代码 | 含义 | 处理 |
|------|------|------|
| 619 | 端口/协议被拦 | 换 TCP 443 模式，或检查公司出口防火墙 |
| 691 | 认证失败 | 密码/证书过期，重置凭据 |
| 809 | 服务未响应 | 服务端进程挂了，联系管理员 |

3. **连上了但没网** → MTU 问题最常见：

```bash
ping -f -l 1472 114.114.114.114   # 不通就减到 1400 试，接口 MTU 相应调小
```

WireGuard 在配置里加 `MTU = 1420`。

4. **分流冲突**：本机和 VPN 都抢默认路由时，检查

```powershell
route print
```

必要时只推内网网段（split tunnel）。

## 参考链接

- [OpenVPN 故障排查 Wiki](https://community.openvpn.net/openvpn/wiki/HOWTO)
- [WireGuard 快速上手](https://www.wireguard.com/quickstart/)
- [RFC 791 - IP 分片](https://datatracker.ietf.org/doc/html/rfc791)
