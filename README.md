# Daily Bible Crawler

매일성경 웹사이트에서 말씀과 해설을 스크린샷으로 캡처하여 구글 포토에 업로드하는 프로그램입니다.

## 기능

- 매일성경 웹사이트에서 말씀과 해설 영역을 스크린샷으로 캡처
- 캡처한 이미지를 구글 포토에 자동으로 업로드
- 실패 시 자동 재시도 기능

## 프로젝트 설정

### 필수 요구사항

- Python 3.11 이상
- Poetry (의존성 관리)
- Docker (선택사항)

### 로컬 개발 환경 설정

1. 저장소 클론
```bash
git clone https://github.com/yourusername/daily-bible-crawler.git
cd daily-bible-crawler
```

2. Poetry 설치 (맥OS 기준)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. 의존성 설치
```bash
poetry install
```

4. Playwright 브라우저 설치
```bash
poetry run playwright install chromium
poetry run playwright install-deps
```

## 구글 API 인증 설정

### credentials.json 발급 받기

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. API 및 서비스 > 사용자 인증 정보로 이동
4. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
5. 애플리케이션 유형을 "데스크톱 앱"으로 선택
6. 생성된 클라이언트 ID의 JSON 파일 다운로드
7. 다운로드한 파일을 프로젝트의 `daily_bible_crawler/credentials.json`으로 복사

### token.json 생성하기

1. 처음 프로그램 실행 시 자동으로 브라우저가 열리며 구글 계정 인증 진행
2. 인증 완료 후 자동으로 `daily_bible_crawler/token.json` 생성
3. 이후 실행시에는 저장된 token.json 사용

## 테스트

### 테스트 환경 설정

1. 테스트용 구글 계정 설정
```bash
cp daily_bible_crawler/credentials.json tests/test_credentials.json
cp daily_bible_crawler/token.json tests/test_token.json
```

2. 테스트 의존성 설치
```bash
poetry install --with dev
```

### 테스트 실행

```bash
# 전체 테스트 실행
poetry run pytest

# 특정 테스트 실행
poetry run pytest tests/test_crawler.py

# 커버리지 리포트 생성
poetry run pytest --cov=daily_bible_crawler tests/
```

## 실행 방법

### Poetry로 실행

```bash
poetry run python -m daily_bible_crawler.main
```

### Docker로 실행

```bash
# 이미지 빌드
docker build -t daily-bible-crawler .

# 컨테이너 실행
docker run daily-bible-crawler
```

## 주의사항

1. `credentials.json`과 `token.json`은 민감한 정보이므로 절대 Git에 커밋하지 마세요.
2. 실제 운영 환경에서는 환경 변수나 시크릿 관리 서비스를 사용하는 것을 권장합니다.
3. 구글 포토 API의 일일 할당량을 확인하고 필요한 경우 증가 요청을 하세요.

## 문제 해결

- 인증 오류 발생 시: token.json을 삭제하고 재인증을 진행해보세요.
- 스크린샷 캡처 실패 시: Playwright 브라우저가 제대로 설치되었는지 확인하세요.
- 구글 포토 업로드 실패 시: API 할당량을 확인하세요.
