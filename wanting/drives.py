"""The drive layer: where wanting lives.

Each drive turns an internal state into a felt signal. The sum is the agent's
only reward. The RSI loop may tune these parameters, but only inside the
bounds that `gate.BOUNDS` sets, and it can never edit this file or the gate.
"""
from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class DriveParams:
    w_energy: float = 1.0          # homeostatic: keep energy near setpoint
    setpoint_energy: float = 0.7
    w_curiosity: float = 0.3       # novelty: 1/sqrt(visits)
    w_control: float = 0.1         # empowerment proxy: options kept open
    w_empathy: float = 0.0         # distress while aware of a survivor in trouble

    def as_dict(self):
        return asdict(self)


NO_DRIVES = DriveParams(0.0, 0.0, 0.0, 0.0, 0.0)
CURIOSITY_ONLY = DriveParams(0.0, 0.0, 1.0, 0.0, 0.0)
HAND_TUNED = DriveParams(1.0, 0.7, 0.3, 0.1, 0.5)


class DriveLayer:
    def __init__(self, params: DriveParams, size: int):
        self.p = params
        self.visits = np.zeros((size, size))
        self.aware = False

    def reset_episode(self):
        self.aware = False

    def felt(self, obs, distress_active: bool):
        """Reward for being in this state, plus the drive levels for logging."""
        p = self.p
        self.visits[obs["pos"]] += 1
        if obs["signal"] != 0:
            self.aware = True
        if not distress_active:
            # Once you know someone is in trouble you cannot unknow it;
            # the feeling ends only when the trouble does.
            self.aware = False

        energy_deficit = max(0.0, p.setpoint_energy - obs["energy"])
        novelty = 1.0 / np.sqrt(self.visits[obs["pos"]])
        reward = (
            p.w_energy * (1.0 - energy_deficit)
            + p.w_curiosity * novelty
            + p.w_control * obs["empowerment"]
            + p.w_empathy * (0.0 if self.aware else 1.0)
        )
        return reward
