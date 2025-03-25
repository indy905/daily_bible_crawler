import locale
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import base64
import pickle
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from loguru import logger
from playwright.sync_api import sync_playwright
from tenacity import retry, wait_exponential, stop_after_attempt
import requests

# 환경 변수에서 설정 가져오기
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')  # 앱 비밀번호로 사용 가능
EMAIL_RECIPIENT = os.environ.get('EMAIL_RECIPIENT')  # 콤마로 구분된 이메일 주소 목록
EMAIL_APP_PASSWORD = os.environ.get('EMAIL_APP_PASSWORD')  # Gmail 앱 비밀번호 

# 이메일 수신자 목록 처리 (콤마로 구분된 이메일 주소를 리스트로 변환)
EMAIL_RECIPIENTS = []
if EMAIL_RECIPIENT:
    EMAIL_RECIPIENTS = [email.strip() for email in EMAIL_RECIPIENT.split(',') if email.strip()]
    logger.info(f"이메일 수신자 {len(EMAIL_RECIPIENTS)}명이 설정되었습니다.")

# 현재 스크립트의 디렉토리 경로를 기준으로 절대 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OAUTH_TOKEN_PATH = os.environ.get('OAUTH_TOKEN_PATH', os.path.join(SCRIPT_DIR, 'token.pickle'))  # OAuth 토큰 저장 경로
OAUTH_CREDENTIALS_PATH = os.environ.get('OAUTH_CREDENTIALS_PATH', os.path.join(SCRIPT_DIR, 'credentials.json'))  # OAuth 인증 정보 경로

# 웹사이트 URL 상수 정의
WEBSITE_URL = "https://sum.su.or.kr:8888/bible/today"

# 로거 설정
logger.add("bible_crawler.log", rotation="1 day", retention="7 days")
locale.setlocale(locale.LC_TIME, 'ko_KR.UTF-8')

# 기존 이메일 전송 함수 (주석 처리)
"""
def send_email(subject, html_content):
    \"\"\"HTML 형식의 이메일을 전송하는 함수\"\"\"
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"이메일 전송 완료: {subject}")
        
    except Exception as e:
        logger.error(f"이메일 전송 중 오류 발생: {str(e)}")
        raise
"""

def send_email_with_app_password(subject, html_content):
    """
    Gmail 앱 비밀번호를 사용하여 HTML 첨부 파일 형식의 이메일을 전송하는 함수
    
    Gmail 앱 비밀번호는 Google 계정 보안 설정에서 생성할 수 있습니다.
    https://myaccount.google.com/apppasswords
    
    Args:
        subject (str): 이메일 제목
        html_content (str): HTML 형식의 이메일 내용
    """
    try:
        if not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECIPIENTS:
            logger.warning("이메일 전송에 필요한 앱 비밀번호 설정이 없습니다.")
            return
        
        for recipient in EMAIL_RECIPIENTS:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # 간단한 본문 텍스트 추가
            plain_text = "오늘의 성경 말씀과 해설을 첨부파일로 보내드립니다. 첨부된 HTML 파일을 열어 확인해 주세요."
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            
            # HTML 파일 첨부
            today_date = datetime.now().strftime('%Y%m%d')
            html_attachment = MIMEText(html_content, 'html', 'utf-8')
            html_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f'bible_content_{today_date}.html')
            msg.attach(html_attachment)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                # 앱 비밀번호 사용
                server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"앱 비밀번호로 이메일 전송 완료: {subject} -> {recipient}")
        
    except Exception as e:
        logger.error(f"앱 비밀번호 이메일 전송 중 오류 발생: {str(e)}")
        raise

