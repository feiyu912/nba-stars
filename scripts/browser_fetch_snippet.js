/* 在 https://www.nba.com/stats/players/traditional 的 DevTools 控制台里跑这段代码。
 *
 * 为什么需要它: 本机只有"从 nba.com 页面里发起的 fetch"能访问 stats.nba.com
 * (直接打开接口地址、curl、python requests 都不通 —— 接口要求 Referer/x-nba-stats 头)。
 *
 * 前置: 先启动收集器
 *     python scripts/browser_collector.py --out /tmp/nba_fetch --port 8899
 * 用法: 把本文件内容粘进控制台回车。进度放在 window.__NBA_PROGRESS 里。
 * 取到的是 playercareerstats, 每个球员一次请求, 常规赛+季后赛+生涯总计都在里面。
 */
(() => {
  const COLLECTOR = 'http://localhost:8899/collect';
  const IDS = window.__NBA_IDS;               // 先执行: window.__NBA_IDS = [76003, 951, ...]
  if (!Array.isArray(IDS) || !IDS.length) {
    console.error('请先设置 window.__NBA_IDS = [...球员ID]');
    return;
  }

  const P = window.__NBA_PROGRESS = { done: 0, total: IDS.length, errors: [], startedAt: Date.now() };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  (async () => {
    for (const pid of IDS) {
      try {
        const r = await fetch(
          `https://stats.nba.com/stats/playercareerstats?PlayerID=${pid}&PerMode=PerGame&LeagueID=00`,
          { headers: { 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true' } },
        );
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j = await r.json();
        const p = await fetch(COLLECTOR, {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ player_id: String(pid), source: 'playercareerstats', data: j }),
        });
        if (!p.ok) throw new Error(`collector HTTP ${p.status}`);
      } catch (e) {
        P.errors.push(`${pid}: ${String(e).slice(0, 80)}`);
      }
      P.done += 1;
      await sleep(350);                        // 对官方接口客气一点, 别把人家惹毛
    }
    P.finished = true;
    console.log('完成:', P.done, '个, 失败', P.errors.length);
  })();

  console.log('已开始, 共', IDS.length, '个球员; 用 window.__NBA_PROGRESS 看进度');
})();