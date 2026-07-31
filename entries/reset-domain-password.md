---
id: reset-domain-password
title: 域账号密码重置标准流程
category: software
tags: [AD, 域控, 密码, 账号]
keywords: [Active Directory, password reset, net user]
author: Boss
created: 2026-07-31 09:20
updated: 2026-07-31 10:10
views: 6
attachment: assets/password-reset-flow.svg
---

## 标准流程

![[assets/password-reset-flow.svg|申请 → 验证 → 执行 → 通知留痕]]

## 操作步骤（管理员）

```powershell
# PowerShell（需装 RSAT / 在域控上执行）
Set-ADAccountPassword -Identity zhangsan -Reset -NewPassword (ConvertTo-SecureString "Temp@2026!" -AsPlainText -Force)
Set-ADUser -Identity zhangsan -ChangePasswordAtLogon $true
Unlock-ADAccount -Identity zhangsan
```

也可在 **AD 用户和计算机** 图形界面右键用户 → 重置密码，勾选“用户下次登录时须更改密码”。

## 验证与通知

1. 电话中核对工号 + 直属主管，避免社工攻击
2. 临时密码通过**另一个渠道**告知（如企业微信），不与申请同渠道
3. 在工单系统记录操作人、时间、工单号

## 参考链接

- [Microsoft Docs - Set-ADAccountPassword](https://learn.microsoft.com/zh-cn/powershell/module/activedirectory/set-adaccountpassword)
- [域账号锁定排查](https://learn.microsoft.com/zh-cn/troubleshoot/windows-server/identity/)
