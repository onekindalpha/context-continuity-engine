# 0013. pip 설치형 패키징 (콘솔 스크립트)

## 상태

확정

## 결정

`pyproject.toml`을 추가해 이 프로젝트를 표준 pip 패키지로 만든다. `pip install -e .`를 저장소 폴더에서 한 번 실행하면 `context-continuity-engine`이라는 명령이 시스템 어디서나(다른 폴더로 이동해도) 바로 실행 가능해진다. `[project.scripts]`에 `context-continuity-engine = "src.cli:main"`을 등록했다. 기존 `python3 -m src.cli` 실행 방식은 그대로 남겨둔다 — 설치를 원치 않는 경우를 위한 대안이다.

## 이유

CLI(0011)를 만든 뒤에도 사용자가 매번 저장소 폴더로 `cd`하고 `python3 -m src.cli ...`라는 긴 명령을 기억해야 했다. "라이브러리처럼 그냥 설치해서 쓰면 안 되냐"는 사용성 문제 제기가 있었고, 표준 Python 패키징(`pyproject.toml` + console script entry point)이 정확히 이 문제를 푸는 관용적인 방법이다. 새 의존성을 추가하지 않고(`dependencies = []`), 기존 `src/` 구조와 테스트를 전혀 바꾸지 않고 순수하게 추가만 했다.

## 범위

- 배포용 패키지 이름은 `context-continuity-engine`, 설치되는 실제 Python 패키지는 기존 `src/`를 그대로 사용한다(`packages = ["src"]`). 패키지 이름이 `src`인 것은 관용적이지 않지만, 이번 범위(개인 로컬 설치)에서는 문제되지 않는다. PyPI에 공개 배포할 계획이 생기면 그때 `src/` → `context_continuity_engine/`으로 이름을 바꾸는 것을 검토한다.
- PyPI에 게시하지 않는다. `pip install -e .`(로컬 editable install) 사용을 전제로 한다.

## 알려진 한계

- editable install(`-e`) 없이 일반 `pip install .`을 하면 소스를 수정해도 재설치 전까지 반영되지 않는다.
- 가상환경을 쓰지 않고 시스템 Python에 설치하면 `pip`가 경고를 낸다(`--break-system-packages`가 필요한 환경도 있음). 이 프로젝트는 표준 라이브러리만 쓰므로 의존성 충돌 위험은 낮지만, 이 문제 자체를 해결해주지는 않는다.
