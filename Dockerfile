FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    locales \
    && rm -rf /var/lib/apt/lists/*

# 한국어 로케일 설정
RUN sed -i '/ko_KR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ENV LANG=ko_KR.UTF-8
ENV LANGUAGE=ko_KR:ko
ENV LC_ALL=ko_KR.UTF-8

# Poetry 설치
RUN pip install poetry

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 설정 (가상환경 생성하지 않음)
RUN poetry config virtualenvs.create false

# 프로젝트 파일 복사
COPY pyproject.toml poetry.lock ./
COPY daily_bible_crawler ./daily_bible_crawler/

# 의존성 설치
RUN poetry install --no-root

# Playwright 설치 및 브라우저 설치
RUN poetry run playwright install chromium
RUN poetry run playwright install-deps

# 필요한 디렉토리 생성
RUN mkdir -p screenshots texts

# 실행 명령
CMD ["poetry", "run", "python", "-m", "daily_bible_crawler.main"] 