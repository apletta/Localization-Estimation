# Tutorial from https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python/blob/master/10-Unscented-Kalman-Filter.

from __future__ import (absolute_import, division)

import math
import random
from math import tan, sin, cos, atan2
import numpy as np
from scipy.linalg import cholesky
import matplotlib.pyplot as plt

# UKF book implementation
from copy import deepcopy
from math import log, exp, sqrt
import sys
import numpy as np
from numpy import eye, zeros, dot, isscalar, outer
from scipy.linalg import cholesky
import scipy.linalg as linalg
#from filterpy.kalman import unscented_transform
#from filterpy.stats import logpdf
#from filterpy.common import pretty_str


################################ Imported functions for UKF from book

# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-arguments

"""Copyright 2015 Roger R Labbe Jr.

FilterPy library.
http://github.com/rlabbe/filterpy

Documentation at:
https://filterpy.readthedocs.org

Supporting book at:
https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

This is licensed under an MIT license. See the readme.MD file
for more information.
"""

def unscented_transform(sigmas, Wm, Wc, noise_cov=None,
                        mean_fn=None, residual_fn=None):
    r"""
    Computes unscented transform of a set of sigma points and weights.
    returns the mean and covariance in a tuple.

    This works in conjunction with the UnscentedKalmanFilter class.


    Parameters
    ----------

    sigmas: ndarray, of size (n, 2n+1)
        2D array of sigma points.

    Wm : ndarray [# sigmas per dimension]
        Weights for the mean.


    Wc : ndarray [# sigmas per dimension]
        Weights for the covariance.

    noise_cov : ndarray, optional
        noise matrix added to the final computed covariance matrix.

    mean_fn : callable (sigma_points, weights), optional
        Function that computes the mean of the provided sigma points
        and weights. Use this if your state variable contains nonlinear
        values such as angles which cannot be summed.

        .. code-block:: Python

            def state_mean(sigmas, Wm):
                x = np.zeros(3)
                sum_sin, sum_cos = 0., 0.

                for i in range(len(sigmas)):
                    s = sigmas[i]
                    x[0] += s[0] * Wm[i]
                    x[1] += s[1] * Wm[i]
                    sum_sin += sin(s[2])*Wm[i]
                    sum_cos += cos(s[2])*Wm[i]
                x[2] = atan2(sum_sin, sum_cos)
                return x

    residual_fn : callable (x, y), optional

        Function that computes the residual (difference) between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y
        are state vectors, not scalars.

        .. code-block:: Python

            def residual(a, b):
                y = a[0] - b[0]
                y = y % (2 * np.pi)
                if y > np.pi:
                    y -= 2*np.pi
                return y

    Returns
    -------

    x : ndarray [dimension]
        Mean of the sigma points after passing through the transform.

    P : ndarray
        covariance of the sigma points after passing throgh the transform.

    Examples
    --------

    See my book Kalman and Bayesian Filters in Python
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python
    """

    kmax, n = sigmas.shape

    try:
        if mean_fn is None:
            # new mean is just the sum of the sigmas * weight
            x = np.dot(Wm, sigmas)    # dot = \Sigma^n_1 (W[k]*Xi[k])
        else:
            x = mean_fn(sigmas, Wm)
    except:
        print(sigmas)
        raise


    # new covariance is the sum of the outer product of the residuals
    # times the weights

    # this is the fast way to do this - see 'else' for the slow way
    if residual_fn is np.subtract or residual_fn is None:
        y = sigmas - x[np.newaxis, :]
        P = np.dot(y.T, np.dot(np.diag(Wc), y))
    else:
        P = np.zeros((n, n))
        for k in range(kmax):
            y = residual_fn(sigmas[k], x)
            P += Wc[k] * np.outer(y, y)

    if noise_cov is not None:
        P += noise_cov

    return (x, P)


def logpdf(x, mean=None, cov=1, allow_singular=True):
    """
    Computes the log of the probability density function of the normal
    N(mean, cov) for the data x. The normal may be univariate or multivariate.

    Wrapper for older versions of scipy.multivariate_normal.logpdf which
    don't support support the allow_singular keyword prior to verion 0.15.0.

    If it is not supported, and cov is singular or not PSD you may get
    an exception.

    `x` and `mean` may be column vectors, row vectors, or lists.
    """

    if mean is not None:
        flat_mean = np.asarray(mean).flatten()
    else:
        flat_mean = None

    flat_x = np.asarray(x).flatten()

    if _support_singular:
        return multivariate_normal.logpdf(flat_x, flat_mean, cov, allow_singular)
    return multivariate_normal.logpdf(flat_x, flat_mean, cov)

def pretty_str(label, arr):
    """
    Generates a pretty printed NumPy array with an assignment. Optionally
    transposes column vectors so they are drawn on one line. Strictly speaking
    arr can be any time convertible by `str(arr)`, but the output may not
    be what you want if the type of the variable is not a scalar or an
    ndarray.

    Examples
    --------
    >>> pprint('cov', np.array([[4., .1], [.1, 5]]))
    cov = [[4.  0.1]
           [0.1 5. ]]

    >>> print(pretty_str('x', np.array([[1], [2], [3]])))
    x = [[1 2 3]].T
    """

    def is_col(a):
        """ return true if a is a column vector"""
        try:
            return a.shape[0] > 1 and a.shape[1] == 1
        except (AttributeError, IndexError):
            return False

    if label is None:
        label = ''

    if label:
        label += ' = '

    if is_col(arr):
        return label + str(arr.T).replace('\n', '') + '.T'

    rows = str(arr).split('\n')
    if not rows:
        return ''

    s = label + rows[0]
    pad = ' ' * len(label)
    for line in rows[1:]:
        s = s + '\n' + pad + line

    return s



################################ Sigma points

## --> Functions for finding sigma points, taken from book's github (see link at top of document)
def print_sigmas(n=1, mean=5, cov=3, alpha=.1, beta=2., kappa=2):
    points = MerweScaledSigmaPoints(n, alpha, beta, kappa)
    print('sigmas: ', points.sigma_points(mean,  cov).T[0])
    Wm, Wc = points.Wm, points.Wc
    print('mean weights:', Wm)
    print('cov weights:', Wc)
    print('lambda:', alpha**2 *(n+kappa) - n)
    print('sum cov', sum(Wc))

