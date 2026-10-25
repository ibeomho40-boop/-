"""엄물포 | 실시간 판단 루프 (노트북)
아두이노 → 센서 값 → 1분 평균 → GRU 출현율 → 3단계 → 아두이노
"""
import time
from collections import deque
import numpy as np
import serial
from tensorflow import keras

PORT, BAUD = "COM3", 9600          # 장치 관리자에서 포트 확인
HIGH, LOW = 0.40, 0.10             # 출현율 기준: 40% 이상 고출력, 10% 이상 저출력

model = keras.models.load_model("gru_bug.keras")
ser = serial.Serial(PORT, BAUD, timeout=1)
hours = deque(maxlen=24)           # 최근 24시간 (1시간 평균값)
this_hour = []                     # 이번 시간의 1분 평균값들


def read_minute():
    """1분 동안 들어온 값을 평균. 고장 값(nan)은 버림"""
    ser.reset_input_buffer()       # 쌓여 있던 옛 데이터 버리기 (3~5초 지연 해결)
    rows, end = [], time.time() + 60
    while time.time() < end:
        try:
            t, h, rain, lux, hr = map(float, ser.readline().decode().strip().split(","))
        except ValueError:
            continue
        if np.isnan(t) or np.isnan(h):
            continue
        rows.append([t, h, rain, lux / 1023, hr])
    return np.mean(rows, axis=0) if rows else None


def features(t, h, rain, lux, hr):
    return [(t - 22) / 6, (h - 70) / 15, rain, lux,
            np.sin(2 * np.pi * hr / 24), np.cos(2 * np.pi * hr / 24)]


while True:
    m = read_minute()
    if m is None:                                   # 센서 이상 → 대체 모드
        ser.write(b"1")                             # 기존 조건문처럼 저출력 유지
        continue
    t, h, rain, lux, hr = m
    this_hour.append(features(t, h, rain >= 0.5, lux, round(hr)))
    cur = np.mean(this_hour, axis=0)                # 이번 시간 평균(진행 중)
    recent = (list(hours) + [cur])[-24:]            # 최근 24시간
    if len(this_hour) == 60:                        # 1시간이 차면 기록
        hours.append(cur)
        this_hour = []

    # 판단 1: 안전 규칙이 AI보다 먼저
    in_time = 19 <= round(hr) <= 23
    if rain >= 0.5 or not in_time:
        level = 0
    elif len(recent) < 24:                          # 기록이 쌓이기 전에는 조건문
        level = 2 if h >= 70 else 1
    else:
        # 판단 2: 최근 24시간 → GRU 출현율
        p = float(model.predict(np.array(recent)[None], verbose=0)[0, 0])
        level = 2 if p >= HIGH else 1 if p >= LOW else 0
        print(f"{round(hr)}시  출현율 {p:.0%}  → 단계 {level}")

    ser.write(str(level).encode())                  # 행동: 아두이노로 전송
