import React, { useEffect, useState } from "react";
import axios from "axios";
import { getApiBase } from "../lib/api";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

const API = getApiBase();

export default function TrendsAnalytics() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrendData();
  }, []);

  const loadTrendData = async () => {
    try {
      const response = await axios.get(
        `${API}/trends/readings`
      );

      setData(response.data);
    } catch (error) {
      console.error("Failed to load trend data:", error);
    } finally {
      setLoading(false);
    }
  };

  const temperatureData = data.filter(
    (item) => item.parameter === "temperature"
  );

  const vibrationData = data.filter(
    (item) =>
      item.parameter === "vertical_vibration" ||
      item.parameter === "horizontal_vibration" ||
      item.parameter === "axial_vibration"
  );

  return (
    <div className="p-8">
      <h1 className="text-5xl font-light mb-8">
        Condition Monitoring Trends & Analytics
      </h1>

      {loading ? (
        <p>Loading trend data...</p>
      ) : (
        <>
          <div className="bg-white p-6 rounded-lg shadow mb-8">
            <h2 className="text-2xl mb-4">
              Temperature Trend
            </h2>

            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={temperatureData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Legend />

                <Line
                  type="monotone"
                  dataKey="value"
                  name="Temperature"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-2xl mb-4">
              Vibration Trend
            </h2>

            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={vibrationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Legend />

                <Line
                  type="monotone"
                  dataKey="value"
                  name="Vibration"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
} 