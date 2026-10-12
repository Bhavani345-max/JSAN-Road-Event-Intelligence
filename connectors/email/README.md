# Email connectors — not implemented yet

For sources that arrive by email, such as partner notifications sent to a
shared inbox. Same contract as every connector: implement `SourceConnector`
(`connectors/base.py`) and return `RawSourceRecord`s.
