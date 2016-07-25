#!/usr/bin/env python
# -*- coding: utf-8 -*-

# #########################################################################
# Copyright (c) 2016, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2016. UChicago Argonne, LLC. This software was produced       #
# under U.S. Government contract DE-AC02-06CH11357 for Argonne National   #
# Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    #
# U.S. Department of Energy. The U.S. Government has rights to use,       #
# reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    #
# UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        #
# ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     #
# modified to produce derivative works, such modified software should     #
# be clearly marked, so as not to confuse it with the version available   #
# from ANL.                                                               #
#                                                                         #
# Additionally, redistribution and use in source and binary forms, with   #
# or without modification, are permitted provided that the following      #
# conditions are met:                                                     #
#                                                                         #
#     * Redistributions of source code must retain the above copyright    #
#       notice, this list of conditions and the following disclaimer.     #
#                                                                         #
#     * Redistributions in binary form must reproduce the above copyright #
#       notice, this list of conditions and the following disclaimer in   #
#       the documentation and/or other materials provided with the        #
#       distribution.                                                     #
#                                                                         #
#     * Neither the name of UChicago Argonne, LLC, Argonne National       #
#       Laboratory, ANL, the U.S. Government, nor the names of its        #
#       contributors may be used to endorse or promote products derived   #
#       from this software without specific prior written permission.     #
#                                                                         #
# THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     #
# Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        #
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    #
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        #
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      #
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       #
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         #
# POSSIBILITY OF SUCH DAMAGE.                                             #
# #########################################################################

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import numpy as np
import scipy.ndimage
import logging

logger = logging.getLogger(__name__)

__author__ = "Doga Gursoy"
__copyright__ = "Copyright (c) 2016, UChicago Argonne, LLC."
__docformat__ = 'restructuredtext en'
__all__ = ['background_mask']

class ImageQuality(object):
    """Stores information about image quality

    Attributes
    ----------------
    orig : numpy.ndarray
    recon : numpy.ndarray
    qualities : list of scalars
    maps : list of numpy.ndarray
    scales : list of scalars
    """
    def __init__(self, original, reconstruction):
        self.orig = original.astype(np.float)
        self.recon = reconstruction.astype(np.float)
        assert(self.orig.shape == self.recon.shape)
        assert(self.orig.ndim == 2)
        self.qualities = []
        self.maps = []
        self.scales = []

    def __str__(self):
        return "QUALITY: " + str(self.qualities) + "\nSCALES: " + str(self.scales)

    def __add__(self, other):
        self.qualities += other.qualities
        self.maps += other.maps
        self.scales += other.scales
        return self

    def add_quality(self,quality,scale,maps=None):
        '''
        Parameters
        -----------
        quality : scalar, list
            The average quality for the image
        map : array, list of arrays, optional
            the local quality rating across the image
        scale : scalar, list
            the size scale at which the quality was calculated
        '''
        if type(quality) is list:
            self.qualities += quality
            self.scales += scale
            if maps is None:
                maps = [None]*len(quality)
            self.maps += maps
        else:
            self.qualities.append(quality)
            self.scales.append(scale)
            self.maps.append(maps)

    def sort(self):
        """Sorts the qualities by scale. #STUB"""

def compute_quality(reference,reconstructions,method="SSIM"):
    """
    Computes image quality metrics for each of the reconstructions.

    Parameters
    ---------
    reference : array
        the discrete reference image. In a future release, we will
        determine the best way to compare a continuous domain to a discrete
        reconstruction.
    reconstructions : list of arrays
        A list of discrete reconstructions
    method : string, enum?, optional
        The quality metric desired for this comparison.
        Options include: SSIM, MSSSIM

    Returns
    ---------
    metrics : list of ImageQuality
    """
    if not (type(reconstructions) is list):
        reconstructions = [reconstructions]

    dictionary = {"SSIM": _compute_ssim, "MSSSIM": _compute_msssim,
                "FSIM": _calculate_FSIM}
    method = dictionary[method]

    metrics = []
    for image in reconstructions:
        IQ = ImageQuality(reference, image)
        IQ = method(IQ)
        metrics.append(IQ)

    return metrics

