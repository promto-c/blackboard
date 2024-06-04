import pytest
from qtpy import QtGui
from blackboard.utils.color_utils import ColorUtils

@pytest.mark.parametrize(
    "color1, color2, expected_color",
    [
        (QtGui.QColor(255, 0, 0, 255), QtGui.QColor(0, 0, 255, 255), QtGui.QColor(127, 0, 127, 255)),  # Fully opaque colors
        (QtGui.QColor(255, 0, 0, 0), QtGui.QColor(0, 0, 255, 255), QtGui.QColor(0, 0, 255, 255)),  # One fully transparent, one fully opaque
        (QtGui.QColor(255, 0, 0, 128), QtGui.QColor(0, 0, 255, 128), QtGui.QColor(127, 0, 127, 255)),  # Both half-transparent
        (QtGui.QColor(255, 0, 0, 0), QtGui.QColor(0, 0, 255, 0), QtGui.QColor(0, 0, 0, 0)),  # Both fully transparent
        (QtGui.QColor(255, 0, 0, 100), QtGui.QColor(0, 0, 255, 200), QtGui.QColor(85, 0, 170, 255)),  # Different alpha values
    ]
)
def test_blend_colors(color1, color2, expected_color):
    result = ColorUtils.blend_colors(color1, color2)
    assert result == expected_color, f"Expected {expected_color}, got {result}"

if __name__ == "__main__":
    pytest.main()
