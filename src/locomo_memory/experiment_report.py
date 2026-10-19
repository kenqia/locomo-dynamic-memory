"""A short experiment report whose complete evidence remains in JSON artifacts."""
import json


def render_report(state, scope, run=None):
    lines = [f'# 开发集实验记录：{scope}', '',
             f"生成时间：{state['updated_at']}。实际状态：`{state.get('status', 'unknown')}`。", '',
             '开发集为 conv-26、conv-30、conv-41、conv-42。本地测试 conv-43、conv-44 未运行；本地结果不代表教师隐藏评分。动态准确率未评，缺少独立动态标签。', '']
    if not run:
        lines += ['模型评测未启动。计划预览及受控检查不代表真实评测完成。', '',
                  '当前阻塞：' + '、'.join(state.get('blockers', [])), '']
        return '\n'.join(lines)
    lines += [f"Run `{run['run_id']}`，状态 `{run['status']}`。", '',
              f"计划与执行数量：`{json.dumps(run['progress'], ensure_ascii=False)}`。", '',
              '完整逐项结果、全部尝试、Prompt/schema、配置、版本身份和原始 Trace 保存在同目录的 Run JSON。', '']
    lines += ['## 策略结果', '', '| 策略 | 成功 / 计划 | 成功 QA 均值 / 可计分数 | 基线运行得分 / 分母 | 未计分数 |', '| --- | --- | --- | --- | --- |']
    for strategy, group in run.get('summary', {}).items():
        execution, qa, score = group.get('execution', {}), group.get('qa', {}), group.get('baseline_run_score', {})
        lines.append(f"| {strategy} | {execution.get('succeeded')} / {execution.get('planned')} | {qa.get('mean')} / {qa.get('scored')} | {score.get('value')} / {score.get('denominator')} ({score.get('status')}) | {score.get('excluded')} |")
    lines += ['', '按对话、类别及不同分母的完整统计保存在 `grouped-summary.json`。未完成运行的基线运行得分保持未完成，不能将待执行项提前判零。', '',
              '## 开销', '', '构建与查询分别统计；provider 未报告用量与结果未知调用不视为零。完整全文与 RAG 的上下文量分别保留；Vector 的额外问题分析和 BM25 开销保留在 Trace。', '',
              '构建：`' + json.dumps(run.get('build_usage_summary', {}), ensure_ascii=False) + '`', '',
              '查询与所有保留尝试：`' + json.dumps(run.get('usage_summary', {}), ensure_ascii=False) + '`', '',
              '## 失败检查', '', '失败项与完整证据保存在 `failure-cases.json` 和逐项 Run 记录。来源命中不能单独证明语义事实正确；自动记录的根因为未确定，须结合来源、Memory、召回、扩展、有效证据与引用独立复核。', '',
              '已提交成功项在显式恢复时跳过；失败和未知项仅经显式选择重试。外部模型已计费但结果尚未提交的窗口可能重复计费，不承诺跨 provider 恰好一次调用。', '']
    return '\n'.join(lines)
