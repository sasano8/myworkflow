"""A root lists independent requirement catalogs; each catalog is its namespace."""
from dataclasses import dataclass
import re

from myworkflow.contracts.errors import ContractError
from myworkflow.contracts.models import ContractCatalog, Workflow


@dataclass(frozen=True)
class RootCatalog:
    id: str
    name: str
    catalogs: tuple[ContractCatalog, ...]

    def validate(self) -> None:
        if (not isinstance(self.id, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', self.id)
                or not isinstance(self.name, str) or not self.name.strip()):
            raise ContractError('Root catalog requires a valid ID and nonempty name')
        if not isinstance(self.catalogs, tuple) or any(not isinstance(c, ContractCatalog) for c in self.catalogs):
            raise ContractError('catalogs: expected a tuple of ContractCatalog')
        seen = set()
        for catalog in self.catalogs:
            if not catalog.id:
                raise ContractError(f'{self.id}: child catalog requires an ID and name')
            try:
                catalog.validate()
            except ValueError as exc:
                raise ContractError(f'{self.id}/{catalog.id}: {exc}') from exc
            if catalog.id in seen:
                raise ContractError(f'{self.id}: duplicate catalog {catalog.id}')
            seen.add(catalog.id)

    def catalog(self, catalog_id: str) -> ContractCatalog:
        self.validate()
        for catalog in self.catalogs:
            if catalog.id == catalog_id:
                return catalog
        raise ContractError(f'{self.id}: unknown catalog {catalog_id}')

    def workflow(self, catalog_id: str, workflow_id: str) -> Workflow:
        for workflow in self.catalog(catalog_id).workflows:
            if workflow.id == workflow_id:
                return workflow
        raise ContractError(f'{self.id}/{catalog_id}: unknown workflow {workflow_id}')
