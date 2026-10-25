"""엄물포 | GRU 날벌레 출현율 모델 학습 (TensorFlow/Keras)
virtual_data.csv 열: time, temp, hum, rain, lux, bug_count  (1시간 간격)
 - 지금은 문헌 기반 가상 데이터, 이후 현장 트랩 개체 수로 교체
"""
import numpy as np
import pandas as pd
from tensorflow import keras
from tensorflow.keras import layers

WIN = 24                                   # 최근 24시간을 보고 예측
FEATS = ["temp", "hum", "rain", "lux", "hour_sin", "hour_cos"]

df = pd.read_csv("virtual_data.csv", parse_dates=["time"])
hour = df["time"].dt.hour
df["hour_sin"] = np.sin(2 * np.pi * hour / 24)   # 23시와 0시가 가깝도록 시각을 원 위의 점으로
df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
df["temp"] = (df["temp"] - 22) / 6               # 표준화: 단위가 다른 값을 비슷한 크기로
df["hum"] = (df["hum"] - 70) / 15
df["lux"] = df["lux"].clip(0, 1)                 # 0(어두움) ~ 1(밝음)으로 맞춘 값

# 출현율 0~1: 상위 1% 개체 수를 1로 보고 나눔
y_all = (df["bug_count"] / df["bug_count"].quantile(0.99)).clip(0, 1).values
X_all = df[FEATS].values.astype("float32")

# 슬라이딩 윈도우: [i-23 ... i] 24시간 → i시점 출현율
X = np.stack([X_all[i - WIN + 1:i + 1] for i in range(WIN - 1, len(df))])
y = y_all[WIN - 1:]

# 시간 순서대로 나누기: 앞 절반(1년차) 학습, 뒤 절반(2년차) 평가
split = len(X) // 2
X_tr, y_tr, X_te, y_te = X[:split], y[:split], X[split:], y[split:]

model = keras.Sequential([
    layers.Input(shape=(WIN, len(FEATS))),
    layers.GRU(16),                         # 은닉 상태(기억) 16칸
    layers.Dense(1, activation="sigmoid"),  # 출현율 0~1
])
model.compile(optimizer="adam", loss="mse")
model.fit(X_tr, y_tr, epochs=30, batch_size=32, validation_split=0.1, verbose=2)

pred = model.predict(X_te).ravel()
rmse = np.sqrt(np.mean((pred - y_te) ** 2))
r2 = 1 - np.sum((pred - y_te) ** 2) / np.sum((y_te - y_te.mean()) ** 2)
r = np.corrcoef(pred, y_te)[0, 1]
print(f"RMSE {rmse:.3f}  R² {r2:.3f}  r {r:.3f}")   # 성공 기준: r ≥ 0.7

model.save("gru_bug.keras")
