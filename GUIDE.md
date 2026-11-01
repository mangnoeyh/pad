# Pad

제한된 시간 안에 업무 요구를 함께 이해하고, 사용자가 판단 이유를 설명할 수 있는 검증 가능한 결과를 만드는 범용 작업 키트입니다. 사람과 AI의 이중 루프 운영 Skill, 로컬 데이터 탐색·SQL 도구와 기록 템플릿을 제공합니다. 여러 업무에 적용할 수 있는 도구와 지침을 모았습니다.

## 작업을 시작할 때

[START_HERE.md](START_HERE.md)에 시작 요청과 재개 요청을 준비했습니다. 작업 공간에서 이 공개 키트를 별도 폴더로 가져오고, 시작 문서와 [double-loop-solver Skill](.agents/skills/double-loop-solver/SKILL.md)을 직접 읽히면 됩니다. 과제 루트와 기존 지침을 유지하세요.

- 처음에는 문제와 자료를 함께 이해하고 실제 병렬 기능을 짧게 확인합니다. 사용자의 이해 확인 후에는 시작 요청에 위임된 E2E 구현을 자율 진행합니다.
- 메인은 사용자와 운영상 빠진 요구·핵심 최적화·목표 간 절충을 논의합니다. 담당자에게 보낼 질문을 만들고, 부분 답변은 미답 부분을 좁혀 다시 묻습니다.
- 워커는 기존 환경에서 가장 단순한 유효한 방법으로 서비스 구현·검증을 계속합니다. 중요한 결정에 의존하는 부분만 기다리며, 메인이 확정한 변경을 명시적으로 전달합니다.
- 설정과 입력을 바꿔 쓰는 서비스라면 사람은 개발 중 일반 판단 기준을 정하고, 서비스는 실행 중 예외 선정·재계산·검증을 자동 수행하도록 만듭니다. 과거 명단이나 기본 설정의 결과 한 번으로 완성을 판단하지 않습니다.
- 메인은 통합·전체 검증도 책임집니다. 대표 결과·실제 데이터 처리·판단 근거를 설명하고, 제출 전 사용자가 자신의 말로 설명할 기회를 갖습니다.

적용 순서와 내부·외부 루프 사례는 [이중 루프 적용 방법](DOUBLE_LOOP.md), 작업 완료 후 질답 구성과 연습은 [제출 전 예상 질답 준비](PRACTICE_QA.md)를 참고하세요.

구현·검증이 끝나면 [전체 해설 보고서 양식](templates/solution-review.md)으로 문제·접근·코드 구조·실제 검증·협업 과정과 한계를 정리하고, 예상 질답은 별도 파일로 작성하도록 시작 요청에 연결했습니다. 완성 문서는 실제 과제 환경 안에 저장합니다.

대화 운영 방식은 Markdown 지침이며, 아래 선택형 실행 도구를 함께 제공합니다. 별도 모델·API 키·프레임워크 설치가 필요하지 않으며, 실제 타이머나 실행을 강제로 제어하는 프로그램은 아닙니다. 계약·실행 결과·사람의 결정은 과제 작업 공간에 남깁니다.

## 환경과 테스트

이 문서의 `tools/`, `examples/`, `requirements-*.txt`와 테스트 명령은 **키트 루트에서 실행하는 경로**입니다. 키트를 실제 과제 아래의 별도 폴더에 복제했다면 과제 루트와 구분하세요. 문서의 Markdown 링크는 해당 문서 위치 기준이며, 시작 요청의 키트 경로는 확인한 복제본 루트에 맞춰 해석합니다.

실제 자료를 처리할 때는 스크립트·입력·출력의 위치를 명확히 지정하세요. 아래 `/path/to/kit`와 `/path/to/task`를 현재 환경의 절대 경로로 바꾸면 과제 폴더에서도 실행할 수 있습니다. 실제 과제 자료·결과·학습 기록은 과제의 허용 위치에 저장합니다.

```bash
python "/path/to/kit/tools/check_environment.py"
python "/path/to/kit/tools/inspect_data.py" "/path/to/task/data/input.csv" --output-dir "/path/to/task/artifacts/triage"
```

