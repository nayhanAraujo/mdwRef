// static/js/dashboards.js

function initDashboards(data) {
  if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
  } else {
    console.error("ChartDataLabels plugin não está carregado! Verifique a ordem dos scripts em layout.html.");
  }

  const defaultColors = [
    'rgba(0, 123, 255, 0.8)', 'rgba(40, 167, 69, 0.8)', 'rgba(255, 193, 7, 0.8)',
    'rgba(23, 162, 184, 0.8)', 'rgba(108, 117, 125, 0.8)', 'rgba(220, 53, 69, 0.8)',
    'rgba(102, 16, 242, 0.8)', 'rgba(253, 126, 20, 0.8)' 
  ];
  const defaultBorderColors = defaultColors.map(color => color.replace('0.8', '1'));

  const datalabelsBarConfig = {
    display: true,
    anchor: 'end',
    align: 'top',
    color: '#444',
    font: { weight: '600', size: 10 },
    formatter: (value) => value
  };
  
  const datalabelsPieDoughnutConfig = {
    display: true,
    color: '#ffffff',
    font: { weight: 'bold', size: 11 },
    formatter: (value, ctx) => {
      let sum = 0;
      let dataArr = ctx.chart.data.datasets[0].data;
      dataArr.map(d => sum += parseFloat(d) || 0);
      if (sum === 0) return '0 (0%)';
      let percentage = (value * 100 / sum).toFixed(1) + '%';
      return `${value}\n(${percentage})`;
    }
  };

  // Gráfico 1: Variáveis por Unidade de Medida (filtrando valores > 0)
  const ctxVarsPorUnidade = document.getElementById('graficoVarsPorUnidade');
  if (ctxVarsPorUnidade && data.labelsVarsPorUnidade && data.dadosVarsPorUnidade) {
    const filteredLabels = data.labelsVarsPorUnidade.filter((_, i) => data.dadosVarsPorUnidade[i] > 0);
    const filteredData = data.dadosVarsPorUnidade.filter(value => value > 0);
    if (filteredLabels.length > 0 && filteredData.length > 0) {
      new Chart(ctxVarsPorUnidade, {
        type: 'bar',
        data: {
          labels: filteredLabels,
          datasets: [{
            label: 'Quantidade', data: filteredData,
            backgroundColor: defaultColors[0], borderColor: defaultBorderColors[0], borderWidth: 1
          }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, datalabels: datalabelsBarConfig }, scales: { y: { beginAtZero: true } } }
      });
    } else {
      console.warn("Dashboard: Nenhum dado com quantidade > 0 para 'Variáveis por Unidade'. ID esperado: graficoVarsPorUnidade");
    }
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Variáveis por Unidade'. ID esperado: graficoVarsPorUnidade");
  }

  // Gráfico 2: Proporção: Variáveis Com vs. Sem Fórmula
  const ctxVarsComFormula = document.getElementById('graficoVarsComFormula');
  if (ctxVarsComFormula && typeof data.comFormula !== 'undefined' && typeof data.semFormula !== 'undefined') {
    new Chart(ctxVarsComFormula, {
      type: 'doughnut',
      data: {
        labels: ['Com Fórmula', 'Sem Fórmula'],
        datasets: [{ data: [data.comFormula, data.semFormula], backgroundColor: [defaultColors[1], defaultColors[5]], borderColor: [defaultBorderColors[1], defaultBorderColors[5]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' }, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Variáveis Com/Sem Fórmula'. ID esperado: graficoVarsComFormula");
  }

  // Gráfico 3: Distribuição de Casas Decimais (Variáveis)
  const ctxCasasDecimais = document.getElementById('graficoCasasDecimais');
  if (ctxCasasDecimais && data.labelsCasasDecimais && data.dadosCasasDecimais) {
    new Chart(ctxCasasDecimais, {
      type: 'bar',
      data: {
        labels: data.labelsCasasDecimais,
        datasets: [{
          label: 'Nº de Variáveis', data: data.dadosCasasDecimais,
          backgroundColor: defaultColors[2], borderColor: defaultBorderColors[2], borderWidth: 1
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, datalabels: datalabelsBarConfig }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
    });
  } else {
     console.warn("Dashboard: Canvas ou dados ausentes para 'Casas Decimais'. ID esperado: graficoCasasDecimais");
  }

  // Gráfico 4: Proporção: Variáveis Com vs. Sem Normalidade
  const ctxVarsComNormalidade = document.getElementById('graficoVarsComNormalidade');
  if (ctxVarsComNormalidade && typeof data.comNormalidade !== 'undefined' && typeof data.semNormalidade !== 'undefined') {
    new Chart(ctxVarsComNormalidade, {
      type: 'pie',
      data: {
        labels: ['Com Normalidade', 'Sem Normalidade'],
        datasets: [{ data: [data.comNormalidade, data.semNormalidade], backgroundColor: [defaultColors[3], defaultColors[4]], borderColor: [defaultBorderColors[3], defaultBorderColors[4]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' }, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Variáveis Com/Sem Normalidade'. ID esperado: graficoVarsComNormalidade");
  }

  // Gráfico 5: Scripts por Status de Aprovação
  const ctxScriptsAprovado = document.getElementById('graficoScriptsAprovado');
  if (ctxScriptsAprovado && data.labelsScriptsAprovado && data.dadosScriptsAprovado) {
    new Chart(ctxScriptsAprovado, {
      type: 'doughnut',
      data: {
        labels: data.labelsScriptsAprovado,
        datasets: [{ data: data.dadosScriptsAprovado, backgroundColor: [defaultColors[0], defaultColors[5]], borderColor: [defaultBorderColors[0], defaultBorderColors[5]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: {position: 'top'}, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Scripts por Aprovação'. ID esperado: graficoScriptsAprovado");
  }
  
  // Gráfico 6: Scripts por Status de Atividade
  const ctxScriptsAtivo = document.getElementById('graficoScriptsAtivo');
  if (ctxScriptsAtivo && data.labelsScriptsAtivo && data.dadosScriptsAtivo) {
    new Chart(ctxScriptsAtivo, {
      type: 'doughnut',
      data: {
        labels: data.labelsScriptsAtivo,
        datasets: [{ data: data.dadosScriptsAtivo, backgroundColor: [defaultColors[1], defaultColors[4]], borderColor: [defaultBorderColors[1], defaultBorderColors[4]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: {position: 'top'}, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
     console.warn("Dashboard: Canvas ou dados ausentes para 'Scripts por Atividade'. ID esperado: graficoScriptsAtivo");
  }

  // Gráfico 7: Scripts por Sistema
  const ctxScriptsSistema = document.getElementById('graficoScriptsSistema');
  if (ctxScriptsSistema && data.labelsScriptsSistema && data.dadosScriptsSistema) {
    new Chart(ctxScriptsSistema, {
      type: 'pie',
      data: {
        labels: data.labelsScriptsSistema,
        datasets: [{ data: data.dadosScriptsSistema, backgroundColor: [defaultColors[3], defaultColors[6], defaultColors[2]], borderColor: [defaultBorderColors[3], defaultBorderColors[6], defaultBorderColors[2]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: {position: 'top'}, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Scripts por Sistema'. ID esperado: graficoScriptsSistema");
  }
  
  // Gráfico 8: Referências por Ano
  const ctxReferenciasAno = document.getElementById('graficoReferenciasAno');
  if (ctxReferenciasAno && data.labelsRefAno && data.dadosRefAno) {
    new Chart(ctxReferenciasAno, {
      type: 'bar',
      data: {
        labels: data.labelsRefAno,
        datasets: [{
          label: 'Nº de Referências', data: data.dadosRefAno,
          backgroundColor: defaultColors[2], borderColor: defaultBorderColors[2], borderWidth: 1
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: {display: false}, datalabels: datalabelsBarConfig }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 }} } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Referências por Ano'. ID esperado: graficoReferenciasAno");
  }

  // Gráfico 9: Usuários por Perfil
  const ctxUsuariosPerfil = document.getElementById('graficoUsuariosPerfil');
  if (ctxUsuariosPerfil && data.labelsUserPerfil && data.dadosUserPerfil) {
    new Chart(ctxUsuariosPerfil, {
      type: 'pie',
      data: {
        labels: data.labelsUserPerfil,
        datasets: [{ data: data.dadosUserPerfil, backgroundColor: [defaultColors[5], defaultColors[0], defaultColors[4]], borderColor: [defaultBorderColors[5], defaultBorderColors[0], defaultBorderColors[4]], borderWidth: 1 }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: {position: 'top'}, datalabels: datalabelsPieDoughnutConfig } }
    });
  } else {
    console.warn("Dashboard: Canvas ou dados ausentes para 'Usuários por Perfil'. ID esperado: graficoUsuariosPerfil");
  }
}