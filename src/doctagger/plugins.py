"""Plugin system for DocTagger.

This module provides an extensible plugin architecture that allows users to:
1. Add custom document processors
2. Add custom storage backends
3. Add custom metadata extractors
4. Add custom LLM providers

Example plugin:
    ```python
    from doctagger.plugins import ProcessorPlugin, register_plugin

    class MyCustomProcessor(ProcessorPlugin):
        name = "my-processor"
        version = "1.0.0"

        def process(self, document, context):
            # Custom processing logic
            return document

    register_plugin(MyCustomProcessor())
    ```
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginMetadata(BaseModel):
    """Metadata for a plugin."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = []


class PluginContext(BaseModel):
    """Context passed to plugins during processing."""

    file_path: Path
    config: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class BasePlugin(ABC):
    """Base class for all plugins."""

    name: str = "base-plugin"
    version: str = "0.0.0"
    description: str = ""
    author: str = ""

    def __init__(self):
        """Initialize plugin."""
        self._enabled = True

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
        )

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the plugin."""
        self._enabled = True
        logger.info(f"Plugin '{self.name}' enabled")

    def disable(self) -> None:
        """Disable the plugin."""
        self._enabled = False
        logger.info(f"Plugin '{self.name}' disabled")

    def on_load(self) -> None:
        """Called when plugin is loaded."""
        pass

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass


class ProcessorPlugin(BasePlugin):
    """Plugin for custom document processing."""

    # Processing priority (lower = earlier)
    priority: int = 100

    @abstractmethod
    def process(
        self, text: str, context: PluginContext
    ) -> tuple[str, Dict[str, Any]]:
        """
        Process document text.

        Args:
            text: Extracted document text
            context: Processing context

        Returns:
            Tuple of (modified_text, additional_metadata)
        """
        pass

    def can_process(self, context: PluginContext) -> bool:
        """
        Check if this plugin can process the document.

        Args:
            context: Processing context

        Returns:
            True if plugin should process this document
        """
        return True


class StoragePlugin(BasePlugin):
    """Plugin for custom storage backends."""

    @abstractmethod
    def save(self, file_path: Path, destination: str, metadata: Dict[str, Any]) -> str:
        """
        Save a file to storage.

        Args:
            file_path: Local file path
            destination: Destination path/key
            metadata: File metadata

        Returns:
            Storage URL or path
        """
        pass

    @abstractmethod
    def load(self, source: str, local_path: Path) -> Path:
        """
        Load a file from storage.

        Args:
            source: Storage URL or path
            local_path: Local destination path

        Returns:
            Local file path
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Storage path

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    def list(self, prefix: str = "") -> List[str]:
        """
        List files in storage.

        Args:
            prefix: Optional path prefix

        Returns:
            List of file paths
        """
        pass


class MetadataExtractorPlugin(BasePlugin):
    """Plugin for custom metadata extraction."""

    @abstractmethod
    def extract(
        self, text: str, context: PluginContext
    ) -> Dict[str, Any]:
        """
        Extract metadata from document.

        Args:
            text: Document text
            context: Processing context

        Returns:
            Extracted metadata dictionary
        """
        pass


