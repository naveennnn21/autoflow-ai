"""TemplateProvider - Reusable code templates."""

class TemplateProvider:
    @staticmethod
    def model_imports() -> str:
        return "import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
"
    @staticmethod
    def schema_imports() -> str:
        return "from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
"
    @staticmethod
    def model_config() -> str:
        return "    model_config = {\"from_attributes\": True}
"
