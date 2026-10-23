"""Rollback failed in-memory research transitions; no native world authority."""
from copy import deepcopy
from functools import wraps


def rollback_on_error(function):
    @wraps(function)
    def transition(state, *args, **kwargs):
        before = deepcopy(state)
        try:
            return function(state, *args, **kwargs)
        except Exception:
            state.clear()
            state.update(before)
            raise
    return transition
