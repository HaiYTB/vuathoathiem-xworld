import os
import sys
import time
from pystyle import Colors, Colorate, Center, Col
import json
import logging
import requests
import websocket
from cloudscraper import create_scraper
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich import box
import urllib.parse
from fake_useragent import UserAgent


logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class Stats_Monitor:
    """
    Monitor Screen

    :param asset_type: Type of money
    :type asset_type: str
    """
    def __init__(self, asset_type):
        self.console = Console()
        self.data = None
        self.asset_type = asset_type.upper()
        self.room = None
        self.streak = 0
        self.max_streak = 0
        self.p_l = 0
        self.ROOMS = {
            1: "Nhà Kho",
            2: "Phòng họp",
            3: "Phòng giám đốc",
            4: "Phòng trò chuyện",
            5: "Phòng giám sát",
            6: "Văn phòng",
            7: "Phòng tài vụ",
            8: "Phòng nhân sự"
        }

    def tool_info(self, data):
        if not data:
            return Panel("Đang chờ dữ liệu...", title="Thông tin TOOL", style="blue")
        lines = []
        if self.room:
            lines.append(f"Phòng an toàn: {self.ROOMS.get(self.room, 0)}")
        lines.extend([
            f"Số {self.asset_type} đang có: {data['wallet']}",
            f"Chuỗi hiện tại: {self.streak}",
            f"Chuỗi cao nhất: {self.max_streak}",
            f"Số {self.asset_type} cược ban đầu: {data['first_bet_amount']}",
            f"Số {self.asset_type} cược hiện tại: {data['current_bet_amount']}",
            f"Hệ số: {data['multiplier']}",
            f"Lãi/lỗ: {self.p_l}",
        ])
        text = "\n".join(lines)
        return Panel(text, title="Thông tin TOOL", style="blue")

    def room_info(self):
        if not self.data:
            return Panel("Đang chờ dữ liệu...", title="Thông tin kì", style="blue")

        issue_id = self.data.get("issue_id", "N/A")
        if "State" in self.data:
            state = self.data.get("State", "N/A")
        else:
            state = self.data.get("state", "N/A")
        total_bet_amount = self.data.get("total_bet_amount", 0)
        user_cnt = self.data.get("user_cnt", 0)

        info = f"""
Kì hiện tại: {issue_id}
Kì tiếp theo: {int(issue_id) + 1}
Trạng thái: {state}
Tổng số tiền đã cược: {total_bet_amount} {self.asset_type}
Số người đã cược: {user_cnt}
"""

        return Panel(info, title="📊 Thông tin kì hiện tại", style="green")

    def countdown_info(self, countdown_data):
        if not countdown_data:
            return Panel("Đang chờ countdown...", title="⏰ Countdown", style="yellow")

        issue_id = countdown_data.get("issue_id", "N/A")
        countdown = countdown_data.get("count_down", 0)
        style = "red" if countdown <= 10 else "yellow"

        countdown_text = f"""
Kì hiện tại: {issue_id}
Sát thủ đến sau: {countdown}s
"""

        return Panel(countdown_text, title="⏰ Countdown", style=style)

    def result_info(self, result_data):
        if not result_data:
            return Panel("Đang chờ kết quả...", title="🎯 Kết quả", style="blue")

        issue_id = result_data.get("issue_id", "N/A")
        killed_room_id = result_data["killed_room"]
        killed_room = self.ROOMS.get(killed_room_id, "N/A")
        total_award = result_data.get("total_award_amount", 0)
        total_bet = result_data.get("total_bet_amount", 0)

        if "award_amount" in result_data:
            bet_amount = result_data["bet_amount"]
            award_amount = result_data["award_amount"]
            room_bet = result_data["room_id"]
            if killed_room_id != room_bet:
                self.p_l += (award_amount - bet_amount)
                self.streak += 1
                if self.streak > self.max_streak:
                    self.max_streak = self.streak
            else:
                logging.info(
                    f"""
Phòng bạn chọn: {self.ROOMS.get(room_bet, "N/A")}
Phòng bị giết: {killed_room}
Lãi/lỗ trước đó: {self.p_l}
Lãi/lỗ hiện tại: {self.p_l - bet_amount}
Chuỗi trước đó: {self.streak}
Chuỗi hiện tại: 0"""
                )
                self.p_l -= bet_amount
                self.streak = 0
            text = f"""
Kì hiện tại: {issue_id}
Phòng bạn chọn: {self.ROOMS.get(room_bet, "N/A")}
Phòng bị giết: {killed_room}
Tổng số {self.asset_type} nhận được: {total_award}
Tổng số {self.asset_type} của phòng bị giết: {total_bet}
Số {self.asset_type} đã cược: {bet_amount}
Số {self.asset_type} nhận được: {award_amount}
"""
        else:
            text = f"""
Kì hiện tại: {issue_id}
Phòng bị giết: {killed_room}
Tổng số {self.asset_type} nhận được: {total_award}
Tổng số {self.asset_type} của phòng bị giết: {total_bet}
"""

        return Panel(text, title="🎯 Kết quả", style="red")

    def result_panel(self, result_data):
        if not result_data:
            table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("Thông báo", style="cyan", width=50)
            table.add_row("Đang chờ dữ liệu từ websocket...")
            return table

        table = Table(
            title=f"KẾT QUẢ TỪNG PHÒNG",
            show_header=True,
            header_style="bold yellow",
            box=box.DOUBLE_EDGE,
            title_style="bold green"
        )

        rooms = sorted(result_data["rooms"], key=lambda x: x["room_id"])
        table.add_column("Phòng", style="cyan", width=18)
        table.add_column("Tổng cược", style="cyan", width=10)
        table.add_column("Số người", justify="center", width=8)
        table.add_column("Trạng thái", justify="center", width=12)

        killed_room_id = result_data["killed_room"]

        for room in rooms:
            status = "❌ Bị giết" if killed_room_id == room["room_id"] else "✅ Sống"
            table.add_row(
                self.ROOMS.get(int(room["room_id"]), "N/A"),
                str(room["total_bet_amount"]),
                str(room["user_cnt"]),
                status
            )

        return table

    def stats(self):
        if not self.data:
            table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("Thông báo", style="cyan", width=50)
            table.add_row("Đang chờ dữ liệu từ websocket...")
            return table

        table = Table(
            title=f"🎮 VUA THOÁT HIỂM - BY HAITOOL - {self.asset_type}",
            show_header=True,
            header_style="bold yellow",
            box=box.DOUBLE_EDGE,
            title_style="bold green"
        )

        table.add_column("Phòng", style="cyan", width=18)
        table.add_column("Số người", justify="center", width=10)
        table.add_column("Tổng cược", justify="center", width=13)
        table.add_column("Thời gian cược cuối", justify="center", width=17)

        if "room_stat" in self.data:
            rooms = sorted(self.data["room_stat"], key=lambda x: x["room_id"])
        else:
            rooms = sorted(self.data["rooms"], key=lambda x: x["room_id"])
        for room in rooms:
            room_name = self.ROOMS.get(room.get("room_id", 0), "N/A")
            total_bet_amount = room.get("total_bet_amount", 0)
            user_cnt = room.get("user_cnt", 0)
            ts = room.get("last_bet_time", 0)
            if isinstance(ts, (int, float)) and ts > 0:
                last_bet_time = time.strftime("%H:%M:%S", time.localtime(ts))
            else:
                last_bet_time = time.strftime("%H:%M:%S", time.localtime())

            table.add_row(
                room_name,
                str(user_cnt),
                str(total_bet_amount),
                str(last_bet_time)
            )

        return table

    def update(self, data):
        self.data = data

    def display(self, countdown_data=None, result_data=None, tool_data=None):
        os.system("cls" if os.name == "nt" else "clear")
        banner = (
            " ___  ___  ________  ___  _________  ________  ________  ___          \n"
            "|\\  \\|\\  \\|\\   __  \\|\\  \\|\\___   ___\\\\   __  \\|\\   __  \\|\\  \\         \n"
            "\\ \\  \\\\\\  \\ \\  \\|\\  \\ \\  \\|___ \\  \\_\\ \\  \\|\\  \\ \\  \\|\\  \\ \\  \\        \n"
            " \\ \\   __  \\ \\   __  \\ \\  \\   \\ \\  \\ \\ \\  \\\\\\  \\ \\  \\\\\\  \\ \\  \\       \n"
            "  \\ \\  \\ \\  \\ \\  \\ \\  \\ \\  \\   \\ \\  \\ \\ \\  \\\\\\  \\ \\  \\\\\\  \\ \\  \\____  \n"
            "   \\ \\__\\ \\__\\ \\__\\ \\__\\ \\__\\   \\ \\__\\ \\ \\_______\\ \\_______\\ \\_______\\\n"
            "    \\|__|\\|__|\\|__|\\|__|\\|__|    \\|__|  \\|_______|\\|_______|\\|_______|\n"
        ).rstrip("\n")

        self.console.print(Panel(Align.center(banner), style="bold cyan"))
        self.console.print(self.room_info())
        self.console.print(self.tool_info(tool_data))

        if countdown_data:
            self.console.print(self.countdown_info(countdown_data))

        if result_data:
            self.console.print(self.result_info(result_data))
            self.console.print(self.result_panel(result_data))
            result_data = None

        self.console.print(self.stats())

        help_text = "Nhấn Ctrl+C để dừng!"
        self.console.print(f"\n{help_text:^80}", style="dim")

