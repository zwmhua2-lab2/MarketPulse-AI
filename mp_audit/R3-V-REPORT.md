# R3 第 4/5 项独立审计
开始 UTC：2026-10-21T18:53:17.701Z
固定来源：研究提交 `5cdc62ddcf42814130440ff47a47a1c3c9648b25`（本地 Git 对象只读）

## 固定源原始字节 SHA-256
- research/kernel.py: 8e0e1431d1a9a097755d786ccc46527b0050ae5d89941e30dd13f4c1d879378a；二次读取 一致
- research/cost_breakdown.py: 8e1784a07dc68c8615db5d00c2f9049f822a0ddc86f2461ea22c8265fd9b64cc；二次读取 一致
- research/cost_breakdown.txt: 196e624828fc4a0260a7d4c24735d68b02d041dc8e00929858a127250757ce12；二次读取 一致
- research/test_registry.json: f02558e0136e7ac668fa550edfe5070804eb3f851ac42de2668189c805f6ff8c；二次读取 一致
- research/run_r3_explore.txt: dc43877f0ae5b37833792561954c02aa17e8d834c3b43eb72492f8698868b3a1；二次读取 一致
- research/data_availability.txt: e7853c5be23e8da8011d6c1a05b960c939971aac755b99d9fd99ed82a3976afc；二次读取 一致

## 成本敏感性
- VERIFIED：K=(1-s)(1-f)/((1+s)(1+f))，f=10/10000；s=0/5/10 bps → 往返 19.98 / 29.96 / 39.92 bps。cost_breakdown.txt 的既有基准 29.96 bps；BTC 5m gross 0.02、net -29.94 bps。
- 新成本下 G1/G2：NOT_VERIFIED（没有逐笔原始收益序列，未重跑回测）。

## 累计比较次数 m
- m 来源：VERIFIED；distinct keys=60, windows={"confirm-30pct":12,"explore-70pct":12,"explore-730d":36}, R3 header m=60, rows=36, 0.05/60=0.0008333333333333334
- 历史漏登完整性：NOT_VERIFIED（注册表不能证明未入账比较不存在）。

## OI 5m REST
- VERIFIED；URL：https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=5；HTTP：200；响应 851 字节；原始 SHA-256 2cfc8efd47dcfefd0f2a9863c2fb5e831618ae28793e89a9dea3f47ea530cd50；时间戳 1792607400000, 1792607700000, 1792608000000, 1792608300000, 1792608600000；相邻差值 300000, 300000, 300000, 300000 ms；覆盖 2026-10-21T18:30:00.000Z .. 2026-10-21T18:50:00.000Z；仅此样本粒度 5m

## 日归档 metrics ZIP
- VERIFIED；URL：https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-10-01.zip；首次及必要的一次复测均 HTTP 200、各 11631 字节。第一次因脚本误要求原始行序递增而记为 `NOT_VERIFIED`；修正后复测成功，以下哈希均针对复测响应。
- 原始 ZIP SHA-256：e65cebeb721c5179e7734cbf7053516f1e5ec04fe273f2dfa3174ac17d716042；内存解压 CSV SHA-256：bd9f1d65780357b4ca9ca906d339cf93a828bb9516f8ad5d0ae15647b4cf5b11。保存 ZIP 后独立读回 SHA-256：e65cebeb721c5179e7734cbf7053516f1e5ec04fe273f2dfa3174ac17d716042，一致。
- CSV 原始行序非时间顺序；`create_time` 按 UTC 解析并排序，共 288 条。首五时间戳：1790812800000, 1790813100000, 1790813400000, 1790813700000, 1790814000000；末五：1790897700000, 1790898000000, 1790898300000, 1790898600000, 1790898900000。相邻差值：300000 ms × 287；覆盖 2026-10-01T00:00:00.000Z .. 2026-10-01T23:55:00.000Z；仅此样本为 5m，不能从 `daily` 目录名推断记录粒度。

## 范围与复核
- 资金费率、大小户比例、主动成交、清算、完整回溯深度：NOT_VERIFIED。
- 测试：`node --test mp_audit/*.test.mjs test/fetch-history.test.mjs`：54 pass、0 fail；单独 `node --test mp_audit/*.test.mjs` 曾于前一版测试得到 8 pass、0 fail，最终版的 11 项已包含在前述联合命令中。`node --test`：51 pass、7 fail，均因历史前端缺少 `vitest`、`msw`、`@testing-library/jest-dom`，未新增依赖。
- 白名单 diff：暂存区 `git diff --cached --name-status origin/main` 仅 5 个 `A mp_audit/**` 路径（本报告、脚本、测试、OI JSON、metrics ZIP），白名单外变化数 0；新增文本 196 行，低于 300 行上限。`test/fetch-history.test.mjs` 的 HEAD 内容按当前 CRLF 签出重建与现文件字节一致，SHA-256 均为 aeccbef5f6bcf1c4b28ce6107fc6da3393ed9ff79c4b6a32f20a3389bee64ff4。
- 累计真实下载响应字节：851 + 11631 + 11631 = 24113 / 20971520。
- 结束 UTC：2026-10-21T18:54:46.650Z；自 2026-10-21T18:50:24.352Z 开始约 4 分 22 秒（小于 2 小时）。
- oi-5m.json 二次读取 SHA-256：2cfc8efd47dcfefd0f2a9863c2fb5e831618ae28793e89a9dea3f47ea530cd50；与原始哈希一致。
