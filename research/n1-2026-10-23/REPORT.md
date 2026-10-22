# N1 长周期补证据
实际运行开始：2026-10-23T02:00:27+08:00；实际计算停止：2026-10-23T02:33:35+08:00；总耗时：1987.76 秒。预设 36 项：完成 36 项，实际调用完成 36 项。此前只读启动核对为 01:46；04:43 为固定截止时间。

执行端曾因缺少 ARCHITECTURE.md 停下，Human 裁决豁免，依据为本仓库 AGENTS.md 的研究沙盒例外。

本次 `m=96` 仅在 N1 独立登记快照中有效，未写入仓库 `research/test_registry.json`。后续任务直接读取该文件仍会得到 `m=60`，不得据此重置累计比较次数。须单独授权补记新增 36 项，且不得修改历史条目。

## 结论

36 项净收益点估计全部为负：窗口一为 −30.887 至 −13.655 bps，窗口二为 −31.051 至 −14.397 bps。同一 18 组从窗口一扩展至窗口二，仅 1 组点估计改善，变化范围为 −2.252 至 +1.524 bps；18 组净收益区间全部收窄，宽度减少 2.238 至 16.351 bps。区间变窄没有产生正净期望证据。跨 0 的 11 项均为 1d；4h、12h 的 24 项及窗口二 BTC failed_breakdown_reclaim 1d 的净区间上界均低于 0。
窗口 1：完成 18/18，分类 {"探索候选": 0, "该窗口不支持正净期望": 12, "证据不足": 6, "未证明相对优势": 0}。
窗口 2：完成 18/18，分类 {"探索候选": 0, "该窗口不支持正净期望": 13, "证据不足": 5, "未证明相对优势": 0}。
新旧窗口均为探索；重叠窗口不构成独立确认。K 线信号不等同强平、订单流或因果证据。

## 两组预设结果（收益单位 bps）

### 窗口 1
|币种|Family|持有期|事件/有效块|净收益 [区间]|基线差值 [区间]|m|G1/G2|状态/原因|
|---|---|---|---|---|---|---|---|---|
|BTC-USDT|panic_drop_long v0|4h|6962/2157|-20.759 [-31.041, -10.432]|7.092 [-1.749, 16.437]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|panic_drop_long v0|12h|6962/2157|-23.040 [-42.502, -4.183]|0.604 [-14.254, 14.635]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|panic_drop_long v0|1d|6962/493|-24.607 [-55.771, 7.726]|-7.552 [-28.337, 12.346]|96|False/False|证据不足; |
|BTC-USDT|failed_breakdown_reclaim v0|4h|13565/2445|-26.256 [-33.172, -19.482]|1.569 [-3.902, 6.847]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|failed_breakdown_reclaim v0|12h|13565/2445|-25.662 [-42.668, -9.134]|-2.025 [-12.717, 8.034]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|failed_breakdown_reclaim v0|1d|13561/495|-22.664 [-51.270, 4.783]|-5.639 [-20.276, 8.138]|96|False/False|证据不足; |
|BTC-USDT|squeeze_breakout v0|4h|10742/2041|-30.887 [-37.699, -23.924]|-3.060 [-9.399, 2.963]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|squeeze_breakout v0|12h|10737/2041|-25.727 [-42.347, -8.198]|-2.091 [-14.919, 11.124]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|squeeze_breakout v0|1d|10731/494|-23.302 [-53.376, 8.163]|-6.357 [-25.431, 13.593]|96|False/False|证据不足; |
|ETH-USDT|panic_drop_long v0|4h|7889/2247|-19.642 [-30.335, -9.160]|8.104 [-1.072, 17.509]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|panic_drop_long v0|12h|7889/2247|-23.112 [-46.269, -0.936]|0.350 [-16.035, 16.117]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|panic_drop_long v0|1d|7889/494|-13.655 [-57.503, 28.567]|2.807 [-23.969, 25.492]|96|False/False|证据不足; |
|ETH-USDT|failed_breakdown_reclaim v0|4h|13483/2441|-24.874 [-33.752, -16.102]|2.875 [-3.901, 9.659]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|failed_breakdown_reclaim v0|12h|13483/2441|-26.149 [-48.138, -5.515]|-2.668 [-15.849, 10.664]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|failed_breakdown_reclaim v0|1d|13477/495|-19.308 [-60.139, 18.201]|-2.820 [-21.413, 14.289]|96|False/False|证据不足; |
|ETH-USDT|squeeze_breakout v0|4h|11153/2067|-27.009 [-35.069, -18.730]|0.730 [-6.376, 7.880]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|squeeze_breakout v0|12h|11149/2066|-23.625 [-43.085, -3.985]|-0.187 [-15.663, 15.277]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|squeeze_breakout v0|1d|11147/494|-15.887 [-50.031, 18.802]|0.467 [-23.093, 23.934]|96|False/False|证据不足; |

