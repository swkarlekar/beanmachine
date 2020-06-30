# Copyright (c) Facebook, Inc. and its affiliates.
"""Tests for bmg_nodes.py"""
import unittest

from beanmachine.ppl.compiler.bmg_nodes import (
    AdditionNode,
    BernoulliNode,
    BetaNode,
    BinomialNode,
    BooleanNode,
    ExpNode,
    HalfCauchyNode,
    IfThenElseNode,
    MultiplicationNode,
    NaturalNode,
    NegateNode,
    NormalNode,
    PositiveRealNode,
    ProbabilityNode,
    RealNode,
    SampleNode,
    StudentTNode,
    TensorNode,
    ToPositiveRealNode,
    ToRealNode,
    ToTensorNode,
)
from beanmachine.ppl.compiler.bmg_types import (
    Natural,
    PositiveReal,
    Probability,
    upper_bound,
)
from torch import Tensor, tensor


class ASTToolsTest(unittest.TestCase):
    def test_inf_type(self) -> None:
        """test_inf_type"""

        # The infimum type of a node is the *smallest* type that the
        # node can be converted to.

        # TODO: These tests only exercise nodes that we can actually
        # convert to BMG nodes right now. As we add more supported
        # node types to BMG, add tests here that reflect the BMG
        # type system rules.

        # Constants

        b = BooleanNode(True)
        prob = ProbabilityNode(0.5)
        pos = PositiveRealNode(1.5)
        real = RealNode(-1.5)
        nat = NaturalNode(2)
        t = TensorNode(tensor([1.0, 1.0]))

        self.assertEqual(b.inf_type, bool)
        self.assertEqual(prob.inf_type, Probability)
        self.assertEqual(pos.inf_type, PositiveReal)
        self.assertEqual(real.inf_type, float)
        self.assertEqual(nat.inf_type, Natural)
        self.assertEqual(t.inf_type, Tensor)

        # Constant infimum type depends on the value,
        # not the type of the container.

        self.assertEqual(ProbabilityNode(1.0).inf_type, bool)
        self.assertEqual(NaturalNode(1).inf_type, bool)
        self.assertEqual(PositiveRealNode(2.0).inf_type, Natural)
        self.assertEqual(RealNode(2.5).inf_type, PositiveReal)
        self.assertEqual(TensorNode(tensor(1.5)).inf_type, PositiveReal)

        # Distributions

        bern = SampleNode(BernoulliNode(prob))
        beta = SampleNode(BetaNode(pos, pos))
        bino = SampleNode(BinomialNode(nat, prob))
        half = SampleNode(HalfCauchyNode(pos))
        norm = SampleNode(NormalNode(real, pos))
        stut = SampleNode(StudentTNode(pos, pos, pos))

        self.assertEqual(bern.inf_type, bool)
        self.assertEqual(beta.inf_type, Probability)
        self.assertEqual(bino.inf_type, Natural)
        self.assertEqual(half.inf_type, PositiveReal)
        self.assertEqual(norm.inf_type, float)
        self.assertEqual(stut.inf_type, float)

        # Multiplication

        # Do not be confused by the notation here. What we are saying in these
        # comments is "the smallest type that a multiplication of a bool by a
        # probability can possibly be is probability".  We are NOT implying
        # here that BMG supports multiplication of bools by probabilities,
        # because it does not. Remember, the purpose of this code is that it
        # is part of an algorithm that computes *requirements* that must be met
        # to satisfy the BMG type system.
        #
        # What this is really saying is "if we multiplied a bool by a probability,
        # we could meet the requirements of the BMG type system by inserting code
        # that converted the bool to a probability."

        # bool x bool -> Probability
        # bool x Probability -> Probability
        # bool x Natural -> PositiveReal
        # bool x PositiveReal -> PositiveReal
        # bool x float -> float
        # bool x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(bern, bern).inf_type, Probability)
        self.assertEqual(MultiplicationNode(bern, beta).inf_type, Probability)
        self.assertEqual(MultiplicationNode(bern, bino).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bern, half).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bern, norm).inf_type, float)
        self.assertEqual(MultiplicationNode(bern, t).inf_type, Tensor)

        # Probability x bool -> Probability
        # Probability x Probability -> Probability
        # Probability x Natural -> PositiveReal
        # Probability x PositiveReal -> PositiveReal
        # Probability x float -> float
        # Probability x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(beta, bern).inf_type, Probability)
        self.assertEqual(MultiplicationNode(beta, beta).inf_type, Probability)
        self.assertEqual(MultiplicationNode(beta, bino).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(beta, half).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(beta, norm).inf_type, float)
        self.assertEqual(MultiplicationNode(beta, t).inf_type, Tensor)

        # Natural x bool -> PositiveReal
        # Natural x Probability -> PositiveReal
        # Natural x Natural -> PositiveReal
        # Natural x PositiveReal -> PositiveReal
        # Natural x float -> float
        # Natural x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(bino, bern).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bino, beta).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bino, bino).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bino, half).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(bino, norm).inf_type, float)
        self.assertEqual(MultiplicationNode(bino, t).inf_type, Tensor)

        # PositiveReal x bool -> PositiveReal
        # PositiveReal x Probability -> PositiveReal
        # PositiveReal x Natural -> PositiveReal
        # PositiveReal x PositiveReal -> PositiveReal
        # PositiveReal x float -> float
        # PositiveReal x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(half, bern).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(half, beta).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(half, bino).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(half, half).inf_type, PositiveReal)
        self.assertEqual(MultiplicationNode(half, norm).inf_type, float)
        self.assertEqual(MultiplicationNode(half, t).inf_type, Tensor)

        # float x bool -> float
        # float x Probability -> float
        # float x Natural -> float
        # float x PositiveReal -> float
        # float x float -> float
        # float x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(norm, bern).inf_type, float)
        self.assertEqual(MultiplicationNode(norm, beta).inf_type, float)
        self.assertEqual(MultiplicationNode(norm, bino).inf_type, float)
        self.assertEqual(MultiplicationNode(norm, half).inf_type, float)
        self.assertEqual(MultiplicationNode(norm, norm).inf_type, float)
        self.assertEqual(MultiplicationNode(norm, t).inf_type, Tensor)

        # Tensor x bool -> Tensor
        # Tensor x Probability -> Tensor
        # Tensor x Natural -> Tensor
        # Tensor x PositiveReal -> Tensor
        # Tensor x float -> Tensor
        # Tensor x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(t, bern).inf_type, Tensor)
        self.assertEqual(MultiplicationNode(t, beta).inf_type, Tensor)
        self.assertEqual(MultiplicationNode(t, bino).inf_type, Tensor)
        self.assertEqual(MultiplicationNode(t, half).inf_type, Tensor)
        self.assertEqual(MultiplicationNode(t, norm).inf_type, Tensor)
        self.assertEqual(MultiplicationNode(t, t).inf_type, Tensor)

        # Addition

        # bool + bool -> PositiveReal
        # bool + Probability -> PositiveReal
        # bool + Natural -> PositiveReal
        # bool + PositiveReal -> PositiveReal
        # bool + float -> float
        # bool + Tensor -> Tensor
        self.assertEqual(AdditionNode(bern, bern).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bern, beta).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bern, bino).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bern, half).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bern, norm).inf_type, float)
        self.assertEqual(AdditionNode(bern, t).inf_type, Tensor)

        # Probability + bool -> PositiveReal
        # Probability + Probability -> PositiveReal
        # Probability + Natural -> PositiveReal
        # Probability + PositiveReal -> PositiveReal
        # Probability + float -> float
        # Probability + Tensor -> Tensor
        self.assertEqual(AdditionNode(beta, bern).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(beta, beta).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(beta, bino).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(beta, half).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(beta, norm).inf_type, float)
        self.assertEqual(AdditionNode(beta, t).inf_type, Tensor)

        # Natural + bool -> PositiveReal
        # Natural + Probability -> PositiveReal
        # Natural + Natural -> PositiveReal
        # Natural + PositiveReal -> PositiveReal
        # Natural + float -> float
        # Natural + Tensor -> Tensor
        self.assertEqual(AdditionNode(bino, bern).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bino, beta).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bino, bino).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bino, half).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(bino, norm).inf_type, float)
        self.assertEqual(AdditionNode(bino, t).inf_type, Tensor)

        # PositiveReal + bool -> PositiveReal
        # PositiveReal + Probability -> PositiveReal
        # PositiveReal + Natural -> PositiveReal
        # PositiveReal + PositiveReal -> PositiveReal
        # PositiveReal + float -> float
        # PositiveReal + Tensor -> Tensor
        self.assertEqual(AdditionNode(half, bern).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(half, beta).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(half, bino).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(half, half).inf_type, PositiveReal)
        self.assertEqual(AdditionNode(half, norm).inf_type, float)
        self.assertEqual(AdditionNode(half, t).inf_type, Tensor)

        # float + bool -> float
        # float + Probability -> float
        # float + Natural -> float
        # float + PositiveReal -> float
        # float + float -> float
        # float + Tensor -> Tensor
        self.assertEqual(AdditionNode(norm, bern).inf_type, float)
        self.assertEqual(AdditionNode(norm, beta).inf_type, float)
        self.assertEqual(AdditionNode(norm, bino).inf_type, float)
        self.assertEqual(AdditionNode(norm, half).inf_type, float)
        self.assertEqual(AdditionNode(norm, norm).inf_type, float)
        self.assertEqual(AdditionNode(norm, t).inf_type, Tensor)

        # Tensor + bool -> Tensor
        # Tensor + Probability -> Tensor
        # Tensor + Natural -> Tensor
        # Tensor + PositiveReal -> Tensor
        # Tensor + float -> Tensor
        # Tensor + Tensor -> Tensor
        self.assertEqual(AdditionNode(t, bern).inf_type, Tensor)
        self.assertEqual(AdditionNode(t, beta).inf_type, Tensor)
        self.assertEqual(AdditionNode(t, bino).inf_type, Tensor)
        self.assertEqual(AdditionNode(t, half).inf_type, Tensor)
        self.assertEqual(AdditionNode(t, norm).inf_type, Tensor)
        self.assertEqual(AdditionNode(t, t).inf_type, Tensor)

        # IfThenElse

        # bool : bool -> bool
        # bool : Probability -> Probability
        # bool : Natural -> Natural
        # bool : PositiveReal -> PositiveReal
        # bool : float -> float
        # bool : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, bern, bern).inf_type, bool)
        self.assertEqual(IfThenElseNode(bern, bern, beta).inf_type, Probability)
        self.assertEqual(IfThenElseNode(bern, bern, bino).inf_type, Natural)
        self.assertEqual(IfThenElseNode(bern, bern, half).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, bern, norm).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, bern, t).inf_type, Tensor)

        # Probability : bool -> Probability
        # Probability : Probability -> Probability
        # Probability : Natural -> PositiveReal
        # Probability : PositiveReal -> PositiveReal
        # Probability : float -> float
        # Probability : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, beta, bern).inf_type, Probability)
        self.assertEqual(IfThenElseNode(bern, beta, beta).inf_type, Probability)
        self.assertEqual(IfThenElseNode(bern, beta, bino).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, beta, half).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, beta, norm).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, beta, t).inf_type, Tensor)

        # Natural : bool -> Natural
        # Natural : Probability -> PositiveReal
        # Natural : Natural -> Natural
        # Natural : PositiveReal -> PositiveReal
        # Natural : float -> float
        # Natural : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, bino, bern).inf_type, Natural)
        self.assertEqual(IfThenElseNode(bern, bino, beta).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, bino, bino).inf_type, Natural)
        self.assertEqual(IfThenElseNode(bern, bino, half).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, bino, norm).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, bino, t).inf_type, Tensor)

        # PositiveReal : bool -> PositiveReal
        # PositiveReal : Probability -> PositiveReal
        # PositiveReal : Natural -> PositiveReal
        # PositiveReal : PositiveReal -> PositiveReal
        # PositiveReal : float -> float
        # PositiveReal : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, half, bern).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, half, beta).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, half, bino).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, half, half).inf_type, PositiveReal)
        self.assertEqual(IfThenElseNode(bern, half, norm).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, half, t).inf_type, Tensor)

        # float : bool -> float
        # float : Probability -> float
        # float : Natural -> float
        # float : PositiveReal -> float
        # float : float -> float
        # float : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, norm, bern).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, norm, beta).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, norm, bino).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, norm, half).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, norm, norm).inf_type, float)
        self.assertEqual(IfThenElseNode(bern, norm, t).inf_type, Tensor)

        # Tensor : bool -> Tensor
        # Tensor : Probability -> Tensor
        # Tensor : Natural -> Tensor
        # Tensor : PositiveReal -> Tensor
        # Tensor : float -> Tensor
        # Tensor : Tensor -> Tensor
        self.assertEqual(IfThenElseNode(bern, t, bern).inf_type, Tensor)
        self.assertEqual(IfThenElseNode(bern, t, beta).inf_type, Tensor)
        self.assertEqual(IfThenElseNode(bern, t, bino).inf_type, Tensor)
        self.assertEqual(IfThenElseNode(bern, t, half).inf_type, Tensor)
        self.assertEqual(IfThenElseNode(bern, t, norm).inf_type, Tensor)
        self.assertEqual(IfThenElseNode(bern, t, t).inf_type, Tensor)

        # Negate
        # - bool -> float
        # - Probability -> float
        # - Natural -> float
        # - PositiveReal -> float
        # - float -> float
        # - Tensor -> Tensor
        self.assertEqual(NegateNode(bern).inf_type, float)
        self.assertEqual(NegateNode(beta).inf_type, float)
        self.assertEqual(NegateNode(bino).inf_type, float)
        self.assertEqual(NegateNode(half).inf_type, float)
        self.assertEqual(NegateNode(norm).inf_type, float)
        self.assertEqual(NegateNode(t).inf_type, Tensor)

        # Exp
        # exp bool -> PositiveReal
        # exp Probability -> PositiveReal
        # exp Natural -> PositiveReal
        # exp PositiveReal -> PositiveReal
        # exp float -> float
        # exp Tensor -> Tensor
        self.assertEqual(ExpNode(bern).inf_type, PositiveReal)
        self.assertEqual(ExpNode(beta).inf_type, PositiveReal)
        self.assertEqual(ExpNode(bino).inf_type, PositiveReal)
        self.assertEqual(ExpNode(half).inf_type, PositiveReal)
        self.assertEqual(ExpNode(norm).inf_type, float)
        self.assertEqual(ExpNode(t).inf_type, Tensor)

        # To Real
        self.assertEqual(ToRealNode(bern).inf_type, float)
        self.assertEqual(ToRealNode(beta).inf_type, float)
        self.assertEqual(ToRealNode(bino).inf_type, float)
        self.assertEqual(ToRealNode(half).inf_type, float)
        self.assertEqual(ToRealNode(norm).inf_type, float)
        # To Real is illegal on tensors

        # To Tensor
        self.assertEqual(ToTensorNode(bern).inf_type, Tensor)
        self.assertEqual(ToTensorNode(beta).inf_type, Tensor)
        self.assertEqual(ToTensorNode(bino).inf_type, Tensor)
        self.assertEqual(ToTensorNode(half).inf_type, Tensor)
        self.assertEqual(ToTensorNode(norm).inf_type, Tensor)
        self.assertEqual(ToTensorNode(t).inf_type, Tensor)

        # To Positive Real
        self.assertEqual(ToPositiveRealNode(bern).inf_type, PositiveReal)
        self.assertEqual(ToPositiveRealNode(beta).inf_type, PositiveReal)
        self.assertEqual(ToPositiveRealNode(bino).inf_type, PositiveReal)
        self.assertEqual(ToPositiveRealNode(half).inf_type, PositiveReal)
        # To Positive Real is illegal on reals and tensors

    def test_requirements(self) -> None:
        """test_requirements"""

        # Every node can list the *exact* types that it will accept
        # for each input. In some cases this is independent of inputs;
        # a Bernoulli node accepts only a Probability. In some cases
        # this depends on inputs; a multiplication node with inputs
        # Probability and PositiveReal requires that the Probability
        # be converted via a ToPositiveReal node.

        # TODO: These tests only exercise nodes that we can actually
        # convert to BMG nodes right now. As we add more supported
        # node types to BMG, add tests here that reflect the BMG
        # type system rules.

        # Constants

        b = BooleanNode(True)
        prob = ProbabilityNode(0.5)
        pos = PositiveRealNode(1.5)
        real = RealNode(-1.5)
        nat = NaturalNode(2)
        t = TensorNode(tensor([1.0, 1.0]))

        self.assertEqual(b.requirements, [])
        self.assertEqual(prob.requirements, [])
        self.assertEqual(pos.requirements, [])
        self.assertEqual(real.requirements, [])
        self.assertEqual(nat.requirements, [])
        self.assertEqual(t.requirements, [])

        # Distributions

        self.assertEqual(BernoulliNode(prob).requirements, [Probability])
        self.assertEqual(BetaNode(pos, pos).requirements, [PositiveReal, PositiveReal])
        self.assertEqual(BinomialNode(nat, prob).requirements, [Natural, Probability])
        self.assertEqual(HalfCauchyNode(pos).requirements, [PositiveReal])
        self.assertEqual(NormalNode(real, pos).requirements, [float, PositiveReal])
        self.assertEqual(
            StudentTNode(pos, pos, pos).requirements,
            [PositiveReal, float, PositiveReal],
        )

        bern = SampleNode(BernoulliNode(prob))
        beta = SampleNode(BetaNode(pos, pos))
        bino = SampleNode(BinomialNode(nat, prob))
        half = SampleNode(HalfCauchyNode(pos))
        norm = SampleNode(NormalNode(real, pos))

        # Multiplication

        # Do not be confused by the notation here. What we are saying in these
        # comments is "the smallest type that a multiplication of a bool by a
        # probability can possibly be is probability".  We are NOT implying
        # here that BMG supports multiplication of bools by probabilities,
        # because it does not. Remember, the purpose of this code is that it
        # is part of an algorithm that computes *requirements* that must be met
        # to satisfy the BMG type system.
        #
        # What this is really saying is "if we multiplied a bool by a probability,
        # we could meet the requirements of the BMG type system by inserting code
        # that converted the bool to a probability."

        # bool x bool -> Probability
        # bool x Probability -> Probability
        # bool x Natural -> PositiveReal
        # bool x PositiveReal -> PositiveReal
        # bool x float -> float
        # bool x Tensor -> Tensor
        self.assertEqual(
            MultiplicationNode(bern, bern).requirements, [Probability, Probability]
        )
        self.assertEqual(
            MultiplicationNode(bern, beta).requirements, [Probability, Probability]
        )
        self.assertEqual(
            MultiplicationNode(bern, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(bern, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(MultiplicationNode(bern, norm).requirements, [float, float])
        self.assertEqual(MultiplicationNode(bern, t).requirements, [Tensor, Tensor])

        # Probability x bool -> Probability
        # Probability x Probability -> Probability
        # Probability x Natural -> PositiveReal
        # Probability x PositiveReal -> PositiveReal
        # Probability x float -> float
        # Probability x Tensor -> Tensor
        self.assertEqual(
            MultiplicationNode(beta, bern).requirements, [Probability, Probability]
        )
        self.assertEqual(
            MultiplicationNode(beta, beta).requirements, [Probability, Probability]
        )
        self.assertEqual(
            MultiplicationNode(beta, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(beta, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(MultiplicationNode(beta, norm).requirements, [float, float])
        self.assertEqual(MultiplicationNode(beta, t).requirements, [Tensor, Tensor])

        # Natural x bool -> PositiveReal
        # Natural x Probability -> PositiveReal
        # Natural x Natural -> PositiveReal
        # Natural x PositiveReal -> PositiveReal
        # Natural x float -> float
        # Natural x Tensor -> Tensor
        self.assertEqual(
            MultiplicationNode(bino, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(bino, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(bino, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(bino, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(MultiplicationNode(bino, norm).requirements, [float, float])
        self.assertEqual(MultiplicationNode(bino, t).requirements, [Tensor, Tensor])

        # PositiveReal x bool -> PositiveReal
        # PositiveReal x Probability -> PositiveReal
        # PositiveReal x Natural -> PositiveReal
        # PositiveReal x PositiveReal -> PositiveReal
        # PositiveReal x float -> float
        # PositiveReal x Tensor -> Tensor
        self.assertEqual(
            MultiplicationNode(half, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(half, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(half, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            MultiplicationNode(half, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(MultiplicationNode(half, norm).requirements, [float, float])
        self.assertEqual(MultiplicationNode(half, t).requirements, [Tensor, Tensor])

        # float x bool -> float
        # float x Probability -> float
        # float x Natural -> float
        # float x PositiveReal -> float
        # float x float -> float
        # float x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(norm, bern).requirements, [float, float])
        self.assertEqual(MultiplicationNode(norm, beta).requirements, [float, float])
        self.assertEqual(MultiplicationNode(norm, bino).requirements, [float, float])
        self.assertEqual(MultiplicationNode(norm, half).requirements, [float, float])
        self.assertEqual(MultiplicationNode(norm, norm).requirements, [float, float])
        self.assertEqual(MultiplicationNode(norm, t).requirements, [Tensor, Tensor])

        # Tensor x bool -> Tensor
        # Tensor x Probability -> Tensor
        # Tensor x Natural -> Tensor
        # Tensor x PositiveReal -> Tensor
        # Tensor x float -> Tensor
        # Tensor x Tensor -> Tensor
        self.assertEqual(MultiplicationNode(t, bern).requirements, [Tensor, Tensor])
        self.assertEqual(MultiplicationNode(t, beta).requirements, [Tensor, Tensor])
        self.assertEqual(MultiplicationNode(t, bino).requirements, [Tensor, Tensor])
        self.assertEqual(MultiplicationNode(t, half).requirements, [Tensor, Tensor])
        self.assertEqual(MultiplicationNode(t, norm).requirements, [Tensor, Tensor])
        self.assertEqual(MultiplicationNode(t, t).requirements, [Tensor, Tensor])

        # Addition

        # bool + bool -> PositiveReal
        # bool + Probability -> PositiveReal
        # bool + Natural -> PositiveReal
        # bool + PositiveReal -> PositiveReal
        # bool + float -> float
        # bool + Tensor -> Tensor
        self.assertEqual(
            AdditionNode(bern, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bern, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bern, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bern, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(AdditionNode(bern, norm).requirements, [float, float])
        self.assertEqual(AdditionNode(bern, t).requirements, [Tensor, Tensor])

        # Probability + bool -> PositiveReal
        # Probability + Probability -> PositiveReal
        # Probability + Natural -> PositiveReal
        # Probability + PositiveReal -> PositiveReal
        # Probability + float -> float
        # Probability + Tensor -> Tensor
        self.assertEqual(
            AdditionNode(beta, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(beta, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(beta, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(beta, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(AdditionNode(beta, norm).requirements, [float, float])
        self.assertEqual(AdditionNode(beta, t).requirements, [Tensor, Tensor])

        # Natural + bool -> PositiveReal
        # Natural + Probability -> PositiveReal
        # Natural + Natural -> PositiveReal
        # Natural + PositiveReal -> PositiveReal
        # Natural + float -> float
        # Natural + Tensor -> Tensor
        self.assertEqual(
            AdditionNode(bino, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bino, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bino, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(bino, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(AdditionNode(bino, norm).requirements, [float, float])
        self.assertEqual(AdditionNode(bino, t).requirements, [Tensor, Tensor])

        # PositiveReal + bool -> PositiveReal
        # PositiveReal + Probability -> PositiveReal
        # PositiveReal + Natural -> PositiveReal
        # PositiveReal + PositiveReal -> PositiveReal
        # PositiveReal + float -> float
        # PositiveReal + Tensor -> Tensor
        self.assertEqual(
            AdditionNode(half, bern).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(half, beta).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(half, bino).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(
            AdditionNode(half, half).requirements, [PositiveReal, PositiveReal]
        )
        self.assertEqual(AdditionNode(half, norm).requirements, [float, float])
        self.assertEqual(AdditionNode(half, t).requirements, [Tensor, Tensor])

        # float + bool -> float
        # float + Probability -> float
        # float + Natural -> float
        # float + PositiveReal -> float
        # float + float -> float
        # float + Tensor -> Tensor
        self.assertEqual(AdditionNode(norm, bern).requirements, [float, float])
        self.assertEqual(AdditionNode(norm, beta).requirements, [float, float])
        self.assertEqual(AdditionNode(norm, bino).requirements, [float, float])
        self.assertEqual(AdditionNode(norm, half).requirements, [float, float])
        self.assertEqual(AdditionNode(norm, norm).requirements, [float, float])
        self.assertEqual(AdditionNode(norm, t).requirements, [Tensor, Tensor])

        # Tensor + bool -> Tensor
        # Tensor + Probability -> Tensor
        # Tensor + Natural -> Tensor
        # Tensor + PositiveReal -> Tensor
        # Tensor + float -> Tensor
        # Tensor + Tensor -> Tensor
        self.assertEqual(AdditionNode(t, bern).requirements, [Tensor, Tensor])
        self.assertEqual(AdditionNode(t, beta).requirements, [Tensor, Tensor])
        self.assertEqual(AdditionNode(t, bino).requirements, [Tensor, Tensor])
        self.assertEqual(AdditionNode(t, half).requirements, [Tensor, Tensor])
        self.assertEqual(AdditionNode(t, norm).requirements, [Tensor, Tensor])
        self.assertEqual(AdditionNode(t, t).requirements, [Tensor, Tensor])

        # IfThenElse

        # bool : bool -> bool
        # bool : Probability -> Probability
        # bool : Natural -> Natural
        # bool : PositiveReal -> PositiveReal
        # bool : float -> float
        # bool : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, bern, bern).requirements, [bool, bool, bool]
        )
        self.assertEqual(
            IfThenElseNode(bern, bern, beta).requirements,
            [bool, Probability, Probability],
        )
        self.assertEqual(
            IfThenElseNode(bern, bern, bino).requirements, [bool, Natural, Natural]
        )
        self.assertEqual(
            IfThenElseNode(bern, bern, half).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, bern, norm).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, bern, t).requirements, [bool, Tensor, Tensor]
        )

        # Probability : bool -> Probability
        # Probability : Probability -> Probability
        # Probability : Natural -> PositiveReal
        # Probability : PositiveReal -> PositiveReal
        # Probability : float -> float
        # Probability : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, beta, bern).requirements,
            [bool, Probability, Probability],
        )
        self.assertEqual(
            IfThenElseNode(bern, beta, beta).requirements,
            [bool, Probability, Probability],
        )
        self.assertEqual(
            IfThenElseNode(bern, beta, bino).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, beta, half).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, beta, norm).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, beta, t).requirements, [bool, Tensor, Tensor]
        )

        # Natural : bool -> Natural
        # Natural : Probability -> PositiveReal
        # Natural : Natural -> Natural
        # Natural : PositiveReal -> PositiveReal
        # Natural : float -> float
        # Natural : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, bino, bern).requirements, [bool, Natural, Natural]
        )
        self.assertEqual(
            IfThenElseNode(bern, bino, beta).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, bino, bino).requirements, [bool, Natural, Natural]
        )
        self.assertEqual(
            IfThenElseNode(bern, bino, half).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, bino, norm).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, bino, t).requirements, [bool, Tensor, Tensor]
        )

        # PositiveReal : bool -> PositiveReal
        # PositiveReal : Probability -> PositiveReal
        # PositiveReal : Natural -> PositiveReal
        # PositiveReal : PositiveReal -> PositiveReal
        # PositiveReal : float -> float
        # PositiveReal : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, half, bern).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, half, beta).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, half, bino).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, half, half).requirements,
            [bool, PositiveReal, PositiveReal],
        )
        self.assertEqual(
            IfThenElseNode(bern, half, norm).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, half, t).requirements, [bool, Tensor, Tensor]
        )

        # float : bool -> float
        # float : Probability -> float
        # float : Natural -> float
        # float : PositiveReal -> float
        # float : float -> float
        # float : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, norm, bern).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, norm, beta).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, norm, bino).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, norm, half).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, norm, norm).requirements, [bool, float, float]
        )
        self.assertEqual(
            IfThenElseNode(bern, norm, t).requirements, [bool, Tensor, Tensor]
        )

        # Tensor : bool -> Tensor
        # Tensor : Probability -> Tensor
        # Tensor : Natural -> Tensor
        # Tensor : PositiveReal -> Tensor
        # Tensor : float -> Tensor
        # Tensor : Tensor -> Tensor
        self.assertEqual(
            IfThenElseNode(bern, t, bern).requirements, [bool, Tensor, Tensor]
        )
        self.assertEqual(
            IfThenElseNode(bern, t, beta).requirements, [bool, Tensor, Tensor]
        )
        self.assertEqual(
            IfThenElseNode(bern, t, bino).requirements, [bool, Tensor, Tensor]
        )
        self.assertEqual(
            IfThenElseNode(bern, t, half).requirements, [bool, Tensor, Tensor]
        )
        self.assertEqual(
            IfThenElseNode(bern, t, norm).requirements, [bool, Tensor, Tensor]
        )
        self.assertEqual(
            IfThenElseNode(bern, t, t).requirements, [bool, Tensor, Tensor]
        )

        # Negate
        # - bool -> float
        # - Probability -> float
        # - Natural -> float
        # - PositiveReal -> float
        # - float -> float
        # - Tensor -> Tensor
        self.assertEqual(NegateNode(bern).requirements, [float])
        self.assertEqual(NegateNode(beta).requirements, [float])
        self.assertEqual(NegateNode(bino).requirements, [float])
        self.assertEqual(NegateNode(half).requirements, [float])
        self.assertEqual(NegateNode(norm).requirements, [float])
        self.assertEqual(NegateNode(t).requirements, [Tensor])

        # Exp
        # exp bool -> PositiveReal
        # exp Probability -> PositiveReal
        # exp Natural -> PositiveReal
        # exp PositiveReal -> PositiveReal
        # exp float -> float
        # exp Tensor -> Tensor
        self.assertEqual(ExpNode(bern).requirements, [PositiveReal])
        self.assertEqual(ExpNode(beta).requirements, [PositiveReal])
        self.assertEqual(ExpNode(bino).requirements, [PositiveReal])
        self.assertEqual(ExpNode(half).requirements, [PositiveReal])
        self.assertEqual(ExpNode(norm).requirements, [float])
        self.assertEqual(ExpNode(t).requirements, [Tensor])

        # To Real
        self.assertEqual(ToRealNode(bern).requirements, [upper_bound(float)])
        self.assertEqual(ToRealNode(beta).requirements, [upper_bound(float)])
        self.assertEqual(ToRealNode(bino).requirements, [upper_bound(float)])
        self.assertEqual(ToRealNode(half).requirements, [upper_bound(float)])
        self.assertEqual(ToRealNode(norm).requirements, [upper_bound(float)])
        # To Real is illegal on tensors

        # To Tensor
        self.assertEqual(ToTensorNode(bern).requirements, [upper_bound(Tensor)])
        self.assertEqual(ToTensorNode(beta).requirements, [upper_bound(Tensor)])
        self.assertEqual(ToTensorNode(bino).requirements, [upper_bound(Tensor)])
        self.assertEqual(ToTensorNode(half).requirements, [upper_bound(Tensor)])
        self.assertEqual(ToTensorNode(norm).requirements, [upper_bound(Tensor)])
        self.assertEqual(ToTensorNode(t).requirements, [upper_bound(Tensor)])

        # To Positive Real
        self.assertEqual(
            ToPositiveRealNode(bern).requirements, [upper_bound(PositiveReal)]
        )
        self.assertEqual(
            ToPositiveRealNode(beta).requirements, [upper_bound(PositiveReal)]
        )
        self.assertEqual(
            ToPositiveRealNode(bino).requirements, [upper_bound(PositiveReal)]
        )
        self.assertEqual(
            ToPositiveRealNode(half).requirements, [upper_bound(PositiveReal)]
        )
        # To Positive Real is illegal on reals and tensors
