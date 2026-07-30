"""Models Generator - Generates SQLAlchemy models from MetadataModel.

Consumes the metadata layer (entity YAMLs) and produces production-ready
SQLAlchemy 2.0 models with relationships, indexes, constraints, enums,
UUID PKs, multi-tenancy, timestamps, and soft-delete.
"""

from typing import Dict, List, Optional, Set

from scripts.generators.common.intermediate_model import (
    EntityDef, FieldDef, MetadataModel, RelationshipDef,
)
from scripts.generators.common.metadata_loader import MetadataLoader
from scripts.generators.common.writer import FileWriter

# ---------------------------------------------------------------------------
# SQLAlchemy type mapping: IntermediateModel type -> SQLAlchemy column string
# ---------------------------------------------------------------------------

SA_TYPE = {
    'uuid':    'UUID(as_uuid=True)',
    'string':  'String({maxlen})',
    'text':    'Text',
    'int':     'Integer',
    'float':   'Float',
    'bool':    'Boolean',
    'datetime':'DateTime(timezone=True)',
    'json':    'JSON',
    'enum':    'Enum({enum_class})',
}

# Deduced import sets
SA_IMPORTS: Dict[str, str] = {
    'UUID': 'from sqlalchemy.dialects.postgresql import UUID',
}
SA_TYPES: Dict[str, str] = {
    'String': 'String', 'Text': 'Text', 'Integer': 'Integer',
    'Float': 'Float', 'Boolean': 'Boolean', 'DateTime': 'DateTime',
    'JSON': 'JSON', 'Enum': 'Enum', 'ForeignKey': 'ForeignKey',
    'Index': 'Index', 'UniqueConstraint': 'UniqueConstraint',
}

# ---------------------------------------------------------------------------
# Table name lookup cache
# ---------------------------------------------------------------------------

def _build_table_map(model: MetadataModel) -> Dict[str, str]:
    """Map Entity name -> table name."""
    return {n: e.table for n, e in model.entities.items()}

# ---------------------------------------------------------------------------
# Enum generation
# ---------------------------------------------------------------------------

def _collect_enums(model: MetadataModel) -> Dict[str, tuple]:
    """Collect all unique enums across entities. Returns {EnumClassName: (values,)}."""
    enums: Dict[str, tuple] = {}
    for entity in model.entities.values():
        for field in entity.fields.values():
            if field.type == 'enum' and field.enum_values:
                key = field.enum_name or field.name.capitalize()
                if key not in enums:
                    enums[key] = tuple(field.enum_values)
    return enums


def _generate_enums_content(enums: Dict[str, tuple]) -> List[str]:
    """Generate the shared enums.py file content."""
    lines = [
        '"""AutoFlow AI - Shared SQLAlchemy enums."""',
        'import enum',
        '',
    ]
    for ename in sorted(enums):
        values = enums[ename]
        lines.append(f'class {ename}(str, enum.Enum):')
        for v in values:
            lines.append(f'    {v.upper()} = "{v}"')
        lines.append('')
    return lines


def _enum_imports_for_entity(entity: EntityDef, all_enums: Dict[str, tuple]) -> Set[str]:
    """Return set of enum class names this entity needs to import from enums.py."""
    needed: Set[str] = set()
    for field in entity.fields.values():
        if field.type == 'enum' and field.enum_name:
            needed.add(field.enum_name)
    return needed

# ---------------------------------------------------------------------------
# Column generation
# Column default generation