코드는 Python 3.10 이상 문법을 사용하며, CPython 3.12.14에서 검증했습니다. 먼저 `python tools/check_environment.py`로 설치 상태를 확인하세요. 필요한 패키지가 없고 설치가 허용된 경우, 활성화한 격리 환경에서 해당 묶음만 설치하는 것을 권장합니다.

```bash
python -m pip install -r requirements-core.txt
# 예측 모델 예제를 사용할 때
python -m pip install -r requirements-ml.txt
# Excel·Parquet를 읽을 때
python -m pip install -r requirements-formats.txt
```

- `requirements-core.txt`: pandas·DuckDB
- `requirements-ml.txt`: core와 scikit-learn
- `requirements-formats.txt`: core와 openpyxl·pyarrow

로컬 검증은 다음 명령으로 실행합니다.

```bash
python -m unittest discover -s tests -v
```

선택 의존성이 없으면 해당 형식·기능 테스트가 건너뛰어질 수 있습니다. 전체 기능을 검증하려면 필요한 의존성을 모두 설치하고, 실행 결과의 skip·실패 항목을 확인하세요. 이 명령들은 설치된 Codex를 변경하지 않습니다.

## 빠른 시작

제공받은 작업 환경과 과제 README를 먼저 확인합니다. 다음 명령은 외부 다운로드 없이 합성 데이터를 만들고 탐색합니다. 실제 데이터로 작업할 때는 입력·출력 경로를 바꾸세요.

```bash
python tools/check_environment.py
python examples/make_demo_data.py --output-dir data/demo
python tools/inspect_data.py data/demo/measurements.csv --output-dir artifacts/triage
python tools/query_data.py data/demo/measurements.csv --sql "SELECT equipment, COUNT(*) AS n FROM data GROUP BY equipment" --output artifacts/count.csv
```

환경 점검은 설치된 패키지 상태를 확인합니다. 스크립트가 패키지를 설치하거나 네트워크에 접속하지는 않습니다. 필요한 패키지가 없을 때만 제공 환경에서 허용하는 방법으로 준비하세요. 통제된 작업 환경에서는 제공된 도구와 허용된 설치 절차를 따르세요.

전체 옵션은 각 명령 뒤에 `--help`를 붙여 확인할 수 있습니다. `--overwrite`는 `tools/inspect_data.py`와 `tools/query_data.py`에서만 지원하며, 기존 결과를 바꿀 의도가 있을 때 사용하세요. `examples/make_demo_data.py`와 `examples/tabular_ml.py`에는 이 옵션이 없습니다. 합성 데이터는 새 파일 위치를, ML 결과는 새 폴더 또는 빈 폴더를 지정하세요.

## 무엇을 쓸까

| 목적 | 파일 | 결과·주의점 |
| --- | --- | --- |
| 실행 환경 확인 | `tools/check_environment.py` | Python·패키지 상태, `--json` 지원 |
| 데이터 구조·품질 확인 | `tools/inspect_data.py` | `profile.json`, `profile.md` |
| 로컬 데이터 SQL 분석 | `tools/query_data.py` | `.csv`, `.json`, `.jsonl` 결과 |
| 합성 데이터 생성 | `examples/make_demo_data.py` | `measurements.csv`, 표준 라이브러리만 사용 |
| 표형 예측 모델 예제 | `examples/tabular_ml.py` | `metrics.json`, `predictions.csv`, `report.md` |
| 이중 루프 문제 해결 | `.agents/skills/double-loop-solver/SKILL.md` | 고정 기준 아래 개선, 중요한 해석은 사람 판단 |
| 입력·업무 요구 파악 | `.agents/skills/data-triage/SKILL.md` | 관측 사실과 가정, 다음 분석의 근거 |
| 결론·모델 검증 | `.agents/skills/analysis-validation/SKILL.md` | 검증 결과와 한계 |
| 계획·결정·보고 기록 | `templates/` | 과제 지정 양식이 있으면 그 양식을 우선 |

### 데이터 탐색

```bash
python tools/inspect_data.py data/input.csv --output-dir artifacts/triage --max-rows 100000
python tools/inspect_data.py data/input.xlsx --sheet 0 --output-dir artifacts/sheet0
```

CSV, TSV, Excel, JSON, JSONL, Parquet를 다룹니다. 형식이 모호하면 `--format`을, CSV 인코딩이 다르면 `--encoding`을 지정하세요. Excel·Parquet에는 해당 읽기 패키지가 필요할 수 있습니다.

