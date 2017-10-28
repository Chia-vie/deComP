import sys

try:
    import cupy
    numpy_or_cupy = cupy
    cupy.cuda.set_allocator(cupy.cuda.MemoryPool().malloc)

    def get_array_module(*arrays):
        xp = cupy.get_array_module(arrays[0])
        if any(x is not None and cupy.get_array_module(x)
               is not xp for x in arrays):
            raise TypeError("All the data types should be the same.")

        return xp

except ImportError:
    import numpy
    numpy_or_cupy = numpy

    def get_array_module(*arrays):
        return numpy