class VuaThoatHiem:
    """
    Main class for interacting with the X World & Escape Room API.

    :param user_id: User ID
    :type user_id: str
    :param user_secret_key: User Secret Key
    :type user_secret_key: str
    :param asset_type: Type of money
    :type asset_type: str
    :param bet_amount: Bet Amount
    :type bet_amount: int/float
    :param multiplier: Bet multiplier after loss
    :type multiplier: float
    """
    def __init__(self, user_id, user_secret_key, asset_type, bet_amount, multiplier):
        self.user_id = user_id
        self.user_secret_key = user_secret_key
        self.asset_type = asset_type.upper()
        self.first_bet_amount = bet_amount
        self.current_bet_amount = bet_amount
        self.multiplier = multiplier
        self.user_agent = str(UserAgent().random)
        self.session = create_scraper(sess=requests.Session())
        self.monitor = Stats_Monitor(self.asset_type)
        self.monitor.first_wallet = float(self.wallet())
        self.wallet_amount = float(self.wallet())
        self.current_room = 0
        self.auto_play = False
        self.countdown = None
        self.result = None

    def _open(self, ws):
        ws.send(json.dumps({
            "msg_type": "handle_enter_game",
            "asset_type": self.asset_type,
            "user_id": int(self.user_id),
            "user_secret_key": self.user_secret_key,
        }))

    def _message(self, ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("msg_type")

            if msg_type == "notify_enter_game":
                self.monitor.update(data)
                self.result = None
            elif msg_type == "notify_count_down":
                self.countdown = data
            elif msg_type == "notify_issue_stat":
                self.monitor.data = data
                if self.auto_play:
                    safe_room = int(self.analysis(data["rooms"]))
                    if safe_room:
                        self.monitor.room = safe_room
                        if self.current_room == 0:
                            self.bet(safe_room, self.current_bet_amount)
                            self.current_bet_amount = self.first_bet_amount
                        elif self.current_room != safe_room:
                            self.enter_room(safe_room)
                        self.current_room = safe_room
            elif msg_type == "notify_result":
                self.result = data
                room_bet = data.get("room_id")
                killed = data.get("killed_room")
                if room_bet and killed:
                    if room_bet == killed:
                        self.current_bet_amount *= self.multiplier
                    else:
                        self.current_bet_amount = self.first_bet_amount

            tool_data = {
                "wallet": self.wallet_amount,
                "first_bet_amount": self.first_bet_amount,
                "current_bet_amount": self.current_bet_amount,
                "multiplier": self.multiplier
            }
            self.monitor.display(self.countdown, self.result, tool_data)

            if "killed_room" in json.loads(message):
                time.sleep(5)
                ws.send(json.dumps({
                    "msg_type": "handle_enter_game",
                    "asset_type": self.asset_type,
                    "user_id": int(self.user_id),
                    "user_secret_key": self.user_secret_key,
                }))
                self.current_room = 0
                self.wallet_amount = float(self.wallet())
        except Exception as e:
            print(f"{Colors.red}Lỗi xử lí message: {e}{Colors.reset}")
            time.sleep(2)

    def _close(self, ws, status, msg):
        print(f"{Colors.green}>>> WS CLOSED: {status} - {msg}{Colors.reset}")

    def _error(self, ws, error):
        print(f"{Colors.red}!!! ERROR: {error} - {ws}{Colors.reset}")

    def stats(self):
        """
        {"asset_type":"BUILD","count_down":1,"issue_id":829344,"msg_type":"notify_count_down"}

        {"asset_type":"BUILD","issue_id":829344,"msg_type":"notify_issue_stat","rooms":[{"room_id":8,"total_bet_amount":190962.4,"user_cnt":25},{"room_id":1,"total_bet_amount":106840,"user_cnt":11},{"room_id":5,"total_bet_amount":70703,"user_cnt":15},{"room_id":7,"total_bet_amount":70410,"user_cnt":29},{"room_id":3,"total_bet_amount":64520.7,"user_cnt":19},{"room_id":2,"total_bet_amount":50525,"user_cnt":25},{"room_id":6,"total_bet_amount":62910,"user_cnt":13},{"room_id":4,"total_bet_amount":51109.299999999996,"user_cnt":32}],"state":"countdown","total_bet_amount":667980.3999999999,"user_cnt":169,"user_cnt_countdown":20}

        {"asset_type":"BUILD","issue_id":829344,"killed_room":4,"msg_type":"notify_result","next_issue_id":829345,"rooms":[{"room_id":8,"total_bet_amount":190962.4,"user_cnt":25},{"room_id":1,"total_bet_amount":106840,"user_cnt":11},{"room_id":5,"total_bet_amount":70703,"user_cnt":15},{"room_id":7,"total_bet_amount":70410,"user_cnt":29},{"room_id":3,"total_bet_amount":64520.7,"user_cnt":19},{"room_id":2,"total_bet_amount":50525,"user_cnt":25},{"room_id":6,"total_bet_amount":62910,"user_cnt":13},{"room_id":4,"total_bet_amount":51109.299999999996,"user_cnt":32}],"total_award_amount":45993.869999999995,"total_bet_amount":667980.3999999999}

        {"asset_type":"BUILD","award_amount":11.732201558580638,"bet_amount":10,"is_killed":false,"issue_id":835086,"killed_room":7,"msg_type":"notify_result","next_issue_id":835087,"room_id":1,"rooms":[{"room_id":7,"total_bet_amount":96248,"user_cnt":23},{"room_id":4,"total_bet_amount":50820,"user_cnt":11},{"room_id":2,"total_bet_amount":41200,"user_cnt":21},{"room_id":8,"total_bet_amount":99632.2,"user_cnt":18},{"room_id":5,"total_bet_amount":55721,"user_cnt":22},{"room_id":6,"total_bet_amount":56900.2,"user_cnt":14},{"room_id":3,"total_bet_amount":87800,"user_cnt":16},{"room_id":1,"total_bet_amount":108002.3537187466,"user_cnt":51}],"total_award_amount":86623.2,"total_bet_amount":596323.7537187466,"user_id":2258926}

        {"asset_type":"BUILD","info":{"asset_type":"BUILD","issue_id":829345,"start_time":1763288501,"end_time":1763374901,"State":"pending","join_user_cnt":0},"issue_id":829345,"last_killed_room_id":4,"msg_type":"notify_enter_game","room_stat":[{"room_id":8,"user_cnt":1,"total_bet_amount":0,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288501.286966},{"room_id":5,"user_cnt":1,"total_bet_amount":100,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288501.524538},{"room_id":4,"user_cnt":1,"total_bet_amount":0,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288501.551864},{"room_id":7,"user_cnt":1,"total_bet_amount":43600,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288502.058792},{"room_id":1,"user_cnt":2,"total_bet_amount":47200,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288503.509468},{"room_id":6,"user_cnt":2,"total_bet_amount":52900,"total_award_amount":0,"is_killed":0,"last_bet_time":1763288504.699557}],"user_id":2258926,"user_info":{"user_id":0,"asset_type":"","issue_id":0,"room_id":0,"bet_amount":0,"is_killed":0,"award_amount":0},"vip_skin_type":""}

        {"asset_type":"BUILD","issue_id":829345,"msg_type":"notify_issue_stat","rooms":[{"room_id":8,"total_bet_amount":0,"user_cnt":1},{"room_id":5,"total_bet_amount":100,"user_cnt":1},{"room_id":4,"total_bet_amount":0,"user_cnt":1},{"room_id":7,"total_bet_amount":43600,"user_cnt":1},{"room_id":1,"total_bet_amount":47200,"user_cnt":2},{"room_id":6,"total_bet_amount":52900,"user_cnt":2},{"room_id":2,"total_bet_amount":29900,"user_cnt":1}],"state":"pending","total_bet_amount":173700,"user_cnt":9,"user_cnt_countdown":20}
        """
        HEADERS = [
            "Connection: Upgrade",
            "Pragma: no-cache",
            "Cache-Control: no-cache",
            f"User-Agent: {self.user_agent}",
            "Upgrade: websocket",
            "Origin: https://escapemaster.net",
            "Sec-WebSocket-Version: 13",
            "Accept-Encoding: gzip, deflate, br",
            "Accept-Language: vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
        ]
        self.ws = websocket.WebSocketApp(
            "wss://api.escapemaster.net/escape_master/ws",
            header=HEADERS,
            on_open=lambda ws: self._open(ws),
            on_message=lambda ws, msg: self._message(ws, msg),
            on_close=lambda ws, status, msg: self._close(ws, status, msg),
            on_error=lambda ws, err: self._error(ws, err),
        )
        self.ws.run_forever()

    def wallet(self):
        url = "https://wallet.3games.io/api/wallet/user_asset"
        headers = {  
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "Content-Type": "application/json",
            "Country-Code": "vn",
            "Origin": "https://xworld.info",
            "Referer": "https://xworld.info/",
            "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": self.user_agent,
            "User-Id": self.user_id,
            "User-Secret-Key": self.user_secret_key,
            "Xb-Language": "vi-VN",
        }
        data = {
            "source": "home",
            "user_id": self.user_id
        }
        response = requests.post(url, headers=headers, json=data).json()
        return response["data"]["user_asset"][self.asset_type]

    def analysis(self, rooms):
        try:
            base_url = "http://160.25.233.225:61324/predict"
            params = {}

            for r in rooms:
                rid = r["room_id"]
                params[f"r{rid}u"] = r["user_cnt"]
                params[f"r{rid}b"] = r["total_bet_amount"]

            h10_raw = self.recent_10()
            if h10_raw and h10_raw.get("code") == 0:
                h10 = [d["killed_room_id"] for d in h10_raw["data"]]
            else:
                h10 = []

            h100_raw = self.recent_100()
            if h100_raw and h100_raw.get("code") == 0:
                killed_map = h100_raw["data"]["room_id_2_killed_times"]
                h100 = []
                for room_id, cnt in killed_map.items():
                    h100.extend([int(room_id)] * int(cnt))
            else:
                h100 = []

            if not h10 and h100:
                h10 = h100[-10:]
            if not h10:
                h10 = [5,2,4,1,4,8,2,4,8,1]
            if not h100:
                h100 = h10[:]

            params["history10"] = ",".join(str(x) for x in h10)
            params["history100"] = ",".join(str(x) for x in h100)

            res = requests.get(base_url, params=params, timeout=5).json()
            safe_room = res.get("safest_room", {}).get("room_id", 0)

            return safe_room if safe_room > 0 else None
    
        except Exception as e:
            print(f"{Colors.red}API ERROR: {e}{Colors.reset}")
            return None

    def recent_10(self):
        """
        Information of the last 10 matches
        """
        # {'code': 0, 'data': [{'issue_id': 827287, 'killed_room_id': 5}, {'issue_id': 827286, 'killed_room_id': 2}, {'issue_id': 827285, 'killed_room_id': 4}, {'issue_id': 827284, 'killed_room_id': 1}, {'issue_id': 827283, 'killed_room_id': 4}, {'issue_id': 827282, 'killed_room_id': 8}, {'issue_id': 827281, 'killed_room_id': 2}, {'issue_id': 827280, 'killed_room_id': 4}, {'issue_id': 827279, 'killed_room_id': 8}, {'issue_id': 827278, 'killed_room_id': 1}], 'msg': 'ok'}
        url = f"https://api.escapemaster.net/escape_game/recent_10_issues?asset={self.asset_type}"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.user_agent,
            "User-Id": self.user_id,
            "User-Login": "login_v2",
            "User-Secret-Key": self.user_secret_key,
            "Country-Code": "vn",
            "Origin": "https://xworld.info",
            "Referer": "https://xworld.info/",
            "Xb-language": "vi-VN",
        }
        data = {
            "asset": self.asset_type
        }
        return self.session.get(url, headers=headers, json=data).json()

    def recent_100(self):
        """
        Information of the last 100 matches
        """
        # {'code': 0, 'data': {'room_id_2_killed_times': {'2': 12, '4': 18, '1': 18, '8': 10, '5': 15, '6': 9, '7': 12, '3': 6}}, 'msg': 'ok'}
        url = f"https://api.escapemaster.net/escape_game/recent_100_issues?asset={self.asset_type}"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.user_agent,
            "User-Id": self.user_id,
            "User-Login": "login_v2",
            "User-Secret-Key": self.user_secret_key,
            "Country-Code": "vn",
            "Origin": "https://xworld.info",
            "Referer": "https://xworld.info/",
            "Xb-language": "vi-VN",
        }
        data = {
            "asset": self.asset_type
        }
        return self.session.get(url, headers=headers, json=data).json()

    def enter_room(self, room_id):
        """
        Choose an escape room

        :param room_id: Room ID
        :type room_id: int
        """
        url = "https://api.escapemaster.net/escape_game/enter_room"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.user_agent,
            "User-Id": self.user_id,
            "User-Login": "login_v2",
            "User-Secret-Key": self.user_secret_key,
            "Content-Length": "52",
            "Content-Type": "application/json",
            "Origin": "https://escapemaster.net",
            "Referer": "https://escapemaster.net/",
        }
        data = {
            "asset_type": self.asset_type,
            "room_id": int(room_id),
            "user_id": int(self.user_id),
        }
        return self.session.post(url, headers=headers, json=data).json()

    def bet(self, room_id, bet_amount):
        """
        Bet money on escape room

        :param room_id: Room ID
        :type room_id: int
        :param bet_amount: Bet Amount
        :type bet_amount: int/float
        """
        # {'code': 0, 'data': None, 'msg': 'ok'}
        url = "https://api.escapemaster.net/escape_game/bet"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,en-VN;q=0.8,en;q=0.7,fr-FR;q=0.6,fr;q=0.5,en-US;q=0.4",
            "Sec-Ch-Ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?1",
            "Sec-Ch-Ua-Platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": self.user_agent,
            "User-Id": self.user_id,
            "User-Login": "login_v2",
            "User-Secret-Key": self.user_secret_key,
            "Content-Length": "68",
            "Content-Type": "application/json",
            "Origin": "https://escapemaster.net",
            "Referer": "https://escapemaster.net/",
        }
        data = {
            "asset_type": self.asset_type,
            "bet_amount": bet_amount,
            "room_id": int(room_id),
            "user_id": int(self.user_id),
        }
        return self.session.post(url, headers=headers, json=data).json()