class MerweScaledSigmaPoints(object):

    """
    Generates sigma points and weights according to Van der Merwe's
    2004 dissertation[1] for the UnscentedKalmanFilter class.. It
    parametizes the sigma points using alpha, beta, kappa terms, and
    is the version seen in most publications.

    Unless you know better, this should be your default choice.

    Parameters
    ----------

    n : int
        Dimensionality of the state. 2n+1 weights will be generated.

    alpha : float
        Determines the spread of the sigma points around the mean.
        Usually a small positive value (1e-3) according to [3].
        Larger alpha means sigma points are more spread out,
        ex. make alpha large for fat tails, small for typical gaussian.
        When sigma points are more spread out, more weight is given to 
        points closer to the mean (so less to furthe away points).

    beta : float
        Incorporates prior knowledge of the distribution of the mean. For
        Gaussian x beta=2 is optimal, according to [3].

    kappa : float, default=0.0
        Secondary scaling parameter usually set to 0 according to [4],
        or to 3-n according to [5].

    sqrt_method : function(ndarray), default=scipy.linalg.cholesky
        Defines how we compute the square root of a matrix, which has
        no unique answer. Cholesky is the default choice due to its
        speed. Typically your alternative choice will be
        scipy.linalg.sqrtm. Different choices affect how the sigma points
        are arranged relative to the eigenvectors of the covariance matrix.
        Usually this will not matter to you; if so the default cholesky()
        yields maximal performance. As of van der Merwe's dissertation of
        2004 [6] this was not a well reseached area so I have no advice
        to give you.

        If your method returns a triangular matrix it must be upper
        triangular. Do not use numpy.linalg.cholesky - for historical
        reasons it returns a lower triangular matrix. The SciPy version
        does the right thing.

    subtract : callable (x, y), optional
        Function that computes the difference between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y
        are state vectors, not scalars.

    Attributes
    ----------

    Wm : np.array
        weight for each sigma point for the mean

    Wc : np.array
        weight for each sigma point for the covariance

    Examples
    --------

    See my book Kalman and Bayesian Filters in Python
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python


    References
    ----------

    .. [1] R. Van der Merwe "Sigma-Point Kalman Filters for Probabilitic
           Inference in Dynamic State-Space Models" (Doctoral dissertation)

    """


    def __init__(self, n, alpha, beta, kappa, sqrt_method=None, subtract=None):
        #pylint: disable=too-many-arguments

        self.n = n
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        if sqrt_method is None:
            self.sqrt = cholesky
        else:
            self.sqrt = sqrt_method

        if subtract is None:
            self.subtract = np.subtract
        else:
            self.subtract = subtract

        self._compute_weights()


    def num_sigmas(self):
        """ Number of sigma points for each variable in the state x"""
        return 2*self.n + 1


    def sigma_points(self, x, P):
        """ Computes the sigma points for an unscented Kalman filter
        given the mean (x) and covariance(P) of the filter.
        Returns tuple of the sigma points and weights.

        Works with both scalar and array inputs:
        sigma_points (5, 9, 2) # mean 5, covariance 9
        sigma_points ([5, 2], 9*eye(2), 2) # means 5 and 2, covariance 9I

        Parameters
        ----------

        x : An array-like object of the means of length n
            Can be a scalar if 1D.
            examples: 1, [1,2], np.array([1,2])

        P : scalar, or np.array
           Covariance of the filter. If scalar, is treated as eye(n)*P.

        Returns
        -------

        sigmas : np.array, of size (n, 2n+1)
            Two dimensional array of sigma points. Each column contains all of
            the sigmas for one dimension in the problem space.

            Ordered by Xi_0, Xi_{1..n}, Xi_{n+1..2n}
        """

        if self.n != np.size(x):
            raise ValueError("expected size(x) {}, but size is {}".format(
                self.n, np.size(x)))

        n = self.n

        if np.isscalar(x):
            x = np.asarray([x])

        if  np.isscalar(P):
            P = np.eye(n)*P
        else:
            P = np.atleast_2d(P)

        lambda_ = self.alpha**2 * (n + self.kappa) - n
        U = self.sqrt((lambda_ + n)*P)

        sigmas = np.zeros((2*n+1, n))
        sigmas[0] = x
        for k in range(n):
            # pylint: disable=bad-whitespace
            sigmas[k+1]   = self.subtract(x, -U[k])
            sigmas[n+k+1] = self.subtract(x, U[k])

        return sigmas


    def _compute_weights(self):
        """ Computes the weights for the scaled unscented Kalman filter.

        """

        n = self.n
        lambda_ = self.alpha**2 * (n +self.kappa) - n

        c = .5 / (n + lambda_)
        self.Wc = np.full(2*n + 1, c)
        self.Wm = np.full(2*n + 1, c)
        self.Wc[0] = lambda_ / (n + lambda_) + (1 - self.alpha**2 + self.beta)
        self.Wm[0] = lambda_ / (n + lambda_)



    def __repr__(self):

        return '\n'.join([
            'MerweScaledSigmaPoints object',
            pretty_str('n', self.n),
            pretty_str('alpha', self.alpha),
            pretty_str('beta', self.beta),
            pretty_str('kappa', self.kappa),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            pretty_str('subtract', self.subtract),
            pretty_str('sqrt', self.sqrt)
            ])

################################ Plotting functions

