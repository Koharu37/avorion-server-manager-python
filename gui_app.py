import customtkinter as ctk
import json
import os
import subprocess
import threading
import time
import psutil
from pathlib import Path
from tkinter import filedialog

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "steamcmdPath": "C:\\steamcmd",
    "serverPath": "C:\\avorion-server",
    "galaxyName": "avorion_galaxy",
    "serverName": "My Avorion Server",
    "port": 27000,
    "maxPlayers": 10,
    "saveInterval": 300,
    "adminSteamId": "",
    "seed": "",
    "loadPath": "",
    "discordWebhookUrl": "",
    "discordEnabled": False
}

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            cfg.update(loaded)
    except Exception:
        pass
    return cfg

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Avorion Server Manager")
        self.geometry("1000x700")
        self.config = load_config()
        self.is_running = False
        
        self.server_process = None
        self.install_process = None
        
        # UI Setup: Sidebar + Main Frame
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Avorion\nManager", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 30))
        
        self.btn_nav_dashboard = ctk.CTkButton(self.sidebar_frame, text="🏠 대시보드", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=lambda: self.select_frame("dashboard"))
        self.btn_nav_dashboard.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_nav_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ 서버 설정", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=lambda: self.select_frame("settings"))
        self.btn_nav_settings.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_nav_console = ctk.CTkButton(self.sidebar_frame, text="💻 콘솔", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=lambda: self.select_frame("console"))
        self.btn_nav_console.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_nav_steamcmd = ctk.CTkButton(self.sidebar_frame, text="📥 SteamCMD", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=lambda: self.select_frame("steamcmd"))
        self.btn_nav_steamcmd.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="테마 설정:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 20))
        self.appearance_mode_optionemenu.set("Dark")
        
        # --- Main Frames ---
        self.frames = {}
        
        self.frame_dashboard = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_settings = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_console = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_steamcmd = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self.frames["dashboard"] = self.frame_dashboard
        self.frames["settings"] = self.frame_settings
        self.frames["console"] = self.frame_console
        self.frames["steamcmd"] = self.frame_steamcmd
        
        self.setup_dashboard()
        self.setup_settings()
        self.setup_console()
        self.setup_steamcmd()
        
        self.select_frame("dashboard")
        self.update_status_loop()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def select_frame(self, name):
        # Update button colors
        buttons = {
            "dashboard": self.btn_nav_dashboard,
            "settings": self.btn_nav_settings,
            "console": self.btn_nav_console,
            "steamcmd": self.btn_nav_steamcmd
        }
        for k, btn in buttons.items():
            if k == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")
        
        # Show selected frame
        for f in self.frames.values():
            f.grid_forget()
        self.frames[name].grid(row=0, column=1, sticky="nsew")

    # ----- DASHBOARD -----
    def setup_dashboard(self):
        self.frame_dashboard.grid_columnconfigure(0, weight=1)
        self.frame_dashboard.grid_rowconfigure(0, weight=1)
        
        card = ctk.CTkFrame(self.frame_dashboard, corner_radius=15)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl_title = ctk.CTkLabel(card, text="서버 제어", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_title.pack(pady=(30, 10), padx=50)
        
        self.lbl_status = ctk.CTkLabel(card, text="🔴 OFFLINE", font=ctk.CTkFont(size=28, weight="bold"), text_color="#ff4444")
        self.lbl_status.pack(pady=(10, 30))
        
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(pady=(0, 40), padx=40)
        
        self.btn_start = ctk.CTkButton(btn_frame, text="▶ 서버 시작", font=ctk.CTkFont(size=16, weight="bold"), height=45, fg_color="#2ecc71", hover_color="#27ae60", command=self.start_server)
        self.btn_start.pack(side="left", padx=15)
        
        self.btn_stop = ctk.CTkButton(btn_frame, text="■ 서버 중지", font=ctk.CTkFont(size=16, weight="bold"), height=45, fg_color="#e74c3c", hover_color="#c0392b", state="disabled", command=self.stop_server)
        self.btn_stop.pack(side="left", padx=15)

        # 자원 사용량 카드
        self.card_usage = ctk.CTkFrame(self.frame_dashboard, corner_radius=15)
        self.card_usage.place(relx=0.5, rely=0.8, anchor="center")
        
        self.lbl_cpu = ctk.CTkLabel(self.card_usage, text="CPU: 0%", font=ctk.CTkFont(size=14, family="Consolas"))
        self.lbl_cpu.pack(side="left", padx=20, pady=15)
        
        self.lbl_ram = ctk.CTkLabel(self.card_usage, text="RAM: 0MB", font=ctk.CTkFont(size=14, family="Consolas"))
        self.lbl_ram.pack(side="left", padx=20, pady=15)

    # ----- SETTINGS -----
    def setup_settings(self):
        self.frame_settings.grid_columnconfigure(0, weight=1)
        self.frame_settings.grid_rowconfigure(0, weight=1)
        
        # Scrollable Frame for settings
        scroll = ctk.CTkScrollableFrame(self.frame_settings, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        scroll.grid_columnconfigure(0, weight=1)
        
        # 1. Path Settings Card
        card_paths = ctk.CTkFrame(scroll, corner_radius=10)
        card_paths.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        card_paths.grid_columnconfigure(1, weight=1)
        
        lbl_paths = ctk.CTkLabel(card_paths, text="폴더 및 경로", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_paths.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        self.entries = {}
        
        # steamcmdPath
        ctk.CTkLabel(card_paths, text="SteamCMD 경로").grid(row=1, column=0, sticky="w", padx=20, pady=10)
        f_steam = ctk.CTkFrame(card_paths, fg_color="transparent")
        f_steam.grid(row=1, column=1, sticky="ew", padx=20, pady=10)
        f_steam.grid_columnconfigure(0, weight=1)
        ent_steam = ctk.CTkEntry(f_steam)
        ent_steam.insert(0, str(self.config.get("steamcmdPath", "")))
        ent_steam.grid(row=0, column=0, sticky="ew")
        self.entries["steamcmdPath"] = ent_steam
        ctk.CTkButton(f_steam, text="폴더 찾기", width=70, command=lambda: self.browse_path("steamcmdPath")).grid(row=0, column=1, padx=(10, 0))
        ctk.CTkButton(f_steam, text="다운로드", width=70, fg_color="#3498db", hover_color="#2980b9", command=self.download_steamcmd).grid(row=0, column=2, padx=(10, 0))

        # serverPath
        ctk.CTkLabel(card_paths, text="서버 설치 경로").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        f_server = ctk.CTkFrame(card_paths, fg_color="transparent")
        f_server.grid(row=2, column=1, sticky="ew", padx=20, pady=10)
        f_server.grid_columnconfigure(0, weight=1)
        ent_server = ctk.CTkEntry(f_server)
        ent_server.insert(0, str(self.config.get("serverPath", "")))
        ent_server.grid(row=0, column=0, sticky="ew")
        self.entries["serverPath"] = ent_server
        ctk.CTkButton(f_server, text="폴더 찾기", width=70, command=lambda: self.browse_path("serverPath")).grid(row=0, column=1, padx=(10, 0))
        
        # loadPath
        ctk.CTkLabel(card_paths, text="서버 불러오기 (폴더)").grid(row=3, column=0, sticky="w", padx=20, pady=10)
        f_load = ctk.CTkFrame(card_paths, fg_color="transparent")
        f_load.grid(row=3, column=1, sticky="ew", padx=20, pady=10)
        f_load.grid_columnconfigure(0, weight=1)
        ent_load = ctk.CTkEntry(f_load, placeholder_text="서버 데이터 폴더를 선택하세요 (server.ini가 있는 폴더)")
        # 마이그레이션: 기존 dataPath가 있으면 loadPath로 가져옴
        old_val = self.config.get("loadPath", self.config.get("dataPath", ""))
        ent_load.insert(0, str(old_val))
        ent_load.grid(row=0, column=0, sticky="ew")
        self.entries["loadPath"] = ent_load
        ctk.CTkButton(f_load, text="폴더 찾기", width=70, command=lambda: self.browse_path("loadPath")).grid(row=0, column=1, padx=(10, 0))
        
        self.lbl_load_status = ctk.CTkLabel(card_paths, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_load_status.grid(row=4, column=1, sticky="w", padx=20, pady=(0, 10))
        
        # 입력칸 값이 바뀔 때마다 상태 체크
        ent_load.bind("<KeyRelease>", self.check_load_path)
        self.after(100, lambda: self.check_load_path(None))
        
        # 2. Server Settings Card
        card_srv = ctk.CTkFrame(scroll, corner_radius=10)
        card_srv.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        card_srv.grid_columnconfigure(1, weight=1)
        
        lbl_srv = ctk.CTkLabel(card_srv, text="서버 환경 설정", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_srv.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        row_idx = 1
        for key in ["serverName", "galaxyName", "port", "maxPlayers", "saveInterval", "adminSteamId", "seed"]:
            val = self.config.get(key, "")
            ctk.CTkLabel(card_srv, text=key).grid(row=row_idx, column=0, sticky="w", padx=20, pady=10)
            ent = ctk.CTkEntry(card_srv)
            ent.insert(0, str(val))
            ent.grid(row=row_idx, column=1, sticky="ew", padx=20, pady=10)
            self.entries[key] = ent
            row_idx += 1
            
        # 3. Discord Settings Card
        card_discord = ctk.CTkFrame(scroll, corner_radius=10)
        card_discord.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        card_discord.grid_columnconfigure(1, weight=1)
        
        lbl_discord = ctk.CTkLabel(card_discord, text="디스코드 알림 연동", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_discord.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        self.chk_discord_var = ctk.BooleanVar(value=bool(self.config.get("discordEnabled", False)))
        chk_discord = ctk.CTkCheckBox(card_discord, text="디스코드 알림 켜기", variable=self.chk_discord_var)
        chk_discord.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=10)
        self.entries["discordEnabled_chk"] = chk_discord
        
        ctk.CTkLabel(card_discord, text="Webhook URL").grid(row=2, column=0, sticky="w", padx=20, pady=10)
        ent_discord = ctk.CTkEntry(card_discord, placeholder_text="https://discord.com/api/webhooks/...")
        ent_discord.insert(0, str(self.config.get("discordWebhookUrl", "")))
        ent_discord.grid(row=2, column=1, sticky="ew", padx=20, pady=10)
        self.entries["discordWebhookUrl"] = ent_discord
            
        btn_save = ctk.CTkButton(scroll, text="💾 설정 저장", font=ctk.CTkFont(weight="bold"), height=40, command=self.save_settings_action)
        btn_save.grid(row=3, column=0, pady=20)

    def browse_path(self, key):
        path = filedialog.askdirectory(title=f"{key} 폴더 선택")
        if path:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, path)
            if key == "loadPath":
                self.check_load_path(None)

    def check_load_path(self, event):
        path_str = self.entries["loadPath"].get().strip()
        if not path_str:
            self.lbl_load_status.configure(text="💡 기본 저장 경로(%AppData%)가 사용됩니다.", text_color="gray")
            return
            
        p = Path(path_str)
        if p.exists() and p.is_dir():
            if (p / "server.ini").exists():
                self.lbl_load_status.configure(text=f"✅ 기존 서버 인식됨 (이름: {p.name})", text_color="#2ecc71")
            else:
                self.lbl_load_status.configure(text=f"⚠️ 새 서버가 이 위치에 생성됩니다.", text_color="#f39c12")
        else:
            self.lbl_load_status.configure(text="❌ 올바르지 않은 폴더 경로입니다.", text_color="#ff4444")

    def download_steamcmd(self):
        def _download():
            path_str = self.entries["steamcmdPath"].get().strip()
            if not path_str:
                path_str = r"C:\steamcmd"
                self.after(0, lambda: self.entries["steamcmdPath"].insert(0, path_str))
            
            target_dir = Path(path_str)
            steamcmd_exe = target_dir / "steamcmd.exe"
            
            if steamcmd_exe.exists():
                self.log_console(f"SteamCMD가 이미 {target_dir}에 존재합니다.")
                return
                
            self.log_console(f"SteamCMD 다운로드 시작... ({target_dir})")
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                
                import urllib.request
                import zipfile
                import io
                
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                        z.extractall(target_dir)
                self.log_console("SteamCMD 다운로드 및 압축 해제 완료!")
            except Exception as e:
                self.log_console(f"[오류] SteamCMD 다운로드 실패: {e}")
                
        threading.Thread(target=_download, daemon=True).start()
        self.select_frame("console")

    def save_settings_action(self):
        for k, ent in self.entries.items():
            if k == "discordEnabled_chk":
                self.config["discordEnabled"] = self.chk_discord_var.get()
                continue
            val = ent.get()
            if k in ["port", "maxPlayers", "saveInterval"]:
                try: val = int(val)
                except: pass
            self.config[k] = val
        save_config(self.config)
        self.log_console("설정이 저장되었습니다.")

    # ----- CONSOLE -----
    def setup_console(self):
        self.frame_console.grid_rowconfigure(1, weight=1)
        self.frame_console.grid_columnconfigure(0, weight=1)
        
        lbl = ctk.CTkLabel(self.frame_console, text="서버 콘솔 로그", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        self.textbox = ctk.CTkTextbox(self.frame_console, state="disabled", font=ctk.CTkFont(family="Consolas", size=13), fg_color="#000000", text_color="#00ff00")
        self.textbox.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="nsew")
        
        input_frame = ctk.CTkFrame(self.frame_console, fg_color="transparent")
        input_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.entry_cmd = ctk.CTkEntry(input_frame, placeholder_text="서버 명령어 입력 (예: /save, /stop)...", font=ctk.CTkFont(family="Consolas", size=13))
        self.entry_cmd.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_cmd.bind("<Return>", lambda e: self.send_command())
        
        btn_send = ctk.CTkButton(input_frame, text="전송", width=80, command=self.send_command)
        btn_send.grid(row=0, column=1)

    # ----- STEAMCMD -----
    def setup_steamcmd(self):
        self.frame_steamcmd.grid_columnconfigure(0, weight=1)
        self.frame_steamcmd.grid_rowconfigure(0, weight=1)
        
        card = ctk.CTkFrame(self.frame_steamcmd, corner_radius=15)
        card.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl = ctk.CTkLabel(card, text="Avorion Dedicated Server", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=(40, 5), padx=50)
        
        lbl2 = ctk.CTkLabel(card, text="App ID: 565060", font=ctk.CTkFont(size=14), text_color="gray")
        lbl2.pack(pady=(0, 30))
        
        self.btn_install = ctk.CTkButton(card, text="📥 서버 설치 / 업데이트", font=ctk.CTkFont(size=16, weight="bold"), width=250, height=50, command=self.install_server)
        self.btn_install.pack(pady=(0, 20), padx=40)
        
        self.lbl_install_status = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14))
        self.lbl_install_status.pack(pady=(0, 30))

    # ----- LOGIC -----
    def send_discord_webhook(self, content, color=3066993):
        if not self.config.get("discordEnabled"): return
        url = self.config.get("discordWebhookUrl", "").strip()
        if not url: return
        
        def _send():
            import urllib.request
            import json
            payload = {
                "embeds": [{
                    "title": "Avorion Server Status",
                    "description": content,
                    "color": color
                }]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            try:
                urllib.request.urlopen(req, timeout=5)
            except Exception as e:
                self.log_console(f"[경고] 디스코드 웹훅 전송 실패: {e}")
                
        threading.Thread(target=_send, daemon=True).start()

    def log_console(self, msg):
        def _append():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", msg + "\n")
            self.textbox.see("end")
            self.textbox.configure(state="disabled")
        self.after(0, _append)

    def stream_output(self, process, prefix=""):
        def _read(stream):
            try:
                for raw_line in iter(stream.readline, b""):
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                    if line:
                        self.log_console(f"{prefix}{line}")
            except Exception:
                pass
        threading.Thread(target=_read, args=(process.stdout,), daemon=True).start()
        threading.Thread(target=_read, args=(process.stderr,), daemon=True).start()

    def start_server(self):
        self.save_settings_action()
        
        if self.server_process and self.server_process.poll() is None:
            return
            
        server_path = Path(self.config["serverPath"])
        exe = server_path / "bin" / "AvorionServer.exe"
        if not exe.exists():
            exe = server_path / "AvorionServer.exe"
            
        if not exe.exists():
            self.log_console(f"[오류] {exe} 를 찾을 수 없습니다.")
            self.log_console("먼저 [SteamCMD] 탭에서 [서버 설치 / 업데이트]를 진행해주세요.")
            self.select_frame("steamcmd")
            return

        load_path_str = self.config.get("loadPath", "").strip()
        datapath_arg = ""
        galaxy_arg = str(self.config["galaxyName"])
        
        if load_path_str:
            p = Path(load_path_str)
            if p.parent == p:
                self.log_console("[오류] 드라이브 최상위 경로는 서버 폴더로 선택할 수 없습니다.")
                self.select_frame("console")
                return
                
            # 사용자가 선택한 폴더 자체를 서버 폴더로 사용
            datapath_arg = str(p.parent)
            galaxy_arg = p.name
                
        args = [
            str(exe),
            "--galaxy-name", galaxy_arg,
            "--server-name", str(self.config["serverName"]),
            "--port", str(self.config["port"]),
            "--max-players", str(self.config["maxPlayers"]),
            "--save-interval", str(self.config["saveInterval"]),
        ]
        
        if datapath_arg:
            args += ["--datapath", datapath_arg]
            
        if self.config.get("adminSteamId"):
            args += ["--admin", str(self.config["adminSteamId"])]
        if self.config.get("seed"):
            args += ["--seed", str(self.config["seed"])]

        self.log_console("=== 서버 시작 ===")
        self.select_frame("console")
        try:
            self.server_process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(server_path),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.stream_output(self.server_process)
        except Exception as e:
            self.log_console(f"[오류] 서버 시작 실패: {e}")

    def stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            self.log_console("=== 서버 중지 시도 중 ===")
            self.select_frame("console")
            def _stop():
                try:
                    if self.server_process.stdin:
                        self.server_process.stdin.write(b"/save\n")
                        self.server_process.stdin.flush()
                        time.sleep(2)
                        self.server_process.stdin.write(b"/stop\n")
                        self.server_process.stdin.flush()
                except:
                    pass
                for _ in range(10):
                    time.sleep(1)
                    if self.server_process.poll() is not None:
                        return
                try:
                    self.server_process.kill()
                    self.log_console("강제 종료되었습니다.")
                except: pass
            threading.Thread(target=_stop, daemon=True).start()

    def send_command(self):
        cmd = self.entry_cmd.get().strip()
        if not cmd: return
        self.entry_cmd.delete(0, "end")
        
        if self.server_process and self.server_process.poll() is None:
            self.log_console(f"> {cmd}")
            
            # /say 명령어 커스텀 처리 (게임 내에 "Server"라는 이름으로 공지)
            if cmd.startswith("/say "):
                text = cmd[5:].replace('"', '\\"')
                # Avorion Lua API를 이용해 Server 이름으로 메시지 전송
                cmd = f'/run Server():broadcastChatMessage("Server", 0, "{text}")'
                
            try:
                self.server_process.stdin.write((cmd + "\n").encode("utf-8"))
                self.server_process.stdin.flush()
            except Exception as e:
                self.log_console(f"[오류] 명령 전송 실패: {e}")
        else:
            self.log_console("[오류] 서버가 실행 중이 아닙니다.")

    def install_server(self):
        self.save_settings_action()
        
        if self.install_process and self.install_process.poll() is None:
            return
            
        steamcmd_exe = Path(self.config["steamcmdPath"]) / "steamcmd.exe"
        if not steamcmd_exe.exists():
            self.lbl_install_status.configure(text=f"SteamCMD 없음: {steamcmd_exe}", text_color="#ff4444")
            self.log_console(f"[오류] SteamCMD 경로를 찾을 수 없습니다: {steamcmd_exe}")
            return
            
        server_path = Path(self.config["serverPath"])
        try:
            server_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.lbl_install_status.configure(text="서버 설치 경로 생성 실패", text_color="#ff4444")
            self.log_console(f"[오류] 서버 설치 경로를 만들 수 없습니다 ({server_path}): {e}")
            return
            
        self.btn_install.configure(state="disabled")
        self.lbl_install_status.configure(text="설치 중... 콘솔 탭을 확인하세요.", text_color="#f39c12")
        self.log_console("=== SteamCMD: 서버 설치/업데이트 시작 ===")
        self.select_frame("console")
        
        args = [
            str(steamcmd_exe),
            "+force_install_dir", str(server_path),
            "+login", "anonymous",
            "+app_update", "565060", "validate",
            "+quit"
        ]
        
        try:
            self.install_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.config["steamcmdPath"]),
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.stream_output(self.install_process, "[SteamCMD] ")
            
            def _wait():
                self.install_process.wait()
                if self.install_process.returncode == 0:
                    self.after(0, lambda: self.lbl_install_status.configure(text="설치/업데이트 완료", text_color="#2ecc71"))
                    self.log_console("=== SteamCMD: 설치 정상 완료 ===")
                else:
                    self.after(0, lambda: self.lbl_install_status.configure(text="설치 중 오류 발생", text_color="#ff4444"))
                    self.log_console(f"=== SteamCMD: 비정상 종료 (코드: {self.install_process.returncode}) ===")
                self.after(0, lambda: self.btn_install.configure(state="normal"))
                
            threading.Thread(target=_wait, daemon=True).start()
        except Exception as e:
            self.lbl_install_status.configure(text="SteamCMD 실행 실패", text_color="#ff4444")
            self.log_console(f"[오류] SteamCMD 실행 중 예외 발생: {e}")
            self.btn_install.configure(state="normal")

    def update_status_loop(self):
        running = self.server_process is not None and self.server_process.poll() is None
        
        if running != getattr(self, "is_running", False):
            self.is_running = running
            if running:
                self.send_discord_webhook("✅ **Avorion 서버가 시작되었습니다!** 우주로 접속하세요 🚀", 3066993)
            else:
                self.send_discord_webhook("🔴 **Avorion 서버가 종료되었습니다.**", 15158332)
        
        if running:
            self.lbl_status.configure(text="🟢 ONLINE", text_color="#2ecc71")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            
            # 자원 정보 갱신
            try:
                proc = psutil.Process(self.server_process.pid)
                with proc.oneshot():
                    cpu = proc.cpu_percent()
                    ram = proc.memory_info().rss / (1024 * 1024) # MB
                    self.lbl_cpu.configure(text=f"CPU: {cpu:.1f}%")
                    self.lbl_ram.configure(text=f"RAM: {ram:.0f} MB")
            except:
                pass
        else:
            self.lbl_status.configure(text="🔴 OFFLINE", text_color="#ff4444")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.lbl_cpu.configure(text="CPU: 0%")
            self.lbl_ram.configure(text="RAM: 0 MB")
            
        self.after(2000, self.update_status_loop)

if __name__ == "__main__":
    app = App()
    app.mainloop()