def background_mask(phantom, shape):
    """Returns the background mask.

    Parameters
    ----------
    phantom : Phantom
    shape : ndarray

    Returns
    -------
    ndarray, bool
        True if pixel belongs to (an assumed) background.
    """
    dx, dy = shape
    _x = np.arange(0, 1, 1 / dx)
    _y = np.arange(0, 1, 1 / dy)
    px, py = np.meshgrid(_x, _y)

    mask = np.zeros(shape, dtype=np.bool)
    mask += (px - 0.5)**2 + (py - 0.5)**2 < 0.5**2
    for m in range(phantom.population):
        x = phantom.feature[m].center.x
        y = phantom.feature[m].center.y
        rad = phantom.feature[m].radius
        mask -= (px - x)**2 + (py - y)**2 < rad**2
    return mask

from phasepack import phasecongmono as _phasecongmono
import matplotlib.pyplot as plt
def _calculate_FSIM(imQual):
    """
    FSIM Index with automatic downsampling, Version 1.0
    Copyright(c) 2010 Lin ZHANG, Lei Zhang, Xuanqin Mou and David Zhang
    All Rights Reserved.
    ----------------------------------------------------------------------
    Permission to use, copy, or modify this software and its documentation
    for educational and research purposes only and without fee is here
    granted, provided that this copyright notice and the original authors'
    names appear on all copies and supporting documentation. This program
    shall not be used, rewritten, or adapted as the basis of a commercial
    software or hardware product without first obtaining permission of the
    authors. The authors make no representations about the suitability of
    this software for any purpose. It is provided "as is" without express
    or implied warranty.
    ----------------------------------------------------------------------
    Lin Zhang, Lei Zhang, Xuanqin Mou, and David Zhang,"FSIM: a feature
    similarity index for image qualtiy assessment", IEEE Transactions on Image
    Processing, vol. 20, no. 8, pp. 2378-2386, 2011.

    ----------------------------------------------------------------------
    An implementation of the algorithm for calculating the Feature SIMilarity
    (FSIM) index was ported to Python.

    Parameters
    --------------------------
    imQual : ImageQuality
    imageRef : numpy.ndarray
        the first image being compared
    imageDis : numpy.ndarray
        the second image being compared. Given 2 test images img1 and img2.
        For gray-scale images, their dynamic range should be 0-255. For
        colorful images, the dynamic range of each color channel should be
        0-255.

    Returns
    ------------------
    FSIM : scalar
        the similarty score calculated using FSIM algorithm. FSIM only
        considers the luminance component of images. For colorful images,
        convert to grayscale first.
    FSIMmap : numpy.ndarray
        local similarity score
    """

    Y1 = imQual.orig
    Y2 = imQual.recon
    [rows, cols] = Y1.shape

    # Downsample the image
    minDimension = min(rows,cols)
    F = max(1,round(minDimension / 256))

    aveY1 = scipy.ndimage.filters.uniform_filter(Y1,size=F)
    aveY2 = scipy.ndimage.filters.uniform_filter(Y2,size=F)
    Y1 = aveY1[::F,::F]
    Y2 = aveY2[::F,::F]

    # Calculate the phase congruency maps
    [PC1,Orient1,ft1,T1] = _phasecongmono(Y1)
    [PC2,Orient2,ft2,T2] = _phasecongmono(Y2)
    #plt.imshow(PC1,cmap=plt.cm.gray)
    #plt.show(block=True)
    #print(np.min(PC1))

    # Calculate the gradient magnitude map using Scharr filters
    dx = np.array([[3.  ,0.  ,-3. ],
                   [10. ,0.  ,-10.],
                   [3.  ,0.  ,-3. ]])/16
    dy = np.array([[3.  ,10. ,3.  ],
                   [0.  ,0.  ,0.  ],
                   [-3. ,-10.,-3. ]])/16

    IxY1 = scipy.ndimage.filters.convolve(Y1, dx)
    IyY1 = scipy.ndimage.filters.convolve(Y1, dy)
    gradientMap1 = np.sqrt(IxY1**2 + IyY1**2)

    IxY2 = scipy.ndimage.filters.convolve(Y2, dx)
    IyY2 = scipy.ndimage.filters.convolve(Y2, dy)
    gradientMap2 = np.sqrt(IxY2**2 + IyY2**2)

    # Calculate the FSIM
    T1 = 0.85   # fixed and depends on dynamic range
    T2 = 160    # fixed and depends on dynamic range
    PCSimMatrix = (2 * PC1 * PC2 + T1) / (PC1**2 + PC2**2 + T1) # results range (0,1]
    gradientSimMatrix = (2*gradientMap1*gradientMap2 + T2) / (gradientMap1**2 + gradientMap2**2 + T2)
    PCm = np.maximum(PC1, PC2)
    FSIMmap = gradientSimMatrix * PCSimMatrix
    FSIM = np.sum(FSIMmap * PCm) / np.sum(PCm)

    imQual.add_quality(FSIM, 0, maps=FSIMmap)
    return imQual


