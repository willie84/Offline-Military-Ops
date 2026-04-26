"""OffGrid Ops — offline AI assistant for service members in DDIL environments.

Run `python cli.py --help` to see all commands.
"""

from __future__ import annotations

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


if __name__ == "__main__":
    app()