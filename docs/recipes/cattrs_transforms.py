from cattrs import Converter

from corm import Storage
from docs.examples.document_transforms import (
    Member,
    check_transforms,
    export_member,
    load_member,
)

converter = Converter()
converter.register_structure_hook(Member, lambda data, _: load_member(data, Storage()))
converter.register_unstructure_hook(Member, export_member)

if __name__ == "__main__":
    check_transforms(
        lambda data: converter.structure(data, Member), converter.unstructure
    )
