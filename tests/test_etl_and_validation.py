import unittest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.engine.base_trainer import BaseTrainer
from core.models.base_event import BaseEvent

class DummyTrainer(BaseTrainer):
    def train_walk_forward(self, historical_events, validation_steps):
        pass
    def get_feature_importance(self):
        return {}

class TestValidation(unittest.TestCase):
    
    def setUp(self):
        self.trainer = DummyTrainer(model=None)
        
    def test_walk_forward_splits(self):
        splits = self.trainer.generate_walk_forward_splits(2008, 2010, step_years=1)
        self.assertEqual(len(splits), 2)
        
        self.assertEqual(splits[0]["train_start_year"], 2008)
        self.assertEqual(splits[0]["train_end_year"], 2008)
        self.assertEqual(splits[0]["test_start_year"], 2009)
        self.assertEqual(splits[0]["test_end_year"], 2009)
        
        self.assertEqual(splits[1]["train_start_year"], 2008)
        self.assertEqual(splits[1]["train_end_year"], 2009)
        self.assertEqual(splits[1]["test_start_year"], 2010)
        self.assertEqual(splits[1]["test_end_year"], 2010)

    def test_leakage_detection(self):
        train_events = [BaseEvent(id="1", date=datetime(2020, 1, 1), location="a", participants=["A", "B"])]
        test_events = [BaseEvent(id="2", date=datetime(2019, 12, 31), location="a", participants=["A", "B"])]
        
        with self.assertRaises(ValueError) as context:
            self.trainer._verify_no_leakage(train_events, test_events)
            
        self.assertTrue("CRITICAL: Data Leakage Detected" in str(context.exception))
        
    def test_no_leakage(self):
        train_events = [BaseEvent(id="1", date=datetime(2019, 12, 31), location="a", participants=["A", "B"])]
        test_events = [BaseEvent(id="2", date=datetime(2020, 1, 1), location="a", participants=["A", "B"])]
        
        # Should not raise exception
        self.trainer._verify_no_leakage(train_events, test_events)

if __name__ == '__main__':
    unittest.main()
