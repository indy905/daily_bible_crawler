import os
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from daily_bible_crawler.main import capture_bible_content

@patch('daily_bible_crawler.main.sync_playwright')
def test_capture_bible_content(mock_playwright):
    # Mock Playwright objects
    mock_browser = Mock()
    mock_page = Mock()
    
    # Setup mock chain
    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page
    
    # Mock page.content() 메서드
    mock_page.content.return_value = "<html><body>Mock HTML Content</body></html>"
    
    # Mock page.evaluate 메서드 호출 결과
    mock_page.evaluate.side_effect = [
        # 웹사이트 구조
        {
            'bible': {'exists': True, 'id': 'font_uparea02', 'className': '', 'children': 8},
            'explanation': {'exists': True, 'id': 'font_uparea03', 'className': '', 'children': 5}
        },
        # CSS 추출
        "body { font-family: sans-serif; }",
        # 성경 말씀 추출
        {
            'header': '매일성경 2025.03.24(월)\n제자도\n본문 : 누가복음(Luke) 14:25 - 14:35',
            'verses': [
                {'number': '25', 'text': '수많은 무리가 함께 갈새 예수께서 돌이키사 이르시되'},
                {'number': '26', 'text': '무릇 내게 오는 자가 자기 부모와 처자와 형제와 자매와 더욱이 자기 목숨까지 미워하지 아니하면 능히 내 제자가 되지 못하고'}
            ]
        },
        # 해설 추출
        {
            'title': '예수님을 따르는 많은 무리를 보시고 제자가 되려면 그에 따르는 분명한 대가가 있음을 알고 따라야 한다고 말씀하십니다.',
            'sections': [
                {
                    'subtitle': '예수님은 어떤 분입니까?',
                    'content': '전체 예수님이 원하시는 것은 더 많은 추종자가 아니라 진정한 제자입니다.'
                },
                {
                    'subtitle': '내게 주시는 교훈은 무엇입니까?',
                    'content': '26-33절 예수님을 따르는 제자에게 요구되는 세 가지 덕목이 있습니다.'
                }
            ],
            'info': '매일성경 2025.03.24(월)'
        }
    ]
    
    # 해설 탭 클릭 모의
    mock_click = Mock()
    mock_page.locator.return_value = mock_click
    
    # 함수 호출 중 발생할 수 있는 예외 처리
    try:
        content, html_content, css_content = capture_bible_content()
    except Exception as e:
        pytest.fail(f"테스트 실패: {str(e)}")
    
    # 검증
    assert "말씀" in content
    assert "해설" in content
    assert "매일성경 2025.03.24(월)" in content["말씀"]
    assert "예수님을 따르는 많은 무리를" in content["해설"]
    assert "bible-content" in html_content
    assert "explanation-wrapper" in html_content
    assert "body { font-family: sans-serif; }" == css_content
    
    # 메서드 호출 검증
    mock_page.goto.assert_called_once_with("https://sum.su.or.kr:8888/bible/today")
    mock_page.evaluate.assert_called()
    mock_page.locator.assert_called_with("#mainTitle_3") 