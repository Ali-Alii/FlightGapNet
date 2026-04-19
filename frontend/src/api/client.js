import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 60000,
});

// Global error logger — doesn't suppress errors, just logs them
api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error(
      "[API Error]",
      err.config?.url,
      err.response?.status,
      err.response?.data?.detail || err.message
    );
    return Promise.reject(err);
  }
);

export const fetchLiveFlights = (bounds) =>
  api.get("/flights/live", { params: bounds }).then((r) => r.data);

export const fetchTrack = (icao24) =>
  api.get(`/flights/track/${icao24}`).then((r) => r.data);

export const searchFlights = (q) =>
  api.get("/flights/search", { params: { q } }).then((r) => r.data);

export const predictTrajectory = (payload) =>
  api.post("/predict/trajectory", payload).then((r) => r.data);

export const getModelHistory = (modelType) =>
  api.get(`/predict/model-history/${modelType}`).then((r) => r.data);

export const computeRouteAnalytics = (track) =>
  api.post("/analytics/route", { track }).then((r) => r.data);

// New: returns all ICAO24s available in the local CSV dataset
export const fetchAvailableAircraft = () =>
  api.get("/predict/available-aircraft").then((r) => r.data);