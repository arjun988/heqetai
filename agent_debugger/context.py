"""
Context management for AgentDebugger.
Provides advanced context engineering and management capabilities.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class ContextType(Enum):
    """Types of context that can be managed"""

    MEMORY = "memory"
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"
    TASK = "task"
    ENVIRONMENT = "environment"
    USER_PREFERENCE = "user_preference"
    SYSTEM_STATE = "system_state"


class ContextPriority(Enum):
    """Priority levels for context items"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVE = "archive"


@dataclass
class ContextItem:
    """Represents a single context item"""

    id: str
    type: ContextType
    key: str
    value: Any
    priority: ContextPriority
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    agent_id: Optional[str] = None
    step_id: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

    def is_expired(self) -> bool:
        """Check if this context item has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to their string values
        data["type"] = self.type.value
        data["priority"] = self.priority.value
        # Convert datetime objects to ISO format strings
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        if self.expires_at:
            data["expires_at"] = self.expires_at.isoformat()
        return data


class ContextManager:
    """Advanced context management system for agents"""

    def __init__(self, max_context_items: int = 10000, auto_cleanup: bool = True):
        self.max_context_items = max_context_items
        self.auto_cleanup = auto_cleanup
        self.context_items: Dict[str, ContextItem] = {}
        self.context_index: Dict[str, Set[str]] = {}  # key -> set of context item IDs
        self.type_index: Dict[ContextType, Set[str]] = (
            {}
        )  # type -> set of context item IDs
        self.agent_index: Dict[str, Set[str]] = (
            {}
        )  # agent_id -> set of context item IDs
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> set of context item IDs
        self.priority_queues: Dict[ContextPriority, List[str]] = {
            priority: [] for priority in ContextPriority
        }

    def add_context(
        self,
        type: ContextType,
        key: str,
        value: Any,
        priority: ContextPriority = ContextPriority.MEDIUM,
        expires_in: Optional[timedelta] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> str:
        """Add a new context item"""

        # Generate unique ID
        context_id = str(uuid.uuid4())

        # Calculate expiration time
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in

        # Create context item
        context_item = ContextItem(
            id=context_id,
            type=type,
            key=key,
            value=value,
            priority=priority,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=expires_at,
            tags=tags or [],
            metadata=metadata or {},
            agent_id=agent_id,
            step_id=step_id,
        )

        # Store the context item
        self.context_items[context_id] = context_item

        # Update indexes
        self._update_indexes(context_item)

        # Auto cleanup if enabled
        if self.auto_cleanup and len(self.context_items) > self.max_context_items:
            self._cleanup_old_items()

        return context_id

    def get_context(self, context_id: str) -> Optional[ContextItem]:
        """Get a context item by ID"""
        return self.context_items.get(context_id)

    def get_contexts_by_key(self, key: str) -> List[ContextItem]:
        """Get all context items with a specific key"""
        context_ids = self.context_index.get(key, set())
        return [
            self.context_items[cid] for cid in context_ids if cid in self.context_items
        ]

    def get_contexts_by_type(self, type: ContextType) -> List[ContextItem]:
        """Get all context items of a specific type"""
        context_ids = self.type_index.get(type, set())
        return [
            self.context_items[cid] for cid in context_ids if cid in self.context_items
        ]

    def get_contexts_by_agent(self, agent_id: str) -> List[ContextItem]:
        """Get all context items for a specific agent"""
        context_ids = self.agent_index.get(agent_id, set())
        return [
            self.context_items[cid] for cid in context_ids if cid in self.context_items
        ]

    def get_contexts_by_tag(self, tag: str) -> List[ContextItem]:
        """Get all context items with a specific tag"""
        context_ids = self.tag_index.get(tag, set())
        return [
            self.context_items[cid] for cid in context_ids if cid in self.context_items
        ]

    def search_contexts(
        self,
        query: str,
        type_filter: Optional[ContextType] = None,
        agent_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
        priority_filter: Optional[List[ContextPriority]] = None,
    ) -> List[ContextItem]:
        """Search context items with various filters"""

        results = []

        for context_item in self.context_items.values():
            # Skip expired items
            if context_item.is_expired():
                continue

            # Apply filters
            if type_filter and context_item.type != type_filter:
                continue

            if agent_filter and context_item.agent_id != agent_filter:
                continue

            if tag_filter and not any(tag in context_item.tags for tag in tag_filter):
                continue

            if priority_filter and context_item.priority not in priority_filter:
                continue

            # Text search in key, value, and tags
            searchable_text = f"{context_item.key} {str(context_item.value)} {' '.join(context_item.tags)}"
            if query.lower() in searchable_text.lower():
                results.append(context_item)

        # Sort by priority and creation time
        results.sort(key=lambda x: (x.priority.value, x.created_at), reverse=True)
        return results

    def update_context(self, context_id: str, **updates) -> bool:
        """Update a context item"""
        if context_id not in self.context_items:
            return False

        context_item = self.context_items[context_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(context_item, key):
                setattr(context_item, key, value)

        context_item.updated_at = datetime.now()

        # Rebuild indexes if needed
        if any(key in ["type", "agent_id", "tags"] for key in updates.keys()):
            self._remove_from_indexes(context_item)
            self._update_indexes(context_item)

        return True

    def delete_context(self, context_id: str) -> bool:
        """Delete a context item"""
        if context_id not in self.context_items:
            return False

        context_item = self.context_items[context_id]
        self._remove_from_indexes(context_item)
        del self.context_items[context_id]
        return True

    def clear_contexts(
        self,
        type_filter: Optional[ContextType] = None,
        agent_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> int:
        """Clear context items with optional filters"""
        to_delete = []

        for context_id, context_item in self.context_items.items():
            if type_filter and context_item.type != type_filter:
                continue

            if agent_filter and context_item.agent_id != agent_filter:
                continue

            if tag_filter and not any(tag in context_item.tags for tag in tag_filter):
                continue

            to_delete.append(context_id)

        for context_id in to_delete:
            self.delete_context(context_id)

        return len(to_delete)

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of all contexts"""
        summary = {
            "total_items": len(self.context_items),
            "by_type": {},
            "by_priority": {},
            "by_agent": {},
            "expired_count": 0,
            "oldest_item": None,
            "newest_item": None,
        }

        oldest_datetime = None
        newest_datetime = None

        for context_item in self.context_items.values():
            # Count by type
            type_name = context_item.type.value
            summary["by_type"][type_name] = summary["by_type"].get(type_name, 0) + 1

            # Count by priority
            priority_name = context_item.priority.value
            summary["by_priority"][priority_name] = (
                summary["by_priority"].get(priority_name, 0) + 1
            )

            # Count by agent
            if context_item.agent_id:
                summary["by_agent"][context_item.agent_id] = (
                    summary["by_agent"].get(context_item.agent_id, 0) + 1
                )

            # Check for expired items
            if context_item.is_expired():
                summary["expired_count"] += 1

            # Track oldest and newest
            if oldest_datetime is None or context_item.created_at < oldest_datetime:
                oldest_datetime = context_item.created_at

            if newest_datetime is None or context_item.created_at > newest_datetime:
                newest_datetime = context_item.created_at

        # Convert to ISO format strings
        if oldest_datetime:
            summary["oldest_item"] = oldest_datetime.isoformat()
        if newest_datetime:
            summary["newest_item"] = newest_datetime.isoformat()

        return summary

    def export_contexts(
        self,
        format: str = "json",
        include_expired: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export contexts in various formats"""
        contexts_to_export = []

        for context_item in self.context_items.values():
            if not include_expired and context_item.is_expired():
                continue

            # Apply filters if provided
            if filters:
                if "type" in filters and context_item.type != filters["type"]:
                    continue
                if (
                    "agent_id" in filters
                    and context_item.agent_id != filters["agent_id"]
                ):
                    continue
                if "tags" in filters and not any(
                    tag in context_item.tags for tag in filters["tags"]
                ):
                    continue

            contexts_to_export.append(context_item.to_dict())

        if format == "json":
            return json.dumps(contexts_to_export, indent=2, default=str)
        elif format == "csv":
            # Simple CSV export
            if not contexts_to_export:
                return ""

            headers = list(contexts_to_export[0].keys())
            csv_lines = [",".join(headers)]

            for context in contexts_to_export:
                row = []
                for header in headers:
                    value = str(context.get(header, "")).replace(",", ";")
                    row.append(f'"{value}"')
                csv_lines.append(",".join(row))

            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def import_contexts(self, data: str, format: str = "json") -> int:
        """Import contexts from various formats"""
        imported_count = 0

        if format == "json":
            contexts_data = json.loads(data)
            for context_data in contexts_data:
                try:
                    # Convert string dates back to datetime objects
                    context_data["created_at"] = datetime.fromisoformat(
                        context_data["created_at"]
                    )
                    context_data["updated_at"] = datetime.fromisoformat(
                        context_data["updated_at"]
                    )
                    if context_data.get("expires_at"):
                        context_data["expires_at"] = datetime.fromisoformat(
                            context_data["expires_at"]
                        )

                    # Convert enum values back
                    context_data["type"] = ContextType(context_data["type"])
                    context_data["priority"] = ContextPriority(context_data["priority"])

                    # Create context item
                    context_item = ContextItem(**context_data)
                    self.context_items[context_item.id] = context_item
                    self._update_indexes(context_item)
                    imported_count += 1

                except Exception as e:
                    print(f"Error importing context: {e}")
                    continue

        return imported_count

    def _update_indexes(self, context_item: ContextItem):
        """Update all indexes for a context item"""
        # Key index
        if context_item.key not in self.context_index:
            self.context_index[context_item.key] = set()
        self.context_index[context_item.key].add(context_item.id)

        # Type index
        if context_item.type not in self.type_index:
            self.type_index[context_item.type] = set()
        self.type_index[context_item.type].add(context_item.id)

        # Agent index
        if context_item.agent_id:
            if context_item.agent_id not in self.agent_index:
                self.agent_index[context_item.agent_id] = set()
            self.agent_index[context_item.agent_id].add(context_item.id)

        # Tag index
        for tag in context_item.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(context_item.id)

        # Priority queue
        self.priority_queues[context_item.priority].append(context_item.id)

    def _remove_from_indexes(self, context_item: ContextItem):
        """Remove a context item from all indexes"""
        # Key index
        if context_item.key in self.context_index:
            self.context_index[context_item.key].discard(context_item.id)
            if not self.context_index[context_item.key]:
                del self.context_index[context_item.key]

        # Type index
        if context_item.type in self.type_index:
            self.type_index[context_item.type].discard(context_item.id)
            if not self.type_index[context_item.type]:
                del self.type_index[context_item.type]

        # Agent index
        if context_item.agent_id and context_item.agent_id in self.agent_index:
            self.agent_index[context_item.agent_id].discard(context_item.id)
            if not self.agent_index[context_item.agent_id]:
                del self.agent_index[context_item.agent_id]

        # Tag index
        for tag in context_item.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(context_item.id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]

        # Priority queue
        if context_item.id in self.priority_queues[context_item.priority]:
            self.priority_queues[context_item.priority].remove(context_item.id)

    def _cleanup_old_items(self):
        """Clean up old context items based on priority and age"""
        # Remove expired items first
        expired_items = [
            cid for cid, item in self.context_items.items() if item.is_expired()
        ]
        for cid in expired_items:
            self.delete_context(cid)

        # If still over limit, remove lowest priority items
        if len(self.context_items) > self.max_context_items:
            items_by_priority = []
            for priority in [
                ContextPriority.ARCHIVE,
                ContextPriority.LOW,
                ContextPriority.MEDIUM,
                ContextPriority.HIGH,
            ]:
                for cid in self.priority_queues[priority]:
                    if cid in self.context_items:
                        items_by_priority.append(
                            (cid, self.context_items[cid].created_at)
                        )

            # Sort by creation time (oldest first)
            items_by_priority.sort(key=lambda x: x[1])

            # Remove oldest items until under limit
            items_to_remove = len(self.context_items) - self.max_context_items
            for cid, _ in items_by_priority[:items_to_remove]:
                self.delete_context(cid)
