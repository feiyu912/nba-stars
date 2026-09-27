/* NBA Player Analysis — 静态站 (无依赖、无构建)
 * 数据: data.js (window.NBA_DATA) · 图表: 手写 SVG · 语言切换 = 整页重渲染
 * 交互: 表头点击排序、悬停自定义 tooltip、球员筛选
 */
'use strict';

const D = window.NBA_DATA;
const BY = Object.fromEntries(D.players.map((p) => [p.name, p]));
const DIMS = ['scoring', 'impact', 'playmaking', 'defense', 'rebounding'];
const HUE = { scoring: 'var(--scoring)', impact: 'var(--impact)', playmaking: 'var(--playmaking)',
  defense: 'var(--defense)', rebounding: 'var(--rebounding)' };
// 每个维度参与排名的人数 (百分位用)
const RANKED_N = Object.fromEntries(DIMS.map((d) => [d, D.players.filter((p) => p[d] !== null && p[d] !== undefined).length]));
['stl_rank', 'blk_rank', 'oreb_rank', 'dreb_rank'].forEach((k) => {
  DIMS.push(k); RANKED_N[k] = D.players.filter((p) => p[k] !== null && p[k] !== undefined).length; DIMS.pop();
});

// ══════════════ 文案 ══════════════
const I18N = {
  en: {
    brand: 'NBA Player Analysis', brandSub: 'era-adjusted · 101 players',
    g_rank: 'Rankings', g_explore: 'Explore', g_about: 'About',
    n_overview: 'Overview', n_scoring: 'Scoring', n_playmaking: 'Playmaking',
    n_defense: 'Defense', n_rebounding: 'Rebounding', n_impact: 'Impact',
    n_compare: 'Playoff & cross-dim', n_players: 'Player profile', n_data: 'Data & method',
    k_players: 'Players', k_span: 'Seasons covered', k_dims: 'Dimensions', k_verified: 'Verified',
    k_verified_sub: 'vs primary source',
    top5: 'Leaders by dimension', sec_all: 'All dimensions',
    integrity: 'Steals/blocks and the offensive/defensive rebound split start in 1973-74, turnovers in 1977-78. Missing values are shown as — and the affected players are excluded from that ranking rather than estimated.',
    l_scoring: 'Points per game (free throws discounted 0.7x, pace-adjusted) × efficiency relative to the era × scarcity, combined with a per-minute view. Every playoff game counts 3x.',
    l_impact: 'Ridge regression on O-DPM (third-party proxy target) using era-adjusted Z-scores. O-DPM is a proxy, not ground truth.',
    l_playmaking: 'Assists per game (pace-adjusted) × assist-to-turnover ratio × scarcity, independent of scoring.',
    l_defense: 'Steals + blocks, pace-adjusted, with era scarcity and playoff-experience bonuses.',
    l_rebounding: 'Total rebounds per game, pace-adjusted, with an era scarcity bonus.',
    l_compare: 'Who raises his game when it matters, and how the dimensions line up.',
    l_players: 'Career curve, dimension ranks and scoring structure for every player.',
    l_data: 'Where the numbers come from, and what they cannot tell you.',
    s_leaders: 'Leaderboard', s_dist: 'Where the field sits', s_scatter: 'Production vs efficiency',
    s_split: 'Scoring structure', s_table: 'Full table', s_stlblk: 'Steals vs blocks',
    s_dimpact: 'Defensive impact', s_po: 'Playoff vs regular season', s_cross: 'Cross-dimension ranks',
    s_curve: 'Career curve', s_radar: 'Dimension profile',
    c_rank: 'Rank', c_player: 'Player', c_ppg: 'PPG', c_rpg: 'RPG', c_apg: 'APG', c_ts: 'TS%',
    c_gp: 'GP', c_seasons: 'Seasons', c_span: 'Career', c_pct: 'Pctl', c_ft: 'FT%',
    c_stl: 'STL', c_blk: 'BLK', c_def: 'STL+BLK', c_sample: 'Seasons', c_peak_orb: 'Peak ORB',
    c_peak_drb: 'Peak DRB', c_reg: 'Regular', c_po: 'Playoffs', c_change: 'Δ', c_po_gp: 'PO GP',
    c_pred: 'Model', c_actual: 'D-DPM', c_curve: 'Curve', c_orb: 'ORB', c_drb: 'DRB',
    t_note_stlblk: 'Steals measure perimeter anticipation, blocks measure rim protection. Combined into one number a guard\'s steals and a centre\'s blocks cancel out, so they are ranked separately.',
    t_note_play: 'Turnovers were not recorded before 1977-78. For players whose careers began earlier the AST/TOV ratio is estimated from a league-average turnover count and tagged — never silently filled.',
    t_note_dimpact: 'Model quality: 53 training players, 5-fold cross-validated R² = 0.359, Spearman = 0.667. Players without steals/blocks data are not predicted.',
    t_excl_nodata: '{n} players are not ranked — their careers ended before 1973-74, so no steals or blocks exist.',
    t_excl_thin: '{n} more have fewer than 5 seasons of defensive data, too few for a 5-year peak window.',
    t_reb_split: '{n} players have no offensive/defensive rebound split (careers before 1973-74); their total-rebound rank is unaffected.',
    tag_est: 'EST', tag_nodef: 'N/A',
    search: 'Search player…', ver: 'Verification', ver_i: 'Every row was re-fetched from the NBA.com API and compared field by field.',
    ver_reg: 'Regular season', ver_po: 'Playoffs', ver_pre: 'Playoff rows before 2003',
    ver_rows: 'Rows', ver_match: 'Match', ver_src: 'Primary source', ver_br: 'vs Basketball-Reference',
    ver_built: 'Built', lim: 'Known limitations', method: 'Methodology',
    method_body: 'Two views per dimension (per-game and per-minute, both era-adjusted); peak-5-season average weighted 0.6 against career average 0.4; playoff games weighted 3x; then the median rank across the two views.',
    repo: 'Source & full documentation', sort_hint: 'Click a column header to sort',
    lim_items: [
      'Early-era players are not comparable to modern ones. Steals/blocks and the rebound split start in 1973-74, turnovers in 1977-78; affected players are excluded rather than estimated.',
      'AST/TOV for the 19 players whose careers began before 1977-78 is estimated. Replacing that estimate with a neutral multiplier moves 92 of 101 players — Oscar Robertson falls from #6 to #36. This is the last estimated input in the project.',
      'O-DPM and D-DPM come from a third party and are themselves estimates; the ridge R² measures how well box scores reproduce that metric, not true impact.',
      'Scarcity and era Z-scores compare a player to this 101-player pool, not the whole league — the pool skews toward all-time greats.',
      'Multi-team seasons count the combined row only, so per-team splits are not available.',
      'No ABA data: Julius Erving and Malone are NBA-only here.',
    ],
  },
  zh: {
    brand: 'NBA 球员分析', brandSub: '时代修正 · 101 名球员',
    g_rank: '排名', g_explore: '探索', g_about: '关于',
    n_overview: '总览', n_scoring: '得分', n_playmaking: '组织',
    n_defense: '防守', n_rebounding: '篮板', n_impact: '影响力',
    n_compare: '季后赛与跨维度', n_players: '球员画像', n_data: '数据与方法',
    k_players: '球员', k_span: '覆盖赛季', k_dims: '维度', k_verified: '校验一致率',
    k_verified_sub: '对照一手数据源',
    top5: '各维度领跑者', sec_all: '全部维度',
    integrity: '抢断/盖帽与进攻/防守篮板拆分始于 1973-74 赛季，失误始于 1977-78 赛季。缺失值显示为 —，相关球员从该维度排除，不做估算填充。',
    l_scoring: '场均得分（罚球按 0.7 折算、节奏修正）× 相对效率 × 稀缺度，再与每分钟视角合并。每场季后赛按 3 场常规赛计算。',
    l_impact: '用岭回归拟合 O-DPM（第三方代理指标），特征为时代修正后的 Z 分数。O-DPM 是代理指标，不是真值。',
    l_playmaking: '场均助攻（节奏修正）× 助攻失误比 × 稀缺度，与得分完全独立。',
    l_defense: '抢断 + 盖帽，节奏修正，叠加时代稀缺度与季后赛经验加成。',
    l_rebounding: '场均总篮板，节奏修正，叠加时代稀缺度加成。',
    l_compare: '谁在关键时刻更强，以及各维度之间的横向关系。',
    l_players: '每名球员的生涯曲线、各维度名次与得分结构。',
    l_data: '数据从哪来，以及它回答不了什么。',
    s_leaders: '排行榜', s_dist: '所有人分布在哪', s_scatter: '产量与效率',
    s_split: '得分结构', s_table: '完整表格', s_stlblk: '抢断与盖帽',
    s_dimpact: '防守影响力', s_po: '季后赛与常规赛', s_cross: '跨维度名次',
    s_curve: '生涯曲线', s_radar: '维度画像',
    c_rank: '名次', c_player: '球员', c_ppg: '场均得分', c_rpg: '场均篮板', c_apg: '场均助攻',
    c_ts: '真实命中率', c_gp: '出场', c_seasons: '赛季数', c_span: '生涯', c_pct: '百分位', c_ft: '罚球占比',
    c_stl: '抢断', c_blk: '盖帽', c_def: '抢断+盖帽', c_sample: '有效赛季', c_peak_orb: '巅峰进攻篮板',
    c_peak_drb: '巅峰防守篮板', c_reg: '常规赛', c_po: '季后赛', c_change: '变化', c_po_gp: '季后赛出场',
    c_pred: '模型预测', c_actual: '实际 D-DPM', c_curve: '生涯曲线', c_orb: '进攻篮板', c_drb: '防守篮板',
    t_note_stlblk: '抢断体现外线预判，盖帽体现护框。合成一项会让后卫的抢断和中锋的盖帽互相抵消，所以分开排名。',
    t_note_play: '1977-78 赛季之前不记录失误。生涯开始于那时的球员，助失比是用联盟平均失误数估算的，已打标记 —— 不做静默填充。',
    t_note_dimpact: '模型质量：训练样本 53 人，5 折交叉验证 R² = 0.359，Spearman = 0.667。没有抢断/盖帽数据的球员不参与预测。',
    t_excl_nodata: '{n} 人不参与排名 —— 他们的生涯在 1973-74 之前结束，没有任何抢断/盖帽记录。',
    t_excl_thin: '另有 {n} 人有效赛季不足 5 个，样本撑不起 5 年巅峰窗口。',
    t_reb_split: '{n} 人没有进攻/防守篮板拆分（生涯在 1973-74 之前）；他们的总篮板名次不受影响。',
    tag_est: '估算', tag_nodef: '无数据',
    search: '搜索球员…', ver: '数据校验', ver_i: '每一行都从 NBA.com 接口重新取回并逐字段比对。',
    ver_reg: '常规赛', ver_po: '季后赛', ver_pre: '2003 年前的季后赛行',
    ver_rows: '行数', ver_match: '一致率', ver_src: '一手数据源', ver_br: '对照 Basketball-Reference',
    ver_built: '构建于', lim: '已知局限', method: '方法论',
    method_body: '每个维度两个视角（场均与每分钟，均做时代修正）；巅峰 5 年均值按 0.6、生涯均值按 0.4 加权；季后赛按 3 倍计入；最后取两个视角名次的中位数。',
    repo: '源码与完整文档', sort_hint: '点击表头排序',
    lim_items: [
      '早期球员与现代不可直接比较。抢断/盖帽与篮板拆分始于 1973-74，失误始于 1977-78；受影响的球员一律排除，不做估算。',
      '生涯开始于 1977-78 之前的 19 人，助失比是估算值。把估算换成中性乘数会让 101 人里的 92 人名次变动 —— Oscar Robertson 会从 #6 掉到 #36。这是项目里最后一处估算输入。',
      'O-DPM 与 D-DPM 来自第三方，本身也是估计值；岭回归的 R² 衡量的是「基础数据能多大程度复现该指标」，不代表真实影响力。',
      '稀缺度与时代 Z 分数的比较基准是这 101 人池，不是全联盟 —— 池子偏向历史级球星。',
      '多队赛季只计合并数据，因此拿不到「交易前在 A 队打得如何」这类拆分。',
      '不含 ABA 数据：Julius Erving 与 Malone 在这里只有 NBA 部分。',
    ],
  },
};
let lang = localStorage.getItem('nba_lang') || 'en';
const t = (k) => I18N[lang][k];
const fmt = (v, d = 1) => (v === null || v === undefined ? '—' : Number(v).toFixed(d));
const int = (v) => (v === null || v === undefined ? '—' : String(Math.round(v)));
const pct = (rank, dim) => (rank === null || rank === undefined ? null
  : Math.max(6, Math.round((1 - (rank - 1) / Math.max(1, RANKED_N[dim] - 1)) * 100)));

