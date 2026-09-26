"""NBA 球员多维排名系统的计算核心。

模块:
  config      参数 (时代基准、权重、阈值)
  data        数据加载与契约校验
  era         时代修正 (pace / 竞争强度 / 稀缺性 / Z-score)
  engine      排名引擎 (双视角 → 巅峰+生涯 → 季后赛 → 中位数名次)
  dimensions  四个维度的指标构造
  ridge       岭回归 + 交叉验证
  run         按正确顺序跑完并写出结果
"""

__all__ = ["config", "data", "dimensions", "engine", "era", "ridge", "run"]
