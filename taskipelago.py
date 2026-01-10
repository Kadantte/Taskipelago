import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml

RANDOM_TOKEN = "nothing here, get pranked nerd"

# ----------------------------
# Dark theme helpers (ttk)
# ----------------------------
def apply_dark_theme(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use("clam")

    bg = "#1e1e1e"
    panel = "#252526"
    field = "#2d2d30"
    fg = "#e6e6e6"
    muted = "#bdbdbd"
    border = "#3a3a3a"
    accent = "#3b82f6"

    root.configure(bg=bg)

    style.configure(".", background=bg, foreground=fg, fieldbackground=field)

    style.configure("TFrame", background=bg)
    style.configure("TLabelframe", background=bg, foreground=fg, bordercolor=border)
    style.configure("TLabelframe.Label", background=bg, foreground=fg)

    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("Muted.TLabel", background=bg, foreground=muted)

    style.configure("TButton", background=panel, foreground=fg, bordercolor=border, focusthickness=1, focuscolor=accent)
    style.map("TButton", background=[("active", "#303030")])

    style.configure("TEntry", fieldbackground=field, background=field, foreground=fg, bordercolor=border, insertcolor=fg)
    style.configure("TSpinbox", fieldbackground=field, background=field, foreground=fg, bordercolor=border, insertcolor=fg)

    style.configure("TCombobox",
                    fieldbackground=field,
                    background=field,
                    foreground=fg,
                    arrowcolor=fg,
                    bordercolor=border)
    style.map("TCombobox",
              fieldbackground=[("readonly", field)],
              background=[("readonly", field)],
              foreground=[("readonly", fg)])

    style.configure("TCheckbutton", background=bg, foreground=fg)
    style.map("TCheckbutton", background=[("active", bg)])

    style.configure("TNotebook", background=bg, bordercolor=border)
    style.configure("TNotebook.Tab", background=panel, foreground=fg, padding=(12, 6))
    style.map("TNotebook.Tab", background=[("selected", "#2f2f2f")])

    return {"bg": bg, "panel": panel, "field": field, "fg": fg, "muted": muted, "border": border, "accent": accent}


# ----------------------------
# Scrollable container
# ----------------------------
class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, colors=None):
        super().__init__(parent)
        self.colors = colors or {"bg": "#1e1e1e"}

        self.canvas = tk.Canvas(self, highlightthickness=0, bg=self.colors["bg"])
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.inner)

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda _e: widget.bind_all("<MouseWheel>", self._on_mousewheel))
        widget.bind("<Leave>", lambda _e: widget.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ----------------------------
# Rows
# ----------------------------
class TaskRow:
    def __init__(self, parent, filler_token: str):
        self.frame = ttk.Frame(parent)
        self.filler_token = filler_token

        self.task_var = tk.StringVar()
        self.reward_var = tk.StringVar()
        self.filler_var = tk.BooleanVar()

        # Save user's last non-filler reward so unchecking restores it
        self._saved_reward = ""

        self.task_entry = ttk.Entry(self.frame, textvariable=self.task_var)
        self.reward_entry = ttk.Entry(self.frame, textvariable=self.reward_var)
        self.filler_cb = ttk.Checkbutton(self.frame, text="Filler", variable=self.filler_var, command=self.on_filler_toggle)

        self.task_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.reward_entry.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self.filler_cb.grid(row=0, column=2, sticky="w")

        self.frame.grid_columnconfigure(0, weight=3)
        self.frame.grid_columnconfigure(1, weight=3)

    def on_filler_toggle(self):
        if self.filler_var.get():
            current = self.reward_var.get().strip()
            if current and current != self.filler_token:
                self._saved_reward = current
            self.reward_var.set(self.filler_token)
        else:
            self.reward_var.set(self._saved_reward)

    def get_data(self):
        return (
            self.task_var.get().strip(),
            self.reward_var.get().strip(),
            self.filler_var.get()
        )


class DeathLinkRow:
    def __init__(self, parent, on_remove):
        self.frame = ttk.Frame(parent)
        self.text_var = tk.StringVar()
        self._on_remove = on_remove

        self.entry = ttk.Entry(self.frame, textvariable=self.text_var)
        self.btn = ttk.Button(self.frame, text="Remove", command=self.remove, width=8)

        self.entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.btn.grid(row=0, column=1, sticky="e")

        self.frame.grid_columnconfigure(0, weight=1)

    def remove(self):
        self.frame.destroy()
        self._on_remove(self)

    def get_text(self):
        return self.text_var.get().strip()


# ----------------------------
# Main app
# ----------------------------
class TaskipelagoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Taskipelago")
        self.geometry("980x700")
        self.minsize(850, 600)

        self.colors = apply_dark_theme(self)

        self.task_rows = []
        self.deathlink_rows = []

        self.build_ui()

    def build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        editor = ttk.Frame(notebook)
        notebook.add(editor, text="Task Editor")

        # Use grid everywhere for consistent alignment
        editor.grid_columnconfigure(0, weight=1)
        editor.grid_rowconfigure(1, weight=0)  # meta
        editor.grid_rowconfigure(2, weight=3)  # tasks section
        editor.grid_rowconfigure(3, weight=2)  # deathlink section
        editor.grid_rowconfigure(4, weight=0)  # export button

        # --- Meta / global settings
        meta = ttk.LabelFrame(editor, text="Player / Global Settings")
        meta.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        meta.grid_columnconfigure(1, weight=1)

        ttk.Label(meta, text="Player Name:").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.player_name_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.player_name_var, width=25).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=8)

        ttk.Label(meta, text="Progression Balancing (0–99):").grid(row=0, column=2, sticky="w", padx=(0, 10), pady=8)
        self.progression_var = tk.IntVar(value=50)
        ttk.Spinbox(meta, from_=0, to=99, textvariable=self.progression_var, width=5).grid(row=0, column=3, sticky="w", padx=(0, 10), pady=8)

        ttk.Label(meta, text="Accessibility:").grid(row=0, column=4, sticky="w", padx=(0, 10), pady=8)
        self.accessibility_var = tk.StringVar(value="full")
        ttk.Combobox(meta, textvariable=self.accessibility_var, values=["full", "items", "minimal"], width=10, state="readonly") \
            .grid(row=0, column=5, sticky="w", padx=(0, 10), pady=8)

        # --- Tasks section
        tasks_section = ttk.LabelFrame(editor, text="Tasks")
        tasks_section.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        tasks_section.grid_columnconfigure(0, weight=1)
        tasks_section.grid_rowconfigure(2, weight=1)

        ttk.Label(tasks_section, text="Add tasks + rewards. Use Filler to set the filler token.", style="Muted.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

        # Column labels
        cols = ttk.Frame(tasks_section)
        cols.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 0))
        cols.grid_columnconfigure(0, weight=3)
        cols.grid_columnconfigure(1, weight=3)
        cols.grid_columnconfigure(2, weight=0)

        ttk.Label(cols, text="Task").grid(row=0, column=0, sticky="w")
        ttk.Label(cols, text="Reward / Challenge").grid(row=0, column=1, sticky="w")
        ttk.Label(cols, text="").grid(row=0, column=2, sticky="w")

        self.tasks_scroll = ScrollableFrame(tasks_section, colors=self.colors)
        self.tasks_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(8, 8))

        tasks_btns = ttk.Frame(tasks_section)
        tasks_btns.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))
        tasks_btns.grid_columnconfigure(0, weight=1)

        ttk.Button(tasks_btns, text="Add Task", command=self.add_task_row).grid(row=0, column=0, sticky="w")

        # --- DeathLink section
        dl_section = ttk.LabelFrame(editor, text="DeathLink Task Pool")
        dl_section.grid(row=3, column=0, sticky="nsew")
        dl_section.grid_columnconfigure(0, weight=1)
        dl_section.grid_rowconfigure(1, weight=1)

        ttk.Label(dl_section, text="Independent list. Used when a DeathLink is received.", style="Muted.TLabel") \
            .grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))

        self.dl_scroll = ScrollableFrame(dl_section, colors=self.colors)
        self.dl_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(8, 8))

        dl_btns = ttk.Frame(dl_section)
        dl_btns.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        dl_btns.grid_columnconfigure(0, weight=1)

        ttk.Button(dl_btns, text="Add DeathLink Task", command=self.add_deathlink_row).grid(row=0, column=0, sticky="w")

        # --- Export button
        bottom = ttk.Frame(editor)
        bottom.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bottom.grid_columnconfigure(0, weight=1)

        ttk.Button(bottom, text="Export YAML", command=self.export_yaml).grid(row=0, column=0, sticky="e")

        # Start with one row each
        self.add_task_row()
        self.add_deathlink_row()

    def add_task_row(self):
        row = TaskRow(self.tasks_scroll.inner, filler_token=RANDOM_TOKEN)
        row.frame.pack(fill="x", pady=4)
        self.task_rows.append(row)

    def add_deathlink_row(self):
        row = DeathLinkRow(self.dl_scroll.inner, on_remove=self._remove_deathlink_row)
        row.frame.pack(fill="x", pady=4)
        self.deathlink_rows.append(row)

    def _remove_deathlink_row(self, row: DeathLinkRow):
        self.deathlink_rows = [r for r in self.deathlink_rows if r is not row]

    def export_yaml(self):
        player_name = self.player_name_var.get().strip()
        if not player_name:
            messagebox.showerror("Error", "Player name is required.")
            return

        tasks = []
        rewards = []

        for row in self.task_rows:
            task, reward, filler_flag = row.get_data()

            if not task:
                continue

            if not reward:
                messagebox.showerror("Error", "Each task must have a reward or be marked Filler.")
                return

            tasks.append(task)
            rewards.append(RANDOM_TOKEN if filler_flag else reward)

        if not tasks:
            messagebox.showerror("Error", "No tasks defined.")
            return

        death_link_pool = []
        for r in self.deathlink_rows:
            txt = r.get_text()
            if txt:
                death_link_pool.append(txt)

        data = {
            "description": "YAML template for Taskipelago",
            "name": player_name,
            "game": "Taskipelago",
            "Taskipelago": {
                "progression_balancing": int(self.progression_var.get()),
                "accessibility": self.accessibility_var.get(),
                "tasks": tasks,
                "rewards": rewards,
                "death_link_pool": death_link_pool,
            }
        }

        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML Files", "*.yaml")]
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)

        messagebox.showinfo("Success", f"YAML exported to:\n{path}")


if __name__ == "__main__":
    TaskipelagoApp().mainloop()
