"""
base_plugin.py — Universal Plugin Interface

Every new domain (Football, Stocks, Tennis) must implement this interface.
The core engine never needs to know what domain it is running.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from core.models.base_event import BaseEvent
from core.generators.base_generator import BaseFeatureGenerator


class BasePlugin(ABC):
    """
    Abstract base that every domain plugin must implement.
    Implementing this interface is ALL that is required to add a new domain.
    """

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """e.g. 'cricket', 'football', 'stocks'"""
        pass

    @property
    @abstractmethod
    def plugin_version(self) -> str:
        """Semantic version string. e.g. '1.0.0'"""
        pass

    @abstractmethod
    def get_feature_generator(self, engine) -> BaseFeatureGenerator:
        """Returns the domain-specific feature generator."""
        pass

    @abstractmethod
    def get_connector(self) -> Any:
        """Returns the domain-specific data connector."""
        pass

    @abstractmethod
    def parse_event(self, raw_data: Dict[str, Any]) -> BaseEvent:
        """Converts raw API/file data into a BaseEvent domain object."""
        pass

    @abstractmethod
    def target_variable(self, event: BaseEvent) -> Optional[int]:
        """
        Returns the training target for this event.
        e.g., 1 if team_a wins, 0 if team_b wins, None if unknown.
        """
        pass

    @abstractmethod
    def validation_rules(self, raw_data: Dict[str, Any]) -> List[str]:
        """
        Returns a list of validation error messages.
        Empty list = data is valid and safe to import.
        """
        pass

    def describe(self) -> Dict[str, str]:
        """Returns a human-readable description of this plugin."""
        return {
            "domain": self.domain_name,
            "version": self.plugin_version,
            "connector": type(self.get_connector()).__name__,
            "feature_generator": type(self.get_feature_generator(None)).__name__,
        }


class PluginRegistry:
    """Global registry of all loaded plugins. Accessed by the core engine."""
    _plugins: Dict[str, BasePlugin] = {}

    @classmethod
    def register(cls, plugin: BasePlugin):
        cls._plugins[plugin.domain_name] = plugin
        import logging
        logging.info(f"Plugin registered: {plugin.domain_name} v{plugin.plugin_version}")

    @classmethod
    def get(cls, domain: str) -> Optional[BasePlugin]:
        return cls._plugins.get(domain)

    @classmethod
    def list_domains(cls) -> List[str]:
        return list(cls._plugins.keys())
