# 多智能体学伴系统的轻量高效 RAG 方案

## 1. 现状判断

结合 `idea.md` 的系统目标和当前 `data/knowledge_base/` 结构，现有知识库已经有两个优点：

- 知识范围比较收敛，主要围绕数据结构课程
- 树与二叉树主题已经被拆成多个子文件，天然适合细粒度检索

但当前实现的 RAG 仍然偏“最小可用”：

- `KnowledgeBaseRepository.retrieve()` 还是本地全文遍历 + 简单关键词命中
- chunk 主要按段落和固定字符数切分，没有显式章节语义
- 没有召回后重排，容易把“沾边但不关键”的段落塞进上下文
- 没有上下文预算控制，后续一旦知识库继续增大，token 会明显浪费

所以更合适的方向不是无限扩张知识库或引入很重的 Agent 检索链，而是做一套：

`主题路由 -> 混合召回 -> 轻量 rerank -> 上下文压缩 -> 按任务注入`

这套方案能明显提升回答质量，同时把 token 和工程复杂度控制住。

---

## 2. 设计目标

这套 RAG 方案建议优先满足 4 个目标：

1. 检索更准：减少“相关但不回答问题”的段落进入上下文
2. token 更省：只给 LLM 最必要的证据片段
3. 任务可控：不同智能体只取自己需要的上下文
4. 便于迭代：先做轻量版本，后续再平滑接入向量库和更强 reranker

---

## 3. 推荐总方案

### 3.1 总体链路

建议把当前 QA 检索链路升级为：

```text
用户问题
-> Query 理解与主题识别
-> Topic/文件级预筛选
-> 混合召回（稀疏 + 稠密）
-> 轻量 rerank
-> 相邻片段合并 / 去重 / 压缩
-> 按 token 预算打包上下文
-> 交给对应智能体生成答案
```

其中最关键的是 4 个点：

- 先做“文件级预筛选”，减少全库搜索
- 用“混合召回”补足单一关键词检索的不稳定性
- 用“轻量 rerank”解决最终上下文排序问题
- 用“预算式打包”限制 token 消耗

---

## 4. 知识库侧改造

### 4.1 保持当前分文件结构，不继续无限拆分

你现在的结构已经比“大而全单文件”合理：

- `tree_and_binarytree_01_tree_and_binary_tree_basics.md`
- `tree_and_binarytree_02_binary_tree_traversal_and_threading.md`
- `tree_and_binarytree_03_tree_forest_and_huffman.md`
- `tree_and_binarytree_04_complexity_teaching_and_examples.md`

建议继续保持“主题文件 + 章节内小节”的模式，不要继续拆成几十个超小文件。原因是：

- 文件太碎会让索引维护复杂
- rerank 候选会变多
- 上下文拼接会更零散

比较合适的是：

- 文件级：一个中等主题
- chunk 级：文件中的一个小节或一个小节下的 1 到 2 个自然段

### 4.2 给每个知识文件补元数据头

建议每个 `.md` 文件都补一个 front matter，最少保留这些字段：

```yaml
---
topic: tree_and_binarytree
subtopics: [tree, binary_tree, full_binary_tree, complete_binary_tree]
aliases: [树, 二叉树, 满二叉树, 完全二叉树]
difficulty: basic
priority: high
---
```

再增加两个很实用的字段：

- `prerequisites`: 先修概念
- `related_files`: 相关文件名

这样做的价值是：

- 可先按 topic / alias 做文件预筛
- 可在 rerank 后补充相邻知识
- 可支持后续“弱项优先”的个性化加权

### 4.3 建一个轻量索引文件，而不是每次临时扫库

建议在 `data/vector_store/` 下维护两个索引产物：

- `kb_chunks.jsonl`
- `kb_manifest.json`

其中每条 chunk 至少包含：

```json
{
  "chunk_id": "tree_and_binarytree_02#sec_2_3",
  "file_name": "tree_and_binarytree_02_binary_tree_traversal_and_threading.md",
  "topic": "tree_and_binarytree",
  "section_title": "二叉树的遍历",
  "aliases": ["前序遍历", "中序遍历", "后序遍历", "层序遍历"],
  "char_count": 320,
  "text": "...",
  "prev_chunk_id": "tree_and_binarytree_02#sec_2_2",
  "next_chunk_id": "tree_and_binarytree_02#sec_2_4"
}
```

