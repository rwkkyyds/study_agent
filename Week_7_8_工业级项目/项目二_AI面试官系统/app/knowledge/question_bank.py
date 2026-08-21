"""阶段五本地岗位题库。

当前用结构化 Python 数据模拟后续向量库/RAG 检索结果。题库条目保留
skill、difficulty、keywords、expected_points 等字段，方便服务层做可测试检索。
"""

QUESTION_BANK = [
    {
        "id": "qb-rag-mid-001",
        "skill": "RAG",
        "difficulty": "mid",
        "question_type": "rag",
        "question": "你的 RAG 系统如何设计 chunk、embedding、top_k 和引用来源，以减少幻觉？",
        "expected_points": ["chunk 策略", "embedding 模型", "top_k", "引用来源", "幻觉评估"],
        "keywords": ["RAG", "向量", "知识库", "Milvus", "Embedding"],
        "source": "岗位题库 RAG",
    },
    {
        "id": "qb-rag-senior-001",
        "skill": "RAG",
        "difficulty": "senior",
        "question_type": "rag",
        "question": "如果 RAG 召回结果相关性波动，你会如何设计离线评估集、线上指标和回滚策略？",
        "expected_points": ["评估集", "召回率", "命中率", "线上监控", "回滚策略"],
        "keywords": ["RAG", "评估", "召回", "监控", "回滚"],
        "source": "岗位题库 RAG",
    },
    {
        "id": "qb-agent-mid-001",
        "skill": "Agent",
        "difficulty": "mid",
        "question_type": "agent",
        "question": "你的 Agent 工作流如何做状态管理、条件路由和工具调用失败重试？",
        "expected_points": ["状态对象", "条件路由", "工具抽象", "失败重试", "人工兜底"],
        "keywords": ["Agent", "LangGraph", "工具调用", "状态", "路由"],
        "source": "岗位题库 Agent",
    },
    {
        "id": "qb-backend-mid-001",
        "skill": "Backend",
        "difficulty": "mid",
        "question_type": "backend",
        "question": "请说明你如何设计 FastAPI 服务的认证、数据库 Session、异常处理和测试隔离。",
        "expected_points": ["JWT", "Session", "依赖注入", "异常码", "测试数据库"],
        "keywords": ["FastAPI", "后端", "JWT", "SQLAlchemy", "测试"],
        "source": "岗位题库 后端",
    },
    {
        "id": "qb-deploy-mid-001",
        "skill": "Deployment",
        "difficulty": "mid",
        "question_type": "deployment",
        "question": "你如何用 Docker Compose 编排 API、数据库、缓存和向量库，并设计健康检查？",
        "expected_points": ["服务拆分", "环境变量", "健康检查", "网络", "数据卷"],
        "keywords": ["Docker", "Compose", "部署", "健康检查", "数据卷"],
        "source": "岗位题库 部署",
    },
    {
        "id": "qb-system-senior-001",
        "skill": "System Design",
        "difficulty": "senior",
        "question_type": "system_design",
        "question": "如果 AI 面试系统需要支持 10 倍并发，你会如何拆分服务、缓存热点并保护数据库？",
        "expected_points": ["服务拆分", "缓存", "限流", "队列", "数据库保护"],
        "keywords": ["系统设计", "并发", "缓存", "数据库", "队列"],
        "source": "岗位题库 系统设计",
    },
    {
        "id": "qb-frontend-junior-001",
        "skill": "Frontend",
        "difficulty": "junior",
        "question_type": "frontend",
        "question": "如果前端要展示一场模拟面试，你会如何组织题目、回答、追问和报告状态？",
        "expected_points": ["页面状态", "接口调用", "加载态", "错误处理", "报告展示"],
        "keywords": ["前端", "React", "状态管理", "接口", "报告"],
        "source": "岗位题库 前端",
    },
]

