import warnings

DEPRECIATION_WARNING = """
Brokers support would be removed from version 0.7.0
Use omspy for live order placement with brokers
"""
warnings.warn(DEPRECIATION_WARNING, DeprecationWarning, stacklevel=2)
