# Learning Assistant

一个面向《数据结构》课程的智能学伴后端项目，当前提供：

- 基于本地知识库的 RAG 问答
- 基于 LLM 的习题生成
- 基于 LLM 的简答题评估
- 学生画像更新与学习计划生成
- FastAPI 接口

## 项目结构

```text
learning_assistant/
├─ app/
│  ├─ main.py
│  ├─ routes.py
│  ├─ orchestrator.py
│  ├─ models/
│  ├─ repositories/
│  ├─ services/
│  └─ tools/
├─ data/
│  ├─ knowledge_base/
│  ├─ profiles/
│  ├─ question_bank/
│  └─ vector_store/
├─ idea.md
└─ README.md
```

## 环境要求

- Python 3.11+

建议安装依赖：

```powershell
pip install fastapi uvicorn pydantic
```

## 环境变量配置

LLM 使用 DashScope 的 OpenAI 兼容接口。请先配置环境变量。

### PowerShell

当前终端临时生效：

```powershell
$env:OPENAI_API_KEY="你的API Key"
$env:OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:OPENAI_MODEL="qwen-plus-2025-07-28"
```

也可以使用：

```powershell
$env:DASHSCOPE_API_KEY="你的API Key"
```

说明：

- `OPENAI_API_KEY` 与 `DASHSCOPE_API_KEY` 二选一即可
- `OPENAI_BASE_URL` 默认就是 DashScope 兼容地址，不配也能运行
- `OPENAI_MODEL` 默认是 `qwen-plus-2025-07-28`

## 启动方式

在项目根目录执行：

```powershell
uvicorn app.main:app --reload
```

启动后默认访问：

- `http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`

## 数据准备

### 1. 知识库

放在 `data/knowledge_base/`，支持：

- `.md`
- `.txt`

建议一份文件对应一个主题，例如：

- `stack.md`
- `queue.md`
- `binary_tree.md`

### 2. 题库

放在 `data/question_bank/`，每个文件建议按知识点拆分，例如：

- `stack.json`
- `queue.json`
- `binary_tree.json`

题目格式示例：

```json
[
  {
    "question_id": "stack_choice_001",
    "knowledge_point": "栈",
    "question_type": "choice",
    "difficulty": "easy",
    "question": "以下哪种数据结构最符合后进先出（LIFO）的特征？",
    "options": ["栈", "队列", "链表", "图"],
    "answer": "A",
    "analysis": "栈的典型特征是后进先出。"
  }
]
```

说明：

- `question_type` 支持 `choice` 和 `short_answer`
- 简答题的 `options` 写 `null`

## 主要接口

### 1. 初始化学生画像

`POST /profile/init`

请求体：

```json
{
  "student_id": "stu_001",
  "target": "期末达到85分",
  "available_time": "每天1小时"
}
```

### 2. 问答

`POST /chat`

请求体：

```json
{
  "student_id": "stu_001",
  "message": "什么是栈，它和队列有什么区别？"
}
```

### 3. 生成练习题

`POST /exercise/generate`

请求体：

```json
{
  "student_id": "stu_001",
  "knowledge_point": "二叉树",
  "question_type": "short_answer",
  "difficulty": "medium",
  "count": 1
}
```

### 4. 评估答案

`POST /exercise/evaluate`

请求体：

```json
{
  "student_id": "stu_001",
  "question_id": "generated_xxxxxxxx",
  "student_answer": "中序遍历是左根右。"
}
```

### 5. 生成学习计划

`POST /plan/generate`

请求体：

```json
{
  "student_id": "stu_001",
  "duration": "3天"
}
```

## 当前实现说明

- 问答、出题、简答评估、画像更新、学习计划已接入 LLM
- RAG 当前使用本地知识库检索，不依赖向量库
- `data/profiles/` 会自动保存学生画像
- 生成题目会写入 `data/question_bank/_generated_questions.json`

## 常见问题

### 1. 提示缺少 API key

请确认已经配置：

- `OPENAI_API_KEY`

或：

- `DASHSCOPE_API_KEY`

### 2. 启动成功但问答没有命中文档

请检查：

- 知识库文件是否在 `data/knowledge_base/`
- 文件是否为 UTF-8 编码
- 问题是否包含明确知识点，如“栈”“队列”“二叉树”

### 3. 评估或出题报 LLM 超时

这通常是外部接口响应较慢，可以重试一次；当前客户端已设置较宽的请求超时。
