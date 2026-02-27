import tkinter as tk

from engine.config import BG_MENU
from engine.menu import MainMenuFrame
from engine.game_frame import GameFrame


class TextAdventureGame:
    """游戏主控制器，负责主菜单与游戏帧的切换"""

    MENU_SIZE = "1280x720"
    GAME_SIZE = "1740x720"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("剧本阅读器")
        self.root.configure(bg=BG_MENU)
        self.root.resizable(True, True)
        self.root.minsize(1280, 720)
        self._frame: tk.Frame | None = None
        self._apply_window_size(1280, 720, preserve_center=False)
        self.show_main_menu()

    def _apply_window_size(self, width: int, height: int, preserve_center: bool = True):
        self.root.update_idletasks()
        if preserve_center:
            cur_w = self.root.winfo_width() or width
            cur_h = self.root.winfo_height() or height
            cur_x = self.root.winfo_x()
            cur_y = self.root.winfo_y()
            cx = cur_x + cur_w // 2
            cy = cur_y + cur_h // 2
        else:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            cx = screen_w // 2
            cy = screen_h // 2

        x = max(0, cx - width // 2)
        y = max(0, cy - height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _set_frame(self, frame: tk.Frame):
        if self._frame:
            self._frame.destroy()
        self._frame = frame

    def show_main_menu(self):
        self._apply_window_size(1280, 720, preserve_center=True)
        self._set_frame(MainMenuFrame(self.root, self))

    def start_game(self, script_path: str):
        self._apply_window_size(1740, 720, preserve_center=True)
        self._set_frame(GameFrame(self.root, self, script_path))


def main():
    root = tk.Tk()
    TextAdventureGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