def plot_covariance(
        mean, cov=None, variance=1.0, std=None, interval=None,
        ellipse=None, title=None, axis_equal=True,
        show_semiaxis=False, show_center=True,
        facecolor=None, edgecolor=None,
        fc='none', ec='#004080',
        alpha=1.0, xlim=None, ylim=None,
        ls='solid'):
    """
    Plots the covariance ellipse for the 2D normal defined by (mean, cov)

    `variance` is the normal sigma^2 that we want to plot. If list-like,
    ellipses for all ellipses will be ploted. E.g. [1,2] will plot the
    sigma^2 = 1 and sigma^2 = 2 ellipses. Alternatively, use std for the
    standard deviation, in which case `variance` will be ignored.

    ellipse is a (angle,width,height) tuple containing the angle in radians,
    and width and height radii.

    You may provide either cov or ellipse, but not both.

    Parameters
    ----------

    mean : row vector like (2x1)
        The mean of the normal

    cov : ndarray-like
        2x2 covariance matrix

    variance : float, default 1, or iterable float, optional
        Variance of the plotted ellipse. May specify std or interval instead.
        If iterable, such as (1, 2**2, 3**2), then ellipses will be drawn
        for all in the list.


    std : float, or iterable float, optional
        Standard deviation of the plotted ellipse. If specified, variance
        is ignored, and interval must be `None`.

        If iterable, such as (1, 2, 3), then ellipses will be drawn
        for all in the list.

    interval : float range [0,1), or iterable float, optional
        Confidence interval for the plotted ellipse. For example, .68 (for
        68%) gives roughly 1 standand deviation. If specified, variance
        is ignored and `std` must be `None`

        If iterable, such as (.68, .95), then ellipses will be drawn
        for all in the list.


    ellipse: (float, float, float)
        Instead of a covariance, plots an ellipse described by (angle, width,
        height), where angle is in radians, and the width and height are the
        minor and major sub-axis radii. `cov` must be `None`.

    title: str, optional
        title for the plot

    axis_equal: bool, default=True
        Use the same scale for the x-axis and y-axis to ensure the aspect
        ratio is correct.

    show_semiaxis: bool, default=False
        Draw the semiaxis of the ellipse

    show_center: bool, default=True
        Mark the center of the ellipse with a cross

    facecolor, fc: color, default=None
        If specified, fills the ellipse with the specified color. `fc` is an
        allowed abbreviation

    edgecolor, ec: color, default=None
        If specified, overrides the default color sequence for the edge color
        of the ellipse. `ec` is an allowed abbreviation

    alpha: float range [0,1], default=1.
        alpha value for the ellipse

    xlim: float or (float,float), default=None
       specifies the limits for the x-axis

    ylim: float or (float,float), default=None
       specifies the limits for the y-axis

    ls: str, default='solid':
        line style for the edge of the ellipse
    """

    from matplotlib.patches import Ellipse
    import matplotlib.pyplot as plt

    if cov is not None and ellipse is not None:
        raise ValueError('You cannot specify both cov and ellipse')

    if cov is None and ellipse is None:
        raise ValueError('Specify one of cov or ellipse')

    if facecolor is None:
        facecolor = fc

    if edgecolor is None:
        edgecolor = ec

    if cov is not None:
        ellipse = covariance_ellipse(cov)

    if axis_equal:
        plt.axis('equal')

    if title is not None:
        plt.title(title)

    ax = plt.gca()

    angle = np.degrees(ellipse[0])
    width = ellipse[1] * 2.
    height = ellipse[2] * 2.

    std = _std_tuple_of(variance, std, interval)
    for sd in std:
        e = Ellipse(xy=mean, width=sd*width, height=sd*height, angle=angle,
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    alpha=alpha,
                    lw=2, ls=ls)
        ax.add_patch(e)
    x, y = mean
    if show_center:
        plt.scatter(x, y, marker='+', color=edgecolor)

    if xlim is not None:
        ax.set_xlim(xlim)

    if ylim is not None:
        ax.set_ylim(ylim)

    if show_semiaxis:
        a = ellipse[0]
        h, w = height/4, width/4
        plt.plot([x, x+ h*cos(a+np.pi/2)], [y, y + h*sin(a+np.pi/2)])
        plt.plot([x, x+ w*cos(a)], [y, y + w*sin(a)])

def covariance_ellipse(P, deviations=1):
    """
    Returns a tuple defining the ellipse representing the 2 dimensional
    covariance matrix P.

    Parameters
    ----------

    P : nd.array shape (2,2)
       covariance matrix

    deviations : int (optional, default = 1)
       # of standard deviations. Default is 1.

    Returns (angle_radians, width_radius, height_radius)
    """

    U, s, _ = linalg.svd(P)
    orientation = math.atan2(U[1, 0], U[0, 0])
    width = deviations * math.sqrt(s[0])
    height = deviations * math.sqrt(s[1])

    if height > width:
        raise ValueError('width must be greater than height')

    return (orientation, width, height)

def _std_tuple_of(var=None, std=None, interval=None):
    """
    Convienence function for plotting. Given one of var, standard
    deviation, or interval, return the std. Any of the three can be an
    iterable list.

    Examples
    --------
    >>>_std_tuple_of(var=[1, 3, 9])
    (1, 2, 3)

    """

    if std is not None:
        if np.isscalar(std):
            std = (std,)
        return std


    if interval is not None:
        if np.isscalar(interval):
            interval = (interval,)

        return norm.interval(interval)[1]

    if var is None:
        raise ValueError("no inputs were provided")

    if np.isscalar(var):
        var = (var,)
    return np.sqrt(var)

################################ Unscented Kalman Filter implementation from book

# -*- coding: utf-8 -*-
# pylint: disable=invalid-name

"""Copyright 2015 Roger R Labbe Jr.

FilterPy library.
http://github.com/rlabbe/filterpy

Documentation at:
https://filterpy.readthedocs.org

Supporting book at:
https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

This is licensed under an MIT license. See the readme.MD file
for more information.
"""

