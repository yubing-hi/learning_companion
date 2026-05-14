# 🧠 学伴智能体系统实现方案（数据结构课程）

---

# 一、项目目标

本系统面向 **《数据结构》课程**，聚焦栈、队列、链表、树、图、递归、排序、查找等核心知识点，构建一个能够辅助学生完成 **知识问答、学习诊断、个性化练习、学习规划** 的智能学伴系统。

系统目标是实现一个围绕课程内容展开、具备学习连续性和个性化能力的教育智能体系统，而不是泛化聊天机器人。

---

# 二、技术方案与总体架构

## 1. 技术方案

- 后端框架：`FastAPI`
- 主流程编排：自定义轻量级 `orchestrator`
- LLM 与 RAG：按需使用 `LangChain`
- 数据模型校验：`Pydantic`
- 数据存储：本地文件
- 向量检索：可选 `FAISS` 或 `Chroma`

## 2. 方案优势

- `FastAPI` 适合快速构建清晰的接口与服务层
- 轻量 `orchestrator` 便于控制主流程，方便后续调试和修改
- `LangChain` 只用于 RAG、Prompt 和结构化输出，边界明确
- 本地文件存储实现成本低，适合作业初版开发，后续也方便升级

## 3. 总体架构

```text
用户/前端
   ↓
FastAPI API 层
   ↓
Controller Orchestrator
   ↓
┌─────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│   QA        │  Exercise   │ Evaluation  │ Diagnosis   │   Planner   │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
   ↓                 ↓              ↓              ↓              ↓
         Repositories / Tools / Local Files / Vector Store
   ↓
Student Profile + Question Bank + Knowledge Base
```

## 4. 分层设计

- API 层：接收请求、校验参数、返回统一响应
- Orchestrator 层：识别意图、调度服务、串联流程
- Services 层：实现问答、诊断、练习、判题、规划等核心逻辑
- Repositories 层：负责 Profile、题库、知识库的本地文件读写
- Tools 层：封装检索、LLM 调用、解析和关键词匹配能力

## 5. 推荐项目目录结构

```text
learning_assistant/
├─ app/
│  ├─ main.py
│  ├─ api/
│  │  └─ routes.py
│  ├─ orchestrator/
│  │  └─ controller.py
│  ├─ services/
│  │  ├─ qa_service.py
│  │  ├─ exercise_service.py
│  │  ├─ evaluation_service.py
│  │  ├─ diagnosis_service.py
│  │  └─ planner_service.py
│  ├─ repositories/
│  │  ├─ profile_repo.py
│  │  ├─ question_repo.py
│  │  └─ kb_repo.py
│  ├─ models/
│  │  ├─ request_models.py
│  │  ├─ response_models.py
│  │  ├─ profile_models.py
│  │  ├─ exercise_models.py
│  │  └─ plan_models.py
│  └─ tools/
│     ├─ llm_client.py
│     ├─ retriever.py
│     ├─ parser.py
│     └─ keyword_matcher.py
├─ data/
│  ├─ profiles/
│  ├─ question_bank/
│  ├─ knowledge_base/
│  └─ vector_store/
├─ idea.md
└─ requirements.txt
```

---

# 三、核心模块设计

## 1. Controller Orchestrator

### 职责

- 接收统一请求
- 识别用户意图
- 加载学生画像
- 路由到问答、练习、判题、规划等模块
- 统一组织返回结果

### 权限

- ❌ 不直接操作底层文件
- ✅ 通过 Repository 读取 Profile
- ✅ 调用 DiagnosisService 完成画像更新

### 推荐接口

```python
class Controller:
    def handle(self, request: UserRequest) -> UnifiedResponse:
        ...
```

### 路由策略

- 优先规则判断：
  - “什么是”“为什么” → `qa`
  - “出一道题”“练习一下” → `exercise`
  - “帮我规划”“三天复习” → `plan`
- 规则无法判断时，再用一次轻量 LLM 分类

## 2. QAService

### 职责

- 回答数据结构相关问题
- 基于课程知识库进行 RAG 检索
- 根据学生画像调整回答深度
- 返回结构化答案

### 自适应教学策略

- `薄弱`：详细讲解 + 基本概念 + 示例 + 易错点
- `一般`：简洁解释 + 关键原理 + 例题提示
- `掌握良好`：快速总结 + 延伸知识 + 对比分析

### 推荐接口

```python
class QAService:
    def answer(self, question: str, profile: StudentProfile) -> QAResponse:
        ...
```

### 输出示例

