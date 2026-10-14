# PDF connectors — not implemented yet

For sources that publish documents, such as traffic advisories and press
notes issued as PDF files. Same contract as every connector: implement
`SourceConnector` (`connectors/base.py`) and return `RawSourceRecord`s.