class UnscentedKalmanFilter(object):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=invalid-name
    r"""
    Implements the Scaled Unscented Kalman filter (UKF) as defined by
    Simon Julier in [1], using the formulation provided by Wan and Merle
    in [2]. This filter scales the sigma points to avoid strong nonlinearities.


    Parameters
    ----------

    dim_x : int
        Number of state variables for the filter. For example, if
        you are tracking the position and velocity of an object in two
        dimensions, dim_x would be 4.


    dim_z : int
        Number of of measurement inputs. For example, if the sensor
        provides you with position in (x,y), dim_z would be 2.

        This is for convience, so everything is sized correctly on
        creation. If you are using multiple sensors the size of `z` can
        change based on the sensor. Just provide the appropriate hx function


    dt : float
        Time between steps in seconds.



    hx : function(x)
        Measurement function. Converts state vector x into a measurement
        vector of shape (dim_z).

    fx : function(x,dt)
        function that returns the state x transformed by the
        state transistion function. dt is the time step in seconds.

    points : class
        Class which computes the sigma points and weights for a UKF
        algorithm. You can vary the UKF implementation by changing this
        class. For example, MerweScaledSigmaPoints implements the alpha,
        beta, kappa parameterization of Van der Merwe, and
        JulierSigmaPoints implements Julier's original kappa
        parameterization. See either of those for the required
        signature of this class if you want to implement your own.

    sqrt_fn : callable(ndarray), default=None (implies scipy.linalg.cholesky)
        Defines how we compute the square root of a matrix, which has
        no unique answer. Cholesky is the default choice due to its
        speed. Typically your alternative choice will be
        scipy.linalg.sqrtm. Different choices affect how the sigma points
        are arranged relative to the eigenvectors of the covariance matrix.
        Usually this will not matter to you; if so the default cholesky()
        yields maximal performance. As of van der Merwe's dissertation of
        2004 [6] this was not a well reseached area so I have no advice
        to give you.

        If your method returns a triangular matrix it must be upper
        triangular. Do not use numpy.linalg.cholesky - for historical
        reasons it returns a lower triangular matrix. The SciPy version
        does the right thing as far as this class is concerned.

    x_mean_fn : callable  (sigma_points, weights), optional
        Function that computes the mean of the provided sigma points
        and weights. Use this if your state variable contains nonlinear
        values such as angles which cannot be summed.

        .. code-block:: Python

            def state_mean(sigmas, Wm):
                x = np.zeros(3)
                sum_sin, sum_cos = 0., 0.

                for i in range(len(sigmas)):
                    s = sigmas[i]
                    x[0] += s[0] * Wm[i]
                    x[1] += s[1] * Wm[i]
                    sum_sin += sin(s[2])*Wm[i]
                    sum_cos += cos(s[2])*Wm[i]
                x[2] = atan2(sum_sin, sum_cos)
                return x

    z_mean_fn : callable  (sigma_points, weights), optional
        Same as x_mean_fn, except it is called for sigma points which
        form the measurements after being passed through hx().

    residual_x : callable (x, y), optional
    residual_z : callable (x, y), optional
        Function that computes the residual (difference) between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y
        are state vectors, not scalars. One is for the state variable,
        the other is for the measurement state.

        .. code-block:: Python

            def residual(a, b):
                y = a[0] - b[0]
                if y > np.pi:
                    y -= 2*np.pi
                if y < -np.pi:
                    y = 2*np.pi
                return y

    Attributes
    ----------

    x : numpy.array(dim_x)
        state estimate vector

    P : numpy.array(dim_x, dim_x)
        covariance estimate matrix

    x_prior : numpy.array(dim_x)
        Prior (predicted) state estimate. The *_prior and *_post attributes
        are for convienence; they store the  prior and posterior of the
        current epoch. Read Only.

    P_prior : numpy.array(dim_x, dim_x)
        Prior (predicted) state covariance matrix. Read Only.

    x_post : numpy.array(dim_x)
        Posterior (updated) state estimate. Read Only.

    P_post : numpy.array(dim_x, dim_x)
        Posterior (updated) state covariance matrix. Read Only.

    z : ndarray
        Last measurement used in update(). Read only.

    R : numpy.array(dim_z, dim_z)
        measurement noise matrix

    Q : numpy.array(dim_x, dim_x)
        process noise matrix

    K : numpy.array
        Kalman gain

    y : numpy.array
        innovation residual

    log_likelihood : scalar
        Log likelihood of last measurement update.

    likelihood : float
        likelihood of last measurment. Read only.

        Computed from the log-likelihood. The log-likelihood can be very
        small,  meaning a large negative value such as -28000. Taking the
        exp() of that results in 0.0, which can break typical algorithms
        which multiply by this value, so by default we always return a
        number >= sys.float_info.min.

    mahalanobis : float
        mahalanobis distance of the measurement. Read only.

    inv : function, default numpy.linalg.inv
        If you prefer another inverse function, such as the Moore-Penrose
        pseudo inverse, set it to that instead:

        .. code-block:: Python

            kf.inv = np.linalg.pinv


    Examples
    --------

    Simple example of a linear order 1 kinematic filter in 2D. There is no
    need to use a UKF for this example, but it is easy to read.

    >>> def fx(x, dt):
    >>>     # state transition function - predict next state based
    >>>     # on constant velocity model x = vt + x_0
    >>>     F = np.array([[1, dt, 0, 0],
    >>>                   [0, 1, 0, 0],
    >>>                   [0, 0, 1, dt],
    >>>                   [0, 0, 0, 1]], dtype=float)
    >>>     return np.dot(F, x)
    >>>
    >>> def hx(x):
    >>>    # measurement function - convert state into a measurement
    >>>    # where measurements are [x_pos, y_pos]
    >>>    return np.array([x[0], x[2]])
    >>>
    >>> dt = 0.1
    >>> # create sigma points to use in the filter. This is standard for Gaussian processes
    >>> points = MerweScaledSigmaPoints(4, alpha=.1, beta=2., kappa=-1)
    >>>
    >>> kf = UnscentedKalmanFilter(dim_x=4, dim_z=2, dt=dt, fx=fx, hx=hx, points=points)
    >>> kf.x = np.array([-1., 1., -1., 1]) # initial state
    >>> kf.P *= 0.2 # initial uncertainty
    >>> z_std = 0.1
    >>> kf.R = np.diag([z_std**2, z_std**2]) # 1 standard
    >>> kf.Q = Q_discrete_white_noise(dim=2, dt=dt, var=0.01**2, block_size=2)
    >>>
    >>> zs = [[i+randn()*z_std, i+randn()*z_std] for i in range(50)] # measurements
    >>> for z in zs:
    >>>     kf.predict()
    >>>     kf.update(z)
    >>>     print(kf.x, 'log-likelihood', kf.log_likelihood)

    For in depth explanations see my book Kalman and Bayesian Filters in Python
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

    Also see the filterpy/kalman/tests subdirectory for test code that
    may be illuminating.

    References
    ----------

    .. [1] Julier, Simon J. "The scaled unscented transformation,"
        American Control Converence, 2002, pp 4555-4559, vol 6.

        Online copy:
        https://www.cs.unc.edu/~welch/kalman/media/pdf/ACC02-IEEE1357.PDF

    .. [2] E. A. Wan and R. Van der Merwe, “The unscented Kalman filter for
        nonlinear estimation,” in Proc. Symp. Adaptive Syst. Signal
        Process., Commun. Contr., Lake Louise, AB, Canada, Oct. 2000.

        Online Copy:
        https://www.seas.harvard.edu/courses/cs281/papers/unscented.pdf

    .. [3] S. Julier, J. Uhlmann, and H. Durrant-Whyte. "A new method for
           the nonlinear transformation of means and covariances in filters
           and estimators," IEEE Transactions on Automatic Control, 45(3),
           pp. 477-482 (March 2000).

    .. [4] E. A. Wan and R. Van der Merwe, “The Unscented Kalman filter for
           Nonlinear Estimation,” in Proc. Symp. Adaptive Syst. Signal
           Process., Commun. Contr., Lake Louise, AB, Canada, Oct. 2000.

           https://www.seas.harvard.edu/courses/cs281/papers/unscented.pdf

    .. [5] Wan, Merle "The Unscented Kalman Filter," chapter in *Kalman
           Filtering and Neural Networks*, John Wiley & Sons, Inc., 2001.

    .. [6] R. Van der Merwe "Sigma-Point Kalman Filters for Probabilitic
           Inference in Dynamic State-Space Models" (Doctoral dissertation)
    """

    def __init__(self, dim_x, dim_z, dt, hx, fx, points,
                 sqrt_fn=None, x_mean_fn=None, z_mean_fn=None,
                 residual_x=None,
                 residual_z=None):
        """
        Create a Kalman filter. You are responsible for setting the
        various state variables to reasonable values; the defaults below will
        not give you a functional filter.

        """

        #pylint: disable=too-many-arguments

        self.x = zeros(dim_x)
        self.P = eye(dim_x)
        self.x_prior = np.copy(self.x)
        self.P_prior = np.copy(self.P)
        self.Q = eye(dim_x)
        self.R = eye(dim_z)
        self._dim_x = dim_x
        self._dim_z = dim_z
        self.points_fn = points
        self._dt = dt
        self._num_sigmas = points.num_sigmas()
        self.hx = hx
        self.fx = fx
        self.x_mean = x_mean_fn
        self.z_mean = z_mean_fn

        # Only computed only if requested via property
        self._log_likelihood = log(sys.float_info.min)
        self._likelihood = sys.float_info.min
        self._mahalanobis = None

        if sqrt_fn is None:
            self.msqrt = cholesky
        else:
            self.msqrt = sqrt_fn

        # weights for the means and covariances.
        self.Wm, self.Wc = points.Wm, points.Wc

        if residual_x is None:
            self.residual_x = np.subtract
        else:
            self.residual_x = residual_x

        if residual_z is None:
            self.residual_z = np.subtract
        else:
            self.residual_z = residual_z

        # sigma points transformed through f(x) and h(x)
        # variables for efficiency so we don't recreate every update

        self.sigmas_f = zeros((self._num_sigmas, self._dim_x))
        self.sigmas_h = zeros((self._num_sigmas, self._dim_z))

        self.K = np.zeros((dim_x, dim_z))    # Kalman gain
        self.y = np.zeros((dim_z))           # residual
        self.z = np.array([[None]*dim_z]).T  # measurement
        self.S = np.zeros((dim_z, dim_z))    # system uncertainty
        self.SI = np.zeros((dim_z, dim_z))   # inverse system uncertainty

        self.inv = np.linalg.inv

        # these will always be a copy of x,P after predict() is called
        self.x_prior = self.x.copy()
        self.P_prior = self.P.copy()

        # these will always be a copy of x,P after update() is called
        self.x_post = self.x.copy()
        self.P_post = self.P.copy()

    def predict(self, dt=None, UT=None, fx=None, **fx_args):
        r"""
        Performs the predict step of the UKF. On return, self.x and
        self.P contain the predicted state (x) and covariance (P). '

        Important: this MUST be called before update() is called for the first
        time.

        Parameters
        ----------

        dt : double, optional
            If specified, the time step to be used for this prediction.
            self._dt is used if this is not provided.

        fx : callable f(x, **fx_args), optional
            State transition function. If not provided, the default
            function passed in during construction will be used.

        UT : function(sigmas, Wm, Wc, noise_cov), optional
            Optional function to compute the unscented transform for the sigma
            points passed through hx. Typically the default function will
            work - you can use x_mean_fn and z_mean_fn to alter the behavior
            of the unscented transform.

        **fx_args : keyword arguments
            optional keyword arguments to be passed into f(x).
        """

        if dt is None:
            dt = self._dt

        if UT is None:
            UT = unscented_transform

        # calculate sigma points for given mean and covariance
        self.compute_process_sigmas(dt, fx, **fx_args)

        #and pass sigmas through the unscented transform to compute prior
        self.x, self.P = UT(self.sigmas_f, self.Wm, self.Wc, self.Q,
                            self.x_mean, self.residual_x)

        # save prior
        self.x_prior = np.copy(self.x)
        self.P_prior = np.copy(self.P)

    def update(self, z, R=None, UT=None, hx=None, **hx_args):
        """
        Update the UKF with the given measurements. On return,
        self.x and self.P contain the new mean and covariance of the filter.

        Parameters
        ----------

        z : numpy.array of shape (dim_z)
            measurement vector

        R : numpy.array((dim_z, dim_z)), optional
            Measurement noise. If provided, overrides self.R for
            this function call.

        UT : function(sigmas, Wm, Wc, noise_cov), optional
            Optional function to compute the unscented transform for the sigma
            points passed through hx. Typically the default function will
            work - you can use x_mean_fn and z_mean_fn to alter the behavior
            of the unscented transform.

        **hx_args : keyword argument
            arguments to be passed into h(x) after x -> h(x, **hx_args)
        """

        if z is None:
            self.z = np.array([[None]*self._dim_z]).T
            self.x_post = self.x.copy()
            self.P_post = self.P.copy()
            return

        if hx is None:
            hx = self.hx

        if UT is None:
            UT = unscented_transform

        if R is None:
            R = self.R
        elif isscalar(R):
            R = eye(self._dim_z) * R

        # pass prior sigmas through h(x) to get measurement sigmas
        # the shape of sigmas_h will vary if the shape of z varies, so
        # recreate each time
        sigmas_h = []
        for s in self.sigmas_f:
            sigmas_h.append(hx(s, **hx_args))

        self.sigmas_h = np.atleast_2d(sigmas_h)

        # mean and covariance of prediction passed through unscented transform
        zp, self.S = UT(self.sigmas_h, self.Wm, self.Wc, R, self.z_mean, self.residual_z)
        self.SI = self.inv(self.S)

        # compute cross variance of the state and the measurements
        Pxz = self.cross_variance(self.x, zp, self.sigmas_f, self.sigmas_h)


        self.K = dot(Pxz, self.SI)        # Kalman gain
        self.y = self.residual_z(z, zp)   # residual

        # update Gaussian state estimate (x, P)
        self.x = self.x + dot(self.K, self.y)
        self.P = self.P - dot(self.K, dot(self.S, self.K.T))

        # save measurement and posterior state
        self.z = deepcopy(z)
        self.x_post = self.x.copy()
        self.P_post = self.P.copy()

        # set to None to force recompute
        self._log_likelihood = None
        self._likelihood = None
        self._mahalanobis = None

    def cross_variance(self, x, z, sigmas_f, sigmas_h):
        """
        Compute cross variance of the state `x` and measurement `z`.
        """

        Pxz = zeros((sigmas_f.shape[1], sigmas_h.shape[1]))
        N = sigmas_f.shape[0]
        for i in range(N):
            dx = self.residual_x(sigmas_f[i], x)
            dz = self.residual_z(sigmas_h[i], z)
            Pxz += self.Wc[i] * outer(dx, dz)
        return Pxz

    def compute_process_sigmas(self, dt, fx=None, **fx_args):
        """
        computes the values of sigmas_f. Normally a user would not call
        this, but it is useful if you need to call update more than once
        between calls to predict (to update for multiple simultaneous
        measurements), so the sigmas correctly reflect the updated state
        x, P.
        """

        if fx is None:
            fx = self.fx

        # calculate sigma points for given mean and covariance
        sigmas = self.points_fn.sigma_points(self.x, self.P)

        for i, s in enumerate(sigmas):
            self.sigmas_f[i] = fx(s, dt, **fx_args)

    def batch_filter(self, zs, Rs=None, dts=None, UT=None, saver=None):
        """
        Performs the UKF filter over the list of measurement in `zs`.

        Parameters
        ----------

        zs : list-like
            list of measurements at each time step `self._dt` Missing
            measurements must be represented by 'None'.

        Rs : None, np.array or list-like, default=None
            optional list of values to use for the measurement error
            covariance R.

            If Rs is None then self.R is used for all epochs.

            If it is a list of matrices or a 3D array where
            len(Rs) == len(zs), then it is treated as a list of R values, one
            per epoch. This allows you to have varying R per epoch.

        dts : None, scalar or list-like, default=None
            optional value or list of delta time to be passed into predict.

            If dtss is None then self.dt is used for all epochs.

            If it is a list where len(dts) == len(zs), then it is treated as a
            list of dt values, one per epoch. This allows you to have varying
            epoch durations.

        UT : function(sigmas, Wm, Wc, noise_cov), optional
            Optional function to compute the unscented transform for the sigma
            points passed through hx. Typically the default function will
            work - you can use x_mean_fn and z_mean_fn to alter the behavior
            of the unscented transform.

        saver : filterpy.common.Saver, optional
            filterpy.common.Saver object. If provided, saver.save() will be
            called after every epoch

        Returns
        -------

        means: ndarray((n,dim_x,1))
            array of the state for each time step after the update. Each entry
            is an np.array. In other words `means[k,:]` is the state at step
            `k`.

        covariance: ndarray((n,dim_x,dim_x))
            array of the covariances for each time step after the update.
            In other words `covariance[k,:,:]` is the covariance at step `k`.

        Examples
        --------

        .. code-block:: Python

            # this example demonstrates tracking a measurement where the time
            # between measurement varies, as stored in dts The output is then smoothed
            # with an RTS smoother.

            zs = [t + random.randn()*4 for t in range (40)]

            (mu, cov, _, _) = ukf.batch_filter(zs, dts=dts)
            (xs, Ps, Ks) = ukf.rts_smoother(mu, cov)

        """
        #pylint: disable=too-many-arguments

        try:
            z = zs[0]
        except TypeError:
            raise TypeError('zs must be list-like')

        if self._dim_z == 1:
            if not(isscalar(z) or (z.ndim == 1 and len(z) == 1)):
                raise TypeError('zs must be a list of scalars or 1D, 1 element arrays')
        else:
            if len(z) != self._dim_z:
                raise TypeError(
                    'each element in zs must be a 1D array of length {}'.format(self._dim_z))

        z_n = np.size(zs, 0)
        if Rs is None:
            Rs = [self.R] * z_n

        if dts is None:
            dts = [self._dt] * z_n

        # mean estimates from Kalman Filter
        if self.x.ndim == 1:
            means = zeros((z_n, self._dim_x))
        else:
            means = zeros((z_n, self._dim_x, 1))

        # state covariances from Kalman Filter
        covariances = zeros((z_n, self._dim_x, self._dim_x))

        for i, (z, r, dt) in enumerate(zip(zs, Rs, dts)):
            self.predict(dt=dt, UT=UT)
            self.update(z, r, UT=UT)
            means[i, :] = self.x
            covariances[i, :, :] = self.P

            if saver is not None:
                saver.save()

        return (means, covariances)

    def rts_smoother(self, Xs, Ps, Qs=None, dts=None, UT=None):
        """
        Runs the Rauch-Tung-Striebal Kalman smoother on a set of
        means and covariances computed by the UKF. The usual input
        would come from the output of `batch_filter()`.

        Parameters
        ----------

        Xs : numpy.array
           array of the means (state variable x) of the output of a Kalman
           filter.

        Ps : numpy.array
            array of the covariances of the output of a kalman filter.

        Qs: list-like collection of numpy.array, optional
            Process noise of the Kalman filter at each time step. Optional,
            if not provided the filter's self.Q will be used

        dt : optional, float or array-like of float
            If provided, specifies the time step of each step of the filter.
            If float, then the same time step is used for all steps. If
            an array, then each element k contains the time  at step k.
            Units are seconds.

        UT : function(sigmas, Wm, Wc, noise_cov), optional
            Optional function to compute the unscented transform for the sigma
            points passed through hx. Typically the default function will
            work - you can use x_mean_fn and z_mean_fn to alter the behavior
            of the unscented transform.

        Returns
        -------

        x : numpy.ndarray
           smoothed means

        P : numpy.ndarray
           smoothed state covariances

        K : numpy.ndarray
            smoother gain at each step

        Examples
        --------

        .. code-block:: Python

            zs = [t + random.randn()*4 for t in range (40)]

            (mu, cov, _, _) = kalman.batch_filter(zs)
            (x, P, K) = rts_smoother(mu, cov, fk.F, fk.Q)
        """
        #pylint: disable=too-many-locals, too-many-arguments

        if len(Xs) != len(Ps):
            raise ValueError('Xs and Ps must have the same length')

        n, dim_x = Xs.shape

        if dts is None:
            dts = [self._dt] * n
        elif isscalar(dts):
            dts = [dts] * n

        if Qs is None:
            Qs = [self.Q] * n

        if UT is None:
            UT = unscented_transform

        # smoother gain
        Ks = zeros((n, dim_x, dim_x))

        num_sigmas = self._num_sigmas

        xs, ps = Xs.copy(), Ps.copy()
        sigmas_f = zeros((num_sigmas, dim_x))

        for k in reversed(range(n-1)):
            # create sigma points from state estimate, pass through state func
            sigmas = self.points_fn.sigma_points(xs[k], ps[k])
            for i in range(num_sigmas):
                sigmas_f[i] = self.fx(sigmas[i], dts[k])

            xb, Pb = UT(
                sigmas_f, self.Wm, self.Wc, self.Q,
                self.x_mean, self.residual_x)

            # compute cross variance
            Pxb = 0
            for i in range(num_sigmas):
                y = self.residual_x(sigmas_f[i], xb)
                z = self.residual_x(sigmas[i], Xs[k])
                Pxb += self.Wc[i] * outer(z, y)

            # compute gain
            K = dot(Pxb, self.inv(Pb))

            # update the smoothed estimates
            xs[k] += dot(K, self.residual_x(xs[k+1], xb))
            ps[k] += dot(K, ps[k+1] - Pb).dot(K.T)
            Ks[k] = K

        return (xs, ps, Ks)

    @property
    def log_likelihood(self):
        """
        log-likelihood of the last measurement.
        """
        if self._log_likelihood is None:
            self._log_likelihood = logpdf(x=self.y, cov=self.S)
        return self._log_likelihood

    @property
    def likelihood(self):
        """
        Computed from the log-likelihood. The log-likelihood can be very
        small,  meaning a large negative value such as -28000. Taking the
        exp() of that results in 0.0, which can break typical algorithms
        which multiply by this value, so by default we always return a
        number >= sys.float_info.min.
        """
        if self._likelihood is None:
            self._likelihood = exp(self.log_likelihood)
            if self._likelihood == 0:
                self._likelihood = sys.float_info.min
        return self._likelihood

    @property
    def mahalanobis(self):
        """"
        Mahalanobis distance of measurement. E.g. 3 means measurement
        was 3 standard deviations away from the predicted value.

        Returns
        -------
        mahalanobis : float
        """
        if self._mahalanobis is None:
            self._mahalanobis = sqrt(float(dot(dot(self.y.T, self.SI), self.y)))
        return self._mahalanobis

    def __repr__(self):
        return '\n'.join([
            'UnscentedKalmanFilter object',
            pretty_str('x', self.x),
            pretty_str('P', self.P),
            pretty_str('x_prior', self.x_prior),
            pretty_str('P_prior', self.P_prior),
            pretty_str('Q', self.Q),
            pretty_str('R', self.R),
            pretty_str('S', self.S),
            pretty_str('K', self.K),
            pretty_str('y', self.y),
            pretty_str('log-likelihood', self.log_likelihood),
            pretty_str('likelihood', self.likelihood),
            pretty_str('mahalanobis', self.mahalanobis),
            pretty_str('sigmas_f', self.sigmas_f),
            pretty_str('h', self.sigmas_h),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            pretty_str('residual_x', self.residual_x),
            pretty_str('residual_z', self.residual_z),
            pretty_str('msqrt', self.msqrt),
            pretty_str('hx', self.hx),
            pretty_str('fx', self.fx),
            pretty_str('x_mean', self.x_mean),
            pretty_str('z_mean', self.z_mean)
            ])




