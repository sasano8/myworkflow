from dataclasses import dataclass
from pathlib import Path
from myworkflow.acceptance.gherkin import load_cases
from myworkflow.acceptance.rendering import DocumentOptions
from myworkflow.fingerprints import contract_fingerprint, tree_fingerprint


@dataclass(frozen=True)
class AcceptanceConfig:
    program: object
    definitions: object
    features: tuple[Path, ...]
    root: Path
    sources: tuple[Path, ...]
    documents: DocumentOptions = DocumentOptions()
    registry: object | None = None
    output_directory: Path | None = None
    capabilities: tuple[tuple[str, str], ...] = (('temporal', 'RUN_TEMPORAL_ACCEPTANCE'),)

    def cases(self):
        return load_cases(list(self.features), self.program, self.definitions)

    def implementation_hash(self):
        return tree_fingerprint(self.root, self.sources)

    def contract_hash(self):
        return contract_fingerprint(self.program)
