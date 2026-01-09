from __future__ import annotations

from ..state import GameState, LOAN_CHUNK


def take_loan(state: GameState) -> tuple[bool, str]:
    if state.loan_balance >= state.loan_limit:
        return False, "Loan limit reached."
    amount = min(LOAN_CHUNK, state.loan_limit - state.loan_balance)
    state.cash += amount
    state.loan_balance += amount
    return True, f"Took a loan for ${amount}."


def repay_loan(state: GameState) -> tuple[bool, str]:
    if state.loan_balance <= 0:
        return False, "No loan balance."
    amount = min(LOAN_CHUNK, state.loan_balance)
    if state.cash < amount:
        return False, "Insufficient cash to repay loan."
    state.cash -= amount
    state.loan_balance -= amount
    return True, f"Repaid ${amount} of loans."
