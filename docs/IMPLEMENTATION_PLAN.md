# Solidity 多级代码混淆器（SolObfuscator）技术实施计划

本文件是本仓库的工程规格摘要（源自课程项目技术实施计划书），作为后续按 Phase 下达编码指令时的
唯一对照文本。核心原则：**测试先行、接口解耦、逐级验证、100% 原创代码、跨平台兼容、结果完全可复现**。

## 1. 总体验收标准（Definition of Done）

| 验收维度 | 验收标准 | 验证方式 |
| --- | --- | --- |
| 编译通过率 | 4 个基准合约 × 4 个版本（Original / L1 / L2 / L3）共 16 份，在 solc 0.8.20（开/关 optimizer）下 100% 编译通过 | CLI 批量日志 + solc 校验 |
| 功能等价性 | 16 份合约在同一套参数化 pytest 中 100% Pass，外部函数 ABI 签名无变化 | `pytest tests/ -v` |
| 可复现性 | 相同 `--seed` 多次运行输出字节级一致（Windows / Linux 一致） | 对比两次输出文件哈希 |
| 抗优化有效性 | 开启 `--optimize` 后 L3 不透明谓词与死分支不被全部消除（CFG 复杂度显著留存） | 对比 optimize False/True 的 Slither CFG 指标 |
| 体积合规性 | 所有混淆后合约 Runtime Bytecode < 24,576 bytes | 评测 CSV 检查 |
| 评测与图表 | 一键输出 4 维度 CSV 总表 + 4 张 300 DPI PNG | 检查 `eval/output/` |

## 2. 环境与跨平台规约

- 操作系统：Linux（Ubuntu 虚拟机）优先；Windows / WSL2 需遵守下列规约。
- Python：**3.10 或 3.11**（禁止 3.12/3.13，以保证 `web3[tester]` 加密扩展有预编译 wheel）。
- 编译器：全局锁定 **solc 0.8.20**，通过 `solcx.install_solc("0.8.20")` 安装。
- 依赖清单见根目录 `requirements.txt`；全流程纯 Python，禁止引入 Node.js / Hardhat。
- 显式绑定 solc 路径：调用 Slither 时必须传 `solc=str(solcx.get_executable("0.8.20"))`，
  严禁依赖系统 `PATH`。
