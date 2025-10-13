"""
Data models for AssetFlow
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict


@dataclass
class Position:
    """Investment position model"""
    id: Optional[int] = None
    name: str = ""
    value: float = 0.0
    main_category: str = ""
    sub_category: str = ""
    custom_label: Optional[str] = None
    sub_label: Optional[str] = None  # For sub-classification within custom_label
    date: datetime = None
    invested_value: Optional[float] = None
    percentage: Optional[float] = None
    quantity: Optional[int] = None
    additional_info: Optional[str] = None  # JSON string

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'value': self.value,
            'main_category': self.main_category,
            'sub_category': self.sub_category,
            'custom_label': self.custom_label,
            'sub_label': self.sub_label,
            'date': self.date.isoformat() if self.date else None,
            'invested_value': self.invested_value,
            'percentage': self.percentage,
            'quantity': self.quantity,
            'additional_info': self.additional_info
        }


@dataclass
class AssetMapping:
    """Maps asset names to custom labels"""
    id: Optional[int] = None
    asset_name: str = ""
    custom_label: str = ""
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class TargetAllocation:
    """Target allocation percentages for custom labels"""
    id: Optional[int] = None
    custom_label: str = ""
    target_percentage: float = 0.0
    created_at: datetime = None
    updated_at: datetime = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'custom_label': self.custom_label,
            'target_percentage': self.target_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class SubLabelMapping:
    """Maps assets within a custom_label to sub_labels"""
    id: Optional[int] = None
    asset_name: str = ""
    parent_label: str = ""  # The custom_label (e.g., "Previdencia")
    sub_label: str = ""  # The sub-classification
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class SubLabelTarget:
    """Target allocation for sub-labels within a parent label"""
    id: Optional[int] = None
    parent_label: str = ""  # The custom_label (e.g., "Previdencia")
    sub_label: str = ""
    target_percentage: float = 0.0  # Percentage within the parent category
    created_at: datetime = None
    updated_at: datetime = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'parent_label': self.parent_label,
            'sub_label': self.sub_label,
            'target_percentage': self.target_percentage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
