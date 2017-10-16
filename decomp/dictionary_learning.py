import numpy as np
from .utils.cp_compat import get_array_module
from .utils.dtype import float_type
from .utils.data import minibatch_index
from .utils import assertion
from . import lasso


_JITTER = 1.0e-10


def solve(y, D, alpha, x=None, tol=1.0e-3,
          minibatch=1, maxiter=1000,
          lasso_method='ista', lasso_iter=10,
          mask=None,
          random_seed=None):
    """
    Learn Dictionary with lasso regularization.

    argmin_{x, D} {|y - xD|^2 - alpha |x|}
    s.t. |D_j|^2 <= 1

    with
    y: [..., n_channels]
    x: [..., n_features]
    D: [n_features, n_channels]

    Parameters
    ----------
    y: array-like.
        Shape: [..., ch]
    D: array-like.
        Initial dictionary, shape [ch, n_component]
    alpha: a positive float
        Regularization parameter
    x0: array-like
        An initial estimate of x

    tol: a float.
        Criterion

    mask: an array-like of Boolean (or integer, float)
        The missing point should be zero. One for otherwise.

    Notes
    -----
    This is essentially implements
    Mensch ARTHURMENSCH, A., Mairal JULIENMAIRAL, J., & Thirion BETRANDTHIRION,
    B. (n.d.).
    Dictionary Learning for Massive Matrix Factorization Gael Varoquaux.
    Retrieved from http://proceedings.mlr.press/v48/mensch16.pdf
    """
    # Check all the class are numpy or cupy
    xp = get_array_module(y, D, x)

    rng = np.random.RandomState(random_seed)
    if x is None:
        x = xp.zeros(y.shape[:-1] + (D.shape[0], ), dtype=y.dtype)

    assertion.assert_dtypes(y=y, D=D, x=x)
    assertion.assert_dtypes(mask=mask, dtypes='f')
    assertion.assert_shapes('x', x, 'D', D, axes=1)
    assertion.assert_shapes('y', y, 'D', D, axes=[-1])
    assertion.assert_shapes('y', y, 'mask', mask)

    A = xp.zeros((D.shape[0], D.shape[0]), dtype=y.dtype)
    B = xp.zeros((D.shape[0], D.shape[1]), dtype=y.dtype)
    if mask is not None:
        E = xp.zeros(D.shape[1], dtype=float_type(y.dtype))

    for it in range(1, maxiter):
        try:
            indexes = minibatch_index(y.shape, minibatch, rng)
            x_minibatch = x[indexes]
            y_minibatch = y[indexes]

            # lasso
            if mask is None:
                if lasso_method == 'ista':
                    it2, x_minibatch = lasso.solve_ista(
                        y_minibatch, D, alpha, x0=x_minibatch, tol=tol,
                        maxiter=lasso_iter, xp=xp)
                elif lasso_method == 'fista':
                    it2, x_minibatc = lasso.solve_fista(
                        y_minibatch, D, alpha, x0=x_minibatch, tol=tol,
                        maxiter=lasso_iter, xp=xp)
                else:
                    raise NotImplementedError

            else:
                mask_minibatch = mask[indexes]
                if lasso_method == 'ista':
                    it2, x_minibatch = lasso.solve_ista_mask(
                        y_minibatch, D, alpha, x0=x_minibatch, tol=tol,
                        maxiter=lasso_iter, mask=mask_minibatch, xp=xp)
                elif lasso_method == 'fista':
                    it2, x_minibatc = lasso.solve_fista(
                        y_minibatch, D, alpha, x0=x_minibatch, tol=tol,
                        maxiter=lasso_iter, mask=mask_minibatch, xp=xp)
                else:
                    raise NotImplementedError

            x[indexes] = x_minibatch

            # Dictionary update
            xT = x_minibatch.T
            if y.dtype.kind == 'c':
                xT = xp.conj(xT)

            it_inv = 1.0 / it
            A = (1.0 - it_inv) * A + it_inv * xp.dot(xT, x_minibatch)
            if mask is None:
                B = (1.0 - it_inv) * B + it_inv * xp.dot(xT, y_minibatch)
            else:
                mask_sum = xp.sum(mask_minibatch, axis=0)
                E = E + mask_sum
                B = B + 1.0 / E * (xp.dot(xT, y_minibatch * mask_minibatch)
                                   - mask_sum * B)

            Adiag = xp.expand_dims(xp.diagonal(A), -1)
            U = (B - xp.dot(A, D)) / (Adiag + _JITTER) + D
            if y.dtype.kind == 'c':
                Unorm = xp.sum(xp.real(xp.conj(U) * U), axis=-1, keepdims=True)
            else:
                Unorm = xp.sum(U * U, axis=-1, keepdims=True)

            D_new = U / xp.maximum(Unorm, 1.0)
            if xp.max(xp.abs(D - D_new)) < tol:
                return it, D, x
            D = D_new

        except KeyboardInterrupt:
            return it, D, x
    return maxiter, D, x