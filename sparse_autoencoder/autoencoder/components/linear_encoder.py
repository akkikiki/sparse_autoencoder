"""Linear encoder layer."""
import math
from typing import final

import einops
from jaxtyping import Float
from pydantic import PositiveInt, validate_call
import torch
from torch import Tensor
from torch.nn import Parameter, ReLU, init

from sparse_autoencoder.autoencoder.components.abstract_encoder import AbstractEncoder
from sparse_autoencoder.autoencoder.types import ResetOptimizerParameterDetails
from sparse_autoencoder.tensor_types import Axis
from sparse_autoencoder.utils.tensor_shape import shape_with_optional_dimensions


@final
class LinearEncoder(AbstractEncoder):
    r"""Linear encoder layer.

    Linear encoder layer (essentially `nn.Linear`, with a ReLU activation function). Designed to be
    used as the encoder in a sparse autoencoder (excluding any outer tied bias).

    $$
    \begin{align*}
        m &= \text{learned features dimension} \\
        n &= \text{input and output dimension} \\
        b &= \text{batch items dimension} \\
        \overline{\mathbf{x}} \in \mathbb{R}^{b \times n} &= \text{input after tied bias} \\
        W_e \in \mathbb{R}^{m \times n} &= \text{weight matrix} \\
        b_e \in \mathbb{R}^{m} &= \text{bias vector} \\
        f &= \text{ReLU}(\overline{\mathbf{x}} W_e^T + b_e) = \text{LinearEncoder output}
    \end{align*}
    $$
    """

    _weight: Float[
        Parameter,
        Axis.names(Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE, Axis.INPUT_OUTPUT_FEATURE),
    ]
    """Weight parameter internal state."""

    _bias: Float[Parameter, Axis.names(Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE)]
    """Bias parameter internal state."""

    @property
    def weight(
        self,
    ) -> Float[
        Parameter,
        Axis.names(Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE, Axis.INPUT_OUTPUT_FEATURE),
    ]:
        """Weight parameter.

        Each row in the weights matrix acts as a dictionary vector, representing a single basis
        element in the learned activation space.
        """
        return self._weight

    @property
    def bias(self) -> Float[Parameter, Axis.names(Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE)]:
        """Bias parameter."""
        return self._bias

    @property
    def reset_optimizer_parameter_details(self) -> list[ResetOptimizerParameterDetails]:
        """Reset optimizer parameter details.

        Details of the parameters that should be reset in the optimizer, when resetting
        dictionary vectors.

        Returns:
            List of tuples of the form `(parameter, axis)`, where `parameter` is the parameter to
            reset (e.g. encoder.weight), and `axis` is the axis of the parameter to reset.
        """
        return [
            ResetOptimizerParameterDetails(parameter=self.weight, axis=-2),
            ResetOptimizerParameterDetails(parameter=self.bias, axis=-1),
        ]

    activation_function: ReLU
    """Activation function."""

    @validate_call
    def __init__(
        self,
        input_features: PositiveInt,
        learnt_features: PositiveInt,
        n_components: PositiveInt | None,
    ):
        """Initialize the linear encoder layer.

        Args:
            input_features: Number of input features to the autoencoder.
            learnt_features: Number of learnt features in the autoencoder.
            n_components: Number of source model components the SAE is trained on.
        """
        super().__init__(
            input_features=input_features,
            learnt_features=learnt_features,
            n_components=n_components,
        )
        self._learnt_features = learnt_features
        self._input_features = input_features
        self._n_components = n_components

        self._weight = Parameter(
            torch.empty(
                shape_with_optional_dimensions(n_components, learnt_features, input_features),
            )
        )
        self._bias = Parameter(
            torch.zeros(shape_with_optional_dimensions(n_components, learnt_features))
        )
        self.activation_function = ReLU()

        self.reset_parameters()

    def reset_parameters(self) -> None:
        """Initialize or reset the parameters."""
        # Assumes we are using ReLU activation function (for e.g. leaky ReLU, the `a` parameter and
        # `nonlinerity` must be changed.
        init.kaiming_uniform_(self._weight, nonlinearity="relu")

        # Bias (approach from nn.Linear)
        fan_in = self._weight.size(1)
        bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0
        init.uniform_(self._bias, -bound, bound)

    def forward(
        self,
        x: Float[
            Tensor, Axis.names(Axis.BATCH, Axis.COMPONENT_OPTIONAL, Axis.INPUT_OUTPUT_FEATURE)
        ],
    ) -> Float[Tensor, Axis.names(Axis.BATCH, Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE)]:
        """Forward pass.

        Args:
            x: Input tensor.

        Returns:
            Output of the forward pass.
        """
        z = (
            einops.einsum(
                x,
                self.weight,
                f"{Axis.BATCH} ... {Axis.INPUT_OUTPUT_FEATURE}, \
                    ... {Axis.LEARNT_FEATURE} {Axis.INPUT_OUTPUT_FEATURE} \
                    -> {Axis.BATCH} ... {Axis.LEARNT_FEATURE}",
            )
            + self.bias
        )

        return self.activation_function(z)

    def extra_repr(self) -> str:
        """String extra representation of the module."""
        return (
            f"input_features={self._input_features}, "
            f"learnt_features={self._learnt_features}, "
            f"n_components={self._n_components}"
        )
