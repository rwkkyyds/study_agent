---
name: "Section_6_代码模块化分割规范"
description: "指导AI生成Section_6异常处理与降级的demo代码时，将功能分散到多个文件，避免单文件超过300-400行，提高代码可读性和学习体验"
applyTo: "Week_3_Agent工具调用/Section_6_异常处理与降级"
version: "1.0"
---

# Section 6 - 异常处理与降级的代码分文件规范

## 技能目的

确保 Section_6 的所有 demo 代码遵循**模块化分割原则**，使学生能够：
- ✅ 逐个理解每个模块的职责
- ✅ 快速定位和查看相关代码
- ✅ 不被长代码文件压倒
- ✅ 清晰理解从基础→进阶→整合的学习路径

## 何时使用这个规范

**MUST USE** 当生成以下内容时：
- demo*.py 文件（演示代码）
- 超过 200 行的代码逻辑
- 包含多个独立功能模块的代码
- 学生需要分阶段理解的复杂概念

**DO NOT USE** 当：
- 生成 README.md、学习笔记等文档
- 代码确实只有 50-100 行
- 生成脚本或一次性工具代码

---

## 核心规则

### 规则1：文件大小限制（硬性）

```
✅ 推荐范围：100-250 行
✅ 允许范围：250-350 行
❌ 禁止范围：超过 400 行
```

**理由**：
- 100-250 行：可以在一个屏幕内看完，学习无压力
- 250-350 行：包含较完整的一个功能，可接受
- 超过 400 行：需要滚动，容易看完前面忘后面 ❌

### 规则2：按功能模块分割（逻辑分离）

不是按行数硬分，而是**按功能职责分割**：

#### 示例：重试策略演示

✅ **推荐的分割方式**：

```
demo2a_retry_tenacity_basics.py
├── 导入 & 日志配置
├── FlakyAPI 工具类（模拟不稳定API）
├── @retry 装饰器方式的重试
└── demo 场景1：装饰器重试基础

demo2b_retry_manual_advanced.py
├── 导入
├── 手动重试函数
├── 自定义重试逻辑
└── demo 场景2、3：手动重试 & 重试耗尽

demo2c_retry_langgraph_integration.py
├── 导入
├── LangGraph Agent 状态定义
├── Agent 节点函数（集成重试）
├── 工具定义
└── demo 场景4：Agent 集成重试
```

❌ **不推荐的方式**：

```
demo2_retry_strategy.py  ← 单文件 350+ 行，包含所有内容
```

### 规则3：文件命名约定

**格式**：`demo{编号}_{功能}_{层级}.py`

```
demo1_exception_basics.py
          ↑           ↑
       功能名      可选的层级描述

demo2a_retry_tenacity_basics.py
      ↑  ↑                  ↑
   编号 a/b/c          子功能说明

demo3_fallback_degrade.py  ← 单功能，不需要分割
```

**命名规范**：
- `demo1_`: 异常捕获基础
- `demo2a_`: 重试策略 - tenacity 装饰器版
- `demo2b_`: 重试策略 - 手动重试版
- `demo2c_`: 重试策略 - LangGraph 集成版
- `demo3_`: 降级与熔断
- `demo4_`: 综合实战（可选，如果需要整合）

### 规则4：每个文件的结构

```python
"""
demo2a_retry_tenacity_basics.py - 重试策略（tenacity装饰器）

学习目标：
1. 理解 tenacity 库的基本用法
2. 掌握指数退避的配置
3. 学会异常类型选择性重试

简要说明：
这个文件重点讲解如何用 @retry 装饰器快速实现重试，
特点是代码简洁、配置声明式。
"""

# ============================================================
# 导入和日志配置
# ============================================================

import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 1. 模拟工具类
# ============================================================

class FlakyAPI:
    """模拟不稳定的 API"""
    pass


# ============================================================
# 2. 核心业务逻辑
# ============================================================

@retry(...)
def call_api_with_retry(query: str) -> str:
    """使用 tenacity 装饰器重试"""
    pass


# ============================================================
# 3. 演示场景
# ============================================================

def demo_scenario_1():
    """演示：基础重试"""
    pass

def demo_scenario_2():
    """演示：选择性重试"""
    pass


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    print("demo2a: 重试策略（tenacity装饰器）")
    demo_scenario_1()
    demo_scenario_2()
```

### 规则5：文件之间的依赖关系

#### 模块依赖图

```
demo1_exception_basics.py
    ↓（基础异常处理）
demo2a_retry_tenacity_basics.py
    ↓（基本重试）
demo2b_retry_manual_advanced.py
    ↓（高级重试）
demo2c_retry_langgraph_integration.py
    ↓（集成到Agent）
demo3_fallback_degrade.py
    ↓（降级策略）
demo4_integration_test.py （可选：综合测试）
```

**原则**：
- 每个 demo 文件应该是**相对独立**的（不依赖其他 demo 的执行结果）
- 共享的工具类（如 `FlakyAPI`）可以重复定义，或者提取到 `utils.py`
- 不要出现 `from demo2a import FlakyAPI` 这样的文件间依赖

### 规则6：共享代码处理方案

#### 方案A：重复定义（推荐用于小工具类）

