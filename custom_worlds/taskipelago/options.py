from dataclasses import dataclass
from typing import List

from Options import PerGameCommonOptions, DeathLink, OptionList


class Tasks(OptionList):
    display_name = "Tasks"
    default: List[str] = []


class Rewards(OptionList):
    display_name = "Rewards"
    default: List[str] = []


class DeathLinkPool(OptionList):
    display_name = "DeathLink Task Pool"
    default: List[str] = []


@dataclass
class TaskipelagoOptions(PerGameCommonOptions):
    death_link: DeathLink
    tasks: Tasks
    rewards: Rewards
    death_link_pool: DeathLinkPool