// ══════════════ DOM ══════════════
const NS = 'http://www.w3.org/2000/svg';
function h(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  n.append(...kids.filter((x) => x !== null && x !== undefined && x !== false));
  return n;
}
function s(tag, attrs = {}, ...kids) {
  const n = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) n.setAttribute(k, v);
  n.append(...kids.filter((x) => x !== null && x !== undefined));
  return n;
}

let TIP;
function tip(node, html) {
  if (!TIP) { TIP = h('div', { id: 'tip' }); document.body.append(TIP); }
  const show = (e) => {
    TIP.innerHTML = html;
    TIP.style.opacity = 1;
    const w = 270;
    TIP.style.left = `${Math.min(e.clientX + 14, window.innerWidth - w)}px`;
    TIP.style.top = `${Math.min(e.clientY + 16, window.innerHeight - 120)}px`;
  };
  node.addEventListener('mouseenter', show);
  node.addEventListener('mousemove', show);
  node.addEventListener('mouseleave', () => { TIP.style.opacity = 0; });
  return node;
}
const tipRows = (title, rows) => `<div class="tip-t">${title}</div>`
  + rows.map(([k, v]) => `<div class="tip-r"><span>${k}</span><b>${v}</b></div>`).join('');

// ══════════════ 通用零件 ══════════════
function rankCell(rank) {
  if (rank === null || rank === undefined) return h('span', { class: 'rank na' }, '—');
  const r = Math.round(rank);
  return h('span', { class: `rank${r <= 3 ? ` t${r}` : ''}` }, String(r));
}
function badge(p) {
  return h('span', { class: 'badge', style: `--tc:${p.teamColor}`, title: p.team },
    p.team || '—');
}
function pctCell(value, dim, digits = 1) {
  const p = pct(value, dim);
  return h('span', { class: 'pct-cell' },
    h('span', { class: 'pct', style: 'width:44px' },
      h('i', { style: `width:${p === null ? 0 : p}%;--pc:${HUE[dim] || 'var(--accent)'}` })),
    h('span', { class: 'v' }, p === null ? '—' : String(p)));
}
function tags(p, dim) {
  const out = [];
  if (dim === 'defense' && p.def_excluded) out.push(h('span', { class: 'tag' }, t('tag_nodef')));
  if (dim === 'playmaking' && p.tov_estimated) out.push(h('span', { class: 'tag w' }, t('tag_est')));
  return out;
}

