# This file is part of tf-plan.

# tf-plan is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# tf-plan is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with tf-plan. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=missing-docstring,redefined-outer-name


from collections import OrderedDict
import pytest
import tensorflow as tf

import rddlgym
from tfplan.planners import DEFAULT_CONFIG, StraightLinePlanner


@pytest.fixture(scope="module")
def rddl():
    return "Navigation-v2"


@pytest.fixture(scope="module")
def env(rddl):
    return rddlgym.make(rddl, mode=rddlgym.GYM)


@pytest.fixture(scope="module")
def planner(rddl):
    model = rddlgym.make(rddl, mode=rddlgym.AST)
    config = {**DEFAULT_CONFIG, **{"epochs": 10}}
    planner_ = StraightLinePlanner(model, config)
    planner_.build(model.instance.horizon)
    return planner_


def test_build_policy_ops(planner):
    policy = planner.policy
    compiler = planner.compiler
    assert not policy.parallel_plans
    assert policy.horizon == compiler.rddl.instance.horizon
    assert hasattr(policy, "_policy_variables")


def test_build_initial_state_ops(planner):
    initial_state = planner.initial_state
    compiler = planner.compiler
    batch_size = compiler.batch_size
    assert isinstance(initial_state, tuple)
    assert len(initial_state) == len(compiler.initial_state_fluents)
    for tensor, fluent in zip(initial_state, compiler.initial_state_fluents):
        assert tensor.dtype == fluent[1].dtype
        assert tensor.shape == (batch_size, *fluent[1].shape.fluent_shape)


def test_build_trajectory_ops(planner):
    trajectory = planner.trajectory
    actions = trajectory.actions

    batch_size = planner.compiler.batch_size
    horizon = planner.compiler.rddl.instance.horizon
    action_fluents = planner.compiler.default_action_fluents

    for action, action_fluent in zip(actions, action_fluents):
        size = action_fluent[1].shape.as_list()
        assert action.shape.as_list() == [batch_size, horizon, *size]


def test_call(planner, env):
    state, timestep = env.reset()
    action = planner(state, timestep)
    assert isinstance(action, OrderedDict)


def test_get_batch_initial_state(planner, env):
    # pylint: disable=protected-access
    with planner.compiler.graph.as_default():
        state = env.observation_space.sample()

        batch_state = planner._get_batch_initial_state(state)
        assert len(state) == len(batch_state)

        for fluent, batch_fluent in zip(state.values(), batch_state):
            assert fluent.dtype == batch_fluent.dtype
            assert fluent.shape == batch_fluent.shape[1:]
            assert batch_fluent.shape[0] == planner.compiler.batch_size


def test_get_noise_samples(planner):
    # pylint: disable=protected-access
    with tf.Session(graph=planner.compiler.graph) as sess:
        samples_ = planner._get_noise_samples(sess)
        assert planner.simulator.noise.dtype == samples_.dtype
        assert planner.simulator.noise.shape.as_list() == list(samples_.shape)


def test_get_action(planner, env):
    # pylint: disable=protected-access
    with tf.Session(graph=planner.compiler.graph) as sess:
        sess.run(tf.global_variables_initializer())
        state = env.observation_space.sample()
        batch_state = planner._get_batch_initial_state(state)
        samples = planner._get_noise_samples(sess)
        feed_dict = {
            planner.initial_state: batch_state,
            planner.simulator.noise: samples,
        }
        actions_ = planner._get_action(sess, feed_dict)
        action_fluents = planner.compiler.default_action_fluents
        assert isinstance(actions_, OrderedDict)
        assert len(actions_) == len(action_fluents)
        for action_, action_fluent in zip(actions_.values(), action_fluents):
            assert tf.dtypes.as_dtype(action_.dtype) == action_fluent[1].dtype
            assert list(action_.shape) == list(action_fluent[1].shape.fluent_shape)
