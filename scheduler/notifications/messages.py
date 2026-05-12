"""Telegram message formatters."""

from html import escape


def _line(label: str, value) -> str:
    return f"{label}: {escape(str(value))}"


def _temp(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}°C"


def _price(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def _pnl(value) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.2f} USD"


def _header(slug: str | None, fallback: str | None = None) -> str:
    title = slug or fallback or "unknown-market"
    return f"<b>{escape(title)}</b>"


def taf_changed(
    slug: str,
    old_tx,
    new_tx,
    old_tn,
    new_tn,
    old_bin: str | None,
    new_bin: str | None,
) -> str:
    lines = [
        _header(slug),
        "",
        "<b>TAF Changed</b>",
        f"TX: {_temp(old_tx)} → {_temp(new_tx)}",
        f"TN: {_temp(old_tn)} → {_temp(new_tn)}",
    ]
    if old_bin and new_bin and old_bin != new_bin:
        lines.append(f"Target bin: {escape(old_bin)} → {escape(new_bin)}")
    elif new_bin:
        lines.append(_line("Target bin", new_bin))
    return "\n".join(lines)


def order_result(
    slug: str,
    status: str,
    bin_label: str,
    estimate,
    yes_price,
) -> str:
    return "\n".join([
        _header(slug),
        "",
        "<b>Order Result</b>",
        _line("Status", status),
        _line("Bin", bin_label),
        _line("Estimate", _temp(estimate)),
        _line("YES price", _price(yes_price)),
    ])


def rebalance(
    slug: str,
    old_bin: str,
    new_bin: str,
    status: str,
    reason: str,
) -> str:
    return "\n".join([
        _header(slug),
        "",
        "<b>Rebalance</b>",
        _line("Old bin", old_bin),
        _line("New bin", new_bin),
        _line("Status", status),
        _line("Reason", reason),
    ])


def resolved(
    slug: str | None,
    market_id: str,
    bin_label: str,
    outcome: str,
    status: str,
    pnl,
) -> str:
    return "\n".join([
        _header(slug, market_id),
        "",
        "<b>Resolved</b>",
        _line("Bin", bin_label),
        _line("Outcome", outcome),
        _line("Status", status),
        _line("PnL", _pnl(pnl)),
    ])
