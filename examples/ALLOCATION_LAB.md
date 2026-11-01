# 작은 배정 후보 비교

8개 작업을 3개 자원에 배정하는 합성 예제다. 기존 환경의 Python 표준 라이브러리만 사용한다. 각 작업은 최대 한 자원을 쓰고, 자원별 정원과 허용된 연결을 지킨다. 이 예제는 미배정을 허용하되 **배정 개수 최대화 → 같은 개수에서 비용 최소화** 순으로 비교한다. 실제 과제가 전원 처리를 요구한다면 이 예제의 부분 처리 허용을 가져오면 안 된다.

각 연결의 비용은 독립적으로 더할 수 있는 음이 아닌 정수다. 시간창, 이동 경로, 대상 간 상호작용, 공정성, 가변 크기, 사용자 정책 예외는 구현하지 않는다. 해당 조건이 있으면 입력 모델·방법·독립 검사 모두 다시 설계한다. 상세 선택 기준은 [방법 선택](../.agents/skills/double-loop-solver/references/method-selection.md)을 참고한다.

## 실행

키트 루트에서 실행한다. 아래 출력 폴더와 파일은 아직 없는 경로여야 한다. 이미 실행했다면 다른 이름을 쓴다. 프로그램은 입력을 바꾸거나 기존 결과를 덮어쓰지 않는다.

```sh
python examples/allocation_lab.py --input examples/allocation_input.json --output-dir artifacts/allocation-a
python tools/check_allocations.py --input artifacts/allocation-a/effective-input.json --candidates artifacts/allocation-a/greedy.json artifacts/allocation-a/scarcity.json --output artifacts/allocation-a/comparison.json
```

- `allocation_lab.py`: 입력 순서대로 가장 싼 빈 자원을 고르는 기준선과, 선택지가 적은 작업부터 배정하는 후보를 각각 저장한다. 두 방법 모두 휴리스틱이며 최적성을 주장하지 않는다. 개선 후보가 더 나쁘거나 부분 결과여도 둘 다 남긴다.
- `effective-input.json`: 해당 실행에 실제 적용된 입력과 정원. 후보에는 이 파일의 바이트 해시가 포함된다.
- `check_allocations.py`: 솔버를 불러오지 않고 저장된 배정을 원래 입력에 대조한다. 누락·추가 ID, 금지 연결, 정원 위반, 입력 해시 불일치를 확인하고 배정 수·미배정 목록·비용·자원 사용량을 다시 계산한다.
- 작은 입력은 모든 선택을 열거한 기준 결과와도 비교한다. 탐색 상한을 넘으면 `skipped`로 남기며, 이 경우 최적성·불가능성을 입증하지 않는다. 전체 열거의 결론도 이 작은 입력과 명시한 계약에만 해당한다.

기본 예제에서 먼저 선택한 작업이 선택지가 하나뿐인 작업의 자리를 차지할 수 있다. 저장된 두 결과의 미배정 목록과 비용을 나란히 보고, 배정 수가 다른 결과를 비용만으로 비교하면 왜 잘못되는지 설명해 본다. 비교 기록은 [공통 양식](../templates/candidate-comparison.md)의 필요한 칸만 사용한다. 알고리즘의 우월성을 일반화하거나 다른 실행의 설정값을 섞지 않는다.

## 현재 설정으로 다시 계산

`--capacity`는 이 합성 계약에서 허용한 운영자 입력이다. 설정을 바꾸면 후보와 검사 기준이 모두 새 입력을 사용한다. 원본 JSON은 그대로 남는다.

```sh
python examples/allocation_lab.py --input examples/allocation_input.json --capacity R1=3 --output-dir artifacts/allocation-b
python tools/check_allocations.py --input artifacts/allocation-b/effective-input.json --candidates artifacts/allocation-b/greedy.json artifacts/allocation-b/scarcity.json --output artifacts/allocation-b/comparison.json
```

정원을 `R1=0`으로 바꾼 별도 실행도 확인한다. 배정할 곳이 없는 작업은 미배정으로 표시해야 하며 정원·금지 연결을 어겨 숨기면 안 된다. 새 입력으로 이전 후보를 검사하면 해시 불일치로 비교에서 제외된다. 이것은 CLI에서의 입력·후보 대응 확인이며, 웹 서비스의 경합·원자적 저장이나 브라우저 화면 검증을 대신하지 않는다.

## 입력·검사 범위

입력은 `schema_version: 1`, `resources`의 `id`·`capacity`, `items`의 `id`·`costs`로 구성한다. `costs`에 없는 자원은 그 작업에 배정할 수 없다. 후보의 `assignment`는 모든 작업 ID를 포함하고 자원 ID 또는 `null`을 값으로 가진다. 후보는 `schema_version`, `method`, `input_sha256`, `assignment` 네 필드를 사용한다.

중복 JSON 키·ID, 알 수 없는 필드·자원, 양끝 공백이나 제어 문자가 있는 ID, 음수·불리언·소수 비용/정원은 오류다. ID는 출력 가능한 문자 128자 이내이며, 입력은 4 MiB·자원 1,000개·작업 10,000개·허용 연결 100,000개로 제한한다. 이 상한이 해당 규모의 성능을 보장하지는 않는다. 전체 열거는 기본 200,000개 조합·최대 200개 작업에서만 수행하고, `--oracle-limit`을 높여도 조합 수의 절대 상한은 1,000,000개다. `--no-oracle`로 전체 열거를 생략할 수도 있다.

검사 CLI는 유효한 후보들에 0, 잘못된 후보가 있으면 1, 입력·파일 오류에 2를 반환한다. **종료코드 0은 전원 배정이나 서비스 완성을 뜻하지 않는다.** `completeness`, 미배정 목록, 실제 제약과 전체 열거 상태를 함께 읽는다. 해시는 같은 바이트를 사용했는지 확인하며 자료의 진위·변조 방지를 보장하지 않는다.

이 예제의 도구는 이 배정 계약 전용이다. 실제 작업에서는 해당 문제의 단위·제약·현재 설정·정책·검증 근거를 비교 양식에 명시한다. 실행 시간 비교가 필요하면 입력 준비·계산·검사 중 어디를 측정했는지도 함께 남긴다. CLI 성공을 속도 향상 근거로 삼지 않는다.

## 연결 연습

[두 트랙 리허설](TWO_TRACK_REHEARSAL.md)은 첫 결과의 문제 발견, 기준 전달, 현재 설정의 재계산, 최종 설명을 연결한다. 이 예제는 시작 프롬프트의 필수 실행 단계가 아니다.