```python
# demo2a_retry_tenacity_basics.py
class FlakyAPI:
    """模拟API"""
    pass

# demo2b_retry_manual_advanced.py
class FlakyAPI:
    """模拟API（同上）"""
    pass
```

**优点**：每个文件自包含，可独立运行  
**缺点**：代码重复

#### 方案B：提取到 utils（推荐用于大工具类）

```
Section_6_异常处理与降级/
├── utils.py              ← 共享工具和类
├── demo1_exception_basics.py
├── demo2a_retry_tenacity_basics.py
├── demo2b_retry_manual_advanced.py
├── demo2c_retry_langgraph_integration.py
├── demo3_fallback_degrade.py
└── README.md
```

**utils.py 内容**：
```python
"""
utils.py - Section_6 共享工具和工具类
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FlakyAPI:
    """
    模拟一个不稳定的 API
    
    这个类在多个 demo 中使用，提取出来避免重复
    """
    def __init__(self, fail_count: int = 2):
        self.fail_count = fail_count
        self.call_count = 0
    
    def call(self, query: str) -> str:
        self.call_count += 1
        if self.call_count <= self.fail_count:
            raise ConnectionError(f"API 暂时不可用（模拟故障 {self.call_count}/{self.fail_count}）")
        return f"结果: {query}"


class CircuitBreaker:
    """熔断器实现"""
    pass
```

**各 demo 文件中导入**：
```python
# demo2a_retry_tenacity_basics.py
from utils import FlakyAPI

# demo2b_retry_manual_advanced.py
from utils import FlakyAPI

# demo2c_retry_langgraph_integration.py
from utils import FlakyAPI
```

**方案选择**：
- 工具类 < 50 行 → 用方案A（重复定义）
- 工具类 ≥ 50 行 → 用方案B（提取到 utils）

---

## 实际例子：Section_6 的理想结构

### 当前结构（不符合规范）

```
demo1_exception_basics.py         ← ~150 行 ✅ 合理
demo2_retry_strategy.py            ← ~350 行 ⚠️ 边界，可以分割
demo3_fallback_degrade.py          ← ~200 行 ✅ 合理
```

### 建议的改进方案

```
demo1_exception_basics.py
    ├─ 异常捕获基础
    ├─ Try-except 模式
    ├─ 自定义异常
    └─ ~150 行 ✅

demo2a_retry_tenacity_basics.py
    ├─ FlakyAPI 工具
    ├─ @retry 装饰器方式
    ├─ 场景1：装饰器基础
    └─ ~150 行 ✅

demo2b_retry_manual_advanced.py
    ├─ 手动重试函数
    ├─ 场景2、3：手动重试与耗尽
    ├─ 对比分析
    └─ ~150 行 ✅

demo2c_retry_langgraph_integration.py
    ├─ LangGraph Agent 定义
    ├─ 重试集成节点
    ├─ 场景4：Agent 重试
    └─ ~150 行 ✅

demo3_fallback_degrade.py
    ├─ 降级策略
    ├─ 熔断器
    ├─ 多种演示
    └─ ~200 行 ✅
```

---

## 生成代码的检查清单

每次生成 demo 代码时，请确保：

### 步骤1：规划阶段
- [ ] 确认是否需要分文件（总代码 > 200 行？）
- [ ] 列出所有功能模块
- [ ] 绘制功能依赖图
- [ ] 确定每个文件的职责

### 步骤2：分割阶段
- [ ] 每个文件 100-250 行（硬性限制 400 行）
- [ ] 文件名遵循 `demo{编号}_{功能}_{层级}.py` 格式
- [ ] 按学习递进顺序命名（a → b → c）

### 步骤3：实现阶段
- [ ] 每个文件有清晰的模块说明（Docstring）
- [ ] 共享代码提取到 utils.py（如果有）
- [ ] 每个文件可独立运行（if __name__ == "__main__"）
- [ ] 导入语句清晰，无循环依赖

### 步骤4：验证阶段
- [ ] 每个文件都能独立运行 `python demo2a_*.py`
- [ ] 输出说明清晰，学生能看懂
- [ ] 代码行数符合规范（< 400 行）
- [ ] 文件数合理（3-5 个 demo，不要超过 8 个）

---

## 总结：为什么这样做

| 问题 | 解决方案 | 效果 |
|------|--------|------|
| 代码文件太长 | 按功能分割 | 每个文件 150-200 行，可以一屏看完 |
| 看完前面忘后面 | 模块化设计 | 每个模块职责明确，易于理解 |
| 重复代码 | utils.py 集中 | 共享代码在一个地方，易于维护 |
| 学习路径不清晰 | 按递进顺序命名 | demo2a → demo2b → demo2c，递进明确 |
| 文件间有依赖 | 相对独立的设计 | 每个 demo 可以单独运行学习 |

---

## 快速参考

```
📋 规则速记：
1. 文件大小：100-250 行（最多 350 行）
2. 命名格式：demo{号}_{功能}_{层级}.py
3. 分割标准：按功能职责，不是按行数
4. 共享代码：提取到 utils.py（可选）
5. 递进顺序：a/b/c 表示从基础到高级
6. 独立运行：每个 demo 可单独执行

⏱️ 生成时间：会增加 10-15%，但学生体验提升 50%+
```
