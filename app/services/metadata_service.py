"""
Metadata Service for generating professional LLM-powered geodata reports.

Uses Google Gemini AI to create comprehensive, multilingual metadata reports
for geodata packages with quality assessment and usage recommendations.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger("urbaniq.metadata_service")

# Template directory path
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "metadata"

# Dataset type mapping for display names
DATASET_DISPLAY_NAMES = {
    "de": {
        "bezirksgrenzen": "Bezirksgrenzen Berlin",
        "gebaeude": "Gebäudedaten Berlin",
        "oepnv_haltestellen": "ÖPNV-Haltestellen",
    },
    "en": {
        "bezirksgrenzen": "District Boundaries Berlin",
        "gebaeude": "Building Data Berlin",
        "oepnv_haltestellen": "Public Transport Stops",
    },
}

# License information mapping
LICENSE_INFO = {
    "geoportal": {
        "license": "CC BY 3.0 DE",
        "source_attribution": "Berlin Geoportal (https://gdi.berlin.de)",
        "usage_terms": "Freie Nutzung mit Quellenangabe",
    },
    "osm": {
        "license": "Open Database License (ODbL)",
        "source_attribution": "OpenStreetMap Contributors",
        "usage_terms": "Share-alike license, see https://opendatacommons.org/licenses/odbl/",
    },
}


class MetadataError(Exception):
    """Base exception for metadata service errors."""

    pass


class TemplateError(MetadataError):
    """Raised when template rendering fails."""

    pass


class LLMError(MetadataError):
    """Raised when LLM processing fails."""

    pass


class MetadataService:
    """
    Service for generating LLM-powered metadata reports for geodata packages.

    Creates professional, multilingual metadata reports using OpenAI GPT
    integration with Jinja2 template system for consistent formatting.
    """

    def __init__(self) -> None:
        """Initialize Metadata Service with OpenAI and template engine."""
        logger.info("Initializing Metadata Service")

        # Initialize Jinja2 template engine
        self.template_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.template_env.filters["number_format"] = self._format_number

        # Initialize OpenAI client if API key available
        self.llm = None

        if settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    model_name="gpt-4o",  # Better for creative report generation
                    temperature=0.3,  # Creative but consistent for report generation
                    openai_api_key=settings.openai_api_key.get_secret_value(),  # type: ignore[arg-type]
                )
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.llm = None
        else:
            logger.warning("OpenAI API key not configured, LLM enhancement disabled")
            self.llm = None

    def create_metadata_report(
        self, datasets: list[dict[str, Any]], bezirk: str, request_info: dict[str, Any]
    ) -> str:
        """
        Create comprehensive metadata report for geodata packages.

        Generates professional metadata reports with quality assessment,
        usage recommendations, and licensing information using OpenAI GPT
        enhancement and Jinja2 templates.

        Args:
            datasets: List of dataset dictionaries from ProcessingService output
            bezirk: Berlin district name for spatial context
            request_info: Additional request context (language, user preferences)

        Returns:
            Comprehensive Markdown metadata report as string

        Raises:
            MetadataError: If report generation fails
            TemplateError: If template rendering fails

        Example:
            >>> service = MetadataService()
            >>> datasets = [...] # ProcessingService harmonized output
            >>> report = service.create_metadata_report(datasets, "Pankow", {"language": "de"})
            >>> print(report[:100])  # "# Geodaten-Metadatenreport: Pankow..."
        """
        if not datasets:
            raise MetadataError("No datasets provided for metadata report generation")

        logger.info(
            f"Creating metadata report for {len(datasets)} datasets in {bezirk}",
            extra={"bezirk": bezirk, "dataset_count": len(datasets)},
        )

        try:
            # Determine language (default to German)
            language = request_info.get("language", "de")
            if language not in ["de", "en"]:
                language = "de"

            # Prepare template context
            context = self._prepare_template_context(datasets, bezirk, language, request_info)

            # Enhance context with LLM analysis if available
            if self.llm:
                try:
                    enhanced_context = self._enhance_with_llm(context, language)
                    context.update(enhanced_context)
                    logger.info("Successfully enhanced metadata with LLM analysis")
                except Exception as e:
                    logger.warning(f"LLM enhancement failed, using basic context: {e}")

            # Render template
            template_name = f"geodata_report_{language}.md"
            template = self.template_env.get_template(template_name)
            report = template.render(**context)

            logger.info(
                f"Metadata report generated successfully ({len(report)} characters)",
                extra={"report_length": len(report), "language": language},
            )

            return report

        except Exception as e:
            logger.error(
                f"Failed to generate metadata report: {str(e)}",
                extra={"bezirk": bezirk, "dataset_count": len(datasets), "error": str(e)},
            )
            raise MetadataError(f"Metadata report generation failed: {str(e)}") from e

    def _prepare_template_context(
        self,
        datasets: list[dict[str, Any]],
        bezirk: str,
        language: str,
        request_info: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        """Prepare base template context from dataset information."""
        # Calculate overview statistics
        total_features = sum(
            dataset.get("runtime_stats", {}).get("feature_count", 0) for dataset in datasets
        )

        # Calculate overall quality score (weighted average)
        quality_scores = []
        feature_counts = []
        for dataset in datasets:
            stats = dataset.get("runtime_stats", {})
            if "data_quality_score" in stats:
                quality_scores.append(stats["data_quality_score"])
                feature_counts.append(stats.get("feature_count", 1))

        if quality_scores:
            overall_quality = sum(
                score * count for score, count in zip(quality_scores, feature_counts, strict=True)
            ) / sum(feature_counts)
            overall_quality_score = f"{overall_quality:.1%}"
        else:
            overall_quality_score = "N/A"

        # Calculate coverage percentage (average)
        coverage_percentages = [
            dataset.get("runtime_stats", {}).get("coverage_percentage", 0) for dataset in datasets
        ]
        coverage_percentage = (
            sum(coverage_percentages) / len(coverage_percentages) if coverage_percentages else 0
        )

        # Process datasets for template
        processed_datasets = []
        for dataset in datasets:
            processed_dataset = self._process_dataset_for_template(dataset, language)
            processed_datasets.append(processed_dataset)

        return {
            "bezirk": bezirk,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "dataset_count": len(datasets),
            "total_features": total_features,
            "coverage_percentage": f"{coverage_percentage:.1f}",
            "overall_quality_score": overall_quality_score,
            "datasets": processed_datasets,
            "language": language,
        }

    def _process_dataset_for_template(
        self, dataset: dict[str, Any], language: str
    ) -> dict[str, Any]:
        """Process individual dataset for template rendering."""
        dataset_type = dataset.get("dataset_type", "unknown")
        source = dataset.get("source", "unknown")

        # Get display name
        display_names = DATASET_DISPLAY_NAMES.get(language, DATASET_DISPLAY_NAMES["en"])
        display_name = display_names.get(dataset_type, dataset_type.title())

        # Get licensing information
        license_info = LICENSE_INFO.get(
            source,
            {
                "license": "Unknown",
                "source_attribution": "Unknown source",
                "usage_terms": "See original source for terms",
            },
        )

        # Extract runtime statistics
        stats = dataset.get("runtime_stats", {})
        feature_count = stats.get("feature_count", 0)
        quality_score = stats.get("data_quality_score", 0)

        # Format quality assessment
        if quality_score >= 0.9:
            quality_assessment = "Sehr hoch" if language == "de" else "Very High"
        elif quality_score >= 0.8:
            quality_assessment = "Hoch" if language == "de" else "High"
        elif quality_score >= 0.7:
            quality_assessment = "Gut" if language == "de" else "Good"
        elif quality_score >= 0.6:
            quality_assessment = "Mittel" if language == "de" else "Medium"
        else:
            quality_assessment = "Niedrig" if language == "de" else "Low"

        # Get predefined metadata
        predefined = dataset.get("predefined_metadata", {})

        return {
            "dataset_type": dataset_type,
            "display_name": display_name,
            "description": predefined.get("description", "No description available"),
            "source": source.title(),
            "feature_count": self._format_number(feature_count),
            "quality_score": f"{quality_score:.1%}" if quality_score else "N/A",
            "quality_assessment": quality_assessment,
            "update_frequency": predefined.get("update_frequency", "Unknown"),
            "spatial_extent": self._format_spatial_extent(stats.get("spatial_extent", [])),
            "key_attributes": self._extract_key_attributes(dataset, language),
            "license": license_info["license"],
            "source_attribution": license_info["source_attribution"],
            "usage_terms": license_info["usage_terms"],
            "usage_notes": self._generate_usage_notes(dataset_type, language),
        }

    def _extract_key_attributes(
        self, dataset: dict[str, Any], language: str
    ) -> list[dict[str, str]]:
        """Extract key attributes for dataset documentation."""
        dataset_type = dataset.get("dataset_type", "")

        # Define key attributes per dataset type
        attribute_mappings = {
            "bezirksgrenzen": {
                "de": [
                    {"name": "bezirk_name", "description": "Name des Bezirks"},
                    {"name": "flaeche_ha", "description": "Fläche in Hektar"},
                ],
                "en": [
                    {"name": "bezirk_name", "description": "District name"},
                    {"name": "flaeche_ha", "description": "Area in hectares"},
                ],
            },
            "gebaeude": {
                "de": [
                    {"name": "nutzung", "description": "Gebäudenutzung"},
                    {"name": "geschosse", "description": "Anzahl Geschosse"},
                    {"name": "baujahr", "description": "Baujahr"},
                ],
                "en": [
                    {"name": "nutzung", "description": "Building usage"},
                    {"name": "geschosse", "description": "Number of floors"},
                    {"name": "baujahr", "description": "Construction year"},
                ],
            },
            "oepnv_haltestellen": {
                "de": [
                    {"name": "name", "description": "Name der Haltestelle"},
                    {"name": "operator", "description": "Verkehrsbetreiber"},
                    {"name": "transport_mode", "description": "Verkehrsmittel"},
                ],
                "en": [
                    {"name": "name", "description": "Stop name"},
                    {"name": "operator", "description": "Transport operator"},
                    {"name": "transport_mode", "description": "Transport mode"},
                ],
            },
        }

        return attribute_mappings.get(dataset_type, {}).get(language, [])

    def _generate_usage_notes(self, dataset_type: str, language: str) -> str:
        """Generate usage notes for dataset types."""
        usage_notes = {
            "bezirksgrenzen": {
                "de": "Zur räumlichen Filterung und als Referenzgeometrie für Analysen",
                "en": "For spatial filtering and as reference geometry for analyses",
            },
            "gebaeude": {
                "de": "Geeignet für Stadtplanung, Demografie und Immobilienanalysen",
                "en": "Suitable for urban planning, demographics and real estate analyses",
            },
            "oepnv_haltestellen": {
                "de": "Ideal für Mobilitäts- und Erreichbarkeitsanalysen",
                "en": "Ideal for mobility and accessibility analyses",
            },
        }

        return usage_notes.get(dataset_type, {}).get(language, "")

    def _enhance_with_llm(self, context: dict[str, Any], language: str) -> dict[str, Any]:
        """Enhance template context with LLM-generated insights."""
        if not self.llm:
            return {}

        # Create prompt for LLM analysis
        prompt_template = PromptTemplate(
            input_variables=["context", "language"],
            template=self._get_llm_prompt_template(language),
        )

        # Prepare context for LLM
        llm_context = {
            "bezirk": context.get("bezirk", "Unknown"),
            "dataset_count": context.get("dataset_count", 0),
            "total_features": context.get("total_features", 0),
            "datasets": [
                {
                    "type": ds.get("dataset_type", "unknown"),
                    "features": ds.get("feature_count", "N/A"),
                    "quality": ds.get("quality_score", "N/A"),
                }
                for ds in context.get("datasets", [])
            ],
        }

        try:
            # Generate LLM response
            prompt = prompt_template.format(context=str(llm_context), language=language)
            response = self.llm.invoke(prompt)

            # Parse LLM response (simplified - could be enhanced with structured output)
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            enhanced_data = self._parse_llm_response(content, language)

            return enhanced_data
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {str(e)}")
            return {}

    def _get_llm_prompt_template(self, language: str) -> str:
        """Get LLM prompt template for metadata enhancement."""
        if language == "de":
            return """Du bist ein Experte für Geodaten-Analyse und Metadaten-Dokumentation.

