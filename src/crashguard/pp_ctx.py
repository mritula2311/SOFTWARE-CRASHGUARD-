"""Context of the NHTSA studies: pooled records, folds, labels and the per-cell feature frames (``pp_pool``, ``pp_feat``)."""
from __future__ import annotations

import numpy as np

from crashguard import pp_feat as PF
from crashguard import pp_pool as PP
from crashguard.pp_common import MODES, cls_of


class Ctx:
    def __init__(self):
        d = PP.load()
        self.T = PP.table(d)
        self.fold = d["fold"]
        self.dev, self.val, self.test = (self.fold == f for f in ("dev", "val", "test"))
        self.ref = self.T.ref.to_numpy(float)
        self.y = cls_of(self.ref)
        self.group = self.T.group.to_numpy()
        self.mode = self.T["mode"].to_numpy()
        self.mode_idx = np.array([MODES.index(m) for m in self.mode])
        self.v = self.T.v.to_numpy(float)
        self.F = PF.build()

    def cell(self, rg: float, fs: int):
        return self.F[(rg, fs)]
