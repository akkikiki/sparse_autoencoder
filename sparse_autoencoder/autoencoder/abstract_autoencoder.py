"""Abstract Sparse Autoencoder Model."""
from abc import ABC, abstractmethod
from typing import NamedTuple

from jaxtyping import Float
from torch import Tensor
from torch.nn import Module

from sparse_autoencoder.autoencoder.components.abstract_decoder import AbstractDecoder
from sparse_autoencoder.autoencoder.components.abstract_encoder import AbstractEncoder
from sparse_autoencoder.autoencoder.components.abstract_outer_bias import AbstractOuterBias
from sparse_autoencoder.autoencoder.types import ResetOptimizerParameterDetails
from sparse_autoencoder.tensor_types import Axis


class AutoencoderForwardPassResult(NamedTuple):
    """Autoencoder Forward Pass Result."""

    learned_activations: Float[
        Tensor, Axis.names(Axis.BATCH, Axis.COMPONENT_OPTIONAL, Axis.LEARNT_FEATURE)
    ]

    decoded_activations: Float[
        Tensor, Axis.names(Axis.BATCH, Axis.COMPONENT_OPTIONAL, Axis.INPUT_OUTPUT_FEATURE)
    ]


class AbstractAutoencoder(Module, ABC):
    """Abstract Sparse Autoencoder Model.

    Warning:
        All components should support an optional component axis, which comes after the batch axis
            (as various PyTorch helpers assume the batch axis is the first axis). This means all
            parameters must be created with this dimension if n_components is not None. And all type
            signatures should allow for it.
    """

    @property
    @abstractmethod
    def encoder(self) -> AbstractEncoder:
        """Encoder."""

    @property
    @abstractmethod
    def decoder(self) -> AbstractDecoder:
        """Decoder."""

    @property
    @abstractmethod
    def pre_encoder_bias(self) -> AbstractOuterBias:
        """Pre-encoder bias."""

    @property
    @abstractmethod
    def post_decoder_bias(self) -> AbstractOuterBias:
        """Post-decoder bias."""

    @property
    def reset_optimizer_parameter_details(self) -> list[ResetOptimizerParameterDetails]:
        """Reset optimizer parameter details.

        Details of the parameters that should be reset in the optimizer, when resetting
        dictionary vectors.

        Returns:
            List of tuples of the form `(parameter, axis)`, where `parameter` is the parameter to
            reset (e.g. encoder.weight), and `axis` is the axis of the parameter to reset.
        """
        return (
            self.encoder.reset_optimizer_parameter_details
            + self.decoder.reset_optimizer_parameter_details
        )

    @abstractmethod
    def forward(
        self,
        x: Float[
            Tensor, Axis.names(Axis.BATCH, Axis.COMPONENT_OPTIONAL, Axis.INPUT_OUTPUT_FEATURE)
        ],
    ) -> AutoencoderForwardPassResult:
        """Forward Pass.

        Args:
            x: Input activations (e.g. activations from an MLP layer (or MLP layers) in a
                transformer model).

        Returns:
            Tuple of learned activations and decoded activations.
        """

    @abstractmethod
    def reset_parameters(self) -> None:
        """Reset the parameters."""
