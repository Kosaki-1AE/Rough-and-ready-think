"""Read the authenticated user's playlists using the official YouTube Data API."""
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

def youtube_client(credentials_file='client_secret.json', token_file='.youtube_oauth_token.json'):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError('Install OAuth dependencies: python -m pip install -r requirements.txt') from exc
    credentials = None
    token = Path(token_file)
    if token.exists():
        credentials = Credentials.from_authorized_user_file(str(token), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        secret = Path(credentials_file)
        if not secret.exists():
            raise FileNotFoundError('Missing OAuth client JSON: '+str(secret))
        flow = InstalledAppFlow.from_client_secrets_file(str(secret), SCOPES)
        credentials = flow.run_local_server(port=0, open_browser=True)
    token.write_text(credentials.to_json(), encoding='utf-8')
    try:
        token.chmod(0o600)
    except OSError:
        pass
    return build('youtube', 'v3', credentials=credentials, cache_discovery=False)

def pages(request_builder, **kwargs):
    page_token = None
    while True:
        response = request_builder(**kwargs, pageToken=page_token).execute()
        for item in response.get('items', []):
            yield item
        page_token = response.get('nextPageToken')
        if not page_token:
            break

def collect_my_playlists(add, rows, credentials_file, token_file, playlist_limit=0):
    client = youtube_client(credentials_file, token_file)
    playlists = list(pages(client.playlists().list, part='snippet,status', mine=True, maxResults=50))
    print('OAuth: found', len(playlists), 'playlists')
    for playlist in playlists:
        privacy = playlist.get('status', {}).get('privacyStatus', 'unknown')
        if privacy != 'unlisted':
            print('Skipped playlist (privacy=%s): %s' % (privacy, playlist.get('snippet', {}).get('title', playlist['id'])))
            continue
        playlist_id = playlist['id']
        title = playlist.get('snippet', {}).get('title', playlist_id)
        count = 0
        for item in pages(client.playlistItems().list, part='snippet,contentDetails', playlistId=playlist_id, maxResults=50):
            snippet = item.get('snippet', {})
            vid = item.get('contentDetails', {}).get('videoId') or snippet.get('resourceId', {}).get('videoId')
            if not vid:
                continue
            entry = {'id':vid, 'title':snippet.get('title', ''), 'channel':snippet.get('videoOwnerChannelTitle', '')}
            add(rows, entry, 'oauth_my_playlist', title)
            count += 1
            if playlist_limit and count >= playlist_limit:
                break
        print('OAuth playlist:',title, count)
    return len(playlists)
