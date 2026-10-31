# Ralph loop with Bob-Shell

Ralph loop 本质是 `while true; do cat PROMPT.md | agent; done`：每轮启动一个全新的非交互 session，用同一份 prompt 驱动，上下文不跨轮保留，进度只通过工作区（文件、git、进度文件）传递。

Bob-Shell 的非交互模式（`bob -p`）可直接实现。

## 文件

- [`ralph.sh`](./ralph.sh)：循环脚本（bash）
- [`ralph.ps1`](./ralph.ps1)：循环脚本（PowerShell）
- [`PROMPT.md`](./PROMPT.md)：每轮使用的 prompt 模板

## 使用

```bash
cd <your-project>
cp <this-dir>/PROMPT.md .   # 按需修改任务描述
bash <this-dir>/ralph.sh -n 20
```

参数：

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `-p` | prompt 文件 | `PROMPT.md` |
| `-n` | 最大迭代次数 | `20` |
| `-m` | `--chat-mode`（如 `code`） | 不指定 |
| `-s` | 每轮间隔秒数 | `2` |

PowerShell：

```powershell
.\ralph.ps1 -MaxIterations 20 -PromptFile PROMPT.md -ChatMode code
```

参数名对应：`-PromptFile`、`-MaxIterations`、`-ChatMode`、`-SleepSeconds`。

每轮日志保存在 `.ralph/logs/iteration-NNN.log`。

## 机制

- 每轮执行 `bob -p "$(cat PROMPT.md)" --yolo --hide-intermediary-output`。
- 非交互模式默认只允许非破坏性工具，`--yolo` 才能写文件；写入范围仅限启动目录。
- 退出条件：输出中出现单独一行 `<promise>COMPLETE</promise>`，或达到最大迭代次数（退出码 1）。
- 首次使用需先接受 license：`bob --accept-license -p "hi"`。

## 注意
- `--yolo` 自动批准所有工具调用，应在独立分支 / 容器 / 可回滚的仓库中运行，并始终设置 `-n` 上限。

