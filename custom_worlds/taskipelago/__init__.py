from __future__ import annotations

from typing import Dict, List, Any

from BaseClasses import Item, ItemClassification, Location, Region
from worlds.AutoWorld import World, WebWorld
from worlds.LauncherComponents import Component, Type, components, launch_subprocess
from worlds.generic.Rules import set_rule

from .options import TaskipelagoOptions

print("Loading Taskipelago world module...")

BASE_LOCATION_ID = 910_000          # REWARD locations (multiworld items)
BASE_COMPLETE_LOC_ID = 913_000      # COMPLETION locations (logic tokens/events)
BASE_ITEM_ID = 911_000              # Reward filler items
MAX_TASKS = 1000

class TaskipelagoWeb(WebWorld):
    game = "Taskipelago"


class TaskipelagoItem(Item):
    game = "Taskipelago"


class TaskipelagoLocation(Location):
    game = "Taskipelago"


class TaskipelagoWorld(World):
    game = "Taskipelago"
    web = TaskipelagoWeb()
    options_dataclass = TaskipelagoOptions

    # These get populated during generate_early() for the current generation run.
    item_name_to_id: Dict[str, int] = {}
    location_name_to_id: Dict[str, int] = {}

    # Pre-register a stable ID->name mapping so the server can resolve names and stuff.
    location_name_to_id = {}
    for i in range(1, MAX_TASKS + 1):
        location_name_to_id[f"Task {i} (Reward)"] = BASE_LOCATION_ID + (i - 1)
        location_name_to_id[f"Task {i} (Complete)"] = BASE_COMPLETE_LOC_ID + (i - 1)
    item_name_to_id = {f"Reward {i}": BASE_ITEM_ID + (i - 1) for i in range(1, MAX_TASKS + 1)}

    def generate_early(self) -> None:
        tasks = [str(t).strip() for t in self.options.tasks.value if str(t).strip()]
        rewards = [str(r).strip() for r in self.options.rewards.value if str(r).strip()]

        if not tasks:
            raise Exception("Taskipelago: tasks list is empty.")
        if len(tasks) != len(rewards):
            raise Exception(f"Taskipelago: tasks ({len(tasks)}) and rewards ({len(rewards)}) must be same length.")

        # DeathLink pool validation
        if bool(self.options.death_link):
            dl_pool = [str(x).strip() for x in self.options.death_link_pool.value if str(x).strip()]
            if not dl_pool:
                raise Exception("Taskipelago: death_link is enabled but death_link_pool is empty.")

        n = len(tasks)
        if n > MAX_TASKS:
            raise Exception(f"Taskipelago: too many tasks ({n}). Max supported is {MAX_TASKS}.")

        # --- prereqs ---
        raw_prereqs = list(getattr(self.options, "task_prereqs").value or [])
        # normalize length
        if len(raw_prereqs) < n:
            raw_prereqs += [""] * (n - len(raw_prereqs))
        raw_prereqs = raw_prereqs[:n]
        raw_prereqs = [str(x).strip() for x in raw_prereqs]

        parsed_prereqs = []  # list[list[int]] each is list of 0-based indices
        for i, txt in enumerate(raw_prereqs):
            if not txt:
                parsed_prereqs.append([])
                continue
            parts = [p.strip() for p in txt.split(",") if p.strip()]
            reqs = []
            for p in parts:
                try:
                    idx_1 = int(p)
                except ValueError:
                    raise Exception(f"Taskipelago: invalid prereq '{p}' on task {i+1}. Use comma-separated integers like '1,2'.")
                if idx_1 < 1 or idx_1 > n:
                    raise Exception(f"Taskipelago: prereq '{idx_1}' on task {i+1} is out of range (1..{n}).")
                if idx_1 == (i + 1):
                    raise Exception(f"Taskipelago: task {i+1} cannot require itself.")
                reqs.append(idx_1 - 1)
            # de-dupe while preserving order
            seen = set()
            reqs = [x for x in reqs if not (x in seen or seen.add(x))]
            parsed_prereqs.append(reqs)

        # If lock_prereqs is ON, detect cycles (generator-visible logic must be acyclic)
        lock = bool(getattr(self.options, "lock_prereqs"))
        if lock:
            # simple DFS cycle detect on task graph edges i -> prereq
            visiting = set()
            visited = set()

            def dfs(v: int):
                if v in visiting:
                    raise Exception("Taskipelago: prereq graph contains a cycle. Fix your prereqs.")
                if v in visited:
                    return
                visiting.add(v)
                for u in parsed_prereqs[v]:
                    dfs(u)
                visiting.remove(v)
                visited.add(v)

            for i in range(n):
                dfs(i)

        # store
        self._tasks = tasks
        self._rewards = rewards
        self._raw_prereqs = raw_prereqs
        self._parsed_prereqs = parsed_prereqs
        self._lock_prereqs = lock

        # Stable names
        self._location_names = [f"Task {i+1}" for i in range(n)]
        self._reward_item_names = [f"Reward {i+1}" for i in range(n)]

        # ID maps for this generation
        self.location_name_to_id = {name: BASE_LOCATION_ID + i for i, name in enumerate(self._location_names)}
        # rewards (optional)
        self.item_name_to_id = {name: BASE_ITEM_ID + i for i, name in enumerate(self._reward_item_names)}

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        tasks_region = Region("Tasks", self.player, self.multiworld)

        for loc_name in self._location_names:
            loc_id = self.location_name_to_id[loc_name]
            tasks_region.locations.append(TaskipelagoLocation(self.player, loc_name, loc_id, tasks_region))

        self.multiworld.regions += [menu, tasks_region]
        menu.connect(tasks_region)

    def create_items(self) -> None:
        # Optional: reward items (these can still be sent around as filler if you want).
        for name in self._reward_item_names:
            self.multiworld.itempool.append(
                TaskipelagoItem(name, ItemClassification.filler, self.item_name_to_id[name], self.player)
            )

        # REQUIRED for option 2: progression tokens (these will be locked to their own task locations)
        # We do NOT put these in the itempool; we lock-place them in generate_basic().
        # They still need stable IDs and to exist as Items.
        self._token_items = []
        for name in self._token_item_names:
            self._token_items.append(
                TaskipelagoItem(name, ItemClassification.progression, self.item_name_to_id[name], self.player)
            )


    def set_rules(self) -> None:
        if not getattr(self, "_lock_prereqs", False):
            return

        # For each task location i, require owning completion tokens for its prereqs.
        for i, loc_name in enumerate(self._location_names):
            req_indices = self._parsed_prereqs[i]
            if not req_indices:
                continue

            required_token_names = [self._token_item_names[j] for j in req_indices]
            location = self.multiworld.get_location(loc_name, self.player)

            def rule(state, req=tuple(required_token_names), player=self.player):
                return all(state.has(token_name, player) for token_name in req)

            location.access_rule = rule

    def generate_basic(self) -> None:
        for i, loc_name in enumerate(self._location_names):
            loc = self.multiworld.get_location(loc_name, self.player)
            loc.place_locked_item(self._token_items[i])

        # Goal: all task locations checked (equivalent to owning all tokens)
        my_locations = [self.multiworld.get_location(name, self.player) for name in self._location_names]
        self.multiworld.completion_condition[self.player] = lambda state: all(
            loc in state.locations_checked for loc in my_locations
        )

    def fill_slot_data(self) -> Dict[str, Any]:
        return {
            "tasks": list(self._tasks),
            "rewards": list(self._rewards),

            "task_prereqs": list(self._raw_prereqs),
            "lock_prereqs": bool(getattr(self, "_lock_prereqs", False)),

            "death_link_pool": [str(x).strip() for x in self.options.death_link_pool.value if str(x).strip()],
            "death_link_enabled": bool(self.options.death_link),

            "base_location_id": BASE_LOCATION_ID,
            "base_item_id": BASE_ITEM_ID,     # if you still use Reward {i}
            "base_token_id": BASE_TOKEN_ID,   # NEW: if you ever want to resolve tokens client-side
        }

def launch_client(*args):
    from .client import launch
    launch_subprocess(launch, name="TaskipelagoClient", args=args)

components.append(
    Component(
        "Taskipelago Client",
        func=launch_client,
        component_type=Type.CLIENT,
    )
)