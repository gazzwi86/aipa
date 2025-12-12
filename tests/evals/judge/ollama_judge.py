"""Custom Ollama LLM for DeepEval evaluation.

This module provides an Ollama-based LLM that can be used as a judge
in DeepEval tests. It connects to a local Ollama server to evaluate
agent responses.
"""

import httpx
from deepeval.models.base_model import DeepEvalBaseLLM


class OllamaJudge(DeepEvalBaseLLM):
    """Custom Ollama LLM for DeepEval evaluation.

    Uses a local Ollama instance to judge agent responses.
    Default model is gemma3:12b but can be configured.

    Example:
        judge = OllamaJudge(model="gemma3:12b")
        metric = GEval(name="test", criteria="...", model=judge)
    """

    def __init__(
        self,
        model: str = "gemma3:12b",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """Initialize Ollama judge.

        Args:
            model: Ollama model name (default: gemma3:12b)
            base_url: Ollama server URL (default: localhost:11434)
            timeout: Request timeout in seconds (default: 120)
        """
        self._model_name = model
        self.base_url = base_url
        self.timeout = timeout

    def load_model(self) -> "OllamaJudge":
        """Load the model (no-op for Ollama, model is loaded on demand)."""
        return self

    def generate(self, prompt: str) -> str:
        """Generate a response synchronously.

        Args:
            prompt: The evaluation prompt

        Returns:
            Model response as string
        """
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self._model_name,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    async def a_generate(self, prompt: str) -> str:
        """Generate a response asynchronously.

        Args:
            prompt: The evaluation prompt

        Returns:
            Model response as string
        """
        # Use explicit Timeout object for async client
        timeout = httpx.Timeout(timeout=300.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self._model_name,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    def get_model_name(self) -> str:
        """Get the model identifier for logging/tracking."""
        return f"ollama/{self._model_name}"
