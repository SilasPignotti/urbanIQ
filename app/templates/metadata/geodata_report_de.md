# Geodaten-Metadatenreport: {{ bezirk }}

*Erstellt am {{ creation_date }} | Koordinatensystem: ETRS89/UTM Zone 33N (EPSG:25833)*

## 📊 Übersicht

- **Bezirk**: {{ bezirk }}
- **Anzahl Datensätze**: {{ dataset_count }}
- **Gesamtfeatures**: {{ total_features | number_format }}
- **Datenabdeckung**: {{ coverage_percentage }}%
- **Gesamtqualität**: {{ overall_quality_score }}

## 📍 Enthaltene Datensätze

{% for dataset in datasets %}
### {{ dataset.display_name }} ({{ dataset.source }})
{% if dataset.dataset_type == "bezirksgrenzen" %}
*Automatisch für räumliche Filterung enthalten*
{% endif %}

**Beschreibung**: {{ dataset.description }}

**Technische Details**:
- Features: {{ dataset.feature_count | number_format }}
- Räumliche Ausdehnung: {{ dataset.spatial_extent }}
- Aktualität: {{ dataset.update_frequency }}
- Qualitätsbewertung: {{ dataset.quality_score }} ({{ dataset.quality_assessment }})

**Attribute**:
{% for attr in dataset.key_attributes %}
- `{{ attr.name }}`: {{ attr.description }}
{% endfor %}

{% if dataset.usage_notes %}
**Nutzungshinweise**: {{ dataset.usage_notes }}
{% endif %}

---
{% endfor %}

## 🎯 Datenqualität und Vollständigkeit

{% if quality_assessment %}
{{ quality_assessment.summary }}

**Detailbewertung**:
- Geometrische Validität: {{ quality_assessment.geometry_validity }}%
- Attributvollständigkeit: {{ quality_assessment.attribute_completeness }}%
- Räumliche Abdeckung: {{ quality_assessment.spatial_coverage }}%

{% if quality_assessment.known_limitations %}
**Bekannte Einschränkungen**:
{% for limitation in quality_assessment.known_limitations %}
- {{ limitation }}
{% endfor %}
{% endif %}
{% endif %}

## 💡 Nutzungsempfehlungen

{% if usage_recommendations %}
{% for recommendation in usage_recommendations %}
### {{ recommendation.category }}
{{ recommendation.text }}

{% if recommendation.software_hints %}
**Software-Empfehlungen**: {{ recommendation.software_hints | join(', ') }}
{% endif %}
{% endfor %}
{% endif %}

### Empfohlene Analysekombinationen
{% if recommended_analyses %}
{% for analysis in recommended_analyses %}
- **{{ analysis.title }}**: {{ analysis.description }}
{% endfor %}
{% else %}
- Räumliche Analyse mit Bezirksgrenze als Referenz
- Qualitätsprüfung durch Geometrievalidierung
- Attributanalyse je nach Datensatztyp
{% endif %}

## ⚖️ Rechtliche Hinweise und Lizenzen

{% for dataset in datasets %}
**{{ dataset.display_name }}**:
- Lizenz: {{ dataset.license }}
- Quelle: {{ dataset.source_attribution }}
- Nutzungsbedingungen: {{ dataset.usage_terms }}

{% endfor %}

### Allgemeine Nutzungsbestimmungen
- Daten sind unter den angegebenen Lizenzen zu verwenden
- Quellenangabe bei Veröffentlichungen erforderlich
- Für kommerzielle Nutzung gelten zusätzliche Bestimmungen
- Aktualität und Vollständigkeit werden nicht garantiert

## 📧 Kontakt und Support

Bei Fragen zu diesem Datensatz oder bei Problemen wenden Sie sich an:
- **Berlin Geoportal**: https://www.berlin.de/sen/sbw/stadtdaten/geoportal/
- **OpenStreetMap Community**: https://www.openstreetmap.org/

---

*Dieser Metadatenreport wurde automatisch mit urbanIQ Berlin generiert. 
Letzte Aktualisierung der Metadaten: {{ creation_date }}*