这个索引很重要，因为它能支撑：

- 快速过滤
- 相邻 chunk 合并
- 按 section_title 做结果解释
- 未来无缝加 embedding / reranker

---

## 5. Chunk 设计

### 5.1 不建议只按固定字符切

当前 `chunk_size=400` 的固定切分太粗糙，容易把一个概念定义截断，或把“定义”和“例子”拆开。

建议改成“标题感知切分”：

1. 先按 Markdown 标题切成 section
2. section 过长时，再按自然段切
3. 再长才做字符级兜底切分

### 5.2 推荐 chunk 粒度

推荐每个 chunk 控制在：

- 中文 180 到 350 字左右
- 尽量是一个完整的小知识单元

对于“定义 + 性质 + 对比”这类紧密内容，不要强行拆太碎。

### 5.3 使用 Parent-Child 思路，但做轻量版

不用上完整 ParentDocumentRetriever，也可以借鉴它的思想：

- 检索对象是 child chunk
- 最终送给 LLM 的是 child 所属 section 的精简父块

例如：

- 召回命中“完全二叉树定义”
- 最终给模型的是“完全二叉树定义 + 判定方法 + 与满二叉树区别”的合并段

这样能兼顾：

- 召回精度
- 上下文完整性
- token 控制

---

## 6. 检索策略

### 6.1 先做文件级预筛选

这是最划算的一步。

在真正 chunk 检索前，先根据下面信息选出候选文件：

- 用户问题中的主题词
- 文件 front matter 的 `aliases`
- 学生画像中的弱项 topic
- 当前智能体任务类型

建议控制为：

- 全库文件数较小时：最多保留 3 到 5 个候选文件
- 单主题明确时：只搜 1 到 2 个文件

例如：

- 问“完全二叉树和满二叉树区别”
- 优先只搜 `tree_and_binarytree_01` 与 `tree_and_binarytree_04`

这样比全库直接向量检索更省，也更稳。

### 6.2 使用混合召回，而不是只靠向量或只靠关键词

建议召回层采用：

- 稀疏检索：BM25 或关键词倒排
- 稠密检索：embedding 相似度

然后做融合。

推荐的轻量融合方式：

```text
final_recall_score =
0.45 * sparse_score +
0.45 * dense_score +
0.10 * metadata_boost
```

其中 `metadata_boost` 可以来自：

- 命中标题
- 命中 alias
- 命中学生弱项 topic
- 文件优先级更高

如果你当前阶段还不想立即接入向量库，也可以先做过渡版：

- 第一阶段：关键词/标题命中 + alias 命中 + 简单词频
- 第二阶段：再加 embedding

### 6.3 候选数必须限制

建议严格限制：

- 稀疏召回 top 8
- 稠密召回 top 8
- 融合去重后保留 10 到 12 个候选

这一步就能避免 rerank 面对太多候选，造成额外开销。

---

## 7. Rerank 设计

### 7.1 Rerank 必须加，但要轻量

对于你的系统，rerank 是最值得加的一层，因为：

- 数据结构问答常常术语相近
- 真正影响回答质量的不是“有没有召回到”，而是“排在最前面的证据对不对”

### 7.2 推荐两档方案

#### 方案 A：本地轻量 reranker

如果后续可接本地模型，优先考虑：

- `bge-reranker-base`
- 同级别 cross-encoder reranker

适合：

- 候选 8 到 12 条
- 只对最终候选做排序

优点：

- 不额外消耗 LLM token
- 排序效果通常显著好于简单相似度

#### 方案 B：规则型 rerank + 小模型打分

如果当前阶段不想引入专门 reranker，可以先做：

```text
rerank_score =
0.35 * title_match +
0.25 * alias_match +
0.20 * keyword_density +
0.10 * same_topic_boost +
0.10 * question_type_boost
```

其中 `question_type_boost` 例如：

