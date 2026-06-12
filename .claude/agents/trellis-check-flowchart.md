# trellis-check 智能体流程图

> 使用 Mermaid 语法绘制的完整流程图集。
> 在支持 Mermaid 的 Markdown 渲染器中查看（GitHub、VS Code + 插件、Typora 等）。

---

## 图一：整体架构 — trellis-check 在 Trellis 工作流中的位置

```mermaid
flowchart TB
    subgraph MAIN["主会话 Main Session"]
        direction TB
        S1["阶段 2.1：派发 trellis-implement"]
        S2["阶段 2.2：派发 trellis-check"]
        S3["阶段 2.3：trellis-update-spec"]
        S4["阶段 3：提交 & 完成"]
        
        S1 --> S2 --> S3 --> S4
    end
    
    subgraph IMPLEMENT["trellis-implement 子智能体"]
        I1["理解规范 & 需求"]
        I2["实现功能"]
        I3["自检验证"]
        I4["输出 Implementation Complete 报告"]
        I1 --> I2 --> I3 --> I4
    end
    
    subgraph CHECK["trellis-check 子智能体"]
        C1["获取代码变更"]
        C2["对照规范检查"]
        C3["自行修复问题"]
        C4["运行验证"]
        C5["输出 Self-Check Complete 报告"]
        C1 --> C2 --> C3 --> C4 --> C5
    end
    
    S1 -.->|"Agent(subagent_type='trellis-implement')"| IMPLEMENT
    IMPLEMENT -.->|"报告结果"| S2
    S2 -.->|"Agent(subagent_type='trellis-check')"| CHECK
    CHECK -.->|"报告结果"| S3
    
    style MAIN fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style IMPLEMENT fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style CHECK fill:#533483,stroke:#16213e,color:#e0e0e0
```

---

## 图二：trellis-check 上下文加载决策树

