#pragma once

#include <array>
#include "common/mat.h"
#include "system/hardware/hw.h"

const int TRAJECTORY_SIZE = 33;
const int LAT_MPC_N = 16;
const int LON_MPC_N = 32;
const float MIN_DRAW_DISTANCE = 10.0;
const float MAX_DRAW_DISTANCE = 100.0;

template <typename T, size_t size>
constexpr std::array<T, size> build_idxs(float max_val) {
  std::array<T, size> result{};
  for (int i = 0; i < size; ++i) {
    result[i] = max_val * ((i / (double)(size - 1)) * (i / (double)(size - 1)));
  }
  return result;
}

constexpr auto T_IDXS = build_idxs<double, TRAJECTORY_SIZE>(10.0);
constexpr auto T_IDXS_FLOAT = build_idxs<float, TRAJECTORY_SIZE>(10.0);
constexpr auto X_IDXS = build_idxs<double, TRAJECTORY_SIZE>(192.0);
constexpr auto X_IDXS_FLOAT = build_idxs<float, TRAJECTORY_SIZE>(192.0);

const mat3 fcam_intrinsic_matrix = (mat3){{2648.0, 0.0, 1928.0 / 2,
                                           0.0, 2648.0, 1208.0 / 2,
                                           0.0, 0.0, 1.0}};

// tici ecam focal probably wrong? magnification is not consistent across frame
// Need to retrain model before this can be changed
const mat3 ecam_intrinsic_matrix = (mat3){{567.0, 0.0, 1928.0 / 2,
                                           0.0, 567.0, 1208.0 / 2,
                                           0.0, 0.0, 1.0}};

static inline mat3 get_model_yuv_transform() {
  float db_s = 1.0;
  const mat3 transform = (mat3){{
    1.0, 0.0, 0.0,
    0.0, 1.0, 0.0,
    0.0, 0.0, 1.0
  }};
  // Can this be removed since scale is 1?
  return transform_scale_buffer(transform, db_s);
}


const int FACE_KPTS_SIZE = 14;
const vec3 default_face_kpts_3d[FACE_KPTS_SIZE] = {
  {-33.00, -28.50, 38.30}, {-33.00, -39.50, 38.30},
  {33.00, -28.50, 38.30}, {33.00, -39.50, 38.30},
  {-27.50, 36.40, 45.45}, {-19.80, 41.90, 51.50}, {-11.00, 46.30, 58.10}, {0.00, 47.95, 60.30}, {11.00, 46.30, 58.10}, {19.80, 41.90, 51.50}, {27.50, 36.40, 45.45},
  {0.00, -23.00, 46.55}, {-8.80, 10.00, 68.55}, {0.00, 10.00, 50.40},
};

const int face_end_idxs[4]= {1, 3, 10, FACE_KPTS_SIZE-1};
