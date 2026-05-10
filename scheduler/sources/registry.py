from scheduler.sources.taf_tx import TAFTXSource
from scheduler.sources.ecmwf import ECMWFSource
from scheduler.sources.gfs_kma import GFSSource, KMASource
from scheduler.sources.base import TempSource

SOURCE_REGISTRY: dict[str, TempSource] = {
    "TAF_TX": TAFTXSource(),
    "ECMWF":  ECMWFSource(),
    "GFS":    GFSSource(),
    "KMA":    KMASource(),
}