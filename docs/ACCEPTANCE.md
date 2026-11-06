# 手工验收路径

1. 按README安装，`scm init`后Live Overview应为0；不得用Demo补足Live数据。
2. `scm demo`连续执行两次；预期第一次5条事件+3条快照，第二次全部unchanged（若旧版本内容模型变化，首次可能更新）；事件来源example.invalid并明确演示。
3. 页面切Demo，Overview应5条事件；Intelligence查看原文依据与规则、用国家/日期/风险筛选，确认/驳回/备注保存审计；更新后需重新审核。
4. Port Monitor逐一选三个港口，显示各自事件；等待数据应“数据暂不可用”。填写调整人/原因/有效期后保存，Sources可查看审计。
5. Shipment Monitor查看DEMO-0001两快照：11月20日到11月23日，+72h为高；DEMO-0002只有一快照为未知。关联必须显示待核实，不是甩柜判定。
6. Reports在2026-11-06生成Demo日报/周报，查看中文模板、原文引用、来源、条件影响和质量声明。Live空报告明确无重要新增。
7. Sources执行Live采集，来源失败应有独立日志，页面仍可用。网络阻断不能记为成功。运行 `scm audit` 更新真实报告。
8. `pytest -q`和`ruff check src tests`；Streamlit健康接口200及六页面AppTest均通过才可报告相应PASS。

本次自动测试结果见TEST_REPORT；这些操作路径不意味着全部人工浏览器点击已实际执行。
