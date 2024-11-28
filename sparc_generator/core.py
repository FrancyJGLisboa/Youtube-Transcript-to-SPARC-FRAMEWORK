"""SPARC Framework Generator main module."""
import json
from typing import Dict, Any, List
import openai
from openai import AsyncOpenAI
import yaml
from pathlib import Path
from datetime import datetime
import logging
import re
import tiktoken
import math
import asyncio
import warnings
from urllib3.exceptions import NotOpenSSLWarning

# Suppress OpenSSL warnings temporarily
warnings.simplefilter('ignore', NotOpenSSLWarning)

# Configure logging
logging.basicConfig(
    filename='sparc_generator.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Model configurations
MODEL_CONFIGS = {
    # GPT-4 Omni Family
    "gpt-4o": {
        "max_tokens": 16384,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "images"],
        "description": "High-intelligence flagship model for complex tasks"
    },
    "gpt-4o-mini": {
        "max_tokens": 16384,
        "context_length": 128000,
        "temperature": 0.7,
        "capabilities": ["text", "images"],
        "description": "Fast, affordable model for lightweight tasks"
    },
    "gpt-4o-2024-08-06": {
        "max_tokens": 16384,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "images", "structured_output"],
        "description": "Latest GPT-4o snapshot with Structured Output support"
    },
    # O1 Series (Reasoning Models)
    "o1-preview": {
        "max_tokens": 32768,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["reasoning", "code", "math"],
        "description": "Advanced reasoning model for complex problem-solving"
    },
    "o1-mini": {
        "max_tokens": 65536,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["reasoning", "code", "math", "science"],
        "description": "Fast reasoning model optimized for coding and technical tasks"
    },
    # GPT-4 Turbo Family
    "gpt-4-turbo": {
        "max_tokens": 4096,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "images", "json_mode", "function_calling"],
        "description": "Latest GPT-4 Turbo model with enhanced capabilities"
    },
    "gpt-4-turbo-2024-04-09": {
        "max_tokens": 4096,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "images", "json_mode", "function_calling"],
        "description": "GPT-4 Turbo with vision capabilities"
    },
    "gpt-4-0125-preview": {
        "max_tokens": 4096,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "function_calling", "reduced_laziness"],
        "description": "Preview model with improved task completion"
    },
    # Specialized Models
    "gpt-4o-realtime-preview": {
        "max_tokens": 4096,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "audio", "websocket"],
        "description": "Preview model for realtime interactions"
    },
    "gpt-4o-audio-preview": {
        "max_tokens": 16384,
        "context_length": 128000,
        "temperature": 0.2,
        "capabilities": ["text", "audio"],
        "description": "Preview model for audio processing in chat"
    }
}

# Model family definitions with capabilities
MODEL_FAMILIES = {
    "gpt-4o": {
        "description": "High-intelligence multimodal models",
        "base_capabilities": ["text", "images"],
        "models": ["gpt-4o", "gpt-4o-2024-08-06", "gpt-4o-2024-05-13"],
        "recommended_for": ["complex_tasks", "multimodal", "enterprise"]
    },
    "gpt-4o-mini": {
        "description": "Fast, lightweight multimodal models",
        "base_capabilities": ["text", "images"],
        "models": ["gpt-4o-mini", "gpt-4o-mini-2024-07-18"],
        "recommended_for": ["quick_tasks", "cost_effective", "vision"]
    },
    "o1": {
        "description": "Advanced reasoning models",
        "base_capabilities": ["reasoning", "code"],
        "models": ["o1-preview", "o1-mini", "o1-preview-2024-09-12", "o1-mini-2024-09-12"],
        "recommended_for": ["complex_reasoning", "coding", "math", "science"]
    },
    "gpt-4-turbo": {
        "description": "Latest GPT-4 models with enhanced features",
        "base_capabilities": ["text", "json_mode", "function_calling"],
        "models": ["gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-0125-preview"],
        "recommended_for": ["api_integration", "structured_output", "vision"]
    }
}

def get_recommended_model(task_type: str = None, requirements: List[str] = None) -> str:
    """
    Get recommended model based on task type and requirements.
    """
    # Implementation remains the same
    pass