################################ Following tutorial

## --> System motion model
# bicycle model for steering and movement, dt must be small with relatively slower speeds
def move(x, dt, u, wheelbase):
    hdg = x[2]
    vel = u[0]
    steering_angle = u[1]
    dist = vel * dt

    if abs(steering_angle) > 0.001: # is robot turning?
        beta = (dist / wheelbase) * tan(steering_angle)
        r = wheelbase / tan(steering_angle) # radius

        sinh, sinhb = sin(hdg), sin(hdg + beta)
        cosh, coshb = cos(hdg), cos(hdg + beta)
        return x + np.array([-r*sinh + r*sinhb, 
                              r*cosh - r*coshb, beta])
    else: # moving in straight line
        return x + np.array([dist*cos(hdg), dist*sin(hdg), 0])


## --> Measurement noise
# make bearing calculations within +0 to +360deg range
def normalize_angle(x):
    x = x % (2 * np.pi)    # force in range [0, 2 pi)
    if x > np.pi:          # move to [-pi, pi)
        x -= 2 * np.pi
    return x

# residual for measurement vector
def residual_h(a, b):
    y = a - b
    # data in format [dist_1, bearing_1, dist_2, bearing_2,...]
    for i in range(0, len(y), 2):
        y[i + 1] = normalize_angle(y[i + 1])
    return y

