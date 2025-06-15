"use client"

import { useEffect, useRef } from "react"
import { Chart, registerables } from "chart.js"

Chart.register(...registerables)

export function BarChart({ darkMode = false }) {
  const chartRef = useRef(null)
  const chartInstance = useRef(null)

  useEffect(() => {
    if (chartRef.current) {
      // Destroy existing chart instance if it exists
      if (chartInstance.current) {
        chartInstance.current.destroy()
      }

      const ctx = chartRef.current.getContext("2d")

      chartInstance.current = new Chart(ctx, {
        type: "bar",
        data: {
          labels: ["5/5", "5/6", "5/7", "5/10"],
          datasets: [
            {
              label: "Cache Entry Usage",
              data: [24, 10, 16, 9],
              backgroundColor: "rgba(59, 130, 246, 0.8)",
              borderColor: "rgba(59, 130, 246, 1)",
              borderWidth: 1,
              borderRadius: 4,
              barThickness: 40,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false,
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: {
                color: darkMode ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)",
              },
              ticks: {
                precision: 0,
                color: darkMode ? "#94a3b8" : undefined,
              },
            },
            x: {
              grid: {
                display: false,
              },
              ticks: {
                color: darkMode ? "#94a3b8" : undefined,
              },
            },
          },
        },
      })
    }

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy()
      }
    }
  }, [darkMode])

  return (
    <div className="h-[240px]">
      <canvas ref={chartRef} />
    </div>
  )
}