def _column_default(field: FieldDef) -> str:
    """Generate the default value string for a column."""

    # Timestamp auto-fields: created_at, updated_at, deleted_at
    if field.name == 'created_at' and field.type == 'datetime':
        return ', default=lambda: datetime.now(timezone.utc)'
    if field.name == 'updated_at' and field.type == 'datetime':
        return ', default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)'
    if field.name == 'deleted_at' and field.type == 'datetime':
        return ''

    if field.default == 'uuid.uuid4':
        return ', default=uuid.uuid4'
    if isinstance(field.default, str) and field.default.startswith('uuid.'):
        return f', default={field.default}'
    # Enum defaults
    if field.type == 'enum' and field.enum_values and field.default is not None:
        en = field.enum_name or field.name.capitalize()
        return f', default={en}.{str(field.default).upper()}'
    if field.type == 'enum' and field.enum_values and field.default is None and not field.nullable:
        # First enum value as default
        en = field.enum_name or field.name.capitalize()
        return f', default={en}.{field.enum_values[0].upper()}'
    if isinstance(field.default, bool):
        return f', default={str(field.default).lower()}'
    if isinstance(field.default, int):
        return f', default={field.default}'
    if isinstance(field.default, float):
        return f', default={field.default}'
    if field.default is not None:
        return f', default="{field.default}"'
    return ''


def _column_type_str(field: FieldDef) -> str:
    """Generate the column type string."""
    if field.type == 'uuid':
        t = 'UUID(as_uuid=True)'
    elif field.type == 'string':
        maxlen = field.max_length or 255
        t = f'String({maxlen})'
    elif field.type == 'enum':
        en = field.enum_name or field.name.capitalize()
        t = f'Enum({en})'
    else:
        t = SA_TYPE.get(field.type, 'String(255)')
    return t


def _column_options(field: FieldDef) -> str:
    """Generate column constraint/option string (nullable, unique, index, primary_key)."""
    opts = []
    if field.primary_key:
        opts.append('primary_key=True')
    else:
        # nullable: default is True in metadata; SQLAlchemy default is True too
        if not field.nullable:
            opts.append('nullable=False')
    if field.unique:
        opts.append('unique=True')
    if field.indexed:
        opts.append('index=True')
    return ', '.join(opts)


def _fk_column_str(field: FieldDef, table_map: Dict[str, str]) -> str:
    """Generate a ForeignKey column definition."""
    target_entity = field.foreign_key
    target_table = table_map.get(target_entity, target_entity.lower() + 's')
    nn = '' if field.nullable else ', nullable=False'
    idx = ', index=True' if field.indexed else ''
    return f'UUID(as_uuid=True), ForeignKey("{target_table}.id", ondelete="CASCADE"){nn}{idx}'


def _field_to_column(field: FieldDef, table_map: Dict[str, str]) -> str:
    """Convert a FieldDef to a SQLAlchemy column assignment."""
    name = field.name
    default_str = _column_default(field)

    if field.primary_key:
        return f'    {name} = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)'

    if field.foreign_key:
        fk_part = _fk_column_str(field, table_map)
        return f'    {name} = mapped_column({fk_part}{default_str})'

    col_type = _column_type_str(field)
    opts = _column_options(field)
    if opts:
        return f'    {name} = mapped_column({col_type}, {opts}{default_str})'
    if default_str:
        return f'    {name} = mapped_column({col_type}{default_str})'
    return f'    {name} = mapped_column({col_type})'


# ---------------------------------------------------------------------------
# Relationship generation
# ---------------------------------------------------------------------------

def _relationship_to_str(rel: RelationshipDef) -> str:
    """Convert a RelationshipDef to a SQLAlchemy relationship assignment."""
    target = rel.target
    bp = rel.back_populates
    cascade = rel.cascade if rel.type in ('one_to_many', 'one_to_one') else ''

    parts = [f'relationship("{target}"']
    if bp:
        parts.append(f'back_populates="{bp}"')
    if cascade:
        parts.append(f'cascade="{cascade}"')
    if rel.type == 'one_to_one':
        parts.append('uselist=False')
    parts[-1] += ')'  # close relationship(
    return f'    {rel.name} = {", ".join(parts)}'


# ---------------------------------------------------------------------------
# __table_args__ generation
# ---------------------------------------------------------------------------

