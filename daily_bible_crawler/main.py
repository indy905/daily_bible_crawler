import os
import json
import time
from pathlib import Path
from datetime import datetime

from loguru import logger
from playwright.sync_api import sync_playwright
from tenacity import retry, wait_exponential, stop_after_attempt
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests

# 로거 설정
logger.add("bible_crawler.log", rotation="1 day", retention="7 days")

class GooglePhotoUploader:
    """구글 포토 API를 사용하여 이미지를 업로드하는 클래스"""
    
    def __init__(self, token_path: str, credentials_path: str):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """구글 API 인증을 처리하는 메서드"""
        if os.path.exists(self.token_path):
            with open(self.token_path, 'r') as token:
                self.creds = Credentials.from_authorized_user_file(self.token_path)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    ['https://www.googleapis.com/auth/photoslibrary.appendonly']
                )
                self.creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    def upload_image(self, image_path: str, description: str):
        """이미지를 구글 포토에 업로드하는 메서드"""
        try:
            service = build('photoslibrary', 'v1', credentials=self.creds, static_discovery=False)
            
            upload_token = self._upload_media(image_path)
            
            request_body = {
                'newMediaItems': [{
                    'description': description,
                    'simpleMediaItem': {
                        'uploadToken': upload_token
                    }
                }]
            }

            upload_response = service.mediaItems().batchCreate(body=request_body).execute()
            logger.info(f"이미지 업로드 완료: {description}")
            return upload_response
            
        except Exception as e:
            logger.error(f"이미지 업로드 중 오류 발생: {str(e)}")
            raise

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
    def _upload_media(self, image_path: str):
        """이미지 파일을 구글 포토에 업로드하고 업로드 토큰을 반환하는 메서드"""
        headers = {
            'Authorization': f'Bearer {self.creds.token}',
            'Content-Type': 'application/octet-stream',
            'X-Goog-Upload-Protocol': 'raw',
        }
        
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                'https://photoslibrary.googleapis.com/v1/uploads',
                headers=headers,
                data=image_file.read()
            )
            response.raise_for_status()
            return response.content.decode('utf-8')

@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def capture_bible_content():
    """성경 말씀 웹사이트에서 스크린샷을 캡처하는 함수"""
    screenshots = []
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            logger.info("웹사이트 접속 중...")
            page.goto("https://sum.su.or.kr:8888/bible/today")
            page.wait_for_load_state("networkidle")
            
            # 말씀 영역 스크린샷
            logger.info("말씀 영역 스크린샷 캡처 중...")
            word_element = page.locator("#font_uparea02")
            word_path = f"screenshots/word_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            os.makedirs("screenshots", exist_ok=True)
            word_element.screenshot(path=word_path)
            screenshots.append(("말씀", word_path))
            
            # 해설 클릭 및 스크린샷
            logger.info("해설 영역 스크린샷 캡처 중...")
            page.locator("#mainTitle_3").click()
            page.wait_for_load_state("networkidle")
            
            explanation_element = page.locator("#font_uparea03")
            explanation_path = f"screenshots/explanation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            explanation_element.screenshot(path=explanation_path)
            screenshots.append(("해설", explanation_path))
            
            browser.close()
            return screenshots
            
        except Exception as e:
            logger.error(f"스크린샷 캡처 중 오류 발생: {str(e)}")
            raise

def main():
    """메인 함수"""
    try:
        logger.info("프로그램 시작")
        
        # 스크린샷 캡처
        screenshots = capture_bible_content()
        
        # 구글 포토 업로더 초기화
        uploader = GooglePhotoUploader(
            token_path="daily_bible_crawler/token.json",
            credentials_path="daily_bible_crawler/credentials.json"
        )
        
        # 캡처한 스크린샷 업로드
        for description, image_path in screenshots:
            logger.info(f"{description} 이미지 업로드 중...")
            uploader.upload_image(
                image_path=image_path,
                description=f"오늘의 말씀 - {description} ({datetime.now().strftime('%Y-%m-%d')})"
            )
        
        logger.info("프로그램 정상 종료")
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main() 