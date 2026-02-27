import tkinter as tk
from tkinter import ttk, messagebox

from engine.config import BG_CARD, BG_DARK, BG_HOVER, FG_DIM, FG_HINT, FG_MAIN


class ReaderSidebarTabs(tk.Frame):
    def __init__(self, parent, on_back, on_escape):
        super().__init__(parent, bg=BG_CARD, width=260)
        self.pack_propagate(False)
        self._on_back = on_back
        self._on_escape = on_escape
        self._tab_buttons: dict[str, tk.Button] = {}
        self._tab_frames: dict[str, tk.Frame] = {}

        header = tk.Frame(self, bg=BG_CARD)
        header.pack(fill=tk.X, padx=10, pady=(12, 8))

        body = tk.Frame(self, bg=BG_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._build_tab_button(header, "script", "剧本")
        self._build_tab_button(header, "actions", "操作")
        self._build_tab_button(header, "help", "帮助")

        self._tab_frames["script"] = self._build_script_tab(body)
        self._tab_frames["actions"] = self._build_actions_tab(body)
        self._tab_frames["help"] = self._build_help_tab(body)

        self.switch_tab("script")

    def _build_tab_button(self, parent: tk.Frame, key: str, text: str):
        btn = tk.Button(
            parent,
            text=text,
            font=("Microsoft YaHei", 9),
            fg=FG_MAIN,
            bg=BG_HOVER,
            activeforeground=FG_MAIN,
            activebackground=BG_HOVER,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.switch_tab(key),
        )
        btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True)
        self._tab_buttons[key] = btn

    def _build_script_tab(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG_CARD)

        tk.Label(frame, text="当前进度", font=("Microsoft YaHei", 10, "bold"),
                 fg=FG_MAIN, bg=BG_CARD).pack(anchor="w", pady=(2, 2))

        self._progress_value = tk.Label(frame, text="-", font=("Microsoft YaHei", 10),
                                        fg=FG_HINT, bg=BG_CARD, anchor="w", justify=tk.LEFT)
        self._progress_value.pack(fill=tk.X)

        self._current_seg_value = tk.Label(frame, text="当前段落：-", font=("Microsoft YaHei", 9),
                                           fg=FG_DIM, bg=BG_CARD, anchor="w", justify=tk.LEFT)
        self._current_seg_value.pack(fill=tk.X, pady=(4, 8))

        tk.Label(frame, text="分支视图", font=("Microsoft YaHei", 10, "bold"),
                 fg=FG_MAIN, bg=BG_CARD).pack(anchor="w", pady=(2, 4))

        tree_wrap = tk.Frame(frame, bg=BG_CARD)
        tree_wrap.pack(fill=tk.BOTH, expand=True)

        self._branch_tree = ttk.Treeview(tree_wrap, columns=("to", "kind"), show="headings", height=14)
        self._branch_tree.heading("to", text="去向")
        self._branch_tree.heading("kind", text="类型")
        self._branch_tree.column("to", width=130, anchor="w")
        self._branch_tree.column("kind", width=54, anchor="center")
        self._branch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self._branch_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._branch_tree.configure(yscrollcommand=scroll.set)
        self._branch_tree.tag_configure("current", foreground="#88ddbb")
        self._branch_tree.tag_configure("visited", foreground="#9aa0c8")

        return frame

    def _build_actions_tab(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG_CARD)

        tk.Button(frame, text="查看当前进度",
                  font=("Microsoft YaHei", 10),
                  fg=FG_MAIN, bg=BG_HOVER,
                  activeforeground=FG_MAIN, activebackground=BG_HOVER,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._show_progress_message).pack(fill=tk.X, pady=4)

        tk.Button(frame, text="返回上一段 [BackSpace]",
                  font=("Microsoft YaHei", 10),
                  fg=FG_MAIN, bg=BG_HOVER,
                  activeforeground=FG_MAIN, activebackground=BG_HOVER,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._on_back).pack(fill=tk.X, pady=4)

        tk.Button(frame, text="返回主菜单 [ESC]",
                  font=("Microsoft YaHei", 10),
                  fg=FG_MAIN, bg=BG_HOVER,
                  activeforeground=FG_MAIN, activebackground=BG_HOVER,
                  relief=tk.FLAT, cursor="hand2",
                  command=self._on_escape).pack(fill=tk.X, pady=4)

        return frame

    def _build_help_tab(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=BG_CARD)
        text = (
            "快捷键说明\n\n"
            "空格 / 左键：下一段或跳过动画\n"
            "1~9：选择分支\n"
            "BackSpace：返回上一段\n"
            "ESC：返回主菜单"
        )
        tk.Label(frame, text=text,
                 font=("Microsoft YaHei", 9),
                 fg=FG_HINT, bg=BG_CARD,
                 justify=tk.LEFT, anchor="nw").pack(fill=tk.BOTH, expand=True)
        return frame

    def switch_tab(self, key: str):
        for tab_key, frame in self._tab_frames.items():
            frame.pack_forget()
            self._tab_buttons[tab_key].configure(bg=BG_HOVER)
        self._tab_frames[key].pack(fill=tk.BOTH, expand=True)
        self._tab_buttons[key].configure(bg=BG_DARK)

    def update_script_state(self, progress_text: str, current_id: str,
                            segments: dict[str, dict], visited: set[str]):
        self._progress_value.config(text=progress_text)
        self._current_seg_value.config(text=f"当前段落：{current_id}")

        for row in self._branch_tree.get_children():
            self._branch_tree.delete(row)

        ordered_ids = list(segments.keys())
        for idx, seg_id in enumerate(ordered_ids):
            seg = segments.get(seg_id, {})
            targets = self._collect_targets(seg)
            target_text = ", ".join(targets) if targets else "END"
            kind_text = "分支" if seg.get("choices") else "线性"

            prefix = ""
            tags = ()
            if seg_id == current_id:
                prefix = "● "
                tags = ("current",)
            elif seg_id in visited:
                prefix = "✓ "
                tags = ("visited",)

            iid = f"seg-{idx}"
            self._branch_tree.insert("", "end", iid=iid,
                                     text="", values=(f"{prefix}{seg_id} → {target_text}", kind_text),
                                     tags=tags)
            if seg_id == current_id:
                self._branch_tree.selection_set(iid)
                self._branch_tree.see(iid)

    def _collect_targets(self, seg: dict) -> list[str]:
        targets: list[str] = []
        for choice in seg.get("choices", []):
            nxt = choice.get("next")
            if nxt is not None:
                targets.append(str(nxt))
        if "next" in seg and seg.get("next") is not None:
            targets.append(str(seg.get("next")))
        seen = set()
        unique = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique

    def _show_progress_message(self):
        messagebox.showinfo("当前剧本进度", self._progress_value.cget("text") or "暂无进度")
