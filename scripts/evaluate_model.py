import numpy as np
import matplotlib.pyplot as plt
from geopy.distance import geodesic


# --------------------------------------------------
# GRU values
# --------------------------------------------------
true_trajectory = [
    (42.42769595375722, 25.956728901734103),
    (42.3685063583815, 26.023626011560694),
    (42.30931676300578, 26.09052312138728),
    (42.250127167630055, 26.15742023121387),
]

predicted_trajectory = [
    (42.43688974165071, 25.95185422413724),
    (42.38706695684388, 26.013731682244877),
    (42.33718291340158, 26.075389739658497),
    (42.2871795772084, 26.1373044801148),
]

baseline_trajectory = [
    (42.42769595375723, 25.956728901734103),
    (42.3685063583815, 26.02362601156069),
    (42.30931676300578, 26.09052312138728),
    (42.250127167630055, 26.15742023121387),
]

true_altitude = [
    11100.815028901734,
    11118.43352601156,
    11136.052023121387,
    11153.670520231213,
]

pred_altitude = [
    11102.477184791785,
    11121.84022690795,
    11140.65832283042,
    11158.981138725501,
]

baseline_altitude = [
    11100.815028901734,
    11118.43352601156,
    11136.052023121387,
    11153.670520231211,
]


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def to_array(points):
    arr = np.asarray(points, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("Trajectory must be a list of (lat, lon) pairs.")
    return arr


def calculate_lat_lon_metrics(predicted, true):
    pred = to_array(predicted)
    true = to_array(true)

    return {
        "lat_mae": float(np.mean(np.abs(pred[:, 0] - true[:, 0]))),
        "lon_mae": float(np.mean(np.abs(pred[:, 1] - true[:, 1]))),
        "lat_rmse": float(np.sqrt(np.mean((pred[:, 0] - true[:, 0]) ** 2))),
        "lon_rmse": float(np.sqrt(np.mean((pred[:, 1] - true[:, 1]) ** 2))),
    }


def calculate_geodesic_errors(predicted, true):
    pred = to_array(predicted)
    true = to_array(true)
    return np.array(
        [geodesic((p[0], p[1]), (t[0], t[1])).km for p, t in zip(pred, true)],
        dtype=float,
    )


def calculate_geodesic_summary(predicted, true):
    errors = calculate_geodesic_errors(predicted, true)
    return {
        "mean_geodesic_error_km": float(np.mean(errors)),
        "max_geodesic_error_km": float(np.max(errors)),
        "p90_geodesic_error_km": float(np.percentile(errors, 90)),
        "geo_error_series": errors.tolist(),
    }


def calculate_altitude_mae(pred_alt, true_alt):
    pred_alt = np.asarray(pred_alt, dtype=float)
    true_alt = np.asarray(true_alt, dtype=float)
    return float(np.mean(np.abs(pred_alt - true_alt)))


def calculate_path_length_km(trajectory):
    pts = to_array(trajectory)
    total = 0.0
    for i in range(len(pts) - 1):
        total += geodesic((pts[i, 0], pts[i, 1]), (pts[i + 1, 0], pts[i + 1, 1])).km
    return float(total)


def calculate_path_length_error(predicted, true):
    return abs(calculate_path_length_km(predicted) - calculate_path_length_km(true))


def evaluate_trajectory(predicted, true, pred_alt=None, true_alt=None, label="model"):
    metrics = {"label": label}
    metrics.update(calculate_lat_lon_metrics(predicted, true))
    metrics.update(calculate_geodesic_summary(predicted, true))

    if pred_alt is not None and true_alt is not None:
        metrics["altitude_mae_m"] = calculate_altitude_mae(pred_alt, true_alt)

    metrics["path_length_error_km"] = calculate_path_length_error(predicted, true)
    return metrics


def print_metrics(title, metrics):
    print(f"\n=== {title} ===")
    for k, v in metrics.items():
        if k in {"label", "geo_error_series"}:
            continue
        print(f"{k}: {v:.6f}")


# --------------------------------------------------
# Evaluate GRU and baseline
# --------------------------------------------------
gru_metrics = evaluate_trajectory(
    predicted_trajectory,
    true_trajectory,
    pred_altitude,
    true_altitude,
    label="gru",
)

baseline_metrics = evaluate_trajectory(
    baseline_trajectory,
    true_trajectory,
    baseline_altitude,
    true_altitude,
    label="baseline",
)

print_metrics("MODEL (GRU)", gru_metrics)
print_metrics("BASELINE", baseline_metrics)


# --------------------------------------------------
# Plot
# --------------------------------------------------
def plot_trajectory(true_pts, pred_pts, baseline_pts=None):
    true_pts = to_array(true_pts)
    pred_pts = to_array(pred_pts)

    plt.figure(figsize=(7, 7))
    plt.plot(true_pts[:, 1], true_pts[:, 0], marker="o", linestyle="-", label="True")
    plt.plot(pred_pts[:, 1], pred_pts[:, 0], marker="x", linestyle="--", label="GRU")

    if baseline_pts is not None:
        baseline_pts = to_array(baseline_pts)
        plt.plot(
            baseline_pts[:, 1],
            baseline_pts[:, 0],
            marker="s",
            linestyle=":",
            label="Baseline",
        )

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Gap Reconstruction Comparison (GRU)")
    plt.legend()
    plt.grid(True)
    plt.axis("equal")
    plt.show()


plot_trajectory(true_trajectory, predicted_trajectory, baseline_trajectory)