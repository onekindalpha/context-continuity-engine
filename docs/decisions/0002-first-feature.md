# 0002. 첫 번째 구현 기능

## 상태

확정

## 평가 목적

전체 파이프라인(Session Log → Task Context Analysis → Keep/Compress/Externalize → Working Context → Reconstruction Test → Token Comparison)은 session log 입력 파싱에 의존한다. 파싱이 없으면 이후 단계를 테스트할 수 없다.

## 결정

첫 번째 기능: session log ingest.

`src/ingest.py`에서 TXT, Markdown, JSON 형식의 session log를 읽어 공통 내부 표현으로 변환한다.

내부 표현 단위(초안): 발화자, 시각 또는 순서, 텍스트, 원본 형식.

## 이유

1. 이후 모든 단계(Task Context Analysis, Baseline, Reconstruction Test)가 이 출력에 의존한다.
2. LLM 호출이 없어 비용 없이 테스트 가능하다.
3. 실제 session log 확보 전에도 형식 검증을 진행할 수 있다.

## 다음 단계

실제 session log 확보 후 `src/ingest.py`의 파싱 결과를 해당 로그로 검증한다.