```json
{
  "answer": "定义...\n原理...\n示例...\n易错点...",
  "knowledge_points": ["链表", "数组"],
  "sources": ["chapter2_linked_list.md"],
  "profile_update_needed": true
}
```

## 3. DiagnosisService

### 职责

- 分析学生提问和作答结果
- 提取相关知识点
- 更新掌握程度、正确率、错题记录和历史记录
- 作为唯一的 Profile 更新入口

### 推荐接口

```python
class DiagnosisService:
    def update_profile(
        self,
        profile: StudentProfile,
        knowledge_point: str,
        evaluation_result: EvaluationResult | None = None,
        interaction_text: str | None = None
    ) -> StudentProfile:
        ...
```

### 画像更新规则

- 初始状态默认可设为 `一般`
- 连续答对 2 次：`薄弱 → 一般`
- 某知识点近期正确率 `>= 0.8`：`一般 → 掌握良好`
- 连续答错 2 次：当前状态下降一级
- 某知识点近期正确率 `< 0.5`：直接标记为 `薄弱`
- 仅提问但未作答时，只做“弱更新”，记录可能薄弱点，不直接大幅降级

## 4. ExerciseService

### 职责

- 生成围绕指定知识点的练习题
- 支持冷启动测评
- 支持按题型与难度出题
- 优先从题库检索，不足时再调用 LLM 生成

### 当前优先支持题型

- 选择题
- 简答题

### 推荐接口

```python
class ExerciseService:
    def generate(
        self,
        profile: StudentProfile,
        knowledge_point: str | None = None,
        question_type: str = "choice",
        difficulty: str = "easy",
        count: int = 1
    ) -> list[ExerciseItem]:
        ...
```

### 生成策略

- 若题库中存在匹配题目，则优先返回题库题
- 若题库不足，则调用 LLM 按知识点和难度生成新题
- 冷启动时优先返回覆盖多个基础知识点的选择题

## 5. EvaluationService

### 职责

- 对学生答案进行判定
- 给出错误分析与改进建议
- 输出统一评价结果供 DiagnosisService 更新画像

### 推荐接口

```python
class EvaluationService:
    def evaluate(
        self,
        exercise: ExerciseItem,
        student_answer: str,
        profile: StudentProfile
    ) -> EvaluationResult:
        ...
```

### 评价策略

- 选择题：标准答案直接比对
- 简答题：关键词匹配 + LLM 语义评价

### 推荐内部拆分

```python
def evaluate_choice(...)
def evaluate_short_answer(...)
```

## 6. PlannerService

### 职责

- 基于画像生成阶段性学习计划
- 结合学生目标与可用时间安排复习顺序
- 优先安排薄弱知识点

### 推荐接口

```python
class PlannerService:
    def generate_plan(
        self,
        profile: StudentProfile,
        duration: str
    ) -> StudyPlan:
        ...
```

---

# 四、统一数据结构与接口

推荐使用 `Pydantic` 定义数据模型，保证模块间交互稳定。

## 1. 核心数据模型

```python
class UserRequest(BaseModel):
    student_id: str
    message: str
    mode: str | None = None


class StudentProfile(BaseModel):
    student_id: str
    target: str
    available_time: str
    knowledge_state: dict[str, str]
    accuracy_by_topic: dict[str, float]
    wrong_questions: list[dict]
    history: dict[str, list[str]]
    updated_at: str


class QAResponse(BaseModel):
    answer: str
    knowledge_points: list[str]
    sources: list[str]
    profile_update_needed: bool


class ExerciseItem(BaseModel):
    question_id: str
    knowledge_point: str
    question_type: str
    difficulty: str
    question: str
    options: list[str] | None = None
    answer: str
    analysis: str


class EvaluationResult(BaseModel):
    question_id: str
    correct: bool
    score: float
    error_type: str | None = None
    feedback: str
    suggestion: str
    knowledge_point: str


class StudyPlan(BaseModel):
    student_id: str
    duration: str
    goals: list[str]
    daily_plan: list[str]
    focus_topics: list[str]


class UnifiedResponse(BaseModel):
    type: str
    data: dict
    profile_summary: dict
```

## 2. StudentProfile 字段说明

| 字段 | 作用 |
|------|------|
| student_id | 学生唯一标识 |
| target | 学习目标，如“期末 85 分” |
| available_time | 可学习时间，如“每天 1 小时” |
| knowledge_state | 各知识点掌握状态 |
| accuracy_by_topic | 各知识点正确率 |
| wrong_questions | 错题记录 |
| history | 近期提问、近期主题等学习历史 |
| updated_at | 最近更新时间 |

