"""Shared YAML utilities for ITBench scripts."""
import yaml

class IndentedSafeDumper(yaml.SafeDumper):
    """SafeDumper that always indents list items, avoiding the compact
    ``- value`` style that PyYAML produces by default for nested lists."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow=flow, indentless=False)