### 窗口 2
|币种|Family|持有期|事件/有效块|净收益 [区间]|基线差值 [区间]|m|G1/G2|状态/原因|
|---|---|---|---|---|---|---|---|---|
|BTC-USDT|panic_drop_long v0|4h|9196/2808|-22.814 [-31.291, -14.200]|5.310 [-1.829, 12.763]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|panic_drop_long v0|12h|9196/2808|-23.171 [-38.681, -7.461]|1.362 [-10.773, 12.070]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|panic_drop_long v0|1d|9195/639|-23.083 [-49.195, 1.336]|-4.246 [-21.768, 12.215]|96|False/False|证据不足; |
|BTC-USDT|failed_breakdown_reclaim v0|4h|17698/3164|-26.722 [-32.507, -21.055]|1.398 [-2.965, 5.818]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|failed_breakdown_reclaim v0|12h|17696/3164|-26.287 [-40.084, -13.193]|-1.778 [-10.460, 6.359]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|failed_breakdown_reclaim v0|1d|17694/641|-22.842 [-46.012, -0.857]|-4.025 [-15.525, 7.071]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|squeeze_breakout v0|4h|13673/2599|-31.051 [-36.833, -25.317]|-2.933 [-7.916, 2.140]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|squeeze_breakout v0|12h|13673/2599|-26.707 [-40.955, -11.942]|-2.234 [-13.108, 9.051]|96|False/False|该窗口不支持正净期望; |
|BTC-USDT|squeeze_breakout v0|1d|13672/640|-23.880 [-47.936, 2.246]|-5.122 [-21.672, 11.703]|96|False/False|证据不足; |
|ETH-USDT|panic_drop_long v0|4h|10514/2923|-21.894 [-31.060, -12.342]|6.211 [-1.853, 14.558]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|panic_drop_long v0|12h|10514/2923|-24.000 [-44.218, -5.088]|0.420 [-14.067, 14.112]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|panic_drop_long v0|1d|10512/640|-14.397 [-50.910, 18.809]|4.019 [-16.157, 22.044]|96|False/False|证据不足; |
|ETH-USDT|failed_breakdown_reclaim v0|4h|17674/3162|-26.281 [-33.749, -18.791]|1.806 [-3.723, 7.471]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|failed_breakdown_reclaim v0|12h|17668/3162|-27.678 [-45.875, -10.636]|-3.279 [-13.819, 7.370]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|failed_breakdown_reclaim v0|1d|17666/641|-21.554 [-53.999, 9.085]|-3.146 [-18.353, 10.895]|96|False/False|证据不足; |
|ETH-USDT|squeeze_breakout v0|4h|14162/2664|-27.740 [-34.473, -20.881]|0.314 [-5.881, 6.414]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|squeeze_breakout v0|12h|14162/2664|-23.855 [-39.873, -7.474]|0.500 [-12.289, 13.005]|96|False/False|该窗口不支持正净期望; |
|ETH-USDT|squeeze_breakout v0|1d|14159/640|-16.452 [-44.988, 12.605]|1.952 [-17.614, 22.419]|96|False/False|证据不足; |

