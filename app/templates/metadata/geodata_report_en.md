# Geodata Metadata Report: {{ bezirk }}

*Created on {{ creation_date }} | Coordinate System: ETRS89/UTM Zone 33N (EPSG:25833)*

## 📊 Overview

- **District**: {{ bezirk }}
- **Number of Datasets**: {{ dataset_count }}
- **Total Features**: {{ total_features | number_format }}
- **Data Coverage**: {{ coverage_percentage }}%
- **Overall Quality**: {{ overall_quality_score }}

## 📍 Included Datasets

{% for dataset in datasets %}
### {{ dataset.display_name }} ({{ dataset.source }})
{% if dataset.dataset_type == "bezirksgrenzen" %}
*Automatically included for spatial filtering*
{% endif %}

**Description**: {{ dataset.description }}

**Technical Details**:
- Features: {{ dataset.feature_count | number_format }}
- Spatial Extent: {{ dataset.spatial_extent }}
- Update Frequency: {{ dataset.update_frequency }}
- Quality Rating: {{ dataset.quality_score }} ({{ dataset.quality_assessment }})

**Attributes**:
{% for attr in dataset.key_attributes %}
- `{{ attr.name }}`: {{ attr.description }}
{% endfor %}

{% if dataset.usage_notes %}
**Usage Notes**: {{ dataset.usage_notes }}
{% endif %}

---
{% endfor %}

## 🎯 Data Quality and Completeness

{% if quality_assessment %}
{{ quality_assessment.summary }}

**Detailed Assessment**:
- Geometric Validity: {{ quality_assessment.geometry_validity }}%
- Attribute Completeness: {{ quality_assessment.attribute_completeness }}%
- Spatial Coverage: {{ quality_assessment.spatial_coverage }}%

{% if quality_assessment.known_limitations %}
**Known Limitations**:
{% for limitation in quality_assessment.known_limitations %}
- {{ limitation }}
{% endfor %}
{% endif %}
{% endif %}

## 💡 Usage Recommendations

{% if usage_recommendations %}
{% for recommendation in usage_recommendations %}
### {{ recommendation.category }}
{{ recommendation.text }}

{% if recommendation.software_hints %}
**Software Recommendations**: {{ recommendation.software_hints | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}

### Recommended Analysis Combinations
{% if recommended_analyses %}
{% for analysis in recommended_analyses %}
- **{{ analysis.title }}**: {{ analysis.description }}
{% endfor %}
{% else %}
- Spatial analysis using district boundary as reference
- Quality validation through geometry checking
- Attribute analysis depending on dataset type
{% endif %}

## ⚖️ Legal Information and Licenses

{% for dataset in datasets %}
**{{ dataset.display_name }}**:
- License: {{ dataset.license }}
- Source: {{ dataset.source_attribution }}
- Usage Terms: {{ dataset.usage_terms }}

{% endfor %}

### General Terms of Use
- Data must be used under the specified licenses
- Source attribution required for publications
- Additional terms apply for commercial use
- Currency and completeness are not guaranteed

## 📧 Contact and Support

For questions about this dataset or issues, contact:
- **Berlin Geoportal**: https://www.berlin.de/sen/sbw/stadtdaten/geoportal/
- **OpenStreetMap Community**: https://www.openstreetmap.org/

---

*This metadata report was automatically generated with urbanIQ Berlin. 
Last metadata update: {{ creation_date }}*