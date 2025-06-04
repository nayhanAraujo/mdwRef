function updateDateTime() {
    const now = new Date();
    const optionsDate = { day: '2-digit', month: '2-digit', year: 'numeric' };
    const optionsTime = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
    const dateString = now.toLocaleDateString('pt-BR', optionsDate);
    const timeString = now.toLocaleTimeString('pt-BR', optionsTime);
    document.getElementById('currentDateTime').textContent = `${dateString} ${timeString}`;
  }
  
  // Atualiza imediatamente e depois a cada segundo
  updateDateTime();
  setInterval(updateDateTime, 1000); // Atualiza a cada segundo para ver os segundos mudando