- “区别/对比”类问题，优先含“区别/对比/比较”标题的 chunk
- “定义”类问题，优先含“定义/概念/性质”标题的 chunk
- “怎么做题”类问题，优先含“例题/易错点/复杂度分析”的 chunk

这虽然不如真正的 cross-encoder，但已经能明显优于“直接相似度 top_k”。

### 7.3 Rerank 后只保留很少的片段

建议最终给 LLM 的 chunk 数是：

- QA：2 到 4 个
- 习题解析：2 到 3 个
- 学习规划：1 到 2 个 topic 摘要，不直接塞原始长段

这一步非常关键。RAG 质量提升不来自“塞更多”，而来自“塞最对的那几段”。

---

## 8. 上下文压缩与 token 预算

### 8.1 必须有硬预算

建议在检索层就设置预算，不要等到 prompt 太长了才裁剪。

可以给不同任务设不同预算：

- QA 问答上下文：600 到 1000 中文字
- 题目解析上下文：400 到 700 中文字
- 学习规划上下文：用 topic 摘要，不直接塞 chunk，控制在 300 到 500 中文字

### 8.2 压缩规则

对 rerank 后的结果，按下面顺序压缩：

1. 去重：相似 chunk 只留一条
2. 合并：同文件相邻 chunk 合并
3. 截断：每个 chunk 最多保留 220 到 300 字
4. 摘要：若仍超预算，对最低优先级 chunk 做 extractive summary

建议优先做“抽取式压缩”，不要一开始就再调用 LLM 摘要，因为那会额外耗时和耗 token。

### 8.3 上下文拼接格式

送给 LLM 的上下文不要只是纯文本拼接，建议保留结构：

```text
[1] 文件: tree_and_binarytree_01...
标题: 完全二叉树
内容: ...

[2] 文件: tree_and_binarytree_04...
标题: 满二叉树与完全二叉树对比
内容: ...
```

这会提升模型引用和组织答案的稳定性。

---

## 9. 面向多智能体的 RAG 分工

你的系统不是单一 QA Bot，而是多智能体学伴系统，所以不要所有智能体共用同一个“全能检索器”。

建议拆成 3 类检索模式。

### 9.1 QA 智能体

目标：

- 回答“是什么、为什么、怎么区分、如何理解”

检索策略：

- 文件级预筛
- 混合召回
- rerank
- 给 2 到 4 个精炼 chunk

### 9.2 Exercise / Evaluation 智能体

目标：

- 生成练习
- 判题或给错因分析

检索策略：

- 优先查题库
- 只在题目解析或知识点解释时查 RAG
- RAG 只拿“定义 + 易错点 + 示例”小上下文

不要把长篇课程笔记直接喂给判题智能体。

### 9.3 Planner / Diagnosis 智能体

目标：

- 生成复习计划
- 判断学生薄弱点

检索策略：

- 不直接查原始 chunk
- 依赖 topic-level 摘要、学生画像、错误记录

也就是说，规划智能体主要用“知识摘要层”，而不是“原始文本层”。

这能显著减少 token 消耗。

---

## 10. 建议加入两层知识表示

为了兼顾问答质量和 token 控制，建议知识库同时维护两层表示：

### 10.1 Chunk 层

用于精确问答和证据检索。

### 10.2 Topic Summary 层

每个主题单独维护一份短摘要，例如：

- 核心定义
- 高频混淆点
- 常见题型
- 学习建议

例如在 `data/knowledge_base/summary/` 下维护：

- `tree_and_binarytree.summary.md`
- `stack.summary.md`
- `queue.summary.md`

这层主要给：

- Planner
- Diagnosis
- 冷启动引导
- 大范围复习建议

这样能避免这些任务反复调用原始长文档。

---

## 11. 最小可实现版本

为了避免一次性做太重，建议分三步实现。

### 第一步：低成本升级

只改现有本地检索，不上向量库也可以：

1. 给知识文件补 front matter
2. 改成按 Markdown 标题切 chunk
3. 增加文件级预筛选
4. 增加规则型 rerank
5. 增加上下文预算与相邻合并

这一步通常就能比现在明显提升。

### 第二步：接入 embedding 混合召回

建议新增：