# residual for state vector
def residual_x(a, b):
    y = a - b
    y[2] = normalize_angle(y[2])
    return y

## --> Measurement model to get state position and heading for observed locations
# pass in landmarks formatted as [dist_1, bearing_1, dist_2, bearing_2,...]
def Hx(x, landmarks):
    """ takes a state variable and returns the measurement
    that would correspond to that state. """
    hx = []
    for lmark in landmarks:
        px, py = lmark
        dist = sqrt((px - x[0])**2 + (py - x[1])**2)
        angle = atan2(py - x[1], px - x[0])
        hx.extend([dist, normalize_angle(angle - x[2])])
    return np.array(hx)

## --> Compute mean of state 
def state_mean(sigmas, Wm):
    x = np.zeros(3)

    sum_sin = np.sum(np.dot(np.sin(sigmas[:, 2]), Wm))
    sum_cos = np.sum(np.dot(np.cos(sigmas[:, 2]), Wm))
    x[0] = np.sum(np.dot(sigmas[:, 0], Wm)) # x location
    x[1] = np.sum(np.dot(sigmas[:, 1], Wm)) # y location
    x[2] = atan2(sum_sin, sum_cos) # heading angle
    return x

## --> Compute mean of measurement
def z_mean(sigmas, Wm):
    z_count = sigmas.shape[1]
    x = np.zeros(z_count)

    for z in range(0, z_count, 2):
        sum_sin = np.sum(np.dot(np.sin(sigmas[:, z+1]), Wm))
        sum_cos = np.sum(np.dot(np.cos(sigmas[:, z+1]), Wm))

        x[z] = np.sum(np.dot(sigmas[:,z], Wm)) # distance to observed location
        x[z+1] = atan2(sum_sin, sum_cos) # angle to observated location
    return x


