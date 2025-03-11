FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
RUN pip install poetry

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 설정 (가상환경 생성하지 않음)
RUN poetry config virtualenvs.create false

# 프로젝트 파일 복사
COPY pyproject.toml poetry.lock README.md ./
COPY daily_bible_crawler ./daily_bible_crawler
COPY tests ./tests

# 의존성 설치 (개발 의존성 제외)
RUN poetry install --without dev --no-root

# Playwright 설치 및 브라우저 설치
RUN poetry run playwright install chromium
RUN poetry run playwright install-deps

# 구글 인증 파일 복사
COPY daily_bible_crawler/token.json ./daily_bible_crawler/
COPY daily_bible_crawler/credentials.json ./daily_bible_crawler/

# 스크린샷 저장 디렉토리 생성
RUN mkdir -p screenshots

# 실행 명령
CMD ["poetry", "run", "python", "-m", "daily_bible_crawler.main"] 