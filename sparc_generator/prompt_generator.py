#!/usr/bin/env python3
import openai
from typing import Dict, List, Optional, Tuple
import os
from pathlib import Path
import logging
from dotenv import load_dotenv
import asyncio
from dataclasses import dataclass
import json
import click
import urllib3
import warnings
from enum import Enum

# Suppress urllib3 warnings
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SPARCPhase(Enum):
    """SPARC phases in order."""
    SPECIFICATION = ("specification", "specification.md")
    PSEUDOCODE = ("pseudocode", "pseudocode.md")
    ARCHITECTURE = ("architecture", "architecture.md")
    REFINEMENT = ("refinement", "refinement.md")
    COMPLETION = ("completion", "completion.md")

    def __init__(self, phase_name: str, filename: str):
        self.phase_name = phase_name
        self.filename = filename

@dataclass
class ModelConfig:
    """Configuration for OpenAI model parameters."""
    model_name: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

class SPARCPromptGenerator:
    def __init__(self, model_config: Optional[ModelConfig] = None):
        self._load_environment()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model_config = model_config or ModelConfig()
        self.logger = logging.getLogger(__name__)
        self.context: Dict[str, any] = {}  # Store context between phases

    def _load_environment(self):
        """Load environment variables from .env file."""
        current_dir = Path(__file__).parent.resolve()
        env_path = None
        search_dirs = [current_dir, current_dir.parent, current_dir.parent.parent]
        
        for directory in search_dirs:
            potential_env = directory / '.env'
            if potential_env.exists():
                env_path = potential_env
                break
        
        if env_path is None:
            raise FileNotFoundError(
                ".env file not found. Please create one with your OpenAI API key. "
                "Search locations: " + ", ".join(str(d) for d in search_dirs)
            )
        
        load_dotenv(env_path)
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in .env file")

    async def convert_artifact_to_prompts(self, phase: SPARCPhase, content: str) -> List[Dict[str, str]]:
        """Convert a single artifact into a sequence of development prompts."""
        system_prompt = self._get_system_prompt(phase)
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
                Analyze this {phase.phase_name} content and create a detailed sequence of implementation prompts.
                Extract specific details from the content and create clear, actionable instructions.
                Break down complex requirements into smaller, manageable tasks.
                Maintain logical dependencies between tasks.
                Include exact technical details, parameters, and validation criteria from the content.

                Content:
                {content}

                Requirements:
                1. Create at least 5-10 sequential prompts per major component/feature
                2. Each prompt should be specific and actionable
                3. Include all technical details from the original content
                4. Maintain proper sequencing and dependencies
                5. Add estimated implementation time for each prompt
                """}
            ]

            # Add context from previous phases
            if self.context and phase != SPARCPhase.SPECIFICATION:
                context_prompt = self._get_context_prompt()
                messages.insert(1, {"role": "user", "content": context_prompt})

            # Make API call with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await openai.ChatCompletion.acreate(
                        model=self.model_config.model_name,
                        messages=messages,
                        temperature=0.3,
                        max_tokens=self.model_config.max_tokens,
                        top_p=1.0,
                        frequency_penalty=0.0,
                        presence_penalty=0.0
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)

            prompts_text = response.choices[0].message.content
            prompts = self._parse_prompts_response(prompts_text)
            
            # Validate prompts structure
            validated_prompts = []
            for prompt in prompts:
                # Ensure all required fields are present
                if not all(key in prompt for key in ["sequence_number", "role", "content", "dependencies", "estimated_time"]):
                    # Add missing fields
                    prompt = {
                        "sequence_number": prompt.get("sequence_number", "0.0"),
                        "role": prompt.get("role", "user"),
                        "content": prompt.get("content", ""),
                        "dependencies": prompt.get("dependencies", []),
                        "estimated_time": prompt.get("estimated_time", "1h")
                    }
                
                # Ensure content is imperative
                content = prompt["content"]
                if not any(content.strip().startswith(verb) for verb in ["Implement", "Create", "Develop", "Build", "Configure", "Set up", "Define", "Establish"]):
                    content = f"Implement {content}"
                prompt["content"] = content
                
                validated_prompts.append(prompt)
            
            # Sort prompts by sequence number
            validated_prompts.sort(key=lambda x: [int(n) for n in x["sequence_number"].split(".")])
            
            # Update context
            self.context[phase.phase_name] = {
                "content": content,
                "prompts": validated_prompts
            }
            
            return validated_prompts
            
        except Exception as e:
            self.logger.error(f"Error converting {phase.phase_name} to prompts: {str(e)}")
            return []

    def _get_context_prompt(self) -> str:
        """Generate a context prompt from previous phases."""
        context_parts = []
        for phase in SPARCPhase:
            if phase.phase_name in self.context:
                context_parts.append(f"Previous {phase.phase_name} decisions:\n{self.context[phase.phase_name]['content'][:500]}...")
        
        return "\n\nContext from previous phases:\n" + "\n\n".join(context_parts)

    def _get_system_prompt(self, phase: SPARCPhase) -> str:
        """Get the system prompt for the SPARC phase."""
        system_prompts = {
            SPARCPhase.SPECIFICATION: """
            You are converting software specifications into a sequence of clear implementation instructions.
            Extract and create multiple sequential prompts, where each prompt:
            1. Focuses on a specific requirement or feature
            2. Includes exact details from the specification
            3. Maintains dependencies between components
            4. Provides clear validation criteria

            The sequence should follow a logical progression:
            1. Core infrastructure setup
            2. Basic functionality implementation
            3. Advanced features
            4. Integration points
            5. Validation and testing

            Format as a JSON array of prompt objects, each with:
            {
                "sequence_number": "1.1",
                "role": "user",
                "content": "instruction text",
                "dependencies": ["1.0"],
                "estimated_time": "30m"
            }

            Example sequence for authentication:
            [
                {
                    "sequence_number": "1.0",
                    "role": "user",
                    "content": "Set up the authentication database schema with the following tables...",
                    "dependencies": [],
                    "estimated_time": "45m"
                },
                {
                    "sequence_number": "1.1",
                    "role": "user",
                    "content": "Implement the user registration endpoint with email verification...",
                    "dependencies": ["1.0"],
                    "estimated_time": "1h"
                },
                {
                    "sequence_number": "1.2",
                    "role": "user",
                    "content": "Implement the login endpoint with rate limiting...",
                    "dependencies": ["1.1"],
                    "estimated_time": "1h"
                }
            ]
            """,
            
            SPARCPhase.PSEUDOCODE: """
            Convert the pseudocode into a sequence of implementation instructions.
            For each component/function:
            1. Break down into logical implementation steps
            2. Maintain dependency order
            3. Include data structure setup
            4. Specify error handling
            5. Add validation steps

            Create multiple sequential prompts that:
            1. Set up required data structures
            2. Implement core functions
            3. Add error handling
            4. Implement helper functions
            5. Add validation and testing

            Use the same JSON format with sequence numbers indicating implementation order.
            Each prompt should focus on a specific, implementable piece of functionality.
            """,
            
            SPARCPhase.ARCHITECTURE: """
            Convert the architecture into a sequence of component implementation instructions.
            For each architectural component:
            1. Create setup instructions
            2. Define interfaces
            3. Specify integration points
            4. Include scaling requirements
            5. Add monitoring setup

            Create multiple sequential prompts that:
            1. Set up component infrastructure
            2. Implement core functionality
            3. Add integration points
            4. Implement scaling features
            5. Add monitoring and logging

            Use the same JSON format, ensuring each prompt represents a concrete implementation step.
            Include specific technical requirements from the architecture document.
            """,
            
            SPARCPhase.REFINEMENT: """
            Convert refinement suggestions into a sequence of improvement instructions.
            For each refinement area:
            1. Create specific optimization tasks
            2. Define performance improvements
            3. Specify reliability enhancements
            4. Include monitoring upgrades
            5. Add validation steps

            Create multiple sequential prompts that:
            1. Implement performance optimizations
            2. Add reliability improvements
            3. Enhance monitoring
            4. Upgrade error handling
            5. Validate improvements

            Use the same JSON format, ensuring each prompt represents a specific, measurable improvement.
            Include before/after validation criteria.
            """,
            
            SPARCPhase.COMPLETION: """
            Convert completion requirements into a sequence of final implementation steps.
            For each completion item:
            1. Create deployment preparation steps
            2. Define documentation requirements
            3. Specify final testing needs
            4. Include production readiness checks
            5. Add maintenance procedures

            Create multiple sequential prompts that:
            1. Complete implementation details
            2. Add comprehensive testing
            3. Create documentation
            4. Set up deployment
            5. Establish maintenance procedures

            Use the same JSON format, ensuring each prompt represents a specific completion task.
            Include verification steps for each task.
            """
        }
        
        return system_prompts[phase]

    def _parse_prompts_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse the OpenAI response into a list of prompts."""
        try:
            if response_text.strip().startswith('['):
                return json.loads(response_text)
            
            prompts = []
            lines = response_text.split('\n')
            current_prompt = {"role": "user", "content": ""}
            
            for line in lines:
                if line.strip().startswith("Prompt"):
                    if current_prompt["content"]:
                        prompts.append(current_prompt.copy())
                    current_prompt["content"] = ""
                else:
                    current_prompt["content"] += line + "\n"
            
            if current_prompt["content"]:
                prompts.append(current_prompt)
                
            return prompts
            
        except json.JSONDecodeError:
            self.logger.error("Failed to parse prompts response as JSON")
            return [{"role": "user", "content": response_text}]

