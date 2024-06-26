# Third Party Imports
# -------------------
from qtpy import QtGui


# Class Definitions
# -----------------
class ColorUtils:

    @staticmethod
    def blend_colors(color1: QtGui.QColor, color2: QtGui.QColor) -> QtGui.QColor:
        """Blend two QColor objects using the weight of their alpha values.

        Args:
            color1 (QtGui.QColor): The first color.
            color2 (QtGui.QColor): The second color.

        Returns:
            QtGui.QColor: The resulting blended color.

        Examples:
            >>> from qtpy import QtGui
            >>> color1 = QtGui.QColor(255, 0, 0, 255)
            >>> color2 = QtGui.QColor(0, 0, 255, 255)
            >>> ColorUtils.blend_colors(color1, color2).getRgb()
            (127, 0, 127, 255)

            >>> color1 = QtGui.QColor(255, 0, 0, 0)
            >>> color2 = QtGui.QColor(0, 0, 255, 255)
            >>> ColorUtils.blend_colors(color1, color2).getRgb()
            (0, 0, 255, 255)

            >>> color1 = QtGui.QColor(255, 0, 0, 100)
            >>> color2 = QtGui.QColor(0, 0, 255, 200)
            >>> ColorUtils.blend_colors(color1, color2).getRgb()
            (85, 0, 170, 255)
        """
        r1, g1, b1, a1 = color1.getRgb()
        r2, g2, b2, a2 = color2.getRgb()

        # Return transparent color if total alpha is zero
        total_alpha = a1 + a2
        if total_alpha == 0:
            return QtGui.QColor(0, 0, 0, 0)

        # Blend the RGB components using the alpha weights
        r = min((r1 * a1 + r2 * a2) // total_alpha, 255)
        g = min((g1 * a1 + g2 * a2) // total_alpha, 255)
        b = min((b1 * a1 + b2 * a2) // total_alpha, 255)

        # The alpha of the resulting color is the sum of the alphas (clamped to 255)
        a = min(total_alpha, 255)

        return QtGui.QColor(r, g, b, a)

    @staticmethod
    def create_pastel_color(color: QtGui.QColor, saturation: float = 0.4, value: float = 0.9) -> QtGui.QColor:
        """Create a pastel version of the given color.

        Args:
            color (QtGui.QColor): The original color.
            saturation (float): The desired saturation factor (default: 0.4).
            value (float): The desired value/brightness factor (default: 0.9).

        Returns:
            QtGui.QColor: The pastel color.
        """
        h, s, v, a = color.getHsvF()

        # Decrease saturation and value to achieve a more pastel look
        s *= saturation
        v *= value

        pastel_color = QtGui.QColor.fromHsvF(h, s, v, a)
        return pastel_color


if __name__ == "__main__":
    import doctest
    doctest.testmod()