**기본 탐색은 처음 최대 100,000행을 읽습니다. 무작위 표본이 아닙니다.** 시간·그룹 순서가 있는 데이터에서는 편향될 수 있습니다. `sampled`, `exact_row_count`, `total_rows`와 읽은 행 수를 확인하고, 전체 건수를 알 수 없을 때 이를 전체 통계로 보고하지 마세요. 큰 파일에서 제한을 늘리기 전 메모리를 확인하세요.

### SQL 분석

```bash
python tools/query_data.py data/input.csv --sql "SELECT category, COUNT(*) AS n FROM data GROUP BY category ORDER BY n DESC" --output artifacts/by_category.csv
```

입력은 `data`라는 테이블로 조회합니다. 실제 컬럼명으로 SQL을 바꾸세요. 기본 입력 범위는 처음 최대 100,000행이며 결과도 최대 10,000행으로 제한하며, 초과하면 출력을 생략하고 오류를 표시합니다. `--max-rows`, `--max-result-rows`를 조정할 수 있습니다. 단일 조회문만 지원하며 원격 데이터·확장 설치·외부 파일 접근을 위한 범용 SQL 실행기가 아닙니다.

### 예측 모델 예제

위 합성 데이터로 시간 순서에 따른 검증을 연습할 수 있습니다. pandas와 scikit-learn이 필요합니다.

```bash
python examples/tabular_ml.py data/demo/measurements.csv --target target --task classification --split time --time-column timestamp --group-column equipment --output-dir artifacts/ml
```

`--task classification|regression`, `--split random|time|group`, `--test-size`, `--seed`, `--max-rows`를 지원합니다. 시간·그룹 컬럼을 지정하면 역할 컬럼은 특징에서 제외됩니다. 기본값이 실제 과제에 맞는다는 뜻은 아닙니다. 그룹 간 일반화가 목표라면 `--split group --group-column equipment`처럼 분할을 바꾸세요. 결과 폴더는 새 폴더 또는 빈 폴더를 사용합니다. 합성 데이터 성능은 실제 업무 성능의 근거가 아닙니다.

## AI와 함께 쓰는 방법

대화형 시작·재개 요청은 [START_HERE.md](START_HERE.md)를 사용하세요. 아래는 문제를 함께 읽는 짧은 시작 요청입니다. 이후 동의한 작업에 필요한 세부 Skill만 읽힙니다. 복제한 하위 폴더의 Skill이 자동 발견되는지는 실행 환경에 따라 다릅니다. 보이지 않으면 Skill 파일 경로를 직접 지정하세요. 기존 과제의 `AGENTS.md`를 덮어쓰지 마세요.

> START_HERE.md의 두 트랙 진행을 적용해줘. 먼저 문제·자료·필수 결과를 쉬운 예시로 설명하고 내 이해를 확인해줘. 이해 확인 후에는 워커가 가장 간단한 방법으로 필수 E2E 구현을 자율 진행하고, 메인은 나와 숨은 운영 요구·핵심 최적화를 논의해줘. 담당자 답변의 미답 부분은 후속 질문으로 좁혀주고, 확정한 변경만 워커에게 전달해줘. 실제 병렬 실행과 답변 대기 중 실행 지속은 처음에 짧게 확인해줘.

실행 후에는 다음처럼 검증을 요청할 수 있습니다.

> analysis-validation Skill에 따라 결론을 재검증해줘. 사용한 입력 범위, 필터·조인 전후 건수, 단위·분모, 기준선 대비 결과와 재현 명령을 확인하고, 실제로 실행한 검사와 아직 확인하지 못한 사항을 나눠 기록해줘.

AI가 만든 코드·수치·설명은 실행 결과와 대조합니다. 예측이 필요하지 않은 과제에 모델을 억지로 넣지 말고, 집계·시각화·간단한 규칙으로 목표를 달성할 수 있으면 먼저 사용하세요.

## 공개 자료로 가져오기

이 키트를 공개 저장소로 사용할 때는 해당 저장소의 실제 공개 URL에서 제공 환경 안으로 복제합니다. 비공개 파일을 업로드하는 대신, 공개된 자료를 필요한 범위에서 가져오는 흐름입니다.

```bash
git clone https://github.com/mangnoeyh/pad.git pad
git -C pad rev-parse HEAD
```

