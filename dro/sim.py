"""Leaky integrate-and-fire simulation of the whole graph.

The neuron model follows Shiu et al., "A Drosophila computational brain
model reveals sensorimotor processing", Nature 2024, and is a step-by-step
port of the authors' Brian2 code (``model.py`` in
https://github.com/philshiu/Drosophila_brain_model). Every neuron is
identical; the only thing that differs between neurons is the wiring, which
comes from the connectome.

What one time step does, in the reference's order:

1. Neurons that are not refractory integrate ``v`` and ``g`` exactly over
   one step. Refractory neurons are frozen: neither ``v`` nor ``g`` changes.
2. A non-refractory neuron with ``v`` above the threshold spikes.
3. Spikes sent one synaptic delay ago arrive and add to ``g``. Arrivals are
   not blocked by the refractory period.
4. External input spikes add directly to ``v`` (not to ``g``), so every
   input spike makes its neuron fire once.
5. Neurons that spiked are reset: ``v`` to rest and ``g`` to zero.

Neurons with external input have no refractory period, so they fire at
exactly the input rate.

The only constant that differs from the paper is ``w_synapse_mv``. It is the
paper's single free parameter and was fitted there on the FlyWire dataset;
see ``docs/CALIBRATION_NOTES.md`` for how the value used here was chosen on
MaleCNS.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import sparse


@dataclass(frozen=True)
class Params:
    dt_ms: float = 0.1  # integration step
    v_rest_mv: float = -52.0  # resting and reset potential
    v_threshold_mv: float = -45.0  # spike threshold
    tau_membrane_ms: float = 20.0  # membrane time constant
    tau_synapse_ms: float = 5.0  # synaptic decay time constant
    refractory_ms: float = 2.2  # silent period after a spike
    delay_ms: float = 1.8  # delay between a spike and its effect
    w_synapse_mv: float = 0.10  # effect of one synapse (paper: 0.275 on FlyWire)
    input_weight: float = 250.0  # one input spike equals this many synapses

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Result:
    spike_counts: np.ndarray  # spikes per neuron over the whole run
    spike_times_ms: np.ndarray  # time of every spike
    spike_neurons: np.ndarray  # neuron index of every spike
    duration_ms: float


def simulate(
    weights: sparse.csr_matrix,
    input_rates_hz: np.ndarray,
    duration_ms: float,
    seed: int,
    params: Params = Params(),
) -> Result:
    """Run the network.

    ``input_rates_hz[i]`` is the rate of external Poisson input into neuron
    ``i``; zero means the neuron only hears the rest of the network.
    """
    n = weights.shape[0]
    rng = np.random.default_rng(seed)
    steps = int(round(duration_ms / params.dt_ms))
    delay_steps = max(1, int(round(params.delay_ms / params.dt_ms)))

    v_rest = np.float32(params.v_rest_mv)
    v_threshold = np.float32(params.v_threshold_mv)
    v = np.full(n, v_rest, dtype=np.float32)
    g = np.zeros(n, dtype=np.float32)  # synaptic drive, in mV
    last_spike = np.full(n, -(10**9), dtype=np.int64)  # step of the last spike
    pending = np.zeros((delay_steps, n), dtype=np.float32)  # delayed arrivals
    counts = np.zeros(n, dtype=np.int32)

    driven = np.flatnonzero(input_rates_hz > 0)
    spike_probability = input_rates_hz[driven] * params.dt_ms / 1000.0
    input_kick = np.float32(params.w_synapse_mv * params.input_weight)
    synapse_kick = np.float32(params.w_synapse_mv)

    refractory_steps = np.full(n, int(round(params.refractory_ms / params.dt_ms)), dtype=np.int64)
    refractory_steps[driven] = 0

    # Exact solution of dv/dt = (v_rest - v + g) / tau_m, dg/dt = -g / tau_s
    # over one step.
    keep_v = np.float32(np.exp(-params.dt_ms / params.tau_membrane_ms))
    keep_g = np.float32(np.exp(-params.dt_ms / params.tau_synapse_ms))
    g_to_v = np.float32(
        params.tau_synapse_ms
        / (params.tau_synapse_ms - params.tau_membrane_ms)
        * (float(keep_g) - float(keep_v))
    )
    indptr, indices, data = weights.indptr, weights.indices, weights.data

    # Only neurons that have ever received input need updating: a neuron at
    # rest with no input stays exactly at rest. ``awake`` lists them.
    is_awake = np.zeros(n, dtype=bool)
    is_awake[driven] = True
    awake = driven.copy()

    times, who = [], []
    for step in range(steps):
        slot = step % delay_steps

        v_awake, g_awake = v[awake], g[awake]
        active = (step - last_spike[awake]) >= refractory_steps[awake]
        v_awake = np.where(active, v_rest + (v_awake - v_rest) * keep_v + g_awake * g_to_v, v_awake)
        g_awake = np.where(active, g_awake * keep_g, g_awake)

        fired = awake[active & (v_awake > v_threshold)]

        g_awake += pending[slot, awake]
        pending[slot, awake] = 0.0
        v[awake], g[awake] = v_awake, g_awake

        if driven.size:
            hits = rng.random(driven.size) < spike_probability
            v[driven[hits]] += input_kick

        if fired.size:
            v[fired] = v_rest
            g[fired] = 0.0
            last_spike[fired] = step
            counts[fired] += 1
            times.append(np.full(fired.size, step * params.dt_ms, dtype=np.float32))
            who.append(fired.astype(np.int32))
            # Send each spike to its targets. ``slot`` was just emptied, so
            # it is the arrival slot one full delay from now.
            if fired.size > 40:
                arriving = np.asarray(weights[fired].sum(axis=0)).ravel()
                pending[slot] += synapse_kick * arriving
                targets = np.flatnonzero(arriving)
            else:
                reached = []
                for neuron in fired:
                    start, stop = indptr[neuron], indptr[neuron + 1]
                    pending[slot, indices[start:stop]] += synapse_kick * data[start:stop]
                    reached.append(indices[start:stop])
                targets = np.concatenate(reached)
            new = targets[~is_awake[targets]]
            if new.size:
                is_awake[new] = True
                awake = np.flatnonzero(is_awake)

    return Result(
        spike_counts=counts,
        spike_times_ms=np.concatenate(times) if times else np.zeros(0, np.float32),
        spike_neurons=np.concatenate(who) if who else np.zeros(0, np.int32),
        duration_ms=duration_ms,
    )