def _table_args_for_entity(entity: EntityDef) -> List[str]:
    """Generate __table_args__ entries for indexes and constraints."""
    args = []
    for idx in entity.indexes:
        cols = ', '.join(f'"{c}"' for c in idx.columns)
        uniq = ', unique=True' if idx.unique else ''
        args.append(f'Index("{idx.name}", {cols}{uniq})')
    for con in entity.constraints:
        cols = ', '.join(f'"{c}"' for c in con.columns)
        if con.type == 'unique':
            args.append(f'UniqueConstraint({cols}, name="{con.name}")')
        elif con.type == 'check':
            args.append(f'CheckConstraint({cols}, name="{con.name}")')
    return args


# ---------------------------------------------------------------------------
# Full file generation
# ---------------------------------------------------------------------------

def _needed_imports(entity: EntityDef) -> Dict[str, bool]:
    """Determine which SQLAlchemy imports are needed for this entity."""
    needs: Dict[str, bool] = {
        'String': False, 'Text': False, 'Integer': False, 'Float': False,
        'Boolean': False, 'DateTime': False, 'JSON': False, 'Enum': False,
        'ForeignKey': False, 'Index': False, 'UniqueConstraint': False,
    }

    for field in entity.fields.values():
        t = field.type
        if t == 'string': needs['String'] = True
        elif t == 'text': needs['Text'] = True
        elif t == 'int': needs['Integer'] = True
        elif t == 'float': needs['Float'] = True
        elif t == 'bool': needs['Boolean'] = True
        elif t == 'datetime': needs['DateTime'] = True
        elif t == 'json': needs['JSON'] = True
        elif t == 'enum': needs['Enum'] = True

        if field.foreign_key:
            needs['ForeignKey'] = True

    for rel in entity.relationships.values():
        if rel.type in ('many_to_one', 'one_to_one'):
            needs['ForeignKey'] = True

    for idx in entity.indexes:
        needs['Index'] = True
    for con in entity.constraints:
        if con.type == 'unique':
            needs['UniqueConstraint'] = True

    return needs


def _build_sa_imports(entity: EntityDef) -> List[str]:
    """Build the SQLAlchemy import line based on needed types."""
    needs = _needed_imports(entity)
    needed_types = [t for t, needed in sorted(needs.items()) if needed]
    if not needed_types:
        return []
    return [f'from sqlalchemy import {", ".join(needed_types)}']


def _build_file_content(entity: EntityDef, table_map: Dict[str, str],
                        all_enums: Dict[str, tuple]) -> str:
    """Build the complete model file content for one entity."""
    lines: List[str] = []

    # Docstring
    lines.append('"""AutoFlow AI - SQLAlchemy model."""')

    # Imports
    sa_imports = _build_sa_imports(entity)
    for imp in sa_imports:
        lines.append(imp)

    # Always needed imports
    lines.append('import uuid')
    lines.append('from datetime import datetime, timezone')
    lines.append('from typing import Any, Dict, List, Optional')
    lines.append('from sqlalchemy.dialects.postgresql import UUID')
    lines.append('from sqlalchemy.orm import Mapped, mapped_column, relationship')
    lines.append('from app.core.database import Base')
    lines.append('import enum')

    # Enum imports from enums.py
    enum_imports = _enum_imports_for_entity(entity, all_enums)
    if enum_imports:
        names = ', '.join(sorted(enum_imports))
        lines.append(f'from app.models.enums import {names}')

    # Enums local to this entity (if any, that aren't shared)
    # We only put non-shared enums here -- shared ones are in enums.py
    local_enums: Dict[str, tuple] = {}
    for field in entity.fields.values():
        if field.type == 'enum' and field.enum_values:
            en = field.enum_name or field.name.capitalize()
            if en not in all_enums:
                local_enums[en] = tuple(field.enum_values)

    lines.append('')
    for ename in sorted(local_enums):
        values = local_enums[ename]
        lines.append(f'class {ename}(str, enum.Enum):')
        for v in values:
            lines.append(f'    {v.upper()} = "{v}"')
        lines.append('')

    # Model class
    lines.append('')
    lines.append(f'class {entity.name}(Base):')
    lines.append(f'    __tablename__ = "{entity.table}"')

    # __table_args__
    table_args = _table_args_for_entity(entity)
    if table_args:
        args_joined = ', '.join(table_args)
        lines.append(f'    __table_args__ = ({args_joined},)')
    lines.append('')

    # Add auto-id field first (not in YAML, generated from uuid flag)
    if entity.uuid:
        lines.append(f'    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)')

    # Auto-create FK columns from many_to_one relationships
    auto_fk_names: Set[str] = set()
    for rel_name, rel in entity.relationships.items():
        if rel.type in ('many_to_one', 'one_to_one'):
            fk_name = f'{rel_name}_id'
            if fk_name not in entity.fields:
                fk_field = FieldDef(
                    name=fk_name, type='uuid',
                    foreign_key=rel.target,
                    nullable=True, indexed=True,
                )
                lines.append(_field_to_column(fk_field, table_map))
                auto_fk_names.add(fk_name)
    auto_fk_names.add('id')  # id is handled by uuid flag

    # Regular columns (skipping auto-generated FK fields)
    for fname, field in entity.fields.items():
        if field.primary_key or fname in auto_fk_names:
            continue
        lines.append(_field_to_column(field, table_map))

    # Relationships
    for rname, rel in entity.relationships.items():
        lines.append(_relationship_to_str(rel))

    lines.append('')
    return '\n'.join(lines)