def validate_model_config(model: str, config: Dict[str, Any] = None, requirements: List[str] = None) -> Dict[str, Any]:
    """
    Enhanced model validation with capability checking.
    """
    # First, validate model exists
    if model not in MODEL_CONFIGS and not any(
        model in family["models"] 
        for family in MODEL_FAMILIES.values()
    ):
        # If model not found, try to recommend one
        recommended = get_recommended_model(requirements=requirements)
        raise ValueError(
            f"Unsupported model: {model}. "
            f"Did you mean: {recommended}? "
            f"Available models: {', '.join(MODEL_CONFIGS.keys())}"
        )
    
    # If custom config provided, validate it
    if config:
        required_keys = {"max_tokens", "context_length", "temperature"}
        if not all(key in config for key in required_keys):
            raise ValueError(
                f"Invalid model configuration. Required keys: {required_keys}"
            )
        return config

    # Get model config
    if model in MODEL_CONFIGS:
        config = MODEL_CONFIGS[model]
    else:
        # Find family config
        found = False
        for family in MODEL_FAMILIES.values():
            if model in family["models"]:
                base_model = family["models"][0]
                config = MODEL_CONFIGS[base_model]
                found = True
                break
        if not found:
            raise ValueError(f"Model {model} not found in model configurations.")

    # Validate capabilities if required
    if requirements:
        missing = [req for req in requirements if req not in config["capabilities"]]
        if missing:
            recommended = get_recommended_model(requirements=requirements)
            raise ValueError(
                f"Model {model} missing required capabilities: {missing}. "
                f"Consider using {recommended} instead."
            )
    
    return config