def _compute_msssim(imQual, nlevels=5, filtersize=(11,11), sigma=1.2, L=255, K=(0.01,0.03)):
    '''
    An implementation of the Multi-Scale Structural SIMilarity index (MS-SSIM).

    References
    -------------
    Multi-scale Structural Similarity Index (MS-SSIM)
    Z. Wang, E. P. Simoncelli and A. C. Bovik, "Multi-scale structural similarity
    for image quality assessment," Invited Paper, IEEE Asilomar Conference on
    Signals, Systems and Computers, Nov. 2003

    Parameters
    -------------
    img1 : ndarray
    img2 : ndarray
        img1 and img2 are refrence and distorted images. The order doesn't
        matter because the SSIM index is symmetric.
    nlevels : int
        The max number of levels to analyze
    filtersize : 2-tuple
        Sets the smallest scale at which local quality is calculated. Subsquent
        filters are larger.
    sigma : float
        Sets the standard deviation of the gaussian filter. Set this value to
        None if you want to use a box filter.
    L : int
        The color depth of the images. L = 2^bidepth - 1
    K : 2-tuple
        A list of two constants which help prevent division by zero.

    Returns
    --------------
    imQual : ImageQuality
        A struct used to organize image quality information.
    '''
    img1 = imQual.orig
    img2 = imQual.recon

    # CHECK INPUTS FOR VALIDITY
    # assert that the image is larger than 11x11
    (M,N) = img1.shape
    assert(M >= 11 and N >= 11)
    # assert that the window is smaller than the image and larger than 2x2
    (H,W) = filtersize
    assert((H*W) > 4 and H<=M and W<=N)
    # assert that there is at least one level requested
    assert(nlevels > 0)
    # assert that the image never becomes smaller than the filter
    min_img_width = min(M,N)/(2^(nlevels-1))
    max_win_width = max(H,W)
    assert(min_img_width >= max_win_width)

    # The relative imporance of each level as determined by human experimentation
    weight = [0.0448, 0.2856, 0.3001, 0.2363, 0.1333]

    lowpass_filter = np.ones((2,2))/4
    img1 = img1.astype(np.float)
    img2 = img2.astype(np.float)

    for l in range(0,nlevels):
        #print(img1.shape)
        imQual += _compute_ssim(ImageQuality(img1,img2), filtersize=filtersize, sigma=sigma, L=L, K=K, scale=l)
        if l == nlevels-1: break

        # Apply lowpass filter retain size, reflect at edges
        filtered_im1 = scipy.ndimage.filters.convolve(img1, lowpass_filter)
        filtered_im2 = scipy.ndimage.filters.convolve(img2, lowpass_filter) # mode='same'
        # Downsample by factor of two using numpy slicing
        img1 = filtered_im1[::2,::2]
        img2 = filtered_im2[::2,::2]

    return imQual

