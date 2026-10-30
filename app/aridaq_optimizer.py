from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math

import networkx as nx


# Coulomb constant in kJ mol^-1 nm e^-2.
# Charges are expressed in elementary-charge units.
COULOMB_K = 138.935456


class ARIDAQError(ValueError):
    """Raised when ARIDAQ receives invalid model inputs."""


@dataclass(frozen=True)
class ARIDAQConfig:
    # Electrostatic screening length, in nanometres.
    debye_length_nm: float = 1.0

    # Strength of the logistic-friction penalty.
    friction_scale: float = 1.0

    # Logistic function steepness and midpoint.
    friction_steepness: float = 10.0
    friction_midpoint: float = 0.5

    # Scale used to combine the two energy pools.
    # Must use the same energy units as the pool energies.
    energy_temperature: float = 1.0

    # Energy reference used to convert edge energies
    # into non-negative route costs.
    energy_reference: float = 0.0

    # Penalty applied to steric conflicts.
    steric_scale: float = 1.0


@dataclass
class EnergyEvaluation:
    low_pool_energy: float
    high_pool_energy: float
    combined_pool_energy: float
    screened_electrostatic_energy: float
    logistic_friction: float
    steric_penalty: float
    total_energy: float


class ARIDAQOptimizer:
    """
    ARIDAQ: energy-informed graph optimization.

    Graph nodes represent molecular or biological states.
    Graph edges represent possible transitions.

    Supported node attributes:
        energy_low: energy of the low-energy state
        energy_high: energy of the high-energy state

    Supported edge attributes:
        distance_nm: separation in nanometres
        charge_i: charge at the first endpoint, in elementary charges
        charge_j: charge at the second endpoint, in elementary charges
        friction: normalized disturbance value, normally in [0, 1]
        steric_penalty: non-negative steric constraint penalty
        transition_energy: additional transition energy

    IMPORTANT:
    Gene-interaction networks do not automatically contain
    molecular distances or charges. Do not invent these values.
    Supply physical attributes only when they are supported
    by appropriate data.
    """

    def __init__(
        self,
        config: ARIDAQConfig | None = None,
    ):
        self.config = config or ARIDAQConfig()
        self._validate_config()

    def _validate_config(self) -> None:
        c = self.config

        if c.debye_length_nm <= 0:
            raise ARIDAQError(
                "Debye length must be positive."
            )

        if c.energy_temperature <= 0:
            raise ARIDAQError(
                "Energy temperature must be positive."
            )

        if c.friction_scale < 0:
            raise ARIDAQError(
                "Friction scale cannot be negative."
            )

        if c.friction_steepness <= 0:
            raise ARIDAQError(
                "Friction steepness must be positive."
            )

        if c.steric_scale < 0:
            raise ARIDAQError(
                "Steric scale cannot be negative."
            )

    @staticmethod
    def _finite(value: Any, name: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ARIDAQError(
                f"{name} must be numeric."
            ) from exc

        if not math.isfinite(number):
            raise ARIDAQError(
                f"{name} must be finite."
            )

        return number

    def screened_coulomb(
        self,
        distance_nm: float,
        charge_i: float,
        charge_j: float,
    ) -> float:
        """
        Debye-screened Coulomb potential:

        U(r) = K * q_i * q_j / r * exp(-r / lambda_D)

        Returns kJ/mol under the stated unit convention.
        """

        r = self._finite(distance_nm, "distance_nm")
        qi = self._finite(charge_i, "charge_i")
        qj = self._finite(charge_j, "charge_j")

        if r <= 0:
            raise ARIDAQError(
                "Distance must be greater than zero."
            )

        return (
            COULOMB_K
            * qi
            * qj
            / r
            * math.exp(
                -r / self.config.debye_length_nm
            )
        )

    def logistic_friction(
        self,
        friction: float,
    ) -> float:
        """
        Logistic disturbance penalty:

        F(x) = scale / (1 + exp(-k * (x - midpoint)))

        The result is bounded between zero and friction_scale.
        """

        x = self._finite(friction, "friction")

        if not 0.0 <= x <= 1.0:
            raise ARIDAQError(
                "Normalized friction must be between 0 and 1."
            )

        z = self.config.friction_steepness * (
            x - self.config.friction_midpoint
        )

        # Stable sigmoid evaluation.
        if z >= 0:
            sigmoid = 1.0 / (1.0 + math.exp(-z))
        else:
            ez = math.exp(z)
            sigmoid = ez / (1.0 + ez)

        return self.config.friction_scale * sigmoid

    def combine_energy_pools(
        self,
        low_energy: float,
        high_energy: float,
    ) -> float:
        """
        Combine low- and high-energy states using a
        two-state log-sum-exp free-energy expression:

        U = -T * log(exp(-E_low/T) + exp(-E_high/T))

        T is an energy scale, not automatically a physical
        temperature unless the units and model justify it.
        """

        low = self._finite(
            low_energy, "low_energy"
        )
        high = self._finite(
            high_energy, "high_energy"
        )

        t = self.config.energy_temperature

        # Numerically stable log-sum-exp calculation.
        minimum = min(low, high)

        return minimum - t * math.log(
            math.exp(-(low - minimum) / t)
            + math.exp(-(high - minimum) / t)
        )

    def evaluate_state(
        self,
        low_energy: float,
        high_energy: float,
        distance_nm: float,
        charge_i: float,
        charge_j: float,
        friction: float = 0.0,
        steric_penalty: float = 0.0,
        transition_energy: float = 0.0,
    ) -> EnergyEvaluation:
        """Evaluate one candidate transition or molecular state."""

        steric = self._finite(
            steric_penalty, "steric_penalty"
        )

        transition = self._finite(
            transition_energy, "transition_energy"
        )

        if steric < 0:
            raise ARIDAQError(
                "Steric penalty cannot be negative."
            )

        pool_energy = self.combine_energy_pools(
            low_energy,
            high_energy,
        )

        electrostatic = self.screened_coulomb(
            distance_nm,
            charge_i,
            charge_j,
        )

        friction_energy = self.logistic_friction(
            friction
        )

        total = (
            pool_energy
            + electrostatic
            + friction_energy
            + self.config.steric_scale * steric
            + transition
        )

        return EnergyEvaluation(
            low_pool_energy=float(low_energy),
            high_pool_energy=float(high_energy),
            combined_pool_energy=pool_energy,
            screened_electrostatic_energy=electrostatic,
            logistic_friction=friction_energy,
            steric_penalty=steric,
            total_energy=total,
        )

    def edge_cost(
        self,
        edge_data: dict[str, Any],
    ) -> float:
        """
        Convert a transition's energy into a non-negative
        search cost for Dijkstra's shortest-path algorithm.
        """

        required = (
            "distance_nm",
            "charge_i",
            "charge_j",
            "energy_low",
            "energy_high",
        )

        missing = [
            key for key in required
            if key not in edge_data
        ]

        if missing:
            raise ARIDAQError(
                "Missing edge attributes: "
                + ", ".join(missing)
            )

        evaluation = self.evaluate_state(
            low_energy=edge_data["energy_low"],
            high_energy=edge_data["energy_high"],
            distance_nm=edge_data["distance_nm"],
            charge_i=edge_data["charge_i"],
            charge_j=edge_data["charge_j"],
            friction=edge_data.get("friction", 0.0),
            steric_penalty=edge_data.get(
                "steric_penalty", 0.0
            ),
            transition_energy=edge_data.get(
                "transition_energy", 0.0
            ),
        )

        # Dijkstra requires non-negative edge costs.
        # This transformation preserves ordering between
        # individual edge energies, but route-level results
        # depend on the chosen energy reference.
        return max(
            0.0,
            evaluation.total_energy
            - self.config.energy_reference,
        )

    def optimize(
        self,
        graph: nx.Graph,
        source: Any,
        target: Any,
    ) -> dict[str, Any]:
        """
        Find the minimum-cost route through a supplied graph.

        This is an energy-informed graph-search baseline.
        It does not, by itself, prove a global molecular
        energy minimum or implement a complete protein-folding
        or molecular-docking simulation.
        """

        if not isinstance(graph, nx.Graph):
            raise ARIDAQError(
                "graph must be a NetworkX graph."
            )

        if source not in graph:
            raise ARIDAQError(
                f"Source node {source!r} is not in the graph."
            )

        if target not in graph:
            raise ARIDAQError(
                f"Target node {target!r} is not in the graph."
            )

        if source == target:
            return {
                "algorithm": "ARIDAQ energy-informed search",
                "source": source,
                "target": target,
                "path": [source],
                "total_cost": 0.0,
                "edge_costs": [],
                "status": "success",
            }

        weighted_graph = nx.DiGraph()

        weighted_graph.add_nodes_from(
            graph.nodes(data=True)
        )

        for u, v, data in graph.edges(data=True):
            cost = self.edge_cost(data)

            weighted_graph.add_edge(
                u,
                v,
                weight=cost,
            )

            if not graph.is_directed():
                weighted_graph.add_edge(
                    v,
                    u,
                    weight=cost,
                )

        try:
            path = nx.dijkstra_path(
                weighted_graph,
                source,
                target,
                weight="weight",
            )

        except nx.NetworkXNoPath as exc:
            raise ARIDAQError(
                "No route connects the selected nodes."
            ) from exc

        edge_costs = [
            weighted_graph[u][v]["weight"]
            for u, v in zip(path[:-1], path[1:])
        ]

        return {
            "algorithm": "ARIDAQ energy-informed search",
            "source": source,
            "target": target,
            "path": path,
            "total_cost": float(sum(edge_costs)),
            "edge_costs": edge_costs,
            "number_of_transitions": len(edge_costs),
            "status": "success",
        }