- `kb_chunks.jsonl`
- embedding 建库脚本
- 本地向量索引

召回改成：

- sparse top 8
- dense top 8
- merge + rerank

### 第三步：按智能体拆检索入口

例如：

- `QARetriever`
- `ExerciseContextRetriever`
- `PlannerSummaryRetriever`

这样各模块不会共享同一套大而全上下文。

---

## 12. 与当前项目结构的对应落点

你现在项目里最适合改造的点如下：

- `app/repositories/kb_repo.py`
  - 从“遍历文件 + 段落打分”升级成“索引驱动检索器”
- `app/tools/retriever.py`
  - 从薄封装升级成支持 `mode/top_k/token_budget` 的检索入口
- `app/services/qa_service.py`
  - 增加 query 类型识别、上下文预算、结构化 context packing
- `data/knowledge_base/*.md`
  - 补 front matter，统一标题层次
- `data/vector_store/`
  - 存 manifest、chunk 索引和向量索引

建议新增的数据结构：

```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    file_name: str
    topic: str
    section_title: str
    text: str
    recall_score: float
    rerank_score: float
    final_score: float
```

以及：

```python
class RetrievalConfig(BaseModel):
    mode: str
    top_k_recall: int = 8
    top_k_rerank: int = 4
    token_budget: int = 900
    candidate_files_limit: int = 4
```

---

## 13. 一套适合你项目的默认参数

建议初始参数直接这样定：

```text
文件预筛数: 4
稀疏召回: top 8
稠密召回: top 8
融合后候选: 10
rerank 后保留: 4
最终送入 LLM: 2 到 3 个上下文块
QA token 预算: 900
Exercise/Eval token 预算: 600
Planner token 预算: 400
```

如果问题属于“定义型”或“区别型”，还可以进一步收紧：

- 最终只给 2 个块

---

## 14. 最终推荐结论

最适合你当前这套多智能体学伴系统的，不是重型 RAG，而是：

`知识文件加元数据 + 标题感知 chunk + 文件级预筛 + 混合召回 + 轻量 rerank + 严格上下文预算 + 按智能体分检索入口`

这套方案的优势是：

- 比当前关键词检索明显更准
- 比“全量向量搜 + 大段塞上下文”更省 token
- 和你现在的目录结构天然兼容
- 能先轻量实现，再逐步接入真正的 embedding 与 reranker

如果只做一个最值得优先落地的点，我建议先做：

`文件级预筛 + 标题感知 chunk + rerank + token_budget`

因为这四项对效果/成本比最高。

---

## 15. 当前已落地的 RAG 实现

当前项目已经按照“本地文档构建知识库 -> 文本切分和向量化索引 -> Agent 工具化检索 -> rerank -> 上下文注入”的方向完成第一版代码实现。实现重点不是引入重型 RAG 框架，而是在现有项目结构中做一套轻量、可降级、方便多智能体复用的 RAG 能力。

### 15.1 当前代码落点

本次实现涉及以下模块：

- `app/repositories/kb_repo.py`
  - RAG 的核心仓储与检索实现。
  - 负责从 `data/knowledge_base/` 读取本地 Markdown/TXT 文档。
  - 负责解析 front matter、按 Markdown 标题切分 chunk、建立 chunk 元数据。
  - 负责构建和读取本地索引文件。
  - 负责文件级预筛、sparse 召回、embedding 召回、merge 去重、rerank 和上下文打包。

- `app/tools/embedding_client.py`
  - OpenAI-compatible embedding 客户端。
  - 默认调用 `/embeddings` 接口。
  - 默认 embedding 模型为 `text-embedding-v4`。
  - 可通过环境变量 `OPENAI_EMBEDDING_MODEL` 覆盖。
  - API key 从 `OPENAI_API_KEY` 或 `DASHSCOPE_API_KEY` 读取。

- `app/tools/rag_tool.py`
  - 面向 Agent 的 RAG 工具封装。
  - 工具名为 `knowledge_rag_search`。
  - Agent 可以按需传入 `query / mode / top_k / token_budget / use_llm_rerank` 调用检索。