/** 迷你生涯曲线: 排行榜里一眼看出是"巅峰型"还是"长青型" */
function spark(name, color, key = 'ppg') {
  const c = D.curves[name];
  if (!c) return h('span', { class: 'v' }, '—');
  const vals = c[key].filter((v) => v !== null);
  if (vals.length < 3) return h('span', { class: 'v' }, '—');
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const VW = 64, VH = 18;
  const X = (i) => (i / Math.max(1, c[key].length - 1)) * VW;
  const Y = (v) => VH - 2 - vscale(v, lo, hi || 1, VH - 5);
  const pts = c[key].map((v, i) => (v === null ? null : `${X(i).toFixed(1)},${Y(v).toFixed(1)}`))
    .filter(Boolean).join(' ');
  const g = s('svg', { width: VW, height: VH, viewBox: `0 0 ${VW} ${VH}`, 'aria-hidden': 'true',
    style: 'display:block;overflow:visible' },
  s('polyline', { points: pts, fill: 'none', stroke: color, 'stroke-width': 1.4,
    'stroke-linejoin': 'round', opacity: 0.85 }));
  const peak = vals.indexOf(Math.max(...vals));
  g.append(s('circle', { cx: X(peak), cy: Y(vals[peak]), r: 1.7, fill: color }));
  return tip(g, tipRows(name, [[t('c_' + key) + ' 峰值', fmt(vals[peak], key === 'ts' ? 3 : 1)],
    [t('c_span'), `${c.season[0]}–${c.season[c.season.length - 1]}`]]));
}

/** 排行榜: 名次 | 队徽 | 姓名 | 生涯曲线 | 主值 | 次值 */
function board(rows, { dim, valueKey, digits = 1, altKey = null, altDigits = 1, unit = '' }) {
  return h('div', { class: 'board' },
    h('div', { class: 'board-head' },
      h('span', {}, t('c_rank')), h('span', {}, ''), h('span', {}, t('c_player')),
      h('span', {}, t('c_curve')), h('span', {}, t('c_' + valueKey) || valueKey),
      h('span', {}, altKey ? t('c_' + altKey) || altKey : '')),
    ...rows.map((p) => h('div', { class: 'board-row' },
      rankCell(p[dim]),
      badge(p),
      h('span', { class: 'nm' }, h('span', { class: 'who' }, p.name), ...tags(p, dim),
        h('span', { class: 'meta' }, `${p.first.slice(2, 4)}–${p.last.slice(2, 4)}`)),
      h('span', { style: 'display:flex;justify-content:flex-end' }, spark(p.name, HUE[dim], dim === 'playmaking' ? 'ppg' : 'ppg')),
      h('span', { class: 'v', style: `color:${HUE[dim]}` }, fmt(p[valueKey], digits) + unit),
      h('span', { class: 'v', style: 'color:var(--text-3)' },
        altKey ? fmt(p[altKey], altDigits) : ''))));
}

