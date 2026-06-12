# trellis-implement 智能体流程图

> 使用 Mermaid 语法绘制的完整流程图集。
> 在支持 Mermaid 的 Markdown 渲染器中查看（GitHub、VS Code + 插件、Typora 等）。

---

## 图一：整体架构 — trellis-implement 在 Trellis 工作流中的位置

```mermaid
flowchart TB
    subgraph MAIN["主会话 Main Session"]
        direction TB
        S2_1["阶段 2.1：派发 trellis-implement"]
        S2_2["阶段 2.2：派发 trellis-check"]
        S2_3["阶段 2.3：trellis-update-spec"]
        S3["阶段 3：提交 & 完成"]
        
        S2_1 --> S2_2 --> S2_3 --> S3
    end
    
    subgraph IMPLEMENT["trellis-implement 子智能体"]
        direction TB
        I1["1. 理解规范
        阅读 .trellis/spec/"]
        I2["2. 理解需求
        阅读 prd.md + info.md"]
        I3["3. 实现功能
        按规范编写代码"]
        I4["4. 自行检查
        运行 lint + type-check"]
        I5["5. 报告结果
        Implementation Complete"]
        I1 --> I2 --> I3 --> I4 --> I5
    end
    
    subgraph CHECK["trellis-check 子智能体"]
        direction TB
        C1["获取代码变更"]
        C2["对照规范检查"]
        C3["自行修复问题"]
        C4["运行验证"]
        C5["输出 Self-Check 报告"]
        C1 --> C2 --> C3 --> C4 --> C5
    end
    
    S2_1 -.->|"Agent(subagent_type='trellis-implement')"| IMPLEMENT
    IMPLEMENT -.->|"Implementation Complete 报告"| S2_2
    S2_2 -.->|"Agent(subagent_type='trellis-check')"| CHECK
    CHECK -.->|"Self-Check Complete 报告"| S2_3
    
    style MAIN fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style IMPLEMENT fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style CHECK fill:#533483,stroke:#16213e,color:#e0e0e0
```

---

## 图二：上下文加载决策树

