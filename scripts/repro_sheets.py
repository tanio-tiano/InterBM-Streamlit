import traceback

try:
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    from config import settings

    scopes = settings.SCOPES
    cred_file = settings.CRED_FILE
    url = settings.SHEET_URL

    print('Using cred file:', cred_file)
    print('Using sheet url:', url)

    creds = ServiceAccountCredentials.from_json_keyfile_name(cred_file, scopes)
    client = gspread.authorize(creds)
    ss = client.open_by_url(url)
    print('Opened spreadsheet:', ss.title)
    print('Worksheets:', [ws.title for ws in ss.worksheets()])
except Exception:
    traceback.print_exc()