- `app/tools/retriever.py`
  - 保留对当前 `QAService` 的兼容入口。
  - 当前 `LocalKnowledgeRetriever` 本质上是对 `KnowledgeBaseRepository.retrieve()` 的轻量封装。

- `app/scripts/build_kb_index.py`
  - 手动构建或重建知识库索引的脚本。
  - 配置好 embedding API 后，可以运行：

```powershell
python app\scripts\build_kb_index.py
```

- `data/vector_store/`
  - 保存索引产物：
    - `kb_chunks.jsonl`
    - `kb_manifest.json`

### 15.2 当前检索链路

当前实际链路如下：

```text
本地知识文档
-> Markdown/front matter 解析
-> 标题感知 chunk 切分
-> chunk 元数据构建
-> embedding 向量化（如果可用）
-> 写入 kb_chunks.jsonl / kb_manifest.json

用户问题 / Agent 任务
-> Agent 或 QAService 调用 RAG 工具
-> 文件级预筛
-> sparse 召回
-> embedding dense 召回（如果可用）
-> merge 去重
-> 规则 rerank 预排序
-> LLM rerank 精排（如果可用）
-> 相邻片段合并与 token budget 打包
-> 返回可注入 prompt 的结构化上下文
```

### 15.3 索引结构

当前索引文件为：

```text
data/vector_store/kb_chunks.jsonl
data/vector_store/kb_manifest.json
```

`kb_chunks.jsonl` 中每条 chunk 包含：

```json
{
  "chunk_id": "stack.md#chunk_0000",
  "file_name": "stack.md",
  "section_title": "栈（Stack） > 一、栈的基本概念 > 1.1 定义",
  "text": "...",
  "topic": "stack",
  "subtopics": ["stack", "sequential_stack"],
  "aliases": ["栈", "Stack", "顺序栈"],
  "char_count": 128,
  "prev_chunk_id": null,
  "next_chunk_id": "stack.md#chunk_0001",
  "embedding": [...]
}
```

`kb_manifest.json` 记录：

- 构建时间
- chunk 数量
- chunk 大小
- embedding 模型
- embedding 是否启用
- embedding API key 是否可用
- 源文件的文件名、mtime 和 size

如果知识库源文件发生变化，索引会被判断为 stale，并在下次检索时自动重建。

### 15.4 Chunk 切分策略

当前 chunk 构建策略是：

1. 优先解析文档 front matter。
2. 按 Markdown 标题层级切分 section。
3. section 过长时，再按自然段切分。
4. 自然段仍过长时，再按固定字符长度兜底切分。
5. 为每个 chunk 记录 `prev_chunk_id` 和 `next_chunk_id`，便于后续上下文合并。

默认 `chunk_size` 为 `380` 字符，适合当前数据结构课程知识库的密度。

### 15.5 混合召回策略

当前召回由三部分组成：

1. 文件级预筛
   - 根据 query 与文件名、topic、subtopics、aliases、section_title 的匹配程度筛选候选文件。
   - 默认最多保留 4 个候选文件。

2. sparse 召回
   - 使用标题命中、正文关键词命中、正文前部关键词密度、完整短语命中等信号。
   - 默认取 sparse top 8。

3. embedding dense 召回
   - 对 query 生成 embedding。
   - 与 chunk embedding 计算余弦相似度。
   - 默认取 dense top 8。
   - 如果 embedding API 不可用，会自动降级，不影响 sparse 检索。

融合后的召回分数为：

```text
recall_score =
0.45 * sparse_score
+ 0.45 * dense_score
+ 0.10 * metadata_score
```

随后对 sparse 和 dense 的候选结果进行 merge 去重。

### 15.6 Merge 去重策略

当前保留了两层 merge：

1. 召回阶段 merge
   - 按 `chunk_id` 去重。
   - 同一个 chunk 如果同时被 sparse 和 dense 命中，会合并其 `sparse_score / dense_score / metadata_score`。
   - 避免重复 chunk 浪费 rerank 候选名额。

2. 打包阶段 merge
   - 对同一文件、同一 section 的相邻 chunk 做轻量合并。
   - 避免最终注入给 Agent 的上下文过碎。

### 15.7 Rerank 策略