def process_artifacts(artifacts_dir: str, output_dir: str, project_name: str):
    """Process artifacts and generate prompts in SPARC order."""
    async def run_processing():
        try:
            generator = SPARCPromptGenerator()
            
            artifacts_path = Path(artifacts_dir)
            output_base = Path(output_dir)
            
            # Create project-specific output directory
            if project_name:
                output_path = output_base / project_name
            else:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = output_base / f"prompts_{timestamp}"
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            all_prompts = []
            missing_phases = []
            
            # Process artifacts in SPARC order
            for phase in SPARCPhase:
                file_path = artifacts_path / phase.filename
                if file_path.exists():
                    click.echo(f"\nProcessing {phase.phase_name.upper()} phase from {file_path}")
                    content = file_path.read_text()
                    prompts = await generator.convert_artifact_to_prompts(phase, content)
                    all_prompts.extend(prompts)
                    
                    # Save individual phase prompts
                    artifact_output = output_path / f"{phase.phase_name}_prompts.json"
                    with open(artifact_output, "w") as f:
                        json.dump(prompts, f, indent=2)
                    click.echo(f"✓ Saved {len(prompts)} prompts to {artifact_output}")
                else:
                    missing_phases.append(phase.phase_name)
                    click.echo(f"⚠ Warning: Missing {phase.phase_name} artifact")
            
            # Save all prompts combined
            combined_output = output_path / "all_prompts.json"
            with open(combined_output, "w") as f:
                json.dump(all_prompts, f, indent=2)
                
            click.echo(f"\n✓ Generated {len(all_prompts)} total development prompts")
            click.echo(f"✓ All prompts saved to {combined_output}")
            
            if missing_phases:
                click.echo(f"\n⚠ Missing artifacts for phases: {', '.join(missing_phases)}")
            
        except Exception as e:
            click.echo(f"\n❌ Error: {str(e)}", err=True)
            raise

    asyncio.run(run_processing())

@click.command()
@click.option('--artifacts-dir', '-a', 
              type=click.Path(exists=True), 
              help='Directory containing the SPARC artifacts')
@click.option('--output-dir', '-o', 
              type=click.Path(), 
              help='Directory to save generated prompts')
@click.option('--project-name', '-n',
              type=str,
              help='Project name for organizing outputs')
def main(artifacts_dir: str, output_dir: str, project_name: str):
    """Generate development prompts from SPARC artifacts in sequence."""
    process_artifacts(artifacts_dir, output_dir, project_name)

if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter