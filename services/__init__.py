"""REI processing stages. Each sub-package is one stage of the pipeline:

ingestion -> extraction -> geo_resolution -> confidence -> qc -> lifecycle -> publishing

They are plain Python modules in one process for now; the boundaries are kept
clean so a stage can become its own service when scale requires it.
"""