## 点估计与区间宽度变化
相对历史 R3 比较使用其已保存、保留两位小数的输出（m=60）；N1 m=96，因此区间宽度变化同时受数据窗口与多重校正影响。原 R3 数据末根 confirm=0，本次已剔除，不能把差异全部归因于历史长度。

|窗口|币种 / Family / 持有期|相对 R3 净点估计变化 bps|相对 R3 净区间宽度变化 bps|相对 R3 差值点估计变化 bps|相对 R3 差值区间宽度变化 bps|
|---|---|---|---|---|---|
|1|BTC-USDT / panic_drop_long v0 / 4h|8.501|-5.661|7.202|-3.784|
|1|BTC-USDT / panic_drop_long v0 / 12h|0.370|-5.081|-3.526|-1.991|
|1|BTC-USDT / panic_drop_long v0 / 1d|-6.587|-0.003|-14.532|-2.428|
|1|BTC-USDT / failed_breakdown_reclaim v0 / 4h|2.014|-3.150|0.719|-2.321|
|1|BTC-USDT / failed_breakdown_reclaim v0 / 12h|2.748|-2.257|-1.125|-2.569|
|1|BTC-USDT / failed_breakdown_reclaim v0 / 1d|0.826|2.743|-7.219|2.173|
|1|BTC-USDT / squeeze_breakout v0 / 4h|0.763|-2.504|-0.510|-2.017|
|1|BTC-USDT / squeeze_breakout v0 / 12h|4.533|1.439|0.699|-0.706|
|1|BTC-USDT / squeeze_breakout v0 / 1d|2.748|2.529|-5.307|-12.665|
|1|ETH-USDT / panic_drop_long v0 / 4h|8.898|-16.395|7.384|-13.618|
|1|ETH-USDT / panic_drop_long v0 / 12h|3.258|-26.617|-1.100|-19.728|
|1|ETH-USDT / panic_drop_long v0 / 1d|2.525|-6.920|-6.633|-5.520|
|1|ETH-USDT / failed_breakdown_reclaim v0 / 4h|5.936|-6.300|4.455|-4.440|
|1|ETH-USDT / failed_breakdown_reclaim v0 / 12h|6.461|-12.547|2.132|-9.977|
|1|ETH-USDT / failed_breakdown_reclaim v0 / 1d|10.002|-11.530|1.050|-15.458|
|1|ETH-USDT / squeeze_breakout v0 / 4h|3.331|-6.081|1.880|-6.164|
|1|ETH-USDT / squeeze_breakout v0 / 12h|0.665|-9.701|-3.617|-9.600|
|1|ETH-USDT / squeeze_breakout v0 / 1d|2.183|-12.847|-6.793|-29.753|
|2|BTC-USDT / panic_drop_long v0 / 4h|6.446|-9.179|5.420|-7.378|
|2|BTC-USDT / panic_drop_long v0 / 12h|0.239|-12.180|-2.768|-8.037|
|2|BTC-USDT / panic_drop_long v0 / 1d|-5.063|-12.969|-11.226|-9.127|
|2|BTC-USDT / failed_breakdown_reclaim v0 / 4h|1.548|-5.388|0.548|-4.287|
|2|BTC-USDT / failed_breakdown_reclaim v0 / 12h|2.123|-8.899|-0.878|-6.501|
|2|BTC-USDT / failed_breakdown_reclaim v0 / 1d|0.648|-8.155|-5.605|-3.644|
|2|BTC-USDT / squeeze_breakout v0 / 4h|0.599|-4.765|-0.383|-4.324|
|2|BTC-USDT / squeeze_breakout v0 / 12h|3.553|-3.697|0.556|-4.591|
|2|BTC-USDT / squeeze_breakout v0 / 1d|2.170|-8.827|-4.072|-18.315|
|2|ETH-USDT / panic_drop_long v0 / 4h|6.646|-18.852|5.491|-15.789|
|2|ETH-USDT / panic_drop_long v0 / 12h|2.370|-32.820|-1.030|-23.700|
|2|ETH-USDT / panic_drop_long v0 / 1d|1.783|-23.271|-5.421|-16.779|
|2|ETH-USDT / failed_breakdown_reclaim v0 / 4h|4.529|-8.992|3.386|-6.806|
|2|ETH-USDT / failed_breakdown_reclaim v0 / 12h|4.932|-19.931|1.521|-15.301|
|2|ETH-USDT / failed_breakdown_reclaim v0 / 1d|7.756|-26.785|0.724|-21.912|
|2|ETH-USDT / squeeze_breakout v0 / 4h|2.600|-8.827|1.464|-8.125|
|2|ETH-USDT / squeeze_breakout v0 / 12h|0.435|-16.400|-2.930|-15.246|
|2|ETH-USDT / squeeze_breakout v0 / 1d|1.618|-24.087|-5.308|-36.746|

