"""Source connectors: one sub-package per acquisition method (RSS, API, …).

A connector's only job is to fetch items from one external source and return
them as `RawSourceRecord`s. It does not classify, extract or store anything.
"""
