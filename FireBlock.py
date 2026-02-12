import ctypes
import json
import os
import subprocess
import sys
import webbrowser  # اضافه شده برای باز کردن لینک
from tkinter import filedialog

import customtkinter as ctk

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# --- Resource & Path Helper ---
def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)


# --- Font Loader ---
def load_custom_font(font_path):
    if not os.path.exists(font_path):
        return False
    try:
        path_buf = ctypes.create_unicode_buffer(font_path)
        ctypes.windll.gdi32.AddFontResourceExW(ctypes.byref(path_buf), 0x10, 0)
        return True
    except:
        return False


FONT_FAMILY = "SN Pro"
FONT_FILES = ["SNPro-Regular.ttf", "SNPro-Bold.ttf"]
for f in FONT_FILES:
    load_custom_font(resource_path(f))


# --- Dark Theme Colors ---
class Colors:
    BG = "#1C1C1E"
    CARD = "#2C2C2E"
    BLUE = "#007AFF"
    RED = "#FF453A"
    GREEN = "#32D74B"
    TEXT_MAIN = "#FFFFFF"
    TEXT_SUB = "#98989D"
    HOVER = "#3A3A3C"


APP_WIDTH = 400
# ارتفاع را کمی افزایش دادیم تا جا برای فوتر باز شود
HEIGHT_COMPACT = 370 
HEIGHT_EXPANDED = 540


# --- Backend Logic ---
class FirewallManager:
    DATA_FILE = os.path.join(get_base_path(), "blocked_apps.json")

    @staticmethod
    def load_blocked_list():
        if os.path.exists(FirewallManager.DATA_FILE):
            try:
                with open(FirewallManager.DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    @staticmethod
    def save_blocked_list(data):
        with open(FirewallManager.DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def block_app(exe_path):
        exe_name = os.path.basename(exe_path)
        rule_name = f"{exe_name}[FireBlock]"

        current_list = FirewallManager.load_blocked_list()
        for item in current_list:
            if item["path"].lower() == exe_path.lower():
                return False, "App is already blocked."

        cmd_out = f'netsh advfirewall firewall add rule name="{rule_name}" dir=out action=block program="{exe_path}" enable=yes'
        cmd_in = f'netsh advfirewall firewall add rule name="{rule_name}" dir=in action=block program="{exe_path}" enable=yes'

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd_out, capture_output=True, startupinfo=startupinfo)
            subprocess.run(cmd_in, capture_output=True, startupinfo=startupinfo)

            current_list.append({"name": exe_name, "path": exe_path, "rule": rule_name})
            FirewallManager.save_blocked_list(current_list)
            return True, f"Blocked: {exe_name}"
        except Exception as e:
            return False, "System Error (Run as Admin)"

    @staticmethod
    def unblock_app(item_data):
        rule_name = item_data["rule"]
        cmd = f'netsh advfirewall firewall delete rule name="{rule_name}"'
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, capture_output=True, startupinfo=startupinfo)

            current_list = FirewallManager.load_blocked_list()
            new_list = [d for d in current_list if d["rule"] != rule_name]
            FirewallManager.save_blocked_list(new_list)
            return True
        except:
            return False


# --- UI Components ---
class BlockedRow(ctk.CTkFrame):
    def __init__(self, master, data, unblock_callback):
        super().__init__(master, fg_color=Colors.CARD, corner_radius=12)
        self.pack(fill="x", pady=4, padx=5)

        self.lbl = ctk.CTkLabel(
            self,
            text=data["name"],
            font=(FONT_FAMILY, 13),
            text_color=Colors.TEXT_MAIN,
            anchor="w",
        )
        self.lbl.pack(side="left", padx=(12, 0), fill="x", expand=True, pady=10)

        self.btn = ctk.CTkButton(
            self,
            text="Unblock",
            width=65,
            height=26,
            corner_radius=15,
            font=(FONT_FAMILY, 11, "bold"),
            fg_color=Colors.HOVER,
            hover_color=Colors.RED,
            text_color=Colors.RED,
            command=lambda: unblock_callback(data, self),
        )
        self.btn.bind("<Enter>", lambda e: self.btn.configure(text_color="#FFFFFF"))
        self.btn.bind("<Leave>", lambda e: self.btn.configure(text_color=Colors.RED))
        self.btn.pack(side="right", padx=10)