def banner(speed_char=0.0000001, speed_line=0.0001):
    text = r"""
 ___  ___  ________  ___  _________  ________  ________  ___          
|\  \|\  \|\   __  \|\  \|\___   ___\\   __  \ \|\   __  \|\  \         
\ \  \\\  \ \  \|\  \ \  \|___ \  \_\ \  \|\  \ \  \|\  \ \  \        
 \ \   __  \ \   __  \ \  \   \ \  \ \ \  \\\  \ \  \\\  \ \  \       
  \ \  \ \  \ \  \ \  \ \  \   \ \  \ \ \  \\\  \ \  \\\  \ \  \____  
   \ \__\ \__\ \__\ \__\ \__\   \ \__\ \ \_______\ \_______\ \_______\
    \|__|\|__|\|__|\|__|\|__|    \|__|  \|_______|\|_______|\|_______|
"""

    os.system("cls" if os.name == "nt" else "clear")
    lines = text.splitlines()
    for line in lines:
        for i in range(len(line) + 1):
            sys.stdout.write(
                "\r" + Colors.reset + Colorate.Horizontal(
                    Colors.rainbow,
                    Center.XCenter(line[:i])
                )
            )
            sys.stdout.flush()
            time.sleep(speed_char)
        print()
        # time.sleep(speed_line)
    print("\n")

