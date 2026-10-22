"""N1 integrity, frozen 36 comparisons, isolated kernel workers and evidence."""
import csv
import ctypes
import dataclasses
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parent
RESEARCH = ROOT.parent
sys.path.insert(0, str(RESEARCH))
import numpy as np
import pandas as pd
import kernel
from families import FAMILIES

DEADLINE = 1792701780
FIRST = 1515669000000
STEP = 300000
COINS = ['BTC-USDT', 'ETH-USDT']
VERSIONS = ['panic_drop_long v0', 'failed_breakdown_reclaim v0', 'squeeze_breakout v0']
HORIZONS = ['4h', '12h', '1d']
COLUMNS = 'ts,open,high,low,close,volume,vol_ccy,vol_ccy_quote,confirm'.split(',')
ORIGINAL_FIRST = {'BTC-USDT':1729438200000, 'ETH-USDT':1729438500000}
Q_LO, Q_HI, N_BOOT, M, SEED = 0.0260416667, 99.9739583333, 50000, 96, 20261021
PARAMS = dict(m=M, alpha=0.05, alpha_per_m=0.05/M, q_lo=Q_LO, q_hi=Q_HI, bootstrap=N_BOOT, seed=SEED)
NOTICE = '本次 `m=96` 仅在 N1 独立登记快照中有效，未写入仓库 `research/test_registry.json`。后续任务直接读取该文件仍会得到 `m=60`，不得据此重置累计比较次数。须单独授权补记新增 36 项，且不得修改历史条目。'

