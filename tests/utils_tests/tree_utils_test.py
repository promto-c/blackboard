import pytest
from PyQt5 import QtGui, QtCore
from blackboard.utils.tree_utils import TreeUtil  # Adjust the import according to your project structure

@pytest.fixture
def sample_model():
    model = QtGui.QStandardItemModel()
    root = model.invisibleRootItem()

    # Add some items to the model
    child1 = QtGui.QStandardItem("Child 1")
    child1.setCheckable(True)
    child1.setCheckState(QtCore.Qt.Checked)

    child2 = QtGui.QStandardItem("Child 2")
    child2.setCheckable(True)
    child2.setCheckState(QtCore.Qt.Unchecked)

    leaf1 = QtGui.QStandardItem("Leaf 1")
    leaf1.setCheckable(True)
    leaf1.setCheckState(QtCore.Qt.Checked)

    child1.appendRow(leaf1)
    root.appendRow(child1)
    root.appendRow(child2)

    return model

def test_only_checked(sample_model):
    """Test that only checked items are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, is_only_checked=True)
    assert len(indexes) == 2  # Child 1 and Leaf 1 are checked
    assert all([sample_model.data(index, QtCore.Qt.DisplayRole) in ["Child 1", "Leaf 1"] for index in indexes])

def test_only_leaf(sample_model):
    """Test that only leaf nodes are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, is_only_leaf=True)
    assert len(indexes) == 2
    assert sample_model.data(indexes[0], QtCore.Qt.DisplayRole) == "Leaf 1"

def test_data_match(sample_model):
    """Test that items matching specific data are returned."""
    indexes = TreeUtil.get_model_indexes(sample_model, data_match=(QtCore.Qt.DisplayRole, "Leaf 1"))
    assert len(indexes) == 1
    assert sample_model.data(indexes[0], QtCore.Qt.DisplayRole) == "Leaf 1"
