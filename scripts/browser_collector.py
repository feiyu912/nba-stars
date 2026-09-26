"""浏览器取数的本地收集器。

背景: 本机 stats.nba.com 只有"从 nba.com 页面里发起的 fetch"能通
(直接访问、curl、python requests 都不行 —— 接口要求 Referer/x-nba-stats 头)。
所以取数流程是: 浏览器页面 fetch → POST 到本收集器 → 落盘成 JSON。

用法:
  1. python scripts/browser_collector.py --out /tmp/nba_fetch --port 8899
  2. 在 https://www.nba.com/stats/players/traditional 页面的控制台里跑
     scripts/browser_fetch_snippet.js 里的代码
  3. 数据落在 --out 目录, 每个球员一个 <player_id>.json
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ARGS = argparse.ArgumentParser()
ARGS.add_argument("--out", default="/tmp/nba_fetch")
ARGS.add_argument("--port", type=int, default=8899)
OPTS = ARGS.parse_args()
OUT = Path(OPTS.out)
OUT.mkdir(parents=True, exist_ok=True)


class Collector(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._cors()

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            pid = str(payload["player_id"])
            (OUT / f"{pid}.json").write_text(json.dumps(payload, ensure_ascii=False))
            n = len(list(OUT.glob("*.json")))
            print(f"  收集 {pid}  (累计 {n} 个)", flush=True)
            body = json.dumps({"ok": True, "collected": n}).encode()
        except Exception as exc:  # 不静默: 打印失败原因
            print(f"  收集失败: {type(exc).__name__}: {exc}", flush=True)
            body = json.dumps({"ok": False, "error": str(exc)}).encode()
        self._cors()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # 关掉默认的每请求日志, 太吵
        pass


if __name__ == "__main__":
    print(f"收集器已启动: http://localhost:{OPTS.port}/collect  ->  {OUT}")
    ThreadingHTTPServer(("127.0.0.1", OPTS.port), Collector).serve_forever()
