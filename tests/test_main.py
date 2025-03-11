import os
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from daily_bible_crawler.main import GooglePhotoUploader, capture_bible_content

@pytest.fixture
def mock_credentials():
    return {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "test_uri",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret"
    }

@pytest.fixture
def uploader(mock_credentials, tmp_path):
    token_path = tmp_path / "token.json"
    creds_path = tmp_path / "credentials.json"
    with open(token_path, 'w') as f:
        f.write('{"token": "test_token", "refresh_token": "test_refresh_token", "client_id": "test_client_id", "client_secret": "test_client_secret"}')
    with open(creds_path, 'w') as f:
        f.write('{"installed": {"client_id": "test"}}')
    
    with patch('google.oauth2.credentials.Credentials.from_authorized_user_file') as mock_creds:
        mock_creds.return_value.token = "test_token"
        mock_creds.return_value.valid = True
        uploader = GooglePhotoUploader(str(token_path), str(creds_path))
        return uploader

def test_google_photo_uploader_init(uploader):
    assert uploader.creds is not None
    assert uploader.creds.token == "test_token"

@patch('daily_bible_crawler.main.requests.post')
def test_upload_media(mock_post, uploader):
    mock_post.return_value.content = b"test_upload_token"
    mock_post.return_value.raise_for_status = Mock()
    
    with patch('builtins.open', mock_open(read_data=b'test_image_data')):
        token = uploader._upload_media("test.png")
    
    assert token == "test_upload_token"
    mock_post.assert_called_once()

@patch('daily_bible_crawler.main.build')
@patch('daily_bible_crawler.main.GooglePhotoUploader._upload_media')
def test_upload_image(mock_upload_media, mock_build, uploader):
    mock_upload_media.return_value = "test_upload_token"
    mock_service = Mock()
    mock_build.return_value = mock_service
    mock_service.mediaItems().batchCreate().execute.return_value = {"result": "success"}
    
    result = uploader.upload_image("test.png", "test description")
    
    assert result == {"result": "success"}
    mock_upload_media.assert_called_once_with("test.png")

@patch('daily_bible_crawler.main.sync_playwright')
def test_capture_bible_content(mock_playwright):
    # Mock Playwright objects
    mock_browser = Mock()
    mock_page = Mock()
    mock_element = Mock()
    
    # Setup mock chain
    mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page
    mock_page.locator.return_value = mock_element
    mock_element.screenshot = Mock()
    
    # Mock os.makedirs to prevent directory creation
    with patch('os.makedirs'):
        result = capture_bible_content()
    
    # Verify results
    assert len(result) == 2
    assert result[0][0] == "말씀"
    assert result[1][0] == "해설"
    
    # Verify method calls
    mock_page.goto.assert_called_once_with("https://sum.su.or.kr:8888/bible/today")
    mock_page.wait_for_load_state.assert_called_with("networkidle")
    mock_page.locator.assert_any_call("#font_uparea02")
    mock_page.locator.assert_any_call("#mainTitle_3")
    mock_page.locator.assert_any_call("#font_uparea03")
    assert mock_element.screenshot.call_count == 2 