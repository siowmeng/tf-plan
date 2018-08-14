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


from pyrddl.parser import RDDLParser
from tfrddlsim.compiler import Compiler

from tfplan.planners.online_plan import OnlinePlanning
from tfplan.planners.open_loop_planner import OpenLoopPlanner

import numpy as np
import tensorflow as tf

import unittest


class TestOnlinePlanning(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        parser = RDDLParser()
        parser.build()

        with open('rddl/Navigation.rddl', mode='r') as file:
            NAVIGATION = file.read()
            cls.rddl = parser.parse(NAVIGATION)

        cls.compiler = Compiler(cls.rddl, batch_mode=True)
        cls.initial_state = cls.compiler.compile_initial_state(batch_size=1)
        cls.default_action = cls.compiler.compile_default_action(batch_size=1)

        batch_size = 128
        cls.horizon = 10
        planner = OpenLoopPlanner(cls.compiler, batch_size, cls.horizon)
        planner.build(learning_rate=0.05)
        cls.online_planner = OnlinePlanning(cls.compiler, planner)
        cls.online_planner.build()

    @unittest.skip('not implemented')
    def test_planning_graph(self):
        self.fail()

    def test_execution_graph(self):
        action = self.online_planner.action
        self.assertIsInstance(action, tuple)
        self.assertEqual(len(action), len(self.default_action))
        self.assertTrue(all(isinstance(fluent, tf.Tensor) for fluent in action))
        for action_fluent, default_action_fluent in zip(action, self.default_action):
            self.assertEqual(action_fluent.shape, default_action_fluent.shape)
            self.assertEqual(action_fluent.dtype, default_action_fluent.dtype)

        state = self.online_planner.state
        self.assertIsInstance(state, tuple)
        self.assertEqual(len(state), len(self.initial_state))
        self.assertTrue(all(isinstance(fluent, tf.Tensor) for fluent in state))
        for state_fluent, initial_state_fluent in zip(state, self.initial_state):
            self.assertEqual(state_fluent.shape, initial_state_fluent.shape)
            self.assertEqual(state_fluent.dtype, initial_state_fluent.dtype)

        next_state = self.online_planner.next_state
        self.assertIsInstance(next_state, tuple)
        self.assertEqual(len(next_state), len(self.initial_state))
        self.assertTrue(all(isinstance(fluent, tf.Tensor) for fluent in next_state))
        for state_fluent, initial_state_fluent in zip(next_state, self.initial_state):
            self.assertEqual(state_fluent.shape, initial_state_fluent.shape)
            self.assertEqual(state_fluent.dtype, initial_state_fluent.dtype)

        reward = self.online_planner.reward
        self.assertIsInstance(reward, tuple)
        self.assertEqual(len(reward), 1)
        self.assertIsInstance(reward[0], tf.Tensor)
        self.assertListEqual(reward[0].shape.as_list(), [1, 1])
        self.assertEqual(reward[0].dtype, tf.float32)

    @unittest.skip('not implemented')
    def test_monitoring_graph(self):
        self.fail()

    def test_online_planning_cycle(self):
        initial_state, states, actions, rewards = self.online_planner.run(self.initial_state, self.horizon, epochs=10, show_progress=False)
        self.assertEqual(len(states), self.horizon)
        self.assertEqual(len(actions), self.horizon)
        self.assertEqual(len(rewards), self.horizon)

        for state in states:
            self.assertIsInstance(state, tuple)
            self.assertEqual(len(state), len(self.initial_state))
            self.assertTrue(all(isinstance(fluent, np.ndarray) for fluent in state))
            for state_fluent, initial_state_fluent in zip(state, self.initial_state):
                self.assertEqual(state_fluent.shape, initial_state_fluent.shape)
                if initial_state_fluent.dtype == tf.float32:
                    self.assertEqual(state_fluent.dtype, np.float32)
                elif initial_state_fluent.dtype == tf.int32:
                    self.assertEqual(state_fluent.dtype, np.int32)
                elif initial_state_fluent.dtype == tf.bool:
                    self.assertEqual(state_fluent.dtype, np.bool)

        for action in actions:
            self.assertIsInstance(action, tuple)
            self.assertEqual(len(action), len(self.default_action))
            self.assertTrue(all(isinstance(fluent, np.ndarray) for fluent in action))
            for action_fluent, default_action in zip(action, self.default_action):
                self.assertEqual(action_fluent.shape, default_action.shape)
                if default_action.dtype == tf.float32:
                    self.assertEqual(action_fluent.dtype, np.float32)
                elif default_action.dtype == tf.int32:
                    self.assertEqual(action_fluent.dtype, np.int32)
                elif default_action.dtype == tf.bool:
                    self.assertEqual(action_fluent.dtype, np.bool)