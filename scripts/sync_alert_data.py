#!/usr/bin/env python3
"""Mirror published JSON for ChatGPT's Cloudflare connector; never edit alert state."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_ID = '939edb81f78bc31df2f9b60b6223a0fb'
NAMESPACE_ID = 'd0d6feb3776c4dd79be67c789e4f0ceb'
SOURCE_FILES = {'daily_data': 'data.json', 'qdii_data': 'qdii.json'}
ALLOWED_KEYS = frozenset((*SOURCE_FILES, 'data_meta'))


def payload(output, revision):
    from verify_publication import verify_artifact
    output = Path(output)
    verify_artifact(output)
    entries, datasets = [], {}
    for key, name in SOURCE_FILES.items():
        raw = (output/name).read_bytes()
        parsed = json.loads(raw)
        entries.append({'key': key, 'value': raw.decode('utf-8')})
        datasets[key] = {'sha256': hashlib.sha256(raw).hexdigest(),
                         'date': parsed.get('date'), 'fetched_at': parsed.get('fetched_at')}
    meta = {'schema_version': 1, 'published_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'commit': revision, 'datasets': datasets}
    entries.append({'key': 'data_meta', 'value': json.dumps(meta, ensure_ascii=False)})
    if {item['key'] for item in entries} != ALLOWED_KEYS:
        raise ValueError('同步仅允许写入数据镜像，不能写入提醒状态')
    return entries


def publish(entries, token):
    if not token:
        raise ValueError('缺少 CLOUDFLARE_API_TOKEN')
    if {item['key'] for item in entries} != ALLOWED_KEYS:
        raise ValueError('拒绝覆盖提醒状态')
    request = urllib.request.Request(
        f'https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/bulk',
        data=json.dumps(entries, ensure_ascii=False).encode('utf-8'), method='PUT',
        headers={'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
            if not result.get('success'):
                raise RuntimeError('Cloudflare KV 写入未成功')
            return
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise RuntimeError('现有 Actions Token 缺少目标账户的 Workers KV Storage Edit 权限') from None
            if error.code != 429 and error.code < 500:
                raise RuntimeError(f'Cloudflare KV 返回 HTTP {error.code}') from None
            if attempt == 2:
                raise RuntimeError(f'Cloudflare KV 连续失败 HTTP {error.code}') from None
        except urllib.error.URLError:
            if attempt == 2:
                raise RuntimeError('Cloudflare KV 网络请求连续失败') from None
        time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    entries = payload(args.out, os.environ.get('GITHUB_SHA', 'local'))
    publish(entries, os.environ.get('CLOUDFLARE_API_TOKEN'))
    print('提醒数据已同步至 Cloudflare KV：daily_data、qdii_data、data_meta；未修改提醒基线与去重状态')


if __name__ == '__main__':
    main()