/** 可排序表格: 点表头排序, 前两列固定 */
function dtable(cols, rows, { defaultSort = null } = {}) {
  let sortKey = defaultSort, asc = true;
  const wrap = h('div', { class: 'tw' });
  const render = () => {
    const sorted = [...rows];
    if (sortKey) {
      sorted.sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return asc ? (x > y ? 1 : x < y ? -1 : 0) : (x < y ? 1 : x > y ? -1 : 0);
      });
    }
    wrap.replaceChildren(h('table', {},
      h('thead', {}, h('tr', {}, ...cols.map((c, i) => h('th', {
        class: `${c.align === 'l' ? 'l' : ''} ${i === 0 ? 'c1' : i === 1 ? 'c2' : ''} ${sortKey === c.key ? `sorted${asc ? ' asc' : ''}` : ''}`,
        title: t('sort_hint'),
        onclick: () => { if (sortKey === c.key) asc = !asc; else { sortKey = c.key; asc = c.asc !== false; } render(); },
      }, c.label)))),
      h('tbody', {}, ...sorted.map((r) => h('tr', {}, ...cols.map((c, i) => h('td', {
        class: `${c.align === 'l' ? 'l' : 'n'} ${i === 0 ? 'c1' : i === 1 ? 'c2' : ''}`,
      }, c.render ? c.render(r)
        : (typeof r[c.key] === 'number' ? (c.digits === 0 ? int(r[c.key]) : fmt(r[c.key], c.digits))
          : (r[c.key] ?? '—')))))))));
  };
  render();
  return wrap;
}

// ══════════════ 图表 ══════════════
const W = 900;
const vscale = (v, lo, hi, out) => (v - lo) / (hi - lo || 1) * out;

/** 点分布图: 每个球员一个点 + 直接标注头部几人 (取代 25 条横条) */
function dotStrip(rows, { dim, valueKey, color, labelTop = 6, digits = 1, unit = '' }) {
  const H = 108, pad = 30;
  const vals = rows.map((r) => r[valueKey]);
  const lo = Math.min(...vals) * 0.94, hi = Math.max(...vals) * 1.02;
  const x = (v) => pad + vscale(v, lo, hi, W - pad * 2);
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': t('s_dist') });
  // 轴 + 刻度
  g.append(s('line', { class: 'gl', x1: pad, x2: W - pad, y1: H - 26, y2: H - 26 }));
  for (let i = 0; i <= 4; i++) {
    const v = lo + (hi - lo) * i / 4;
    g.append(s('text', { class: 'ax', x: x(v), y: H - 12, 'text-anchor': 'middle' }, fmt(v, digits) + unit));
  }
  // 点: y 抖动避免重叠, 中位数一线为基准
  const mid = H / 2 - 8;
  const jitter = (i, n) => ((i % 7) - 3) * 3.2;
  rows.forEach((r, i) => {
    const cx = x(r[valueKey]), cy = mid + jitter(i, rows.length);
    g.append(tip(s('circle', { class: 'dot', cx, cy, r: 4, fill: color,
      opacity: i < 10 ? 0.95 : 0.45 }), tipRows(r.name,
      [[t('c_rank') + ' / ' + .0, Math.round(r[dim])], [t('c_' + valueKey) || valueKey, fmt(r[valueKey], digits)],
        [t('c_span'), `${r.first}–${r.last}`], ['Team', `${r.team} · ${r.seasons} ${t('c_seasons')}`]])));
  });
  // 标注头部
  rows.slice(0, labelTop).forEach((r) => {
    const cx = x(r[valueKey]);
    g.append(s('text', { class: 'dt', x: cx, y: H - 46, 'text-anchor': cx > W - 90 ? 'end' : cx < 90 ? 'start' : 'middle' },
      r.name.split(' ').slice(-1)[0]));
    g.append(s('line', { class: 'gl dash', x1: cx, x2: cx, y1: H - 42, y2: mid - 6 }));
  });
  return g;
}

/** 堆叠条: 得分结构 */
function splitChart(rows) {
  const H = rows.length * 26 + 34, pad = 30, nameW = 190;
  const x0 = pad + nameW, w = W - x0 - pad;
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img' });
  const segs = [['split2', HUE.scoring, '2P'], ['split3', HUE.impact, '3P'], ['splitFt', 'var(--text-4)', 'FT']];
  g.append(s('text', { class: 'ax', x: W - pad, y: 12, 'text-anchor': 'end' },
    '2P / 3P / FT'));
  rows.forEach((p, i) => {
    const y = 22 + i * 26;
    g.append(s('text', { class: 'dl', x: pad, y: y + 11 }, p.name));
    g.append(s('text', { class: 'dv', x: x0 - 8, y: y + 11, 'text-anchor': 'end' }, `${fmt(p.splitFt, 0)}%`));
    let cx = x0;
    segs.forEach(([k, c, lab]) => {
      const ww = (p[k] / 100) * w;
      if (ww > 0) g.append(tip(s('rect', { x: cx, y, width: ww, height: 13, fill: c, opacity: 0.9 }),
        tipRows(p.name, [[lab, `${fmt(p[k], 1)}%`], [t('c_ppg'), fmt(p.ppg)]])));
      cx += ww;
    });
  });
  return g;
}

