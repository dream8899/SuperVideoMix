# 提案：推送排列组合拼接（permutation_concat.py）与 SKILL.md 工作流条目

- 稳定 ID：`PROPOSAL-2026-08-15-permutation-concat`
- 日期：2026-08-15
- 来源任务：用户明确指令，Claude 端已有更新，要求把 `permutation_concat.py` 与 SKILL.md 中对应的排列组合拼接条目同步推送到 GitHub。
- 原始证据：用户指令“规则固化：N 段素材 → 2 段/N 段拼接 → 每个序号在第一位最多出现一次 → 01 永久排除第一位”；本地工作区已有脚本与 SKILL.md 新增条目（未提交）。
- 适用范围：对已拆分段做首位去重排列组合拼接；仅用于自有或已获授权素材。
- 反例：01 不得出现在第一位；同一序号不得在多个组合中占据第一位；不修改分段本身。
- 风险：脚本直接调用 ffmpeg concat 且使用 `-y`，与 Skill“先计划后审批、不覆盖现有成品”的默认门禁不一致；本次按用户要求保持与 Claude 端一致原样同步，风险由用户确认；脚本不触碰源分段，输出到新建目录。
- 建议动作：
  1. 提交 governance 提案与人工批准记录。
  2. 提交 `SKILL.md` 条目与 `scripts/permutation_concat.py`。
  3. 补充最小测试并运行完整测试与受控演化守卫。
  4. 推送 origin/main。
- 状态：`proposed`
