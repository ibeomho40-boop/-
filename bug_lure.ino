// 엄물포 | 기상 반응형 395nm 날벌레 유인 장치 (아두이노 나노)
// 역할: 센서 값 전송(인지) + 강우 안전 규칙 + LED 출력(행동)
#include <Wire.h>
#include <RTClib.h>     // RTC 모듈 (DS3231 기준)
#include <DHT.h>        // 온습도 센서 (DHT22 기준)

#define DHT_PIN   2
#define RAIN_PIN  3     // 강우 센서 DO: 젖으면 LOW
#define LUX_PIN   A0    // 조도 센서(CdS): 밝을수록 값이 커지게 배선
#define LED_PIN   9     // MOSFET 게이트 → 395nm LED (PWM)

DHT dht(DHT_PIN, DHT22);
RTC_DS3231 rtc;

int level = 0;                       // 파이썬이 보낸 단계: 0 소등, 1 저출력, 2 고출력
float temp = NAN, hum = NAN;
unsigned long lastSend = 0, lastDht = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();
  rtc.begin();
  pinMode(RAIN_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  bool raining = digitalRead(RAIN_PIN) == LOW;

  // 1) 파이썬(GRU)에서 온 명령 읽기: '0' / '1' / '2'
  while (Serial.available()) {
    char c = Serial.read();
    if (c >= '0' && c <= '2') level = c - '0';
  }

  // 2) 온습도는 2초마다만 읽기 (DHT22는 너무 자주 읽으면 오류)
  if (millis() - lastDht >= 2000) {
    lastDht = millis();
    temp = dht.readTemperature();
    hum  = dht.readHumidity();
  }

  // 3) 100ms마다 센서 값 전송: 기온,습도,강우,조도,시
  if (millis() - lastSend >= 100) {
    lastSend = millis();
    DateTime now = rtc.now();
    Serial.print(temp);  Serial.print(',');
    Serial.print(hum);   Serial.print(',');
    Serial.print(raining ? 1 : 0); Serial.print(',');
    Serial.print(analogRead(LUX_PIN)); Serial.print(',');
    Serial.println(now.hour());
  }

  // 4) 행동: 비가 오면 AI 명령과 상관없이 소등 (안전 규칙 최우선)
  int pwm = 0;
  if (!raining) {
    if (level == 2) pwm = 255;       // 고출력
    else if (level == 1) pwm = 100;  // 저출력
  }
  analogWrite(LED_PIN, pwm);
}