def _to_snake_case(name: str) -> str:
    """Convert PascalCase to snake_case, handling acronyms.
    APIKey -> api_key, OAuthToken -> oauth_token, OrganizationMember -> organization_member
    """
    import re
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    # Handle consecutive uppercase acronymes: APIToken -> API_Token
    s2 = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1_\2', s1)
    return s2.lower()


def _build_init_content(entities: List[EntityDef]) -> str:
    """Generate __init__.py that re-exports all models and the enums module."""
    lines: List[str] = []
    lines.append('"""AutoFlow AI - SQLAlchemy models."""')
    lines.append('')

    # Enums are imported directly by each model file; __init__ doesn't re-export them

    # Import each model
    entity_names = sorted(e.name for e in entities)
    for ename in entity_names:
        module = _to_snake_case(ename)
        lines.append(f'from app.models.{module} import {ename}')

    lines.append('')
    lines.append('')
    lines.append('__all__ = [')
    for ename in entity_names:
        lines.append(f'    "{ename}",')
    lines.append(']')
    lines.append('')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Generator class
# ---------------------------------------------------------------------------

class ModelsGenerator:
    """Generates all SQLAlchemy model files from metadata entities."""

    def __init__(self, writer: Optional[FileWriter] = None):
        self.writer = writer
        self.loader = MetadataLoader()

    def generate(self, writer: Optional[FileWriter] = None,
                 force: bool = False) -> List[str]:
        """Generate all model files from metadata. Main entry point."""
        model = self.loader.load_all()
        return self.generate_from_metadata(model, writer or self.writer, force)

    def generate_from_metadata(self, model: MetadataModel,
                               writer: FileWriter,
                               force: bool = False) -> List[str]:
        """Generate model files from a MetadataModel instance."""
        results: List[str] = []
        table_map = _build_table_map(model)
        all_enums = _collect_enums(model)

        # 1. Generate shared enums.py
        enums_content = _generate_enums_content(all_enums)
        writer.write('backend/app/models/enums.py',
                     '\n'.join(enums_content), force=force)
        results.append('backend/app/models/enums.py')

        # 2. Generate one model file per entity (in dependency order)
        entities = model.sorted_entities()
        for entity in entities:
            content = _build_file_content(entity, table_map, all_enums)
            module_name = entity.table.rstrip('s')  # approximate module name
            # Better: use entity name to determine file name
            fname = self._entity_filename(entity)
            path = f'backend/app/models/{fname}'
            writer.write(path, content, force=force)
            results.append(path)

        # 3. Generate __init__.py
        init_content = _build_init_content(entities)
        writer.write('backend/app/models/__init__.py',
                     init_content, force=force)
        results.append('backend/app/models/__init__.py')

        return results

    @staticmethod
    def _entity_filename(entity: EntityDef) -> str:
        """Convert entity name to filename."""
        return _to_snake_case(entity.name) + '.py'