class MinimalBlocker(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FireBlock")
        self.geometry(f"{APP_WIDTH}x{HEIGHT_COMPACT}")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG)

        try:
            icon_path = resource_path("FireBlock.ico")
            self.iconbitmap(bitmap=icon_path)
        except Exception as e:
            print(f"Icon Error: {e}")

        self.is_expanded = False

        # --- UI LAYOUT ---

        # 1. Title
        self.lbl_title = ctk.CTkLabel(
            self,
            text="FireBlock",
            font=(FONT_FAMILY, 24, "bold"),
            text_color=Colors.TEXT_MAIN,
        )
        self.lbl_title.pack(pady=(35, 5), anchor="center")

        self.lbl_sub = ctk.CTkLabel(
            self,
            text="Select .exe to disable internet",
            font=(FONT_FAMILY, 12),
            text_color=Colors.TEXT_SUB,
        )
        self.lbl_sub.pack(pady=(0, 25), anchor="center")

        # 2. Input
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x", padx=30)

        self.entry_path = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Path to application...",
            height=42,
            corner_radius=12,
            font=(FONT_FAMILY, 13),
            fg_color=Colors.CARD,
            border_width=0,
            text_color=Colors.TEXT_MAIN,
            placeholder_text_color=Colors.TEXT_SUB,
        )
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_browse = ctk.CTkButton(
            self.input_frame,
            text="📂",
            width=42,
            height=42,
            corner_radius=12,
            fg_color=Colors.CARD,
            hover_color=Colors.HOVER,
            text_color=Colors.BLUE,
            font=(FONT_FAMILY, 18),
            command=self.browse_file,
        )
        self.btn_browse.pack(side="right")

        # 3. Action Button
        self.btn_block = ctk.CTkButton(
            self,
            text="Block Connection",
            height=46,
            corner_radius=12,
            fg_color=Colors.BLUE,
            hover_color="#0062CC",
            font=(FONT_FAMILY, 14, "bold"),
            command=self.perform_block,
        )
        self.btn_block.pack(fill="x", padx=30, pady=(20, 10))

        # 4. Status Message
        self.lbl_status = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, 12), height=20)
        self.lbl_status.pack(pady=(0, 5))

        # 5. Toggle List Button
        self.btn_toggle = ctk.CTkButton(
            self,
            text="Show Blocked Apps (0) ▼",
            font=(FONT_FAMILY, 12, "bold"),
            fg_color="transparent",
            text_color=Colors.TEXT_SUB,
            hover_color=Colors.CARD,
            height=45,
            corner_radius=12,
            anchor="center",
            command=self.toggle_list,
        )
        self.btn_toggle.pack(fill="x", padx=30)

        # 6. Credits / Footer (By Arman Haghshenas)
        # این بخش را با side="bottom" پک میکنیم تا همیشه پایین بماند
        self.lbl_credits = ctk.CTkLabel(
            self,
            text="By Arman Haghshenas",
            font=(FONT_FAMILY, 11),
            text_color=Colors.TEXT_SUB,
            cursor="hand2"  # تغییر نشانگر موس به دست
        )
        self.lbl_credits.pack(side="bottom", pady=(0, 15))
        
        # اتصال رویداد کلیک برای باز کردن سایت
        self.lbl_credits.bind("<Button-1>", lambda e: webbrowser.open("https://armvnhs.ir"))
        # افکت تغییر رنگ هنگام هاور
        self.lbl_credits.bind("<Enter>", lambda e: self.lbl_credits.configure(text_color=Colors.BLUE))
        self.lbl_credits.bind("<Leave>", lambda e: self.lbl_credits.configure(text_color=Colors.TEXT_SUB))

        # 7. Hidden List (Scrollable) - Will be packed between toggle and credits
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", height=200
        )

        self.update_count()

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if f:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, f.replace("/", "\\"))

    def show_status(self, message, is_error=False):
        color = Colors.RED if is_error else Colors.GREEN
        self.lbl_status.configure(text=message, text_color=color)
        self.after(3000, lambda: self.lbl_status.configure(text=""))

    def perform_block(self):
        path = self.entry_path.get()
        if not path or not os.path.exists(path):
            self.show_status("Invalid file path", True)
            return

        success, msg = FirewallManager.block_app(path)
        self.show_status(msg, is_error=not success)

        if success:
            self.entry_path.delete(0, "end")
            self.refresh_list()
            self.update_count()

    def update_count(self):
        count = len(FirewallManager.load_blocked_list())
        arrow = "▲" if self.is_expanded else "▼"
        prefix = "Hide List" if self.is_expanded else "Show Blocked Apps"
        self.btn_toggle.configure(text=f"{prefix} ({count})  {arrow}")

    def toggle_list(self):
        if self.is_expanded:
            self.list_frame.pack_forget()
            self.geometry(f"{APP_WIDTH}x{HEIGHT_COMPACT}")
            self.is_expanded = False
        else:
            self.geometry(f"{APP_WIDTH}x{HEIGHT_EXPANDED}")
            # لیست را قبل از فوتر پک میکنیم
            self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
            self.refresh_list()
            self.is_expanded = True

        self.update_count()

    def refresh_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        data = FirewallManager.load_blocked_list()
        if not data:
            ctk.CTkLabel(
                self.list_frame, text="No apps blocked yet", text_color=Colors.TEXT_SUB
            ).pack(pady=20)
            return

        for item in reversed(data):
            BlockedRow(self.list_frame, item, self.handle_unblock)

    def handle_unblock(self, item_data, row_obj):
        if FirewallManager.unblock_app(item_data):
            row_obj.destroy()
            self.show_status(f"Unblocked: {item_data['name']}")
            self.update_count()
            if not self.list_frame.winfo_children():
                self.refresh_list()


if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
    else:
        app = MinimalBlocker()
        app.mainloop()