```mermaid
flowchart TD
    START(["trellis-implement 子智能体启动"]) --> Q1{"输入中是否有
    &lt;!-- trellis-hook-injected --&gt;
    标记？"}
    
    Q1 -->|"✅ YES"| HOOK_INJECTED["上下文已由钩子注入
    包含:
    ├─ implement.jsonl 引用的 spec
    ├─ prd.md 需求文档
    └─ info.md 技术设计（如有）
    直接进入工作流"]
    
    Q1 -->|"❌ NO"| Q2{"分派提示第一行
    是否有
    'Active task: &lt;path&gt;'？"}
    
    Q2 -->|"✅ YES"| MANUAL["从 task path 手动加载：
    1. 读取 &lt;task&gt;/prd.md
    2. 读取 &lt;task&gt;/info.md（如有）
    3. 读取 &lt;task&gt;/implement.jsonl
    4. 逐条读取 JSONL 中引用的 spec"]
    
    Q2 -->|"❌ NO"| Q3{"运行 task.py current
    能否获取任务路径？"}
    
    Q3 -->|"✅ YES"| MANUAL
    Q3 -->|"❌ NO"| ASK_USER["询问用户当前活动任务
    不盲目猜测"]
    
    HOOK_INJECTED --> WORKFLOW(["进入五步实现工作流"])
    MANUAL --> WORKFLOW
    ASK_USER --> WORKFLOW
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style HOOK_INJECTED fill:#0f3460,stroke:#00ff88,color:#fff
    style MANUAL fill:#533483,stroke:#ffaa00,color:#fff
    style ASK_USER fill:#5c2a2a,stroke:#ff4444,color:#fff
    style WORKFLOW fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图三：五步实现工作流（核心流程）

```mermaid
flowchart TD
    START(["上下文加载完成"]) --> STEP1
    
    subgraph STEP1["步骤 1：理解规范"]
        direction TB
        S1A["确定任务涉及的 package 和 layer"] --> S1B["阅读 .trellis/spec/&lt;package&gt;/&lt;layer&gt;/ 规范"]
        S1B --> S1C["阅读共享指南
        .trellis/spec/guides/"]
        S1C --> S1D["提取关键约定：
        ├─ 目录结构
        ├─ 命名规则
        ├─ 代码模式
        └─ API 设计规范"]
    end
    
    STEP1 --> STEP2
    
    subgraph STEP2["步骤 2：理解需求"]
        direction TB
        S2A["读取 prd.md
        ├─ 核心需求
        ├─ 验收标准
        └─ 优先级"] --> S2B{"info.md
        存在？"}
        S2B -->|"YES"| S2C["读取 info.md
        ├─ 架构决策
        ├─ 技术约束
        ├─ 实现方案
        └─ 技术选型"]
        S2B -->|"NO"| S2D["仅基于 prd.md
        进行技术判断"]
        S2C --> S2E["确定：
        ├─ 需要修改的文件
        ├─ 需要创建的文件
        └─ 需要遵循的模式"]
        S2D --> S2E
    end
    
    STEP2 --> STEP3
    
    subgraph STEP3["步骤 3：实现功能"]
        direction TB
        S3A["按照规范编写代码"] --> S3B{"遵循原则？"}
        S3B --> S3C["✅ 遵循现有代码模式"]
        S3B --> S3D["✅ 不过度工程化"]
        S3B --> S3E["✅ 只做必要工作"]
        S3B --> S3F["✅ 保持可读性"]
        S3C & S3D & S3E & S3F --> S3G["代码编写完成"]
    end
    
    STEP3 --> STEP4
    
    subgraph STEP4["步骤 4：自行检查"]
        direction TB
        S4A["运行 lint"] --> S4B{"Lint 通过？"}
        S4B -->|"NO"| S4C["修复 lint 问题"]
        S4C --> S4A
        S4B -->|"YES"| S4D["运行 type-check"]
        S4D --> S4E{"TypeCheck 通过？"}
        S4E -->|"NO"| S4F["修复类型错误"]
        S4F --> S4D
        S4E -->|"YES"| STEP5
    end
    
    STEP4 --> STEP5
    
    subgraph STEP5["步骤 5：报告结果"]
        direction TB
        S5A["生成 Implementation Complete 报告"]
        S5A --> S5B["Files Modified 列表"]
        S5A --> S5C["Implementation Summary"]
        S5A --> S5D["Verification Results
        Lint + TypeCheck 状态"]
    end
    
    STEP5 --> END_NODE(["返回主会话"])
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style END_NODE fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图四：PreToolUse 钩子上下文注入流程（Implement 视角）

```mermaid
flowchart TD
    START(["主会话调用
    Agent(subagent_type='trellis-implement')"]) --> HOOK["PreToolUse 钩子触发
    inject-subagent-context.py"]
    
    HOOK --> PARSE["解析 stdin JSON
    _parse_hook_input()
    提取 subagent_type"]
    
    PARSE --> CHECK{"subagent_type
    == 'trellis-implement'？"}
    
    CHECK -->|"NO"| EXIT_A(["sys.exit(0)
    不修改，放行"])
    
    CHECK -->|"YES"| FIND_TASK["查找活动任务
    get_current_task()
    → resolve_active_task()"]
    
    FIND_TASK --> TASK_EXISTS{"任务目录
    &lt;task_path&gt;
    存在？"}
    
    TASK_EXISTS -->|"NO"| EXIT_B(["sys.exit(0)
    无任务上下文，放行"])
    
    TASK_EXISTS -->|"YES"| LOAD_JSONL["get_implement_context()
    1. read_jsonl_entries()
       读取 implement.jsonl"]
    
    LOAD_JSONL --> JSONL_WARN{"JSONL 有已整理条目？"}
    
    JSONL_WARN -->|"NO"| WARN_STDERR["stderr 警告：
    'implement.jsonl 没有已整理条目
    — 子智能体将仅收到 prd.md'"]
    
    JSONL_WARN -->|"YES"| READ_FILES["逐文件读取
    JSONL 中引用的所有 spec"]
    
    WARN_STDERR --> READ_PRD
    READ_FILES --> READ_PRD["读取 prd.md"]
    
    READ_PRD --> READ_INFO{"info.md
    存在？"}
    
    READ_INFO -->|"YES"| LOAD_INFO["读取 info.md
    技术设计文档"]
    READ_INFO -->|"NO"| SKIP_INFO["跳过 info.md
    （可选文件）"]
    
    LOAD_INFO --> BUILD
    SKIP_INFO --> BUILD
    
    BUILD["build_implement_prompt()
    构建完整提示词：
    ├─ &lt;!-- trellis-hook-injected --&gt;
    ├─ 角色定义：Implement 智能体
    ├─ 上下文区块（spec + prd + info）
    ├─ 任务区块（原始 prompt）
    ├─ 工作流指引（五步）
    └─ 约束（禁止 commit 等）"]
    
    BUILD --> ASSEMBLE["组装多平台输出格式"]
    ASSEMBLE --> OUTPUT["stdout JSON 输出
    子智能体收到完整上下文"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style EXIT_A fill:#5c2a2a,stroke:#888,color:#aaa
    style EXIT_B fill:#5c2a2a,stroke:#888,color:#aaa
    style WARN_STDERR fill:#5c2a2a,stroke:#ffaa00,color:#e0e0e0
    style OUTPUT fill:#0f3460,stroke:#00ff88,color:#fff
```

---

## 图五：Implement 与 Check 上下文加载对比

```mermaid
flowchart LR
    subgraph IMPL["trellis-implement 上下文"]
        direction TB
        I1["implement.jsonl
        └─ 开发规范
        └─ 编码约定
        └─ API 设计规范"]
        I2["prd.md
        └─ 功能需求
        └─ 验收标准"]
        I3["info.md（可选）
        └─ 架构决策
        └─ 技术约束
        └─ 实现方案"]
        
        I1 --> I_PROMPT["注入实现提示词
        build_implement_prompt()"]
        I2 --> I_PROMPT
        I3 --> I_PROMPT
    end
    
    subgraph CHK["trellis-check 上下文"]
        direction TB
        C1["check.jsonl
        └─ 检查规范
        └─ 检查清单"]
        C2["prd.md
        └─ 功能需求
        └─ 验收标准"]
        
        C1 --> C_PROMPT["注入检查提示词
        build_check_prompt()"]
        C2 --> C_PROMPT
    end
    
    I_PROMPT --> COMPARE["关键差异"]
    C_PROMPT --> COMPARE
    
    COMPARE --> DIFF["implement 多加载:
    ├─ info.md（技术设计）
    └─ implement.jsonl（编码规范）
    
    check 多加载:
    └─ check.jsonl（检查清单）"]
    
    style I_PROMPT fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style C_PROMPT fill:#533483,stroke:#16213e,color:#e0e0e0
    style COMPARE fill:#1a1a2e,stroke:#e94560,color:#fff
    style DIFF fill:#1a1a2e,stroke:#e0e0e0,color:#e0e0e0
```

---

## 图六：禁止操作与权限边界

```mermaid
flowchart TD
    START(["trellis-implement 子智能体"]) --> PERM["拥有的权限"]
    
    PERM --> ALLOWED["✅ 允许的操作"]
    ALLOWED --> A1["Read — 读取任何文件"]
    ALLOWED --> A2["Write / Edit — 创建和修改代码"]
    ALLOWED --> A3["Bash — 运行 lint / type-check / grep"]
    ALLOWED --> A4["Glob / Grep — 搜索文件和代码"]
    ALLOWED --> A5["Exa MCP — 搜索外部文档"]
    
    PERM --> FORBIDDEN["❌ 禁止的操作"]
    FORBIDDEN --> F1["git commit"]
    FORBIDDEN --> F2["git push"]
    FORBIDDEN --> F3["git merge"]
    FORBIDDEN --> F4["派生子智能体
    (Agent 工具不可用)"]
    
    FORBIDDEN --> RATIONALE["设计理由"]
    
    RATIONALE --> R1["提交权归主会话
    只有经过 check 验证后
    主会话才能提交"]
    RATIONALE --> R2["防止未验证代码
    进入版本历史"]
    RATIONALE --> R3["保持 git 历史归属清晰
    提交者始终是开发者"]
    RATIONALE --> R4["防止递归膨胀
    子智能体再派子智能体
    → 无限循环"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style ALLOWED fill:#0f3460,stroke:#00ff88,color:#fff
    style FORBIDDEN fill:#5c2a2a,stroke:#ff4444,color:#fff
    style RATIONALE fill:#533483,stroke:#16213e,color:#e0e0e0
```

---

## 图七：Implement → Check 双智能体循环

```mermaid
flowchart TD
    START(["主会话：任务就绪"]) --> DISPATCH_I["阶段 2.1
    派发 trellis-implement"]
    
    DISPATCH_I --> I_WORK["trellis-implement
    五步工作流执行"]
    
    I_WORK --> I_REPORT["返回 Implementation Complete 报告"]
    
    I_REPORT --> DISPATCH_C["阶段 2.2
    派发 trellis-check"]
    
    DISPATCH_C --> C_WORK["trellis-check
    四步工作流执行"]
    
    C_WORK --> C_REPORT["返回 Self-Check Complete 报告"]
    
    C_REPORT --> ANALYZE{"主会话分析报告"}
    
    ANALYZE -->|"全部通过 ✅"| NEXT["→ 阶段 2.3
    trellis-update-spec"]
    
    ANALYZE -->|"有小问题，已修复 ✅"| NEXT
    
    ANALYZE -->|"有未修复问题 ⚠️"| DECIDE{"问题严重程度？"}
    
    DECIDE -->|"小问题"| MANUAL_FIX["主会话直接处理
    或用户决策"]
    
    DECIDE -->|"需重新实现"| DISPATCH_I
    
    DECIDE -->|"需产品决策"| ASK_USER_LOOP["向用户报告
    等待决策"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style DISPATCH_I fill:#0f3460,stroke:#00ff88,color:#fff
    style DISPATCH_C fill:#533483,stroke:#ffaa00,color:#fff
    style NEXT fill:#0f3460,stroke:#00ff88,color:#fff
    style ASK_USER_LOOP fill:#5c2a2a,stroke:#ff4444,color:#fff
```

---

## 图八：完整生命周期时序图

```mermaid
sequenceDiagram
    actor User
    participant Main as 主会话
    participant Hook as PreToolUse 钩子
    participant FS as 文件系统
    participant Impl as trellis-implement
    participant Check as trellis-check
    
    User->>Main: 触发工作流
    
    Main->>Main: 阶段 2.1：准备派发 implement
    Main->>Hook: Agent(subagent_type="trellis-implement")
    
    activate Hook
    Hook->>FS: 读取 implement.jsonl
    FS-->>Hook: spec 索引列表
    Hook->>FS: 逐文件读取 spec
    FS-->>Hook: 开发规范内容
    Hook->>FS: 读取 prd.md + info.md
    FS-->>Hook: 需求 + 技术设计
    Hook->>Hook: build_implement_prompt()
    Hook-->>Main: 更新后的 tool_input
    deactivate Hook
    
    Main->>Impl: 启动子智能体（完整上下文）
    
    activate Impl
    Impl->>Impl: 步骤 1: 理解规范
    Impl->>Impl: 步骤 2: 理解需求
    Impl->>Impl: 步骤 3: 实现功能（Write/Edit）
    Impl->>Impl: 步骤 4: lint + type-check
    
    alt 自检失败
        Impl->>Impl: 修复问题 → 重新检查
    end
    
    Impl-->>Main: Implementation Complete 报告
    deactivate Impl
    
    Main->>Main: 阶段 2.2：派发 check
    
    Main->>Hook: Agent(subagent_type="trellis-check")
    
    activate Hook
    Hook->>FS: 读取 check.jsonl + prd.md
    Hook->>Hook: build_check_prompt()
    Hook-->>Main: 更新后的 tool_input
    deactivate Hook
    
    Main->>Check: 启动子智能体
    
    activate Check
    Check->>Check: git diff 获取变更
    Check->>Check: 对照 spec 检查
    Check->>Check: 发现问题 → 自行修复
    Check->>Check: lint + type-check 验证
    Check-->>Main: Self-Check Complete 报告
    deactivate Check
    
    Main->>Main: 分析报告
    
    alt 全部通过
        Main->>Main: 阶段 2.3 → 3.4 提交
        Main->>User: 报告完成
    else 需要重新实现
        Main->>Impl: 再次派发 implement
    end
```

---

## 图九：平台适配路径对比

```mermaid
flowchart LR
    subgraph C1["Class-1 平台（有钩子）"]
        direction TB
        P1["Claude Code / Cursor
        CodeBuddy / Droid / Kiro"]
    end
    
    subgraph C2["Class-2 平台（无钩子）"]
        direction TB
        P2["Codex / Copilot
        Gemini CLI / Qoder"]
    end
    
    C1 --> PATH1["路径 1：钩子自动注入
    PreToolUse hook
    → 自动加载 implement.jsonl
    → 自动加载 prd.md + info.md
    → 上下文注入 prompt
    → 子智能体直接工作"]
    
    C2 --> PATH2["路径 2：手动加载
    1. 查找 'Active task:' 行
    2. 或 task.py current
    3. 自行读取 implement.jsonl
    4. 逐文件读取 spec
    5. 读取 prd.md + info.md"]
    
    PATH1 --> WORK
    PATH2 --> WORK
    
    WORK["执行五步实现工作流"] --> REPORT["输出报告"]
    
    style C1 fill:#0f3460,stroke:#00ff88,color:#fff
    style C2 fill:#533483,stroke:#ffaa00,color:#fff
    style WORK fill:#1a1a2e,stroke:#e0e0e0,color:#e0e0e0
    style REPORT fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图十：报告格式数据结构

```mermaid
flowchart TD
    REPORT["## Implementation Complete"] --> SECTION1
    
    SECTION1["### Files Modified（已修改文件）
    - src/components/Feature.tsx — 新组件
    - src/hooks/useFeature.ts — 新钩子
    - src/types/feature.ts — 类型定义"] --> SECTION2
    
    SECTION2["### Implementation Summary（实现总结）
    1. 创建 Feature 组件，包含 loading/error/empty 状态
    2. 添加 useFeature 钩子，处理数据获取逻辑
    3. 定义 FeatureData 和 FeatureState 类型
    4. 遵循现有的组件模式（参见 ExistingComponent）"] --> SECTION3
    
    SECTION3["### Verification Results（验证结果）
    - Lint: ✅ Passed
    - TypeCheck: ✅ Passed"]
    
    SECTION3 --> DETAIL["报告要点：
    ├─ Files Modified: 变更清单（新增/修改/删除）
    ├─ Implementation Summary: 做了什么、为什么这样做
    └─ Verification Results: 质量检查状态"]
    
    style REPORT fill:#1a1a2e,stroke:#00ff88,color:#fff
    style SECTION1 fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style SECTION2 fill:#16213e,stroke:#16213e,color:#e0e0e0
    style SECTION3 fill:#0f3460,stroke:#00ff88,color:#e0e0e0
    style DETAIL fill:#533483,stroke:#16213e,color:#e0e0e0
```

---

## 图十一："不过度工程化"原则的决策流程

```mermaid
flowchart TD
    START(["需要实现某个功能"]) --> Q1{"有现成的
    代码模式可参考？"}
    
    Q1 -->|"YES"| FOLLOW["遵循现有模式
    不引入新范式"]
    
    Q1 -->|"NO"| Q2{"这个功能
    未来真的需要
    这种灵活性吗？"}
    
    Q2 -->|"不确定"| SKIP["不做——等需求明确时
    再重构更便宜"]
    
    Q2 -->|"YES（确信）"| Q3{"增加的复杂度
    与收益匹配吗？"}
    
    Q3 -->|"NO"| SKIP
    Q3 -->|"YES"| DO_IT["可以实现
    但要写清楚 why"]
    
    FOLLOW --> VERIFY{"代码可读性
    是否保持？"}
    DO_IT --> VERIFY
    
    VERIFY -->|"YES"| DONE(["✅ 通过"])
    VERIFY -->|"NO"| SIMPLIFY["简化代码
    保持可读性优先"]
    SIMPLIFY --> DONE
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style FOLLOW fill:#0f3460,stroke:#00ff88,color:#fff
    style SKIP fill:#5c2a2a,stroke:#ffaa00,color:#e0e0e0
    style DO_IT fill:#533483,stroke:#00ff88,color:#fff
    style DONE fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图例

| 颜色 | 含义 |
|------|------|
| 🔵 蓝色 (`#0f3460`) | trellis-implement 相关 / 正常路径 |
| 🟣 紫色 (`#533483`) | trellis-check 相关 / 降级路径 |
| ⬛ 深色 (`#1a1a2e`) | 入口/出口/判断节点 |
| 🟢 绿色边框 (`#00ff88`) | 成功/正常路径标记 |
| 🟠 橙色边框 (`#ffaa00`) | 降级/手动加载路径 |
| 🔴 红色边框/背景 (`#ff4444`/`#5c2a2a`) | 禁止操作/错误/需要用户介入 |