def options():
    text = """
1. Tự động chơi với thuật toán của tool
2. Theo dõi câc kì
3. Thống kê 10 ván gần đây
4. Thống kê 100 ván gần đây
===================================
0. Thoát tool
"""
    lines = text.splitlines()

    for line in lines:
        for i in range(len(line) + 1):
            sys.stdout.write(
                "\r" + Colors.reset + Colorate.Horizontal(
                    Colors.yellow_to_green,
                    line[:i]
                )
            )
            sys.stdout.flush()
            time.sleep(0.009)
        print()
        time.sleep(0.02)
    option = input(f"{Colors.white}Chọn lựa chọn(Nhập số): {Colors.reset}").strip()
    return option

def check_config(file_name="config_vth.json"):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "xworld" not in data or "vth" not in data or "key" not in data:
                return False
            else:
                if ("user_id" not in data["xworld"] or 
                    "user_secret_key" not in data["xworld"] or 
                    "bet_amount" not in data["vth"] or 
                    "multiplier" not in data["vth"]):
                    return False
            return True
    except json.JSONDecodeError as e:
        return False
    except FileNotFoundError:
        return False


def edit_config(data, file_name="config_vth.json"):
    def force_input(label, cast_type=str):
        while True:
            v = input(f"{Colors.cyan}{label}: {Colors.reset}").strip()
            if v == "":
                print(f"{Colors.red}Giá trị không được rỗng!{Colors.reset}")
                continue
            try:
                return cast_type(v)
            except:
                print(f"{Colors.red}Sai định dạng!{Colors.reset}")

    def parse_from_link():
        url = input(f"{Colors.cyan}Nhập link chứa userId & secretKey: {Colors.reset}").strip()
        try:
            query = urllib.parse.urlparse(url).query
            params = urllib.parse.parse_qs(query)
            uid = params.get("userId", [None])[0]
            sk = params.get("secretKey", [None])[0]
            if not uid:
                print(f"{Colors.red}Không tìm thấy userId trong link, yêu cầu nhập thủ công{Colors.reset}")
                uid = force_input("Nhập User ID")
            if not sk:
                print(f"{Colors.red}Không tìm thấy secretKey trong link, yêu cầu nhập thủ công{Colors.reset}")
                sk = force_input("Nhập User Secret Key")
            return uid, sk
        except Exception:
            print(f"{Colors.red}Link không hợp lệ. Nhập thủ công!{Colors.reset}")
            return force_input("Nhập User ID"), force_input("Nhập User Secret Key")

    xworld = data.get("xworld", {"user_id": "", "user_secret_key": ""})
    current_id = xworld.get("user_id", "")
    current_sk = xworld.get("user_secret_key", "")
    if current_id and current_sk:
        change = input(f"{Colors.cyan}Đã có User ID & Secret Key. Muốn thay đổi? (Ghi 'n' để giữ nguyên): {Colors.reset}").strip()
        if change.lower() == "n":
            print(f"{Colors.green}Giữ nguyên thông tin cũ{Colors.reset}")
        else:
            print(f"{Colors.cyan}Chọn phương thức nhập:{Colors.reset}")
            print("1. Tự động qua link")
            print("2. Nhập thủ công")
            while True:
                method = input("Chọn 1 hoặc 2: ").strip()
                if method in ["1", "2"]:
                    break
                print(f"{Colors.red}Lựa chọn không hợp lệ!{Colors.reset}")
            if method == "1":
                user_id, user_secret_key = parse_from_link()
            else:
                user_id = force_input("Nhập User ID")
                user_secret_key = force_input("Nhập User Secret Key")
            data["xworld"]["user_id"] = user_id
            data["xworld"]["user_secret_key"] = user_secret_key
    else:
        print(f"{Colors.cyan}Chọn phương thức nhập:{Colors.reset}")
        print("1. Tự động qua link")
        print("2. Nhập thủ công")
        while True:
            method = input("Chọn 1 hoặc 2: ").strip()
            if method in ["1", "2"]:
                break
            print(f"{Colors.red}Lựa chọn không hợp lệ!{Colors.reset}")
        if method == "1":
            user_id, user_secret_key = parse_from_link()
        else:
            user_id = force_input("Nhập User ID")
            user_secret_key = force_input("Nhập User Secret Key")
        data["xworld"]["user_id"] = user_id
        data["xworld"]["user_secret_key"] = user_secret_key

    vth = data.get("vth", {})
    old_bet = vth.get("bet_amount")
    old_multi = vth.get("multiplier")
    print(f"{Colors.cyan}Cấu hình tiền cược{Colors.reset}")
    if old_bet is not None:
        print(f"Số tiền cược hiện tại: {old_bet}")
    data["vth"]["bet_amount"] = force_input("Nhập số tiền cược", float)
    if old_multi is not None:
        print(f"Hệ số thua hiện tại: {old_multi}")
    data["vth"]["multiplier"] = force_input("Nhập hệ số nhân khi thua", float)

    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return data


