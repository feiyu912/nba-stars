import pandas as pd
from sklearn.preprocessing import StandardScaler

# 读数据
df = pd.read_csv("data.csv")

# 计算 TS+
df["TS_plus"] = df["TS"] / df["league_TS"]

# 选特征
features = ["PPG", "TS_plus", "AST_pct"]

X = df[features]

# 标准化（很关键）
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 加权评分（第二版：降低AST权重，突出得分能力）
df["Score"] = (
    0.5 * X_scaled[:, 0] +   # PPG 权重最高
    0.3 * X_scaled[:, 1] +   # TS+ 效率
    0.2 * X_scaled[:, 2]     # AST 组织
)

# Context：效率 × 组织能力的非线性组合
df["Context"] = df["TS_plus"] * (df["AST_pct"] ** 0.3)
context_scaled = StandardScaler().fit_transform(df[["Context"]])
df["Score"] += 0.2 * context_scaled[:, 0]

# 排名
df = df.sort_values("Score", ascending=False)

print(df[["player", "Score"]])