"""
OpenAI API client for extracting investment positions from documents
"""

import os
import json
import base64
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from openai import OpenAI
from openai.types.chat import ChatCompletion


class OpenAIExtractor:
    """Extract investment positions from images/PDFs using OpenAI Vision API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key. If not provided, will try to get from OPENAI_API_KEY env var
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            raise ValueError(
                "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.\n"
                "Get your API key from: https://platform.openai.com/api-keys"
            )

        self.client = OpenAI(api_key=self.api_key)

    def extract_positions_from_image(
        self,
        image_data: bytes,
        model: str = "gpt-4o",
        mime_type: str = "image/jpeg"
    ) -> Tuple[List[Dict], Dict]:
        """
        Extract investment positions from an image

        Args:
            image_data: Raw image bytes
            model: OpenAI model to use (gpt-4o or gpt-4o-mini)
            mime_type: MIME type of the image

        Returns:
            Tuple of (positions list, metadata dict)
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Create the prompt for structured extraction
        prompt = self._create_extraction_prompt()

        try:
            # Call OpenAI Vision API
            response: ChatCompletion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.1  # Low temperature for more consistent extraction
            )

            # Parse response
            result = self._parse_response(response)

            # Add metadata
            metadata = {
                'model_used': model,
                'tokens_used': response.usage.total_tokens if response.usage else 0,
                'extraction_date': datetime.now()
            }

            return result, metadata

        except Exception as e:
            raise Exception(f"Failed to extract positions from image: {str(e)}")

    def _create_extraction_prompt(self) -> str:
        """Create the extraction prompt for OpenAI"""
        return """
Analyze this investment statement/document and extract ALL investment positions.

For each position, extract:
- name: Asset name (e.g., "Tesouro IPCA+ 2035", "MXRF11", "XP Credito Estruturado FIC FI RF CP")
- value: Current value in BRL (as float, e.g., 12500.75)
- invested_value: Original invested amount in BRL (as float, if available, otherwise null)
- main_category: Main category (choose from: "Renda Fixa", "Fundos de Investimentos", "Fundos Imobiliários", "Previdência Privada", "COE", "Outro")
- sub_category: Sub-category or type (e.g., "Pós-Fixado", "IPCA+", "Multimercados", "FII - Papel", etc.)

Also extract document metadata:
- position_date: Date of the statement (YYYY-MM-DD format)
- account: Account number or institution name (if visible)

Return ONLY valid JSON in this exact format (no markdown, no explanations):
{
  "positions": [
    {
      "name": "Asset Name",
      "value": 12500.75,
      "invested_value": 10000.00,
      "main_category": "Renda Fixa",
      "sub_category": "Pós-Fixado"
    }
  ],
  "metadata": {
    "position_date": "2024-01-31",
    "account": "12345-6"
  }
}

IMPORTANT:
- Extract ALL positions visible in the document
- Convert Brazilian number format (1.234,56) to standard format (1234.56)
- If invested_value is not shown, use null
- If you cannot determine a field, use reasonable defaults
- Ensure all numeric values are numbers, not strings
- Return valid JSON only
"""

    def _parse_response(self, response: ChatCompletion) -> List[Dict]:
        """
        Parse OpenAI response into positions list

        Args:
            response: OpenAI API response

        Returns:
            List of position dictionaries
        """
        try:
            # Get the content from response
            content = response.choices[0].message.content

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Parse JSON
            data = json.loads(content)

            # Validate structure
            if "positions" not in data:
                raise ValueError("Response missing 'positions' field")

            positions = data["positions"]

            # Validate each position has required fields
            for pos in positions:
                if "name" not in pos or "value" not in pos:
                    raise ValueError(f"Position missing required fields: {pos}")

                # Ensure value is float
                pos["value"] = float(pos["value"])

                # Handle invested_value
                if "invested_value" in pos and pos["invested_value"] is not None:
                    pos["invested_value"] = float(pos["invested_value"])
                else:
                    pos["invested_value"] = None

            return positions

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}\nContent: {content[:200]}")
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAI response: {str(e)}")

    def get_extraction_metadata(self, response: ChatCompletion) -> Dict:
        """Extract metadata from OpenAI response"""
        try:
            content = response.choices[0].message.content

            # Try to extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            metadata = data.get("metadata", {})

            # Parse position_date if present
            if "position_date" in metadata:
                try:
                    metadata["position_date"] = datetime.strptime(
                        metadata["position_date"],
                        "%Y-%m-%d"
                    )
                except Exception:
                    metadata["position_date"] = datetime.now()
            else:
                metadata["position_date"] = datetime.now()

            return metadata

        except Exception:
            return {"position_date": datetime.now()}

    @staticmethod
    def estimate_cost(model: str, image_size_kb: int) -> float:
        """
        Estimate API call cost

        Args:
            model: Model name (gpt-4o or gpt-4o-mini)
            image_size_kb: Image size in KB

        Returns:
            Estimated cost in USD
        """
        # Token estimates (rough approximation)
        # Images: ~85 tokens per 512x512 tile, prompt ~500 tokens, completion ~2000 tokens
        base_tokens = 500  # Prompt
        image_tokens = (image_size_kb / 170) * 85  # Very rough estimate
        completion_tokens = 2000

        total_input_tokens = base_tokens + image_tokens

        # Pricing (as of 2024)
        if model == "gpt-4o":
            # $2.50 per 1M input tokens, $10 per 1M output tokens
            input_cost = (total_input_tokens / 1_000_000) * 2.50
            output_cost = (completion_tokens / 1_000_000) * 10.00
        else:  # gpt-4o-mini
            # $0.15 per 1M input tokens, $0.60 per 1M output tokens
            input_cost = (total_input_tokens / 1_000_000) * 0.15
            output_cost = (completion_tokens / 1_000_000) * 0.60

        return round(input_cost + output_cost, 4)

    def validate_api_key(self) -> bool:
        """
        Validate that the API key works

        Returns:
            True if valid, False otherwise
        """
        try:
            # Try a simple API call
            self.client.models.list()
            return True
        except Exception:
            return False