실제로 쓴 공개 저장소 URL·커밋·파일·용도를 작업 기록에 남기는 것을 권장합니다. 서드파티 자료의 후보와 기록 예시는 [ATTRIBUTION.md](ATTRIBUTION.md)에 있습니다. 전체 Skill 모음이나 하네스를 한꺼번에 설치할 필요는 없습니다.

## 통제된 작업 환경에서의 사용

접근·실행·전송에 제약이 있는 작업 공간에서는 최신 운영 지침과 실제 과제 README를 우선합니다. 이 키트가 추가 권한을 부여하지는 않습니다.

- 원본 데이터는 보존하고 파생 결과를 별도 경로에 저장합니다. 작업 자료와 이력을 외부 서비스나 Git 저장소로 보낼 권한이 없으면 전송하지 않습니다.
- 해당 환경에서 허용된 AI와 계정만 사용합니다. 개인 API 키나 외부 AI 연결도 그 환경의 허용 범위를 따릅니다.
- 제공된 도구를 임의로 업데이트하거나 관리 설정·접근·전송 제한을 우회하지 않습니다. UI 자동 조작·Computer Use도 작업 공간에서 허용될 때만 사용합니다.
- 공개 코드·템플릿은 요구사항에 맞게 선택하고 검증합니다. 사용한 부분과 수정한 부분, 출처와 라이선스를 기록합니다.
- 참조 저장소의 공개 유지 조건이 있으면 해당 운영 지침을 따릅니다.
- AI 사용이 제한된 후속 절차가 시작되면 답변 작성·수정·실시간 코칭을 중단합니다. 이해를 돕는 설명과 연습은 AI 사용이 허용되는 작업 단계에서 진행합니다.

이 저장소에는 범용 도구·지침·합성 예제·빈 양식만 둡니다. 개별 작업의 원본 자료·완성 결과·비공개 운영 문서는 해당 작업 공간에서 관리합니다.

## 필요한 기능만 선택하기

작업 지시와 기존 스택·남은 시간이 우선입니다. 다음 파일들은 함께 제공되지만, 한 번에 모두 읽거나 새 프레임워크를 설치할 필요가 없습니다.

