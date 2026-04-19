# AeroTrack — Trajectory Interpolation & Prediction System

## 📌 Overview

AeroTrack is a full-stack project designed to analyze and reconstruct aircraft trajectories from ADS-B data.
It focuses on **gap-filling (trajectory interpolation)** using both **classical baselines** and **deep learning models (LSTM & GRU)**.

The system includes:

* Data collection & preprocessing pipeline
* Gap simulation (ADS-B signal loss)
* Baseline + ML model comparison
* Evaluation metrics (geodesic error, MAE, RMSE, etc.)
* Interactive frontend dashboard for visualization

---

## 🚀 Features

### 🔹 Data Processing

* Cleans raw ADS-B trajectories
* Removes:

  * ground points
  * unrealistic speeds
  * altitude outliers
* Resamples trajectories to uniform time intervals
* Computes derived features (velocity, heading, etc.)

### 🔹 Gap Simulation

* Simulates missing trajectory segments
* Configurable gap size (5–30 points)
* Used to evaluate model reconstruction performance

### 🔹 Models Implemented

#### 📊 Baselines

* Great Circle (Geodesic interpolation) ⭐ **Best baseline**
* Last Hold (last known position)
* Constant Velocity
* Kalman Filter

#### 🤖 Machine Learning

* LSTM (Long Short-Term Memory)
* GRU (Gated Recurrent Unit)

---

## 📈 Evaluation Metrics

* Latitude MAE / RMSE
* Longitude MAE / RMSE
* Mean Geodesic Error (km)
* Max Geodesic Error
* P90 Geodesic Error
* Altitude MAE
* Path Length Error

---

## 📊 Key Results

| Model       | Mean Geodesic Error (km) |
| ----------- | ------------------------ |
| GreatCircle | **0.98** ✅ Best overall  |
| Kalman      | 1.21                     |
| ConstVel    | 1.50                     |
| LSTM        | 2.29                     |
| GRU         | 4.12                     |
| LastHold    | 21.85 ❌ Worst            |

👉 **Conclusion:**

* GreatCircle is the strongest baseline
* LSTM performs better than GRU
* ML models do **not outperform classical methods** in this setup

---

## 🏗️ Project Structure

```
aerotrack/
│
├── backend/
│   ├── data/                # Raw & processed trajectories
│   ├── saved_models/        # Trained models
│   ├── scripts/
│   │   ├── train_models.py
│   │   ├── evaluate_model.py
│   ├── services/            # Preprocessing, utilities
│   └── config.py
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── BenchmarkPage.jsx
│   │   ├── components/
│   │   └── App.jsx
│   ├── package.json
│   └── tailwind.config.js
│
├── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/aerotrack.git
cd aerotrack
```

---

## 🧠 Backend Setup

### 2️⃣ Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

## 📊 Run Data Processing & Training

### 4️⃣ Train models

```bash
python backend/scripts/train_models.py
```

### 5️⃣ Evaluate models

```bash
python backend/scripts/evaluate_model.py
```

---

## 🌐 Frontend Setup

### 6️⃣ Navigate to frontend

```bash
cd frontend
```

### 7️⃣ Install dependencies

```bash
npm install
```

### 8️⃣ Run frontend

```bash
npm run dev
```

Then open:

```
http://localhost:5173
```

---

## 🎯 How to Use

1. Open the dashboard
2. Select a model:

   * Baseline or ML (LSTM / GRU)
3. Choose an aircraft trajectory
4. Visualize:

   * Original vs predicted trajectory
   * Gap reconstruction
   * Performance metrics

---

## ⚠️ Known Issues

* Some trajectories are dropped due to:

  * insufficient length
  * zero speed signals
* ML models underperform compared to geometric baselines
* Frontend uses static benchmark values (can be linked to backend for dynamic updates)

---

## 🔮 Future Improvements

* Improve ML performance with:

  * attention models (Transformers)
  * better feature engineering
* Real-time streaming predictions
* Connect frontend to backend API dynamically
* Deploy system (cloud + database)

