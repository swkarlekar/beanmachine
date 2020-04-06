# Copyright (c) Facebook, Inc. and its affiliates.
import unittest

import torch.distributions as dist
import torch.tensor as tensor
from beanmachine.ppl.model.statistical_model import StatisticalModel, sample
from beanmachine.ppl.model.utils import Mode
from beanmachine.ppl.world import Variable, World


class WorldTest(unittest.TestCase):
    class SampleModel(object):
        @sample
        def foo(self):
            return dist.Normal(tensor(0.0), tensor(1.0))

        @sample
        def bar(self):
            return dist.Normal(self.foo(), tensor(1.0))

    class SampleModelWithParentUpdate(object):
        @sample
        def foo(self):
            return dist.Normal(tensor(0.0), tensor(1.0))

        @sample
        def baz(self):
            return dist.Normal(tensor(0.0), tensor(1.0))

        @sample
        def bar(self):
            if self.foo().item() > 0.3:
                return dist.Normal(self.foo(), tensor(1.0))
            return dist.Normal(self.baz(), tensor(1.0))

    class SampleLargeModelUpdate(object):
        @sample
        def foo(self):
            return dist.Normal(tensor(0.0), tensor(1.0))

        @sample
        def baz(self):
            return dist.Normal(self.foo(), tensor(1.0))

        @sample
        def foobar(self):
            if self.foo().item() < 1:
                return dist.Normal(self.foo(), tensor(1.0))
            return dist.Normal(tensor(0.0), tensor(1.0))

        @sample
        def bar(self):
            if self.foo().item() < 0.3:
                return dist.Normal(self.foo(), tensor(1.0))
            if self.foo().item() < 0.5:
                return dist.Normal(self.baz(), tensor(1.0))
            if self.foo().item() < 0.7:
                return dist.Normal(self.foobar(), tensor(1.0))
            return dist.Normal(self.foobaz(), tensor(1.0))

        @sample
        def foobaz(self):
            if self.foo().item() < 1:
                return dist.Normal(self.foobar(), 1)
            return dist.Normal(tensor(0.0), tensor(1.0))

    class SampleLargeModelWithAncesters(object):
        @sample
        def X(self):
            return dist.Categorical([0.5, 0.5])

        @sample
        def A(self, i):
            return dist.Normal(0.0, 1.0)

        @sample
        def B(self, i):
            return dist.Normal(self.A(i), tensor(1.0))

        @sample
        def C(self, i):
            return dist.Normal(self.B(i), tensor(1.0))

        @sample
        def D(self, i):
            return dist.Normal(self.B(i), abs(self.C(i).item()) + 0.1)

        @sample
        def Y(self):
            return dist.Normal(self.D(self.X().item()), tensor(1.0))

    def test_world_change(self):
        model = self.SampleModel()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()
        StatisticalModel.set_mode(Mode.INFERENCE)
        world.set_observations({bar_key: tensor(0.1)})
        world_vars = world.variables_.vars()
        world_vars[foo_key] = Variable(
            distribution=dist.Normal(tensor(0.0), tensor(1.0)),
            value=tensor(0.5),
            log_prob=dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.5)),
            parent=set(),
            children=set({bar_key}),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.5),
            jacobian=tensor(0.0),
        )

        world_vars[bar_key] = Variable(
            distribution=dist.Normal(tensor(0.5), tensor(1.0)),
            value=tensor(0.1),
            log_prob=dist.Normal(tensor(0.5), tensor(1.0)).log_prob(tensor(0.1)),
            parent=set({foo_key}),
            children=set(),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.1),
            jacobian=tensor(0.0),
        )

        bar_markov_blanket = world.get_markov_blanket(bar_key)
        self.assertListEqual(list(bar_markov_blanket), [])
        foo_markov_blanket = world.get_markov_blanket(foo_key)
        self.assertListEqual(list(foo_markov_blanket), [])

        children_log_update, world_log_update, node_log_update, _ = world.propose_change(
            foo_key, tensor(0.25)
        )

        expected_children_log_update = dist.Normal(tensor(0.25), tensor(1.0)).log_prob(
            tensor(0.1)
        ) - dist.Normal(tensor(0.5), tensor(1.0)).log_prob(tensor(0.1))
        expected_world_log_update = expected_children_log_update + node_log_update

        self.assertAlmostEqual(
            children_log_update.item(), expected_children_log_update.item(), places=3
        )
        self.assertAlmostEqual(
            world_log_update.item(), expected_world_log_update.item(), places=3
        )

        for node in world.diff_.to_be_deleted_vars():
            self.assertEqual(world.diff_.is_marked_for_delete(node), False)

    def test_world_change_with_parent_update_and_new_node(self):
        model = self.SampleModelWithParentUpdate()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()
        baz_key = model.baz()
        StatisticalModel.set_mode(Mode.INFERENCE)
        world.set_observations({bar_key: tensor(0.1)})

        world_vars = world.variables_.vars()
        world_vars[foo_key] = Variable(
            distribution=dist.Normal(tensor(0.0), tensor(1.0)),
            value=tensor(0.5),
            log_prob=dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.5)),
            parent=set(),
            children=set({bar_key}),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.5),
            jacobian=tensor(0.0),
        )

        world_vars[bar_key] = Variable(
            distribution=dist.Normal(tensor(0.5), tensor(1.0)),
            value=tensor(0.1),
            log_prob=dist.Normal(tensor(0.5), tensor(1.0)).log_prob(tensor(0.1)),
            parent=set({foo_key}),
            children=set(),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.1),
            jacobian=tensor(0.0),
        )

        children_log_update, world_log_update, _, _ = world.propose_change(
            foo_key, tensor(0.25)
        )

        expected_children_log_update = (
            dist.Normal(world.diff_.get_node(baz_key).value, tensor(1.0))
            .log_prob(tensor(0.1))
            .sub(dist.Normal(tensor(0.5), tensor(1.0)).log_prob(tensor(0.1)))
        )

        expected_node_update = 0.0938
        expected_world_update = expected_children_log_update.add(
            tensor(expected_node_update)
        ).add(
            dist.Normal(tensor(0.0), tensor(1.0)).log_prob(
                world.diff_.get_node(baz_key).value
            )
        )
        self.assertAlmostEqual(
            children_log_update.item(), expected_children_log_update.item(), places=3
        )
        self.assertAlmostEqual(
            world_log_update.item(), expected_world_update.item(), places=3
        )
        self.assertEqual((baz_key) in world.diff_.get_node(bar_key).parent, True)

        for node in world.diff_.to_be_deleted_vars():
            self.assertEqual(world.diff_.is_marked_for_delete(node), False)

    def test_world_change_with_multiple_parent_update(self):
        model = self.SampleLargeModelUpdate()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()
        baz_key = model.baz()
        foobar_key = model.foobar()
        foobaz_key = model.foobaz()
        StatisticalModel.set_mode(Mode.INFERENCE)
        world.set_observations({bar_key: tensor(0.1)})

        world_vars = world.variables_.vars()
        world_vars[foo_key] = Variable(
            distribution=dist.Normal(tensor(0.0), tensor(1.0)),
            value=tensor(0.2),
            log_prob=dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.2)),
            parent=set(),
            children=set({bar_key}),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.2),
            jacobian=tensor(0.0),
        )

        world_vars[bar_key] = Variable(
            distribution=dist.Normal(tensor(0.2), tensor(1.0)),
            value=tensor(0.1),
            log_prob=dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(0.1)),
            parent=set({foo_key}),
            children=set(),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.1),
            jacobian=tensor(0.0),
        )

        expected_node_update = (
            dist.Normal(tensor(0.0), tensor(1.0))
            .log_prob(0.35)
            .sub(dist.Normal(tensor(0.0), tensor(1.0)).log_prob(0.2))
        )

        children_log_update, world_log_update, _, score = world.propose_change(
            foo_key, tensor(0.35)
        )

        expected_children_log_update = (
            dist.Normal(world.diff_.get_node(baz_key).value, tensor(1.0))
            .log_prob(tensor(0.1))
            .sub(dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(0.1)))
        )

        expected_world_update = expected_children_log_update.add(
            expected_node_update
        ).add(
            dist.Normal(world.diff_.get_node(foo_key).value, tensor(1.0)).log_prob(
                world.diff_.get_node(baz_key).value
            )
        )

        self.assertAlmostEqual(
            children_log_update.item(), expected_children_log_update.item(), places=3
        )
        self.assertAlmostEqual(
            world_log_update.item(), expected_world_update.item(), places=3
        )
        self.assertEqual((baz_key) in world.diff_.get_node(bar_key).parent, True)

        for node in world.diff_.to_be_deleted_vars():
            self.assertEqual(world.diff_.is_marked_for_delete(node), False)

        world.accept_diff()

        children_log_update, world_log_update, node_log_update, score = world.propose_change(
            foo_key, tensor(0.55)
        )

        expected_node_update = (
            dist.Normal(tensor(0.0), tensor(1.0))
            .log_prob(0.55)
            .sub(dist.Normal(tensor(0.0), tensor(1.0)).log_prob(0.35))
        )

        expected_children_log_update = (
            dist.Normal(world.diff_.get_node(foobar_key).value, tensor(1.0))
            .log_prob(tensor(0.1))
            .sub(
                dist.Normal(world.diff_.get_node(baz_key).value, tensor(1.0)).log_prob(
                    tensor(0.1)
                )
            )
        )

        expected_world_update = (
            expected_children_log_update.add(expected_node_update)
            .add(
                dist.Normal(world.diff_.get_node(foo_key).value, tensor(1.0)).log_prob(
                    world.diff_.get_node(foobar_key).value
                )
            )
            .sub(world.variables_.get_node(baz_key).log_prob)
        )

        self.assertEqual(node_log_update.item(), expected_node_update.item())

        self.assertAlmostEqual(
            children_log_update.item(), expected_children_log_update.item(), places=3
        )
        self.assertAlmostEqual(
            world_log_update.item(), expected_world_update.item(), places=3
        )
        self.assertEqual((foobar_key) in world.diff_.get_node(bar_key).parent, True)

        for node in world.diff_.to_be_deleted_vars():
            if node == baz_key:
                self.assertEqual(world.diff_.is_marked_for_delete(node), True)
            else:
                self.assertEqual(world.diff_.is_marked_for_delete(node), False)

        world.accept_diff()
        self.assertEqual(baz_key in world_vars, False)
        self.assertEqual(baz_key in world_vars[foo_key].children, False)

        children_log_update, world_log_update, _, _ = world.propose_change(
            foo_key, tensor(0.75)
        )

        world.accept_diff()

        self.assertEqual(baz_key in world_vars, False)
        self.assertEqual(foobar_key in world_vars, True)
        self.assertEqual(foobar_key in world_vars[bar_key].parent, False)
        self.assertEqual(bar_key in world_vars[foobar_key].children, False)
        self.assertEqual(foobar_key in world_vars[foobaz_key].parent, True)
        self.assertEqual(foobaz_key in world_vars[foobar_key].children, True)

        children_log_update, world_log_update, _, _ = world.propose_change(
            foo_key, tensor(1.05)
        )

        world.accept_diff()

        self.assertEqual(foobar_key in world_vars, False)
        self.assertEqual(foobar_key in world_vars[foo_key].children, False)
        self.assertEqual(foobar_key in world_vars[foobaz_key].parent, False)

    def test_ancestor_change(self):
        model = self.SampleLargeModelWithAncesters()
        world = StatisticalModel.reset()
        X_key = model.X()
        A_key_0 = model.A(0.0)
        A_key_1 = model.A(1.0)
        B_key_0 = model.B(0.0)
        B_key_1 = model.B(1.0)
        C_key_0 = model.C(0.0)
        C_key_1 = model.C(1.0)
        D_key_0 = model.D(0.0)
        D_key_1 = model.D(1.0)
        Y_key = model.Y()
        StatisticalModel.set_mode(Mode.INFERENCE)
        world.set_observations({Y_key: tensor(0.1)})

        world_vars = world.variables_.vars()
        world_variable = world.variables_

        world_variable.add_node(
            X_key,
            Variable(
                distribution=dist.Categorical(tensor([0.5, 0.5])),
                value=tensor(0.0),
                log_prob=dist.Categorical(tensor([0.5, 0.5])).log_prob(tensor(1.0)),
                parent=set(),
                children=set({Y_key}),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(0.0),
                jacobian=tensor(0.0),
            ),
        )

        world_variable.add_node(
            A_key_0,
            Variable(
                distribution=dist.Normal(tensor(0.0), tensor(1.0)),
                value=tensor(0.1),
                log_prob=dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.1)),
                parent=set(),
                children=set({B_key_0}),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(0.1),
                jacobian=tensor(0.0),
            ),
        )

        world_variable.add_node(
            B_key_0,
            Variable(
                distribution=dist.Normal(tensor(0.1), tensor(1.0)),
                value=tensor(0.2),
                log_prob=dist.Normal(tensor(0.1), tensor(1.0)).log_prob(tensor(0.2)),
                parent=set({A_key_0}),
                children=set({C_key_0, D_key_0}),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(0.2),
                jacobian=tensor(0.0),
            ),
        )

        world_variable.add_node(
            C_key_0,
            Variable(
                distribution=dist.Normal(tensor(0.2), tensor(1.0)),
                value=tensor(0.2),
                log_prob=dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(0.2)),
                parent=set({B_key_0}),
                children=set({D_key_0}),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(0.2),
                jacobian=tensor(0.0),
            ),
        )

        world_variable.add_node(
            D_key_0,
            Variable(
                distribution=dist.Normal(tensor(0.2), tensor(0.2)),
                value=tensor(0.2),
                log_prob=dist.Normal(tensor(0.2), tensor(0.2)).log_prob(tensor(0.2)),
                parent=set({B_key_0, C_key_0}),
                children=set({Y_key}),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(0.2),
                jacobian=tensor(0.0),
            ),
        )

        world_variable.add_node(
            Y_key,
            Variable(
                distribution=dist.Normal(tensor(0.2), tensor(1.0)),
                value=tensor(1.0),
                log_prob=dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(1.0)),
                parent=set({D_key_0, X_key}),
                children=set(),
                proposal_distribution=None,
                extended_val=None,
                is_discrete=False,
                transforms=[],
                unconstrained_value=tensor(1.0),
                jacobian=tensor(0.0),
            ),
        )

        children_log_update, world_log_update, node_log_update, score = world.propose_change(
            X_key, tensor(1.0)
        )

        a_value = tensor(0.0)
        b_value = tensor(0.0)
        c_value = tensor(0.0)
        d_value = tensor(0.0)

        diff_vars = world.diff_.vars()
        for key in diff_vars:
            if key == D_key_1:
                d_value = diff_vars[key].value
            if key == C_key_1:
                c_value = diff_vars[key].value
            if key == B_key_1:
                b_value = diff_vars[key].value
            if key == A_key_1:
                a_value = diff_vars[key].value
        expected_children_log_update = dist.Normal(d_value, tensor(1.0)).log_prob(
            tensor(1.0)
        ) - dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(1.0))

        self.assertAlmostEqual(
            children_log_update.item(), expected_children_log_update.item(), places=3
        )
        expected_node_log_update = tensor(0.0)

        self.assertAlmostEqual(
            node_log_update.item(), expected_node_log_update.item(), places=3
        )
        expected_world_log_update = expected_children_log_update + node_log_update
        old_nodes_deletions = (
            dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.1))
            + dist.Normal(tensor(0.1), tensor(1.0)).log_prob(tensor(0.2))
            + dist.Normal(tensor(0.2), tensor(1.0)).log_prob(tensor(0.2))
            + dist.Normal(tensor(0.2), tensor(0.2)).log_prob(tensor(0.2))
        )
        new_nodes_additions = (
            dist.Normal(tensor(0.0), tensor(1.0)).log_prob(a_value)
            + dist.Normal(a_value, tensor(1.0)).log_prob(b_value)
            + dist.Normal(b_value, tensor(1.0)).log_prob(c_value)
            + dist.Normal(b_value.item(), abs(c_value.item()) + 0.1).log_prob(d_value)
        )
        expected_world_log_update += new_nodes_additions - old_nodes_deletions
        self.assertAlmostEqual(
            world_log_update.item(), expected_world_log_update.item(), places=3
        )

        self.assertEqual(world.diff_.is_marked_for_delete(A_key_0), True)
        self.assertEqual(world.diff_.is_marked_for_delete(B_key_0), True)
        self.assertEqual(world.diff_.is_marked_for_delete(C_key_0), True)
        self.assertEqual(world.diff_.is_marked_for_delete(D_key_0), True)
        self.assertEqual(world.diff_.is_marked_for_delete(A_key_1), False)
        self.assertEqual(world.diff_.is_marked_for_delete(B_key_1), False)
        self.assertEqual(world.diff_.is_marked_for_delete(C_key_1), False)

        world.accept_diff()

        self.assertEqual(A_key_0 in world_vars, False)
        self.assertEqual(B_key_0 in world_vars, False)
        self.assertEqual(C_key_0 in world_vars, False)
        self.assertEqual(D_key_0 in world_vars, False)
        self.assertEqual(A_key_1 in world_vars, True)
        self.assertEqual(B_key_1 in world_vars, True)
        self.assertEqual(C_key_1 in world_vars, True)

    def test_get_world_node(self):
        world = World()
        with self.assertRaises(ValueError):
            world.get_node_in_world_raise_error("test")

    def test_compute_score(self):
        world = World()
        world_vars = world.variables_.vars()
        world_vars["tmp"] = Variable(
            distribution=dist.Normal(tensor(0.2), tensor(0.2)),
            value=tensor(0.2),
            log_prob=dist.Normal(tensor(0.2), tensor(0.2)).log_prob(tensor(0.2)),
            parent=set({}),
            children=set({None}),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.2),
            jacobian=tensor(0.0),
        )
        with self.assertRaises(ValueError):
            world.compute_score(world_vars["tmp"])

    def test_update_graph_small_bar(self):
        model = self.SampleModel()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()

        StatisticalModel.set_mode(Mode.INFERENCE)
        world.update_graph(bar_key)

        foo_expected_parent = set()
        foo_expected_children = set({bar_key})
        bar_expected_parent = set({foo_key})
        bar_expected_children = set()

        self.assertEqual(foo_expected_children, world.diff_.get_node(foo_key).children)
        self.assertEqual(foo_expected_parent, world.diff_.get_node(foo_key).parent)
        self.assertEqual(bar_expected_children, world.diff_.get_node(bar_key).children)
        self.assertEqual(bar_expected_parent, world.diff_.get_node(bar_key).parent)

        foo_expected_dist = dist.Normal(tensor(0.0), tensor(1.0))
        bar_expected_dist = dist.Normal(
            world.diff_.get_node(foo_key).value, tensor(1.0)
        )

        self.assertEqual(
            foo_expected_dist.mean, world.diff_.get_node(foo_key).distribution.mean
        )
        self.assertEqual(
            foo_expected_dist.stddev, world.diff_.get_node(foo_key).distribution.stddev
        )
        self.assertEqual(
            bar_expected_dist.mean, world.diff_.get_node(bar_key).distribution.mean
        )
        self.assertEqual(
            bar_expected_dist.stddev, world.diff_.get_node(bar_key).distribution.stddev
        )

    def test_update_graph_small_foo(self):
        model = self.SampleModel()
        world = StatisticalModel.reset()
        foo_key = model.foo()

        StatisticalModel.set_mode(Mode.INFERENCE)
        world.update_graph(foo_key)

        foo_expected_parent = set()
        foo_expected_children = set()

        self.assertEqual(foo_expected_children, world.diff_.get_node(foo_key).children)
        self.assertEqual(foo_expected_parent, world.diff_.get_node(foo_key).parent)

    def test_update_graph_parent_update(self):
        model = self.SampleModelWithParentUpdate()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()
        baz_key = model.baz()

        StatisticalModel.set_mode(Mode.INFERENCE)
        world.update_graph(foo_key)
        world.update_graph(bar_key)
        world.update_graph(baz_key)
        world.accept_diff()

        world.propose_change(foo_key, tensor(0.8))

        foo_expected_parent = set()
        foo_expected_children = set({bar_key})
        bar_expected_parent = set({foo_key})
        bar_expected_children = set()

        self.assertEqual(foo_expected_children, world.diff_.get_node(foo_key).children)
        self.assertEqual(foo_expected_parent, world.diff_.get_node(foo_key).parent)
        self.assertEqual(bar_expected_children, world.diff_.get_node(bar_key).children)
        self.assertEqual(bar_expected_parent, world.diff_.get_node(bar_key).parent)

        world.accept_diff()

        world.propose_change(foo_key, tensor(0.2))

        foo_expected_parent = set()
        foo_expected_children = set({bar_key})
        baz_expected_parent = set()
        baz_expected_children = set({bar_key})
        bar_expected_parent = set({foo_key, baz_key})
        bar_expected_children = set()

        self.assertEqual(foo_expected_children, world.diff_.get_node(foo_key).children)
        self.assertEqual(foo_expected_parent, world.diff_.get_node(foo_key).parent)
        self.assertEqual(baz_expected_children, world.diff_.get_node(baz_key).children)
        self.assertEqual(baz_expected_parent, world.diff_.get_node(baz_key).parent)
        self.assertEqual(bar_expected_children, world.diff_.get_node(bar_key).children)
        self.assertEqual(bar_expected_parent, world.diff_.get_node(bar_key).parent)

    def test_world_propose_change_score(self):
        model = self.SampleModel()
        world = StatisticalModel.reset()
        foo_key = model.foo()
        bar_key = model.bar()
        StatisticalModel.set_mode(Mode.INFERENCE)

        world_vars = world.variables_.vars()
        world.set_observations({bar_key: tensor(0.1)})
        world_vars[foo_key] = Variable(
            distribution=dist.Normal(tensor(0.0), tensor(1.0)),
            value=tensor(0.5),
            log_prob=dist.Normal(tensor(0.0), tensor(1.0)).log_prob(tensor(0.5)),
            parent=set(),
            children=set({bar_key}),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.5),
            jacobian=tensor(0.0),
        )
        world_vars[bar_key] = Variable(
            distribution=dist.Normal(tensor(0.5), tensor(1.0)),
            value=tensor(0.1),
            log_prob=dist.Normal(tensor(0.5), tensor(1.0)).log_prob(tensor(0.1)),
            parent=set({foo_key}),
            children=set(),
            proposal_distribution=None,
            extended_val=None,
            is_discrete=False,
            transforms=[],
            unconstrained_value=tensor(0.1),
            jacobian=tensor(0.0),
        )

        score = world.propose_change(foo_key, tensor(0.25))[3]
        expected_score = dist.Normal(0, 1).log_prob(0.25) + dist.Normal(
            0.25, 1.0
        ).log_prob(0.1)
        self.assertAlmostEqual(score, expected_score)
