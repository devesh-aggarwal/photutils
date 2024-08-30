# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for the core module.
"""

from contextlib import nullcontext

import numpy as np
import pytest
from astropy.modeling.models import Gaussian1D, Gaussian2D
from astropy.utils.exceptions import AstropyUserWarning
from numpy.testing import assert_allclose

from photutils.centroids.gaussian import (_gaussian1d_moments, centroid_1dg,
                                          centroid_2dg)
from photutils.utils._optional_deps import HAS_SCIPY


@pytest.fixture(name='test_data')
def fixture_test_data():
    xcen = 25.7
    ycen = 26.2
    data = np.zeros((3, 3))
    data[0:2, 1] = 1.0
    data[1, 0:2] = 1.0
    data[1, 1] = 2.0
    return data, xcen, ycen


# NOTE: the fitting routines in astropy use scipy.optimize
@pytest.mark.skipif(not HAS_SCIPY, reason='scipy is required')
@pytest.mark.parametrize('x_std', [3.2, 4.0])
@pytest.mark.parametrize('y_std', [5.7, 4.1])
@pytest.mark.parametrize('theta', np.deg2rad([30.0, 45.0]))
def test_centroids(test_data, x_std, y_std, theta):
    data, xcen, ycen = test_data

    model = Gaussian2D(2.4, xcen, ycen, x_stddev=x_std, y_stddev=y_std,
                       theta=theta)
    y, x = np.mgrid[0:50, 0:47]
    data = model(x, y)
    xc, yc = centroid_1dg(data)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)
    xc, yc = centroid_2dg(data)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)

    # test with errors
    error = np.sqrt(data)
    xc, yc = centroid_1dg(data, error=error)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)
    xc, yc = centroid_2dg(data, error=error)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)

    # test with mask
    mask = np.zeros(data.shape, dtype=bool)
    data[10, 10] = 1.0e5
    mask[10, 10] = True
    xc, yc = centroid_1dg(data, mask=mask)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)
    xc, yc = centroid_2dg(data, mask=mask)
    assert_allclose((xc, yc), (xcen, ycen), rtol=0, atol=1.0e-3)


@pytest.mark.skipif(not HAS_SCIPY, reason='scipy is required')
@pytest.mark.parametrize('use_mask', [True, False])
def test_centroids_nan_withmask(use_mask):
    xc_ref = 24.7
    yc_ref = 25.2
    model = Gaussian2D(2.4, xc_ref, yc_ref, x_stddev=5.0, y_stddev=5.0)
    y, x = np.mgrid[0:50, 0:50]
    data = model(x, y)
    data[20, :] = np.nan
    if use_mask:
        mask = np.zeros(data.shape, dtype=bool)
        mask[20, :] = True
        nwarn = 0
        ctx = nullcontext()
    else:
        mask = None
        nwarn = 1
        match = 'Input data contains non-finite values'
        ctx = pytest.warns(AstropyUserWarning, match=match)

    with ctx as warnlist:
        xc, yc = centroid_1dg(data, mask=mask)
        assert_allclose([xc, yc], [xc_ref, yc_ref], rtol=0, atol=1.0e-3)
        if nwarn == 1:
            assert len(warnlist) == nwarn

    with ctx as warnlist:
        xc, yc = centroid_2dg(data, mask=mask)
        assert_allclose([xc, yc], [xc_ref, yc_ref], rtol=0, atol=1.0e-3)
        if nwarn == 1:
            assert len(warnlist) == nwarn


@pytest.mark.skipif(not HAS_SCIPY, reason='scipy is required')
def test_invalid_mask_shape():
    data = np.zeros((4, 4))
    mask = np.zeros((2, 2), dtype=bool)

    match = 'data and mask must have the same shape'
    with pytest.raises(ValueError, match=match):
        centroid_1dg(data, mask=mask)
    with pytest.raises(ValueError, match=match):
        centroid_2dg(data, mask=mask)
    with pytest.raises(ValueError, match=match):
        _gaussian1d_moments(data, mask=mask)


@pytest.mark.skipif(not HAS_SCIPY, reason='scipy is required')
def test_invalid_error_shape():
    error = np.zeros((2, 2), dtype=bool)
    match = 'data and error must have the same shape'
    with pytest.raises(ValueError, match=match):
        centroid_1dg(np.zeros((4, 4)), error=error)
    with pytest.raises(ValueError, match=match):
        centroid_2dg(np.zeros((4, 4)), error=error)


@pytest.mark.skipif(not HAS_SCIPY, reason='scipy is required')
def test_centroid_2dg_dof():
    data = np.ones((2, 2))
    match = 'Input data must have a least 7 unmasked values to fit'
    with pytest.raises(ValueError, match=match):
        centroid_2dg(data)


def test_gaussian1d_moments():
    x = np.arange(100)
    desired = (75, 50, 5)
    g = Gaussian1D(*desired)
    data = g(x)
    result = _gaussian1d_moments(data)
    assert_allclose(result, desired, rtol=0, atol=1.0e-6)

    data[0] = 1.0e5
    mask = np.zeros(data.shape).astype(bool)
    mask[0] = True
    result = _gaussian1d_moments(data, mask=mask)
    assert_allclose(result, desired, rtol=0, atol=1.0e-6)

    data[0] = np.nan
    mask = np.zeros(data.shape).astype(bool)
    mask[0] = True

    match = 'Input data contains non-finite values'
    ctx = pytest.warns(AstropyUserWarning, match=match)
    with ctx as warnlist:
        result = _gaussian1d_moments(data, mask=mask)
        assert_allclose(result, desired, rtol=0, atol=1.0e-6)
        assert len(warnlist) == 1
