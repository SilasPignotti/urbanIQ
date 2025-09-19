"""
NLP Service for parsing German natural language geodata requests.

Uses OpenAI GPT via LangChain to extract Berlin districts and datasets
from natural language input with confidence scoring and error handling.
"""

import json
import logging
from typing import Any

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, field_validator

from app.config import settings

logger = logging.getLogger("urbaniq.nlp_service")

# Berlin districts as defined in SERVICE_ARCHITECTURE.md
BERLIN_DISTRICTS = [
    "Mitte",
    "Pankow",
    "Charlottenburg-Wilmersdorf",
    "Spandau",
    "Steglitz-Zehlendorf",
    "Tempelhof-Schöneberg",
    "Neukölln",
    "Treptow-Köpenick",
    "Marzahn-Hellersdorf",
    "Lichtenberg",
    "Reinickendorf",
    "Friedrichshain-Kreuzberg",
]

# Available datasets for expanded scope
AVAILABLE_DATASETS = [
    "gebaeude",  # Buildings from Berlin Geoportal
    "oepnv_haltestellen",  # Public transport stops from OpenStreetMap
    "radverkehrsnetz",  # Cycling network data from Berlin Geoportal
    "strassennetz",  # Street network data from Berlin Geoportal
    "ortsteilgrenzen",  # Ortsteile administrative boundaries from Berlin Geoportal
    "einwohnerdichte",  # Population density 2024 data from Berlin Geoportal
    "geschosszahl",  # Building floors categorization from Berlin Geoportal
]


class ParsedRequest(BaseModel):
    """
    Structured output model for parsed natural language requests.

    Represents extracted information from German geodata requests
    including district, datasets, and confidence scoring.
    """

    bezirk: str | None = Field(
        default=None, description="Extracted Berlin district name (standardized)"
    )
    datasets: list[str] = Field(default_factory=list, description="List of identified datasets")
    confidence: float = Field(description="Confidence score for the parsing (0.0-1.0)")
    error_message: str | None = Field(default=None, description="Error message if parsing failed")
    reasoning: str | None = Field(
        default=None, description="LLM reasoning for the parsing decision"
    )

    @field_validator("bezirk")
    @classmethod
    def validate_bezirk(cls, v: str | None) -> str | None:
        """Validate bezirk is a known Berlin district."""
        if v is None:
            return v

        # Normalize district name for comparison
        normalized = v.strip()
        if normalized in BERLIN_DISTRICTS:
            return normalized

        # Handle common variations
        district_variations = {
            "charlottenburg": "Charlottenburg-Wilmersdorf",
            "wilmersdorf": "Charlottenburg-Wilmersdorf",
            "tempelhof": "Tempelhof-Schöneberg",
            "schöneberg": "Tempelhof-Schöneberg",
            "kreuzberg": "Friedrichshain-Kreuzberg",
            "friedrichshain": "Friedrichshain-Kreuzberg",
            "treptow": "Treptow-Köpenick",
            "köpenick": "Treptow-Köpenick",
            "steglitz": "Steglitz-Zehlendorf",
            "zehlendorf": "Steglitz-Zehlendorf",
        }

        normalized_lower = normalized.lower()
        if normalized_lower in district_variations:
            return district_variations[normalized_lower]

        # Return original if not found (LLM confidence should be low)
        return normalized

    @field_validator("datasets")
    @classmethod
    def validate_datasets(cls, v: list[str]) -> list[str]:
        """Validate datasets are from available set."""
        if not v:
            return v

        # Filter to only available datasets
        valid_datasets = [ds for ds in v if ds in AVAILABLE_DATASETS]
        return valid_datasets

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        return max(0.0, min(1.0, v))

    @property
    def datasets_json(self) -> str:
        """Return datasets as JSON string for Job model integration."""
        return json.dumps(self.datasets)

    @property
    def is_confident(self) -> bool:
        """Check if confidence meets minimum threshold (0.7)."""
        return self.confidence >= 0.7

    def model_dump_for_job(self) -> dict[str, Any]:
        """Return model data formatted for Job model creation."""
        return {"bezirk": self.bezirk, "datasets": self.datasets_json}