# TODO: what are ellipse_step and step?
def run_localization(cmds, landmarks, sigma_vel, sigma_steer, sigma_range, sigma_bearing, ellipse_step=20, step=10):

    plt.figure()

    # set up sigma points and ukf
    points = MerweScaledSigmaPoints(n=3, alpha=0.00001, beta=2, kappa=0, subtract=residual_x)
    ukf = UnscentedKalmanFilter(dim_x=3, dim_z=2*len(landmarks), fx=move, hx=Hx, dt=dt, points=points, x_mean_fn=state_mean, z_mean_fn=z_mean, residual_x=residual_x, residual_z=residual_h)

    # set up matrices 
    ukf.x = np.array([2, 6, 0.3]) # state estimate
    ukf.P = np.diag([.1, .1, .05]) # covariance estimate (uncertainty)
    ukf.R = np.diag([sigma_range**2, sigma_bearing**2]*len(landmarks)) # measurement noise
    ukf.Q = np.eye(3)*0.0001 # process noise

    sim_pos = ukf.x.copy() # copy of state

    # plot landmarks
    if len(landmarks) > 0:
        plt.scatter(landmarks[:, 0], landmarks[:, 1], marker='s', s=60)

    track = []
    for i, u in enumerate(cmds):
        sim_pos = move(sim_pos, dt/step, u, wheelbase)
        track.append(sim_pos)

        if i % step == 0:
            ukf.predict(u=u, wheelbase=wheelbase)

            if i % ellipse_step == 0:
                # plot covariance pre-update, semi-transparent
                plot_covariance( (ukf.x[0], ukf.x[1]), ukf.P[0:2, 0:2], std=6, facecolor='k', alpha=0.3)
                x, y = sim_pos[0], sim_pos[1]
                z = []

                for lmark in landmarks:
                    dx, dy = lmark[0] - x, lmark[1] - y
                    d = sqrt(dx**2 + dy**2) + np.random.randn()*sigma_range # euclidean distance from robot to landmark
                    bearing = atan2(lmark[1]-y, lmark[0]-x) # bearing to landmark
                    a = (normalize_angle(bearing-sim_pos[2] + np.random.randn()*sigma_bearing)) # normalized angle to landmark
                    z.extend([d, a]) # distance and normalized angle pair array for all landmarks
                ukf.update(z, landmarks=landmarks) # update mean and covariance of filter

                if i % ellipse_step == 0:
                    # plot covariance post-update, not as transparent
                    plot_covariance( (ukf.x[0], ukf.x[1]), ukf.P[0:2, 0:2], std=6, facecolor='g', alpha=0.8 )

    track = np.array(track)
    plt.plot(track[:, 0], track[:, 1], color='k', lw=2)
    plt.axis('equal')
    plt.title("UKF Robot Localization Tutorial")
    plt.show()
    return ukf


