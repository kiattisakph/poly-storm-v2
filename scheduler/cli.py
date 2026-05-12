"""CLI contract for the scheduler package."""

import argparse
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from scheduler.app import build_scheduler, run_cycle, run_resolve

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="STORM v2 scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run one normal scheduler cycle and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="with --once, treat the cycle as TAF-triggered",
    )
    parser.add_argument(
        "--resolve-once",
        action="store_true",
        help="run resolver once and exit",
    )
    parser.add_argument(
        "--list-jobs",
        action="store_true",
        help="print configured job ids and exit",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_arg_parser().parse_args(argv)


def run_cli_command(args: argparse.Namespace) -> int:
    """Dispatch one CLI command. This is the scheduler entrypoint contract."""
    if args.once:
        return _run_once(args.force)

    if args.resolve_once:
        return _run_resolver_once()

    scheduler = build_scheduler()

    if args.list_jobs:
        return _print_jobs(scheduler)

    return _start_scheduler(scheduler)


def _run_once(force: bool) -> int:
    run_cycle(force=force)
    return 0


def _run_resolver_once() -> int:
    run_resolve()
    return 0


def _print_jobs(scheduler: BlockingScheduler) -> int:
    for job in scheduler.get_jobs():
        print(f"{job.id}: {job.trigger}")
    return 0


def _start_scheduler(scheduler: BlockingScheduler) -> int:
    logger.info("STORM v2 starting...")
    scheduler.start()
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_cli_command(parse_args(argv))
