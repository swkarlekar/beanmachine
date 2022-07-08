/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

#pragma once

#include <concepts>

namespace beanmachine::minibmg {

// The AD (Auto-Differentiation) facilities are built on the concept of
// a Number.  A type T satisfies the concept Number<T> if it supports
// all of the following operations.
template <typename T>
concept Number = requires(T a, T b) {
  // there should be a conversion from double to T.
  std::convertible_to<double, T>;
  // it should support the arithmetic oeprators.
  { a + b } -> std::convertible_to<T>;
  { a - b } -> std::convertible_to<T>;
  { -a } -> std::convertible_to<T>;
  { (a * b) } -> std::convertible_to<T>;
  { a / b } -> std::convertible_to<T>;
  // it should support the following transcendental operations.
  { a.pow(b) } -> std::convertible_to<T>;
  { a.exp() } -> std::convertible_to<T>;
  { a.log() } -> std::convertible_to<T>;
  { a.atan() } -> std::convertible_to<T>;
  // There should be a conservative (meaning it can sometime return false when
  // a number satisfies the test) way to sometimes know if a value is exactly
  // zero or one.
  { a.is_definitely_zero() } -> std::same_as<bool>;
  { a.is_definitely_one() } -> std::same_as<bool>;
};

// Support binary operators with double on the left.

template <typename T>
requires Number<T>
inline T operator+(double a, T b) {
  return T(a) + b;
}

template <typename T>
requires Number<T>
inline T operator-(double a, T b) {
  return T(a) - b;
}

template <typename T>
requires Number<T>
inline T operator*(double a, T b) {
  return T(a) * b;
}

template <typename T>
requires Number<T>
inline T operator/(double a, T b) {
  return T(a) / b;
}

template <typename T>
requires Number<T>
inline T pow(double a, T b) {
  return T(a).pow(b);
}

} // namespace beanmachine::minibmg
