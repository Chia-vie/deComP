import unittest
from decomp.utils.cp_compat import numpy_or_cupy as xp
import decomp.dictionary_learning as dic
from .testings import allclose


class TestFloat(unittest.TestCase):
    def randn(self, *shape):
        return self.rng.randn(*shape)

    def setUp(self):
        self.rng = xp.random.RandomState(0)
        self.Dtrue = self.randn(3, 5)
        xtrue = self.randn(101, 3)
        self.xtrue = xtrue * self.rng.uniform(size=303).reshape(101, 3)

        self.y = xp.dot(self.xtrue, self.Dtrue) + self.randn(101, 5) * 0.1
        self.D = self.Dtrue + self.randn(*self.Dtrue.shape) * 0.3
        self.mask = xp.rint(
                self.rng.uniform(0.3, 1, size=505)).reshape(101, 5)

    def test_run(self):
        D = self.D.copy()
        alpha = 2.0
        it, D, x = dic.solve(self.y, D, alpha, x=None, tol=1.0e-6,
                             minibatch=1, maxiter=1000,
                             lasso_method='ista', lasso_iter=10,
                             random_seed=0)
        self.assertTrue(it < 1000 - 1)
        self.assert_minimum(x, D, alpha, tol=1.0e-5, n=3)

    def test_run_minibatch(self):
        D = self.D.copy()
        alpha = 2.0
        it, D, x = dic.solve(self.y, D, alpha, x=None, tol=1.0e-6,
                             minibatch=10, maxiter=1000,
                             lasso_method='ista', lasso_iter=10,
                             random_seed=0)
        self.assertTrue(it < 1000 - 1)
        self.assert_minimum(x, D, alpha, tol=1.0e-5, n=3)

    def test_run_minibatch_mask(self):
        D = self.D.copy()
        alpha = 2.0
        y = self.mask * self.y
        it, D, x = dic.solve(y, D, alpha, x=None, tol=1.0e-5,
                             minibatch=10, maxiter=10000,
                             lasso_method='ista', lasso_iter=10,
                             random_seed=0, mask=self.mask)
        self.assertTrue(it < 10000 - 1)
        D = self.D.copy()
        self.assert_minimum(x, D, alpha, tol=1.0e-6, n=3, mask=self.mask)
        # make sure that the solution is different from
        it2, D2, x2 = dic.solve(self.y, D, alpha, x=None, tol=1.0e-5,
                                minibatch=10, maxiter=10000,
                                lasso_method='ista', lasso_iter=10,
                                random_seed=0)
        self.assertFalse(allclose(D, D2, atol=1.0e-4))

    def error(self, x, D, alpha, mask=None):
        mask = xp.ones(self.y.shape, dtype=float) if mask is None else mask
        D = D / xp.maximum(xp.sum(D * D, axis=0), 1.0)
        loss = xp.sum(xp.square(xp.abs(
            self.y - xp.tensordot(x, D, axes=1))))
        return 0.5 / alpha * loss + xp.sum(xp.abs(x))

    def assert_minimum(self, x, D, alpha, tol, n=3, mask=None):
        loss = self.error(x, D, alpha, mask)
        for _ in range(n):
            dx = self.randn(*x.shape) * tol
            dD = self.randn(*D.shape) * tol
            self.assertTrue(loss < self.error(x + dx, D + dD, alpha, mask))


class TestFloatTensor(TestFloat):
    def setUp(self):
        self.rng = xp.random.RandomState(0)
        self.Dtrue = self.randn(3, 5)
        xtrue = self.randn(101, 10, 3)
        self.xtrue = xtrue * self.rng.uniform(size=3030).reshape(101, 10, 3)

        self.y = xp.dot(self.xtrue, self.Dtrue) + self.randn(101, 10, 5) * 0.1
        self.D = self.Dtrue + self.randn(*self.Dtrue.shape) * 0.3
        self.mask = xp.rint(
                self.rng.uniform(0.4, 1, size=5050)).reshape(101, 10, 5)


class TestComplex(TestFloat):
    def randn(self, *shape):
        return self.rng.randn(*shape) + self.rng.randn(*shape) * 1.0j

    def error(self, x, D, alpha, mask=None):
        mask = xp.ones(self.y.shape, dtype=float) if mask is None else mask
        D = D / xp.maximum(xp.real(xp.sum(xp.conj(D) * D, axis=0)), 1.0)
        loss = xp.sum(xp.square(xp.abs(
            self.y - xp.tensordot(x, D, axes=1))))
        return 0.5 / alpha * loss + xp.sum(xp.abs(x))


if __name__ == '__main__':
    unittest.main()