def _compute_ssim(imQual, filtersize=(11,11), sigma=1.2, L=255, K=(0.01,0.03), scale=0):
    """
    A modified version of the Structural SIMilarity index (SSIM) based on an
    implementation by Helder C. R. de Oliveira, based on the implementation by
    Antoine Vacavant, ISIT lab, antoine.vacavant@iut.u-clermont1.fr
    http://isit.u-clermont1.fr/~anvacava

    References
    -------------
    Z. Wang, A. C. Bovik, H. R. Sheikh and E. P. Simoncelli. Image quality
    assessment: From error visibility to structural similarity. IEEE
    Transactions on Image Processing, 13(4):600--612, 2004.

    Z. Wang and A. C. Bovik. Mean squared error: Love it or leave it? - A new
    look at signal fidelity measures. IEEE Signal Processing Magazine,
    26(1):98--117, 2009.

    Attributes
    ----------
    imQual : ImageQuality
    L : scalar, default = 255
        The dynamic range of the images. i.e 2^bitdepth-1
    filtersize : list, optional
        The dimensions of the filter to use.
    sigma : list, optional
        The standard deviation of the gaussian filter. If not specified,
        means are calculated using uniform square filters.

    Returns
    ----------
    imQual : ImageQuality
        A struct used to organize image quality information.
    """

    c_1 = (K[0]*L)**2
    c_2 = (K[1]*L)**2

    window = np.ones(filtersize)
    if sigma is not None:
        window = _gauss_2d(filtersize, sigma)
    # Normalization
    window /= np.sum(window)

    img1 = imQual.orig
    img2 = imQual.recon

    # TODO: Replace convolve with uniform and gaussian filtering methods because they can probably be optimized to be faster.
    # Means obtained by Gaussian filtering of inputs
    mu_1 = scipy.ndimage.filters.convolve(img1, window)
    mu_2 = scipy.ndimage.filters.convolve(img2, window)

    # Squares of means
    mu_1_sq = mu_1**2
    mu_2_sq = mu_2**2
    mu_1_mu_2 = mu_1 * mu_2

    # Squares of input matrices
    im1_sq = img1**2
    im2_sq = img2**2
    im12 = img1*img2

    # Variances obtained by Gaussian filtering of inputs' squares
    sigma_1_sq = scipy.ndimage.filters.convolve(im1_sq, window)
    sigma_2_sq = scipy.ndimage.filters.convolve(im2_sq, window)

    # Covariance
    sigma_12 = scipy.ndimage.filters.convolve(im12, window)

    # Centered squares of variances
    sigma_1_sq -= mu_1_sq
    sigma_2_sq -= mu_2_sq
    sigma_12 -= mu_1_mu_2

    if (c_1 > 0) & (c_2 > 0):
        ssim_map = ((2*mu_1_mu_2 + c_1) * (2*sigma_12 + c_2)) / ((mu_1_sq + mu_2_sq + c_1) * (sigma_1_sq + sigma_2_sq + c_2))
    else:
        numerator1 = 2 * mu_1_mu_2 + c_1
        numerator2 = 2 * sigma_12 + c_2

        denominator1 = mu_1_sq + mu_2_sq + c_1
        denominator2 = sigma_1_sq + sigma_2_sq + c_2

        ssim_map = np.ones(mu_1.size)

        index = (denominator1 * denominator2 > 0)

        ssim_map[index] = (numerator1[index] * numerator2[index]) / (denominator1[index] * denominator2[index])
        index = (denominator1 != 0) & (denominator2 == 0)
        ssim_map[index] = numerator1[index] / denominator1[index]

    # return SSIM
    index = np.mean(ssim_map)
    imQual.add_quality(index, scale, maps=ssim_map)
    return imQual

def _gauss_2d(shape=(11,11), sigma=1.5):
    """
    Code from Stack Overflow's thread
    2D gaussian mask - should give the same result as MATLAB's
    fspecial('gaussian',[shape],[sigma])
    """
    m, n = [(ss-1.)/2. for ss in shape]
    y, x = np.ogrid[-m:m+1, -n:n+1]
    h = np.exp(-(x*x + y*y) / (2.*sigma*sigma))
    h[h < np.finfo(h.dtype).eps*h.max()] = 0
    sumh = h.sum()
    if sumh != 0:
        h /= sumh
    return h