def clean(value):
    if isinstance(value, dict):
        return {k:clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    return value

def save(name, value):
    target=ROOT/name
    temp=ROOT/(name+'.tmp')
    temp.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(temp, target)

def log(event, **kw):
    record=clean(dict(epoch=time.time(), utc=dt.datetime.now(dt.timezone.utc).isoformat(), event=event, **kw))
    line=json.dumps(record, ensure_ascii=False, allow_nan=False)
    with (ROOT/'run.log').open('a',encoding='utf-8') as fh:
        fh.write(line+'\n')
    print(line,flush=True)

def utc(ts):
    return dt.datetime.fromtimestamp(ts/1000,dt.timezone.utc).isoformat()

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as fh:
        for part in iter(lambda:fh.read(1024*1024),b''):
            h.update(part)
    return h.hexdigest()

def peak_memory():
    class PMC(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    obj=PMC()
    obj.cb=ctypes.sizeof(obj)
    get_process=ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype=ctypes.c_void_p
    fn=ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(PMC),ctypes.c_ulong]
    if not fn(get_process(),ctypes.byref(obj),obj.cb):
        raise ctypes.WinError()
    return int(obj.PeakWorkingSetSize)

def inspect_file(path):
    result=dict(path=str(path),status='NOT_VERIFIED')
    if not path.exists():
        return None,dict(result,reason='FILE_NOT_AVAILABLE')
    result['sha256']=sha(path)
    frame=pd.read_csv(path,dtype=str,keep_default_na=False)
    result['columns']=list(frame.columns)
    result['raw_rows']=len(frame)
    if list(frame.columns)!=COLUMNS or frame.empty:
        return None,dict(result,reason='HEADER_MISMATCH_OR_EMPTY')
    if not frame.ts.str.fullmatch(r'[0-9]+').all():
        return None,dict(result,reason='TIMESTAMP_NOT_INTEGER')
    frame['ts']=frame.ts.astype('int64')
    result['input_strictly_ascending']=bool((frame.ts.diff().iloc[1:]>0).all())
    result['duplicate_rows']=int(frame.ts.duplicated().sum())
    duplicated=frame[frame.ts.duplicated(keep=False)]
    result['conflicting_duplicate_timestamps']=int(sum(len(group.drop_duplicates())>1 for _,group in duplicated.groupby('ts')))
    result['unclosed_rows']=int((frame['confirm']=='0').sum())
    result['invalid_confirm_rows']=int((~frame['confirm'].isin(['0','1'])).sum())
    frame=frame[frame['confirm']!='0'].sort_values('ts').reset_index(drop=True)
    if frame.empty:
        return None,dict(result,reason='NO_CLOSED_CANDLES')
    numeric=frame[COLUMNS[1:8]].apply(pd.to_numeric,errors='coerce').to_numpy(dtype=float)
    result['nonfinite_values']=int((~np.isfinite(numeric)).sum())
    o,h,l,c=numeric[:,0],numeric[:,1],numeric[:,2],numeric[:,3]
    result['nonpositive_prices']=int((numeric[:,:4]<=0).sum())
    result['ohlc_bad_rows']=int(((h<np.maximum.reduce([o,l,c]))|(l>np.minimum.reduce([o,h,c]))).sum())
    result['negative_volume_values']=int((numeric[:,4:]<0).sum())
    ts=frame.ts.to_numpy()
    diff=np.diff(ts)
    result['off_grid_timestamps']=int((ts%STEP!=0).sum())
    result['non_5m_intervals']=int((diff!=STEP).sum())
    gaps=[]
    for i in np.flatnonzero(diff>STEP):
        gaps.append(dict(previous_ts=int(ts[i]),next_ts=int(ts[i+1]),previous_utc=utc(int(ts[i])),next_utc=utc(int(ts[i+1])),missing_bars=int(diff[i]//STEP-1)))
    result.update(closed_rows=len(frame),first_ts=int(ts[0]),last_ts=int(ts[-1]),first_utc=utc(int(ts[0])),last_utc=utc(int(ts[-1])),missing_bars=sum(g['missing_bars'] for g in gaps),gaps=gaps)
    bad=['duplicate_rows','conflicting_duplicate_timestamps','invalid_confirm_rows','nonfinite_values','nonpositive_prices','ohlc_bad_rows','negative_volume_values','off_grid_timestamps','non_5m_intervals']
    result['status']='VERIFIED' if not any(result[k] for k in bad) and result['input_strictly_ascending'] else 'NOT_VERIFIED'
    result['reason']=None if result['status']=='VERIFIED' else 'INTEGRITY_FAILURE_NO_COMPUTATION_ACROSS_GAPS'
    return frame,result

def prepare():
    records=[json.loads(x) for x in (ROOT/'run.log').read_text(encoding='utf-8').splitlines()]
    downloads=[r for r in records if r['event']=='download_finished']
    if not downloads:
        raise RuntimeError('DOWNLOAD_NOT_FINISHED: run prepare only after downloader exits')
    integrity={}
    splice={}
    frozen={}
    for coin in COINS:
        old,old_info=inspect_file(RESEARCH/'data'/f'{coin}_5m.csv')
        new_path=ROOT/'data'/f'{coin}_5m_2018-2024.csv'
        if not new_path.exists():
            new_path=pathlib.Path(str(new_path)+'.partial')
        new,new_info=inspect_file(new_path)
        download=downloads[-1]['status'][coin]
        integrity[coin]=dict(original=old_info,new=new_info,download=download)
        contiguous=bool(new is not None and old is not None and int(new.ts.iloc[-1])+STEP==int(old.ts.iloc[0]))
        complete=bool(download['complete'] and new_info['status']=='VERIFIED' and old_info['status']=='VERIFIED' and new_info.get('first_ts')==FIRST and old_info.get('first_ts')==ORIGINAL_FIRST[coin] and contiguous)
        splice[coin]=dict(status='VERIFIED' if complete else 'NOT_VERIFIED',equation='new_last_ts + 300000 == original_first_ts',new_last_ts=new_info.get('last_ts'),original_first_ts=old_info.get('first_ts'),boundary_contiguous=contiguous,whole_series_adjacent_intervals_checked=True if new is not None and old is not None else False,no_gaps_or_duplicates=complete)
        frozen[coin]=dict(eligible=complete,window1=dict(start_inclusive=FIRST,end_exclusive=ORIGINAL_FIRST[coin]),window2=dict(start_inclusive=FIRST,end_exclusive=old_info.get('last_ts',0)+STEP),reason=None if complete else 'DATA_AVAILABILITY_OR_INTEGRITY_UNRESOLVED')
    save('integrity.json',integrity)
    save('splice_check.json',splice)
    original=json.loads((RESEARCH/'test_registry.json').read_text())
    if len(original)!=60:
        raise RuntimeError(f'ORIGINAL_REGISTRY_COUNT={len(original)}')
    rows=[]
    snapshot=dict(original)
    stamp=dt.datetime.now(dt.timezone.utc).isoformat()
    for window in (1,2):
        for coin in COINS:
            for version in VERSIONS:
                for horizon in HORIZONS:
                    key=f'n1-window{window}-2018|{version}|{coin}|{horizon}'
                    assert key not in snapshot
                    snapshot[key]=stamp
                    rows.append(dict(id=len(rows),window=window,coin=coin,version=version,horizon=horizon,**PARAMS,**frozen[coin][f'window{window}'],status='PENDING' if frozen[coin]['eligible'] else 'NOT_VERIFIED',reason=frozen[coin]['reason'],n_raw=None,n_blocks=None,net=None,n_lo=None,n_hi=None,delta=None,d_lo=None,d_hi=None,G1=None,G2=None))
    assert len(snapshot)==96 and all(snapshot[k]==v for k,v in original.items())
    save('registry_snapshot.json',snapshot)
    save('frozen_windows.tmp',dict(frozen_epoch=time.time(),windows=frozen,rows=rows,**PARAMS,seed_policy='One PCG64 stream, seed 20261021. Probe first; remaining window/coin/family/horizon order. State passed between child processes.'))
    save('rng_state.tmp',np.random.default_rng(SEED).bit_generator.state)
    for window in (1,2):
        save(f'results_window{window}.json',[r for r in rows if r['window']==window])
    log('windows_and_registry_frozen_before_evaluation',windows=frozen,registry_original=60,registry_snapshot=96,**PARAMS)
    return rows

def dataframe(row):
    paths=[ROOT/'data'/f"{row['coin']}_5m_2018-2024.csv"]
    if row['window']==2:
        paths.append(RESEARCH/'data'/f"{row['coin']}_5m.csv")
    frames=[pd.read_csv(p,dtype={'ts':'int64'}) for p in paths]
    df=pd.concat(frames,ignore_index=True)
    df=df[(df['confirm']==1)&(df.ts>=row['start_inclusive'])&(df.ts<row['end_exclusive'])].reset_index(drop=True)
    assert df.ts.iloc[0]==row['start_inclusive'] and df.ts.iloc[-1]+STEP==row['end_exclusive']
    assert np.all(np.diff(df.ts.to_numpy())==STEP)
    for col in COLUMNS[1:8]:
        df[col]=df[col].astype(float)
    df['time']=pd.to_datetime(df.ts,unit='ms',utc=True)
    return df

def worker(row_id):
    start=time.time()
    frozen=json.loads((ROOT/'frozen_windows.tmp').read_text(encoding='utf-8'))
    row=frozen['rows'][row_id]
    try:
        if time.time()>=DEADLINE:
            raise RuntimeError('DEADLINE')
        df=dataframe(row)
        mask=np.asarray(FAMILIES[row['version']](df),dtype=bool)
        bars=kernel.HORIZON_BARS[row['horizon']]
        rng=np.random.default_rng(SEED)
        rng.bit_generator.state=json.loads((ROOT/'rng_state.tmp').read_text())
        actual=kernel.evaluate(df,mask,kernel.forward_returns(df,bars),kernel.gross_returns(df,bars),row['version'],row['coin'],row['horizon'],rng,N_BOOT,q_lo=Q_LO,q_hi=Q_HI)
        row.update(dataclasses.asdict(actual))
        finite=all(math.isfinite(getattr(actual,k)) for k in ['net','delta','n_lo','n_hi','d_lo','d_hi'])
        row.update(status='COMPLETE' if actual.enough and finite else 'NOT_VERIFIED',reason=None if actual.enough and finite else 'INSUFFICIENT_SAMPLES_OR_NONFINITE_INTERVAL',G1=bool(actual.gate1),G2=bool(actual.gate2),elapsed_seconds=time.time()-start,peak_working_set_bytes=peak_memory(),evaluated=True)
        if row['status']!='COMPLETE':
            row['classification']='NOT_VERIFIED'
        elif row['G1'] and row['G2']:
            row['classification']='探索候选'
        elif row['n_hi']<0:
            row['classification']='该窗口不支持正净期望'
        elif row['n_lo']<=0<=row['n_hi']:
            row['classification']='证据不足'
        elif row['G2'] and not row['G1']:
            row['classification']='未证明相对优势'
        else:
            row['classification']='NOT_VERIFIED'
        save(f'row_{row_id:02d}.json.tmp',dict(row=row,rng_state=rng.bit_generator.state))
    except Exception as exc:
        row.update(status='NOT_VERIFIED',reason=f'{type(exc).__name__}: {exc}',classification='NOT_VERIFIED',elapsed_seconds=time.time()-start,peak_working_set_bytes=peak_memory(),evaluated=False)
        save(f'row_{row_id:02d}.json.tmp',dict(row=row))

CSV_FIELDS=['id','window','coin','version','horizon','start_inclusive','end_exclusive','status','reason','classification','n_raw','n_blocks','net','n_lo','n_hi','delta','d_lo','d_hi','G1','G2','m','alpha','alpha_per_m','q_lo','q_hi','bootstrap','seed','elapsed_seconds','process_wall_seconds','peak_working_set_bytes']

def persist(row, rows):
    rows[row['id']]=row
    path=ROOT/f"results_window{row['window']}.csv"
    exists=path.exists()
    with path.open('a',newline='',encoding='utf-8-sig' if not exists else 'utf-8') as fh:
        writer=csv.DictWriter(fh,fieldnames=CSV_FIELDS,extrasaction='ignore')
        if not exists:
            writer.writeheader()
        writer.writerow(clean(row))
        fh.flush()
        os.fsync(fh.fileno())
    save(f"results_window{row['window']}.json",[r for r in rows if r['window']==row['window']])

def evaluate_all(rows):
    probe=next(r for r in rows if r['window']==2 and r['coin']=='BTC-USDT' and r['version']=='panic_drop_long v0' and r['horizon']=='4h')
    order=[probe['id']]+[r['id'] for r in rows if r['id']!=probe['id']]
    log('evaluation_order',ids=order,seed_policy='single original-seed RNG stream, probe retained without repeat',**PARAMS)
    while order:
        rid=order.pop(0)
        row=rows[rid]
        if row['status']=='PENDING' and time.time()>=DEADLINE-300:
            row.update(status='NOT_VERIFIED',reason='DEADLINE_NO_NEW_COMPARISON')
        if row['status']=='PENDING':
            started=time.time()
            cmd=[sys.executable,'-B',str(__file__),'--worker',str(rid)]
            log('comparison_start',id=rid,window=row['window'],coin=row['coin'],version=row['version'],horizon=row['horizon'],command=cmd,**PARAMS)
            child_log=ROOT/f'child_{rid:02d}.tmp'
            with child_log.open('x',encoding='utf-8') as output:
                process=subprocess.Popen(cmd,stdout=output,stderr=subprocess.STDOUT,cwd=str(RESEARCH.parent))
                killed=False
                while process.poll() is None:
                    if time.time()>=DEADLINE:
                        process.kill()
                        process.wait()
                        killed=True
                        break
                    time.sleep(0.2)
            result_path=ROOT/f'row_{rid:02d}.json.tmp'
            if result_path.exists() and not killed:
                payload=json.loads(result_path.read_text(encoding='utf-8'))
                row=payload['row']
                if 'rng_state' in payload:
                    save('rng_state.tmp',payload['rng_state'])
            else:
                row.update(status='NOT_VERIFIED',reason='DEADLINE_CHILD_TERMINATED' if killed else f'CHILD_EXIT_{process.returncode}',evaluated=False)
            row['process_wall_seconds']=time.time()-started
            log('comparison_finished',row=row)
        persist(row,rows)
        if rid==probe['id']:
            perf=dict(row,probe_included_in_36=True,finished_epoch=time.time())
            if row.get('process_wall_seconds',0)>120 or 'MemoryError' in str(row.get('reason')):
                order.sort(key=lambda k:HORIZONS.index(rows[k]['horizon']))
                perf['batching']='BY_HORIZON_SERIAL_CHILD_PROCESSES'
                log('switch_to_horizon_batches',remaining_ids=order)
            else:
                perf['batching']='SERIAL_CHILD_PROCESSES'
            save('probe_perf.json',perf)
    return rows

def historical_rows():
    output={}
    for line in (RESEARCH/'run_r3_explore.txt').read_text(encoding='utf-8').splitlines():
        match=re.match(r'^(\w+ v0)\s+(BTC-USDT|ETH-USDT)\s+(4h|12h|1d)\s+(\d+)\s+(\d+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+\[\s*([-\d.]+),\s*([-\d.]+)\]\s+\[\s*([-\d.]+),\s*([-\d.]+)\]',line)
        if match:
            v,c,h,_,_,gross,net,base,delta,dlo,dhi,nlo,nhi=match.groups()
            output[(c,v,h)]=dict(net=float(net),width=float(nhi)-float(nlo),delta=float(delta),delta_width=float(dhi)-float(dlo))
    return output

def report(rows):
    events=[json.loads(x) for x in (ROOT/'run.log').read_text(encoding='utf-8').splitlines()]
    start=events[0]['start_epoch']
    stop=time.time()
    completed=sum(r['status']=='COMPLETE' for r in rows)
    evaluated=sum(bool(r.get('evaluated')) for r in rows)
    bj=lambda stamp:dt.datetime.fromtimestamp(stamp,dt.timezone(dt.timedelta(hours=8))).isoformat(timespec='seconds')
    integrity=json.loads((ROOT/'integrity.json').read_text(encoding='utf-8'))
    lines=['# N1 长周期补证据',f'实际运行开始：{bj(start)}；实际计算停止：{bj(stop)}；总耗时：{stop-start:.2f} 秒。预设 36 项：完成 {completed} 项，实际调用完成 {evaluated} 项。此前只读启动核对为 01:46；04:43 为固定截止时间。','', '执行端曾因缺少 ARCHITECTURE.md 停下，Human 裁决豁免，依据为本仓库 AGENTS.md 的研究沙盒例外。','',NOTICE,'','## 结论']
    if not completed:
        lines.append('数据可得性未解决；36 项没有可用于判断收益的完整证据，均以实际原因标记 NOT_VERIFIED。未缩小窗口，未改源、family、成本、门槛或内核。' if any(not v['download']['complete'] for v in integrity.values()) else '尚无可核验的完整统计结果；按各行原因标记 NOT_VERIFIED，不作收益结论。')
    else:
        for w in (1,2):
            subset=[r for r in rows if r['window']==w and r['status']=='COMPLETE']
            counts={k:sum(r.get('classification')==k for r in subset) for k in ['探索候选','该窗口不支持正净期望','证据不足','未证明相对优势']}
            lines.append(f'窗口 {w}：完成 {len(subset)}/18，分类 {json.dumps(counts,ensure_ascii=False)}。')
    lines.extend(['新旧窗口均为探索；重叠窗口不构成独立确认。K 线信号不等同强平、订单流或因果证据。','', '## 两组预设结果（收益单位 bps）'])
    def num(v):
        return '—' if v is None else f'{v*10000:.3f}'
    for w in (1,2):
        lines.extend(['',f'### 窗口 {w}', '|币种|Family|持有期|事件/有效块|净收益 [区间]|基线差值 [区间]|m|G1/G2|状态/原因|','|---|---|---|---|---|---|---|---|---|'])
        for r in rows:
            if r['window']!=w:
                continue
            lines.append(f"|{r['coin']}|{r['version']}|{r['horizon']}|{r.get('n_raw')}/{r.get('n_blocks')}|{num(r.get('net'))} [{num(r.get('n_lo'))}, {num(r.get('n_hi'))}]|{num(r.get('delta'))} [{num(r.get('d_lo'))}, {num(r.get('d_hi'))}]|96|{r.get('G1')}/{r.get('G2')}|{r.get('classification',r['status'])}; {r.get('reason') or ''}|")
    lines.extend(['','## 点估计与区间宽度变化','相对历史 R3 比较使用其已保存、保留两位小数的输出（m=60）；N1 m=96，因此区间宽度变化同时受数据窗口与多重校正影响。原 R3 数据末根 confirm=0，本次已剔除，不能把差异全部归因于历史长度。','', '|窗口|币种 / Family / 持有期|相对 R3 净点估计变化 bps|相对 R3 净区间宽度变化 bps|相对 R3 差值点估计变化 bps|相对 R3 差值区间宽度变化 bps|','|---|---|---|---|---|---|'])
    old=historical_rows()
    for r in rows:
        prior=old.get((r['coin'],r['version'],r['horizon']))
        if r['status']=='COMPLETE' and prior:
            lines.append(f"|{r['window']}|{r['coin']} / {r['version']} / {r['horizon']}|{r['net']*1e4-prior['net']:.3f}|{(r['n_hi']-r['n_lo'])*1e4-prior['width']:.3f}|{r['delta']*1e4-prior['delta']:.3f}|{(r['d_hi']-r['d_lo'])*1e4-prior['delta_width']:.3f}|")
    if not completed:
        lines.append('|—|全部 36 项|NOT_VERIFIED|NOT_VERIFIED|NOT_VERIFIED|NOT_VERIFIED|')
    lines.extend(['','窗口二减窗口一（相同 m=96；两个窗口重叠）：','', '|币种 / Family / 持有期|净点估计变化 bps|净区间宽度变化 bps|差值点估计变化 bps|差值区间宽度变化 bps|','|---|---|---|---|---|'])
    for r in rows:
        if r['window']!=2 or r['status']!='COMPLETE':
            continue
        prior=next(p for p in rows if p['window']==1 and all(p[k]==r[k] for k in ['coin','version','horizon']))
        if prior['status']=='COMPLETE':
            lines.append(f"|{r['coin']} / {r['version']} / {r['horizon']}|{(r['net']-prior['net'])*1e4:.3f}|{((r['n_hi']-r['n_lo'])-(prior['n_hi']-prior['n_lo']))*1e4:.3f}|{(r['delta']-prior['delta'])*1e4:.3f}|{((r['d_hi']-r['d_lo'])-(prior['d_hi']-prior['d_lo']))*1e4:.3f}|")
    lines.extend(['','## 完整性与有效边界'])
    for coin,info in integrity.items():
        for source in ['new','original']:
            item=info[source]
            lines.append(f"- {coin} {source}: {item.get('status')}；原始 {item.get('raw_rows')} / 已收盘 {item.get('closed_rows')} 行；{item.get('first_utc')} → {item.get('last_utc')}；重复 {item.get('duplicate_rows')}，缺失 {item.get('missing_bars')}，非 5m 间隔 {item.get('non_5m_intervals')}，非有限值 {item.get('nonfinite_values')}，OHLC 异常 {item.get('ohlc_bad_rows')}，负成交量 {item.get('negative_volume_values')}，剔除 confirm=0 {item.get('unclosed_rows')}。")
    lines.extend(['逐根间隔、缺口范围、拼接等式、输入 SHA-256 见 integrity.json / splice_check.json；有效窗口在 frozen_windows.tmp 中于运行前冻结。','', '## 命令、运行口径与限制','```powershell','python -B research/n1-2026-10-23/download.py','python -B research/n1-2026-10-23/run_n1.py','```','子进程命令与错误见 run.log / child_*.tmp；每行原始输出及随机状态见 row_*.json.tmp。JSON/CSV 收益为小数比例，报告转为 bps。','Bootstrap=50000；m=96；alpha=0.05；alpha/m=0.0005208333333333333；q_lo=0.0260416667；q_hi=99.9739583333；种子 20261021，单一随机流，性能样本先运行且计入 36 项，不重复。原始 family / 成本 / 分块算法未变。','峰值内存使用 Windows GetProcessMemoryInfo.PeakWorkingSetSize（进程峰值驻留集，不是整机内存）；单行 process_wall_seconds 包含子进程启动，elapsed_seconds 为子进程内加载至评估完成耗时。','原登记快照保留全部 60 条历史条目，并预登记 36 项；未完成项目的状态以结果表为准。','', '## 自检与 NOT_VERIFIED'])
    for r in rows:
        if r['status']!='COMPLETE':
            lines.append(f"- NOT_VERIFIED {r['id']}: window{r['window']} / {r['coin']} / {r['version']} / {r['horizon']}: {r.get('reason')}")
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    log('research_stopped',start_epoch=start,stop_epoch=stop,elapsed_seconds=stop-start,completed=completed,evaluated=evaluated,planned=36)

def selfcheck(rows):
    events=[json.loads(x) for x in (ROOT/'run.log').read_text(encoding='utf-8').splitlines()]
    expected=next(r['sha256'] for r in events if r['event']=='input_hashes')
    unchanged={p:sha(p)==digest for p,digest in expected.items()}
    snapshot=json.loads((ROOT/'registry_snapshot.json').read_text())
    original=json.loads((RESEARCH/'test_registry.json').read_text())
    checks=dict(input_hashes_unchanged=all(unchanged.values()),input_hash_details=unchanged,registry_count_96=len(snapshot)==96,original_60_preserved=len(original)==60 and all(snapshot.get(k)==v for k,v in original.items()),result_rows_36=len(rows)==36,unique_comparisons_36=len({(r['window'],r['coin'],r['version'],r['horizon']) for r in rows})==36,window_counts={w:sum(r['window']==w for r in rows) for w in (1,2)},no_pending=all(r['status']!='PENDING' for r in rows),parameters_correct=all(all(r[k]==v for k,v in PARAMS.items()) for r in rows),completed_before_deadline=time.time()<DEADLINE)
    tracked_diff=subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=RESEARCH.parent,text=True).splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=RESEARCH.parent,text=True).splitlines()
    checks.update(no_tracked_changes=not tracked_diff,untracked_only_n1=all(p.startswith('research/n1-2026-10-23/') for p in untracked),tracked_diff=tracked_diff)
    for w in (1,2):
        with (ROOT/f'results_window{w}.csv').open(encoding='utf-8-sig',newline='') as fh:
            csvrows=list(csv.DictReader(fh))
        checks[f'window{w}_csv_18_unique']=len(csvrows)==18 and len({r['id'] for r in csvrows})==18
    log('one_necessary_selfcheck',checks=checks)
    with (ROOT/'REPORT.md').open('a',encoding='utf-8') as fh:
        fh.write('\n仅执行一轮必要自检：\n```json\n'+json.dumps(checks,ensure_ascii=False,indent=2)+'\n```\n')
    log('artifacts_finalized',epoch_final=time.time())
    lines=['# SHA-256; sha256.txt itself excluded to avoid self-reference.']
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and p.name!='sha256.txt':
            lines.append(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}')
    for p in expected:
        lines.append(f'{sha(p)}  INPUT_READONLY {p}')
    tmp=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.tmp')]
    lines.append('# Temporary files retained intentionally as raw response / per-row / frozen-window evidence: '+str(len(tmp)))
    lines.extend('# TMP '+p for p in tmp)
    (ROOT/'sha256.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        worker(int(sys.argv[2]))
        return
    if '--wait-download' in sys.argv:
        while time.time()<DEADLINE:
            events=(ROOT/'run.log').read_text(encoding='utf-8').splitlines()
            if any('"event": "download_finished"' in line for line in events):
                break
            time.sleep(1)
        else:
            raise RuntimeError('DEADLINE_BEFORE_DOWNLOAD_FINISHED')
    if any((ROOT/f'results_window{w}.csv').exists() for w in (1,2)):
        raise RuntimeError('REFUSE_REPEATED_EVALUATION')
    log('evaluation_launcher',command=[sys.executable,'-B',*sys.argv],script_sha256=sha(__file__))
    rows=prepare()
    rows=evaluate_all(rows)
    report(rows)
    selfcheck(rows)

if __name__=='__main__':
    main()
