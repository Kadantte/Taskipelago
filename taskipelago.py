import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml

RANDOM_TOKEN = "RANDOM"


class TaskRow:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent)

        self.task_var = tk.StringVar()
        self.reward_var = tk.StringVar()
        self.random_var = tk.BooleanVar()

        ttk.Entry(self.frame, textvariable=self.task_var, width=30).grid(row=0, column=0, padx=5)
        ttk.Entry(self.frame, textvariable=self.reward_var, width=30).grid(row=0, column=1, padx=5)
        ttk.Checkbutton(
            self.frame,
            text="Random",
            variable=self.random_var,
            command=self.on_random_toggle
        ).grid(row=0, column=2, padx=5)

    def on_random_toggle(self):
        if self.random_var.get():
            self.reward_var.set(RANDOM_TOKEN)

    def get_data(self):
        return (
            self.task_var.get().strip(),
            self.reward_var.get().strip(),
            self.random_var.get()
        )


class TaskipelagoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Taskipelago")
        self.geometry("950x600")

        self.rows = []

        self.build_ui()

    def build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.editor_tab = ttk.Frame(notebook)
        notebook.add(self.editor_tab, text="Task Editor")

        # ─── Player / Global Options ──────────────────────────────
        meta = ttk.LabelFrame(self.editor_tab, text="Player / Global Settings")
        meta.pack(fill="x", padx=10, pady=10)

        ttk.Label(meta, text="Player Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.player_name_var = tk.StringVar()
        ttk.Entry(meta, textvariable=self.player_name_var, width=25).grid(row=0, column=1, padx=5)

        ttk.Label(meta, text="Progression Balancing (0–99):").grid(row=0, column=2, sticky="w", padx=5)
        self.progression_var = tk.IntVar(value=50)
        ttk.Spinbox(meta, from_=0, to=99, textvariable=self.progression_var, width=5).grid(row=0, column=3, padx=5)

        ttk.Label(meta, text="Accessibility:").grid(row=0, column=4, sticky="w", padx=5)
        self.accessibility_var = tk.StringVar(value="full")
        ttk.Combobox(
            meta,
            textvariable=self.accessibility_var,
            values=["full", "items", "minimal"],
            width=10,
            state="readonly"
        ).grid(row=0, column=5, padx=5)

        # ─── Task Table Header ────────────────────────────────────
        header = ttk.Frame(self.editor_tab)
        header.pack(pady=5)

        ttk.Label(header, text="Task", width=30).grid(row=0, column=0)
        ttk.Label(header, text="Reward / Challenge", width=30).grid(row=0, column=1)
        ttk.Label(header, text="Random?").grid(row=0, column=2)

        self.rows_frame = ttk.Frame(self.editor_tab)
        self.rows_frame.pack(fill="both", expand=True)

        controls = ttk.Frame(self.editor_tab)
        controls.pack(pady=10)

        ttk.Button(controls, text="Add Task", command=self.add_row).grid(row=0, column=0, padx=5)
        ttk.Button(controls, text="Export YAML", command=self.export_yaml).grid(row=0, column=1, padx=5)

        # ─── DeathLink Pool ───────────────────────────────────────
        dl_frame = ttk.LabelFrame(self.editor_tab, text="DeathLink Task Pool")
        dl_frame.pack(fill="x", padx=10, pady=10)

        self.death_link_text = tk.Text(dl_frame, height=5)
        self.death_link_text.pack(fill="x", padx=5, pady=5)

        self.add_row()

    def add_row(self):
        row = TaskRow(self.rows_frame)
        row.frame.pack(pady=2)
        self.rows.append(row)

    def export_yaml(self):
        player_name = self.player_name_var.get().strip()
        if not player_name:
            messagebox.showerror("Error", "Player name is required.")
            return

        tasks = []
        rewards = []

        for row in self.rows:
            task, reward, random_flag = row.get_data()
            if not task:
                continue
            if not reward:
                messagebox.showerror("Error", "Each task must have a reward or be marked Random.")
                return

            tasks.append(task)
            rewards.append(RANDOM_TOKEN if random_flag else reward)

        if not tasks:
            messagebox.showerror("Error", "No tasks defined.")
            return

        death_link_pool = [
            line.strip()
            for line in self.death_link_text.get("1.0", "end").splitlines()
            if line.strip()
        ]

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
