export function selectPeriodChart(charts: any[]) {
  return charts.find((chart) =>
    (chart.type === 'line' || chart.type === 'area') &&
    (!chart.status || chart.status === 'available' || chart.status === 'zero') &&
    Array.isArray(chart.data) && chart.data.length >= 2 &&
    chart.data.every((point: any) =>
      typeof (point.value ?? point.y) === 'number' &&
      Number.isFinite(point.value ?? point.y)
    )
  );
}
