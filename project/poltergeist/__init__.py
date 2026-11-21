#(CS50 final project policy)
"""Poltergeist: haunts a data pipeline with realistic dirty data."""


class DataQualityError(Exception):
    """Raise this from your pipeline to reject bad data loudly and on purpose."""


__all__ = ["DataQualityError"]
