# AI disclosure (CS50 final project policy): the first draft of this file was generated with
# Claude (Anthropic). Replace this note with a description of what YOU changed or wrote.
"""Poltergeist: haunts a data pipeline with realistic dirty data."""


class DataQualityError(Exception):
    """Raise this from your pipeline to reject bad data loudly and on purpose."""


__all__ = ["DataQualityError"]