- 路径统一使用 `pathlib.Path`，禁止硬编码 `/` 或 `\` 拼接。
- 终端与图表输出**强制纯英文 ASCII**，避免 Windows GBK 终端 `UnicodeEncodeError` 与中文字体缺失。
- 单元测试只用 `EthereumTesterProvider`（py-evm）本地沙盒，不依赖外网 RPC 或外部节点进程。

> 已知环境风险（待确认）：当前 Ubuntu 24.04 虚拟机自带的 Python 为 3.12.3，与上述 3.10/3.11 的
> 硬性要求冲突。进入 Phase 1 之前需要先准备 3.11 解释器（deadsnakes / uv / pyenv 任一方案），
> 并验证 `web3[tester]`、`slither-analyzer` 在该解释器下可安装、可运行。

## 3. 引擎五大设计铁律（`obf/engine.py`）

1. **统一 Pass 接口**——每个 Pass 实现纯函数：

   ```python
   def get_patches(
       source_bytes: bytes,
       ast: dict,
       rng: random.Random,
       **kwargs
   ) -> list[tuple[int, int, bytes]]:
       ...
   ```

   返回 `(start_byte, end_byte, replacement_bytes)` 列表。

2. **强制 LF 归一化**——读入后立即
   `source_str.replace("\r\n", "\n").replace("\r", "\n")`，再 `encode("utf-8")`；
   喂给 solc 的字符串与喂给补丁引擎的字节必须同源；写文件统一
   `open(path, "w", encoding="utf-8", newline="\n")`。

3. **全程 UTF-8 字节切片**——AST 节点 `src = "start:length:file_id"` 的偏移单位是 UTF-8 字节，
   不是字符数；含非 ASCII 注释时尤其不能按字符索引。

4. **冲突检测 + 降序逆序替换**——`apply_patches` 先按 start 排序并检测区间重叠
   （嵌套/重叠时保留外层或跳过并打印警告），再按 start 从大到小降序替换，
   保证靠前节点偏移不变。

5. **逐 Pass 重编译刷新 AST**——流水线每应用完一个 Pass 立即重新编译：既实时验证语法/类型正确，
   又拿到最新 AST 与字节坐标，彻底杜绝坐标漂移。

## 4. 分阶段任务

### Phase 1：基准合约与自动化测试靶子（测试先行）

- 目标文件：`requirements.txt`、`contracts/*.sol`、`obf/compiler.py`、`tests/conftest.py`、
  `tests/test_equivalence.py`。
- 4 个单文件、零外部 import、LF 换行、`pragma solidity ^0.8.20;` 的合约：
  - `Counter.sol`：自增、自减、重置、带权限检查的 setter（冒烟测试）。
  - `SimpleERC20.sol`：余额映射、授权、`transfer` / `approve` / `transferFrom`、手续费或阈值常量。
  - `SimpleAuction.sol`：出价、最高价更新、退款提取、结束拍卖等多分支状态机。
  - `EscrowVault.sol`：买家 / 卖家 / 仲裁者三方托管、确认放款、争议退款。
- `obf/compiler.py`：`compile_source(source_str, optimize=False)`，内部先做换行归一化，
  经 `solcx.compile_standard` 一次性返回 `abi`、`bytecode`、`deployed_bytecode`、`opcodes`、`ast`；
  另提供 `get_solc_executable()` 供 Slither 复用。
- 参数化 pytest：可用命令行选项或环境变量切换合约目录（原始 / L1 / L2 / L3），
  每个合约 ≥ 5~8 个用例（正常状态变更断言 + revert 边界）。
- 夹具自动记录部署 Gas、核心函数调用 Gas、Runtime Bytecode 字节数。
- **验收**：`pytest tests/ -v`，4 个原始合约全部编译且 100% Pass。

### Phase 2：核心补丁引擎与 AST 工具（`obf/engine.py`）

- `normalize_source(source_str) -> tuple[str, bytes]`；
- `parse_src("start:length:file_id") -> (start, start + length)`；
- `walk_ast(node, callback)` 递归遍历，支持回传 `ancestors` 祖先路径；
- `apply_patches(source_bytes, patches)`，内置重叠检测与降序替换；
- `run_pipeline(source_str, level, seed, max_injections=3)`，逐 Pass 重编译校验 + 结构化统计日志
  （每个 Pass 修改了多少处节点）。
- **验收**：对含 CRLF 与非 ASCII 注释的 `Counter.sol` 跑空 Pass 与简单替换可正常输出并编译；
  人为构造重叠补丁能被正确拦截。

### Phase 3：三级混淆 Pass（做完一级验收一级）

**3A. Level 1 布局混淆（`obf/passes/layout.py`）**

- 去注释与空白压缩：词法优先级正则，优先原样保留双引号/单引号字符串字面量，再匹配 `//...`
  与 `/*...*/`；保留 SPDX 标识或按需清理；压缩多余空行。
- ABI 安全重命名：仅收集 `private` / `internal` 函数、函数体内部局部变量与参数；
  严格白名单不重命名：`public`/`external` 函数、合约级状态变量、event、modifier、
  struct/enum 成员、constructor/receive/fallback、内置全局标识符（`msg`/`block`/`tx`/`abi` 等）。
- 坐标定位：声明处用 `nameLocation`（solc 0.8+ 原生，精确指向名字本身，**不要**用覆盖整条语句的
  `src`）；引用处用 `referencedDeclaration == target_id` 匹配 `Identifier` 节点的 `src`。
- 命名规则：`rng` 生成无语义十六进制名（如 `_0x1a2b`），确保不与已有符号冲突。
- **验收**：4 个合约跑完 L1，ABI 与原版完全一致，pytest 100% Pass。

**3B. Level 2 数据混淆（`obf/passes/data.py`）**

- 整数 XOR 拆分：筛选 `nodeType == "Literal"` 且 `kind == "number"` 的非负整数；
  通过 `ancestors` 跳过 `PragmaDirective`、定长数组声明、极小整型上下文（uint8/uint16 声明或
  显式小类型转换，避免 `uint256(...)` 在 0.8+ 触发隐式转换报错）、超大数值；
  随机掩码 `R`（1~100000），替换为 `(uint256(N ^ R) ^ uint256(R))`。
- 布尔等价替换：`true` → 等价位运算或运行时恒真表达式（`pure` 函数内只能用纯算术/位运算）；
  `false` → 反向等价表达式。
- **验收**：L1+L2 后 4 份合约编译通过且 pytest 100% Pass。

**3C. Level 3 控制流混淆（`obf/passes/control.py`）**

- 抗编译器优化谓词模板库（≥ 5 组，依赖链上运行时状态）：
  恒真如 `((block.timestamp & 1) <= 1)`、`((tx.gasprice | 1) != 0)`、
  `((uint256(uint160(msg.sender)) % 2) < 2)`；
  恒假如 `((block.timestamp % 2) == 2)`、`((block.number & 1) == 2)`。
- 无副作用死代码：仅局部 `uint256` 临时变量做位运算/算术，绝不修改状态变量，绝不调用
  `revert`/`assert`。
- 注入策略：恒真谓词包裹原语句 `if (<true>) { <stmt> } else { <dead> }`；
  语句间隙插入恒假分支 `if (<false>) { <复杂局部算术> }`。
- 三条红线：
  1. 跳过 `VariableDeclarationStatement`，防止局部变量作用域被锁死在 `if` 内导致
     `Undeclared identifier`；
  2. `pure` 函数直接跳过，或只用基于入参的纯数学恒等式（如 `((x * x + x) % 2 == 0)`）；
  3. 每函数注入不超过 `max_injections`（默认 2 或 3）处，防 `Stack too deep`。
- **验收**：L1+L2+L3 后 4 份合约在 optimize False/True 下均编译通过，pytest 100% Pass。

### Phase 4：CLI 与批量生成（`obf/cli.py`、`README.md`）

- `argparse` + `pathlib.Path`，支持单文件与目录批量；输出强制 UTF-8 + LF。
- `--all-levels` 一次性生成 `L1/`、`L2/`、`L3/` 三套产物；终端打印纯 ASCII 汇总表
  （Contract, Level, Patches Applied, Compile Status）。
- **验收**：一键生成全部 12 份混淆合约零报错，全量 16 份通过回归测试。

### Phase 5：四维度量化评测与绘图（`eval/run_eval.py`、`eval/plot_charts.py`）

对 4 合约 × 4 级别（L0~L3）× 2 优化开关评测，写入 `eval/output/metrics_summary.csv`：

- **Potency**：`ast_nodes`（递归统计 AST 节点总数）；`cfg_basic_blocks` / `cfg_edges`
  （Slither 遍历所有非构造函数，累加 CFG 节点与 `sons` 边）。
- **Stealth**：`opcode_cosine_sim`（EVM opcode 频次向量与原版 L0 的余弦相似度，越接近 1 越自然）。
- **Resilience**：`bytecode_diff_sim`（`difflib.SequenceMatcher` 计算 runtime bytecode 相似度，越低越好）；
  `optimizer_retention_rate`（optimize True/False 下新增 CFG 基本块的留存比例）。
  另导出 `SimpleERC20` 的 L0 / L3 runtime bytecode `.txt`，供 Dedaub 反编译截图。
- **Cost**：`bytecode_size_kb`（< 24 KB 检查）、`deploy_gas`、`avg_exec_gas` 及相对 L0 增长百分比。
- 图表（300 DPI，纯英文标注）：
  `fig1_gas_overhead.png`、`fig2_potency_complexity.png`、
  `fig3_security_gas_tradeoff.png`、`fig4_stealth_resilience_opt.png`。
- **验收**：依次运行两个脚本无异常退出，`eval/output/` 产出完整 CSV 与 4 张无文字重叠的 PNG。

## 5. 三层测试矩阵

1. **编译层校验**：每次 Pass 打补丁后由 `engine.py` 自动触发 solc 0.8.20 编译；
   必须同时验证 `optimizer={"enabled": False}` 与 `{"enabled": True, "runs": 200}`。
2. **功能等价性回归**：`pytest tests/test_equivalence.py -v`；
   校验 public/external 签名集合相等、状态变量与事件一致、非法调用同样 revert。
3. **确定性与跨平台**：固定 `--seed 42` 连跑两次比对哈希；冒烟测试构造 CRLF 输入验证偏移零错位；
   若 `max_injections=3` 触发 `Stack too deep`，自动降级为 1 并确认恢复通过。
