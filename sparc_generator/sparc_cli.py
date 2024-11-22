#!/usr/bin/env python3
"""SPARC Framework CLI interface."""
import click
import asyncio
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import logging
from typing import Dict, Any, Optional

from sparc_generator.core import (
    SPARCPromptGenerator, 
    validate_model_config, 
    MODEL_CONFIGS
)

# Initialize rich console
console = Console()

def load_config() -> Dict[str, Any]:
    """
    Load configuration from .env file.
    
    Returns:
        Dict containing configuration values
    """
    load_dotenv()
    
    # Get required configurations
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file")
    
    # Get model configuration
    model = os.getenv("MODEL", "gpt-4o")
    
    try:
        # Validate model configuration
        model_config = validate_model_config(model)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        raise
    
    return {
        "api_key": api_key,
        "model": model,
        "model_config": model_config,
        "output_dir": os.getenv("OUTPUT_DIR", "output")
    }

def display_model_info(model: str, config: Dict[str, Any]):
    """Display model configuration information."""
    table = Table(title="Model Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Model", model)
    table.add_row("Max Tokens", str(config["max_tokens"]))
    table.add_row("Context Length", str(config["context_length"]))
    table.add_row("Temperature", str(config["temperature"]))
    
    console.print(table)

@click.group()
def cli():
    """SPARC Framework Prompt Generator CLI"""
    pass

@cli.command()
@click.argument('transcript_file', type=click.Path(exists=True))
@click.option('--output', '-o', default=None, help='Output directory for generated files')
@click.option('--project-name', '-n', default=None, help='Project name for organization')
@click.option('--simulate-chat', is_flag=True, help='Simulate chat-based development after generation')
@click.option('--model', '-m', help='Override model specified in .env')
def generate(transcript_file, output, project_name, simulate_chat, model):
    """Generate development plan from transcript."""
    asyncio.run(_generate(transcript_file, output, project_name, simulate_chat, model))

async def _generate(transcript_file: str, output: Optional[str], project_name: Optional[str], 
                   simulate_chat: bool, model_override: Optional[str]):
    """Async logic for the generate command."""
    try:
        # Load configuration
        config = load_config()
        
        # Override model if specified
        if model_override:
            config["model"] = model_override
            config["model_config"] = validate_model_config(model_override)

        # Display configuration
        console.print("\n[bold cyan]Configuration[/bold cyan]")
        display_model_info(config["model"], config["model_config"])

        if not project_name:
            project_name = f"sparc_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        output_dir = Path(output or config["output_dir"]) / project_name

        generator = SPARCPromptGenerator(
            api_key=config["api_key"],
            model=config["model"],
            model_config=config["model_config"]
        )

        # Read transcript
        with console.status("[bold green]Reading transcript..."):
            try:
                with open(transcript_file) as f:
                    transcript = f.read()
            except Exception as e:
                console.print(f"[bold red]Error reading transcript file: {e}[/bold red]")
                return

        # Process transcript with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Analyze Transcript
            task1 = progress.add_task("[cyan]Analyzing transcript...", total=1)
            analysis = await generator.analyze_transcript(transcript)
            if "error" in analysis:
                progress.update(task1, description="[bold red]Analysis Failed[/bold red]", completed=1)
                console.print(f"[bold red]Error in analysis: {analysis['error']}[/bold red]")
                if "raw_response" in analysis:
                    console.print(f"[italic red]Raw Response:[/italic red] {analysis['raw_response']}")
                return
            progress.update(task1, completed=1)

            # Generate SPARC Artifacts
            task2 = progress.add_task("[green]Generating SPARC artifacts...", total=1)
            artifacts = await generator.generate_sparc_artifacts(analysis)
            progress.update(task2, completed=1)

            # Validate Artifacts
            task3 = progress.add_task("[yellow]Validating outputs...", total=1)
            validation = await generator.validate_artifacts(artifacts, analysis)
            if "error" in validation:
                progress.update(task3, description="[bold red]Validation Failed[/bold red]", completed=1)
                console.print(f"[bold red]Error in validation: {validation['error']}[/bold red]")
                if "raw_response" in validation:
                    console.print(f"[italic red]Raw Response:[/italic red] {validation['raw_response']}")
                return
            progress.update(task3, completed=1)

        # Compile plan
        plan = {
            "project_name": project_name,
            "timestamp": datetime.now().isoformat(),
            "model_info": {
                "model": config["model"],
                "config": config["model_config"]
            },
            "analysis": analysis,
            "artifacts": artifacts,
            "validation": validation
        }

        # Save results
        with console.status("[bold green]Saving results..."):
            try:
                generator.save_development_plan(plan, output_dir)
            except Exception as e:
                console.print(f"[bold red]Error saving development plan: {e}[/bold red]")
                logging.error(f"Error saving development plan: {e}")
                return

        # Show summary
        rprint("\n[bold green]Development plan generated successfully![/bold green]\n")

        rprint(Panel.fit(
            f"""[bold]Project Summary[/bold]
            
Project Name: {project_name}
Output Directory: {output_dir}
Model: {config['model']}
Components Generated: {len(artifacts)}
Implementation Ready: {validation.get('overall_assessment', {}).get('ready_for_implementation', False)}

[bold]Next Steps:[/bold]
1. Review generated artifacts in {output_dir}/artifacts
2. Address any gaps identified in validation
3. Begin implementation following the development plan
""",
            title="SPARC Generator Results",
            border_style="green"
        ))

        # Show Critical Gaps
        critical_gaps = validation.get('overall_assessment', {}).get('critical_gaps', [])
        if critical_gaps:
            rprint("\n[bold red]Critical Gaps Identified:[/bold red]")
            for gap in critical_gaps:
                rprint(f"• {gap}")

        # Show API Usage
        usage_report = generator.generate_usage_report()
        rprint(Panel.fit(
            usage_report,
            title="API Usage Summary",
            border_style="blue"
        ))

        # Handle Chat Simulation
        if simulate_chat:
            if validation.get("overall_assessment", {}).get("ready_for_implementation", False):
                console.print("[bold blue]Starting chat-based simulation...[/bold blue]")
                conversation = await generator.chat_simulation(plan["artifacts"])

                # Save conversation
                chat_output_path = output_dir / "chat_simulation.txt"
                try:
                    with open(chat_output_path, "w") as f:
                        f.write(conversation)
                    rprint(f"[bold green]Chat simulation saved to {chat_output_path}[/bold green]")
                except Exception as e:
                    console.print(f"[bold red]Error saving chat simulation: {e}[/bold red]")
                    logging.error(f"Error saving chat simulation: {e}")
            else:
                console.print("[bold yellow]Chat simulation skipped due to validation issues.[/bold yellow]")

    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        logging.error(f"Error in generate command: {str(e)}")
        raise

@cli.command()
def list_models():
    """List available models and their configurations."""
    try:
        config = load_config()
        
        table = Table(title="Available Models")
        table.add_column("Model", style="cyan")
        table.add_column("Max Tokens", style="green")
        table.add_column("Context Length", style="blue")
        table.add_column("Temperature", style="yellow")
        
        for model, cfg in sorted(MODEL_CONFIGS.items()):
            table.add_row(
                model,
                str(cfg["max_tokens"]),
                str(cfg["context_length"]),
                str(cfg["temperature"])
            )
        
        console.print("\n[bold]Currently configured model:[/bold]")
        display_model_info(config["model"], config["model_config"])
        
        console.print("\n[bold]Available models:[/bold]")
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")

if __name__ == '__main__':
    cli()