Analysiere den folgenden Geodaten-Kontext und erstelle Qualitätsbewertungen und Nutzungsempfehlungen:

Kontext: {context}

Generiere eine prägnante Qualitätsbewertung und 3-4 konkrete Nutzungsempfehlungen für diese Geodaten-Kombination.
Fokus auf praktische Anwendungen für Stadtplanung und GIS-Analyse.

Antworte in folgendem Format:
QUALITÄT: [2-3 Sätze zur Datenqualität und -vollständigkeit]
EMPFEHLUNGEN: [Nummerierte Liste mit 3-4 Empfehlungen]
"""
        else:
            return """You are an expert in geodata analysis and metadata documentation.

Analyze the following geodata context and create quality assessments and usage recommendations:

Context: {context}

Generate a concise quality assessment and 3-4 concrete usage recommendations for this geodata combination.
Focus on practical applications for urban planning and GIS analysis.

Respond in the following format:
QUALITY: [2-3 sentences about data quality and completeness]
RECOMMENDATIONS: [Numbered list with 3-4 recommendations]
"""

    def _parse_llm_response(self, response: str, language: str) -> dict[str, Any]:
        """Parse LLM response into structured data."""
        enhanced_data: dict[str, Any] = {}

        try:
            lines = response.strip().split("\n")
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith(("QUALITÄT:", "QUALITY:")):
                    current_section = "quality"
                    enhanced_data["quality_assessment"] = {"summary": line.split(":", 1)[1].strip()}
                elif line.startswith(("EMPFEHLUNGEN:", "RECOMMENDATIONS:")):
                    current_section = "recommendations"
                    enhanced_data["usage_recommendations"] = []
                elif current_section == "recommendations" and line:
                    # Parse recommendation items
                    if "usage_recommendations" in enhanced_data:
                        enhanced_data["usage_recommendations"].append(
                            {
                                "category": "General" if language == "en" else "Allgemein",
                                "text": line.lstrip("1234567890.-").strip(),
                            }
                        )

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        return enhanced_data

    def _format_spatial_extent(self, extent: list) -> str:
        """Format spatial extent coordinates for display."""
        if not extent or len(extent) != 4:
            return "Not available"
        return f"[{extent[0]:.3f}, {extent[1]:.3f}, {extent[2]:.3f}, {extent[3]:.3f}]"

    def _format_number(self, value: int | str) -> str:
        """Format numbers with thousands separators."""
        if isinstance(value, int):
            return f"{value:,}".replace(",", ".")
        return str(value)
