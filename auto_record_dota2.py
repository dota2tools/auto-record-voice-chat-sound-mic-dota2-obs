from http.server import BaseHTTPRequestHandler, HTTPServer
from json import loads as json_loads
from pathlib import Path
from types import SimpleNamespace as _G
from ctypes import *
from ctypes.util import find_library
import obspython as S
import threading
import time

G = _G()
G.__version__ = "0.1.0"
G.obsffi = CDLL(find_library("obs"))  # there an is error if running in admin on win
# see also https://github.com/python/cpython/issues/83424  only on 3.8+
G.obsffi_front = CDLL(find_library("obs-frontend-api"))


def wrap(funcname, restype, argtypes=None, use_lib=None):
    """Simplify wrapping ctypes functions"""
    if use_lib is not None:
        func = getattr(use_lib, funcname)
    else:
        func = getattr(G.obsffi, funcname)
    func.restype = restype
    if argtypes is not None:
        func.argtypes = argtypes
    G.__dict__[funcname] = func


class Config(Structure):
    pass


wrap("obs_frontend_get_profile_config", POINTER(Config), use_lib=G.obsffi_front)
wrap(
    "config_set_string", None, argtypes=[POINTER(Config), c_char_p, c_char_p, c_char_p]
)
wrap("config_save", c_int, argtypes=[POINTER(Config)])


# ********************************************************************************
""" dota2gsi.py MIT by https://pypi.org/project/dota2gsi avalonlee@gmail.com (2019)
Modified by upgradeQ (2022) project url:
https://github.com/dota2tools/auto-record-voice-chat-sound-mic-dota2-obs
"""


class MyServer(HTTPServer):
    def init_state(self):
        self.last_state = None
        self.handlers = []

    def handle_state(self, state):
        for handler in self.handlers:
            handler(self.last_state, state)


class MyRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Receive state from GSI"""
        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length).decode("utf-8")
        state = json_loads(body)
        self.send_header("Content-type", "text/html")
        self.send_response(200)
        self.end_headers()
        self.server.handle_state(state)
        self.server.last_state = state

    def log_message(self, format, *args):
        """Don't print status messages"""
        return


class Server:
    def __init__(self, ip="127.0.0.1", port=3322):
        self.ip = ip
        self.port = port
        self.server = MyServer((ip, port), MyRequestHandler)
        self.server.init_state()

    def start(self):
        print(f"DotA 2 GSI server listening on {self.ip}:{self.port}")
        if len(self.server.handlers) == 0:
            print("Warning: no handlers were added, nothing will happen")
        try:
            self.server.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            pass
        self.server.server_close()
        print("DotA 2 GSI Server stopped.")

    def on_update(self, func):
        """Sets the function to be called when a new state is available.

        The function must accept two arguments:
            last_state - the previous state
            state - the new state
        """
        self.server.handlers.append(func)


# ********************************************************************************

G.counter = 0
G.shutdown = False
G.running = False
G._matches = "."  # folder where to automatically record
G.in_progress = False


def game_state(last_state, state):
    dota_data = {"status": 1}

    try:
        # https://moddota.com/api/#!/vscripts/DOTA_GameState

        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_WAIT_FOR_PLAYERS_TO_LOAD', 'matchid': '6786786780', 'game_time': 10}
        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_HERO_SELECTION', 'matchid': '6786786780', 'game_time': 16}
        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_STRATEGY_TIME', 'matchid': '6786786780', 'game_time': 106}
        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_TEAM_SHOWCASE', 'matchid': '6786786780', 'game_time': 136}
        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_WAIT_FOR_MAP_TO_LOAD', 'matchid': '6786786780', 'game_time': 136}
        # {'status': 1, 'game_state': 'DOTA_GAMERULES_STATE_PRE_GAME', 'matchid': '6786786780', 'game_time': 136}
        # {'name': 'start', 'game_state': 'DOTA_GAMERULES_STATE_GAME_IN_PROGRESS', 'matchid': '6786786780', 'clock_time': 2125, 'game_time': 2398}
        # {'name': 'start', 'game_state': 'DOTA_GAMERULES_STATE_POST_GAME', 'matchid': '6786786780', 'clock_time': 2254, 'game_time': 2526}

        dota_data["game_state"] = state["map"]["game_state"]
        dota_data["matchid"] = state["map"]["matchid"]
        # dota_data["clock_time"] = state["map"]["clock_time"]
        dota_data["game_time"] = state["map"]["game_time"]

    except Exception as e:
        # print('[exception happened]',e)
        dota_data["status"] = 0
    # {'map': {'name': 'start', 'matchid': '6801858263', 'game_time': 16, 'clock_time': 16, 'daytime': False, 'nightstalker_night': False, 'radiant_score': 0, 'dire_score': 0, 'game_state': 'DOTA_GAMERULES_STATE_HERO_SELECTION', 'paused': False, 'win_team': 'none', 'customgamename': '', 'radiant_ward_purchase_cooldown': 0, 'dire_ward_purchase_cooldown': 0, 'roshan_state': 'alive', 'roshan_state_end_seconds': 0}}

    do_recording(dota_data)
    if G.shutdown:
        raise KeyboardInterrupt


def main():
    try:
        server = Server()
        server.on_update(game_state)
        server.start()
    except KeyboardInterrupt:
        pass


def set_path(path):
    "sets recording paths"
    if not S.obs_frontend_recording_active():
        cfg = G.obs_frontend_get_profile_config()
        e = lambda x: x.encode("utf-8")
        G.config_set_string(cfg, e("AdvOut"), e("RecFilePath"), e(path))
        G.config_set_string(cfg, e("SimpleOutput"), e("FilePath"), e(path))
        # replay buffer ?? ffmpeg output ???
        flags = {
            "0": "CONFIG_SUCCESS",
            "-1": "CONFIG_FILENOTFOUND",
            "-2": "CONFIG_ERROR",
        }
        res_flag = G.config_save(cfg)
        print(path, flags[str(res_flag)])


def start():
    S.obs_frontend_recording_start()
    G.in_progress = True


def stop():
    S.obs_frontend_recording_stop()
    G.in_progress = False


def start_btn(*_):
    G.running = True
    print(G._matches)


def stop_btn(*_):
    G.running = False


def do_recording(dota_data):
    if not G.running:
        return
    if not dota_data:
        return
    if dota_data["status"] == 0:
        stop()
        return
    if len(dota_data) < 3:
        return
    if G.in_progress:
        return
    state = dota_data["game_state"]
    if any(
        [
            state == "DOTA_GAMERULES_STATE_INIT",
            state == "DOTA_GAMERULES_STATE_WAIT_FOR_PLAYERS_TO_LOAD",
        ]
    ):
        return
    match_id = dota_data["matchid"]
    t = dota_data["game_time"]
    p = Path(G._matches) / match_id
    sync = p / "sync.txt"
    if not p.exists():
        p.mkdir()
        set_path(str(p.absolute()))
        start()
    if not sync.exists():
        sync.write_text(
            f"Recording started - {time.strftime('%Y-%m-%d %H:%M:%S')} - game time - {t}"
        )


def script_properties():
    props = S.obs_properties_create()
    S.obs_properties_add_path(
        props, "_matches", "Matches destination", S.OBS_PATH_DIRECTORY, "", None
    )
    S.obs_properties_add_button(props, "button1", "Start", start_btn)
    S.obs_properties_add_button(props, "button2", "Stop", stop_btn)
    return props


def script_update(settings):
    G._matches = S.obs_data_get_string(settings, "_matches")


def script_load(settings):
    t = threading.Thread(target=main)
    t.start()


def script_unload():
    G.shutdown = True
