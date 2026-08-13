# 快速开始（中文）

## 安装

```bash
pipx install git+https://github.com/Wanbinyu/agent-audit-gate.git@v0.3.2
audit-gate --version
```

## 使用

```bash
audit-gate demo
audit-gate init run.trajectory.json
# 编辑 tools：真实读写与测试命令结果
audit-gate check run.trajectory.json --pretty
```

`demo` 不需要克隆仓库，安装后即可跑通内置例子。

### 工具事件 JSONL

`tools.jsonl` 每行一个工具：

```json
{"name": "edit_file", "ok": true, "path": "src/foo.py"}
{"name": "run_command", "command": ["python", "-m", "pytest", "-q"], "exit_code": 0}
```

```bash
audit-gate from-events tools.jsonl --claimed completed --pretty
```

`pytest` / `npm test` 等会自动记为验证命令；`npm run build` / `lint` 不算。

未声称 `completed` 时，有写入但还没绿灯测试 → `partial`（退出码 2）。声称做完却没测 → `blocked`。

### 管道 / CI

```bash
audit-gate check run.trajectory.json --quiet
# 退出码 3 = blocked
```

若本机已有 `.claude/usage-gate/*.events.jsonl`：

```bash
audit-gate from-session --pretty
```

## 怎么理解结果

| status | 含义 | 退出码 |
|--------|------|--------|
| completed | 证据足够 | 0 |
| partial | 缺验证且未声称 completed | 2 |
| blocked | 缺证据 / 验证失败 / 假完成声明 | 3 |

**模型说「测过了」不算数。**

## 下一步

- `audit-gate rules` — 规则全文
- `audit-gate schema` — 轨迹 JSON Schema
- 仓库 [README.md](../README.md)