## 3. Profile 示例

```json
{
  "student_id": "stu_001",
  "target": "期末考试达到85分",
  "available_time": "每天1小时",
  "knowledge_state": {
    "栈": "一般",
    "队列": "薄弱",
    "链表": "掌握良好"
  },
  "accuracy_by_topic": {
    "栈": 0.75,
    "队列": 0.40,
    "链表": 0.90
  },
  "wrong_questions": [
    {
      "question_id": "q_013",
      "knowledge_point": "递归",
      "error_type": "理解错误"
    }
  ],
  "history": {
    "recent_questions": ["链表是什么"],
    "recent_topics": ["链表"]
  },
  "updated_at": "2026-04-05T12:00:00"
}
```

## 4. models 与 services 对应关系

| 文件 | 层级 | 主要内容 | 对应的 service 使用方式 |
|------|------|----------|-------------------------|
| `app/models/request_models.py` | models | 定义请求类数据结构，如 `UserRequest` | `Controller` 接收前端请求时使用 |
| `app/models/profile_models.py` | models | 定义学生画像数据结构，如 `StudentProfile` | `QAService`、`DiagnosisService`、`ExerciseService`、`PlannerService` 读取画像时使用 |
| `app/models/exercise_models.py` | models | 定义题目与评估相关数据结构，如 `ExerciseItem`、`EvaluationResult` | `ExerciseService` 生成题目，`EvaluationService` 评估答案时使用 |
| `app/models/plan_models.py` | models | 定义学习计划数据结构，如 `StudyPlan` | `PlannerService` 输出学习计划时使用 |
| `app/models/response_models.py` | models | 定义统一响应格式，如 `QAResponse`、`UnifiedResponse` | 各 service 产出结果、API 层返回前端时使用 |
| `app/services/qa_service.py` | services | 实现课程问答、RAG 检索后的回答生成 | 读取 `StudentProfile`，输出 `QAResponse` |
| `app/services/diagnosis_service.py` | services | 实现学情诊断与画像更新 | 读取并更新 `StudentProfile`，可结合 `EvaluationResult` 更新状态 |
| `app/services/exercise_service.py` | services | 实现练习题生成与冷启动测评出题 | 读取 `StudentProfile`，输出 `ExerciseItem` |
| `app/services/evaluation_service.py` | services | 实现选择题/简答题判题与反馈生成 | 输入 `ExerciseItem` 和学生答案，输出 `EvaluationResult` |
| `app/services/planner_service.py` | services | 实现个性化学习计划生成 | 读取 `StudentProfile`，输出 `StudyPlan` |

说明：

- `models` 负责定义“数据长什么样”，即统一的数据格式和字段规范
- `services` 负责定义“系统拿这些数据做什么”，即具体业务逻辑
- 推荐代码实现时保持“service 输入输出都尽量使用 models 中定义的结构化对象”，避免直接在模块间传递零散字典

## 5. API 设计

建议提供以下接口：

- `POST /chat`
- `POST /exercise/generate`
- `POST /exercise/evaluate`
- `POST /plan/generate`
- `GET /profile/{student_id}`
- `POST /profile/init`

建议统一返回格式：

```json
{
  "type": "qa",
  "data": {},
  "profile_summary": {
    "weak_topics": ["队列", "递归"],
    "strong_topics": ["链表"]
  }
}
```

## 6. 模块间调用原则

- 所有模块都传结构化对象
- 不让多个模块直接写文件
- Profile 更新必须统一走 DiagnosisService
- 题目对象必须统一带 `knowledge_point` 和 `question_type`

---

# 五、存储、知识库与题目设计

## 1. 本地文件存储

初版系统采用本地文件存储，以降低实现复杂度，并保留后续升级空间。

```text
data/
├─ profiles/
│  ├─ stu_001.json
│  └─ stu_002.json
├─ question_bank/
│  ├─ stack.json
│  ├─ queue.json
│  └─ recursion.json
├─ knowledge_base/
│  ├─ chapter1.md
│  ├─ chapter2.md
│  └─ notes.md
└─ vector_store/
   └─ ...
```

## 2. Repository 设计

```python
class ProfileRepository:
    def get(self, student_id: str) -> StudentProfile: ...
    def save(self, profile: StudentProfile) -> None: ...
    def exists(self, student_id: str) -> bool: ...


class QuestionRepository:
    def search(
        self,
        knowledge_point: str,
        difficulty: str,
        question_type: str
    ) -> list[ExerciseItem]:
        ...


class KnowledgeBaseRepository:
    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        ...
```

