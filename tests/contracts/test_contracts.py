"""Formal published contracts, separate from the dependency-free tool suite.

Install the optional [contracts] extra to run these checks.
"""

import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator
from openapi_spec_validator import OpenAPIV31SpecValidator

from subtitle_translator.project.service import ProjectService


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs/schemas/tool-v1.schema.json"
OPENAPI_PATH = ROOT / "docs/schemas/tool-v1.openapi.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validator(definition):
    return Draft202012Validator({"$defs": SCHEMA["$defs"], "$ref": "#/$defs/" + definition})


class ContractTests(unittest.TestCase):
    def test_json_schema_and_openapi_are_valid_standard_documents(self):
        Draft202012Validator.check_schema(SCHEMA)
        document = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        OpenAPIV31SpecValidator(document, base_uri=OPENAPI_PATH.as_uri()).validate()

    def test_runtime_capabilities_match_the_published_contract(self):
        # No workspace or database is created by capabilities discovery.
        data = ProjectService(ROOT / "temp/contract-capabilities").capabilities()
        validator("Capabilities").validate(data)

    def test_persisted_partial_entry_matches_public_entry_contract(self):
        location = ROOT / "temp/contract-tests"
        location.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=location) as directory:
            path = Path(directory)
            source = path / "source.srt"
            source.write_text("7\n00:00:01,001 --> 00:00:02,777\nHello!\n", encoding="utf-8")
            service = ProjectService(path / "workspace")
            project = service.import_project(source)["project"]
            entry = service.list_entries(project["project_id"])["items"][0]
            validator("Entry").validate(entry)
            changed = service.edit_entry({"project_id": project["project_id"], "entry_id": entry["entry_id"],
                                "expected_project_revision": 1, "changes": {"target_text": "Félkész"}})
            validator("PublicEntry").validate(changed["entry"])
            reopened = ProjectService(path / "workspace").list_entries(project["project_id"])["items"][0]
            self.assertEqual(reopened["target"]["state"], "draft")
            validator("Entry").validate(reopened)


if __name__ == "__main__":
    unittest.main()