窗口二减窗口一（相同 m=96；两个窗口重叠）：

|币种 / Family / 持有期|净点估计变化 bps|净区间宽度变化 bps|差值点估计变化 bps|差值区间宽度变化 bps|
|---|---|---|---|---|
|BTC-USDT / panic_drop_long v0 / 4h|-2.055|-3.518|-1.782|-3.594|
|BTC-USDT / panic_drop_long v0 / 12h|-0.131|-7.100|0.758|-6.046|
|BTC-USDT / panic_drop_long v0 / 1d|1.524|-12.965|3.306|-6.700|
|BTC-USDT / failed_breakdown_reclaim v0 / 4h|-0.466|-2.238|-0.171|-1.966|
|BTC-USDT / failed_breakdown_reclaim v0 / 12h|-0.625|-6.643|0.247|-3.932|
|BTC-USDT / failed_breakdown_reclaim v0 / 1d|-0.178|-10.898|1.614|-5.817|
|BTC-USDT / squeeze_breakout v0 / 4h|-0.164|-2.260|0.127|-2.307|
|BTC-USDT / squeeze_breakout v0 / 12h|-0.980|-5.136|-0.143|-3.885|
|BTC-USDT / squeeze_breakout v0 / 1d|-0.578|-11.357|1.235|-5.650|
|ETH-USDT / panic_drop_long v0 / 4h|-2.252|-2.456|-1.893|-2.170|
|ETH-USDT / panic_drop_long v0 / 12h|-0.888|-6.202|0.070|-3.973|
|ETH-USDT / panic_drop_long v0 / 1d|-0.742|-16.351|1.212|-11.259|
|ETH-USDT / failed_breakdown_reclaim v0 / 4h|-1.407|-2.692|-1.070|-2.366|
|ETH-USDT / failed_breakdown_reclaim v0 / 12h|-1.530|-7.383|-0.611|-5.324|
|ETH-USDT / failed_breakdown_reclaim v0 / 1d|-2.246|-15.256|-0.326|-6.455|
|ETH-USDT / squeeze_breakout v0 / 4h|-0.730|-2.747|-0.416|-1.961|
|ETH-USDT / squeeze_breakout v0 / 12h|-0.230|-6.700|0.687|-5.646|
|ETH-USDT / squeeze_breakout v0 / 1d|-0.565|-11.240|1.484|-6.993|

