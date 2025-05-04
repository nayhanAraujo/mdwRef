using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

class Program
{
    static void Main(string[] args)
    {
        try
        {
            if (args.Length != 1)
            {
                Console.Error.WriteLine("Uso: ParseCSFile.exe <caminho_do_arquivo_cs>");
                OutputErrorResult("Uso: ParseCSFile.exe <caminho_do_arquivo_cs>");
                return;
            }

            string filePath = args[0];
            if (!File.Exists(filePath))
            {
                Console.Error.WriteLine($"Arquivo não encontrado: {filePath}");
                OutputErrorResult($"Arquivo não encontrado: {filePath}");
                return;
            }

            string code = File.ReadAllText(filePath, System.Text.Encoding.UTF8);
            var result = ParseFile(code);
            string jsonResult = JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
            Console.WriteLine(jsonResult);
            Console.Out.Flush();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Erro ao processar o arquivo: {ex.Message}");
            OutputErrorResult($"Erro ao processar o arquivo: {ex.Message}");
        }
    }

    static void OutputErrorResult(string errorMessage)
    {
        var errorResult = new Dictionary<string, object>
        {
            ["variaveis"] = new List<Dictionary<string, string>>(),
            ["formulas"] = new List<Dictionary<string, object>>(),
            ["normalidades"] = new List<Dictionary<string, object>>(),
            ["error"] = errorMessage
        };
        string jsonResult = JsonSerializer.Serialize(errorResult, new JsonSerializerOptions { WriteIndented = true });
        Console.WriteLine(jsonResult);
        Console.Out.Flush();
    }

