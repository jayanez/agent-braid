# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded caller-owned numerical cache, with copied values and complete keys."""
from collections import OrderedDict
from copy import deepcopy
from .forecast_data import digest,integer

class ForecastCache:
    def __init__(self,capacity=32):
        self.capacity=integer(capacity,1,32);self.records=OrderedDict()

    def key(self,request,artifact_digest):return digest({'request':request,'artifactDigest':artifact_digest})

    def get(self,key):
        value=self.records.get(key)
        if value is not None:self.records.move_to_end(key)
        return deepcopy(value)

    def put(self,key,value):
        self.records[key]=deepcopy(value);self.records.move_to_end(key)
        while len(self.records)>self.capacity:self.records.popitem(last=False)

    def clear(self):self.records.clear()
