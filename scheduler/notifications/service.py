"""Event-level notification helpers."""

import scheduler.notifications.messages as messages
from scheduler.notifications.telegram import send_message


def notify_taf_changed(
    slug: str,
    old_tx,
    new_tx,
    old_tn,
    new_tn,
    old_bin: str | None,
    new_bin: str | None,
) -> None:
    send_message(messages.taf_changed(
        slug,
        old_tx,
        new_tx,
        old_tn,
        new_tn,
        old_bin,
        new_bin,
    ))


def notify_order_result(
    slug: str,
    status: str,
    bin_label: str,
    estimate,
    yes_price,
) -> None:
    send_message(messages.order_result(
        slug,
        status,
        bin_label,
        estimate,
        yes_price,
    ))


def notify_rebalance(
    slug: str,
    old_bin: str,
    new_bin: str,
    status: str,
    reason: str,
) -> None:
    send_message(messages.rebalance(
        slug,
        old_bin,
        new_bin,
        status,
        reason,
    ))


def notify_resolved(
    slug: str | None,
    market_id: str,
    bin_label: str,
    outcome: str,
    status: str,
    pnl,
) -> None:
    send_message(messages.resolved(
        slug,
        market_id,
        bin_label,
        outcome,
        status,
        pnl,
    ))
