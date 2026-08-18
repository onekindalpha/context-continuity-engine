# 0012. 느슨한 형식 입력 지원

## 상태

확정

## 결정

`src/cli.py`에 `--raw` 옵션을 추가한다. 켜면 엄격한 TXT(`[timestamp] speaker:`)/MD/JSON 형식 대신, "화자: 내용" 정도의 느슨한 텍스트를 입력으로 받는다. 변환은 `src/raw_text_convert.py`가 담당하고, 결과를 `ingest_json`에 그대로 넘긴다.

## 이유

TXT 형식은 채팅 화면에서 그대로 복사한 텍스트의 실제 모습이 아니다. 사용자가 매번 `[timestamp] speaker:` 형식으로 손으로 맞춰야 한다면, 실제로 쓰기 어렵다는 문제가 CLI(0011)를 만든 뒤에도 남는다. 화자 표시("user:", "나:", "assistant:", "클로드:" 등)만 있으면 나머지는 자동으로 turn으로 묶는 변환기를 추가해 이 수고를 없앤다.

`src/ingest.py`의 기존 엄격한 파서는 바꾸지 않는다. `raw_text_convert.py`는 그 앞에 붙는 별도 전처리 단계다 — 기존 테스트와 동작에 영향이 없다.

## 범위

- 화자 별칭: `SPEAKER_ALIASES`에 등록된 것만 인식한다(user/나/사용자/질문/me, assistant/claude/클로드/ai/답변/gpt/chatgpt).
- timestamp는 만들지 않는다. `ingest_json`이 timestamp를 필수로 요구하지 않으므로 문제없다.
- 첫 화자 표시 이전 내용은 버리고 warnings에 남긴다.

## 알려진 한계

- 화자 표시 없이 turn이 번갈아 나오는 형식(예: 단순히 줄바꿈으로만 구분)은 지원하지 않는다.
- 화자 별칭 목록에 없는 표현(예: "질문자:")은 새 turn으로 인식되지 않고 이전 turn 본문에 그대로 들어간다.