class NLPService:
    """
    Natural Language Processing service for German geodata requests.

    Uses OpenAI GPT to parse German text and extract structured
    information about Berlin districts and requested datasets.
    """

    def __init__(self) -> None:
        """Initialize NLP service with OpenAI client."""
        self.confidence_threshold = 0.7

        # Handle both SecretStr and string types (for testing compatibility)
        api_key_value: str | None = None
        if hasattr(settings.openai_api_key, "get_secret_value"):
            api_key_value = settings.openai_api_key.get_secret_value()
        else:
            api_key_value = str(settings.openai_api_key) if settings.openai_api_key else None

        if not api_key_value:
            raise ValueError(
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            )

        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",  # Cost-effective for structured parsing
            temperature=0.1,  # Low temperature for deterministic parsing
            openai_api_key=api_key_value,  # type: ignore[arg-type]
        )

        # Create parser for structured output
        self.parser = PydanticOutputParser(pydantic_object=ParsedRequest)

        # Create prompt template
        self.prompt_template = PromptTemplate(
            template=self._get_prompt_template(),
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

    def _get_prompt_template(self) -> str:
        """Get the prompt template for German geodata request parsing."""
        districts_list = ", ".join(BERLIN_DISTRICTS)
        return f"""Du bist ein Experte für Geodaten-Anfragen in Berlin.
Deine Aufgabe ist es, natürliche deutsche Sprache zu analysieren und strukturierte Informationen über gewünschte Geodaten zu extrahieren.

VERFÜGBARE BERLIN BEZIRKE:
{districts_list}

VERFÜGBARE DATENSÄTZE (nur diese verwenden):
- gebaeude: Gebäudedaten, Bauten, Häuser, Wohngebäude, Bürogebäude
- oepnv_haltestellen: ÖPNV-Haltestellen, Bushaltestellen, U-Bahn-Stationen, S-Bahn-Stationen, öffentlicher Nahverkehr
- radverkehrsnetz: Radwege, Fahrradnetz, Cycling Network, Radverkehr, Fahrradinfrastruktur
- strassennetz: Straßen, Straßennetz, Verkehrsnetz, roads, streets, Verkehrsinfrastruktur
- ortsteilgrenzen: Ortsteile, Ortsteilgrenzen, Stadtteile, sub-districts, neighborhoods
- einwohnerdichte: Bevölkerungsdichte, Einwohnerdichte, population density, demographics
- geschosszahl: Gebäudegeschosse, Stockwerke, Geschosshöhe, building floors, building heights

INTELLIGENTE ANALYSENMUSTER:
MOBILITÄTSANALYSE → automatisch: ["radverkehrsnetz", "strassennetz", "oepnv_haltestellen"]
BEZIRKSANALYSE → automatisch: ["ortsteilgrenzen", "gebaeude", "geschosszahl", "einwohnerdichte"]
GESCHOSSHÖHE → automatisch: ["geschosszahl", "gebaeude"]

ANWEISUNGEN:
1. Identifiziere den Berliner Bezirk aus dem Text
2. Identifiziere die gewünschten Datensätze basierend auf Schlüsselwörtern ODER Analysemustern
3. Bei Analysemustern: verwende die automatische Datensatz-Kombination
4. Bewerte deine Confidence (0.0-1.0) für die Extraktion
5. Gib eine kurze Begründung für deine Entscheidung

ERWEITERTE BEISPIELE:
- "Pankow Mobilitätsanalyse" → bezirk: "Pankow", datasets: ["radverkehrsnetz", "strassennetz", "oepnv_haltestellen"]
- "Mitte Bezirksanalyse" → bezirk: "Mitte", datasets: ["ortsteilgrenzen", "gebaeude", "geschosszahl", "einwohnerdichte"]
- "Charlottenburg Geschosshöhe" → bezirk: "Charlottenburg-Wilmersdorf", datasets: ["geschosszahl", "gebaeude"]
- "Spandau Radwege und Straßen" → bezirk: "Spandau", datasets: ["radverkehrsnetz", "strassennetz"]
- "Pankow Ortsteile und Bevölkerung" → bezirk: "Pankow", datasets: ["ortsteilgrenzen", "einwohnerdichte"]
- "Neukölln cycling infrastructure" → bezirk: "Neukölln", datasets: ["radverkehrsnetz"]

USER QUERY: {{query}}

{{format_instructions}}

WICHTIG:
- Confidence unter 0.7 wenn Bezirk oder Datensätze unklar sind
- Nur verfügbare Datensätze verwenden
- Bezirksnamen exakt wie in der Liste angeben
- Bei Analysemustern: verwende die vordefinierten Kombinationen
- Reasoning auf Deutsch verfassen
"""

    def parse_user_request(self, text: str) -> ParsedRequest:
        """
        Parse natural language text to extract geodata request information.

        Args:
            text: German natural language text describing geodata request

        Returns:
            ParsedRequest with extracted bezirk, datasets, and confidence

        Raises:
            ValueError: If input text is invalid
            RuntimeError: If API call fails after retries
        """
        if not text or not text.strip():
            return ParsedRequest(
                confidence=0.0,
                error_message="Empty or invalid input text",
                reasoning="Eingabe ist leer oder ungültig",
            )

        # Validate input length
        if len(text.strip()) > 500:
            return ParsedRequest(
                confidence=0.0,
                error_message="Input text too long (max 500 characters)",
                reasoning="Eingabe ist zu lang (max 500 Zeichen)",
            )

        try:
            # Create the full prompt
            prompt = self.prompt_template.format(query=text.strip())

            logger.info(f"Processing NLP request: '{text[:100]}...'")

            # Get response from LLM
            response = self.llm.invoke(prompt)

            # Parse the structured response
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            parsed_result = self.parser.parse(content)

            # Validate confidence threshold
            if not parsed_result.is_confident:
                logger.warning(f"Low confidence ({parsed_result.confidence}) for request: {text}")
                parsed_result.error_message = f"Niedrige Confidence ({parsed_result.confidence:.2f}). Bitte präzisieren Sie Ihre Anfrage."

            logger.info(
                f"NLP parsing completed: bezirk={parsed_result.bezirk}, datasets={parsed_result.datasets}, confidence={parsed_result.confidence}"
            )

            return parsed_result

        except Exception as e:
            logger.error(f"NLP parsing failed for '{text}': {str(e)}")

            # Return fallback response with error
            return ParsedRequest(
                confidence=0.0,
                error_message=f"Parsing failed: {str(e)}",
                reasoning=f"Fehler beim Verarbeiten der Anfrage: {str(e)}",
            )

    def get_suggestion_for_failed_request(
        self, _original_text: str, parsed_result: ParsedRequest
    ) -> str:
        """
        Generate helpful suggestion for failed or low-confidence requests.

        Args:
            original_text: Original user input
            parsed_result: Failed parsing result

        Returns:
            Helpful suggestion text in German
        """
        if not parsed_result.bezirk:
            return (
                "Bitte geben Sie einen Berliner Bezirk an. "
                f"Verfügbare Bezirke: {', '.join(BERLIN_DISTRICTS[:3])}... "
                "Beispiel: 'Pankow Gebäude und Haltestellen'"
            )

        if not parsed_result.datasets:
            return (
                "Bitte geben Sie gewünschte Datentypen an. "
                "Verfügbare Daten: Gebäude, ÖPNV-Haltestellen. "
                "Beispiel: 'Mitte Gebäude für Stadtplanung'"
            )

        return (
            "Ihre Anfrage ist nicht eindeutig. "
            "Beispiele: 'Pankow Gebäude', 'Mitte ÖPNV-Haltestellen', "
            "'Charlottenburg Gebäude und Haltestellen'"
        )
