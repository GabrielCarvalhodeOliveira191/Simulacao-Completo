
from flask import Flask, render_template, request, redirect, url_for
import math
import random
import fdb

app = Flask(__name__, template_folder="Templates", static_folder="static")
app.secret_key = "credmais_chave_local"

host = "localhost"
database = r"C:\Users\Aluno\Downloads\Cred-mais-lindo-pft-main\Cred-mais-lindo-pft-main\BANCO.FDB"
usuario = "SYSDBA"
senha = "sysdba"

LIMITE_ALTO_RISCO = 2.0


def conectar_banco():
    return fdb.connect(
        host=host,
        database=database,
        user=usuario,
        password=senha,
        charset="UTF8"
    )


def buscar_taxa():
    conexao = conectar_banco()

    try:
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT DATA_REFERENCIA, TAXA_MENSAL
            FROM TAXA_JUROS
            WHERE TAXA_MENSAL >= 0
        """)

        registros = cursor.fetchall()

        if not registros:
            return None

        registro = random.choice(registros)

        data_referencia = registro[0]
        taxa_mensal = float(registro[1])

        return {
            "ano": data_referencia.year,
            "juros_mensal": taxa_mensal
        }

    finally:
        conexao.close()


def formatar_reais(valor):
    return (
        f"{valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_numero(valor):
    return f"{valor:.2f}".replace(".", ",")


@app.route("/")
def inicio():
    return redirect(url_for("simulacao"))


@app.route("/simulacao", methods=["GET", "POST"])
def simulacao():
    resultado = None
    taxa = None
    erro = None

    if request.method == "POST":
        try:
            valor_texto = request.form.get("valor", "").strip()
            parcelas_texto = request.form.get("parcelas", "").strip()

            valor_texto = (
                valor_texto
                .replace("R$", "")
                .replace(" ", "")
            )

            if "," in valor_texto:
                valor_texto = (
                    valor_texto
                    .replace(".", "")
                    .replace(",", ".")
                )

            valor = float(valor_texto)
            quantidade = int(parcelas_texto)

            if not math.isfinite(valor) or valor <= 0:
                raise ValueError

            if quantidade < 1 or quantidade > 600:
                raise ValueError

        except (ValueError, TypeError, OverflowError):
            erro = (
                "Informe um valor válido e uma quantidade "
                "de parcelas entre 1 e 600."
            )

    if erro is None:
        try:
            taxa = buscar_taxa()
        except Exception:
            app.logger.exception(
                "Erro ao consultar a tabela TAXA_JUROS."
            )
            erro = "Não foi possível consultar as taxas no banco de dados."

    if request.method == "POST" and erro is None:
        if taxa is None:
            erro = "Nenhuma taxa foi cadastrada no banco de dados."

        else:
            try:
                juros_mensal = taxa["juros_mensal"] / 100

                if not math.isfinite(juros_mensal) or juros_mensal < 0:
                    erro = "A taxa cadastrada é inválida."

                else:
                    if juros_mensal == 0:
                        valor_parcela = valor / quantidade
                    else:
                        valor_parcela = (
                            valor * juros_mensal
                            / (
                                1 - (1 + juros_mensal) ** (-quantidade)
                            )
                        )

                    total = valor_parcela * quantidade
                    total_juros = total - valor

                    alto_risco = (
                        taxa["juros_mensal"] >= LIMITE_ALTO_RISCO
                    )

                    resultado = {
                        "valor": formatar_reais(valor),
                        "parcelas": quantidade,
                        "juros": formatar_numero(
                            taxa["juros_mensal"]
                        ),
                        "valor_parcela": formatar_reais(
                            valor_parcela
                        ),
                        "total": formatar_reais(total),
                        "total_juros": formatar_reais(total_juros),
                        "ano": taxa["ano"],
                        "alto_risco": alto_risco,
                        "risco": "Alto" if alto_risco else "Baixo"
                    }

            except (ValueError, TypeError, OverflowError):
                erro = "Não foi possível calcular a simulação com essa taxa."

    if resultado is not None:
        return render_template(
            "resultado_simulacao.html",
            resultado=resultado,
            taxa=taxa,
            erro=None
        )

    return render_template(
        "simulacao.html",
        resultado=None,
        taxa=taxa,
        erro=erro
    )


if __name__ == "__main__":
    app.run(debug=True)
