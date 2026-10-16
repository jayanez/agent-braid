# SPDX-License-Identifier: AGPL-3.0-only
"""Role-aware JSON mapping; backend-only tensors handle explicit missing values."""
from .forecast_data import validate_window,require,integer

def translate_inputs(raw,horizon):
    window=validate_window(raw);integer(horizon);require(horizon in (1,5,10),'unsupported-horizon')
    past={name:channel['values'][:] for name,channel in window['pastCovariates'].items()}
    future={}
    for name,channel in window['knownFutureCovariates'].items():
        require(len(channel['values'])==horizon,'future-covariate-horizon-drift')
        # Known future channels need historical context under the same identity;
        # this v1 narrow interface refuses rather than inventing past values.
        require(name in past,'known-future-context-unavailable')
        future[name]=channel['values'][:]
    return [{'target':[row[:] for row in window['values']],
             'past_covariates':past,'future_covariates':future}]
