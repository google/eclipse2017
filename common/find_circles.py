import cv2
from common.geometry import getRescaledDimensions
HD_MAX_X = 1920
HD_MAX_Y = 1080

def findCircles(image):
    image_cols, image_rows, _ = image.shape

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    first, second = getRescaledDimensions(gray.shape[1], gray.shape[0], HD_MAX_X, HD_MAX_Y)
    gray = cv2.resize(gray, (first, second))
    blurred = cv2.bilateralFilter(gray, 9, 75, 75)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # # detect circles in the image
    dp = 1
    c1 = 100
    c2 = 15
    circles = cv2.HoughCircles(gray, cv2.cv.CV_HOUGH_GRADIENT, dp, second / 8, param1=c1, param2=c2)
    if not len(circles):
        return None
    return circles[0][0]
