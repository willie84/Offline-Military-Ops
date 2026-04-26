"""OffGrid Ops — offline AI assistant for service members in DDIL environments.

Run `python cli.py --help` to see all commands.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.markdown import Markdown

from src.rag.retriever import Retriever
from src.rag.generator import answer as generate_answer

ROOT = Path(__file__).resolve().parent
from rich.live import Live
app = typer.Typer(
    name="oo",
    help="OffGrid Ops — offline AI for the field.",
    no_args_is_help=True,
)
console = Console()


def banner():
    """Print the branded header. Looks great on a projector."""
    console.print(Panel.fit(
        "[bold cyan]OffGrid Ops[/bold cyan]  [dim]· offline AI for the field[/dim]\n"
        "[dim]GenAI.mil track · SCSP Hackathon 2026[/dim]",
        border_style="cyan",
    ))


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask the regulations."),
    k: int = typer.Option(4, "--k", help="Number of chunks to retrieve."),
):
    """Ask a question about Army regulations. Returns a cited answer."""
    banner()
    console.print(f"\n[bold]Q:[/bold] {question}\n")

    with console.status("[cyan]Searching regulations...", spinner="dots"):
        retriever = Retriever()
        chunks = retriever.search(question, k=k)

    if not chunks:
        console.print("[red]No relevant regulations found.[/red]")
        raise typer.Exit(1)

    # Show retrieved sources
    table = Table(title="Retrieved sources", show_header=True, header_style="bold magenta")
    table.add_column("Citation", style="cyan")
    table.add_column("Distance", justify="right", style="dim")
    for c in chunks:
        table.add_row(c.citation, f"{c.distance:.3f}")
    console.print(table)

    # Generate answer
    with console.status("[cyan]Generating answer...", spinner="dots"):
        response = generate_answer(question, chunks)

    console.print(Panel(
        Markdown(response),
        title="[bold green]Answer[/bold green]",
        border_style="green",
    ))


@app.command()
def leave():
    """Interactive flow: collect leave details, fill DA-31, queue in outbox."""
    banner()
    console.print("\n[bold cyan]DA Form 31 — Request and Authority for Leave[/bold cyan]\n")
    console.print("[dim]Answer in plain language. Type 'quit' to abort.[/dim]\n")

    request = typer.prompt(
        "Describe your leave request (e.g. '10 days starting June 3, visiting family in Texas')"
    )
    if request.lower() in ("quit", "exit", "q"):
        raise typer.Exit()

    # TODO: wire to form-fill pipeline (next step)
    console.print(f"\n[yellow]→ Will extract structured fields from:[/yellow] {request}")
    console.print("[dim](form-fill pipeline coming next)[/dim]")


@app.command()
def outbox():
    """Show forms queued in the local outbox waiting to sync."""
    banner()
    console.print("\n[bold]Outbox[/bold]\n")
    # TODO: wire to outbox module
    console.print("[dim](outbox coming next)[/dim]")


@app.command()
def sync():
    """Sync the outbox — the airplane-mode-off moment."""
    banner()
    # TODO: wire to sync engine
    console.print("\n[yellow]Checking connectivity...[/yellow]")
    console.print("[dim](sync coming next)[/dim]")


@app.command()
def status():
    """Show connectivity status, model health, queue depth."""
    banner()
    console.print()
    table = Table(show_header=False)
    table.add_column("", style="bold")
    table.add_column("")
    table.add_row("Mode", "[green]OFFLINE[/green]")
    table.add_row("LLM", "llama3.1:8b (local)")
    table.add_row("Embedder", "nomic-embed-text (local)")
    table.add_row("Knowledge base", "AR 600-8-10, AR 350-1, AR 670-1")
    table.add_row("Outbox", "0 forms queued")
    console.print(table)
@app.command()
def leave(
    request: str = typer.Option(
        None, "--request", "-r",
        help="Leave request in plain language."
    ),
    name: str = typer.Option("MACHARIA, WILLIE A.", "--name"),
    rank: str = typer.Option("SPC", "--rank"),
    unit: str = typer.Option("B Co, 1-1 IN, Fort Liberty / 910-555-0100", "--unit"),
):
    """Generate a DA-31 leave request from natural language."""
    from src.forms.extractor import extract
    from src.forms.renderer import render

    banner()

    if request is None:
        console.print("\n[bold cyan]DA Form 31 — Request and Authority for Leave[/bold cyan]\n")
        request = typer.prompt("Describe your leave request")

    if not request.strip():
        console.print("[red]Empty request, aborting.[/red]")
        raise typer.Exit(1)

    soldier_defaults = {"name": name, "rank": rank, "org_station": unit}

    with console.status("[cyan]Extracting fields from request...", spinner="dots"):
        try:
            leave_request = extract(request, soldier_defaults=soldier_defaults)
        except ValueError as e:
            console.print(f"[red]Extraction failed:[/red]\n{e}")
            raise typer.Exit(1)

    table = Table(title="Extracted fields", show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    for field, value in leave_request.model_dump().items():
        table.add_row(field, str(value))
    console.print(table)

    if not typer.confirm("\nLooks correct? Generate the form?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        raise typer.Exit()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = ROOT / "output" / f"DA31_{timestamp}.pdf"
    with console.status("[cyan]Rendering DA-31 PDF...", spinner="dots"):
        render(leave_request.to_form_dict(), output_path)

    # Queue in outbox
    from src.outbox import db
    priority = db.Priority.URGENT if leave_request.leave_type == "EMERGENCY" else db.Priority.ROUTINE
    summary = (
        f"{leave_request.name} · {leave_request.days_requested}d "
        f"{leave_request.leave_type} leave · "
        f"{leave_request.date_from} to {leave_request.date_to}"
    )
    item_id = db.enqueue(
        form_type="DA-31",
        file_path=str(output_path),
        summary=summary,
        priority=priority,
    )
    console.print(Panel(
        f"[bold green]✓ Form generated and queued[/bold green]\n\n"
        f"[dim]File:[/dim] {output_path}\n"
        f"[dim]Outbox ID:[/dim] {item_id}  [dim](priority: {priority.value})[/dim]\n\n"
        f"[dim]Run `oo outbox` to view queue, `oo sync` when reconnected.[/dim]",
        title="DA-31 ready",
        border_style="green",
    ))
@app.command()
def outbox():
    """Show forms queued in the local outbox."""
    from src.outbox import db
    from src.outbox.connectivity import is_online

    banner()

    online = is_online()
    state = "[green]ONLINE[/green]" if online else "[red]OFFLINE[/red]"
    console.print(f"\nConnectivity: {state}\n")

    items = db.list_all()
    if not items:
        console.print("[dim]Outbox is empty.[/dim]")
        return

    table = Table(title="Outbox", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Form", style="cyan")
    table.add_column("Priority")
    table.add_column("Status")
    table.add_column("Summary")
    table.add_column("Created", style="dim")

    for item in items:
        priority_color = {
            db.Priority.URGENT: "[red]URGENT[/red]",
            db.Priority.ROUTINE: "[yellow]ROUTINE[/yellow]",
            db.Priority.LOW: "[dim]LOW[/dim]",
        }[item.priority]
        status_color = {
            db.Status.PENDING: "[yellow]PENDING[/yellow]",
            db.Status.SENT: "[green]SENT[/green]",
            db.Status.FAILED: "[red]FAILED[/red]",
        }[item.status]
        table.add_row(
            str(item.id),
            item.form_type,
            priority_color,
            status_color,
            item.summary,
            item.created_at.strftime("%H:%M:%S"),
        )
    console.print(table)


@app.command()
def sync():
    """Sync the outbox to the S-1 inbox. Requires connectivity."""
    from src.outbox import db, sync as sync_engine
    from src.outbox.connectivity import is_online

    banner()

    if not is_online():
        console.print("\n[red]✗ OFFLINE — cannot sync.[/red]")
        console.print("[dim]Run `oo online` first to simulate reconnection.[/dim]\n")
        raise typer.Exit(1)

    pending = db.list_pending()
    if not pending:
        console.print("\n[dim]Nothing to sync. Outbox is empty.[/dim]")
        return

    console.print(f"\n[cyan]Connection re-established. Draining {len(pending)} item(s)...[/cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Form", style="cyan")
    table.add_column("Priority")
    table.add_column("Status")

    sent_count = 0
    try:
        with Live(table, console=console, refresh_per_second=10) as live:
            for item in sync_engine.sync_all():
                priority_color = {
                    db.Priority.URGENT: "[red]URGENT[/red]",
                    db.Priority.ROUTINE: "[yellow]ROUTINE[/yellow]",
                    db.Priority.LOW: "[dim]LOW[/dim]",
                }[item.priority]
                table.add_row(
                    item.form_type,
                    priority_color,
                    "[green]✓ DELIVERED[/green]",
                )
                sent_count += 1
                live.refresh()
    except sync_engine.SyncError as e:
        console.print(f"[red]Sync failed:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold green]✓ {sent_count} form(s) delivered to S-1 inbox[/bold green]\n\n"
        f"[dim]Inbox path:[/dim] data/s1_inbox/",
        title="Sync complete",
        border_style="green",
    ))


@app.command()
def offline():
    """Simulate disconnecting from the network."""
    from src.outbox.connectivity import go_offline
    go_offline()
    console.print("[red]✗ OFFLINE[/red] — operating in disconnected mode.")


@app.command()
def online():
    """Simulate reconnecting to the network."""
    from src.outbox.connectivity import go_online
    go_online()
    console.print("[green]✓ ONLINE[/green] — connection restored.")


@app.command()
def status():
    """Show connectivity, model health, and queue depth."""
    from src.outbox import db
    from src.outbox.connectivity import is_online

    banner()
    console.print()

    pending_count = len(db.list_pending())
    online = is_online()

    table = Table(show_header=False)
    table.add_column("", style="bold")
    table.add_column("")
    table.add_row("Connectivity", "[green]ONLINE[/green]" if online else "[red]OFFLINE[/red]")
    table.add_row("LLM", "llama3.1:8b (local)")
    table.add_row("Embedder", "nomic-embed-text (local)")
    table.add_row("Knowledge base", "AR 600-8-10, AR 350-1, AR 670-1 (784 chunks)")
    table.add_row("Outbox", f"{pending_count} form(s) pending" if pending_count else "empty")
    console.print(table)

if __name__ == "__main__":
    app()