/** 散点: 产量 vs 效率, 带中位线 */
function scatter(rows) {
  const H = 430, m = { t: 18, r: 20, b: 42, l: 54 };
  const xs = rows.map((r) => r.ppg), ys = rows.map((r) => r.ts);
  const x0 = Math.min(...xs) - 1, x1 = Math.max(...xs) + 1;
  const y0 = Math.min(...ys) - 0.008, y1 = Math.max(...ys) + 0.008;
  const X = (v) => m.l + vscale(v, x0, x1, W - m.l - m.r);
  const Y = (v) => H - m.b - vscale(v, y0, y1, H - m.t - m.b);
  const med = (a) => { const q = [...a].sort((p, n) => p - n); return q[Math.floor(q.length / 2)]; };
  const mx = med(xs), my = med(ys);
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img' });
  for (let i = 0; i <= 4; i++) {
    const v = y0 + (y1 - y0) * i / 4;
    g.append(s('line', { class: 'gl', x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
    g.append(s('text', { class: 'ax', x: m.l - 8, y: Y(v) + 3, 'text-anchor': 'end' }, fmt(v, 3)));
  }
  for (let i = 0; i <= 5; i++) {
    const v = x0 + (x1 - x0) * i / 5;
    g.append(s('text', { class: 'ax', x: X(v), y: H - m.b + 15, 'text-anchor': 'middle' }, fmt(v, 0)));
  }
  g.append(s('line', { class: 'gl dash', x1: X(mx), x2: X(mx), y1: m.t, y2: H - m.b }));
  g.append(s('line', { class: 'gl dash', x1: m.l, x2: W - m.r, y1: Y(my), y2: Y(my) }));
  g.append(s('text', { class: 'ax', x: W - m.r, y: m.t + 2, 'text-anchor': 'end' },
    `${t('c_ts')} ↑   ${t('c_ppg')} →`));
  const note = new Set([...rows].sort((a, b) => b.ts - a.ts).slice(0, 6)
    .concat([...rows].sort((a, b) => b.ppg - a.ppg).slice(0, 5)).map((p) => p.name));
  rows.forEach((p) => {
    const top = p.scoring <= 10;
    g.append(tip(s('circle', { class: 'dot', cx: X(p.ppg), cy: Y(p.ts), r: top ? 5.5 : 4,
      fill: top ? HUE.scoring : HUE.impact, opacity: note.has(p.name) || top ? 0.95 : 0.42 }),
    tipRows(p.name, [[t('c_ppg'), fmt(p.ppg)], [t('c_ts'), fmt(p.ts, 3)],
      [t('n_scoring') + ' #', int(p.scoring)], [t('c_span'), `${p.first}–${p.last}`]])));
  });
  note.forEach((p) => g.append(s('text', { class: 'dt', x: X(BY[p].ppg) + 9, y: Y(BY[p].ts) + 3 },
    p.split(' ').slice(-1)[0])));
  return g;
}

/** 哑铃: 季后赛 vs 常规赛 */
function dumbbell(rows, { aKey, bKey, digits = 1 }) {
  const H = rows.length * 26 + 30, pad = 26, nameW = 175, valW = 96;
  const vals = rows.flatMap((r) => [r[aKey], r[bKey]]).filter((v) => v !== null);
  const lo = Math.min(...vals) - 1, hi = Math.max(...vals) + 1;
  const x0 = pad + nameW, x1 = W - valW;
  const X = (v) => x0 + vscale(v, lo, hi, x1 - x0);
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img' });
  g.append(s('text', { class: 'ax', x: W - pad, y: 11, 'text-anchor': 'end' }, `${t('c_reg')} ●—●  ${t('c_po')}`));
  rows.forEach((p, i) => {
    const y = 22 + i * 26, mid = y + 6;
    const up = p[bKey] >= p[aKey];
    g.append(s('text', { class: 'dl', x: pad, y: mid + 4 }, p.name));
    g.append(s('line', { x1: X(p[aKey]), x2: X(p[bKey]), y1: mid, y2: mid, stroke: 'var(--line)', 'stroke-width': 2 }));
    g.append(tip(s('circle', { cx: X(p[aKey]), cy: mid, r: 3.6, fill: 'var(--text-4)' }),
      tipRows(p.name, [[t('c_reg'), fmt(p[aKey], digits)], [t('c_po'), fmt(p[bKey], digits)]])));
    g.append(tip(s('circle', { cx: X(p[bKey]), cy: mid, r: 4.4, fill: up ? 'var(--up)' : 'var(--down)' }),
      tipRows(p.name, [[t('c_reg'), fmt(p[aKey], digits)], [t('c_po'), fmt(p[bKey], digits)],
        [t('c_change'), `${up ? '+' : ''}${fmt(p[bKey] - p[aKey], digits)}`]])));
    g.append(s('text', { class: 'dv', x: W - pad, y: mid + 4, 'text-anchor': 'end',
      fill: up ? 'var(--up)' : 'var(--down)' },
    `${up ? '+' : ''}${fmt(p[bKey] - p[aKey], digits)}`));
  });
  return g;
}

/** 生涯曲线 (窄容器里用, viewBox 直接按容器宽度定, 免得被缩放成蚂蚁字) */
function curve(p, key = 'ppg') {
  const c = D.curves[p.name];
  const W = 470, H = 200, m = { t: 14, r: 16, b: 26, l: 40 };
  const vals = c[key].filter((v) => v !== null);
  const lo = Math.min(...vals) * 0.88, hi = Math.max(...vals) * 1.06;
  const X = (i) => m.l + (i / Math.max(1, c.season.length - 1)) * (W - m.l - m.r);
  const Y = (v) => H - m.b - vscale(v, lo, hi, H - m.t - m.b);
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${W} ${H}`, role: 'img' });
  for (let i = 0; i <= 3; i++) {
    const v = lo + (hi - lo) * i / 3;
    g.append(s('line', { class: 'gl', x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v) }));
    g.append(s('text', { class: 'ax', x: m.l - 8, y: Y(v) + 3, 'text-anchor': 'end' }, fmt(v, 1)));
  }
  const pts = c[key].map((v, i) => (v === null ? null : `${X(i)},${Y(v)}`)).filter(Boolean);
  g.append(s('polyline', { points: pts.join(' '), fill: 'none', stroke: HUE.scoring, 'stroke-width': 2 }));
  c[key].forEach((v, i) => {
    if (v === null) return;
    g.append(tip(s('circle', { cx: X(i), cy: Y(v), r: 3, fill: HUE.scoring }),
      tipRows(`${c.season[i]} · ${c.team[i]}`, [[t('c_ppg'), fmt(v)], [t('c_ts'), fmt(c.ts[i], 3)]])));
  });
  [0, c.season.length - 1].forEach((i) => g.append(s('text', { class: 'ax', x: X(i), y: H - 8,
    'text-anchor': i === 0 ? 'start' : 'end' }, c.season[i])));
  return g;
}

/** 雷达: 五个维度名次 */
function radar(p) {
  const S = 300, c = S / 2, R = 92;
  const dims = DIMS.slice(0, 5).map((d) => ({ d, rank: p[d] }));
  const ang = (i) => -Math.PI / 2 + i * 2 * Math.PI / dims.length;
  const rad = (rk) => (rk === null || rk === undefined ? 0 : (1 - (rk - 1) / 100) * R);
  const g = s('svg', { class: 'chart', viewBox: `0 0 ${S} ${S}`, role: 'img', style: 'max-width:330px' });
  [0.25, 0.5, 0.75, 1].forEach((f) => g.append(s('polygon', { class: 'gl',
    points: dims.map((_, i) => `${c + Math.cos(ang(i)) * R * f},${c + Math.sin(ang(i)) * R * f}`).join(' ') })));
  dims.forEach((_, i) => g.append(s('line', { class: 'gl', x1: c, y1: c,
    x2: c + Math.cos(ang(i)) * R, y2: c + Math.sin(ang(i)) * R })));
  g.append(s('polygon', { fill: 'var(--accent)', opacity: 0.16, stroke: 'var(--accent)', 'stroke-width': 2,
    points: dims.map((d, i) => `${c + Math.cos(ang(i)) * rad(d.rank)},${c + Math.sin(ang(i)) * rad(d.rank)}`).join(' ') }));
  dims.forEach((d, i) => {
    const lx = c + Math.cos(ang(i)) * (R + 24), ly = c + Math.sin(ang(i)) * (R + 24);
    g.append(s('text', { class: 'ax', x: lx, y: ly - 2, 'text-anchor': 'middle', fill: HUE[d.d] }, t('n_' + d.d)));
    g.append(s('text', { class: 'dv', x: lx, y: ly + 12, 'text-anchor': 'middle' },
      d.rank === null ? '—' : `#${Math.round(d.rank)}`));
  });
  return g;
}

// ══════════════ 视图 ══════════════
const rankedBy = (dim, n) => D.players.filter((p) => p[dim] !== null && p[dim] !== undefined)
  .sort((a, b) => a[dim] - b[dim]).slice(0, n);
const head = (title, lede) => h('div', { class: 'head' },
  h('div', { class: 'eyebrow' }, t('brand')), h('h2', {}, title), lede ? h('p', {}, lede) : null);
const sec = (title, ...body) => h('section', { class: 'sec' },
  h('div', { class: 'eyebrow' }, title), ...body);
const chartCard = (title, svg) => h('div', { class: 'chart-card' },
  h('div', { class: 'eyebrow' }, title), svg);

const VIEWS = {
  overview() {
    const span = D.players.reduce((a, p) => [Math.min(a[0], +p.first.slice(0, 4)),
      Math.max(a[1], +p.last.slice(0, 4))], [9999, 0]);
    const m = D.meta;
    const cards = [
      [t('k_players'), String(m.players), `${span[0]}–${span[1]}`],
      [t('k_dims'), String(5), t('brandSub')],
      [t('ver_rows'), String(m.regular_rows + m.playoff_rows), `${m.regular_rows} + ${m.playoff_rows}`],
      [t('k_verified'), m.primary_match, t('k_verified_sub')],
    ];
    return [
      head(t('n_overview'), t('integrity')),
      h('div', { class: 'grid g4' }, ...cards.map(([l, v, sub]) => h('div', { class: 'card' },
        h('div', { class: 'kpi-l' }, l), h('div', { class: 'kpi-v' }, v), h('div', { class: 'kpi-s' }, sub)))),
      sec(t('top5'), h('div', { class: 'grid g3' }, ...DIMS.slice(0, 5).map((d) => h('div', { class: 'card' },
        h('div', { class: 'kpi-l', style: `color:${HUE[d]}` }, t('n_' + d)),
        ...rankedBy(d, 5).map((p) => h('div', { style: 'display:flex;align-items:center;gap:8px;margin-top:7px' },
          rankCell(p[d]), badge(p), h('span', { style: 'font-size:12.5px' }, p.name),
          h('span', { class: 'v', style: 'margin-left:auto;color:var(--text-3);font-size:11.5px' },
            d === 'playmaking' ? `${fmt(p.apg)} APG` : d === 'rebounding' ? `${fmt(p.rpg)} RPG` : `${fmt(p.ppg)} PPG`))))))),
    ];
  },

  scoring() {
    const rows = rankedBy('scoring', 25);
    return [
      head(t('n_scoring'), t('l_scoring')),
      sec(t('s_leaders'), board(rows, { dim: 'scoring', valueKey: 'ppg', altKey: 'ts', altDigits: 3 })),
      sec(t('s_dist'), chartCard(t('c_ppg'), dotStrip(rankedBy('scoring', 60), { dim: 'scoring', valueKey: 'ppg', color: HUE.scoring }))),
      sec(t('s_scatter'), chartCard(t('c_ppg') + ' / ' + t('c_ts'), scatter(D.players))),
      sec(t('s_split'), chartCard(t('s_split'), splitChart(rankedBy('scoring', 18)))),
      sec(t('s_table'), dtable([
        { key: 'scoring', label: t('c_rank'), render: (r) => rankCell(r.scoring) },
        { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
        { key: 'ppg', label: t('c_ppg') }, { key: 'ts', label: t('c_ts'), digits: 3 },
        { key: 'splitFt', label: t('c_ft') }, { key: 'gp', label: t('c_gp'), digits: 0 },
      ], D.players.slice().sort((a, b) => a.scoring - b.scoring), { defaultSort: 'scoring' })),
    ];
  },

  impact() {
    return [
      head(t('n_impact'), t('l_impact')),
      sec(t('s_leaders'), board(rankedBy('impact', 25), { dim: 'impact', valueKey: 'ppg', altKey: 'apg' })),
      sec(t('s_dist'), chartCard(t('c_ppg'), dotStrip(rankedBy('impact', 60), { dim: 'impact', valueKey: 'ppg', color: HUE.impact }))),
      h('p', { class: 'note' }, t('t_note_dimpact')),
    ];
  },

  playmaking() {
    return [
      head(t('n_playmaking'), t('l_playmaking')),
      sec(t('s_leaders'), board(rankedBy('playmaking', 25), { dim: 'playmaking', valueKey: 'apg', altKey: 'ppg' })),
      sec(t('s_dist'), chartCard(t('c_apg'), dotStrip(rankedBy('playmaking', 60), { dim: 'playmaking', valueKey: 'apg', color: HUE.playmaking }))),
      h('p', { class: 'note warn' }, t('t_note_play')),
    ];
  },

  defense() {
    const noData = D.players.filter((p) => p.def_excluded).length;
    const rows = rankedBy('defense', 25);
    return [
      head(t('n_defense'), t('l_defense')),
      sec(t('s_leaders'), board(rows, { dim: 'defense', valueKey: 'rpg', altKey: 'seasons' })),
      sec(t('s_dist'), chartCard(t('c_rpg'), dotStrip(rankedBy('defense', 60), { dim: 'defense', valueKey: 'rpg', color: HUE.defense }))),
      h('p', { class: 'note warn' }, t('t_excl_nodata').replace('{n}', noData)),
      sec(t('s_stlblk'),
        h('div', { class: 'grid g2' },
          dtable([
            { key: 'stl_rank', label: t('c_rank'), render: (r) => rankCell(r.stl_rank) },
            { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
            { key: 'stl', label: t('c_stl'), digits: 2 },
          ], D.subsets.steals.map((x) => ({ ...BY[x.name], stl: x.reg_SPG, stl_rank: x.rank })), { defaultSort: 'stl_rank' }),
          dtable([
            { key: 'blk_rank', label: t('c_rank'), render: (r) => rankCell(r.blk_rank) },
            { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
            { key: 'blk', label: t('c_blk'), digits: 2 },
          ], D.subsets.blocks.map((x) => ({ ...BY[x.name], blk: x.reg_BPG, blk_rank: x.rank })), { defaultSort: 'blk_rank' }))),
      h('p', { class: 'note' }, t('t_note_stlblk')),
      sec(t('s_dimpact'), dtable([
        { key: 'rank', label: t('c_rank'), render: (r) => rankCell(r.rank) },
        { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(BY[r.name]), h('span', { class: 'who' }, r.name)) },
        { key: 'def_impact_score', label: t('c_pred'), digits: 2 },
        { key: 'd_dpm', label: t('c_actual'), digits: 2 },
        { key: 'reg_SPG', label: t('c_stl'), digits: 2 },
        { key: 'reg_BPG', label: t('c_blk'), digits: 2 },
      ], D.subsets.dimpact, { defaultSort: 'rank' })),
    ];
  },

  rebounding() {
    const noSplit = D.players.filter((p) => p.reb_split_missing).length;
    return [
      head(t('n_rebounding'), t('l_rebounding')),
      sec(t('s_leaders'), board(rankedBy('rebounding', 25), { dim: 'rebounding', valueKey: 'rpg', altKey: 'apg' })),
      sec(t('s_dist'), chartCard(t('c_rpg'), dotStrip(rankedBy('rebounding', 60), { dim: 'rebounding', valueKey: 'rpg', color: HUE.rebounding }))),
      h('p', { class: 'note warn' }, t('t_reb_split').replace('{n}', noSplit)),
      sec(t('c_orb') + ' / ' + t('c_drb'),
        h('div', { class: 'grid g2' },
          dtable([
            { key: 'oreb_rank', label: t('c_rank'), render: (r) => rankCell(r.oreb_rank) },
            { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
            { key: 'peak_OREB', label: t('c_peak_orb'), digits: 2 },
          ], D.subsets.oreb.map((x) => ({ ...BY[x.name], peak_OREB: x.peak_OREB, oreb_rank: x.rank })), { defaultSort: 'oreb_rank' }),
          dtable([
            { key: 'dreb_rank', label: t('c_rank'), render: (r) => rankCell(r.dreb_rank) },
            { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
            { key: 'peak_DREB', label: t('c_peak_drb'), digits: 2 },
          ], D.subsets.dreb.map((x) => ({ ...BY[x.name], peak_DREB: x.peak_DREB, dreb_rank: x.rank })), { defaultSort: 'dreb_rank' }))),
    ];
  },

  compare() {
    const po = D.players.filter((p) => p.po_gp > 30 && p.po_ppg !== null)
      .sort((a, b) => (b.po_ppg - b.ppg) - (a.po_ppg - a.ppg)).slice(0, 25);
    return [
      head(t('n_compare'), t('l_compare')),
      sec(t('s_po'), chartCard(t('c_reg') + ' / ' + t('c_po'),
        dumbbell(po, { aKey: 'ppg', bKey: 'po_ppg' }))),
      sec(t('s_cross'), dtable([
        { key: 'scoring', label: t('c_rank'), render: (r) => rankCell(r.scoring) },
        { key: 'name', label: t('c_player'), align: 'l', render: (r) => h('span', { class: 'nm' }, badge(r), h('span', { class: 'who' }, r.name)) },
        { key: 'scoring', label: t('n_scoring') }, { key: 'impact', label: t('n_impact') },
        { key: 'playmaking', label: t('n_playmaking') }, { key: 'defense', label: t('n_defense') },
        { key: 'rebounding', label: t('n_rebounding') }, { key: 'ppg', label: t('c_ppg') },
        { key: 'apg', label: t('c_apg') },
      ], D.players, { defaultSort: 'scoring' })),
    ];
  },

  players() {
    const detail = h('div', {});
    const list = h('div', { class: 'plist' });
    const search = h('input', { type: 'search', placeholder: t('search'), 'aria-label': t('search') });
    let cur = 'Michael Jordan';
    const paint = () => {
      const q = search.value.trim().toLowerCase();
      list.replaceChildren(...D.players.filter((p) => p.name.toLowerCase().includes(q))
        .sort((a, b) => (a.scoring ?? 999) - (b.scoring ?? 999))
        .map((p) => h('button', { 'aria-current': p.name === cur ? 'true' : 'false',
          onclick: () => { cur = p.name; paint(); } },
        badge(p), h('span', {}, p.name), h('span', { class: 'v' }, `#${int(p.scoring)}`))));
      const p = BY[cur];
      detail.replaceChildren(
        h('div', { class: 'head', style: 'margin-bottom:14px' },
          h('div', { class: 'nm', style: 'gap:12px' }, badge(p),
            h('div', {}, h('h2', { style: 'margin:0' }, p.name),
              h('p', { style: 'margin:2px 0 0' },
                `${p.first}–${p.last} · ${p.seasons} ${t('c_seasons')} · ${p.gp} ${t('c_gp')} · ${p.team}`)))),
        h('div', { class: 'mrow' }, ...[['ppg', p.ppg, 1], ['rpg', p.rpg, 1], ['apg', p.apg, 1], ['ts', p.ts, 3]]
          .map(([k, v, d]) => h('div', { class: 'metric' },
            h('div', { class: 'kpi-l' }, t('c_' + k)), h('div', { class: 'kpi-v' }, fmt(v, d))))),
        h('div', { class: 'grid g2', style: 'margin-top:12px' },
          chartCard(t('s_radar'), radar(p)), chartCard(t('s_curve'), curve(p))),
        sec(t('s_cross'), dtable([
          { key: 'k', label: '', align: 'l' }, { key: 'v', label: t('c_rank') },
        ], DIMS.slice(0, 5).map((d) => ({ k: t('n_' + d), v: p[d] })))),
        sec(t('s_split'), chartCard(t('s_split'), splitChart([p]))),
      );
    };
    search.addEventListener('input', paint);
    paint();
    return [head(t('n_players'), t('l_players')),
      h('div', { class: 'toolbar' }, search),
      h('div', { class: 'grid', style: 'grid-template-columns:270px minmax(0,1fr)' }, list, detail)];
  },

  data() {
    const m = D.meta;
    return [
      head(t('n_data'), t('l_data')),
      sec(t('ver'), h('p', { class: 'note ok' }, t('ver_i')),
        h('div', { class: 'grid g4' },
          h('div', { class: 'card' }, h('div', { class: 'kpi-l' }, t('ver_reg')),
            h('div', { class: 'kpi-v sm' }, String(m.regular_rows)), h('div', { class: 'kpi-s' }, `${t('ver_match')} ${m.primary_match}`)),
          h('div', { class: 'card' }, h('div', { class: 'kpi-l' }, t('ver_po')),
            h('div', { class: 'kpi-v sm' }, String(m.playoff_rows)), h('div', { class: 'kpi-s' }, `${t('ver_match')} ${m.primary_match}`)),
          h('div', { class: 'card' }, h('div', { class: 'kpi-l' }, t('ver_pre')),
            h('div', { class: 'kpi-v sm' }, String(m.playoff_pre2002_rows)), h('div', { class: 'kpi-s' }, `${t('ver_match')} ${m.primary_match}`)),
          h('div', { class: 'card' }, h('div', { class: 'kpi-l' }, t('ver_br')),
            h('div', { class: 'kpi-v sm' }, m.br_match), h('div', { class: 'kpi-s' }, t('ver_src') + ': NBA.com')))),
      sec(t('method'), h('p', { class: 'note' }, t('method_body'))),
      sec(t('lim'), ...t('lim_items').map((x) => h('p', { class: 'note' }, x))),
      h('footer', {},
        h('a', { href: 'https://github.com/feiyu912/nba-stars' }, t('repo')),
        h('span', {}, `${t('ver_built')}: ${m.generated}`),
        h('span', {}, `${t('k_verified')}: ${m.primary_match}`)),
    ];
  },
};

// ══════════════ 外壳 ══════════════
const NAVG = [
  { g: 'g_rank', items: ['overview', 'scoring', 'playmaking', 'defense', 'rebounding', 'impact'] },
  { g: 'g_explore', items: ['compare', 'players'] },
  { g: 'g_about', items: ['data'] },
];
const SVG_ICON = { overview: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' };

function render() {
  const cur = VIEWS[location.hash.slice(1)] ? location.hash.slice(1) : 'overview';
  const main = document.getElementById('view');
  main.replaceChildren(...VIEWS[cur]());
  document.getElementById('side').replaceChildren(
    h('div', { class: 'side-brand' },
      h('div', { class: 'side-brand-row' }, h('span', {}, '🏀'), h('h1', {}, t('brand'))),
      h('div', { class: 'side-brand-sub' },
        h('p', {}, t('brandSub')),
        h('div', { class: 'lang' }, ...['en', 'zh'].map((l) => h('button', {
          'aria-pressed': l === lang ? 'true' : 'false',
          onclick: () => { lang = l; localStorage.setItem('nba_lang', l); render(); },
        }, l === 'en' ? 'EN' : '中文'))))),
    ...NAVG.map((grp) => h('div', { class: 'side-group' },
      h('span', {}, t(grp.g)),
      ...grp.items.map((k) => h('a', {
        href: `#${k}`, 'aria-current': k === cur ? 'page' : null,
        style: `--dot:${HUE[k] || 'var(--accent)'}`,
      }, h('span', { class: 'sw' }), t('n_' + k))))));
  document.title = `${t('brand')} · NBA`;
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', render);
render();