import pytest
from PyQt5 import QtGui, QtCore
from blackboard.utils.tree_utils import TreeUtil  # Adjust the import according to your project structure

# Constants for test data
CHILD_1_TEXT = "Child 1"
CHILD_2_TEXT = "Child 2"
LEAF_1_TEXT = "Leaf 1"

@pytest.fixture
def sample_model():
    """Fixture to create a sample model with a predefined structure."""
    model = QtGui.QStandardItemModel()
    root = model.invisibleRootItem()

    # Add some items to the model
    child1 = QtGui.QStandardItem(CHILD_1_TEXT)
    child1.setCheckable(True)
    child1.setCheckState(QtCore.Qt.CheckState.Checked)

    child2 = QtGui.QStandardItem(CHILD_2_TEXT)
    child2.setCheckable(True)
    child2.setCheckState(QtCore.Qt.CheckState.Unchecked)

    leaf1 = QtGui.QStandardItem(LEAF_1_TEXT)
    leaf1.setCheckable(True)
    leaf1.setCheckState(QtCore.Qt.CheckState.Checked)

    child1.appendRow(leaf1)
    root.appendRow(child1)
    root.appendRow(child2)

    return model

def assert_items_data(model, indexes, expected_texts):
    """Helper function to assert the data of indexes."""
    assert len(indexes) == len(expected_texts)
    actual_texts = [model.data(index, QtCore.Qt.ItemDataRole.DisplayRole) for index in indexes]
    assert set(actual_texts) == set(expected_texts)

def assert_data_list(data_list, expected_texts):
    """Helper function to assert the data list."""
    assert len(data_list) == len(expected_texts)
    assert set(data_list) == set(expected_texts)

def test_only_checked(sample_model):
    """Test that only checked items are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, is_only_checked=True)
    assert_items_data(sample_model, indexes, [CHILD_1_TEXT, LEAF_1_TEXT])

def test_only_leaf(sample_model):
    """Test that only leaf nodes are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, is_only_leaf=True)
    assert_items_data(sample_model, indexes, [LEAF_1_TEXT, CHILD_2_TEXT])

def test_data_match(sample_model):
    """Test that items matching specific data are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, data_match=(QtCore.Qt.ItemDataRole.DisplayRole, LEAF_1_TEXT))
    assert_items_data(sample_model, indexes, [LEAF_1_TEXT])

def test_get_model_data_list(sample_model):
    """Test that get_model_data_list returns the correct data."""
    data_list = TreeUtil.get_model_data_list(sample_model, column=0, is_only_leaf=True)
    assert_data_list(data_list, [LEAF_1_TEXT, CHILD_2_TEXT])
