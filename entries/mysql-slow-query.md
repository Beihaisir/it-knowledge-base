---
id: mysql-slow-query
title: MySQL 慢查询定位与优化
category: database
tags: [MySQL, 数据库, 性能]
keywords: [slow log, EXPLAIN, 索引, mysqldumpslow]
author: Boss
created: 2026-07-31 09:30
updated: 2026-07-31 10:00
views: 3
---

## 开启慢查询日志

```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;          -- 单位秒，先试 1 秒
SET GLOBAL log_queries_not_using_indexes = 'ON';
```

配置文件 `my.cnf` 持久化：

```ini
[mysqld]
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
```

## 分析慢日志

```bash
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log   # 按耗时 Top10
```

## 用 EXPLAIN 看执行计划

```sql
EXPLAIN SELECT * FROM orders WHERE user_id = 10086 ORDER BY created_at DESC LIMIT 20;
```

重点看：`type`（ALL=全表扫描要警惕）、`key`（有没有用上索引）、`rows`（扫描行数）。

## 常见优化

- 给 where / order by 列建**联合索引**，遵循最左前缀
- `SELECT *` 改成只取需要的列
- 大分页 `LIMIT 100000,20` 改为 `WHERE id > 100000 LIMIT 20`

## 参考链接

- [MySQL 官方：慢查询日志](https://dev.mysql.com/doc/refman/8.0/en/slow-query-log.html)
- [EXPLAIN 输出解读](https://dev.mysql.com/doc/refman/8.0/en/explain-output.html)
- [高性能 MySQL 读书笔记](https://github.com/raywenderlich/)
