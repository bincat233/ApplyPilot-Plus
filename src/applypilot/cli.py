"""ApplyPilot CLI — the main entry point."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from applypilot import __version__


def _parse_log_level(value: str) -> int:
    level = getattr(logging, value.upper(), None)
    if not isinstance(level, int):
        raise typer.BadParameter("Choose one of: debug, info, warning, error, critical.")
    return level


def _configure_logging(
    level: str = "INFO",
    http_level: str = "WARNING",
    log_file: Path | None = None,
) -> None:
    """Set consistent logging output for CLI runs."""
    root_level = _parse_log_level(level)
    noisy_level = _parse_log_level(http_level)
    logging.basicConfig(
        level=root_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(root_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(file_handler)

    # Keep SDK/network internals quiet by default; make them opt-in via
    # --http-log-level debug/info when needed.
    for name in ("LiteLLM", "litellm", "httpx", "httpcore", "openai"):
        noisy = logging.getLogger(name)
        noisy.setLevel(noisy_level)
        noisy.propagate = True

_configure_logging()

app = typer.Typer(
    name="applypilot",
    help="AI-powered end-to-end job application pipeline.",
    no_args_is_help=True,
)
console = Console()
log = logging.getLogger(__name__)

# Valid pipeline stages (in execution order)
VALID_STAGES = ("discover", "enrich", "score", "tailor", "cover", "pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bootstrap() -> None:
    """Common setup: load env, create dirs, init DB."""
    from applypilot.config import load_env, ensure_dirs
    from applypilot.database import init_db

    load_env()
    ensure_dirs()
    init_db()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold]applypilot[/bold] {__version__}")
        raise typer.Exit()


def _build_stage_progress_rows(stats: dict) -> list[tuple[str, int, int, int]]:
    """Build stage-oriented (total, pending, completed) rows for status output."""
    enrich_pending = stats["pending_detail"]
    enrich_total = stats["total"]
    enrich_completed = max(enrich_total - enrich_pending, 0)

    score_pending = stats["unscored"]
    score_completed = stats["scored"]
    score_total = score_pending + score_completed

    tailor_pending = stats["untailored_eligible"]
    tailor_completed = stats["tailored"]
    tailor_total = tailor_pending + tailor_completed

    cover_pending = max(tailor_completed - stats["with_cover_letter"], 0)
    cover_completed = stats["with_cover_letter"]
    cover_total = cover_pending + cover_completed

    pdf_pending = max(tailor_completed - stats["ready_to_apply"], 0)
    pdf_completed = stats["ready_to_apply"]
    pdf_total = pdf_pending + pdf_completed

    apply_pending = max(stats["ready_to_apply"] - stats["applied"], 0)
    apply_completed = stats["applied"]
    apply_total = apply_pending + apply_completed

    return [
        ("Enrichment", enrich_total, enrich_pending, enrich_completed),
        ("Scoring", score_total, score_pending, score_completed),
        ("Tailoring (7+)", tailor_total, tailor_pending, tailor_completed),
        ("Cover Letters", cover_total, cover_pending, cover_completed),
        ("PDF Conversion", pdf_total, pdf_pending, pdf_completed),
        ("Applications", apply_total, apply_pending, apply_completed),
    ]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Application log level: debug, info, warning, error, critical.",
    ),
    http_log_level: str = typer.Option(
        "warning",
        "--http-log-level",
        help="HTTP/SDK log level: debug, info, warning, error, critical.",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Optional file to mirror logs to.",
    ),
) -> None:
    """ApplyPilot — AI-powered end-to-end job application pipeline."""
    _configure_logging(level=log_level, http_level=http_log_level, log_file=log_file)


@app.command()
def init() -> None:
    """Run the first-time setup wizard (profile, resume, search config)."""
    from applypilot.wizard.init import run_wizard

    run_wizard()


@app.command()
def run(
    stages: Optional[list[str]] = typer.Argument(
        None,
        help=(
            "Pipeline stages to run. "
            f"Valid: {', '.join(VALID_STAGES)}, all. "
            "Defaults to 'all' if omitted."
        ),
    ),
    min_score: int = typer.Option(7, "--min-score", help="Minimum fit score for tailor/cover stages."),
    workers: int = typer.Option(1, "--workers", "-w", help="Parallel threads for discovery/enrichment stages."),
    stream: bool = typer.Option(False, "--stream", help="Run stages concurrently (streaming mode)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview stages without executing."),
    show_browser: bool = typer.Option(False, "--show-browser", help="Show browser window during enrichment."),
    reset_enrich_errors: bool = typer.Option(False, "--reset-enrich-errors", help="Clear enrichment errors so failed jobs are retried."),
    site_filter: Optional[list[str]] = typer.Option(
        None,
        "--site-filter",
        help="Limit discovery to matching sites from sites.yaml (repeat flag for multiple).",
    ),
    validation: str = typer.Option(
        "normal",
        "--validation",
        help=(
            "Validation strictness for tailor/cover stages. "
            "strict: banned words = errors, judge must pass. "
            "normal: banned words = warnings only (default, recommended for Gemini free tier). "
            "lenient: banned words ignored, LLM judge skipped (fastest, fewest API calls)."
        ),
    ),
) -> None:
    """Run pipeline stages: discover, enrich, score, tailor, cover, pdf."""
    _bootstrap()

    from applypilot.pipeline import run_pipeline

    stage_list = stages if stages else ["all"]

    # Validate stage names
    for s in stage_list:
        if s != "all" and s not in VALID_STAGES:
            console.print(
                f"[red]Unknown stage:[/red] '{s}'. "
                f"Valid stages: {', '.join(VALID_STAGES)}, all"
            )
            raise typer.Exit(code=1)

    if reset_enrich_errors:
        from applypilot.database import get_connection

        conn = get_connection()
        result_reset = conn.execute(
            "UPDATE jobs SET detail_scraped_at = NULL, detail_error = NULL "
            "WHERE detail_error IS NOT NULL"
        )
        conn.commit()
        console.print(f"[cyan]Reset {result_reset.rowcount} enrichment error job(s) for retry.[/cyan]")

    # Gate AI stages behind Tier 2
    llm_stages = {"score", "tailor", "cover"}
    if any(s in stage_list for s in llm_stages) or "all" in stage_list:
        from applypilot.config import check_tier
        check_tier(2, "AI scoring/tailoring")

    # Validate the --validation flag value
    valid_modes = ("strict", "normal", "lenient")
    if validation not in valid_modes:
        console.print(
            f"[red]Invalid --validation value:[/red] '{validation}'. "
            f"Choose from: {', '.join(valid_modes)}"
        )
        raise typer.Exit(code=1)

    result = run_pipeline(
        stages=stage_list,
        min_score=min_score,
        dry_run=dry_run,
        stream=stream,
        workers=workers,
        headless=not show_browser,
        site_filter=site_filter,
        validation_mode=validation,
    )

    if result.get("errors"):
        raise typer.Exit(code=1)


@app.command()
def add_url(
    url: str = typer.Argument(..., help="Job URL to insert or update."),
    title: str = typer.Option("Manual Add", "--title", help="Job title."),
    site: str = typer.Option("Manual", "--site", help="Source site label."),
    location: Optional[str] = typer.Option(None, "--location", help="Job location."),
    description: Optional[str] = typer.Option(None, "--description", help="Short description."),
    application_url: Optional[str] = typer.Option(None, "--application-url", help="Direct apply URL (defaults to URL)."),
    strategy: str = typer.Option("manual_url", "--strategy", help="Discovery strategy label."),
) -> None:
    """Insert or update a single job URL in the database."""
    _bootstrap()

    from datetime import datetime, timezone
    from applypilot.database import get_connection

    now = datetime.now(timezone.utc).isoformat()
    apply_url = application_url or url
    conn = get_connection()

    exists = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,)).fetchone() is not None

    if exists:
        conn.execute(
            """
            UPDATE jobs
            SET title = COALESCE(NULLIF(?, ''), title),
                site = COALESCE(NULLIF(?, ''), site),
                location = COALESCE(?, location),
                description = COALESCE(?, description),
                application_url = COALESCE(?, application_url),
                strategy = COALESCE(NULLIF(?, ''), strategy),
                discovered_at = COALESCE(discovered_at, ?)
            WHERE url = ?
            """,
            (title, site, location, description, apply_url, strategy, now, url),
        )
        action = "Updated"
    else:
        conn.execute(
            """
            INSERT INTO jobs (
                url, title, salary, description, location, site, strategy, discovered_at, application_url
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
            """,
            (url, title, description, location, site, strategy, now, apply_url),
        )
        action = "Added"

    conn.commit()
    console.print(f"[green]{action} job:[/green] {url}")
    console.print(f"  Site: {site} | Title: {title}")


@app.command()
def apply(
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max applications to submit."),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel browser workers."),
    min_score: int = typer.Option(7, "--min-score", help="Minimum fit score for job selection."),
    model: str = typer.Option("haiku", "--model", "-m", help="Claude model name."),
    continuous: bool = typer.Option(False, "--continuous", "-c", help="Run forever, polling for new jobs."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview actions without submitting."),
    headless: bool = typer.Option(False, "--headless", help="Run browsers in headless mode."),
    url: Optional[str] = typer.Option(None, "--url", help="Apply to a specific job URL."),
    gen: bool = typer.Option(False, "--gen", help="Generate prompt file for manual debugging instead of running."),
    mark_applied: Optional[str] = typer.Option(None, "--mark-applied", help="Manually mark a job URL as applied."),
    mark_failed: Optional[str] = typer.Option(None, "--mark-failed", help="Manually mark a job URL as failed (provide URL)."),
    fail_reason: Optional[str] = typer.Option(None, "--fail-reason", help="Reason for --mark-failed."),
    reset_failed: bool = typer.Option(False, "--reset-failed", help="Reset all failed jobs for retry."),
    remove_expired: bool = typer.Option(False, "--remove-expired", help="Remove expired jobs from the database."),
    reset_in_progress: bool = typer.Option(False, "--reset-in-progress", help="Clear stale in-progress apply locks."),
    kill_chrome: bool = typer.Option(False, "--kill-chrome", help="Kill tracked Chrome worker processes."),
) -> None:
    """Launch auto-apply to submit job applications."""
    _bootstrap()

    from applypilot.config import check_tier, PROFILE_PATH as _profile_path
    from applypilot.database import get_connection

    # --- Utility modes (no Chrome/Claude needed) ---

    if mark_applied:
        from applypilot.apply.launcher import mark_job
        mark_job(mark_applied, "applied")
        console.print(f"[green]Marked as applied:[/green] {mark_applied}")
        return

    if mark_failed:
        from applypilot.apply.launcher import mark_job
        mark_job(mark_failed, "failed", reason=fail_reason)
        console.print(f"[yellow]Marked as failed:[/yellow] {mark_failed} ({fail_reason or 'manual'})")
        return

    if reset_failed:
        from applypilot.apply.launcher import reset_failed as do_reset
        count = do_reset()
        console.print(f"[green]Reset {count} failed job(s) for retry.[/green]")
        return

    if remove_expired:
        from applypilot.apply.launcher import remove_expired as do_remove
        count = do_remove()
        console.print(f"[green]Removed {count} expired job(s).[/green]")
        return

    if reset_in_progress:
        from applypilot.apply.launcher import reset_in_progress as do_reset_in_progress
        count = do_reset_in_progress()
        console.print(f"[green]Reset {count} in-progress job(s).[/green]")
        return

    if kill_chrome:
        from applypilot.apply.chrome import kill_all_chrome

        kill_all_chrome()
        console.print("[green]Killed tracked Chrome worker process(es).[/green]")
        return

    # --- Full apply mode ---

    # Check 1: Tier 3 required (Claude Code CLI + Chrome)
    check_tier(3, "auto-apply")

    # Check 2: Profile exists
    if not _profile_path.exists():
        console.print(
            "[red]Profile not found.[/red]\n"
            "Run [bold]applypilot init[/bold] to create your profile first."
        )
        raise typer.Exit(code=1)

    # Check 3: Tailored resumes exist (skip for --gen with --url)
    if not (gen and url):
        conn = get_connection()
        ready = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL AND applied_at IS NULL"
        ).fetchone()[0]
        if ready == 0:
            console.print(
                "[red]No tailored resumes ready.[/red]\n"
                "Run [bold]applypilot run score tailor[/bold] first to prepare applications."
            )
            raise typer.Exit(code=1)

    if gen:
        from applypilot.apply.launcher import gen_prompt
        target = url or ""
        if not target:
            console.print("[red]--gen requires --url to specify which job.[/red]")
            raise typer.Exit(code=1)
        prompt_file = gen_prompt(target, min_score=min_score, model=model)
        if not prompt_file:
            console.print("[red]No matching job found for that URL.[/red]")
            raise typer.Exit(code=1)
        mcp_path = _profile_path.parent / ".mcp-apply-0.json"
        console.print(f"[green]Wrote prompt to:[/green] {prompt_file}")
        console.print("\n[bold]Run manually:[/bold]")
        console.print(
            f"  claude --model {model} -p "
            f"--mcp-config {mcp_path} "
            f"--permission-mode bypassPermissions < {prompt_file}"
        )
        return

    from applypilot.apply.launcher import main as apply_main

    effective_limit = limit if limit is not None else (0 if continuous else 1)

    console.print("\n[bold blue]Launching Auto-Apply[/bold blue]")
    console.print(f"  Limit:    {'unlimited' if continuous else effective_limit}")
    console.print(f"  Workers:  {workers}")
    console.print(f"  Model:    {model}")
    console.print(f"  Headless: {headless}")
    console.print(f"  Dry run:  {dry_run}")
    if url:
        console.print(f"  Target:   {url}")
    console.print()

    apply_main(
        limit=effective_limit,
        target_url=url,
        min_score=min_score,
        headless=headless,
        model=model,
        dry_run=dry_run,
        continuous=continuous,
        workers=workers,
    )


@app.command()
def status() -> None:
    """Show pipeline statistics from the database."""
    _bootstrap()

    from applypilot.database import get_stats

    stats = get_stats()

    console.print("\n[bold]ApplyPilot Pipeline Status[/bold]\n")

    # Summary table
    summary = Table(title="Pipeline Overview", show_header=True, header_style="bold cyan")
    summary.add_column("Metric", style="bold")
    summary.add_column("Count", justify="right")

    summary.add_row("Total jobs discovered", str(stats["total"]))
    summary.add_row("With full description", str(stats["with_description"]))
    summary.add_row("Pending enrichment", str(stats["pending_detail"]))
    summary.add_row("Enrichment errors", str(stats["detail_errors"]))
    summary.add_row("Scored by LLM", str(stats["scored"]))
    summary.add_row("Pending scoring", str(stats["unscored"]))
    summary.add_row("Tailored resumes", str(stats["tailored"]))
    summary.add_row("Pending tailoring (7+)", str(stats["untailored_eligible"]))
    summary.add_row("Cover letters", str(stats["with_cover_letter"]))
    summary.add_row("Ready to apply", str(stats["ready_to_apply"]))
    summary.add_row("Applied", str(stats["applied"]))
    summary.add_row("Apply errors", str(stats["apply_errors"]))

    console.print(summary)

    progress = Table(title="\nStage Progress", show_header=True, header_style="bold green")
    progress.add_column("Stage", style="bold")
    progress.add_column("Total", justify="right")
    progress.add_column("Pending", justify="right")
    progress.add_column("Completed", justify="right")

    for category, total, pending, completed in _build_stage_progress_rows(stats):
        progress.add_row(category, str(total), str(pending), str(completed))

    console.print(progress)

    # Score distribution
    if stats["score_distribution"]:
        dist_table = Table(title="\nScore Distribution", show_header=True, header_style="bold yellow")
        dist_table.add_column("Score", justify="center")
        dist_table.add_column("Count", justify="right")
        dist_table.add_column("Bar")

        max_count = max(count for _, count in stats["score_distribution"]) or 1
        for score, count in stats["score_distribution"]:
            bar_len = int(count / max_count * 30)
            if score >= 7:
                color = "green"
            elif score >= 5:
                color = "yellow"
            else:
                color = "red"
            bar = f"[{color}]{'=' * bar_len}[/{color}]"
            dist_table.add_row(str(score), str(count), bar)

        console.print(dist_table)

    # By site
    if stats["by_site"]:
        site_table = Table(title="\nJobs by Source", show_header=True, header_style="bold magenta")
        site_table.add_column("Site")
        site_table.add_column("Count", justify="right")

        for site, count in stats["by_site"]:
            site_table.add_row(site or "Unknown", str(count))

        console.print(site_table)

    console.print()


@app.command()
def dashboard() -> None:
    """Generate and open the HTML dashboard in your browser."""
    _bootstrap()

    from applypilot.view import open_dashboard

    open_dashboard()


@app.command()
def doctor() -> None:
    """Check your setup and diagnose missing requirements."""
    import shutil
    from applypilot.config import (
        load_env, PROFILE_PATH, RESUME_PATH, RESUME_PDF_PATH,
        SEARCH_CONFIG_PATH, get_chrome_path,
    )

    load_env()

    ok_mark = "[green]OK[/green]"
    fail_mark = "[red]MISSING[/red]"
    warn_mark = "[yellow]WARN[/yellow]"

    results: list[tuple[str, str, str]] = []  # (check, status, note)

    # --- Tier 1 checks ---
    # Profile
    if PROFILE_PATH.exists():
        results.append(("profile.json", ok_mark, str(PROFILE_PATH)))
    else:
        results.append(("profile.json", fail_mark, "Run 'applypilot init' to create"))

    # Resume
    if RESUME_PATH.exists():
        results.append(("resume.txt", ok_mark, str(RESUME_PATH)))
    elif RESUME_PDF_PATH.exists():
        results.append(("resume.txt", warn_mark, "Only PDF found - plain-text needed for AI stages"))
    else:
        results.append(("resume.txt", fail_mark, "Run 'applypilot init' to add your resume"))

    # Search config
    if SEARCH_CONFIG_PATH.exists():
        results.append(("searches.yaml", ok_mark, str(SEARCH_CONFIG_PATH)))
    else:
        results.append(("searches.yaml", warn_mark, "Will use example config - run 'applypilot init'"))

    # jobspy (discovery dep installed separately)
    try:
        import jobspy  # noqa: F401
        results.append(("python-jobspy", ok_mark, "Job board scraping available"))
    except ImportError:
        results.append(("python-jobspy", warn_mark,
                        "pip install --no-deps python-jobspy && pip install pydantic tls-client requests markdownify regex"))

    # --- Tier 2 checks ---
    from applypilot.llm import resolve_llm_config

    try:
        llm_cfg = resolve_llm_config()
        if llm_cfg.api_base:
            results.append(("LLM API key", ok_mark, f"Custom endpoint: {llm_cfg.api_base} ({llm_cfg.model})"))
        else:
            label = {
                "gemini": "Gemini",
                "openai": "OpenAI",
                "anthropic": "Anthropic",
            }.get(llm_cfg.provider, llm_cfg.provider)
            results.append(("LLM API key", ok_mark, f"{label} ({llm_cfg.model})"))
    except RuntimeError:
        results.append(
            ("LLM API key", fail_mark,
             "Set one of GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_URL, "
             "or set LLM_MODEL with LLM_API_KEY in ~/.applypilot/.env")
        )

    # --- Tier 3 checks ---
    # Claude Code CLI
    claude_bin = shutil.which("claude")
    if claude_bin:
        results.append(("Claude Code CLI", ok_mark, claude_bin))
    else:
        results.append(("Claude Code CLI", fail_mark,
                        "Install from https://claude.ai/code (needed for auto-apply)"))

    # Chrome
    try:
        chrome_path = get_chrome_path()
        results.append(("Chrome/Chromium", ok_mark, chrome_path))
    except FileNotFoundError:
        results.append(("Chrome/Chromium", fail_mark,
                        "Install Chrome or set CHROME_PATH env var (needed for auto-apply)"))

    # Node.js / npx (for Playwright MCP)
    npx_bin = shutil.which("npx")
    if npx_bin:
        results.append(("Node.js (npx)", ok_mark, npx_bin))
    else:
        results.append(("Node.js (npx)", fail_mark,
                        "Install Node.js 18+ from nodejs.org (needed for auto-apply)"))

    # CapSolver (optional)
    capsolver = os.environ.get("CAPSOLVER_API_KEY")
    if capsolver:
        results.append(("CapSolver API key", ok_mark, "CAPTCHA solving enabled"))
    else:
        results.append(("CapSolver API key", "[dim]optional[/dim]",
                        "Set CAPSOLVER_API_KEY in .env for CAPTCHA solving"))

    # --- Render results ---
    console.print()
    console.print("[bold]ApplyPilot Doctor[/bold]\n")

    col_w = max(len(r[0]) for r in results) + 2
    for check, status, note in results:
        pad = " " * (col_w - len(check))
        console.print(f"  {check}{pad}{status}  [dim]{note}[/dim]")

    console.print()

    # Tier summary
    from applypilot.config import get_tier, TIER_LABELS
    tier = get_tier()
    console.print(f"[bold]Current tier: Tier {tier} - {TIER_LABELS[tier]}[/bold]")

    if tier == 1:
        console.print("[dim]  -> Tier 2 unlocks: scoring, tailoring, cover letters (needs LLM API key)[/dim]")
        console.print("[dim]  -> Tier 3 unlocks: auto-apply (needs Claude Code CLI + Chrome + Node.js)[/dim]")
    elif tier == 2:
        console.print("[dim]  -> Tier 3 unlocks: auto-apply (needs Claude Code CLI + Chrome + Node.js)[/dim]")

    console.print()



# Import and add greenhouse subcommand
from applypilot.cli_greenhouse import app as greenhouse_app
app.add_typer(greenhouse_app, name="greenhouse", help="Manage Greenhouse ATS employers")

if __name__ == "__main__":
    app()
