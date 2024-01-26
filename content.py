REGISTRY = [
    {
        "name": "TesseractLanguageModel",
        "plural_name": "Tesseract Language Models",
        "fields": [
            {
                "name": "name",
                "label": "Name",
                "indexed": False,
                "unique": False,
                "multiple": False,
                "in_lists": True,
                "type": "text",
                "choices": [],
                "cross_reference_type": "",
                "has_intensity": False,
                "language": "english",
                "autocomplete": False,
                "synonym_file": None,
                "indexed_with": [],
                "unique_with": [],
                "stats": {},
                "inherited": False
            },
            {
                "name": "code",
                "label": "Code",
                "indexed": False,
                "unique": False,
                "multiple": False,
                "in_lists": True,
                "type": "keyword",
                "choices": [],
                "cross_reference_type": "",
                "has_intensity": False,
                "language": None,
                "autocomplete": False,
                "synonym_file": None,
                "indexed_with": [],
                "unique_with": [],
                "stats": {},
                "inherited": False
            },
            {
                "name": "base_model",
                "label": "Base Model",
                "indexed": False,
                "unique": False,
                "multiple": False,
                "in_lists": True,
                "type": "cross_reference",
                "choices": [],
                "cross_reference_type": "TesseractLanguageModel",
                "has_intensity": False,
                "language": None,
                "autocomplete": False,
                "synonym_file": None,
                "indexed_with": [],
                "unique_with": [],
                "stats": {},
                "inherited": False
            },
            {
                "name": "pages_trained",
                "label": "Pages Trained",
                "indexed": False,
                "unique": False,
                "multiple": False,
                "in_lists": True,
                "type": "number",
                "choices": [],
                "cross_reference_type": "",
                "has_intensity": False,
                "language": None,
                "autocomplete": False,
                "synonym_file": None,
                "indexed_with": [],
                "unique_with": [],
                "stats": {},
                "inherited": False
            }
        ],
        "show_in_nav": True,
        "autocomplete_labels": False,
        "proxy_field": "",
        "templates": {
            "Label": {
                "template": "{{ TesseractLanguageModel.name }}",
                "mime_type": "text/html"
            }
        },
        "view_widget_url": None,
        "edit_widget_url": None,
        "inherited_from_module": None,
        "inherited_from_class": None,
        "base_mongo_indexes": None,
        "has_file_field": False,
        "invalid_field_names": [
            "corpus_id",
            "content_type",
            "last_updated",
            "provenance",
            "field_intensities",
            "path",
            "label",
            "uri"
        ]
    }
]