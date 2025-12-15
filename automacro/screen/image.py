import pyautogui as pag

# PyAutoGUI uses physical coordinates for pixel operations, so we need to
# rescale coordinates accordingly.
from automacro.screen.coordinates import scale_box, center

try:
    import cv2  # noqa: F401

    _has_cv = True
except ImportError:
    _has_cv = False


def locate_image(
    image_path: str,
    *,
    confidence: float = 0.999,
    grayscale: bool = False,
    region: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """
    Locate an image on the screen.

    Args:
        image_path (str): The file path of the image to locate.
        confidence (float): The confidence level for the match (0.0 to 1.0).
        Default is 0.999.
        grayscale (bool): Whether to convert the image to grayscale for
        matching. Setting to True can improve performance, but may result
        in false-positives. Default is False.
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to limit the search area on the screen. Default is None.

    Returns:
        tuple[int, int, int, int] | None: The (left, top, width, height) of first
        found instance of the image, otherwise None if not found on screen.
    """

    if not _has_cv:
        raise NotImplementedError(
            "This function is only available if OpenCV is installed."
        )

    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")

    try:
        if region:
            region = scale_box(*region)
        instance = pag.locateOnScreen(
            image_path, confidence=confidence, grayscale=grayscale, region=region
        )
        return scale_box(*instance, inverse=True) if instance else None
    except pag.ImageNotFoundException:
        return None


def locate_image_center(
    image_path: str,
    *,
    confidence: float = 0.999,
    grayscale: bool = False,
    region: tuple[int, int, int, int] | None = None,
) -> tuple[int, int] | None:
    """
    Locate the center of an image on the screen.

    Args:
        image_path (str): The file path of the image to locate.
        confidence (float): The confidence level for the match (0.0 to 1.0).
        Default is 0.999.
        grayscale (bool): Whether to convert the image to grayscale for
        matching. Setting to True can improve performance, but may result
        in false-positives. Default is False.
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to limit the search area on the screen. Default is None.

    Returns:
        tuple[int, int] | None: The (x, y) coordinates of the center of the first
        found instance of the image, otherwise None if not found on screen.
    """

    instance = locate_image(
        image_path, confidence=confidence, grayscale=grayscale, region=region
    )
    if instance:
        return center(*instance)
    else:
        return None


def locate_image_all(
    image_path: str,
    *,
    confidence: float = 0.999,
    threshold: int = 10,
    grayscale: bool = False,
    region: tuple[int, int, int, int] | None = None,
) -> list[tuple[int, int, int, int]]:
    """
    Locate all instances of an image on the screen.

    Args:
        image_path (str): The file path of the image to locate.
        confidence (float): The confidence level for the match (0.0 to 1.0).
        Default is 0.999.
        threshold (int): The minimum distance threshold in pixels between
        found instances to consider them separate. Default is 10.
        grayscale (bool): Whether to convert the image to grayscale for
        matching. Setting to True can improve performance, but may result
        in false-positives. Default is False.
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to limit the search area on the screen. Default is None.

    Returns:
        list[tuple[int, int, int, int]]: A list of (left, top, width, height)
        tuples for each found instance of the image. Empty list if none found.
    """

    if not _has_cv:
        raise NotImplementedError(
            "This function is only available if OpenCV is installed."
        )

    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("Confidence must be between 0.0 and 1.0")

    try:
        if region:
            region = scale_box(*region)
        instances = pag.locateAllOnScreen(
            image_path, confidence=confidence, grayscale=grayscale, region=region
        )
        # Rescale instances to logical coordinates
        instances = [scale_box(*instance, inverse=True) for instance in instances]

        uniques = []

        # Small optimization to avoid computing square roots
        distance_sq = pow(threshold, 2)

        # Filter out instances that are within the threshold distance of each other
        for i in instances:
            if all(
                map(
                    lambda u: pow(i[0] - u[0], 2) + pow(i[1] - u[1], 2) > distance_sq,
                    uniques,
                )
            ):
                uniques.append(i)

        return uniques
    except pag.ImageNotFoundException:
        return []


def locate_image_center_all(
    image_path: str,
    *,
    confidence: float = 0.999,
    threshold: int = 10,
    grayscale: bool = False,
    region: tuple[int, int, int, int] | None = None,
) -> list[tuple[int, int]]:
    """
    Locate the centers of all instances of an image on the screen.

    Args:
        image_path (str): The file path of the image to locate.
        confidence (float): The confidence level for the match (0.0 to 1.0).
        Default is 0.999.
        threshold (int): The minimum distance threshold in pixels between
        found instances to consider them separate. Default is 10.
        grayscale (bool): Whether to convert the image to grayscale for
        matching. Setting to True can improve performance, but may result
        in false-positives. Default is False.
        region (tuple[int, int, int, int] | None): A region (left, top, width,
        height) to limit the search area on the screen. Default is None.

    Returns:
        list[tuple[int, int]]: A list of (x, y) coordinates for the center of
        each found instance of the image. Empty list if none found.
    """

    instances = locate_image_all(
        image_path,
        confidence=confidence,
        threshold=threshold,
        grayscale=grayscale,
        region=region,
    )
    return [center(*instance) for instance in instances]