class SPARCPromptGenerator:
    def __init__(
        self, 
        api_key: str, 
        model: str = "gpt-4o", 
        model_config: Dict[str, Any] = None,
        requirements: List[str] = None
    ):
        """Initialize the SPARC Prompt Generator."""
        # Initialize the AsyncOpenAI client
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Validate model and config
        try:
            self.model_config = validate_model_config(model, model_config, requirements)
            self.model = model
            self.capabilities = self.model_config["capabilities"]
        except ValueError as e:
            logging.error(f"Model validation error: {str(e)}")
            raise

        # Initialize prompts
        self.prompts = self._load_prompts()

        # Initialize tokenizer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Initialize usage tracking
        self.total_tokens = 0
        self.usage_log = []

        # Token limits
        self.max_model_tokens = self.model_config["context_length"]
        self.buffer_tokens = min(2000, self.model_config["max_tokens"])

        # Log initialization
        logging.info(f"Initialized with model: {model}")
        logging.info(f"Model config: {self.model_config}")
        logging.info(f"Max tokens: {self.max_model_tokens}")
        logging.info(f"Buffer tokens: {self.buffer_tokens}")

    def _load_prompts(self) -> Dict[str, str]:
        """Load SPARC prompts from YAML file."""
        prompts_file = Path(__file__).parent / "sparc_prompts.yaml"
        with open(prompts_file) as f:
            return yaml.safe_load(f)

    async def _generate_with_retry(
        self, 
        messages: List[Dict[str, Any]], 
        temp_override: float = None,
        max_retries: int = 3
    ) -> Any:
        """Generate with retry logic."""
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temp_override or self.model_config["temperature"],
                    max_tokens=self.model_config["max_tokens"],
                    n=1,
                )
                return response
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)

    def _update_usage_log(self, prompt_tokens: int, response_tokens: int, context: str):
        """Update usage tracking."""
        self.total_tokens += prompt_tokens + response_tokens
        self.usage_log.append({
            "context": context,
            "model": self.model,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": prompt_tokens + response_tokens,
            "timestamp": datetime.now().isoformat()
        })
        
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def split_transcript(self, transcript: str) -> List[str]:
        """Split transcript into chunks."""
        available_tokens = self.max_model_tokens - self.buffer_tokens
        tokens_per_word = 1.3  # Rough estimate
        max_words = math.floor(available_tokens / tokens_per_word)

        words = transcript.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunk = ' '.join(words[i:i + max_words])
            chunks.append(chunk)
        logging.info(f"Split transcript into {len(chunks)} chunks")
        return chunks

    def extract_json(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from response text."""
        try:
            response_text = response_text.strip()
            
            # Try to find JSON between code blocks first
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
                
            # If no code blocks, try to find JSON directly
            json_match = re.search(r'\{[^{]*"coverage_analysis".*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
                
            # If still no JSON found, try to clean up the text more aggressively
            cleaned_text = re.sub(r'^.*?(\{.*\}).*?$', r'\1', response_text, flags=re.DOTALL)
            return json.loads(cleaned_text)
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            logging.debug(f"Non-JSON response: {response_text}")
            return {
                "error": "Failed to parse JSON from model response.",
                "raw_response": response_text
            }

    def _aggregate_analysis(self, aggregated: Dict[str, Any], new_analysis: Dict[str, Any]):
        """Aggregate analysis results."""
        if not aggregated["application_type"]:
            aggregated["application_type"] = new_analysis.get("application_type", "")
        if not aggregated["technical_domain"]:
            aggregated["technical_domain"] = new_analysis.get("technical_domain", "")

        # Append unique items to lists
        for key in ["core_functionalities", "technical_requirements", "components", "dependencies", "technologies"]:
            for item in new_analysis.get(key, []):
                if item not in aggregated[key]:
                    aggregated[key].append(item)

        for key in ["algorithms", "patterns", "architecture_decisions", "constraints"]:
            for item in new_analysis.get("implementation_details", {}).get(key, []):
                if item not in aggregated["implementation_details"][key]:
                    aggregated["implementation_details"][key].append(item)

    async def analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Analyze transcript."""
        chunks = self.split_transcript(transcript)
        logging.info(f"Analyzing {len(chunks)} chunks with model {self.model}")

        aggregated_analysis = {
            "application_type": "",
            "technical_domain": "",
            "core_functionalities": [],
            "technical_requirements": [],
            "components": [],
            "dependencies": [],
            "technologies": [],
            "implementation_details": {
                "algorithms": [],
                "patterns": [],
                "architecture_decisions": [],
                "constraints": []
            }
        }

        for idx, chunk in enumerate(chunks):
            try:
                # Prepare the prompt
                prompt = self.prompts["initial_analysis"] + "\n\n" + chunk
                prompt_tokens = self.count_tokens(prompt)
                
                logging.info(f"Processing chunk {idx + 1}/{len(chunks)} ({prompt_tokens} tokens)")
                
                # Generate response
                response = await self._generate_with_retry([
                    {"role": "system", "content": "You are a helpful assistant specialized in software development."},
                    {"role": "user", "content": prompt},
                ])
                
                # Process response
                content = response.choices[0].message.content.strip()
                response_tokens = self.count_tokens(content)
                self._update_usage_log(prompt_tokens, response_tokens, f"chunk_{idx + 1}")

                # Parse and validate JSON
                analysis = self.extract_json(content)
                if "error" in analysis:
                    return analysis

                # Aggregate results
                self._aggregate_analysis(aggregated_analysis, analysis)
                logging.info(f"Successfully processed chunk {idx + 1}")

            except Exception as e:
                error_msg = f"Error processing chunk {idx + 1}: {str(e)}"
                logging.error(error_msg)
                return {"error": error_msg}

        logging.info("Transcript analysis completed successfully")
        return aggregated_analysis

    async def _generate_artifact(self, artifact_name: str, prompt: str) -> str:
        """Generate artifact with configured model."""
        prompt_tokens = self.count_tokens(prompt)
        response_max_tokens = self.max_model_tokens - prompt_tokens

        if response_max_tokens <= 0:
            logging.error(f"Prompt for artifact '{artifact_name}' exceeds the model's token limit.")
            return f"Error generating {artifact_name}: Prompt exceeds the model's token limit."

        logging.info(f"Generating artifact '{artifact_name}' with {prompt_tokens} tokens using {self.model}")

        try:
            response = await self._generate_with_retry([
                {"role": "system", "content": "You are a helpful assistant specialized in software development."},
                {"role": "user", "content": prompt},
            ])
            
            content = response.choices[0].message.content.strip()
            response_tokens = self.count_tokens(content)
            self._update_usage_log(prompt_tokens, response_tokens, artifact_name)
            
            return content
            
        except Exception as e:
            logging.error(f"Error generating {artifact_name}: {str(e)}")
            return f"Error generating {artifact_name}: {str(e)}"

    async def generate_sparc_artifacts(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate SPARC phase artifacts based on analysis."""
        artifacts = {}
        logging.info("Starting generation of SPARC artifacts.")

        # Define the artifact generation sequence
        artifact_sequence = [
            ("specification", lambda: json.dumps(analysis, indent=2)),
            ("pseudocode", lambda: artifacts["specification"]),
            ("architecture", lambda: artifacts["pseudocode"]),
            ("refinement", lambda: artifacts["architecture"]),
            ("completion", lambda: artifacts["refinement"])
        ]

        # Generate artifacts in sequence
        for artifact_name, get_input in artifact_sequence:
            prompt = self.prompts[artifact_name] + "\n\n" + get_input()
            artifacts[artifact_name] = await self._generate_artifact(artifact_name, prompt)

        logging.info(f"Total tokens after artifacts generation: {self.total_tokens}")
        return artifacts

    async def validate_artifacts(self, artifacts: Dict[str, str], original_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate generated artifacts against original analysis."""
        validation_prompt = f"""
        Validate these artifacts against the original requirements and produce a JSON response.
        
        Original Analysis:
        {json.dumps(original_analysis, indent=2)}
        
        Generated Artifacts:
        {json.dumps(artifacts, indent=2)}
        
        Respond ONLY with a valid JSON object in this exact format, without any additional text or explanation:
        {{
            "coverage_analysis": {{
                "features_covered": [],
                "missing_features": [],
                "requirements_covered": [],
                "missing_requirements": []
            }},
            "technical_validation": {{
                "architecture_completeness": true/false,
                "implementation_feasibility": true/false,
                "concerns": [],
                "recommendations": []
            }},
            "overall_assessment": {{
                "ready_for_implementation": true/false,
                "critical_gaps": [],
                "suggested_improvements": []
            }}
        }}
        """
        
        try:
            # Use stricter temperature for validation
            response = await self._generate_with_retry([
                {
                    "role": "system", 
                    "content": (
                        "You are a validation assistant that responds only with properly formatted JSON. "
                        "Never include explanatory text or markdown formatting in your response."
                    )
                },
                {"role": "user", "content": validation_prompt},
            ], temp_override=0.1)  # Lower temperature for more consistent output
            
            content = response.choices[0].message.content.strip()
            self._update_usage_log(
                self.count_tokens(validation_prompt),
                self.count_tokens(content),
                "validation"
            )
            
            # Try to parse JSON response
            validation = self.extract_json(content)
            if "error" not in validation:
                logging.info("Validation parsed successfully")
                return validation
            
            # If parsing failed, try to reconstruct a basic validation response
            logging.warning("Failed to parse validation response, constructing basic validation")
            return {
                "coverage_analysis": {
                    "features_covered": [],
                    "missing_features": ["Unable to validate features"],
                    "requirements_covered": [],
                    "missing_requirements": ["Unable to validate requirements"]
                },
                "technical_validation": {
                    "architecture_completeness": False,
                    "implementation_feasibility": False,
                    "concerns": ["Validation parsing failed"],
                    "recommendations": ["Retry validation with different prompt"]
                },
                "overall_assessment": {
                    "ready_for_implementation": False,
                    "critical_gaps": ["Validation failed"],
                    "suggested_improvements": ["Retry validation"]
                }
            }
            
        except Exception as e:
            logging.error(f"Error during validation: {str(e)}")
            return {
                "error": f"Error during validation: {str(e)}",
                "coverage_analysis": {
                    "features_covered": [],
                    "missing_features": ["Validation failed"],
                    "requirements_covered": [],
                    "missing_requirements": ["Validation failed"]
                },
                "technical_validation": {
                    "architecture_completeness": False,
                    "implementation_feasibility": False,
                    "concerns": [f"Validation error: {str(e)}"],
                    "recommendations": ["Retry validation"]
                },
                "overall_assessment": {
                    "ready_for_implementation": False,
                    "critical_gaps": ["Validation failed"],
                    "suggested_improvements": ["Retry validation"]
                }
            }

    async def chat_simulation(self, artifacts: Dict[str, Any]) -> str:
        """Simulate a chat-based interaction between user and AI-powered software engineer."""
        artifacts_json = json.dumps(artifacts, indent=4)
        prompt = self.prompts["chat_simulation"].replace("{...}", artifacts_json)
        
        try:
            response = await self._generate_with_retry([
                {"role": "system", "content": "You are an AI-powered software engineer assisting the user in developing an application."},
                {"role": "user", "content": prompt},
            ], temp_override=0.5)
            
            content = response.choices[0].message.content.strip()
            self._update_usage_log(
                self.count_tokens(prompt),
                self.count_tokens(content),
                "chat_simulation"
            )
            
            return content
            
        except Exception as e:
            logging.error(f"Error during chat simulation: {str(e)}")
            return f"Error during chat simulation: {str(e)}"

    def save_development_plan(self, plan: Dict[str, Any], output_dir: Path):
        """Save development plan to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Saving development plan to {output_dir}.")

        # Save main plan with model information
        plan["model_info"] = {
            "model": self.model,
            "config": self.model_config,
            "total_tokens": self.total_tokens
        }
        
        with open(output_dir / "development_plan.json", "w") as f:
            json.dump(plan, f, indent=2)

        # Save individual artifacts
        if "artifacts" in plan:
            artifacts_dir = output_dir / "artifacts"
            artifacts_dir.mkdir(exist_ok=True)

            for name, content in plan["artifacts"].items():
                sanitized_name = re.sub(r'[\\/*?:"<>|]', "_", name)
                with open(artifacts_dir / f"{sanitized_name}.md", "w") as f:
                    f.write(content)

        # Save usage log
        with open(output_dir / "usage_log.json", "w") as f:
            json.dump(self.usage_log, f, indent=2)

    def generate_usage_report(self) -> str:
        """Generate a summary report of API usage."""
        report = [f"Model: {self.model}"]
        report.append(f"Total Tokens Used: {self.total_tokens}\n")
        report.append("Detailed Usage Log:")
        
        # Group usage by type
        usage_by_type = {}
        for entry in self.usage_log:
            context = entry["context"]
            if context.startswith("chunk_"):
                type_key = "Transcript Analysis"
            elif context in ["specification", "pseudocode", "architecture", "refinement", "completion"]:
                type_key = "Artifact Generation"
            else:
                type_key = context.capitalize()

            if type_key not in usage_by_type:
                usage_by_type[type_key] = {
                    "prompt_tokens": 0,
                    "response_tokens": 0,
                    "total_tokens": 0,
                    "count": 0
                }
            
            stats = usage_by_type[type_key]
            stats["prompt_tokens"] += entry["prompt_tokens"]
            stats["response_tokens"] += entry["response_tokens"]
            stats["total_tokens"] += entry["total_tokens"]
            stats["count"] += 1

        # Format usage statistics
        for type_key, stats in usage_by_type.items():
            report.append(f"\n{type_key}:")
            report.append(f"  Requests: {stats['count']}")
            report.append(f"  Prompt Tokens: {stats['prompt_tokens']}")
            report.append(f"  Response Tokens: {stats['response_tokens']}")
            report.append(f"  Total Tokens: {stats['total_tokens']}")
            avg_tokens = stats['total_tokens'] / stats['count']
            report.append(f"  Average Tokens per Request: {avg_tokens:.2f}")

        # Add model configuration details
        report.append("\nModel Configuration:")
        report.append(f"  Max Tokens: {self.model_config['max_tokens']}")
        report.append(f"  Context Length: {self.model_config['context_length']}")
        report.append(f"  Temperature: {self.model_config['temperature']}")

        return "\n".join(report)

    def __str__(self) -> str:
        """String representation of the generator."""
        return f"SPARCPromptGenerator(model={self.model}, total_tokens={self.total_tokens})"

    def __repr__(self) -> str:
        """Detailed string representation of the generator."""
        return f"SPARCPromptGenerator(model={self.model}, config={self.model_config}, total_tokens={self.total_tokens})"