def send_email_with_oauth2(subject, html_content):
    """
    OAuth2를 사용하여 Gmail API로 HTML 첨부 파일 형식의 이메일을 전송하는 함수
    
    OAuth2 인증은 Google Cloud Console에서 설정한 OAuth 클라이언트 ID와 비밀번호가 필요합니다.
    https://console.cloud.google.com/apis/credentials
    
    Args:
        subject (str): 이메일 제목
        html_content (str): HTML 형식의 이메일 내용
    """
    try:
        # Gmail API 권한 범위 설정
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        
        creds = None
        # 저장된 토큰이 있으면 로드
        if os.path.exists(OAUTH_TOKEN_PATH):
            with open(OAUTH_TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
                
        # 유효한 인증 정보가 없으면 사용자에게 인증 요청
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(OAUTH_CREDENTIALS_PATH):
                    logger.error(f"OAuth 인증 정보 파일({OAUTH_CREDENTIALS_PATH})이 없습니다.")
                    logger.error("Google Cloud Console에서 OAuth 클라이언트 ID를 생성하고 credentials.json 파일을 다운로드하세요.")
                    return
                    
                flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
                
            # 다음 실행을 위해 토큰 저장
            with open(OAUTH_TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
                
        # Gmail API 서비스 생성
        service = build('gmail', 'v1', credentials=creds)
        
        for recipient in EMAIL_RECIPIENTS:
            # 이메일 메시지 생성
            message = MIMEMultipart()
            message['to'] = recipient
            message['from'] = EMAIL_SENDER
            message['subject'] = subject
            
            # 간단한 본문 텍스트 추가
            plain_text = "오늘의 성경 말씀과 해설을 첨부파일로 보내드립니다. 첨부된 HTML 파일을 열어 확인해 주세요."
            message.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            
            # HTML 파일 첨부
            today_date = datetime.now().strftime('%Y%m%d')
            html_attachment = MIMEText(html_content, 'html', 'utf-8')
            html_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f'bible_content_{today_date}.html')
            message.attach(html_attachment)
            
            # 메시지를 바이트로 변환하고 base64로 인코딩
            raw = base64.urlsafe_b64encode(message.as_bytes())
            raw = raw.decode()
            body = {'raw': raw}
            
            # 메시지 전송
            message_result = (service.users().messages().send(userId='me', body=body).execute())
            logger.info(f"OAuth2로 이메일 전송 완료: {subject} -> {recipient} (메시지 ID: {message_result['id']})")
        
    except HttpError as error:
        logger.error(f"OAuth2 이메일 전송 중 API 오류 발생: {error}")
        raise
    except Exception as e:
        logger.error(f"OAuth2 이메일 전송 중 오류 발생: {str(e)}")
        raise

# 기본 이메일 전송 함수
def send_email(subject, html_content):
    """
    이메일 전송 함수의 래퍼 함수입니다.
    
    1. OAuth2가 설정되어 있으면 OAuth2로 전송
    2. 앱 비밀번호가 설정되어 있으면 앱 비밀번호로 전송
    3. 둘 다 없으면 경고 메시지 표시
    
    Args:
        subject (str): 이메일 제목
        html_content (str): HTML 형식의 이메일 내용
    """
    try:
        # OAuth2 설정이 있는지 확인
        if os.path.exists(OAUTH_CREDENTIALS_PATH):
            send_email_with_oauth2(subject, html_content)
        # 앱 비밀번호가 있는지 확인
        elif EMAIL_APP_PASSWORD:
            send_email_with_app_password(subject, html_content)
        # 기존 비밀번호가 있는지 확인
        elif EMAIL_PASSWORD:
            logger.warning("일반 비밀번호는 보안 위험이 있습니다. 앱 비밀번호나 OAuth2를 사용하세요.")
            logger.warning("앱 비밀번호는 Google 계정 보안 설정에서 생성할 수 있습니다: https://myaccount.google.com/apppasswords")
        else:
            logger.warning("이메일 설정이 완료되지 않아 이메일 전송을 건너뜁니다.")
            logger.info("이메일 전송을 위해 다음 중 하나를 설정하세요:")
            logger.info("1. OAuth2: Google Cloud Console에서 OAuth 클라이언트 ID를 생성하고 credentials.json 파일을 다운로드")
            logger.info("2. 앱 비밀번호: EMAIL_APP_PASSWORD 환경 변수 설정")
    except Exception as e:
        logger.error(f"이메일 전송 중 오류 발생: {str(e)}")
        
# @retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def capture_bible_content():
    """
    웹사이트에서 말씀과 해설 내용을 추출합니다.
    
    웹사이트에서 말씀(성경 구절)과 해설 내용을 추출하고 구조화된 형태로 반환합니다.
    Playwright를 사용하여 웹 페이지를 렌더링하고 JavaScript를 실행하여 내용을 추출합니다.
    
    Returns:
        tuple: (텍스트 내용(dict), HTML 내용(str), CSS 내용(str))
            - 텍스트 내용: {'말씀': str, '해설': str} 형태의 딕셔너리
            - HTML 내용: 구조화된 HTML 문자열
            - CSS 내용: 웹사이트에서 추출한 CSS 스타일
    """
    logger.info("웹사이트 접속 중...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(WEBSITE_URL)
        
        # 페이지의 전체 HTML 구조를 로깅
        page_content = page.content()
        logger.info(f"페이지 내용 길이: {len(page_content)}")
        logger.info("페이지 HTML 구조 확인")
        
        # 웹사이트 구조 분석을 위한 스크립트 실행
        bible_structure = page.evaluate('''
            () => {
                // 말씀 영역 분석
                const bibleContainer = document.querySelector('#font_uparea02');
                const bibleInfo = {
                    exists: !!bibleContainer,
                    id: bibleContainer ? bibleContainer.id : null,
                    className: bibleContainer ? bibleContainer.className : null,
                    children: bibleContainer ? bibleContainer.children.length : 0,
                    text: bibleContainer ? bibleContainer.innerText.substring(0, 100) + '...' : null
                };
                
                // 해설 영역 분석
                const explanationContainer = document.querySelector('#font_uparea03');
                const explanationInfo = {
                    exists: !!explanationContainer,
                    id: explanationContainer ? explanationContainer.id : null,
                    className: explanationContainer ? explanationContainer.className : null,
                    children: explanationContainer ? explanationContainer.children.length : 0,
                    text: explanationContainer ? explanationContainer.innerText.substring(0, 100) + '...' : null
                };
                
                return {
                    bible: bibleInfo,
                    explanation: explanationInfo
                };
            }
        ''')
        logger.info(f"웹사이트 구조: {bible_structure}")
        
        # CSS 스타일 추출
        css_content = page.evaluate('''
            () => {
                const styleSheets = Array.from(document.styleSheets);
                return styleSheets.map(sheet => {
                    try {
                        return Array.from(sheet.cssRules).map(rule => rule.cssText).join('\\n');
                    } catch (e) {
                        return '';
                    }
                }).join('\\n');
            }
        ''')
        
        # 말씀 영역 텍스트 및 HTML 추출
        logger.info("말씀 영역 텍스트 및 HTML 추출 중...")
        
        # 말씀 데이터 추출 - 더 구조화된 방식으로
        bible_data = page.evaluate('''
            () => {
                const bibleDiv = document.querySelector('#font_uparea02');
                if (!bibleDiv) return { header: '', verses: [] };
                
                // 텍스트 내용 가져오기
                const fullText = bibleDiv.innerText;
                const lines = fullText.split('\\n').filter(line => line.trim());
                
                // 헤더 정보 (날짜, 제목, 본문 등) 추출
                let headerEndIndex = 0;
                while (headerEndIndex < lines.length && !lines[headerEndIndex].match(/^\\d+\\s/)) {
                    headerEndIndex++;
                }
                
                const headerLines = lines.slice(0, headerEndIndex);
                const header = headerLines.join('\\n');
                
                // 성경 구절 추출 (숫자로 시작하는 줄)
                const versesLines = lines.slice(headerEndIndex);
                const verses = [];
                
                for (let i = 0; i < versesLines.length; i++) {
                    const line = versesLines[i];
                    const match = line.match(/^(\\d+)\\s(.+)$/);
                    
                    if (match) {
                        verses.push({
                            number: match[1],
                            text: match[2]
                        });
                    }
                }
                
                return { header, verses };
            }
        ''')
        
        logger.info(f"추출된 구절 수: {len(bible_data.get('verses', []))}")
        
        # 헤더 정보
        bible_header = bible_data.get('header', '')
        # 구절 정보
        bible_verses = bible_data.get('verses', [])
        
        # 말씀 HTML 구성
        bible_html = '<div class="bible-header">'
        # 백슬래시 문제 해결을 위해 f-string 대신 format 메서드 사용
        bible_header_with_breaks = bible_header.replace('\n', '<br>')
        bible_html += '<div class="bible-info">{0}</div>'.format(bible_header_with_breaks)
        bible_html += '</div>'
        
        bible_html += '<div class="bible-content">'
        for verse in bible_verses:
            verse_num = verse.get('number', '')
            verse_text = verse.get('text', '')
            bible_html += f'<div class="bible-verse"><span class="verse-number">{verse_num}</span><span class="verse-text">{verse_text}</span></div>'
        bible_html += '</div>'
        
        # 해설 영역 텍스트 및 HTML 추출
        logger.info("해설 영역 텍스트 및 HTML 추출 중...")
        
        # 해설 탭으로 이동 시도
        try:
            page.locator("#mainTitle_3").click()
            try:
                page.wait_for_load_state("networkidle")
                logger.info("해설 탭으로 이동 완료")
            except Exception as e:
                logger.warning(f"wait_for_load_state 호출 중 오류 발생: {e}, 계속 진행합니다.")
        except Exception as e:
            logger.error(f"해설 탭 이동 실패: {e}")
        
        explanation_data = page.evaluate('''
            () => {
                const explanation = {};
                
                // 제목 추출
                const titleElement = document.querySelector('.b_text');
                explanation.title = titleElement ? titleElement.innerText : '';
                
                // 섹션 추출
                explanation.sections = [];
                
                // 더 정확한 섹션 선택자 찾기
                const explanationDiv = document.querySelector('#font_uparea03');
                if (explanationDiv) {
                    // 메인 설명 텍스트 영역
                    const mainTextDiv = explanationDiv.querySelector('.body_text');
                    
                    // 각 섹션 추출 (g_text는 제목, 다음 형제 요소는 내용)
                    const sectionElements = explanationDiv.querySelectorAll('.g_text');
                    
                    for (let i = 0; i < sectionElements.length; i++) {
                        const subtitle = sectionElements[i].innerText.trim();
                        let content = '';
                        
                        // 제목 다음 요소에서 실제 내용 찾기
                        let nextElement = sectionElements[i].nextElementSibling;
                        while (nextElement && !nextElement.classList.contains('g_text')) {
                            // text 클래스를 가진 요소만 처리
                            if (nextElement.classList.contains('text')) {
                                content = nextElement.innerText.trim();
                                break;
                            }
                            nextElement = nextElement.nextElementSibling;
                        }
                        
                        if (subtitle || content) {
                            explanation.sections.push({ subtitle, content });
                        }
                    }
                }
                
                // 정보 추출
                const infoElement = document.querySelector('#dailybible_info2');
                explanation.info = infoElement ? infoElement.innerText : '';
                
                return explanation;
            }
        ''')
        
        logger.info(f"해설 데이터: {explanation_data}")
        
        # 추출한 데이터 구조화
        explanation_title = explanation_data.get('title', '')
        explanation_sections = explanation_data.get('sections', [])
        explanation_info = explanation_data.get('info', '')
        
        # 해설 텍스트 구성
        explanation_text = f"{explanation_title}\n\n"
        for section in explanation_sections:
            subtitle = section.get('subtitle', '')
            content = section.get('content', '')
            explanation_text += f"{subtitle}\n{content}\n\n"
        explanation_text += f"{explanation_info}"
        
        # 해설 HTML 구성
        explanation_html = '<div class="explanation-wrapper">'
        explanation_html += f'<h2 class="explanation-title">{explanation_title}</h2>'
        
        for section in explanation_sections:
            subtitle = section.get('subtitle', '')
            content = section.get('content', '')
            # 줄바꿈을 HTML <br> 태그로 변환하여 해설 내용에 반영
            content_with_breaks = content.replace('\n\n', '<br><br>').replace('\n', '<br>')
            
            explanation_html += f'<div class="explanation-section">'
            explanation_html += f'<h3 class="explanation-subtitle">{subtitle}</h3>'
            explanation_html += f'<div class="explanation-content">{content_with_breaks}</div>'
            explanation_html += '</div>'
        
        explanation_html += f'<div class="explanation-info">{explanation_info}</div>'
        explanation_html += '</div>'
        
        # 텍스트 내용을 딕셔너리로 구성
        content = {
            "말씀": f"{bible_header}\n\n" + '\n'.join([f"{verse.get('number')}. {verse.get('text')}" for verse in bible_verses]),
            "해설": explanation_text
        }
        
        # HTML 내용 구성
        html_content = f'''
        <div class="bible-wrapper">
            <h1 class="section-title">말씀</h1>
            {bible_html}
        </div>
        <div class="explanation-container">
            <h1 class="section-title">해설</h1>
            {explanation_html}
        </div>
        '''
        
        browser.close()
        
    return content, html_content, css_content

def create_html_email(content, html_content, css_content):
    """
    HTML 형식의 이메일 내용을 생성합니다.
    
    추출된 성경 말씀과 해설 내용을 이메일로 보내기 위한 HTML 형식으로 변환합니다.
    
    Args:
        content (dict): {'말씀': str, '해설': str} 형태의 텍스트 내용
        html_content (str): 구조화된 HTML 콘텐츠
        css_content (str): 적용할 CSS 스타일
        
    Returns:
        str: 완성된 HTML 이메일 내용
    """
    today_date = datetime.now().strftime('%Y년 %m월 %d일 (%A)')
    
    # 기본 HTML 구조
    email_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 말씀 - {today_date}</title>
        <style>
            body {{
                font-family: 'Malgun Gothic', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 1px solid #16a085;
                padding-bottom: 10px;
            }}
            .section-title {{
                font-size: 24px;
                font-weight: bold;
                margin-top: 30px;
                margin-bottom: 20px;
                color: #2c3e50;
                border-bottom: 2px solid #16a085;
                padding-bottom: 10px;
            }}
            .bible-header {{
                margin-bottom: 20px;
                font-size: 16px;
                color: #555;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }}
            .bible-info {{
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                line-height: 1.7;
                background-color: #f5f9f8;
                padding: 15px;
                border-left: 4px solid #16a085;
                border-radius: 4px;
            }}
            .bible-content {{
                margin-bottom: 30px;
                font-size: 18px;
                line-height: 1.8;
            }}
            .bible-verse {{
                margin-bottom: 15px;
            }}
            .verse-number {{
                font-weight: bold;
                margin-right: 10px;
                color: #16a085;
            }}
            .verse-text {{
                display: inline;
            }}
            .explanation-wrapper {{
                background-color: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 30px;
            }}
            .explanation-title {{
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }}
            .explanation-section {{
                margin-bottom: 20px;
            }}
            .explanation-subtitle {{
                font-size: 18px;
                font-weight: bold;
                color: #16a085;
                margin-bottom: 10px;
            }}
            .explanation-content {{
                line-height: 1.8;
            }}
            .explanation-info {{
                font-style: italic;
                color: #7f8c8d;
                margin-top: 15px;
                font-size: 14px;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 14px;
                color: #7f8c8d;
                border-top: 1px solid #16a085;
                padding-top: 10px;
            }}
            /* 추가 사용자 정의 스타일 */
            {css_content}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>오늘의 말씀 - {today_date}</h1>
        </div>
        
        {html_content}
        
        <div class="footer">
            <p>본 메일은 자동으로 발송되었습니다.</p>
        </div>
    </body>
    </html>
    """
    
    return email_html

def main():
    """
    프로그램의 메인 함수입니다.
    
    1. 웹사이트에서 성경 말씀과 해설을 추출합니다.
    2. 텍스트 파일로 저장합니다.
    3. HTML 파일로 저장합니다.
    4. 이메일 설정이 있는 경우 이메일을 전송합니다.
    
    오류가 발생하면 로깅 후 예외를 발생시킵니다.
    """
    try:
        logger.info("프로그램 시작")
        
        # 텍스트 및 HTML 내용 추출
        content, html_content, css_content = capture_bible_content()
        
        # 디렉토리 생성 (존재하지 않는 경우)
        os.makedirs("texts", exist_ok=True)
        
        # 날짜 형식의 파일 이름 생성
        today_date = datetime.now().strftime('%Y%m%d')
        file_path = os.path.join("texts", f"bible_content_{today_date}.txt")
        
        # content 타입 로깅
        logger.info(f"Content type: {type(content)}")
        
        # 텍스트 파일로 저장
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if isinstance(content, dict):
                    for description, text in content.items():
                        f.write(f"===== {description} =====\n\n{text}\n\n")
                else:
                    # content가 문자열인 경우 그대로 저장
                    f.write(str(content))
            logger.info(f"내용이 {file_path} 파일에 저장되었습니다.")
        except Exception as e:
            logger.error(f"텍스트 파일 저장 중 오류 발생: {str(e)}")
            raise
        
        # HTML 이메일 내용 생성
        html_email = create_html_email(content, html_content, css_content)
        
        # HTML 파일로 저장
        html_file_path = os.path.join("texts", f"bible_content_{today_date}.html")
        try:
            with open(html_file_path, "w", encoding="utf-8") as f:
                f.write(html_email)
            logger.info(f"HTML 내용이 {html_file_path} 파일에 저장되었습니다.")
        except Exception as e:
            logger.error(f"HTML 파일 저장 중 오류 발생: {str(e)}")
            raise
        
        # 이메일 전송 (환경 변수가 설정된 경우에만 실행)
        # if EMAIL_SENDER and EMAIL_PASSWORD and EMAIL_RECIPIENT:
        email_subject = f"[매일성경] 오늘의 말씀 - {datetime.now().strftime('%Y-%m-%d (%A)')}"
        try:
            send_email(email_subject, html_email)
        except Exception as e:
            logger.error(f"이메일 전송 중 오류 발생: {str(e)}")
            # 이메일 전송 실패는 프로그램을 중단시키지 않음
        # else:
        # #     logger.warning("이메일 설정이 완료되지 않아 이메일 전송을 건너뜁니다.")
        
        logger.info("프로그램 정상 종료")
        
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main() 