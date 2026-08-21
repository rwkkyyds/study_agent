"""面试工作流兼容入口。

阶段四开始，实际实现位于 `app/workflow/interview_graph.py`。
保留本文件是为了让 service 层和旧文档路径继续稳定。
"""

from app.workflow.interview_graph import InterviewWorkflow, ResumeSignal

__all__ = ["InterviewWorkflow", "ResumeSignal"]
