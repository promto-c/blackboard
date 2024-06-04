import pytest
import numpy as np
from blackboard.utils.qimage_utils import ThumbnailUtils


@pytest.mark.parametrize("image_data, expected_output", [
    (np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float32),
     np.array([[  0,  31,  63],
               [ 95, 127, 159],
               [191, 223, 255]], dtype=np.uint8)),

    (np.zeros((3, 3), dtype=np.float32),
     np.zeros((3, 3), dtype=np.uint8)),

    (np.ones((3, 3), dtype=np.float32) * 5,
     np.ones((3, 3), dtype=np.uint8) * 255),

    (np.array([[0, 5, 10], [15, 20, 25], [30, 35, 40]], dtype=np.float32),
     np.array([[  0,  31,  63],
               [ 95, 127, 159],
               [191, 223, 255]], dtype=np.uint8)),

    (np.array([[-10, 0, 10], [-20, -10, 0], [10, 20, 30]], dtype=np.float32),
     np.array([[ 51, 102, 153],
               [  0,  51, 102],
               [153, 204, 255]], dtype=np.uint8)),

    (np.array([[0, 32767, 65535], [16383, 32767, 49151], [8191, 24575, 40959]], dtype=np.uint16),
     np.array([[  0, 127, 255],
               [ 64, 127, 191],
               [ 32,  96, 159]], dtype=np.uint8)),

    (np.array([[0.2, 0.4, 0.6], [0.2, 0.4, 0.6], [0.2, 0.4, 0.6]], dtype=np.float32),
     np.array([[  51, 102, 153],
               [  51, 102, 153],
               [  51, 102, 153]], dtype=np.uint8)),
    ])
def test_normalize_to_uint8(image_data, expected_output):
    # Call the method
    result = ThumbnailUtils.normalize_to_uint8(image_data)
    
    # Assert that the result matches the expected output
    np.testing.assert_array_equal(result, expected_output)

if __name__ == "__main__":
    pytest.main()
