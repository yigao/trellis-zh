# Continue Current Task（继续当前任务）

从正确的阶段/步骤恢复当前任务的工作 —— 在 `.trellis/workflow.md` 中找到对应位置。

---

## 步骤 1：加载当前上下文

```bash
py -3 ./.trellis/scripts/get_context.py
```

确认：当前任务、git 状态、最近的提交。

## 步骤 2：加载阶段索引

```bash
py -3 ./.trellis/scripts/get_context.py --mode phase
```

显示阶段索引（Plan / Execute / Finish）及路由和技能映射。

## 步骤 3：判断当前所处位置

`get_context.py` 会显示活动任务的 `status` 字段。根据 `status` 和产物存在情况进行路由：

- `status=planning` + 无 `prd.md` → **1.1**（加载 `trellis-brainstorm`）
- `status=planning` + `prd.md` 存在 + `implement.jsonl` 未整理（只有种子行 `_example`） → **1.3**
- `status=planning` + `prd.md` + 已整理的 `implement.jsonl` → **1.4**（运行 `task.py start` 进入阶段 2）
- `status=in_progress` + 实现尚未开始 → **2.1**
- `status=in_progress` + 实现已完成，尚未检查 → **2.2**
- `status=in_progress` + 检查已通过 → **3.1**
- `status=completed`（很少见；通常在完成后立即归档） → 归档流程

阶段规则（详细信息见 `.trellis/workflow.md`）：

1. 在阶段内**按顺序**运行步骤 —— `[required]` 步骤不得跳过
2. `[once]` 步骤如果其输出已存在（例如：1.1 的 `prd.md`；1.3 的带有已整理条目的 `implement.jsonl`），则视为已完成 —— 跳过它们
3. 如果新的发现要求回到更早的阶段，可以回退

## 步骤 4：加载具体步骤

确定要从哪个步骤恢复后：

```bash
py -3 ./.trellis/scripts/get_context.py --mode phase --step <X.X> --platform claude
```

按照加载的指令执行。每个 `[required]` 步骤完成后，继续下一个。

---

## 参考

完整的工作流、技能路由表和"禁止跳过"表位于 `.trellis/workflow.md`。本命令仅是一个入口点 —— 权威指南在那里。
