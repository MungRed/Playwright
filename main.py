import tkinter as tk

from engine.config import BG_MENU
from engine.menu import MainMenuFrame
from engine.game_frame import GameFrame


class TextAdventureGame:
    """游戏主控制器，负责主菜单与游戏帧的切换"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("文字冒险游戏")
        self.root.geometry("1280x720")
        self.root.configure(bg=BG_MENU)
        self.root.resizable(False, False)
        self._frame: tk.Frame | None = None
        self.show_main_menu()

    def _set_frame(self, frame: tk.Frame):
        if self._frame:
            self._frame.destroy()
        self._frame = frame

    def show_main_menu(self):
        self._set_frame(MainMenuFrame(self.root, self))

    def start_game(self, script_path: str):
        self._set_frame(GameFrame(self.root, self, script_path))


def main():
    root = tk.Tk()
    TextAdventureGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
