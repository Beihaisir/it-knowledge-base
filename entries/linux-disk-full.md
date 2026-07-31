---
id: linux-disk-full
title: Linux 磁盘爆满应急处理
category: server
tags:
- Linux
- 磁盘
- 运维
keywords:
- df
- du
- journalctl
- docker
- 日志清理
author: Boss
created: 2026-07-31 09:10
updated: 2026-07-31 10:20
views: 10
---

## 1. 先确认整体用量

```bash
df -hT
df -i     # inode 用尽同样会报 No space left
```

## 2. 找出最大目录

```bash
du -xh --max-depth=1 / 2>/dev/null | sort -rh | head -15
```

重点盯 `/var/log`、`/var/lib/docker`、`/var/cache`、`/opt`。

## 3. 常见清理

```bash
journalctl --vacuum-size=200M      # 日志限额
apt clean                          # Debian/Ubuntu 包缓存
docker system prune -f             # 无用镜像/容器（确认后执行）
find /var/log -name "*.log" -mtime +30 -delete
```

## 4. 删掉文件空间却没释放？

进程还握着句柄：

```bash
lsof | grep deleted
systemctl restart <对应服务>
```

## 5. 根治建议

- 给 `/var/log` 单独分区或启用 logrotate 压缩轮转
- 监控脚本：`df -h | awk '$5+0 > 85 {print}'` 接入告警

☠️ **红线**：`rm -rf /var/lib/docker` 前务必确认容器数据已备份。

## 参考链接

- [Red Hat：磁盘空间管理](https://access.redhat.com/documentation/)
- [Docker prune 官方文档](https://docs.docker.com/engine/reference/commandline/system_prune/)
