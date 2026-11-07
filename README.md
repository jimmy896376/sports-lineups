# 스포츠 라인업

축구·야구·농구·배구·하키 주요 리그의 오늘부터 5일간 한국시간 일정과 선발 명단을 표시합니다. 지원 범위는 화면의 종목 메뉴와 `dist/app.js`의 `sources` 목록을 기준으로 합니다.

- 공개 사이트: https://sports-lineups.fuzzyloach5.chatgpt.site/ (`.openai/hosting.json`)
- 화면: `dist/index.html`, `dist/app.js`, `dist/style.css`
- 선수 이름 한국어 표기: `dist/football-ko.js`, `dist/player-ko.js`
- 예상 명단 자료: `dist/projections.json`
- 예상 명단 갱신: GitHub Actions `refresh-lineups.yml`에서 15분 간격으로 `python3 scripts/update-projections.py` 실행

리그에 따라 ESPN 일정·경기 데이터와 별도 리그 자료원을 사용합니다. 예상 명단은 마지막 성공 시점의 스냅샷입니다. 개별 자료원 갱신에 실패하면 5일 표시 기간에 해당하는 마지막 자료만 유지하고, 화면에 자료 시각과 갱신 실패를 표시합니다. 일정과 선발 시각은 한국시간으로 표시합니다. 자료원 주소는 내부 스크립트에 남기고 공개 화면에는 표시하지 않습니다.

WKBL 일정은 공식 월간 일정표에서 읽습니다. 새 시즌 첫 경기 전에는 검증된 이전 선발 5명이 없으므로 경기 시간만 게시하고 선발을 임의로 채우지 않습니다. CPBL 공식 예고투수 자료원은 GitHub 서버에서 403을 반환할 수 있어, 다른 공개 자료와 대조해 등록한 경기별 예고만 보완합니다.

GitHub Actions의 라인업·선수명·승부예측 작업은 사용자 컴퓨터나 Codex 실행 여부와 무관하게 돌아갑니다. 각 작업은 자기 결과 파일만 게시하고, 다른 작업이 그 파일을 먼저 바꾸면 덮어쓰지 않고 다음 실행에서 다시 수집합니다. GitHub 예약 실행 시각은 보장되지 않으므로 화면의 자료 시각도 확인해야 합니다.

이전 쇼츠 작업현황판의 사용하지 않는 라인업 코드는 `legacy/workboard-lineups/`에 보관합니다.

## 선수명 검수

통용되는 한국어 이름과 확인한 별칭을 공통 사전에 저장합니다. 구글 검색, 한국어 스포츠 기사와 구단 자료로 신원을 대조합니다. 검색 결과의 자동 음역이나 성만 일치하는 이름을 적용하지 않습니다. 미등록 이름은 검수 대기 상태이며, 한글 표기가 없다고 판단하지 않습니다.

`node scripts/check-player-names.mjs --audit`는 모든 리그·날짜의 예상 선발과 부상자 목록을 검사하고 `scripts/player-name-audit.json`에 미등록 이름과 검색 링크를 기록합니다. 최신 외부 스냅샷을 점검하려면 `--input /absolute/path/projections.json`을 지정합니다. GitHub 갱신 작업에서도 같은 검사를 실행하고 보고서를 3일간 아티팩트로 보관합니다.

`node scripts/collect-player-names.mjs`는 실제 화면의 모든 리그를 실행해 오늘·내일의 ESPN 실시간 선발, 최근 경기 기반 선발, 부상자까지 수집합니다. 이어 `node scripts/check-player-names.mjs --inventory scripts/player-name-live-inventory.json`으로 검사합니다. GitHub 갱신 작업은 이 검사도 실행하고 결과를 아티팩트로 보관합니다. 수집 실패는 보고서에 남기고 작업을 실패 처리하므로 부분 수집을 전체 점검으로 표시하지 않습니다.

재현 가능한 검수는 `node scripts/check-player-names.mjs --inventory scripts/fixtures/player-name-inventory.json --require-reviewed`로 실행합니다. 미검수 이름이 있으면 실패합니다. 한글 자료가 없거나 표기가 충돌하는 이름은 `scripts/player-name-exceptions.json`에 근거와 함께 영어 유지로 명시합니다. 이번 대조에서 추가한 603개 표기의 근거는 `scripts/player-name-source-review.json`에 있습니다. 근거 링크는 사이트 화면에 출력하지 않습니다.

GitHub의 선수명 작업은 오늘·내일 경기 명단을 수집한 뒤 공개 검색과 한국어 위키 링크를 대조합니다. 검증에 통과한 이름은 `dist/name-catalog.json`에 자동 게시되며, 화면은 새로고침할 때 이 파일을 다시 읽습니다. 검색 차단, 팀 신원 불일치, 표기 충돌이 있으면 영어를 유지합니다. 현재 기간에 경기가 없는 리그의 미래 선수까지 검수 완료했다고 주장하지 않습니다.

팀명은 `dist/team-ko.json`에 확인한 전체 이름·별칭을 저장하고, 구글 대조 근거는 `scripts/team-name-review.json`에 남깁니다. 경기 머리글, 선발 팀명, 부상자 팀명에 같은 표기를 사용합니다.

페이지 새로고침, 새로고침 버튼, 5분 갱신, 리그·언어 전환마다 팀명 사전도 캐시 없이 다시 받아 현재 표시 명단을 대조합니다. 화면의 ‘저장 표기 대조’는 사전과의 비교이며 구글 실시간 재검색을 뜻하지 않습니다. 새 이름은 브라우저의 `sports-lineups-name-review` 기록과 GitHub의 `team-name-live-audit.json` 아티팩트에서 검수 대기로 확인할 수 있습니다. 구글 자동 검색 API는 연결하지 않았으며, CAPTCHA를 우회하지 않습니다.