    static Dictionary<string, object> ParseFile(string code)
    {
        var tree = CSharpSyntaxTree.ParseText(code);
        var root = tree.GetRoot();

        var result = new Dictionary<string, object>
        {
            ["variaveis"] = new List<Dictionary<string, string>>(),
            ["formulas"] = new List<Dictionary<string, object>>(),
            ["normalidades"] = new List<Dictionary<string, object>>()
        };

        var variaveisEncontradas = new HashSet<string>();

        // 1. Extrair variáveis de dicionários (como mapeamentoCampos)
        var dictionaries = root.DescendantNodes()
            .OfType<InitializerExpressionSyntax>()
            .Where(init => init.Parent is EqualsValueClauseSyntax && init.Expressions.Any());

        Console.Error.WriteLine($"Dicionários encontrados: {dictionaries.Count()}");
        foreach (var dict in dictionaries)
        {
            foreach (var expr in dict.Expressions.OfType<InitializerExpressionSyntax>())
            {
                var key = expr.Expressions.FirstOrDefault()?.ToString().Trim('"');
                if (key != null && key.StartsWith("VR_") && !key.Contains("CHART") && !variaveisEncontradas.Contains(key))
                {
                    Console.Error.WriteLine($"Variável encontrada em dicionário: {key}");
                    variaveisEncontradas.Add(key);
                    ((List<Dictionary<string, string>>)result["variaveis"]).Add(new Dictionary<string, string>
                    {
                        ["codigo"] = key,
                        ["nome"] = key.Replace("VR_", "").Replace("_", " ").ToLower(),
                        ["sigla"] = key.Replace("VR_", ""),
                        ["abreviacao"] = key.Replace("VR_", ""),
                        ["unidade"] = "unknown"
                    });
                }
            }
        }

        // 2. Extrair variáveis de propriedades ou campos de classe
        var fieldsAndProperties = root.DescendantNodes()
            .OfType<MemberDeclarationSyntax>()
            .Where(m => m is PropertyDeclarationSyntax || m is FieldDeclarationSyntax);

        Console.Error.WriteLine($"Propriedades/Campos encontrados: {fieldsAndProperties.Count()}");
        foreach (var member in fieldsAndProperties)
        {
            string name = null;
            if (member is PropertyDeclarationSyntax prop)
                name = prop.Identifier.Text;
            else if (member is FieldDeclarationSyntax field)
                name = field.Declaration.Variables.FirstOrDefault()?.Identifier.Text;

            if (name != null && name.StartsWith("VR_") && !name.Contains("CHART") && !variaveisEncontradas.Contains(name))
            {
                Console.Error.WriteLine($"Variável encontrada em propriedade/campo: {name}");
                variaveisEncontradas.Add(name);
                ((List<Dictionary<string, string>>)result["variaveis"]).Add(new Dictionary<string, string>
                {
                    ["codigo"] = name,
                    ["nome"] = name.Replace("VR_", "").Replace("_", " ").ToLower(),
                    ["sigla"] = name.Replace("VR_", ""),
                    ["abreviacao"] = name.Replace("VR_", ""),
                    ["unidade"] = "unknown"
                });
            }
        }

        // 3. Extrair variáveis de strings literais (ex.: em comparações ou switch statements)
        var stringLiterals = root.DescendantNodes()
            .OfType<LiteralExpressionSyntax>()
            .Where(l => l.Token.Value is string && ((string)l.Token.Value).StartsWith("VR_") && ((string)l.Token.Value).EndsWith(".Text"));

        Console.Error.WriteLine($"Strings literais terminadas em .Text encontradas: {stringLiterals.Count()}");
        foreach (var literal in stringLiterals)
        {
            var value = literal.Token.Value as string;
            if (value != null && value.StartsWith("VR_") && value.EndsWith(".Text") && !value.Contains("CHART"))
            {
                string variavel = value.Substring(0, value.Length - ".Text".Length);
                if (!variaveisEncontradas.Contains(variavel))
                {
                    Console.Error.WriteLine($"Variável encontrada em string literal: {variavel}");
                    variaveisEncontradas.Add(variavel);
                    ((List<Dictionary<string, string>>)result["variaveis"]).Add(new Dictionary<string, string>
                    {
                        ["codigo"] = variavel,
                        ["nome"] = variavel.Replace("VR_", "").Replace("_", " ").ToLower(),
                        ["sigla"] = variavel.Replace("VR_", ""),
                        ["abreviacao"] = variavel.Replace("VR_", ""),
                        ["unidade"] = "unknown"
                    });
                }
            }
        }

        // 4. Extrair variáveis de expressões do tipo VR_*.Text (ex.: VR_VAE.Text)
        var memberAccessExpressions = root.DescendantNodes()
            .OfType<MemberAccessExpressionSyntax>()
            .Where(m => m.Name.Identifier.Text == "Text" && m.Expression is IdentifierNameSyntax id && id.Identifier.Text.StartsWith("VR_"));

        Console.Error.WriteLine($"Expressões VR_*.Text encontradas: {memberAccessExpressions.Count()}");
        foreach (var memberAccess in memberAccessExpressions)
        {
            var identifier = ((IdentifierNameSyntax)memberAccess.Expression).Identifier.Text;
            if (identifier.StartsWith("VR_") && !identifier.Contains("CHART") && !variaveisEncontradas.Contains(identifier))
            {
                Console.Error.WriteLine($"Variável encontrada em VR_*.Text: {identifier}");
                variaveisEncontradas.Add(identifier);
                ((List<Dictionary<string, string>>)result["variaveis"]).Add(new Dictionary<string, string>
                {
                    ["codigo"] = identifier,
                    ["nome"] = identifier.Replace("VR_", "").Replace("_", " ").ToLower(),
                    ["sigla"] = identifier.Replace("VR_", ""),
                    ["abreviacao"] = identifier.Replace("VR_", ""),
                    ["unidade"] = "unknown"
                });
            }
        }

        // Extrair fórmulas (procurar métodos com expressões matemáticas)
        var methods = root.DescendantNodes().OfType<MethodDeclarationSyntax>();
        foreach (var method in methods)
        {
            var methodName = method.Identifier.Text;
            var returnStatements = method.DescendantNodes().OfType<ReturnStatementSyntax>();
            foreach (var ret in returnStatements)
            {
                if (ret.Expression != null)
                {
                    var formula = ret.Expression.ToString();
                    var variavel = "VR_" + methodName.Replace("Calcular", "").ToUpper();
                    if (!variavel.Contains("CHART"))
                    {
                        ((List<Dictionary<string, object>>)result["formulas"]).Add(new Dictionary<string, object>
                        {
                            ["variavel"] = variavel,
                            ["expressao"] = formula,
                            ["casas_decimais"] = 1
                        });
                    }
                }
            }
        }

        // Extrair normalidades (procurar métodos como ObterLimitesGrafico)
        foreach (var method in methods.Where(m => m.Identifier.Text.Contains("ObterLimites")))
        {
            var switchStatements = method.DescendantNodes().OfType<SwitchStatementSyntax>();
            foreach (var switchStmt in switchStatements)
            {
                var sections = switchStmt.Sections;
                foreach (var section in sections)
                {
                    var label = section.Labels.FirstOrDefault()?.ToString().Trim('"');
                    if (label != null && label.EndsWith("_CHART"))
                    {
                        var variavel = label.Replace("_CHART", "");
                        // Ignorar variáveis com "CHART" (já filtrado pela lógica anterior, mas reforçando)
                        if (variavel.Contains("CHART")) continue;

                        var assignments = section.DescendantNodes().OfType<ObjectCreationExpressionSyntax>()
                            .Where(o => o.Type.ToString() == "LimiteGrafico");
                        foreach (var assign in assignments)
                        {
                            var initializer = assign.Initializer;
                            if (initializer != null)
                            {
                                float? min = null, max = null, normal = null;
                                foreach (var expr in initializer.Expressions.OfType<AssignmentExpressionSyntax>())
                                {
                                    var propertyName = expr.Left.ToString();
                                    var value = expr.Right.ToString();
                                    if (float.TryParse(value, out float floatValue))
                                    {
                                        if (propertyName == "Min") min = floatValue;
                                        if (propertyName == "Max") max = floatValue;
                                        if (propertyName == "Normal") normal = floatValue;
                                    }
                                }
                                if (min.HasValue && max.HasValue && normal.HasValue)
                                {
                                    ((List<Dictionary<string, object>>)result["normalidades"]).Add(new Dictionary<string, object>
                                    {
                                        ["variavel"] = variavel,
                                        ["sexo"] = method.ParameterList.Parameters.Any(p => p.Identifier.Text == "sexo") ? "M" : "F",
                                        ["valor_min"] = normal.Value,
                                        ["valor_max"] = max.Value,
                                        ["idade_min"] = 0,
                                        ["idade_max"] = 150,
                                        ["referencia"] = "Unknown"
                                    });
                                }
                            }
                        }
                    }
                }
            }
        }

        return result;
    }
}