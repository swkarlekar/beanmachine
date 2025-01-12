# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from beanmachine.ppl.utils.set_of_tensors import SetOfTensors
from torch import tensor


class SetOfTensorsTest(unittest.TestCase):
    def test_set_of_tensors_1(self) -> None:
        self.maxDiff = None

        # Show that we deduplicate these tensors.

        t = [
            tensor(1.0),
            tensor([]),
            tensor([1.0]),
            tensor([1.0, 2.0]),
            tensor([1.0, 2.0, 3.0, 4.0]),
            tensor([[1.0]]),
            tensor([[1.0], [2.0]]),
            tensor([[1.0, 2.0]]),
            tensor([[1.0, 2.0], [3.0, 4.0]]),
            tensor(1.0),
            tensor([]),
            tensor([1.0]),
            tensor([1.0, 2.0]),
            tensor([1.0, 2.0, 3.0, 4.0]),
            tensor([[1.0]]),
            tensor([[1.0], [2.0]]),
            tensor([[1.0, 2.0]]),
            tensor([[1.0, 2.0], [3.0, 4.0]]),
        ]

        s = SetOfTensors(t)

        self.assertEqual(9, len(s))

        observed = str(s)
        expected = """
tensor(1.)
tensor([1., 2., 3., 4.])
tensor([1., 2.])
tensor([1.])
tensor([[1., 2.],
        [3., 4.]])
tensor([[1., 2.]])
tensor([[1.],
        [2.]])
tensor([[1.]])
tensor([])"""
        self.assertEqual(expected.strip(), observed.strip())