## 完整性与有效边界
- BTC-USDT new: VERIFIED；原始 712564 / 已收盘 712564 行；2018-01-11T11:10:00+00:00 → 2024-10-20T15:25:00+00:00；重复 0，缺失 0，非 5m 间隔 0，非有限值 0，OHLC 异常 0，负成交量 0，剔除 confirm=0 0。
- BTC-USDT original: VERIFIED；原始 210240 / 已收盘 210239 行；2024-10-20T15:30:00+00:00 → 2026-10-20T15:20:00+00:00；重复 0，缺失 0，非 5m 间隔 0，非有限值 0，OHLC 异常 0，负成交量 0，剔除 confirm=0 1。
- ETH-USDT new: VERIFIED；原始 712565 / 已收盘 712565 行；2018-01-11T11:10:00+00:00 → 2024-10-20T15:30:00+00:00；重复 0，缺失 0，非 5m 间隔 0，非有限值 0，OHLC 异常 0，负成交量 0，剔除 confirm=0 0。
- ETH-USDT original: VERIFIED；原始 210240 / 已收盘 210239 行；2024-10-20T15:35:00+00:00 → 2026-10-20T15:25:00+00:00；重复 0，缺失 0，非 5m 间隔 0，非有限值 0，OHLC 异常 0，负成交量 0，剔除 confirm=0 1。
逐根间隔、缺口范围、拼接等式、输入 SHA-256 见 integrity.json / splice_check.json；有效窗口在 frozen_windows.tmp 中于运行前冻结。

## 命令、运行口径与限制
下载实际耗时 1864.40 秒；36 个评估子进程墙钟合计 114.31 秒。指定性能样本子进程总墙钟 4.419 秒（加载及评估 3.682 秒），峰值驻留内存 655.695 MiB；全部评估子进程峰值上限 656.750 MiB，无内存异常，无需切换持有期批次。
两币扩展完整窗口分别为 922,803 / 922,804 根已收盘 5m K 线；新段 CSV 表头、字段顺序与原输入一致。
实际正式入口命令为 `python -B research/n1-2026-10-23/run_n1.py --wait-download`，等待下载完成后自动按顺序检查、实测与评估。准备期间曾停止一个尚在等待、未执行评估的旧入口进程；无重复评估。
```powershell
python -B research/n1-2026-10-23/download.py
python -B research/n1-2026-10-23/run_n1.py
```
子进程命令与错误见 run.log / child_*.tmp；每行原始输出及随机状态见 row_*.json.tmp。JSON/CSV 收益为小数比例，报告转为 bps。
Bootstrap=50000；m=96；alpha=0.05；alpha/m=0.0005208333333333333；q_lo=0.0260416667；q_hi=99.9739583333；种子 20261021，单一随机流，性能样本先运行且计入 36 项，不重复。原始 family / 成本 / 分块算法未变。
峰值内存使用 Windows GetProcessMemoryInfo.PeakWorkingSetSize（进程峰值驻留集，不是整机内存）；单行 process_wall_seconds 包含子进程启动，elapsed_seconds 为子进程内加载至评估完成耗时。
原登记快照保留全部 60 条历史条目，并预登记 36 项；未完成项目的状态以结果表为准。

## 自检与 NOT_VERIFIED
本轮 36 项比较、两币数据完整性及拼接检查均完成，没有未完成行。独立新数据确认未执行，状态为 NOT_VERIFIED；本次结果不能作为独立确认。

仅执行一轮必要自检：
```json
{
  "input_hashes_unchanged": true,
  "input_hash_details": {
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\kernel.py": true,
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\families.py": true,
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\test_registry.json": true,
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\run_r3_explore.txt": true,
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\data\\BTC-USDT_5m.csv": true,
    "C:\\Users\\hua\\.local\\share\\opencode\\worktree\\accc2a\\jolly-panda\\research\\data\\ETH-USDT_5m.csv": true
  },
  "registry_count_96": true,
  "original_60_preserved": true,
  "result_rows_36": true,
  "unique_comparisons_36": true,
  "window_counts": {
    "1": 18,
    "2": 18
  },
  "no_pending": true,
  "parameters_correct": true,
  "completed_before_deadline": true,
  "no_tracked_changes": true,
  "untracked_only_n1": true,
  "tracked_diff": [],
  "window1_csv_18_unique": true,
  "window2_csv_18_unique": true
}
```
