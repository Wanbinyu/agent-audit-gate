# 快速开始（中文）

## 安装

```bash
# 本地目录
python -m pip install -e "G:\skill\agent-audit-gate"

# 或 pipx（适合日常）
pipx install G:\skill\agent-audit-gate
```

确认：

```bash
audit-gate --version
```

## 三种用法

### 1. 改模板再检查（最适合人工 / 重要任务）

```bash
cd 你的项目目录
audit-gate init run.trajectory.json
# 编辑 tools：真实读写与测试命令结果
audit-gate check run.trajectory.json --pretty
```

### 2. 用工具事件 JSONL（适合脚本导出）

`tools.jsonl` 每行一个工具：

```json
{"name": "edit_file", "ok": true, "path": "src/foo.py"}
{"name": "run_command", "command": ["python", "-m", "pytest", "-q"], "exit_code": 0}
```

```bash
audit-gate from-events tools.jsonl --claimed completed --pretty
```

`pytest` / `npm test` 等会自动记为验证命令（与 cc-usage-gate 插件同一套识别）；失败的验证会直接 `blocked`。`npm run build` / `lint` 不算验证。

未声称 `completed` 时，有写入但还没跑绿灯测试 → `partial`（退出码 2）。声称做完却没测 → `blocked`。

### 4. 回放 Claude Code 会话（推荐）

先装 [`cc-usage-gate`](../../cc-usage-gate)，正常用 Claude Code。然后：

```bash
audit-gate from-session --pretty
```

### 3. 管道 / CI

```bash
audit-gate check run.trajectory.json --quiet
# 退出码 3 = blocked，可用来卡 CI
```

## 怎么理解结果

| status | 含义 | 退出码 |
|--------|------|--------|
| completed | 证据足够，可算完成 | 0 |
| partial | 有写入但还没绿灯测试，且未声称 completed | 2 |
| blocked | 缺证据 / 验证失败 / 假完成声明 | 3 |

**模型说「测过了」不算数**；需要 `verification` 工具成功（或 from-events 自动识别的测试命令且 exit 0）。

## 和 Claude Code 一起用

本工具不劫持 Claude Code。推荐：

1. 重要改动后，把本轮「改了啥 + 跑了啥命令 + 退出码」写进 `run.trajectory.json` 或 JSONL；
2. 跑 `audit-gate check` / `from-events`；
3. 若 `blocked`，先补验证或修测试，再让 Agent 继续。

以后可为具体产品加日志适配器；核心规则保持稳定。

## 下一步

- `audit-gate rules` — 看规则全文  
- `audit-gate schema` — 轨迹 JSON Schema  
- 仓库 [README.md](../README.md) — 完整说明与 CI 示例  