class LLMProviderPlugin(BasePlugin):
    """Plugin for custom LLM providers."""

    @abstractmethod
    def generate(
        self, prompt: str, **kwargs
    ) -> str:
        """
        Generate text using the LLM.

        Args:
            prompt: Input prompt
            **kwargs: Additional arguments

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """
        Check if the LLM provider is available.

        Returns:
            True if available
        """
        pass


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self):
        """Initialize registry."""
        self._processors: Dict[str, ProcessorPlugin] = {}
        self._storage: Dict[str, StoragePlugin] = {}
        self._extractors: Dict[str, MetadataExtractorPlugin] = {}
        self._llm_providers: Dict[str, LLMProviderPlugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    def register_processor(self, plugin: ProcessorPlugin) -> None:
        """Register a processor plugin."""
        self._processors[plugin.name] = plugin
        plugin.on_load()
        logger.info(f"Registered processor plugin: {plugin.name} v{plugin.version}")

    def register_storage(self, plugin: StoragePlugin) -> None:
        """Register a storage plugin."""
        self._storage[plugin.name] = plugin
        plugin.on_load()
        logger.info(f"Registered storage plugin: {plugin.name} v{plugin.version}")

    def register_extractor(self, plugin: MetadataExtractorPlugin) -> None:
        """Register a metadata extractor plugin."""
        self._extractors[plugin.name] = plugin
        plugin.on_load()
        logger.info(f"Registered extractor plugin: {plugin.name} v{plugin.version}")

    def register_llm_provider(self, plugin: LLMProviderPlugin) -> None:
        """Register an LLM provider plugin."""
        self._llm_providers[plugin.name] = plugin
        plugin.on_load()
        logger.info(f"Registered LLM provider plugin: {plugin.name} v{plugin.version}")

    def register_hook(self, event: str, callback: Callable) -> None:
        """
        Register a hook callback.

        Args:
            event: Event name (e.g., 'pre_process', 'post_process')
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister(self, plugin_name: str) -> bool:
        """
        Unregister a plugin by name.

        Args:
            plugin_name: Plugin name

        Returns:
            True if unregistered
        """
        for registry in [self._processors, self._storage, self._extractors, self._llm_providers]:
            if plugin_name in registry:
                plugin = registry.pop(plugin_name)
                plugin.on_unload()
                logger.info(f"Unregistered plugin: {plugin_name}")
                return True
        return False

    def get_processors(self) -> List[ProcessorPlugin]:
        """Get all enabled processor plugins sorted by priority."""
        plugins = [p for p in self._processors.values() if p.enabled]
        return sorted(plugins, key=lambda p: p.priority)

    def get_storage(self, name: str) -> Optional[StoragePlugin]:
        """Get a storage plugin by name."""
        return self._storage.get(name)

    def get_extractors(self) -> List[MetadataExtractorPlugin]:
        """Get all enabled extractor plugins."""
        return [p for p in self._extractors.values() if p.enabled]

    def get_llm_provider(self, name: str) -> Optional[LLMProviderPlugin]:
        """Get an LLM provider plugin by name."""
        return self._llm_providers.get(name)

    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """
        Trigger a hook event.

        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            List of callback results
        """
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook callback error for '{event}': {e}")
        return results

    def list_plugins(self) -> Dict[str, List[PluginMetadata]]:
        """List all registered plugins."""
        return {
            "processors": [p.metadata for p in self._processors.values()],
            "storage": [p.metadata for p in self._storage.values()],
            "extractors": [p.metadata for p in self._extractors.values()],
            "llm_providers": [p.metadata for p in self._llm_providers.values()],
        }


# Global plugin registry
_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_plugin(plugin: BasePlugin) -> None:
    """
    Register a plugin with the global registry.

    Args:
        plugin: Plugin instance
    """
    if isinstance(plugin, ProcessorPlugin):
        _registry.register_processor(plugin)
    elif isinstance(plugin, StoragePlugin):
        _registry.register_storage(plugin)
    elif isinstance(plugin, MetadataExtractorPlugin):
        _registry.register_extractor(plugin)
    elif isinstance(plugin, LLMProviderPlugin):
        _registry.register_llm_provider(plugin)
    else:
        raise ValueError(f"Unknown plugin type: {type(plugin)}")


def load_plugins_from_directory(plugins_dir: Path) -> int:
    """
    Load plugins from a directory.

    Args:
        plugins_dir: Directory containing plugin modules

    Returns:
        Number of plugins loaded
    """
    import importlib.util

    count = 0

    if not plugins_dir.exists():
        return count

    for plugin_file in plugins_dir.glob("*.py"):
        if plugin_file.name.startswith("_"):
            continue

        try:
            spec = importlib.util.spec_from_file_location(
                plugin_file.stem, plugin_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for plugin classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr not in [BasePlugin, ProcessorPlugin, StoragePlugin, MetadataExtractorPlugin, LLMProviderPlugin]
                    ):
                        try:
                            plugin_instance = attr()
                            register_plugin(plugin_instance)
                            count += 1
                        except Exception as e:
                            logger.error(f"Failed to instantiate plugin {attr_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_file}: {e}")

    return count