def main():
    file_name = "config_vth.json"

    # Config
    if not check_config():
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump({
                "xworld": {
                    "user_id": "",
                    "user_secret_key": ""
                },
                "vth": {
                    "bet_amount": None,
                    "multiplier": None
                },
                "key": None
            }, f, indent=4, ensure_ascii=False)

    with open(file_name, "r") as f:
        data_config = edit_config(json.load(f))
    xworld = data_config["xworld"]
    tool = data_config["vth"]

    print("\n")
    asset_type = input(f"""{Colors.reset}Loại tiền tệ
{Colors.cyan}1. BUILD
{Colors.white}2. WORLD
{Colors.green}3. USDT
{Colors.reset}Chọn số: """)
    if asset_type == "1":
        asset_type = "BUILD"
    elif asset_type == "2":
        asset_type = "WORLD"
    elif asset_type == "3":
        asset_type = "USDT"
    else:
        asset_type = "BUILD"

    while True:
        # MENU
        banner()
        choice = options()
        print("\n")

        vth = VuaThoatHiem(xworld["user_id"], xworld["user_secret_key"], asset_type, tool["bet_amount"], tool["multiplier"])

        if choice == "0":
            break
        elif choice == "1":
            vth.auto_play = True
            vth.stats()
        elif choice == "2":
            vth.stats()
        elif choice == "3":
            print(vth.recent_10())
        elif choice == "4":
            print(vth.recent_100())
        else:
            print(f"{Colors.red}Nhập sai lựa chọn!{Colors.reset}")
        input(f"{Colors.red}Enter để tiếp tục tool! {Colors.reset}")

if __name__ == "__main__":
    main()