| 필요할 때 | 실제 파일 | 적용 방식 |
| --- | --- | --- |
| 검증 이후 파일 변경·빈 테스트 확인 | [실행 근거 도구](.agents/skills/double-loop-solver/references/evidence-tools.md), tools/verify_work.py | 확정한 실제 명령과 관련 파일을 연결; 자동 정답 판정은 아님 |
| 실패 재현·원인 가설·최소 수정 | [evidence-debug](.agents/skills/evidence-debug/SKILL.md) | 가설 / 근거 / 반박 관측 / 최소 확인 |
| 내가 코드 흐름을 이해하고 싶을 때 | [code-walkthrough](.agents/skills/code-walkthrough/SKILL.md) | 실제 입력 → 파일·함수 → 관측 결과, 한 개념씩 |
| 웹 UI 구현·다듬기 | [frontend-design](.agents/skills/frontend-design/SKILL.md) | 현재 요구·스택 안에서 디자인, 사람이 보는 화면 확인과 코드 검사 구분 |
| 웹/API 동작 검증 | [app checks](.agents/skills/double-loop-solver/references/app-checks.md) | 실제 응답 코드·본문·상태 변화, 라벨·ID 연결, 사람의 미리보기 확인 |
| 메인 논의와 워커 구현의 병렬 분담 | [parallel work](.agents/skills/double-loop-solver/references/parallel-work.md) | 메인 통합, 단순 읽기 분류는 사용 가능한 Luna, 구현은 Sol medium; 실제 지원·권한 안에서 선택 |
| 웹 입력·중복 실행·조건 변경·실패 복구 | [web state checks](.agents/skills/double-loop-solver/references/web-state-checks.md) | 실제 정책에 따른 경합·저장 결과·권한과 화면 상태 확인; 버튼 차단과 서버 처리 구분 |
| 범위 변경·기준본·실제 전달 연결 | [baseline and delivery](.agents/skills/double-loop-solver/references/baseline-and-delivery.md) | 추가 조건 사전 점검, 전체 비용 재산정, 실험 승격, 전달 소스에서의 실행 재현 |
| 고정 입력에서 후보 해 개선 | [optimization validation](.agents/skills/analysis-validation/references/optimization-validation.md) | 기준선 실측, 제약과 목적 분리, 축소 선별 뒤 전체 검증, 같은 입력·조건의 안정본 보존 |
| 문제 구조에 맞는 방법 선택·후보 비교 | [method selection](.agents/skills/double-loop-solver/references/method-selection.md), [비교 양식](templates/candidate-comparison.md) | 적용 조건·지원하지 않는 제약 확인, 같은 기준의 처리 범위·품질·시간 비교 |
| 기본 알고리즘부터 운영 최적화까지 찾아보기 | [방법 목차](docs/methods/INDEX.md) | 그래프·DP·구간·문자열·수치·배정·흐름·경로·일정·공간·개선. 관련 절만 읽고 목록 밖 대안도 검토 |
| 여러 방법의 연결·실패·사용자 설명 | [조합](docs/methods/composition.md), [검산](docs/methods/validation.md), [쉬운 설명](docs/methods/explain.md) | 후보 손실과 결합 제약, 작은 정확 해와 전체 검증, 현재 설정·실제 서비스 경로 연결 |
| 기본 계산의 실행 예제와 독립 검산 | [실행 예제 안내](examples/methods/USAGE.md) | 표준 라이브러리 함수·지원 계약·검산 명령. 자료에 있는 모든 방법이 구현된 것은 아님 |
| 작은 합성 문제에서 계산·독립 검산 연습 | [allocation lab](examples/ALLOCATION_LAB.md) | 표준 라이브러리로 후보 생성, 저장 결과 재검사, 한도 내 전체 열거. 범용 최적화 엔진이 아님 |
| 두 트랙의 결정 전달·재계산·설명 연습 | [two-track rehearsal](examples/TWO_TRACK_REHEARSAL.md) | 실제 워커 증거와 모의 대화 구분, 설정 변경 뒤 재검사, 사용자 학습 확인 |
| 요구사항에서 불변식 찾기 | [analysis-validation](.agents/skills/analysis-validation/SKILL.md) | 조건이 성립하는 경우에만 순서 변경·멱등성·직렬화 왕복 확인; 새 패키지 불필요 |
| 문체 수정 전후 수치·단위·인용 후보 대조 | [compare_notes.py](tools/compare_notes.py), [사용 범위](.agents/skills/double-loop-solver/references/note-comparison.md) | 읽기 전용. 변경 후보를 보여주며 의미 보존은 별도 검토 |
| 최종 코드·보고서·질답의 저장본 확인 | [review_delivery.py](tools/review_delivery.py), [계획과 기록 규격](.agents/skills/double-loop-solver/references/delivery-review.md) | 지정 파일 해시·형식·경로·예상 밖 파일 점검; 실제 전달 완료는 아님 |
| 한국어 보고서 교정 | [korean-report-polish](.agents/skills/korean-report-polish/SKILL.md) | 사실·수치·참조·협업 역할을 보존하며 문체만 정리 |
| 예측 데이터의 누수·중복·시점 확인 | [data-audit](.agents/skills/data-triage/references/data-audit.md) | 기존 data-triage에 추가; 특징을 언제 알 수 있었는지 확인 |
| 운영 제약에 맞춘 지표·분할 검토 | [honest-eval](.agents/skills/analysis-validation/references/honest-eval.md) | 기존 analysis-validation에 추가; 지정 지표와 실제 사용 경계 우선 |

원본 버전·수정 내역·저작권 고지는 [ATTRIBUTION.md](ATTRIBUTION.md)와 [vendor/manifest.json](vendor/manifest.json)에 있습니다. 외부 설치 스크립트·MCP 서버·모델 설정·자동 화면 조작 도구는 가져오지 않았습니다.

기존 구현 수정, 실패 경로, 에디터·저장본·서버 불일치, 병렬 작업은 [진행 검토](.agents/skills/double-loop-solver/references/execution-review.md)의 해당 항목만 사용합니다. 문제 파악과 첫 실행 결과부터 [질문 기준](.agents/skills/double-loop-solver/references/stakeholder-questions.md)을 적용해 중요한 운영상 빈틈을 찾고, 부분 답변의 미답 항목을 후속 질문으로 좁힙니다. 전체 체크리스트를 모든 작업에 적용하지 않습니다.