# system inputs
dt = 1.0
wheelbase = 0.5
sigma_vel = 0.1
sigma_steer = np.radians(1)
sigma_range = 0.3
sigma_bearing=0.1

##### Trial 1

# landmarks = np.array([ [5, 10], [10, 5], [15, 15] ])
# cmds = [np.array([1.1, 0.01])]*200

# ukf = run_localization(cmds, landmarks, sigma_vel=sigma_vel, sigma_steer=sigma_steer, sigma_range=sigma_range, sigma_bearing=sigma_bearing)
# print('Final P:', ukf.P.diagonal())

#####

##### Trial 2

landmarks = np.array([ [5, 10], [10, 5] , [15, 15], [20, 5], [0, 30], [50, 30], [40, 10] ])
def turn(v, t0, t1, steps):
    return [[v,a] for a in np.linspace(np.radians(t0), np.radians(t1), steps)]

# accelerate from stop
cmds = [[v, .0] for v in np.linspace(0.001, 1.1, 30)] # 30 velocity steps from 0.001 to 1.1
cmds.extend([cmds[-1]]*50) # maintain final acclerated velocity for 50 more steps

# turn left
v = cmds[-1][0]
cmds.extend(turn(v, 0, 2, 15))
cmds.extend([cmds[-1]]*100)

# turn right
cmds.extend(turn(v, 2, -2, 15))
cmds.extend([cmds[-1]]*200)

cmds.extend(turn(v, -2, 0, 15))
cmds.extend([cmds[-1]]*150)

cmds.extend(turn(v, 0, -1, 25))
cmds.extend([cmds[-1]]*100)

# turn left again
cmds.extend(turn(v, 0, 5, 15))
cmds.extend([cmds[-1]]*100)

ukf=run_localization(cmds, landmarks, sigma_vel=sigma_vel, sigma_steer=sigma_steer, sigma_range=sigma_range, sigma_bearing=sigma_bearing)
print("Final covariance", ukf.P.diagonal() )

#####



