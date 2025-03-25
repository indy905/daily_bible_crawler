# Daily Bible Crawler

매일성경 웹사이트에서 말씀과 해설을 크롤링하여 이메일로 전송하는 프로그램입니다.

## 기능

- 매일성경 웹사이트에서 말씀과 해설 내용을 크롤링
- 크롤링한 내용을 텍스트와 HTML 파일로 저장
- 이메일로 자동 전송 (Gmail OAuth2 또는 앱 비밀번호 사용)

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

## 이메일 설정

### 1. Gmail OAuth2 설정 (권장)

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. Gmail API 활성화
4. API 및 서비스 > 사용자 인증 정보로 이동
5. "사용자 인증 정보 만들기" > "OAuth 클라이언트 ID" 선택
6. 애플리케이션 유형을 "데스크톱 앱"으로 선택
7. 생성된 클라이언트 ID의 JSON 파일 다운로드
8. 다운로드한 파일을 프로젝트의 `daily_bible_crawler/credentials.json`으로 복사

### 2. Gmail 앱 비밀번호 설정 (대체 방법)

1. [Google 계정 보안 설정](https://myaccount.google.com/security)에 접속
2. 2단계 인증 활성화
3. 앱 비밀번호 생성
4. 생성된 앱 비밀번호를 환경 변수로 설정:
```bash
export EMAIL_APP_PASSWORD='your_app_password'
```

## 환경 변수 설정

```bash
# 이메일 설정 (필수)
export EMAIL_SENDER='your_email@gmail.com'
export EMAIL_RECIPIENT='recipient_email@example.com'

# Gmail 앱 비밀번호 사용 시
export EMAIL_APP_PASSWORD='your_app_password'
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

# 컨테이너 실행 (앱 비밀번호 사용 시)
docker run -e EMAIL_SENDER='your_email@gmail.com' \
          -e EMAIL_RECIPIENT='recipient_email@example.com' \
          -e EMAIL_APP_PASSWORD='your_app_password' \
          daily-bible-crawler

# 컨테이너 실행 (OAuth2 사용 시)
docker run -v /path/to/credentials.json:/app/daily_bible_crawler/credentials.json \
          -v /path/to/token.pickle:/app/daily_bible_crawler/token.pickle \
          daily-bible-crawler
```

## 주의사항

1. `credentials.json`과 `token.pickle`은 민감한 정보이므로 절대 Git에 커밋하지 마세요.
2. 실제 운영 환경에서는 환경 변수나 시크릿 관리 서비스를 사용하는 것을 권장합니다.

## 문제 해결

- OAuth2 인증 오류: token.pickle을 삭제하고 재인증을 진행해보세요.
- 이메일 전송 실패: 인증 설정을 확인하세요.
- 크롤링 실패: Playwright 브라우저가 제대로 설치되었는지 확인하세요.
