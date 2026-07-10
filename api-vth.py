import websocket
import json
import requests

def recent_10(user_id, secret_key, asset_type):
    url = "https://api.escapemaster.net/escape_game/recent_10_issues?asset=BUILD"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        "Country-Code": "vn",
        "Origin": "https://xworld.info",
        "Referer": "https://xworld.info/",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "User-Id": "5817856",
        'User-Login': "login_v2",
        "User-Secret-Key": "c970554d46b8fed42c7c3431f7670e68d7f2b153a81b62b79ad162bdb9fbcc1f",
        "Xb-language": "vi-VN",
    }
    data = {
        "asset": asset_type
    }
    return requests.post(url, headers=headers, json=data).json()

def recent_100(user_id, secret_key, asset_type):
    url = "https://api.escapemaster.net/escape_game/recent_100_issues?asset=BUILD"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        "Country-Code": "vn",
        "Origin": "https://xworld.info",
        "Referer": "https://xworld.info/",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "User-Id": "5817856",
        'User-Login': "login_v2",
        "User-Secret-Key": "c970554d46b8fed42c7c3431f7670e68d7f2b153a81b62b79ad162bdb9fbcc1f",
        "Xb-language": "vi-VN",
    }
    data = {
        "asset": asset_type
    }
    return requests.post(url, headers=headers, json=data).json()

def enter_room(room_id, user_id, secret_key, asset_type):
    url = "https://api.escapemaster.net/escape_game/enter_room"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        "Content-Length": "52",
        "Content-Type": "application/json",
        "Origin": "https://escapemaster.net",
        "Referer": "https://escapemaster.net/",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "User-Id": "5817856",
        'User-Login': "login_v2",
        "User-Secret-Key": "c970554d46b8fed42c7c3431f7670e68d7f2b153a81b62b79ad162bdb9fbcc1f",
    }
    data = {
        "asset_type": "BUILD",
        "room_id": 1,
        "user_id": 5817856,
    }
    return requests.post(url, headers=headers, json=data).json()

def bet(room_id, user_id, secret_key, asset_type, bet_amount):
    url = "https://api.escapemaster.net/escape_game/bet"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        "Content-Length": "68",
        "Content-Type": "application/json",
        "Origin": "https://escapemaster.net",
        "Referer": "https://escapemaster.net/",
        "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?1",
        "Sec-Ch-Ua-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
        "User-Id": "5817856",
        'User-Login': "login_v2",
        "User-Secret-Key": "c970554d46b8fed42c7c3431f7670e68d7f2b153a81b62b79ad162bdb9fbcc1f",
    }
    data = {
        "asset_type": "BUILD",
        "bet_amount": 10,
        "room_id": 2,
        "user_id": 5817856,
    }
    return requests.post(url, headers=headers, json=data).json()
print(enter_room(0, 0, 0, 0))

def _open(ws):
    ws.send(json.dumps({
        "msg_type":"handle_enter_game",
        "asset_type":"BUILD",
        "user_id":5817856,
        "user_secret_key":"c970554d46b8fed42c7c3431f7670e68d7f2b153a81b62b79ad162bdb9fbcc1f",
    }))

def _message(ws, message):
    print(message)

ROOMS = [
    ("Nhà Kho", 1),
    ("Phòng họp", 2),
    ("Phòng giám đốc", 3),
    ("Phòng trò chuyện", 4),
    ("Phòng giám sát", 5),
    ("Văn phòng", 6),
    ("Phòng tài vụ", 7),
    ("Phòng nhân sự", 8),
]

HEADERS = [
    "Connection: Upgrade",
    "Pragma: no-cache",
    "Cache-Control: no-cache",
    "User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
    "Upgrade: websocket",
    "Origin: https://escapemaster.net",
    "Sec-WebSocket-Version: 13",
    "Accept-Encoding: gzip, deflate, br",
    "Accept-Language: vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
]

ws = websocket.WebSocketApp(
    "wss://api.escapemaster.net/escape_master/ws",
    header=HEADERS,
    on_open=_open,
    on_message=_message,
)

ws.run_forever()
