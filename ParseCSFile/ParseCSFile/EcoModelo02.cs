using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Data;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using Medware.Clinicas.Laudos;
using Medware.Clinicas.LogDeErro;
using Medware.Clinicas.Util;
using Medware.Clinicas.Util.Forms;
using System.Windows.Forms.DataVisualization.Charting;
using Medware.Clinicas.BD;

namespace EcoModelo02
{
    public partial class EcoModelo02 : ScriptDll
    {

        #region Propriedades

        private Font mFonteDescricaoItem = new Font("Tahoma", 10, FontStyle.Bold);
        private Font mFonteTabela = new Font("Tahoma", 10, FontStyle.Regular);
        private Font mFonteTextoComum = new Font("Tahoma", 10, FontStyle.Regular);
        private Font mFonteTextoTitulo = new Font("Tahoma", 10, FontStyle.Bold);
        public string mSexo;
        private string mDescriaoProcedimento;
        private float mPeso = 0;
        private float mAltura = 0;
        private int mCodProcedimento;
        public double mSupCorp;
        private bool mPintandoSegmentos;
        private Color mCorHipoDifusa = Color.FromArgb(254, 168, 165);
        private Color mCorNormal = Color.FromArgb(209, 0, 0);
        private Color mCorGrid = SystemColors.Control;
        private Dictionary<string, List<Point>> mDictPointAnaliseSegmentar = new Dictionary<string, List<Point>>();
        private Dictionary<string, string> mDicCombo_CoordenadaImgAS = new Dictionary<string, string>();
        public Dictionary<string, bool> mObjetos = new Dictionary<string, bool>();
        #endregion

        #region Construtor
        public EcoModelo02()
        {
            InitializeComponent();
            InicializarDictPointAnaliseSegmentar();
            VincularCoordenadasCombos();
            CarregarCombos();
        }
        public class LimiteGrafico
        {
            public double Min { get; set; }
            public double Max { get; set; }
            public double Normal { get; set; }
            public double Leve { get; set; }
            public double Moderado { get; set; }
            public double Grave { get; set; }
            public double Aumento { get; set; }
            public double Limitrofe { get; set; }
            public double Anormal { get; set; }
            public bool Ascendente { get; set; }
        }
        #endregion

