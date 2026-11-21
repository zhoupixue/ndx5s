#!/usr/bin/env python3
"""NYSE close gate, original engine runner and atomic export."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_site import load_report

def eligible(now):
    import pandas_market_calendars as mcal
    day=now.astimezone(ZoneInfo('America/New_York')).date()
    schedule=mcal.get_calendar('NYSE').schedule(start_date=day,end_date=day)
    if schedule.empty: return None
    close=schedule.iloc[0]['market_close'].to_pydatetime()
    return day if now >= close + dt.timedelta(minutes=15) else None

def catch_up_day(now, published_day):
    """Return the latest eligible NYSE session only when it has not been published."""
    import pandas_market_calendars as mcal

    day = now.astimezone(ZoneInfo('America/New_York')).date()
    schedule = mcal.get_calendar('NYSE').schedule(
        start_date=day - dt.timedelta(days=10), end_date=day
    )
    closed = schedule[schedule['market_close'] <= now - dt.timedelta(minutes=15)]
    if closed.empty:
        return None
    latest = closed.index[-1].date()
    return latest if published_day is None or published_day < latest else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate-only', action='store_true')
    parser.add_argument('--catch-up', action='store_true')
    parser.add_argument('--skip-build', action='store_true')
    a = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    if a.catch_up:
        report = ROOT/'reports/latest.html'
        published_day = dt.date.fromisoformat(load_report(report)['date']) if report.exists() else None
        day = catch_up_day(now, published_day)
    else:
        day = eligible(now)
    if a.gate_only:
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'eligible={str(day is not None).lower()}\n')
        print('交易日已收盘' if day else '非交易日或尚未到收盘后更新窗口');return
    if day is None:
        print('跳过：没有待补发的已收盘交易日' if a.catch_up else '跳过：非交易日或收盘未满十五分钟')
        return
    # Run entirely in staging, so data failure never overwrites last known good snapshot.
    import shutil,tempfile
    with tempfile.TemporaryDirectory(prefix='ndx5s-') as tmp:
        staging=Path(tmp);data=staging/'data';data.mkdir();snap=ROOT/'data/ndx_fwd_eps.csv'
        if snap.exists():shutil.copy2(snap,data/snap.name)
        subprocess.run([sys.executable,str(ROOT/'ndx5s_daily.py'),'--out',str(staging/'reports'),'--data',str(data)],check=True,timeout=2400)
        report=staging/'reports/latest.html';d=load_report(report)
        if d['date'] != str(day): raise ValueError(f'NDX 最新日期 {d["date"]} 不等于本交易日 {day}；保留上一版')
        from update_spx import fetch_spx
        fetch_spx(d['date'],data/'spx_close.json')
        d['generated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
        text=report.read_text();import re
        text=re.sub(r'const D=.*?;\s*const \$',lambda m:'const D='+json.dumps(d,ensure_ascii=False,allow_nan=False).replace('</','<\\/')+';\nconst $',text,count=1,flags=re.S)
        report.write_text(text)
        (ROOT/'reports').mkdir(exist_ok=True)
        shutil.copy2(report,ROOT/'reports/latest.html')
        shutil.copy2(report,ROOT/'reports'/f'ndx5s_daily_{day}.html')
        if (data/snap.name).exists():shutil.copy2(data/snap.name,snap)
        shutil.copy2(data/'spx_close.json',ROOT/'data/spx_close.json')
    if not a.skip_build:
        subprocess.run([sys.executable,str(ROOT/'scripts/build_site.py')],check=True)
if __name__=='__main__':main()
