"""
Public package entrypoint that exposes the backend app factory while the web
package is being refactored into dedicated backend/frontend subpackages.
"""

from .backend import create_app  # re-export for backwards compatibility

__all__ = ["create_app"]