当前实现包含两级 rerank。

第一层是规则 rerank：

```text
rerank_score =
0.35 * title_match
+ 0.25 * alias_match
+ 0.20 * keyword_density
+ 0.10 * same_topic_boost
+ 0.10 * question_type_boost
```

其中 `question_type_boost` 会识别：

- 定义型问题：是什么、定义、概念
- 对比型问题：区别、比较、对比
- 操作型问题：怎么、如何、实现、代码
- 复杂度型问题：时间复杂度、空间复杂度
- 例题/易错型问题：例题、练习、易错

第二层是 LLM rerank：

- 如果 `KnowledgeBaseRepository` 初始化时传入了 `llm_client`，并且 `use_llm_rerank=True`，则启用。
- LLM rerank 只面对规则预排序后的少量候选，默认最多 8 个。
- LLM 只负责根据问题对候选 chunk 排序，不负责生成答案。
- 要求 LLM 输出 JSON：

```json
{
  "ranked_chunk_ids": ["..."],
  "reason": "简短说明"
}
```

如果 LLM rerank 调用失败、API key 不存在或 JSON 解析失败，会自动降级为规则 rerank。

### 15.8 上下文打包策略

当前最终返回给 Agent/QAService 的上下文是结构化文本：

```text
[1] 文件: queue.md
SOURCE: queue.md
标题: 队列（Queue） > 一、队列的基本概念 > 1.4 队列与栈的对比
TITLE: 队列（Queue） > 一、队列的基本概念 > 1.4 队列与栈的对比
内容:
...
```

保留 `SOURCE:` 和 `TITLE:` 是为了兼容当前 `QAService._build_sources()` 的解析方式。

不同任务模式可以设置不同预算：

```text
qa: 900
exercise: 600
evaluation: 600
planner: 400
```

如果内容超过预算，会对 chunk 做截断，避免 prompt 被长上下文挤满。

### 15.9 Agent 工具化调用方式

当前可以通过 `KnowledgeRAGTool` 让 Agent 自主检索：

```python
from app.repositories.kb_repo import KnowledgeBaseRepository
from app.tools.rag_tool import KnowledgeRAGTool

kb_repo = KnowledgeBaseRepository(llm_client=llm_client)
rag_tool = KnowledgeRAGTool(
    kb_repo,
    mode="qa",
    top_k=4,
    token_budget=900,
    use_llm_rerank=True,
)

context = rag_tool("队列和栈有什么区别")
```

返回的 `context` 可以直接注入 Agent 的 system prompt 或 user prompt。

当前 `QAService` 仍通过 `LocalKnowledgeRetriever` 调用，保持兼容：

```python
LocalKnowledgeRetriever(
    kb_repo,
    mode="qa",
    top_k=4,
    token_budget=900,
    use_llm_rerank=True,
)
```

### 15.10 当前运行状态与注意事项

当前已经生成本地索引：

```text
data/vector_store/kb_chunks.jsonl
data/vector_store/kb_manifest.json
```

当前本地验证时使用的是无 API key 降级模式，因此 manifest 中可能显示：

```json
{
  "embedding_enabled": false,
  "embedding_api_key_available": false
}
```

这表示当前索引中还没有真正的 embedding 向量，系统会使用：

```text
文件预筛 + sparse 召回 + merge 去重 + 规则 rerank
```

配置好 `OPENAI_API_KEY` 或 `DASHSCOPE_API_KEY` 后，运行：

```powershell
python app\scripts\build_kb_index.py
```

即可重新构建带 embedding 的索引。之后检索链路会启用：

```text
sparse 召回 + embedding dense 召回 + merge 去重 + LLM rerank
```

### 15.11 已验证的效果样例

在无 embedding、无 LLM rerank 的降级模式下，已经完成基础冒烟验证。

例如问题：

```text
队列和栈有什么区别
```

当前可以优先命中：

```text
queue.md
队列（Queue） > 一、队列的基本概念 > 1.4 队列与栈的对比
```

这说明当前规则召回和 rerank 在没有 embedding 的情况下也具备可用性；配置 embedding 后，语义召回会进一步提升自然语言问题和同义表达的命中能力。