```mermaid
flowchart TD
    START(["trellis-check 子智能体启动"]) --> Q1{"输入中是否有
    &lt;!-- trellis-hook-injected --&gt;
    标记？"}
    
    Q1 -->|"✅ YES（Class-1 平台正常路径）"| HOOK_INJECTED["上下文已由钩子注入
    直接进入工作流"]
    
    Q1 -->|"❌ NO（钩子失败/未触发）"| Q2{"分派提示第一行
    是否有
    'Active task: &lt;path&gt;'？"}
    
    Q2 -->|"✅ YES"| MANUAL_LOAD["从 task path 手动加载：
    1. 读取 &lt;task&gt;/prd.md
    2. 读取 &lt;task&gt;/check.jsonl
    3. 逐条读取 JSONL 中引用的 spec 文件"]
    
    Q2 -->|"❌ NO"| Q3{"运行 task.py current
    能否获取任务路径？"}
    
    Q3 -->|"✅ YES"| MANUAL_LOAD
    Q3 -->|"❌ NO"| ASK_USER["询问用户当前活动任务
    不盲目猜测"]
    
    HOOK_INJECTED --> WORKFLOW_START(["进入检查工作流"])
    MANUAL_LOAD --> WORKFLOW_START
    ASK_USER --> WORKFLOW_START
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style HOOK_INJECTED fill:#0f3460,stroke:#00ff88,color:#fff
    style MANUAL_LOAD fill:#533483,stroke:#ffaa00,color:#fff
    style ASK_USER fill:#5c2a2a,stroke:#ff4444,color:#fff
    style WORKFLOW_START fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图三：四步检查工作流（核心流程）

```mermaid
flowchart TD
    START(["上下文加载完成"]) --> STEP1
    
    subgraph STEP1["步骤 1：获取变更"]
        direction LR
        S1A["git diff --name-only
        列出已更改文件"] --> S1B["git diff
        查看具体变更内容"] --> S1C["确定检查范围"]
    end
    
    STEP1 --> STEP2
    
    subgraph STEP2["步骤 2：对照规范检查"]
        direction TB
        S2A["阅读 .trellis/spec/ 中相关规范"] --> S2B{"逐项检查"}
        S2B --> S2C["目录结构惯例"]
        S2B --> S2D["命名惯例"]
        S2B --> S2E["代码模式一致性"]
        S2B --> S2F["类型定义完整性"]
        S2B --> S2G["潜在 bug"]
        S2C & S2D & S2E & S2F & S2G --> S2H["汇总问题列表"]
    end
    
    STEP2 --> Q_FOUND{"发现问题？"}
    
    Q_FOUND -->|"YES"| STEP3
    
    subgraph STEP3["步骤 3：自行修复"]
        direction TB
        S3A["对每个问题："] --> S3B{"能否自动修复？"}
        S3B -->|"YES"| S3C["使用 Edit 工具直接修复"]
        S3B -->|"NO"| S3D["记录到 Issues Not Fixed
        附无法修复的原因"]
        S3C --> S3E["记录到 Issues Fixed"]
        S3D --> S3F{"还有更多问题？"}
        S3E --> S3F
        S3F -->|"YES"| S3B
        S3F -->|"NO"| STEP4
    end
    
    Q_FOUND -->|"NO"| STEP4
    
    subgraph STEP4["步骤 4：运行验证"]
        direction TB
        S4A["运行 lint 命令"] --> S4B{"Lint 通过？"}
        S4B -->|"NO"| S4C["修复 lint 错误"]
        S4C --> S4A
        S4B -->|"YES"| S4D["运行 type-check"]
        S4D --> S4E{"TypeCheck 通过？"}
        S4E -->|"NO"| S4F["修复类型错误"]
        S4F --> S4D
        S4E -->|"YES"| S4G{"运行测试（如适用）"}
        S4G -->|"NO"| S4H["修复测试失败"]
        S4H --> S4G
        S4G -->|"YES / N/A"| REPORT
    end
    
    REPORT["生成 Self-Check Complete 报告"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style STEP1 fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style STEP2 fill:#16213e,stroke:#16213e,color:#e0e0e0
    style STEP3 fill:#533483,stroke:#16213e,color:#e0e0e0
    style STEP4 fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style REPORT fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图四：Skill 模式下的六步工作流

```mermaid
flowchart TD
    START(["用户输入 /trellis-check"]) --> S1
    
    S1["步骤 1：识别变更内容
    git diff --name-only HEAD
    git status"] --> S2
    
    S2["步骤 2：阅读适用的 Spec
    py -3 ./.trellis/scripts/get_context.py --mode packages
    对每个变更的 package/layer 读取 spec 索引"] --> S3
    
    S3["步骤 3：运行项目检查
    lint + type-check + tests
    修复所有失败后再继续"] --> S4
    
    S4["步骤 4：对照 Checklist 审查"] --> S4_CHECKLIST
    
    subgraph S4_CHECKLIST["审查清单"]
        direction TB
        C1["代码质量
        □ Linter 通过？
        □ 类型检查器通过？
        □ 测试通过？
        □ 无遗留调试日志？
        □ 无抑制的警告？"]
        
        C2["测试覆盖
        □ 新函数有单元测试？
        □ Bug 修复有回归测试？
        □ 行为变更已更新已有测试？"]
        
        C3["Spec 同步
        □ .trellis/spec/ 需要更新？
        （新 pattern、convention、经验教训）"]
    end
    
    S4_CHECKLIST --> Q_CROSS{"变更涉及
    3 层以上？"}
    
    Q_CROSS -->|"YES"| S5
    
    subgraph S5["步骤 5：跨层维度检查"]
        direction TB
        D1["A. 数据流
        Storage→Service→API→UI（读）
        UI→API→Service→Storage（写）
        类型在各层间传递正确？
        错误正确传播？"]
        
        D2["B. 代码复用
        grep -r 搜索已有模式
        2 处以上相同值 → 提取常量
        批量修改后全部更新？"]
        
        D3["C. 导入/依赖
        路径正确（相对 vs 绝对）？
        无循环依赖？"]
        
        D4["D. 同层一致性
        同一概念在其他位置一致？"]
    end
    
    Q_CROSS -->|"NO"| S6
    S5 --> S6
    
    S6["步骤 6：报告并修复
    报告违规项 → 直接修复
    → 重新运行项目检查"] --> END_NODE(["检查完成"])
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style END_NODE fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图五：PreToolUse 钩子上下文注入流程

```mermaid
flowchart TD
    START(["主会话调用
    Agent(subagent_type='trellis-check')"]) --> HOOK["PreToolUse 钩子触发
    inject-subagent-context.py"]
    
    HOOK --> PARSE["解析 stdin JSON
    _parse_hook_input()"]
    
    PARSE --> CHECK_TYPE{"子智能体类型
    == 'trellis-check'？"}
    
    CHECK_TYPE -->|"NO"| EXIT0A(["sys.exit(0)
    不修改，放行"])
    
    CHECK_TYPE -->|"YES"| FIND_TASK["查找活动任务
    get_current_task()
    → resolve_active_task()"]
    
    FIND_TASK --> TASK_EXISTS{"任务目录存在？"}
    
    TASK_EXISTS -->|"NO"| EXIT0B(["sys.exit(0)
    无任务上下文，放行"])
    
    TASK_EXISTS -->|"YES"| CHECK_FINISH{"prompt 包含
    '[finish]'？"}
    
    CHECK_FINISH -->|"YES"| FINISH_CTX["加载 Finish 上下文
    get_check_context()
    → build_finish_prompt()"]
    
    CHECK_FINISH -->|"NO"| NORMAL_CTX["加载常规 Check 上下文
    get_check_context()
    → build_check_prompt()"]
    
    FINISH_CTX --> LOAD_JSONL
    NORMAL_CTX --> LOAD_JSONL
    
    LOAD_JSONL["read_jsonl_entries()
    读取 check.jsonl"] --> LOAD_PRD["读取 prd.md"]
    
    LOAD_PRD --> BUILD_PROMPT["构建注入后的 prompt
    = 角色定义
    + 上下文区块（spec 文件内容）
    + 任务区块（原始 prompt）
    + 工作流指引"]
    
    BUILD_PROMPT --> ASSEMBLE["组装多平台输出
    hookSpecificOutput.updatedInput (Claude Code)
    updated_input (Cursor)
    updatedInput (Gemini CLI)"]
    
    ASSEMBLE --> OUTPUT["stdout JSON 输出
    子智能体收到完整上下文"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style EXIT0A fill:#5c2a2a,stroke:#888,color:#aaa
    style EXIT0B fill:#5c2a2a,stroke:#888,color:#aaa
    style OUTPUT fill:#0f3460,stroke:#00ff88,color:#fff
```

---

## 图六：递归防护机制

```mermaid
flowchart TD
    START(["trellis-check 子智能体
    收到系统提示"]) --> READ_GUIDELINES["读取 &lt;guidelines&gt; 块：
    '对于支持智能体的平台，
    默认调度 trellis-implement
    和 trellis-check'"]
    
    READ_GUIDELINES --> GUARD{"递归防护判断：
    我是什么角色？"}
    
    GUARD -->|"我是 trellis-check
    子智能体"| SELF_EXEMPT["自我豁免：
    '你已经是已调度的子智能体。
    直接实现/检查，
    不要再次派生同类型。'"]
    
    GUARD -->|"我是主会话"| DISPATCH["可以分派子智能体"]
    
    SELF_EXEMPT --> THREE_LAYER
    
    subgraph THREE_LAYER["三层防护"]
        direction TB
        L1["🛡️ 第 1 层：提示词防护
        Agent 定义中的递归防护说明
        '不要派生另一个 trellis-check
        或 trellis-implement 子智能体'"]
        
        L2["🛡️ 第 2 层：工具集防护
        Agent 定义 tools 列表中
        不包含 Agent 工具
        物理上无法调用"]
        
        L3["🛡️ 第 3 层：平台级防护
        Codex: multi_agent = false
        multi_agent_v2.enabled = false
        spawn_agent 工具不可用"]
    end
    
    SELF_EXEMPT --> RESULT["结果：
    子智能体只能自行执行
    检查和修复工作
    需要更多实现 →
    在报告中建议主会话派发"]
    
    style START fill:#1a1a2e,stroke:#e94560,color:#fff
    style SELF_EXEMPT fill:#533483,stroke:#ffaa00,color:#fff
    style DISPATCH fill:#0f3460,stroke:#00ff88,color:#fff
    style RESULT fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图七：平台适配路径对比

```mermaid
flowchart LR
    subgraph PLATFORMS["平台分类"]
        direction TB
        
        subgraph C1["Class-1 平台（有钩子）"]
            direction TB
            P1A["Claude Code"]
            P1B["Cursor"]
            P1C["CodeBuddy"]
            P1D["Droid (Factory)"]
            P1E["Kiro"]
        end
        
        subgraph C2["Class-2 平台（无钩子）"]
            direction TB
            P2A["Codex"]
            P2B["Copilot"]
            P2C["Gemini CLI"]
            P2D["Qoder"]
        end
    end
    
    C1 --> PATH1["路径 1：钩子自动注入
    PreToolUse hook
    → inject-subagent-context.py
    → 上下文自动注入 prompt"]
    
    C2 --> PATH2["路径 2：手动加载协议
    1. 查找分派提示中的
       'Active task:' 行
    2. 或运行 task.py current
    3. 自行读取 check.jsonl
    4. 逐文件读取 spec"]
    
    PATH1 --> WORK["执行检查工作流"]
    PATH2 --> WORK
    
    WORK --> REPORT["输出结构化报告"]
    
    style C1 fill:#0f3460,stroke:#00ff88,color:#fff
    style C2 fill:#533483,stroke:#ffaa00,color:#fff
    style WORK fill:#1a1a2e,stroke:#e0e0e0,color:#e0e0e0
    style REPORT fill:#1a1a2e,stroke:#00ff88,color:#fff
```

---

## 图八：完整生命周期时序图

```mermaid
sequenceDiagram
    actor User
    participant Main as 主会话
    participant Hook as PreToolUse 钩子
    participant FS as 文件系统
    participant Check as trellis-check 子智能体
    
    User->>Main: 触发工作流
    Main->>Main: 阶段 2.1：派发 trellis-implement
    Note over Main: implement 完成，返回报告
    
    Main->>Main: 阶段 2.2：准备派发 trellis-check
    Main->>Hook: Agent(subagent_type="trellis-check", prompt="...")
    
    Hook->>FS: 读取 <task>/check.jsonl
    FS-->>Hook: JSONL 内容（spec 索引）
    
    Hook->>FS: 逐个读取 JSONL 中引用的 spec 文件
    FS-->>Hook: spec 文件内容
    
    Hook->>FS: 读取 <task>/prd.md
    FS-->>Hook: 需求文档内容
    
    Hook->>Hook: 构建注入后的 prompt
    Hook-->>Main: 更新后的 tool_input
    
    Main->>Check: 启动子智能体（含注入上下文）
    
    activate Check
    Check->>Check: 上下文加载判断
    Note over Check: 检测到 <!-- trellis-hook-injected -->
    
    Check->>Check: 步骤 1: git diff 获取变更
    Check->>Check: 步骤 2: 对照 spec 逐项检查
    Check->>Check: 步骤 3: 发现问题 → 自行修复
    Check->>Check: 步骤 4: 运行 lint + type-check
    
    Check-->>Main: Self-Check Complete 报告
    deactivate Check
    
    Main->>Main: 分析报告
    alt 全部通过
        Main->>Main: 阶段 2.3：trellis-update-spec
    else 有未修复问题
        Main->>Main: 决定是否重新派发 implement
    end
    
    Main->>User: 报告完成状态
```

---

## 图九：Finish 阶段 vs 常规 Check 对比

```mermaid
flowchart LR
    subgraph NORMAL["常规 Check（阶段 2.2）"]
        direction TB
        N1["角色：代码和跨层检查器"]
        N2["输入：check.jsonl + prd.md"]
        N3["工作流：获取变更→检查→修复→验证"]
        N4["规范更新：不建议"]
        N5["输出：Self-Check Complete"]
        N1 --> N2 --> N3 --> N4 --> N5
    end
    
    subgraph FINISH["Finish Check（阶段 3）"]
        direction TB
        F1["角色：PR 前最终检查"]
        F2["输入：check.jsonl + prd.md"]
        F3["工作流：审查变更→验证需求→规范同步→最终检查→确认就绪"]
        F4["规范更新：可以更新 spec（含 7 段式模板）"]
        F5["输出：Final Check Complete"]
        F1 --> F2 --> F3 --> F4 --> F5
    end
    
    TRIGGER{"prompt 包含
    '[finish]'？"} -->|"NO"| NORMAL
    TRIGGER -->|"YES"| FINISH
    
    style NORMAL fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style FINISH fill:#533483,stroke:#16213e,color:#e0e0e0
    style TRIGGER fill:#1a1a2e,stroke:#e94560,color:#fff
```

---

## 图十：报告格式数据结构

```mermaid
flowchart TD
    REPORT["Self-Check Complete 报告"] --> SECTION1
    
    SECTION1["### Files Checked（已检查文件）
    - src/components/Feature.tsx
    - src/hooks/useFeature.ts
    - src/utils/helpers.ts"] --> SECTION2
    
    SECTION2["### Issues Found and Fixed（发现并修复的问题）
    1. src/components/Feature.tsx:42 - 缺少类型注解
    2. src/hooks/useFeature.ts:15 - 未使用的导入
    3. src/utils/helpers.ts:8 - 潜在空指针"] --> SECTION3
    
    SECTION3["### Issues Not Fixed（未修复的问题）
    - src/components/Feature.tsx:78
      需要产品确认的错误处理策略
      原因：涉及业务逻辑判断"] --> SECTION4
    
    SECTION4["### Verification Results（验证结果）
    - TypeCheck: ✅ Passed
    - Lint: ✅ Passed
    - Tests: ✅ 15/15 Passed"] --> SECTION5
    
    SECTION5["### Summary（总结）
    Checked 3 files, found 4 issues,
    fixed 3, 1 needs product decision."]
    
    style REPORT fill:#1a1a2e,stroke:#00ff88,color:#fff
    style SECTION1 fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style SECTION2 fill:#16213e,stroke:#16213e,color:#e0e0e0
    style SECTION3 fill:#5c2a2a,stroke:#ffaa00,color:#e0e0e0
    style SECTION4 fill:#0f3460,stroke:#00ff88,color:#e0e0e0
    style SECTION5 fill:#1a1a2e,stroke:#e0e0e0,color:#e0e0e0
```

---

## 图例

| 颜色 | 含义 |
|------|------|
| 🟣 紫色 (`#533483`) | trellis-check 相关 |
| 🔵 蓝色 (`#0f3460`) | 系统/平台相关 |
| ⬛ 深色 (`#1a1a2e`) | 入口/出口节点 |
| 🟢 绿色边框 (`#00ff88`) | 成功/正常路径 |
| 🟠 橙色边框 (`#ffaa00`) | 降级/手动路径 |
| 🔴 红色边框 (`#ff4444`) | 错误/需要用户介入 |
