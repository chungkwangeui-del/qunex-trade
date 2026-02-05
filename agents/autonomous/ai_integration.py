"""
AI Integration Agent
====================

Connects to OpenAI/Claude API for intelligent code analysis and fixes.
Provides smart suggestions, code generation, and natural language explanations.
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Response from AI model."""
    success: bool
    content: str
    model: str
    tokens_used: int = 0
    cost: float = 0.0
    error: Optional[str] = None


@dataclass
class CodeFix:
    """AI-suggested code fix."""
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float
    category: str  # 'bug', 'security', 'performance', 'style'


class AIIntegration:
    """
    AI-powered code analysis and generation.

    Supports:
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Local/offline fallback
    """

    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = self._detect_available_model()
        self.usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'requests_today': 0,
            'last_request': None
        }

    def _detect_available_model(self) -> str:
        """Detect which AI model is available."""
        if self.anthropic_key:
            return 'claude'
        elif self.openai_key:
            return 'openai'
        else:
            return 'offline'

    def is_available(self) -> bool:
        """Check if AI is available."""
        return self.model != 'offline'

    async def analyze_code(self, code: str, context: str = "") -> AIResponse:
        """
        Analyze code for issues, improvements, and explanations.

        Args:
            code: The code to analyze
            context: Additional context about what the code does

        Returns:
            AIResponse with analysis
        """
        prompt = """Analyze this Python code and identify:
1. Bugs or errors
2. Security vulnerabilities
3. Performance issues
4. Code style improvements
5. Missing error handling

Context: {context}

Code:
```python
{code}
```

Provide a structured analysis with specific line numbers and fixes."""

        return await self._call_ai(prompt)

    async def generate_fix(self, code: str, issue: str) -> CodeFix:
        """
        Generate a fix for a specific code issue.

        Args:
            code: The problematic code
            issue: Description of the issue

        Returns:
            CodeFix with the suggested fix
        """
        prompt = """Fix this Python code issue:

Issue: {issue}

Original Code:
```python
{code}
```

Provide:
1. The fixed code
2. A brief explanation of the fix
3. The category (bug/security/performance/style)
4. Your confidence level (0-1)

Format your response as JSON:
{{
    "fixed_code": "...",
    "explanation": "...",
    "category": "...",
    "confidence": 0.95
}}"""

        response = await self._call_ai(prompt)

        if response.success:
            try:
                # Parse JSON from response
                json_match = re.search(r'\{[\s\S]*\}', response.content)
                if json_match:
                    data = json.loads(json_match.group())
                    return CodeFix(
                        file_path="",
                        original_code=code,
                        fixed_code=data.get('fixed_code', code),
                        explanation=data.get('explanation', ''),
                        confidence=data.get('confidence', 0.5),
                        category=data.get('category', 'bug')
                    )
            except json.JSONDecodeError:
                pass

        # Fallback
        return CodeFix(
            file_path="",
            original_code=code,
            fixed_code=code,
            explanation="AI analysis failed",
            confidence=0.0,
            category='unknown'
        )

    async def explain_error(self, error: str, code: str = "") -> str:
        """
        Explain an error in simple terms.

        Args:
            error: The error message/traceback
            code: Related code if available

        Returns:
            Human-readable explanation
        """
        prompt = """Explain this Python error in simple terms that a developer can understand:

Error:
{error}

{"Related Code:" + chr(10) + code if code else ""}

Provide:
1. What the error means
2. Why it likely happened
3. How to fix it
4. Example of the correct code"""

        response = await self._call_ai(prompt)
        return response.content if response.success else f"Could not analyze: {response.error}"

    async def generate_feature(self, description: str, context: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Generate code for a new feature.

        Args:
            description: Natural language description of the feature
            context: Project context (models, services, etc.)

        Returns:
            Dict of file_path -> code content
        """
        context_str = ""
        if context:
            context_str = """
Project Context:
- Models: {', '.join(context.get('models', []))}
- Services: {', '.join(context.get('services', []))}
- Framework: Flask
- Database: SQLite with SQLAlchemy
"""

        prompt = """Generate Python code for this feature:

{description}

{context_str}

Generate complete, production-ready code including:
1. Model (if needed)
2. Service/business logic
3. API route
4. Tests

Format your response as JSON:
{{
    "models/new_model.py": "code...",
    "services/new_service.py": "code...",
    "routes/new_route.py": "code...",
    "tests/test_new.py": "code..."
}}"""

        response = await self._call_ai(prompt)

        if response.success:
            try:
                json_match = re.search(r'\{[\s\S]*\}', response.content)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {}

    async def generate_tests(self, code: str, file_path: str) -> str:
        """
        Generate unit tests for code.

        Args:
            code: The code to test
            file_path: Path to the code file

        Returns:
            Test code as string
        """
        prompt = """Generate comprehensive unit tests for this Python code:

File: {file_path}

Code:
```python
{code}
```

Generate pytest tests that:
1. Test all functions/methods
2. Include edge cases
3. Mock external dependencies
4. Have good coverage

Return only the test code, no explanations."""

        response = await self._call_ai(prompt)
        return response.content if response.success else ""

    async def suggest_improvements(self, code: str) -> List[Dict[str, Any]]:
        """
        Suggest improvements for code.

        Args:
            code: The code to improve

        Returns:
            List of improvement suggestions
        """
        prompt = """Suggest improvements for this Python code:

```python
{code}
```

For each suggestion, provide:
1. What to improve
2. Why it's an improvement
3. The improved code snippet
4. Priority (high/medium/low)

Format as JSON array:
[
    {{
        "what": "...",
        "why": "...",
        "code": "...",
        "priority": "high"
    }}
]"""

        response = await self._call_ai(prompt)

        if response.success:
            try:
                json_match = re.search(r'\[[\s\S]*\]', response.content)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return []

    async def _call_ai(self, prompt: str) -> AIResponse:
        """
        Call the AI model.

        Args:
            prompt: The prompt to send

        Returns:
            AIResponse
        """
        self.usage_stats['total_requests'] += 1
        self.usage_stats['requests_today'] += 1
        self.usage_stats['last_request'] = datetime.now().isoformat()

        if self.model == 'claude':
            return await self._call_claude(prompt)
        elif self.model == 'openai':
            return await self._call_openai(prompt)
        else:
            return await self._offline_response(prompt)

    async def _call_claude(self, prompt: str) -> AIResponse:
        """Call Anthropic Claude API."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.anthropic_key)

            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            tokens = message.usage.input_tokens + message.usage.output_tokens
            cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000

            self.usage_stats['total_tokens'] += tokens
            self.usage_stats['total_cost'] += cost

            return AIResponse(
                success=True,
                content=message.content[0].text,
                model='claude-3-sonnet',
                tokens_used=tokens,
                cost=cost
            )

        except ImportError:
            return AIResponse(
                success=False,
                content="",
                model='claude',
                error="anthropic package not installed. Run: pip install anthropic"
            )
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return AIResponse(
                success=False,
                content="",
                model='claude',
                error=str(e)
            )

    async def _call_openai(self, prompt: str) -> AIResponse:
        """Call OpenAI API."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.openai_key)

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert Python developer helping with code analysis and fixes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096
            )

            tokens = response.usage.total_tokens
            # GPT-4 Turbo pricing
            cost = (response.usage.prompt_tokens * 0.01 + response.usage.completion_tokens * 0.03) / 1000

            self.usage_stats['total_tokens'] += tokens
            self.usage_stats['total_cost'] += cost

            return AIResponse(
                success=True,
                content=response.choices[0].message.content,
                model='gpt-4-turbo',
                tokens_used=tokens,
                cost=cost
            )

        except ImportError:
            return AIResponse(
                success=False,
                content="",
                model='openai',
                error="openai package not installed. Run: pip install openai"
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return AIResponse(
                success=False,
                content="",
                model='openai',
                error=str(e)
            )

    async def _offline_response(self, prompt: str) -> AIResponse:
        """
        Provide basic analysis when no AI is available.
        Uses pattern matching and heuristics.
        """
        # Basic pattern-based analysis
        suggestions = []

        # Check for common issues
        if 'except Exception:' in prompt and 'except Exception' not in prompt:
            suggestions.append("Consider using specific exception types instead of bare 'except Exception:'")

        if 'print(' in prompt:
            suggestions.append("Consider using logging instead of print(s)tatements")

        if 'password' in prompt.lower() and '=' in prompt:
            suggestions.append("Ensure passwords are not hardcoded")

        if 'TODO' in prompt or 'FIXME' in prompt:
            suggestions.append("There are TODO/FIXME comments that need attention")

        if 'import *' in prompt:
            suggestions.append("Avoid wildcard imports for better code clarity")

        content = "Offline Analysis:\n" + "\n".join(f"- {s}" for s in suggestions) if suggestions else "No issues detected in offline mode."

        return AIResponse(
            success=True,
            content=content,
            model='offline',
            tokens_used=0,
            cost=0.0
        )

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get AI usage statistics."""
        return {
            **self.usage_stats,
            'model': self.model,
            'is_available': self.is_available()
        }


# Singleton instance
_ai_instance: Optional[AIIntegration] = None


def get_ai() -> AIIntegration:
    """Get the AI integration singleton."""
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = AIIntegration()
    return _ai_instance


