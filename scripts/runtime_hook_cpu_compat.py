# -*- coding: utf-8 -*-
"""
PyInstaller 运行时钩子 - CPU 兼容性
用于禁用 NumPy/SciPy 的 AVX2 等现代 CPU 指令集优化
解决云桌面虚拟 CPU 不支持 X86_V2 的问题
"""

import os
import sys

# 禁用 NumPy 的 CPU 优化，强制使用通用指令集
os.environ['NPY_BLAS_ORDER'] = ''
os.environ['NPY_LAPACK_ORDER'] = ''

# 对于 NumPy 2.x，使用以下环境变量
os.environ['NPY_ENABLE_CPU_FEATURES'] = ''  # 禁用所有额外 CPU 特性
os.environ['NPY_DISABLE_CPU_FEATURES'] = 'AVX2,AVX512F,FMA3'  # 显式禁用高级指令集

# 兼容旧版 NumPy
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
