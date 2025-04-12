function initDashboards(data) {
  Chart.register(ChartDataLabels);

  const labels1 = data.labels1;
  const dados1 = data.dados1;
  const labels2 = data.labels2;
  const dados2 = data.dados2;
  const com_formula = data.com_formula;
  const sem_formula = data.sem_formula;
  const com_normalidade = data.com_normalidade;
  const sem_normalidade = data.sem_normalidade;

  new Chart(document.getElementById('grafico1'), {
    type: 'bar',
    data: {
      labels: labels1,
      datasets: [{
        label: 'Quantidade',
        data: dados1,
        backgroundColor: 'rgba(0, 123, 255, 0.6)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        datalabels: {
          anchor: 'end',
          align: 'top',
          color: '#000',
          font: { weight: 'bold' }
        }
      }
    }
  });

  new Chart(document.getElementById('grafico2'), {
    type: 'doughnut',
    data: {
      labels: ['Com fórmula', 'Sem fórmula'],
      datasets: [{
        data: [com_formula, sem_formula],
        backgroundColor: ['#28a745', '#dc3545']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        datalabels: {
          color: '#fff',
          formatter: (value, ctx) => `${value}`,
          font: { weight: 'bold' }
        }
      }
    }
  });

  new Chart(document.getElementById('grafico3'), {
    type: 'bar',
    data: {
      labels: labels2,
      datasets: [{
        label: 'Variáveis',
        data: dados2,
        backgroundColor: 'rgba(255, 193, 7, 0.6)'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        datalabels: {
          anchor: 'end',
          align: 'top',
          color: '#000',
          font: { weight: 'bold' }
        }
      }
    }
  });

  new Chart(document.getElementById('grafico4'), {
    type: 'pie',
    data: {
      labels: ['Com normalidade', 'Sem normalidade'],
      datasets: [{
        data: [com_normalidade, sem_normalidade],
        backgroundColor: ['#0dcaf0', '#6c757d']
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        datalabels: {
          color: '#fff',
          formatter: (value, ctx) => `${value}`,
          font: { weight: 'bold' }
        }
      }
    }
  });
}