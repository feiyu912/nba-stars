"""岭回归预测 (进攻/防守影响力维度共用)。

原实现的两个问题:
  1. StandardScaler 在全部 101 行上 fit, 然后才切出训练集 —— 测试行的统计量
     泄漏进了标准化参数。现在只用训练行 fit。
  2. README 里 "与 O-DPM 相关性 r=0.555" 是样本内指标, 会高估模型。
     现在额外报告 K 折交叉验证的样本外 R² 和 Spearman 秩相关。

注意: O-DPM / D-DPM 是代理目标 (proxy), 不是真值。这里的 R² 只说明
"用基础数据能多大程度复现该代理指标", 不代表预测了真实影响力。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

from . import config


@dataclass
class RidgeResult:
    predictions: pd.Series
    n_train: int
    in_sample_r2: float
    cv_r2: float
    cv_spearman: float
    cv_spearman_p: float
    coefficients: dict[str, float]

    def summary(self, label: str) -> str:
        return (
            f"{label}: 训练样本 {self.n_train} 人 | 样本内 R²={self.in_sample_r2:.3f} | "
            f"5折交叉验证 R²={self.cv_r2:.3f}, Spearman={self.cv_spearman:.3f} (p={self.cv_spearman_p:.4f})"
        )


def fit_predict(
    df: pd.DataFrame,
    features: list[str],
    target: str,
    alpha: float = config.RIDGE_ALPHA,
    n_splits: int = 5,
) -> RidgeResult:
    train_mask = df[target].notna()
    if train_mask.sum() < n_splits * 2:
        raise ValueError(f"训练样本只有 {int(train_mask.sum())} 条, 不足以做 {n_splits} 折交叉验证")

    X_all = df[features].copy()
    X_train = X_all[train_mask]
    y_train = df.loc[train_mask, target]

    # 缺失特征用训练集中位数填充 (不用全量中位数, 同样是避免泄漏)
    medians = X_train.median()
    X_all = X_all.fillna(medians)
    X_train = X_train.fillna(medians)

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=0)
    cv_pred = np.empty(len(y_train))
    for tr, te in kf.split(X_train_s):
        m = Ridge(alpha=alpha).fit(X_train_s[tr], y_train.iloc[tr])
        cv_pred[te] = m.predict(X_train_s[te])

    cv_r2 = r2_score(y_train, cv_pred)
    rho, p = spearmanr(y_train, cv_pred)

    model = Ridge(alpha=alpha).fit(X_train_s, y_train)
    preds = pd.Series(model.predict(scaler.transform(X_all)), index=df.index, name="prediction")

    return RidgeResult(
        predictions=preds,
        n_train=int(train_mask.sum()),
        in_sample_r2=float(r2_score(y_train, model.predict(X_train_s))),
        cv_r2=float(cv_r2),
        cv_spearman=float(rho),
        cv_spearman_p=float(p),
        coefficients=dict(zip(features, model.coef_.round(4), strict=True)),
    )


def sensitivity_ft_discount(reg: pd.DataFrame, po: pd.DataFrame, ft_discounts=(0.6, 0.7, 0.8)):
    """罚球折算系数敏感性: 排名波动多大才算稳健。

    返回 {折扣系数: 名次 Series}。原先只对 0.6/0.7/0.8 做过, 保留并集中到这里。
    """
    from .engine import build_dimension

    out = {}
    for d in ft_discounts:
        r = reg.copy()
        p = po.copy()
        for df in (r, p):
            df["FT_points"] = df["FTM"]
            df["FG_points"] = df["PPG"] - df["FT_points"]
            df["PPG_adj_ft"] = df["FG_points"] + df["FT_points"] * d
        res = build_dimension(
            r, p, name=f"FT={d}", key="scoring",
            agg={"PPG": "mean", "TS_pct": "mean", "GP": "sum", "APG": "mean",
                 "FTM": "mean", "MIN": "mean"},
            views={"A": "scoreA", "C": "scoreC"},
            playoff_mode="weighted",
        )
        out[d] = res.set_index("player")["scoring_rank"]
    return out
