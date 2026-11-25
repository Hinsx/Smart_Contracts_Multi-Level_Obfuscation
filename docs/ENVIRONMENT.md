# 环境搭建与验证记录（Phase 0）

记录日期：2026-11-25。宿主机：VirtualBox Ubuntu 24.04.3 LTS（`hin@192.168.56.101`）。
本文件说明"怎么从零复现这套工具链""实际装了什么版本""踩过哪些坑"，供 Phase 1 起直接对照使用。

## 1. 为什么不用系统 Python

系统自带 **Python 3.12.3**，而计划书硬性要求 **3.10 / 3.11**（保证 `web3[tester]` 底层加密扩展
有预编译 wheel）。该机器**没有免密 sudo**，因此采用 `uv` 安装**独立 CPython 3.11** 的方案：
不修改、不替换系统 Python，也不影响系统包管理。

## 2. 安装位置

| 组件 | 位置 |
| --- | --- |
| `uv` 可执行文件 | `~/.local/bin/uv`（0.13.10） |
| 独立 CPython 3.11 | `~/.local/share/uv/python/`（3.11.18，约 96 MB） |
| 项目虚拟环境 | `<repo>/.venv`（约 299 MB，已被 `.gitignore` 排除） |
| solc 0.8.20 | `~/.solcx/solc-v0.8.20`（由 py-solc-x 下载） |
| 仓库 | `~/project/hkust/Smart_Contracts_Multi-Level_Obfuscation` |

## 3. 复现步骤（全程无需 sudo）

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv python install 3.11

cd ~/project/hkust/Smart_Contracts_Multi-Level_Obfuscation
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

日常使用：`source .venv/bin/activate`，或显式调用 `.venv/bin/python`。
`.python-version` 已固定为 `3.11`，`uv` 会据此选择解释器。

## 4. 实际解析版本（2026-11-25）

| 包 | 版本 |
| --- | --- |
| Python | 3.11.18（uv 独立构建） |
| uv | 0.13.10 |
| solc | 0.8.20+commit.a1b79de6.Linux.g++ |
| py-solc-x | 2.1.0 |
| web3 | 8.0.0 |
| py-evm | 0.12.1b1 |
| eth-tester | 0.14.0b1 |
| slither-analyzer | 0.10.3 |
| solc-select | 1.2.0 |
| pytest | 9.2.0 |
| pandas | 3.1.1 |
| matplotlib | 3.11.2 |
| numpy | 2.4.6 |

`requirements.txt` 按计划书保留版本下限（`web3[tester]>=6.15.0` 等），实际解析到较新的
web3 8.0.0、pytest 9.2.0。若 Phase 1 发现 web3 8 / eth-tester beta 与计划书的 API 假设冲突，
可在 `requirements.txt` 中收紧为精确版本（例如 `web3[tester]==6.20.4`）后重装，并在本文件记录变更。

## 5. Phase 0 冒烟验证结果

用一个临时 `Storage` 合约（`set` / `get` + 事件，未提交进仓库）验证整条链路：

| 检查项 | 结果 |
| --- | --- |
| solc 0.8.20 下载与编译 | 通过，optimizer 开 / 关均可编译 |
| AST 获取 | 通过，`Storage` 共 35 个 AST 节点 |
| opcode 提取 | 通过，353 个 opcode、103 种不同指令 |
| py-evm 本地部署 | 通过，部署 150,535 gas，`set()` 43,733 gas，状态读回正确 |
| Slither CFG 统计 | 通过，`set` 5 节点 / 5 边，`get` 2 节点 / 1 边 |

结论：编译 → AST → 字节码/opcode → 本地链部署与 Gas 采集 → Slither CFG，全链路可用。

## 6. 踩坑与结论（Phase 1 起直接参考）

1. **`get_executable` 不在顶层**：py-solc-x 2.1.0 移除了顶层导出，必须
   `from solcx.install import get_executable`。计划书里写的 `solcx.get_executable("0.8.20")`
   在 2.1.0 上会 `ImportError`。
2. **AST 位置**：solc 0.8.20 的 standard-json 输出里，AST 在
   `out["sources"]["X.sol"]["ast"]`，**不在**顶层 `out["ast"]`；
   `outputSelection` 必须写成 `{"*": {"": ["ast"], "*": [...]}}`，否则 solc 直接报
   `"settings.outputSelection." must be an object`。
3. **Slither 0.10.3 没有 `Function.cfg`**：`contract.functions` 返回 `FunctionContract`，
   统计 CFG 用 `len(fn.nodes)` 与 `sum(len(n.sons) for n in fn.nodes)`；
   另注意 Slither 目标是**单文件路径**时构造函数需跳过。
4. **web3 8.0.0 + eth-tester 0.14.0b1**：`EthereumTesterProvider()` 无参构造可用，
   `w3.eth.accounts` 默认 10 个账户，`wait_for_transaction_receipt` 正常返回 `gasUsed`。
5. **无 `curl`、无免密 sudo**：下载一律用 `wget`；需要 root 的操作必须先问过用户。
6. **Windows → VM 的 SSH 引号问题**：PowerShell + OpenSSH 会重组参数、吞掉内层双引号，
   复杂的远端命令不要写在 `ssh host '...'` 里，而是写成 `.sh` 文件 `scp` 上去再 `bash /tmp/x.sh`。
7. **体积**：`.venv` 约 299 MB、`~/.local/share/uv` 约 96 MB，均不进入版本库；
   `.gitignore` 已覆盖 `.venv/` 与 `.solcx/`。

## 7. 后续待定

- 是否把依赖从"下限"改为"精确锁定"（会影响跨机器可复现性）。
- 是否在 CI 中复跑本文件的冒烟流程（当前为手工执行）。
