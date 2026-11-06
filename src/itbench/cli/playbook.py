"""Run Ansible playbook steps from CLI commands."""

from contextlib import nullcontext
from typing import Any

from rich.markup import escape

from itbench.cli.render import console, err_console, fail
from itbench.utils.runner import PlaybookError, run_playbook


def run_step(
    *,
    playbook: str,
    extra_vars: dict[str, Any],
    tags: list[str],
    status: str,
    failure: str,
    verbose: bool,
    run_id: str | None = None,
) -> None:
    """Run one playbook and exit with status 1 if it fails.

    By default the Ansible output is hidden behind a spinner labelled *status*. With *verbose* the
    spinner is replaced by a plain line and the Ansible output is streamed. When the playbook fails
    the captured output is always printed to stderr, followed by *failure*.
    """
    if verbose:
        console.print(f"[dim]{escape(status)}[/dim]")
    spinner = nullcontext() if verbose else console.status(status)

    try:
        with spinner:
            run_playbook(playbook=playbook, extra_vars=extra_vars, tags=tags, run_id=run_id, verbose=verbose)
    except PlaybookError as exc:
        if exc.output:
            err_console.print(exc.output, markup=False, highlight=False, soft_wrap=True)
        fail(f"[red]{escape(failure)} failed:[/red] {escape(str(exc))}")
