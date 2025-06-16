"""
Common elements for XLabel format converters, like custom exceptions and shared constants.
"""
import logging

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class XLabelError(Exception):
    """Base class for exceptions related to XLabel processing."""
    pass

class XLabelFormatError(XLabelError):
    """Exception raised for errors in the XLabel data format or structure."""
    pass

class XLabelConversionError(XLabelError):
    """Exception for errors during format conversion."""
    pass

# --- Shared Constants ---
# Version of the "refined metadata" structure that the converters expect as input
# or produce as output when converting from/to external formats.
REFINED_METADATA_VERSION = "0.1.0" 