## 3. 知识库与 RAG

### 知识库内容：

- 数据结构教材摘要
- 课堂 PPT
- 教师讲义
- 自己整理的知识点 Markdown
- 题目解析文本

### 构建流程：

- 读取课程文档
- 切分为知识片段
- 为文本片段生成向量
- 建立本地向量索引
- 提问时检索最相关片段，再交给 LLM 生成回答

### 要求：

- 以**markdown**格式给出，放在knowledge_base文件夹中
- 每个文档不可过长，防止检索窗口切不到
- 可以在文档最前面加上元数据头

`LangChain` 主要用于：

- 文档加载与切分
- Embedding 调用
- Retriever 封装
- PromptTemplate 组织上下文
- Output Parser 输出结构化结果

## 4. 题目生成与评价设计

当前优先实现：

- 选择题
- 简答题

后续可扩展：

- 填空题
- 代码阅读题
- 编程题

生成策略：

- 初始评估优先使用基础选择题
- 薄弱知识点强化时，生成围绕单一知识点的选择题或简答题
- 进阶训练时加入多知识点综合题

评价策略：

- 选择题：直接答案匹配，输出正确与否、正确答案、解析
- 简答题：先做关键词覆盖检测，再由 LLM 做语义评价，输出错误原因与改进建议

---

# 六、系统流程设计

## 1. 问答流程

```text
用户提问
 → API 接口接收请求
 → Controller 判断为 qa
 → 读取 Student Profile
 → QAService 调用 RAG 检索并生成答案
 → DiagnosisService 根据提问内容做弱更新
 → 返回结构化回答
```

## 2. 练习流程

```text
用户请求练习
 → API 接口接收请求
 → Controller 判断为 exercise
 → 读取 Student Profile
 → ExerciseService 从题库/LLM 生成题目
 → 用户提交答案
 → EvaluationService 评价答案
 → DiagnosisService 更新 knowledge_state / accuracy / wrong_questions
 → 保存 Profile
 → 返回反馈
```

## 3. 学习计划流程

```text
用户请求计划
 → API 接口接收请求
 → Controller 判断为 plan
 → 读取 Student Profile
 → PlannerService 生成学习计划
 → 返回个性化计划
```

## 4. 冷启动流程

```text
新用户进入系统
 → 创建默认 Profile
 → ExerciseService 生成基础测评题
 → EvaluationService 完成测评
 → DiagnosisService 初始化知识点掌握程度
 → 保存 Profile
```

---

# 七、扩展性与开发优先级

## 1. 可扩展性设计

当前方案具备较好的后续优化空间，主要体现在：

- 可单独升级 QA 的 RAG 方案
- 可单独增加新题型
- 可单独增强 Planner 的计划逻辑
- 可单独替换本地文件为数据库

后续可在 `StudentProfile` 中增加：

- `last_review_time`
- `preferred_difficulty`
- `learning_style`
- `mastery_score`

前端也可逐步扩展为：

- 聊天窗口
- 学习画像面板
- 错题本页面
- 学习计划可视化页面

## 2. 开发优先级

### 第一阶段：最小可运行系统

- 搭建 FastAPI 项目结构
- 定义 Pydantic 数据模型
- 完成 ProfileRepository 本地读写
- 完成 QuestionRepository 题库读取
- 实现 Controller 基础路由
- 实现 QA、Exercise、Evaluation、Diagnosis、Planner 的最小版本

### 第二阶段：增强智能能力

- 接入 LangChain 和本地知识库
- 完成 RAG 检索问答
- 增强简答题语义评价
- 优化学习计划生成

### 第三阶段：展示与答辩优化

- 增加简单系统界面
- 展示画像变化过程
- 准备冷启动与个性化示例

---

# 八、系统亮点总结

- 面向《数据结构》课程，任务边界明确
- 采用 `FastAPI + 轻量 orchestrator + LangChain 辅助`，工程结构清晰
- 多模块协作，但主流程可控，便于调试和后续优化
- 使用 Student Profile 维持学习连续性
- 采用 RAG 降低幻觉，提升课程一致性
- 通过题库、评价与诊断形成完整学习闭环
- 初版使用本地文件，开发成本低，后续可平滑升级

---

# ✅ 一句话总结

> 本系统基于 FastAPI、轻量级 Orchestrator 与按需使用的 LangChain，围绕《数据结构》课程实现知识问答、学情诊断、个性化练习与学习规划闭环，并采用 Student Profile 与本地文件存储支撑可迭代、可扩展的实现方案。
