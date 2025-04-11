function confirmarExclusao(cod, rotaBase = '/excluir_variavel') {
    Swal.fire({
      title: 'Deseja excluir?',
      text: "Essa ação não pode ser desfeita.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sim, excluir',
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (result.isConfirmed) {
        window.location.href = `${rotaBase}/${cod}`;
      }
    });
  }



  function confirmarExclusaoVariavel(cod) {
    fetch(`/verificar_vinculo_variavel/${cod}`)
      .then(response => response.json())
      .then(data => {
        let texto = data.vinculada
          ? `Essa variável está vinculada a ${data.total} fórmula(s). Deseja excluir tudo?`
          : `Tem certeza que deseja excluir esta variável?`;
  
        Swal.fire({
          title: 'Confirma exclusão?',
          text: texto,
          icon: 'warning',
          showCancelButton: true,
          confirmButtonColor: '#d33',
          cancelButtonColor: '#3085d6',
          confirmButtonText: 'Sim, excluir',
          cancelButtonText: 'Cancelar'
        }).then((result) => {
          if (result.isConfirmed) {
            window.location.href = `/excluir_variavel/${cod}`;
          }
        });
      });
  }
  
  function confirmarSalvarFormula() {
    Swal.fire({
      title: 'Salvar fórmula?',
      text: 'Deseja realmente salvar essa informação?',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sim, salvar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#28a745',
      cancelButtonColor: '#6c757d'
    }).then((result) => {
      if (result.isConfirmed) {
        document.querySelector('form').submit();
      }
    });
  }
  function addAlternativa() {
    const container = document.getElementById('alternativas-wrapper');
    const input = document.createElement('input');
    input.type = "text";
    input.name = "alternativas[]";
    input.className = "form-control mb-2";
    input.placeholder = "Ex: VR_AO1";
    container.appendChild(input);
  
  function confirmarSalvarReferencia() {

    let autor = document.querySelector('#autor').value;
    let ano = document.querySelector('#ano').value;
    if (autor && ano ){

    Swal.fire({
      title: 'Salvar Referencia?',
      text: 'Deseja realmente salvar essa informação?',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sim, salvar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#28a745',
      cancelButtonColor: '#6c757d'
    }).then((result) => {
      if (result.isConfirmed) {
        document.querySelector('form').submit();
      }
    });
  } else{
      Swal.fire({
           icon: "error",
           title: "Oops...",
           text: "Preencha todos os campos",
           });
    }
  }

  function confirmarSalvaUsuario() {
    let nome = document.querySelector('#nome').value;
    let senha=  document.querySelector('#senha').value;
    let identificacao= document.querySelector('#identificacao').value;
    if (nome && senha && identificacao){

      Swal.fire({
        title: 'Salvar Usuário?',
        text: 'Deseja realmente salvar essa informação?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sim, salvar',
        cancelButtonText: 'Cancelar',
        confirmButtonColor: '#28a745',
        cancelButtonColor: '#6c757d'
      }).then((result) => {
        if (result.isConfirmed) {
          
          document.querySelector('form').submit();
          
        }
      });

    } else{
      Swal.fire({
           icon: "error",
           title: "Oops...",
           text: "Preencha todos os campos",
           });
    }
  }

  function confirmarSalvarVariavel() {
    const sigla = document.querySelector('[name="sigla"]').value.trim().toUpperCase();
  
    if (!sigla.startsWith("VR_")) {
      Swal.fire({
        icon: 'warning',
        title: 'Sigla inválida',
        text: 'A sigla deve começar com \"VR_\"',
      });
      return;
    }
  
    Swal.fire({
      title: 'Salvar?',
      text: 'Deseja realmente salvar esta variável?',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Sim, salvar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#28a745',
      cancelButtonColor: '#6c757d'
    }).then((result) => {
      if (result.isConfirmed) {
        document.querySelector('form').submit();
      }
    });
  }
  

function inserirVariavel() {
  const select = document.getElementById('variavelSelect');
  const formulaField = document.querySelector('[name="formula"]');
  const valor = select.value;

  if (valor) {
    const cursorPos = formulaField.selectionStart;
    const textBefore = formulaField.value.substring(0, cursorPos);
    const textAfter = formulaField.value.substring(cursorPos);
    formulaField.value = textBefore + valor + textAfter;
    formulaField.focus();
  }
}
