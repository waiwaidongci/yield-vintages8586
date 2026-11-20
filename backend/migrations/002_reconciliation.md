# 002 批次核账

新增表 `reconciliations`（SQLAlchemy 启动自动建表，存量库无需手工迁移）：

- `name` 核账单名称；`request_key` 内容哈希（名称+排序批号+口径版本），唯一约束保证重试原单只出一份结论。
- `status` 复用 queued/running/completed/failed；`created/started/finished` 支撑中断恢复（worker 启动与周期巡检将超窗单据重新入队）。
- `batches` 目标批号；`policy` 冻结口径；`candidates`/`excluded` 排队时冻结的参选/不参选报告（并发复核不改变候选）；`checksum` 冻结快照 SHA256。
- `result` 结论（选用报告、逐批口径重算与出处、最优性证明）；`error` 失败原因（无解/未证最优/异常）。

底稿 JSON 新增选填 `batch` 批号字段：`validation.py` 仍强制原有业务字段齐全，`batch` 仅允许为非空字符串；缺批号的旧底稿/旧报告可查但不参与核账候选。