        #region Métodos
        public override void AtualizarControlesVariavelAgendamento()
        {
            try
            {
                float.TryParse((this.ListaVariaveisAgendamento[VariaveisLaudos.VR_PESOPACIENTE.ToString()]).Trim(), out mPeso);
                float.TryParse((this.ListaVariaveisAgendamento[VariaveisLaudos.VR_ALTURAPACIENTE.ToString()]).Trim(), out mAltura);
                mSexo = (this.ListaVariaveisAgendamento[VariaveisLaudos.VR_SEXOPACIENTE.ToString()]).Trim();

                this.ListarDescendentes().Where(a => a.Name.ToUpper().StartsWith("VR_")).ToList().ForEach(ctrl =>
                {
                    if (!ctrl.IsDisposed)
                    {
                        if (ListaVariaveisAgendamento.ContainsKey(ctrl.Name))
                        {
                            ctrl.Text = ListaVariaveisAgendamento[ctrl.Name];
                        }
                    }
                });

                CalculaImc();
                SuperficieCorporal();
                RetornaIconeGeneroPaciente();
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void AdicionarAgrupadoresImpressao()
        {
            try
            {
                mObjetos.Clear();
                bool Preenchido;
                foreach (Control tabPage in tabControlEco.Controls.OfType<TabPage>())
                {
                    foreach (Control panel in tabPage.Controls.OfType<Panel>())
                    {
                        string chave = panel.Tag.ToString();

                        // Verifica se a chave já existe no dicionário
                        if (!mObjetos.ContainsKey(chave))
                        {
                            mObjetos[chave] = false;
                        }

                        foreach (Control textBox in panel.Controls.OfType<TextBox>())
                        {
                            Preenchido = !string.IsNullOrEmpty(textBox.Text);
                            if (Preenchido)
                            {
                                string chaveTextBox = textBox.Parent.Tag.ToString();
                                // Verifica se a chave já existe no dicionário
                                if (mObjetos.ContainsKey(chaveTextBox))
                                {
                                    mObjetos[chaveTextBox] = true;
                                }
                            }
                        }
                    }
                }

                //SETA DADOS DO PACIENTE SEMPRE VISÍVEL NO MRD
                mObjetos["DADOSPACIENTE"] = true;

                //ADICIONA OBJETOS NA IMPRESSÃO SE FOR MARCADA A OPCAO DE IMPRIMIR
                if (!mObjetos.ContainsKey("GEOMETRIA"))
                {
                    mObjetos.Add("GEOMETRIA", VR_IMPRIMIR_GEOMETRIA.Checked);
                }
                if (!mObjetos.ContainsKey("REPOUSO"))
                {
                    mObjetos.Add("REPOUSO", VR_IMPRIMEREPOUSO.Checked);
                }
                if (!mObjetos.ContainsKey("STRESS"))
                {
                    mObjetos.Add("STRESS", VR_IMPRIMESTRESS.Checked);
                }

                this.MoverMRD(mObjetos);
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.ToString());
                LogDeErroClinicas.GerarLog(ex);
            }
        }

        private void AlteracaoAreaFracional()
        {
            try
            {
                double.TryParse(VR_VD_AREA_DIASTOLE.Text, out double diastole);
                double.TryParse(VR_VD_AREA_SISTOLE.Text, out double sistole);
                double retorno = 0;

                if (diastole != 0 && sistole != 0)
                {
                    if (diastole != 0)
                    {
                        retorno = Math.Round((diastole - sistole) / diastole * 100, 1);
                    }
                    else
                    {
                        retorno = 0;
                    }
                }

                VR_FAC_VD.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private string ValorIndexado(double valor, Index index)
        {
            try
            {
                if (mPeso == 0 || mAltura == 0 || mSupCorp == 0) return string.Empty;

                double retorno = 0;

                switch (index)
                {
                    case Index.SuperfCorp:

                        retorno = Math.Round(valor / mSupCorp, 2);
                        break;

                    case Index.Altura:
                        retorno = Math.Round(valor / (mAltura / 100), 2);
                        break;

                    case Index.Altura2:
                        retorno = Math.Round(valor / Math.Pow((mAltura / 100), 2), 2);
                        break;

                    default:
                        retorno = 0;
                        break;
                }

                return retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
                return "0.00";
            }
        }
        private void VolumesVentriculoEsquerdo(VolumeVe volume)
        {
            try
            {
                TextBox parametro = new TextBox();
                TextBox parametroRetorno = new TextBox();
                double retorno;

                switch (volume)
                {
                    case VolumeVe.Diastolico:
                        parametro = VR_VED;
                        parametroRetorno = VR_VDF;
                        break;
                    case VolumeVe.Sistolico:
                        parametro = VR_VES;
                        parametroRetorno = VR_VSF;
                        break;
                    default:
                        break;
                }

                double.TryParse(parametro.Text, out double valor);
                valor /= 10;

                if (valor != 0)
                {
                    retorno = Math.Round(Math.Pow(valor, 3) * (70 / (24 + (valor * 10))));
                }
                else
                {
                    retorno = 0;
                }

                parametroRetorno.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;

            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void VolumeAtrioEsquerdo()
        {
            double retorno = 0;
            //double aux;
            double.TryParse(VR_AE_A4C.Text, out double a4c);
            double.TryParse(VR_AE_A2C.Text, out double a2c);
            double.TryParse(VR_COMPAE_L.Text, out double compae);

            try
            {
                if (!VR_VAE_MANUAL_CHECK.Checked)
                {
                    if (a4c != 0 && a2c != 0 /*&& compae != 0*/)
                    {
                        //aux = 0.85 * a4c * a2c;

                        //if (compae != 0)
                        //{
                        //    retorno = Math.Round((aux / compae), 2) / 10;
                        //}

                        retorno = (a4c + a2c) / 2;
                    }
                    else
                    {
                        retorno = 0;
                    }

                    VR_VAE.Text = retorno == 0 ? string.Empty : retorno.ToString("F1");
                }
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void EscoreParedes()
        {
            try
            {
                List<ComboBox> repouso = tbpAnaliseSegmentarRepouso.Controls.OfType<ComboBox>().ToList();
                List<ComboBox> stress = tbpAnaliseSegmentarStress.Controls.OfType<ComboBox>().ToList();
                decimal MediaR = 0;
                decimal MediaS = 0;
                var cont = 0;
                //Calcular Repouso
                foreach (ComboBox combo in repouso)
                {
                    var valor = decimal.Parse(combo.Text.Left(1));
                    if (valor > 0)
                    {
                        MediaR += valor;
                        cont++;
                    }
                }
                if (MediaR > 0)
                {
                    MediaR = (cont > 0 ? MediaR / cont : 0);
                }
                //Calcular Stress
                cont = 0;
                foreach (ComboBox combo in stress)
                {

                    var valor = decimal.Parse(combo.Text.Left(1));
                    if (valor > 0)
                    {
                        MediaS += valor;
                        cont++;
                    }
                }
                if (MediaS > 0)
                {
                    MediaS = (cont > 0 ? MediaS / cont : MediaS);
                }

                VR_PAREDE_REPOUSO.Text = MediaR.ToString("N2");
                VR_PAREDE_STRESS.Text = MediaS.ToString("N2");

            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void CarregarCombos()
        {
            try
            {
                // mCarregandoCombo = true;

                var ComboAS = new Dictionary<int, string>()
                {
                    { 5, "0 - Não Visualizada" },
                    { 1, "1 - Normal" },
                    { 2, "2 - Hipocinesia" },
                    { 3, "3 - Acinesia" },
                    { 4, "4 - Discinesia" },
                }.ToList();

                tbpAnaliseSegmentarRepouso.Controls.OfType<ComboBox>().ToList().ForEach(t =>
                {
                    ((ComboBox)t).SelectedIndexChanged -= new EventHandler(this.AnaliseSegmentar_IndexChanged);
                    t.DataSource = ComboAS.ToList();
                    t.DisplayMember = "Value";
                    t.ValueMember = "Key";
                    t.SelectedIndex = 1;
                    ((ComboBox)t).SelectedIndexChanged += new EventHandler(this.AnaliseSegmentar_IndexChanged);
                });

                tbpAnaliseSegmentarStress.Controls.OfType<ComboBox>().ToList().ForEach(t =>
                {
                    ((ComboBox)t).SelectedIndexChanged -= new EventHandler(this.AnaliseSegmentar_IndexChanged);
                    t.DataSource = ComboAS.ToList();
                    t.DisplayMember = "Value";
                    t.ValueMember = "Key";
                    t.SelectedIndex = 1;
                    ((ComboBox)t).SelectedIndexChanged += new EventHandler(this.AnaliseSegmentar_IndexChanged);
                });

                //  mCarregandoCombo = false;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        public override void Evento_Atualizar()
        {
            MontarImpressao();

            if (!string.IsNullOrEmpty(VR_LAUDODESCRITIVO.Text))
            {
                TextoLaudo.Rtf = VR_LAUDODESCRITIVO.Rtf;
                TextoLaudo.AdicionarTexto("\r\n", new Font("Microsoft Sans Serif", 10, FontStyle.Bold), HorizontalAlignment.Left);
                TextoLaudo.AdicionarTexto("<<VR_ASSINATURA>>", new Font("Microsoft Sans Serif", 10, FontStyle.Bold), HorizontalAlignment.Right);
                TextoLaudo.AdicionarTexto("\r\n______________________________________\r\n", new Font("Microsoft Sans Serif", 10, FontStyle.Bold), HorizontalAlignment.Right);
                TextoLaudo.AdicionarTexto(ListaVariaveisAgendamento[VariaveisLaudos.VR_MEDICO.ToString()] + "\r\n" + ListaVariaveisAgendamento[VariaveisLaudos.VR_SIGLACONSELHO.ToString()] + " " + ListaVariaveisAgendamento[VariaveisLaudos.VR_UFCONSELHOMEDICO.ToString()] + " - " + ListaVariaveisAgendamento[VariaveisLaudos.VR_CRMMEDICO.ToString()], new Font("Microsoft Sans Serif", 10, FontStyle.Regular), HorizontalAlignment.Right);
                TextoLaudo.AdicionarTexto("\r\n<<VR_OBSMEDICO>>", new Font("Microsoft Sans Serif", 10, FontStyle.Bold), HorizontalAlignment.Right);
            }

            AdicionarAgrupadoresImpressao();
            base.Evento_Atualizar();
        }
        private void EspessuraRelativaParedes()
        {
            double.TryParse(VR_PPVE.Text, out double ppve);
            double.TryParse(VR_VED.Text, out double ved);
            double retorno;
            try
            {
                if (ppve != 0 && ved != 0)
                {
                    retorno = (2 * ppve) / ved;
                }
                else
                {
                    retorno = 0;
                }

                VR_ERP.Text = retorno != 0 ? retorno.ToString("F2") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        public int ExisteReferencia(string descricao)
        {
            int retorno = 0;
            StringBuilder sql = new StringBuilder();

            try
            {
                sql.AppendLine("SELECT");
                sql.AppendLine("    CODREFERENCIA,");
                sql.AppendLine("    DESCRICAO");
                sql.AppendLine("FROM");
                sql.AppendLine("    REFERENCIA");
                sql.AppendLine("WHERE");
                sql.AppendFormat("    DESCRICAO = '{0}'", descricao);

                DataTable dtReferencia = Bd.PreencheDataTable(sql.ToString(), true);

                if (dtReferencia.Rows.Count > 0)
                {
                    DataRow drLinha = dtReferencia.Rows[0];
                    int.TryParse(drLinha["CODREFERENCIA"].ToString(), out retorno);
                }
                return retorno;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex, sql.ToString());
                return 0;
            }
        }
        private void FracaoDeEjecao(FracaoEjecao fracao)
        {
            try
            {

                switch (fracao)
                {
                    case FracaoEjecao.TeichHolz:

                        double.TryParse(VR_VDF.Text, out double vdf);
                        double.TryParse(VR_VSF.Text, out double vsf);
                        double teichholz;


                        if (vdf != 0 && vsf != 0 && string.IsNullOrEmpty(VR_FESIMPSON_MANUAL.Text))
                        {
                            teichholz = ((vdf - vsf) / vdf) * 100;
                        }
                        else
                        {
                            teichholz = 0;
                        }

                        VR_FETEICHHOLZ.Text = teichholz != 0 ? teichholz.ToString("F1") : string.Empty;
                        break;

                    case FracaoEjecao.Simpson:

                        double.TryParse(VR_VDF.Text, out double vdve);
                        double.TryParse(VR_VSVE.Text, out double vsve);
                        double simpson;

                        if (vdve != 0 && vsve != 0)
                        {
                            simpson = ((vdve - vsve) / vdve * 100);
                        }
                        else
                        {
                            simpson = 0;
                        }

                        VR_FESIMPSON_MANUAL.Text = simpson != 0 ? simpson.ToString("F1") : string.Empty;
                        break;
                    default:
                        break;
                }

            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void ImageLegendar()
        {
            try
            {
                Bitmap bit = new Bitmap(pictureBox6.Width, pictureBox6.Height);
                pictureBox6.DrawToBitmap(bit, new Rectangle(0, 0, pictureBox6.Width, pictureBox6.Height));
                pcbImagemLegendar.Image = bit;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void ImageLegenda()
        {
            try
            {
                Bitmap bit = new Bitmap(VR_DESENHOLEGENDA.Width, VR_DESENHOLEGENDA.Height);
                VR_DESENHOLEGENDA.DrawToBitmap(bit, new Rectangle(0, 0, VR_DESENHOLEGENDA.Width, VR_DESENHOLEGENDA.Height));
                pcbImagemLegenda.Image = bit;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void ImageLegendarGeo()
        {
            try
            {
                Bitmap bit = new Bitmap(pictureBox2.Width, pictureBox2.Height);
                pictureBox2.DrawToBitmap(bit, new Rectangle(0, 0, pictureBox2.Width, pictureBox2.Height));
                pictureBoxPintar2.Image = bit;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void ImageLegendaGeo()
        {
            try
            {
                Bitmap bit = new Bitmap(pictureBox1.Width, pictureBox1.Height);
                pictureBox1.DrawToBitmap(bit, new Rectangle(0, 0, pictureBox1.Width, pictureBox1.Height));
                pictureBoxPintar1.Image = bit;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        public void CalculaImc()
        {
            try
            {
                float imc = mPeso / ((mAltura / 100) * (mAltura / 100));

                string normalidade;
                Color corDestaque = new Color();

                if (imc > 10 && imc < 18.5)
                {
                    normalidade = "Magreza";
                    corDestaque = Color.FromArgb(187, 83, 2);
                }
                else if (imc >= 18.5 && imc <= 24.9)
                {
                    normalidade = "Normal";
                    corDestaque = Color.FromArgb(57, 109, 7);
                }
                else if (imc >= 25 && imc <= 29.9)
                {
                    normalidade = "Sobrepeso I";
                    corDestaque = Color.FromArgb(187, 83, 2);
                }
                else if (imc >= 30 && imc <= 39.9)
                {
                    normalidade = "Obesidade II";
                    corDestaque = Color.FromArgb(204, 73, 2);
                }
                else if (imc >= 40 && imc < 100)
                {
                    normalidade = "Obesidade Grave III";
                    corDestaque = Color.FromArgb(177, 3, 3);
                }
                else
                {
                    normalidade = string.Empty;
                    corDestaque = Color.FromArgb(48, 48, 48);
                    imc = 0;
                }

                VR_IMC.Text = imc.ToString("F1");
                VR_IMC.ForeColor = corDestaque;
                VR_DESCRICAOIMC.Text = normalidade;
                VR_DESCRICAOIMC.ForeColor = corDestaque;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void InicializarDictPointAnaliseSegmentar()
        {
            int convet = ClsUtilEco.CONVERT_PIXEL_TWIPS;
            try
            {
                mDictPointAnaliseSegmentar.Add("Coordenada02", new List<Point>() { new Point { X = 175 * convet, Y = 82 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada01", new List<Point>() { new Point { X = 340 * convet, Y = 82 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada06", new List<Point>() { new Point { X = 535 * convet, Y = 82 * convet }, new Point { X = 590 * convet, Y = 195 * convet } });

                mDictPointAnaliseSegmentar.Add("Coordenada03", new List<Point>() { new Point { X = 175 * convet, Y = 600 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada04", new List<Point>() { new Point { X = 340 * convet, Y = 600 * convet }, new Point { X = 340 * convet, Y = 640 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada05", new List<Point>() { new Point { X = 535 * convet, Y = 600 * convet } });

                mDictPointAnaliseSegmentar.Add("Coordenada08", new List<Point>() { new Point { X = 220 * convet, Y = 175 * convet }, new Point { X = 170 * convet, Y = 233 * convet }, new Point { X = 170 * convet, Y = 248 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada07", new List<Point>() { new Point { X = 340 * convet, Y = 175 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada12", new List<Point>() { new Point { X = 490 * convet, Y = 175 * convet } });

                mDictPointAnaliseSegmentar.Add("Coordenada09", new List<Point>() { new Point { X = 220 * convet, Y = 507 * convet }, new Point { X = 170 * convet, Y = 430 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada10", new List<Point>() { new Point { X = 340 * convet, Y = 507 * convet }, new Point { X = 360 * convet, Y = 535 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada11", new List<Point>() { new Point { X = 490 * convet, Y = 507 * convet } });

                mDictPointAnaliseSegmentar.Add("Coordenada13", new List<Point>() { new Point { X = 345 * convet, Y = 240 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada15", new List<Point>() { new Point { X = 345 * convet, Y = 450 * convet } });

                mDictPointAnaliseSegmentar.Add("Coordenada14", new List<Point>() { new Point { X = 245 * convet, Y = 305 * convet }, new Point { X = 243 * convet, Y = 340 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada17", new List<Point>() { new Point { X = 340 * convet, Y = 305 * convet } });
                mDictPointAnaliseSegmentar.Add("Coordenada16", new List<Point>() { new Point { X = 440 * convet, Y = 305 * convet }, new Point { X = 463 * convet, Y = 345 * convet } });
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void IndiceEncurtamentoParedePosteriorVe()
        {
            try
            {
                double.TryParse(VR_VED.Text, out double ved);
                double.TryParse(VR_VES.Text, out double ves);
                double retorno = 0;

                if (ved != 0 && ves != 0)
                {
                    if (ved != 0)
                    {
                        retorno = ((ved - ves) / ved * 100);
                    }
                    else
                    {
                        retorno = 0;
                    }
                }

                VR_PEC.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void RetornaNormalidades(TextBox campo)
        {
            try
            {
                // IDENTIFICAR O CHART DO CAMPO
                Chart GraficoCampo = this.Controls.Find($"{campo.Name}_CHART", true).FirstOrDefault() as Chart;
                // DEFINIR O ENUM DA CLASSE COM BASE NO SEXO
                Sexo sexo = mSexo.StartsWith("M") ? Sexo.Masculino : mSexo.StartsWith("F") ? Sexo.Feminino : Sexo.Indefinido;

                var mapeamentoCampos = new Dictionary<string, Action<double>>
                {
                    //AORTA
                    { "VR_AO", valor => { VR_AO_ANEL_I.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_ANEL_I", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_AO_SV", valor => { VR_AO_SEIO_VALSALVA_I.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_SEIO_VALSALVA_I", valor => {Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_JUNCAO", valor => { VR_AO_JUNCAO_I.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_JUNCAO_I", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_ASC_PROX", valor => { VR_AO_ASC_PROX_I.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AO_ASC_PROX_I", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_ARCOAO", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    //{ "VR_SGL_AE", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AE", valor => { VR_AEI.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AEI", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AE_A4C", valor => { VolumeAtrioEsquerdo(); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AE_A2C", valor => { VolumeAtrioEsquerdo(); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_COMPAE_L", valor => { VolumeAtrioEsquerdo() ;}},
                    { "VR_VAE", valor => { VR_VAE_SC.Text = ValorIndexado(valor, Index.SuperfCorp); 
                        /*VR_VAE_ALTURA.Text = ValorIndexado(valor, Index.Altura);  VR_VAE_ALTURA2.Text = ValorIndexado(valor, Index.Altura2);*/ }},
                    { "VR_VAE_SC", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    //{ "VR_VAE_ALTURA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    //{ "VR_VAE_ALTURA2", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_VSVE", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_VED", valor => { VR_VEDI.Text = ValorIndexado(valor, Index.SuperfCorp); VR_VED_ALTURA.Text = ValorIndexado(valor, Index.Altura);  Grafico(GraficoCampo, sexo, valor); MassaVEntricularVE(); EspessuraRelativaParedes(); VolumesVentriculoEsquerdo(VolumeVe.Diastolico); IndiceEncurtamentoParedePosteriorVe();}},
                    { "VR_VEDI", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_VED_ALTURA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_VES", valor => {Grafico(GraficoCampo, sexo, valor); VolumesVentriculoEsquerdo(VolumeVe.Sistolico); IndiceEncurtamentoParedePosteriorVe();}},
                    { "VR_SEPTO", valor => { MassaVEntricularVE(); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_PPVE", valor => { MassaVEntricularVE(); EspessuraRelativaParedes(); Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_MVE", valor => { VR_MVE_SC.Text = ValorIndexado(valor, Index.SuperfCorp); VR_MVE_ALTURA.Text = ValorIndexado(valor, Index.Altura); Grafico(GraficoCampo, sexo, valor); PintarHipertrifia();}},
                    { "VR_MVE_SC", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_MVE_ALTURA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_ERP", valor => { Grafico(GraficoCampo, sexo, valor); PintarHipertrifia();}},
                    { "VR_VDF", valor => { VR_VDF_I.Text = ValorIndexado(valor, Index.Altura); FracaoDeEjecao(FracaoEjecao.TeichHolz); Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VDF_I", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    //{ "VR_VDF_BI", valor => { VR_VDF_BI_I.Text = ValorIndexado(valor, Index.Altura); Grafico(GraficoCampo, sexo, valor); }},
                    //{ "VR_VDF_BI_I", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VSF", valor => { VR_VSF_I.Text = ValorIndexado(valor, Index.SuperfCorp); FracaoDeEjecao(FracaoEjecao.TeichHolz); Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VSF_I", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    //{ "VR_VSF_BI", valor => { VR_VSF_BI_I.Text = ValorIndexado(valor, Index.SuperfCorp); Grafico(GraficoCampo, sexo, valor); }},
                    //{ "VR_VSF_BI_I", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_FESIMPSON_MANUAL", valor => { FracaoDeEjecao(FracaoEjecao.TeichHolz); Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_FETEICHHOLZ", valor => { Grafico(VR_FESIMPSON_MANUAL_CHART, sexo, valor);}},
                    { "VR_PEC", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_SGL", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_DPDTVE", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_SLINHA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_MAPS", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_INDICEA", valor => { Grafico(GraficoCampo, sexo, valor); RelacaoIndices(Relacao.Ea); }},
                    { "VR_INDICEE", valor => { Grafico(GraficoCampo, sexo, valor); RelacaoIndices(Relacao.Ea); RelacaoIndices(Relacao.Ee); RelacaoIndices(Relacao.mediaEe); }},
                    { "VR_INDICEELINHA", valor => { Grafico(GraficoCampo, sexo, valor); RelacaoIndices(Relacao.mediaEe);}},
                    { "VR_INDICEELINHA_LAT", valor => { Grafico(GraficoCampo, sexo, valor); RelacaoIndices(Relacao.Ee); }},
                    { "VR_REL_E_A", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_MEDIA_E_ELINHA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_REL_E_E_LINHA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_ATRIODIREITOAREA", valor => { Grafico(GraficoCampo, sexo, valor);}},
                    { "VR_AD_A4C", valor => { VR_VAD_SC.Text = ValorIndexado(valor, Index.SuperfCorp); }},
                    { "VR_VAD_SC", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VD_BT", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VD_MEDIO", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VD_BASEAPICE", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_A_PULMONAR", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_EVD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VCI", valor => { Grafico(GraficoCampo, sexo, valor); VariacaoVeiaCavaInferior(); PressaoArterialDiastolica(); }},
                    { "VR_VCII", valor => { VariacaoVeiaCavaInferior(); }},
                    { "VR_VATL", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_GLSVD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_FWSVD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_DSATL", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_DPDT_VD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VD_AREA_DIASTOLE", valor => { AlteracaoAreaFracional(); }},
                    { "VR_VD_AREA_SISTOLE", valor => { AlteracaoAreaFracional(); }},
                    { "VR_FAC_VD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VEL_REG_TRICUSPIDE", valor => { PressaoPulmonarPico(); }},
                    { "VR_V_VCI", valor => { Grafico(GraficoCampo, sexo, valor); PressaoArterialDiastolica(); }},
                    { "VR_PPICO_CALCULADA", valor => { PressaoSistolicaArteriaPulmonar(); }},
                    { "VR_PRESSAO_AD", valor => { PressaoSistolicaArteriaPulmonar(); }},
                    { "VR_PSAP", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_DT_VSVD", valor => { Grafico(GraficoCampo, sexo, valor); }},
                    { "VR_VEL_INICIAL_REG_PULM", valor => { Grafico(GraficoCampo, sexo, valor); }},
                };


                if (mapeamentoCampos.ContainsKey(campo.Name))
                {
                    double.TryParse(campo.Text, out double valor);
                    mapeamentoCampos[campo.Name](valor);
                }

            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void RelacaoIndices(Relacao indice)
        {
            try
            {
                double.TryParse(VR_INDICEE.Text, out double indicee);
                double retorno = 0;

                switch (indice)
                {
                    case Relacao.Ea:

                        double.TryParse(VR_INDICEA.Text, out double indicea);

                        if (indicee != 0 && indicea != 0)
                        {
                            if (indicea != 0)
                            {
                                retorno = Math.Round(Math.Abs(indicee) / Math.Abs(indicea), 2);
                            }
                            else
                            {
                                retorno = 0;
                            }
                        }

                        VR_REL_E_A.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
                        break;

                    case Relacao.Ee:

                        double.TryParse(VR_INDICEELINHA_LAT.Text, out double linhalat);
                        double eelinhalat = Math.Round(Math.Abs(indicee / Math.Abs(linhalat)));

                        if (linhalat != 0 && indicee != 0)
                        {
                            if (eelinhalat != 0)
                            {
                                retorno = ((Math.Abs(eelinhalat) + Math.Abs(eelinhalat)) / 2);
                            }
                            else
                            {
                                retorno = 0;
                            }
                        }

                        VR_MEDIA_E_ELINHA.Text = retorno != 0 ? retorno.ToString("F0") : string.Empty;
                        break;

                    case Relacao.mediaEe:

                        double.TryParse(VR_INDICEELINHA.Text, out double inlinha);

                        if (indicee != 0 && inlinha != 0)
                        {
                            if (inlinha != 0)
                            {
                                retorno = Math.Round(Math.Abs(indicee / Math.Abs(inlinha)));
                            }
                            else
                            {
                                retorno = 0;
                            }
                        }

                        VR_REL_E_E_LINHA.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;

                        break;

                    default:
                        break;
                }
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void MassaVEntricularVE()
        {
            double retorno;
            try
            {
                double.TryParse(VR_VED.Text, out double ved);
                double.TryParse(VR_SEPTO.Text, out double septo);
                double.TryParse(VR_PPVE.Text, out double ppve);

                if (ved != 0 && septo != 0 && ppve != 0)
                {
                    //retorno = Math.Round((0.8 * (1.04 * Math.Pow(((ved / 10) + (septo / 10) + (ppve / 10)), 3) - Math.Pow((ved / 10), 3))) + 0.6, 1);
                    retorno = (0.8 * (1.047 * ((Math.Pow(ved + septo + ppve, 3) - Math.Pow(ved, 3)))) + 0.6) / 1000;
                }
                else
                {
                    retorno = 0;
                }

                VR_MVE.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void MontarImpressaoHipertrofia()
        {
            try
            {

                Bitmap btm = new Bitmap(pictureBoxImpressaoHipertrofia.Width, pictureBoxImpressaoHipertrofia.Height);
                pnlRemodeling.DrawToBitmap(btm, new Rectangle(0, 0, pictureBoxImpressaoHipertrofia.Width, pictureBoxImpressaoHipertrofia.Height));
                pnlConcentricHyper.DrawToBitmap(btm, new Rectangle(pnlConcentricHyper.Width, 0, pictureBoxImpressaoHipertrofia.Width, pictureBoxImpressaoHipertrofia.Height));
                pnlNormal.DrawToBitmap(btm, new Rectangle(0, pnlNormal.Height, pictureBoxImpressaoHipertrofia.Width, pictureBoxImpressaoHipertrofia.Height));
                pnlEccentricHyper.DrawToBitmap(btm, new Rectangle(pnlEccentricHyper.Width, pnlEccentricHyper.Height, pictureBoxImpressaoHipertrofia.Width, pictureBoxImpressaoHipertrofia.Height));
                pictureBoxImpressaoHipertrofia.Image = btm;


            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void MontarImpressaoImageRepouso()
        {
            try
            {
                Bitmap bit = new Bitmap(VR_DESENHOSEGMENTOS.Width, VR_DESENHOSEGMENTOS.Height);
                VR_DESENHOSEGMENTOS.DrawToBitmap(bit, new Rectangle(0, 0, VR_DESENHOSEGMENTOS.Width, VR_DESENHOSEGMENTOS.Height));
                pcbImagemRepouso.Image = bit;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void MontarImpressaoImageStress()
        {
            try
            {
                if (VR_DESENHOSEGMENTOSBOLOTAS.Image == null || VR_DESENHOSEGMENTOSBOLOTAS.Image.Width <= 0 || VR_DESENHOSEGMENTOSBOLOTAS.Image.Height <= 0 ||
                    VR_DESENHOSEGMENTOSTRESS.Image == null || VR_DESENHOSEGMENTOSTRESS.Image.Width <= 0 || VR_DESENHOSEGMENTOSTRESS.Image.Height <= 0)
                {
                    return;
                }

                Bitmap img1 = new Bitmap(VR_DESENHOSEGMENTOSBOLOTAS.Image);
                Bitmap img2 = new Bitmap(VR_DESENHOSEGMENTOSTRESS.Image);

                img1.MakeTransparent();
                img2.MakeTransparent();
                Bitmap btm = new Bitmap(1310, 1611);
                Graphics g = Graphics.FromImage(btm);
                g.DrawImage(img1, 0, 0, img1.Width, img1.Height);
                g.DrawImage(img2, img1.Width - 550, img1.Height - 240, (float)(img2.Width * 1.7), (float)(img2.Height * 1.7));
                pcbImagemStress.Image = btm;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void PintarHipertrifia()
        {
            try
            {
                pnlRemodeling.BackColor = Color.LightBlue;
                pnlConcentricHyper.BackColor = Color.LightBlue;
                pnlNormal.BackColor = Color.LightBlue;
                pnlEccentricHyper.BackColor = Color.LightBlue;

                double.TryParse(VR_MVE_SC.Text, out double IndiceMassaVE);
                double.TryParse(VR_ERP.Text, out double erp);
                if (erp > 0 && IndiceMassaVE > 0)
                {
                    //@BRUNO
                    if (VR_SEXOPACIENTE.ToString() == "Feminino")
                    {
                        if (erp <= 0.42 && IndiceMassaVE <= 95) { pnlNormal.BackColor = Color.Green; }
                        if (erp > 0.42 && IndiceMassaVE <= 95) { pnlRemodeling.BackColor = Color.LightCoral; }
                        if (erp > 0.42 && IndiceMassaVE > 95) { pnlConcentricHyper.BackColor = Color.LightCoral; }
                        if (erp <= 0.42 && IndiceMassaVE > 95) { pnlEccentricHyper.BackColor = Color.LightCoral; }
                    }
                    else
                    {
                        if (erp <= 0.42 && IndiceMassaVE <= 115) { pnlNormal.BackColor = Color.Green; }
                        if (erp > 0.42 && IndiceMassaVE <= 115) { pnlRemodeling.BackColor = Color.LightCoral; }
                        if (erp > 0.42 && IndiceMassaVE > 115) { pnlConcentricHyper.BackColor = Color.LightCoral; }
                        if (erp <= 0.42 && IndiceMassaVE > 115) { pnlEccentricHyper.BackColor = Color.LightCoral; }
                    }

                }

                ImageLegendarGeo();
                ImageLegendaGeo();
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
            MontarImpressaoHipertrofia();
        }
        private Bitmap PintarImgAnaliseSegmentar(Color cor, Bitmap pic)
        {

            Bitmap btm = new Bitmap(pic);
            try
            {
                try
                {
                    foreach (var i in mDicCombo_CoordenadaImgAS)
                    {
                        if (mDictPointAnaliseSegmentar.TryGetValue(i.Value, out List<Point> listaCoordenadasImg))
                            foreach (Point pontos in listaCoordenadasImg)
                            {
                                btm = Pintar(pontos.X, pontos.Y, cor.ToArgb(), btm);
                            }
                    }
                }
                catch (Exception ex)
                {
                    LogDeErroClinicas.GerarLog(ex);
                }
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }

            return btm;
        }
        private void PintarImgAnaliseSegmentar(Control sender, PictureBox pic)
        {
            try
            {
                var obj = sender as ComboBox;
                if (obj != null)
                {
                    if (obj.SelectedValue != null)
                    {
                        ClsUtilEco.Cor cor = (ClsUtilEco.Cor)Enum.Parse(typeof(ClsUtilEco.Cor), obj.SelectedValue.ToString());
                        int corAnaliseSegmentar = Convert.ToInt32(cor.GetAttributeValue<DescriptionAttribute, string>(x => x.Description));
                        if (mDicCombo_CoordenadaImgAS.TryGetValue(obj.Name, out string coordenadaimg))
                        {
                            if (mDictPointAnaliseSegmentar.TryGetValue(coordenadaimg, out List<Point> listaCoordenadasImg))
                            {
                                Bitmap btm = new Bitmap(pic.Image);
                                foreach (Point pontos in listaCoordenadasImg)
                                {
                                    btm = Pintar(pontos.X, pontos.Y, corAnaliseSegmentar, btm);
                                }
                                pic.Image = btm;
                                if (pic == VR_DESENHOSEGMENTOS)
                                {
                                    VR_DESENHOSEGMENTOSBOLOTAS.Image = VR_DESENHOSEGMENTOS.Image;
                                }
                            }
                        }
                    }

                    MontarImpressaoImageRepouso();
                    MontarImpressaoImageStress();
                    ImageLegendar();
                    ImageLegenda();
                }
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void PintarSegmentos(Color cor, int index, PictureBox pic, TabPage tbp)
        {
            Bitmap btm = new Bitmap(pic.Image);
            try
            {
                mPintandoSegmentos = true;
                btm = PintarImgAnaliseSegmentar(cor, btm);
                pic.Image = btm;

                tbp.Controls.OfType<ComboBox>().ToList().ForEach(t =>
                {
                    ((ComboBox)t).SelectedIndexChanged -= new EventHandler(this.AnaliseSegmentar_IndexChanged);
                    t.SelectedIndex = index;
                    ((ComboBox)t).SelectedIndexChanged += new EventHandler(this.AnaliseSegmentar_IndexChanged);
                });

                MontarImpressaoImageRepouso();
                ImageLegendar();
                ImageLegenda();
                mPintandoSegmentos = false;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void PressaoPulmonarPico()
        {
            try
            {
                double.TryParse(VR_VEL_REG_TRICUSPIDE.Text, out double RegTricuspide);
                double retorno;

                if (RegTricuspide != 0)
                {
                    retorno = Math.Round(4 * (RegTricuspide * RegTricuspide));
                }
                else
                {
                    retorno = 0;
                }

                VR_PPICO_CALCULADA.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void PressaoArterialDiastolica()
        {
            try
            {
                double.TryParse(VR_VCI.Text, out double vci);
                double.TryParse(VR_V_VCI.Text, out double vcii);

                string inspiracao = VR_INSPIRACAO.Text;
                int pressao;

                switch (inspiracao)
                {
                    case "profunda":
                        if (vci < 22 && vcii > 49)
                        {
                            pressao = 3;
                        }
                        else if (vci > 21 && vcii < 50)
                        {
                            pressao = 15;
                        }
                        else
                        {
                            pressao = 8;
                        }
                        break;

                    case "superficial":
                        if (vci < 22 && vcii > 19)
                        {
                            pressao = 3;
                        }
                        else if (vci > 21 && vcii < 20)
                        {
                            pressao = 15;
                        }
                        else
                        {
                            pressao = 8;
                        }
                        break;
                    default:
                        pressao = 8;
                        break;
                }

                VR_PRESSAO_AD.Text = pressao.ToString("00");
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void PressaoSistolicaArteriaPulmonar()
        {
            try
            {
                double.TryParse(VR_PPICO_CALCULADA.Text, out double picoCalculada);
                double.TryParse(VR_PRESSAO_AD.Text, out double pressaoAD);
                double retorno;

                if (picoCalculada != 0 && pressaoAD != 0)
                {
                    retorno = (Math.Abs(picoCalculada)) + (pressaoAD);
                }
                else
                {
                    retorno = 0;
                }

                VR_PSAP.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void VincularCoordenadasCombos()
        {
            try
            {
                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTERIORREP", "Coordenada01");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTERIORPOSSTRESS", "Coordenada01");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTEROSEPTALREP", "Coordenada02");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTEROSEPTALPOSSTRESS", "Coordenada02");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFEROSEPTALREP", "Coordenada03");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFEROSEPTALPOSSTRESS", "Coordenada03");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFERIORREP", "Coordenada04");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFERIORPOSSTRESS", "Coordenada04");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFEROLATERALREP", "Coordenada05");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALINFEROLATERALPOSSTRESS", "Coordenada05");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTEROLATERALREP", "Coordenada06");

                mDicCombo_CoordenadaImgAS.Add("VR_BASALANTEROLATERALPOSSTRESS", "Coordenada06");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTERIORREP", "Coordenada07");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTERIORPOSSTRESS", "Coordenada07");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTEROSEPTALREP", "Coordenada08");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTEROSEPTALPOSSTRESS", "Coordenada08");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFEROSEPTALREP", "Coordenada09");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFEROSEPTALPOSSTRESS", "Coordenada09");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFERIORREP", "Coordenada10");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFERIORPOSSTRESS", "Coordenada10");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFEROLATERALREP", "Coordenada11");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDINFEROLATERALPOSSTRESS", "Coordenada11");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTEROLATERALREP", "Coordenada12");

                mDicCombo_CoordenadaImgAS.Add("VR_MIDANTEROLATERALPOSSTRESS", "Coordenada12");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALANTERIORREP", "Coordenada13");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALANTERIORPOSSTRESS", "Coordenada13");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALSEPTALREP", "Coordenada14");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALSEPTALPOSSTRESS", "Coordenada14");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALINFERIORREP", "Coordenada15");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALINFERIORPOSSTRESS", "Coordenada15");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALLATERALREP", "Coordenada16");

                mDicCombo_CoordenadaImgAS.Add("VR_APICALLATERALPOSSTRESS", "Coordenada16");

                mDicCombo_CoordenadaImgAS.Add("VR_APEXREP", "Coordenada17");

                mDicCombo_CoordenadaImgAS.Add("VR_APEXPOSSTRESS", "Coordenada17");
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void VariacaoVeiaCavaInferior()
        {
            try
            {
                double.TryParse(VR_VCI.Text, out double vci);
                double.TryParse(VR_VCII.Text, out double vcii);
                double retorno = 0;

                if (vci != 0 && vcii != 0)
                {
                    if (vci != 0)
                    {
                        retorno = Math.Round((vci - vcii) / vci * 100, 2);
                    }
                    else
                    {
                        retorno = 0;
                    }
                }

                VR_V_VCI.Text = retorno != 0 ? retorno.ToString("F1") : string.Empty;
            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        public void SuperficieCorporal()
        {
            try
            {
                double valor;
                valor = 0.007184 * (Math.Pow(mPeso, 0.425)) * (Math.Pow(mAltura, 0.725));

                VR_SUPCORP.Text = valor.ToString("N2");
                mSupCorp = valor;
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void RetornaIconeGeneroPaciente()
        {
            try
            {
                TabPage tabPage = tabControlEco.TabPages["tabPageMedidas"];

                foreach (Panel panel in tabPage.Controls.OfType<Panel>())
                {
                    foreach (Label label in panel.Controls.OfType<Label>())
                    {
                        if (label.ImageList != null && mSexo != null)
                        {
                            label.ImageIndex = mSexo.StartsWith("M") ? 1 : mSexo.StartsWith("F") ? 0 : -1;
                            toolTipDescricao.SetToolTip(label, $"Valores de normalidade baseados no sexo {mSexo}");
                        }
                    }
                }

            }
            catch (Exception ex)
            {

                LogDeErroClinicas.GerarLog(ex);
            }
        }
        #region Métodos Grafico
        public void Grafico(Chart grafico, Sexo sexo, double valor)
        {
            try
            {
                if (grafico == null) return;

                if (sexo == Sexo.Indefinido)
                {
                    grafico.Series.Clear();
                    grafico.ChartAreas[0].AxisX.CustomLabels.Clear();
                    return;
                }

                var limites = ObterLimitesGrafico(grafico.Name, sexo);

                string descricaoNormalidade = RetornaDescricaoNormalidade(valor, limites);

                if (limites.Aumento != 0 || limites.Limitrofe != 0)
                {
                    RetornaGraficoNormalidade(grafico, valor, descricaoNormalidade, limites.Min, limites.Max, limites.Normal, limites.Aumento, 0);
                }
                else
                {
                    RetornaGraficoNormalidade(grafico, valor, descricaoNormalidade, limites.Min, limites.Max, limites.Normal, limites.Leve, limites.Moderado, limites.Grave, 0);
                }
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private LimiteGrafico ObterLimitesGrafico(string nomeGrafico, Sexo sexo)
        {
            var limites = new LimiteGrafico();

            if (sexo == Sexo.Masculino)
            {
                switch (nomeGrafico)
                {
                    case "VR_AO_CHART":
                        limites = new LimiteGrafico { Min = 23, Max = 57, Normal = 23, Leve = 30, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_ANEL_I_CHART":
                        limites = new LimiteGrafico { Min = 15, Max = 30, Normal = 15, Aumento = 24 };
                        break;
                    case "VR_AO_SV_CHART":
                        limites = new LimiteGrafico { Min = 31, Max = 57, Normal = 31, Leve = 38, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_SEIO_VALSALVA_I_CHART":
                        limites = new LimiteGrafico { Min = 15, Max = 30, Normal = 15, Aumento = 19 };
                        break;
                    case "VR_AO_JUNCAO_CHART":
                        limites = new LimiteGrafico { Min = 26, Max = 57, Normal = 26, Leve = 38, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_JUNCAO_I_CHART":
                        limites = new LimiteGrafico { Min = 13, Max = 25, Normal = 13, Aumento = 18 };
                        break;
                    case "VR_AO_ASC_PROX_CHART":
                        limites = new LimiteGrafico { Min = 26, Max = 57, Normal = 26, Leve = 40, Moderado = 50, Grave = 57 };
                        break;
                    case "VR_AO_ASC_PROX_I_CHART":
                        limites = new LimiteGrafico { Min = 14, Max = 25, Normal = 14, Aumento = 17 };
                        break;
                    case "VR_ARCOAO_CHART":
                        limites = new LimiteGrafico { Min = 22, Max = 57, Normal = 22, Leve = 36, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_SGL_AE_CHART":
                        limites = new LimiteGrafico { Min = -30, Max = 0, Normal = -24, Limitrofe = -18 };
                        break;
                    case "VR_AE_CHART":
                        limites = new LimiteGrafico { Min = 30, Max = 50, Normal = 30, Aumento = 40 };
                        break;
                    case "VR_AEI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 35, Normal = 23, Leve = 27, Moderado = 30, Grave = 35 };
                        break;
                    case "VR_AE_A4C_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 600, Normal = 210, Leve = 300, Moderado = 400, Grave = 600 };
                        break;
                    case "VR_AE_A2C_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 600, Normal = 210, Leve = 300, Moderado = 400, Grave = 600 };
                        break;
                    case "VR_VAE_SC_CHART":
                        limites = new LimiteGrafico { Min = 16, Max = 60, Normal = 16, Leve = 35, Moderado = 42, Grave = 48 };
                        break;
                    case "VR_VAE_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 50, Normal = 0, Aumento = 35.8 };
                        break;
                    case "VR_VAE_ALTURA2_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 48, Normal = 0, Aumento = 35 };
                        break;
                    case "VR_VSVE_CHART":
                        double preditivoCm = Math.Round(((5.7 * mSupCorp) + 12.1) / 10, 2);
                        double preditivoMm = Math.Round(preditivoCm * 10);
                        double minimo = Math.Round(preditivoMm - 20);
                        double maximo = Math.Round(preditivoMm + 20);

                        limites = new LimiteGrafico { Min = minimo, Max = maximo, Normal = minimo, Aumento = preditivoMm };
                        break;
                    case "VR_VED_CHART":
                        limites = new LimiteGrafico { Min = 42, Max = 65, Normal = 42, Aumento = 58.5 };
                        break;
                    case "VR_VEDI_CHART":
                        limites = new LimiteGrafico { Min = 2.5, Max = 4, Normal = 2.5, Leve = 3.2, Moderado = 3.5, Grave = 3.7 };
                        break;
                    case "VR_VED_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 2.4, Max = 4, Normal = 2.4, Leve = 3.4, Moderado = 3.6, Grave = 3.8 };
                        break;
                    case "VR_VES_CHART":
                        limites = new LimiteGrafico { Min = 24.9, Max = 45, Normal = 25, Aumento = 40 };
                        break;
                    case "VR_SEPTO_CHART":
                        limites = new LimiteGrafico { Min = 6, Max = 20, Normal = 6, Leve = 11, Moderado = 14, Grave = 17 };
                        break;
                    case "VR_PPVE_CHART":
                        limites = new LimiteGrafico { Min = 6, Max = 20, Normal = 6, Leve = 11, Moderado = 14, Grave = 17 };
                        break;
                    case "VR_MVE_CHART":
                        limites = new LimiteGrafico { Min = 88, Max = 320, Normal = 88, Leve = 225, Moderado = 259, Grave = 293 };
                        break;
                    case "VR_MVE_SC_CHART":
                        limites = new LimiteGrafico { Min = 49, Max = 180, Normal = 49, Leve = 116, Moderado = 132, Grave = 149 };
                        break;
                    case "VR_MVE_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 41, Max = 180, Normal = 127, Leve = 127, Moderado = 145, Grave = 163 };
                        break;
                    case "VR_ERP_CHART":
                        limites = new LimiteGrafico { Min = 0.32, Max = 0.60, Normal = 0.32, Leve = 0.42, Moderado = 0.46, Grave = 0.51 };
                        break;
                    case "VR_VDF_BI_CHART":
                        limites = new LimiteGrafico { Min = 62, Max = 180, Normal = 62, Aumento = 150 };
                        break;
                    case "VR_VDF_BI_I_CHART":
                        limites = new LimiteGrafico { Min = 34, Max = 90, Normal = 34, Aumento = 74 };
                        break;
                    case "VR_VSF_BI_CHART":
                        limites = new LimiteGrafico { Min = 21, Max = 80, Normal = 21, Aumento = 61 };
                        break;
                    case "VR_VSF_BI_I_CHART":
                        limites = new LimiteGrafico { Min = 11, Max = 40, Normal = 11, Aumento = 31 };
                        break;
                    case "VR_VDF_CHART":
                        limites = new LimiteGrafico { Min = 67, Max = 200, Normal = 67, Aumento = 155 };
                        break;
                    case "VR_VDF_I_CHART":
                        limites = new LimiteGrafico { Min = 50, Max = 150, Normal = 50, Aumento = 100 };
                        break;
                    case "VR_VSF_CHART":
                        limites = new LimiteGrafico { Min = 25, Max = 100, Normal = 25, Aumento = 60 };
                        break;
                    case "VR_VSF_I_CHART":
                        limites = new LimiteGrafico { Min = 20, Max = 100, Normal = 20, Aumento = 40 };
                        break;
                    case "VR_FESIMPSON_MANUAL_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 55, Leve = 45, Moderado = 30, Grave = 30, Ascendente = true };
                        break;
                    case "VR_PEC_CHART":
                        limites = new LimiteGrafico { Min = 25, Max = 100, Normal = 25, Aumento = 43 };
                        break;
                    case "VR_SGL_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = -18, Aumento = -14 };
                        break;
                    case "VR_DPDTVE_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2000, Normal = 1200, Anormal = 2000 };
                        break;
                    case "VR_SLINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.15, Normal = 0, Aumento = 0.07 };
                        break;
                    case "VR_MAPS_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 20, Normal = 0, Aumento = 12 };
                        break;
                    case "VR_INDICEA_CHART":
                        limites = new LimiteGrafico { Min = 0.3, Max = 0.7, Normal = 0.5, Aumento = 0.7 };
                        break;
                    case "VR_INDICEE_CHART":
                        limites = new LimiteGrafico { Min = 0.6, Max = 1.4, Normal = 0.6, Aumento = 1 };
                        break;
                    case "VR_INDICEELINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.15, Normal = 0.07, Anormal = 0.1 };
                        break;
                    case "VR_INDICEELINHA_LAT_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.20, Normal = 0.10, Anormal = 0.1 };
                        break;
                    case "VR_REL_E_A_CHART":
                        limites = new LimiteGrafico { Min = 1, Max = 2.5, Normal = 1, Aumento = 2 };
                        break;
                    case "VR_MEDIA_E_ELINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 14, Normal = 0, Aumento = 14 };
                        break;
                    case "VR_REL_E_E_LINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 15, Normal = 0, Aumento = 15 };
                        break;
                    case "VR_ATRIODIREITOAREA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 30, Normal = 0, Aumento = 18 };
                        break;
                    case "VR_VAD_SC_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 60, Normal =0, Aumento = 39 };
                        break;
                    case "VR_VD_BT_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 41 };
                        break;
                    case "VR_VD_MEDIO_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 60, Normal = 0, Aumento = 35 };
                        break;
                    case "VR_VD_BASEAPICE_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 150, Normal = 0, Aumento = 83 };
                        break;
                    case "VR_A_PULMONAR_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 50, Normal = 0, Aumento = 26 };
                        break;
                    case "VR_EVD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2, Normal = 0, Aumento = 0.5 };
                        break;
                    case "VR_VCI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 30, Normal = 0, Aumento = 21 };
                        break;
                    case "VR_VATL_CHART":
                        limites = new LimiteGrafico { Min = 9.5, Max = 20, Normal = 9.5, Aumento = 15 };
                        break;
                    case "VR_GLSVD_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = 0, Aumento = -20 };
                        break;
                    case "VR_FWSVD_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = 0, Aumento = -23 };
                        break;
                    case "VR_DSATL_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 40, Normal = 17, Anormal = 35 };
                        break;
                    case "VR_DPDT_VD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 800, Normal = 0, Aumento = 400 };
                        break;
                    case "VR_FAC_VD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 35, Aumento = 100 };
                        break;
                    case "VR_V_VCI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 50 };
                        break;
                    case "VR_PSAP_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 40 };
                        break;
                    case "VR_DT_VSVD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 300, Normal = 0, Aumento = 50 };
                        break;
                    case "VR_VEL_INICIAL_REG_PULM_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2.2, Normal = 0, Aumento = 2.2 };
                        break;
                }
            }
            else if (sexo == Sexo.Feminino)
            {
                switch (nomeGrafico)
                {
                    case "VR_AO_CHART":
                        limites = new LimiteGrafico { Min = 21, Max = 57, Normal = 21, Leve = 26, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_ANEL_I_CHART":
                        limites = new LimiteGrafico { Min = 15, Max = 30, Normal = 15, Aumento = 24 };
                        break;
                    case "VR_AO_SV_CHART":
                        limites = new LimiteGrafico { Min = 31, Max = 57, Normal = 31, Leve = 38, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_SEIO_VALSALVA_I_CHART":
                        limites = new LimiteGrafico { Min = 1.5, Max = 3, Normal = 1.5, Aumento = 1.9 };
                        break;
                    case "VR_AO_JUNCAO_CHART":
                        limites = new LimiteGrafico { Min = 23, Max = 57, Normal = 22, Leve = 33, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_JUNCAO_I_CHART":
                        limites = new LimiteGrafico { Min = 13, Max = 25, Normal = 13, Aumento = 18 };
                        break;
                    case "VR_AO_ASC_PROX_CHART":
                        limites = new LimiteGrafico { Min = 23, Max = 57, Normal = 23, Leve = 36, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_AO_ASC_PROX_I_CHART":
                        limites = new LimiteGrafico { Min = 15, Max = 25, Normal = 15, Aumento = 18 };
                        break;
                    case "VR_ARCOAO_CHART":
                        limites = new LimiteGrafico { Min = 22, Max = 57, Normal = 22, Leve = 36, Moderado = 45, Grave = 53 };
                        break;
                    case "VR_SGL_AE_CHART":
                        limites = new LimiteGrafico { Min = -30, Max = 0, Normal = -24, Limitrofe = -18 };
                        break;
                    case "VR_AE_CHART":
                        limites = new LimiteGrafico { Min = 27, Max = 50, Normal = 27, Aumento = 38 };
                        break;
                    case "VR_AEI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 35, Normal = 23, Leve = 27, Moderado = 30, Grave = 35 };
                        break;
                    case "VR_AE_A4C_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 600, Normal = 201, Leve = 300, Moderado = 400, Grave = 600 };
                        break;
                    case "VR_AE_A2C_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 600, Normal = 210, Leve = 300, Moderado = 400, Grave = 600 };
                        break;
                    case "VR_VAE_SC_CHART":
                        limites = new LimiteGrafico { Min = 16, Max = 60, Normal = 16, Leve = 35, Moderado = 42, Grave = 48 };
                        break;
                    case "VR_VAE_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 50, Normal = 0, Aumento = 33.8 };
                        break;
                    case "VR_VAE_ALTURA2_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 48, Normal = 0, Aumento = 35 };
                        break;
                    case "VR_VSVE_CHART":
                        double preditivoCm = Math.Round(((5.7 * mSupCorp) + 12.1) / 10, 2);
                        double preditivoMm = Math.Round(preditivoCm * 10);
                        double minimo = Math.Round(preditivoMm - 20);
                        double maximo = Math.Round(preditivoMm + 20);

                        limites = new LimiteGrafico { Min = minimo, Max = maximo, Normal = minimo, Aumento = preditivoMm };
                        break;
                    case "VR_VED_CHART":
                        limites = new LimiteGrafico { Min = 38, Max = 65, Normal = 37.8, Aumento = 52.2 };
                        break;
                    case "VR_VEDI_CHART":
                        limites = new LimiteGrafico { Min = 2.5, Max = 4, Normal = 2.5, Leve = 3.3, Moderado = 3.5, Grave = 3.8 };
                        break;
                    case "VR_VED_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 2.4, Max = 4, Normal = 2.4, Leve = 3.3, Moderado = 3.5, Grave = 3.7 };
                        break;
                    case "VR_VES_CHART":
                        limites = new LimiteGrafico { Min = 21.6, Max = 45, Normal = 21.6, Aumento = 34.8 };
                        break;
                    case "VR_SEPTO_CHART":
                        limites = new LimiteGrafico { Min = 6, Max = 20, Normal = 6, Leve = 10, Moderado = 13, Grave = 16 };
                        break;
                    case "VR_PPVE_CHART":
                        limites = new LimiteGrafico { Min = 6, Max = 20, Normal = 6, Leve = 10, Moderado = 13, Grave = 16 };
                        break;
                    case "VR_MVE_CHART":
                        limites = new LimiteGrafico { Min = 67, Max = 250, Normal = 67, Leve = 163, Moderado = 187, Grave = 211 };
                        break;
                    case "VR_MVE_SC_CHART":
                        limites = new LimiteGrafico { Min = 43, Max = 160, Normal = 43, Leve = 96, Moderado = 109, Grave = 122 };
                        break;
                    case "VR_MVE_ALTURA_CHART":
                        limites = new LimiteGrafico { Min = 41, Max = 150, Normal = 100, Leve = 100, Moderado = 116, Grave = 129 };
                        break;
                    case "VR_ERP_CHART":
                        limites = new LimiteGrafico { Min = 0.32, Max = 0.60, Normal = 0.32, Leve = 0.42, Moderado = 0.47, Grave = 0.52 };
                        break;
                    case "VR_VDF_BI_CHART":
                        limites = new LimiteGrafico { Min = 46, Max = 150, Normal = 46, Aumento = 106 };
                        break;
                    case "VR_VDF_BI_I_CHART":
                        limites = new LimiteGrafico { Min = 29, Max = 80, Normal = 29, Aumento = 61 };
                        break;
                    case "VR_VSF_BI_CHART":
                        limites = new LimiteGrafico { Min = 14, Max = 60, Normal = 14, Aumento = 42 };
                        break;
                    case "VR_VSF_BI_I_CHART":
                        limites = new LimiteGrafico { Min = 8, Max = 35, Normal = 8, Aumento = 24 };
                        break;
                    case "VR_VDF_CHART":
                        limites = new LimiteGrafico { Min = 56, Max = 200, Normal = 56, Aumento = 104 };
                        break;
                    case "VR_VDF_I_CHART":
                        limites = new LimiteGrafico { Min = 45, Max = 150, Normal = 45, Aumento = 90 };
                        break;
                    case "VR_VSF_CHART":
                        limites = new LimiteGrafico { Min = 20, Max = 100, Normal = 20, Aumento = 50 };
                        break;
                    case "VR_VSF_I_CHART":
                        limites = new LimiteGrafico { Min = 18, Max = 100, Normal = 18, Aumento = 35 };
                        break;
                    case "VR_FESIMPSON_MANUAL_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 55, Leve = 45, Moderado = 30, Grave = 30, Ascendente = true };
                        break;
                    case "VR_PEC_CHART":
                        limites = new LimiteGrafico { Min = 25, Max = 100, Normal = 25, Aumento = 43 };
                        break;
                    case "VR_SGL_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = -18, Aumento = -14 };
                        break;
                    case "VR_DPDTVE_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2000, Normal = 1200, Anormal = 2000 };
                        break;
                    case "VR_SLINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.15, Normal = 0, Aumento = 0.07 };
                        break;
                    case "VR_MAPS_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 20, Normal = 0, Aumento = 12 };
                        break;
                    case "VR_INDICEA_CHART":
                        limites = new LimiteGrafico { Min = 0.3, Max = 0.7, Normal = 0.5, Aumento = 0.7 };
                        break;
                    case "VR_INDICEE_CHART":
                        limites = new LimiteGrafico { Min = 0.6, Max = 1.4, Normal = 0.6, Aumento = 1 };
                        break;
                    case "VR_INDICEELINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.15, Normal = 0.07, Anormal = 0.1 };
                        break;
                    case "VR_INDICEELINHA_LAT_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 0.20, Normal = 0.10, Anormal = 0.1 };
                        break;
                    case "VR_REL_E_A_CHART":
                        limites = new LimiteGrafico { Min = 1, Max = 2.5, Normal = 1, Aumento = 2 };
                        break;
                    case "VR_MEDIA_E_ELINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 14, Normal = 0, Aumento = 14 };
                        break;
                    case "VR_REL_E_E_LINHA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 15, Normal = 0, Aumento = 15 };
                        break;
                    case "VR_ATRIODIREITOAREA_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 30, Normal = 0, Aumento = 18 };
                        break;
                    case "VR_VAD_SC_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 60, Normal = 0, Aumento = 33 };
                        break;
                    case "VR_VD_BT_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 41 };
                        break;
                    case "VR_VD_MEDIO_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 60, Normal = 0, Aumento = 35 };
                        break;
                    case "VR_VD_BASEAPICE_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 150, Normal = 0, Aumento = 83 };
                        break;
                    case "VR_A_PULMONAR_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 50, Normal = 0, Aumento = 26 };
                        break;
                    case "VR_EVD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2, Normal = 0, Aumento = 0.5 };
                        break;
                    case "VR_VCI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 30, Normal = 0, Aumento = 21 };
                        break;
                    case "VR_VATL_CHART":
                        limites = new LimiteGrafico { Min = 9.5, Max = 20, Normal = 9.5, Aumento = 15 };
                        break;
                    case "VR_GLSVD_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = 0, Aumento = -20 };
                        break;
                    case "VR_FWSVD_CHART":
                        limites = new LimiteGrafico { Min = -100, Max = 0, Normal = 0, Aumento = -23 };
                        break;
                    case "VR_DSATL_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 40, Normal = 17, Anormal = 35 };
                        break;
                    case "VR_DPDT_VD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 800, Normal = 0, Aumento = 400 };
                        break;
                    case "VR_FAC_VD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 35, Aumento = 100 };
                        break;
                    case "VR_V_VCI_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 50 };
                        break;
                    case "VR_PSAP_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 100, Normal = 0, Aumento = 40 };
                        break;
                    case "VR_DT_VSVD_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 300, Normal = 0, Aumento = 50 };
                        break;
                    case "VR_VEL_INICIAL_REG_PULM_CHART":
                        limites = new LimiteGrafico { Min = 0, Max = 2.2, Normal = 0, Aumento = 2.2 };
                        break;
                }
            }

            return limites;
        }
        private string RetornaDescricaoNormalidade(double valor, LimiteGrafico limites)
        {
            string retorno = string.Empty;

            if (limites.Aumento != 0)
            {
                if (valor < limites.Min)
                {
                    retorno = "Fora da faixa";
                }
                else if (valor >= limites.Normal && valor < limites.Aumento)
                {
                    retorno = "Normal";
                }
                else
                {
                    retorno = "Aumento";
                }
            }
            else if (limites.Limitrofe != 0)
            {
                if (valor >= limites.Min && valor <= limites.Normal)
                {
                    retorno = "Normal";
                }
                else if (valor >= limites.Normal && valor < limites.Limitrofe)
                {
                    retorno = "Limítrofe";
                }
                else
                {
                    retorno = "Anormal";
                }
            }
            else if (limites.Anormal != 0)
            {
                if (valor <= limites.Normal)
                {
                    retorno = "Anormal";
                }
                else
                {
                    retorno = "Normal";
                }
            }
            else if (limites.Ascendente)
            {
                if (valor < limites.Min)
                {
                    retorno = "Fora da faixa";
                }
                else if (valor >= limites.Normal && valor <= limites.Max)
                {
                    retorno = "Normal";
                }
                else if (valor >= limites.Leve && valor < limites.Normal)
                {
                    retorno = "Leve";
                }
                else if (valor >= limites.Moderado && valor < limites.Leve)
                {
                    retorno = "Moderado";
                }
                else if (valor >= limites.Grave && valor < limites.Moderado || valor < limites.Grave && valor > limites.Min)
                {
                    retorno = "Grave";
                }
                else
                {
                    retorno = "Fora da faixa";
                }

            }
            else
            {
                if (valor < limites.Min)
                {
                    retorno = "Fora da faixa";
                }
                else if (valor >= limites.Min && valor < limites.Leve)
                {
                    retorno = "Normal";
                }
                else if (valor >= limites.Leve && valor < limites.Moderado)
                {
                    retorno = "Leve";
                }
                else if (valor >= limites.Moderado && valor < limites.Grave)
                {
                    retorno = "Moderado";
                }
                else if (valor > limites.Grave)
                {
                    retorno = "Grave";
                }
            }

            return retorno;
        }
        public void RetornaGraficoNormalidade(Chart grafico, double valor, string normalidade, double min, double max, double normal, double leve = 0, double moderado = 0, double grave = 0, double aumento = 0, double intervalo = 1)
        {
            try
            {
                grafico.Series.Clear();
                grafico.ChartAreas[0].AxisX.CustomLabels.Clear();
                grafico.ChartAreas[0].AxisX.StripLines.Clear();

                if (valor != 0)
                {
                    toolTipDescricao.SetToolTip(grafico, normalidade);

                    Series series = grafico.Series.Add("Normalidade");
                    series.ChartType = SeriesChartType.FastPoint;
                    series.MarkerSize = 9;
                    series.MarkerStyle = MarkerStyle.Circle;

                    series.Color = DeterminarCorNormalidade(normalidade);
                    series.Name = normalidade;

                    grafico.ChartAreas[0].AxisX.LabelStyle.Font = new Font("Tahoma", 7, FontStyle.Regular);
                    grafico.ChartAreas[0].BackColor = SystemColors.Window;

                    // Configure os limites dos eixos X e Y
                    ConfigurarEixos(grafico, min, max, intervalo);

                    // Adicione rótulos personalizados para os valores específicos
                    AdicionarRotulosCustomizados(grafico, min, normal, leve, moderado, grave, aumento, max);

                    // Adicione o ponto ao gráfico com base no valor
                    series.Points.Clear();
                    series.Points.AddXY(valor, 0);
                }
                else
                {
                    grafico.Series.Clear();
                    grafico.ChartAreas[0].AxisX.CustomLabels.Clear();
                }
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private Color DeterminarCorNormalidade(string normalidade)
        {
            if (normalidade == "Fora da faixa")
                return Color.Blue;
            else if (normalidade == "Grave")
                return Color.Red;
            else if (normalidade == "Leve")
                return Color.FromArgb(247, 212, 1); //amarelo;
            else if (normalidade == "Moderado")
                return Color.Orange;
            else if (normalidade == "Normal")
                return Color.Green;
            else if (normalidade == "Limítrofe")
                return Color.YellowGreen;
            else
                return Color.Red;
        }
        private void ConfigurarEixos(Chart grafico, double min, double max, double intervalo)
        {
            grafico.ChartAreas[0].AxisX.Minimum = min;
            grafico.ChartAreas[0].AxisX.Maximum = max;
            grafico.ChartAreas[0].AxisX.Interval = intervalo;

            // Defina a cor das linhas de grade principal e dos eixos
            grafico.ChartAreas[0].AxisX.MajorGrid.LineColor = Color.Transparent;
            grafico.ChartAreas[0].AxisY.LineColor = Color.Transparent;
            grafico.ChartAreas[0].AxisX.LineColor = mCorGrid;
            grafico.ChartAreas[0].AxisX.LineWidth = 1;
        }
        private void AdicionarRotulosCustomizados(Chart grafico, double min, double normal, double leve, double moderado, double grave, double aumento, double max)
        {
            labelCustom(grafico.ChartAreas[0].AxisX, min, min.ToString());

            if (min != normal)
            {
                labelCustom(grafico.ChartAreas[0].AxisX, normal, normal.ToString());
            }

            if (leve != 0) labelCustom(grafico.ChartAreas[0].AxisX, leve, leve.ToString());
            if (moderado != 0) labelCustom(grafico.ChartAreas[0].AxisX, moderado, moderado.ToString());
            if (aumento != 0) labelCustom(grafico.ChartAreas[0].AxisX, aumento, aumento.ToString());
            if (grave != 0) labelCustom(grafico.ChartAreas[0].AxisX, grave, grave.ToString());

            labelCustom(grafico.ChartAreas[0].AxisX, max, max.ToString());

        }
        public void labelCustom(Axis axis, double valor, string texto)
        {
            try
            {
                CustomLabel customLabel = new CustomLabel
                {
                    FromPosition = valor - 5000,
                    ToPosition = valor + 5000,
                    Text = texto,
                    ForeColor = Color.FromArgb(48, 48, 48)
                };

                axis.CustomLabels.Add(customLabel);
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        #endregion
        #endregion
        #region eventos
        private void AnaliseSegmentar_IndexChanged(object sender, EventArgs e)
        {
            try
            {

                if (((ComboBox)sender).Parent.Text == tbpAnaliseSegmentarRepouso.Text)
                {
                    PintarImgAnaliseSegmentar(sender as Control, VR_DESENHOSEGMENTOS);
                }
                else
                {
                    PintarImgAnaliseSegmentar(sender as Control, VR_DESENHOSEGMENTOSTRESS);
                }
                EscoreParedes();
            }
            catch (Exception ex)
            {
                LogDeErroClinicas.GerarLog(ex);
            }
        }
        private void EcodopplercardiogramaModelo02_Load(object sender, EventArgs e)
        {
            //mPeso = 80;
            //mAltura = 175;
            //mSexo = "Feminino";

            RetornaIconeGeneroPaciente();
            CalculaImc();
            SuperficieCorporal();
            PintarHipertrifia();
            AdicionarAgrupadoresImpressao();
        }
        private void Parametro_TextChanged(object sender, EventArgs e)
        {
            RetornaNormalidades(((TextBox)sender));
        }
        private void SomenteNumeros_KeyPress(object sender, KeyPressEventArgs e)
        {
            ((TextBox)sender).AceitaSomenteNumeros(e, true);
        }
        private void NormalHipoDifusa(object sender, EventArgs e)
        {
            string btn = ((Button)sender).Name;
            Color cor;

            int index;
            PictureBox desenho;

            switch (btn)
            {
                case "btnNormalASR":
                    index = 1;
                    desenho = VR_DESENHOSEGMENTOS;
                    cor = mCorNormal;
                    break;
                case "btnHipoDifusaASR":
                    index = 2;
                    desenho = VR_DESENHOSEGMENTOS;
                    cor = mCorHipoDifusa;
                    break;
                case "btnNormalASS":
                    index = 1;
                    desenho = VR_DESENHOSEGMENTOSTRESS;
                    cor = mCorNormal;
                    break;
                case "btnHipoDifusaASS":
                    index = 2;
                    desenho = VR_DESENHOSEGMENTOSTRESS;
                    cor = mCorHipoDifusa;
                    break;
                default:
                    index = 0;
                    desenho = null;
                    cor = Color.Transparent;
                    break;
            }

            VR_DESENHOSEGMENTOSBOLOTAS.Image = VR_DESENHOSEGMENTOS.Image;
            PintarSegmentos(cor, index, desenho, tbpAnaliseSegmentarStress);
            MontarImpressaoImageStress();
            EscoreParedes();
        }
        private void Grafico_MouseEnter(object sender, EventArgs e)
        {
            //((Chart)sender).Legends["legendaNormalidade"].Enabled = true;
        }
        private void Grafico_MouseLeave(object sender, EventArgs e)
        {
            //((Chart)sender).Legends["legendaNormalidade"].Enabled = false;
        }
        private void VR_INSPIRACAO_SelectedIndexChanged(object sender, EventArgs e)
        {
            PressaoArterialDiastolica();
        }
        private void VR_VAE_MANUAL_CHECK_CheckedChanged(object sender, EventArgs e)
        {
            bool somenteLeitura = !((CheckBox)sender).Checked;
            VR_VAE.ReadOnly = somenteLeitura;
            VR_VAE_MANUAL_CHECK.ImageIndex = somenteLeitura ? 0 : 1;

            VR_VAE.BackColor = somenteLeitura ? SystemColors.Control : SystemColors.Window;

            if (!somenteLeitura)
            {
                VR_VAE.Focus();
            }
            else
            {
                VR_VAE.Text = String.Empty;
                VolumeAtrioEsquerdo();
            }
        }
        private void Referencias_Click(object sender, EventArgs e)
        {
            string descricao = ((Button)sender).Name;

            if (ExisteReferencia($"{descricao}.pdf") == 0)
            {
                this.DownloadReferencia($"{descricao}.pdf");
            }

            Referencia(descricao);
        }
        #endregion
    }
}
public enum Index
{
    SuperfCorp,
    Altura,
    Altura2
}
public enum Sexo
{
    Masculino,
    Feminino,
    Indefinido
}
public enum VolumeVe
{
    Sistolico,
    Diastolico
}

public enum FracaoEjecao
{
    TeichHolz,
    Simpson
}

public enum Relacao
{
    Ea,
    Ee,
    mediaEe
}
