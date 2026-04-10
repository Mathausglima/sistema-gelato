import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

DB_PATH = Path("gelato_custos.db")

# =========================
# BANCO DE DADOS
# =========================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ingredientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            preco_kg REAL NOT NULL DEFAULT 0,
            unidade_compra TEXT NOT NULL DEFAULT 'kg',
            observacao TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS receitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            rendimento_final_kg REAL NOT NULL DEFAULT 0,
            peso_cuba_kg REAL DEFAULT 4.5,
            bolas_por_kg REAL DEFAULT 14,
            perdas_percentual REAL DEFAULT 0,
            embalagem_custo REAL DEFAULT 0,
            mao_obra_custo REAL DEFAULT 0,
            energia_custo REAL DEFAULT 0,
            outros_custos REAL DEFAULT 0,
            observacao TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS receita_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receita_id INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            quantidade_g REAL NOT NULL,
            FOREIGN KEY (receita_id) REFERENCES receitas(id),
            FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id),
            UNIQUE(receita_id, ingrediente_id)
        )
        """
    )

    conn.commit()
    conn.close()


# =========================
# INGREDIENTES
# =========================

def inserir_ingrediente(nome, preco_kg, unidade_compra, observacao):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ingredientes (nome, preco_kg, unidade_compra, observacao) VALUES (?, ?, ?, ?)",
        (nome.strip(), preco_kg, unidade_compra, observacao.strip()),
    )
    conn.commit()
    conn.close()


def listar_ingredientes():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, nome, preco_kg, unidade_compra, observacao FROM ingredientes ORDER BY nome",
        conn,
    )
    conn.close()
    return df


def excluir_ingrediente(ingrediente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ingredientes WHERE id = ?", (ingrediente_id,))
    conn.commit()
    conn.close()


# =========================
# RECEITAS
# =========================

def inserir_receita(nome, rendimento_final_kg, peso_cuba_kg, bolas_por_kg, perdas_percentual,
                    embalagem_custo, mao_obra_custo, energia_custo, outros_custos, observacao):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO receitas (
            nome, rendimento_final_kg, peso_cuba_kg, bolas_por_kg, perdas_percentual,
            embalagem_custo, mao_obra_custo, energia_custo, outros_custos, observacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            nome.strip(), rendimento_final_kg, peso_cuba_kg, bolas_por_kg, perdas_percentual,
            embalagem_custo, mao_obra_custo, energia_custo, outros_custos, observacao.strip()
        ),
    )
    conn.commit()
    conn.close()


def listar_receitas():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM receitas ORDER BY nome",
        conn,
    )
    conn.close()
    return df


def excluir_receita(receita_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM receita_itens WHERE receita_id = ?", (receita_id,))
    cur.execute("DELETE FROM receitas WHERE id = ?", (receita_id,))
    conn.commit()
    conn.close()


def adicionar_item_receita(receita_id, ingrediente_id, quantidade_g):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO receita_itens (receita_id, ingrediente_id, quantidade_g)
        VALUES (?, ?, ?)
        ON CONFLICT(receita_id, ingrediente_id)
        DO UPDATE SET quantidade_g = excluded.quantidade_g
        """,
        (receita_id, ingrediente_id, quantidade_g),
    )
    conn.commit()
    conn.close()


def remover_item_receita(item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM receita_itens WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def listar_itens_receita(receita_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            ri.id,
            ri.receita_id,
            ri.ingrediente_id,
            i.nome AS ingrediente,
            i.preco_kg,
            ri.quantidade_g,
            (ri.quantidade_g / 1000.0) * i.preco_kg AS custo_ingrediente
        FROM receita_itens ri
        JOIN ingredientes i ON i.id = ri.ingrediente_id
        WHERE ri.receita_id = ?
        ORDER BY i.nome
        """,
        conn,
        params=(receita_id,),
    )
    conn.close()
    return df


def buscar_receita_por_id(receita_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM receitas WHERE id = ?", (receita_id,))
    row = cur.fetchone()
    conn.close()
    return row


# =========================
# CÁLCULOS
# =========================

def calcular_custos_receita(receita_id):
    receita = buscar_receita_por_id(receita_id)
    itens = listar_itens_receita(receita_id)

    if receita is None:
        return None

    custo_ingredientes = float(itens["custo_ingrediente"].sum()) if not itens.empty else 0.0

    perdas_percentual = float(receita["perdas_percentual"] or 0)
    embalagem_custo = float(receita["embalagem_custo"] or 0)
    mao_obra_custo = float(receita["mao_obra_custo"] or 0)
    energia_custo = float(receita["energia_custo"] or 0)
    outros_custos = float(receita["outros_custos"] or 0)
    rendimento_final_kg = float(receita["rendimento_final_kg"] or 0)
    peso_cuba_kg = float(receita["peso_cuba_kg"] or 0)
    bolas_por_kg = float(receita["bolas_por_kg"] or 0)

    custo_perdas = custo_ingredientes * (perdas_percentual / 100)
    custo_total_receita = (
        custo_ingredientes + custo_perdas + embalagem_custo + mao_obra_custo + energia_custo + outros_custos
    )

    custo_por_kg = custo_total_receita / rendimento_final_kg if rendimento_final_kg > 0 else 0
    custo_por_cuba = custo_por_kg * peso_cuba_kg if peso_cuba_kg > 0 else 0
    custo_por_bola = custo_por_kg / bolas_por_kg if bolas_por_kg > 0 else 0
    cubas_por_receita = rendimento_final_kg / peso_cuba_kg if peso_cuba_kg > 0 else 0
    bolas_totais_receita = rendimento_final_kg * bolas_por_kg if bolas_por_kg > 0 else 0

    return {
        "receita": receita,
        "itens": itens,
        "custo_ingredientes": custo_ingredientes,
        "custo_perdas": custo_perdas,
        "embalagem_custo": embalagem_custo,
        "mao_obra_custo": mao_obra_custo,
        "energia_custo": energia_custo,
        "outros_custos": outros_custos,
        "custo_total_receita": custo_total_receita,
        "custo_por_kg": custo_por_kg,
        "custo_por_cuba": custo_por_cuba,
        "custo_por_bola": custo_por_bola,
        "cubas_por_receita": cubas_por_receita,
        "bolas_totais_receita": bolas_totais_receita,
    }


def sugerir_preco(custo, multiplicador):
    return custo * multiplicador


# =========================
# INTERFACE
# =========================

def tela_ingredientes():
    st.subheader("Cadastro de ingredientes")

    with st.form("form_ingrediente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do ingrediente")
            preco_kg = st.number_input("Preço por kg (R$)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            unidade_compra = st.selectbox("Unidade de compra", ["kg", "litro", "unidade"])
            observacao = st.text_input("Observação")

        salvar = st.form_submit_button("Salvar ingrediente")
        if salvar:
            if not nome.strip():
                st.warning("Digite o nome do ingrediente.")
            else:
                try:
                    inserir_ingrediente(nome, preco_kg, unidade_compra, observacao)
                    st.success("Ingrediente salvo com sucesso.")
                except sqlite3.IntegrityError:
                    st.error("Já existe um ingrediente com esse nome.")

    df = listar_ingredientes()
    st.markdown("### Ingredientes cadastrados")
    if df.empty:
        st.info("Nenhum ingrediente cadastrado ainda.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### ✏️ Editar ingrediente")
        ingrediente_id = st.selectbox("Escolha o ingrediente para editar", df["id"].tolist())

        ingrediente = df[df["id"] == ingrediente_id].iloc[0]

        novo_nome = st.text_input("Novo nome", value=ingrediente["nome"])
        novo_preco = st.number_input("Novo preço por kg", value=float(ingrediente["preco_kg"]), step=0.01)
        nova_unidade = st.selectbox("Nova unidade", ["kg", "litro", "unidade"], index=["kg", "litro", "unidade"].index(ingrediente["unidade_compra"]))
        nova_obs = st.text_input("Nova observação", value=ingrediente["observacao"])

        if st.button("Salvar edição"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE ingredientes
                SET nome = ?, preco_kg = ?, unidade_compra = ?, observacao = ?
                WHERE id = ?
                """,
                (novo_nome, novo_preco, nova_unidade, nova_obs, int(ingrediente_id))
            )
            conn.commit()
            conn.close()
            st.success("Ingrediente atualizado com sucesso.")
            st.rerun()

        st.markdown("### 🗑️ Excluir ingrediente")
        excluir_id = st.selectbox("Escolha o ID para excluir", [""] + df["id"].tolist(), key="excluir_ingrediente")
        if st.button("Excluir ingrediente"):
            if excluir_id != "":
                excluir_ingrediente(int(excluir_id))
                st.success("Ingrediente excluído.")
                st.rerun()


def tela_receitas():
    st.subheader("Cadastro de receitas")

    with st.form("form_receita", clear_on_submit=True):
        nome = st.text_input("Nome da receita")
        col1, col2, col3 = st.columns(3)
        with col1:
            rendimento_final_kg = st.number_input("Rendimento final (kg)", min_value=0.0, step=0.01, format="%.2f")
            peso_cuba_kg = st.number_input("Peso da cuba (kg)", min_value=0.0, value=4.5, step=0.1, format="%.2f")
        with col2:
            bolas_por_kg = st.number_input("Bolas por kg", min_value=0.0, value=14.0, step=1.0, format="%.0f")
            perdas_percentual = st.number_input("Perdas (%)", min_value=0.0, value=0.0, step=0.5, format="%.2f")
        with col3:
            embalagem_custo = st.number_input("Custo embalagem (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
            mao_obra_custo = st.number_input("Custo mão de obra (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")

        col4, col5 = st.columns(2)
        with col4:
            energia_custo = st.number_input("Custo energia (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
        with col5:
            outros_custos = st.number_input("Outros custos (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f")

        observacao = st.text_input("Observação")

        salvar = st.form_submit_button("Salvar receita")
        if salvar:
            if not nome.strip():
                st.warning("Digite o nome da receita.")
            elif rendimento_final_kg <= 0:
                st.warning("Informe um rendimento final maior que zero.")
            else:
                try:
                    inserir_receita(
                        nome, rendimento_final_kg, peso_cuba_kg, bolas_por_kg, perdas_percentual,
                        embalagem_custo, mao_obra_custo, energia_custo, outros_custos, observacao
                    )
                    st.success("Receita salva com sucesso.")
                except sqlite3.IntegrityError:
                    st.error("Já existe uma receita com esse nome.")

    df = listar_receitas()
    st.markdown("### Receitas cadastradas")
    if df.empty:
        st.info("Nenhuma receita cadastrada ainda.")
    else:
        st.dataframe(df, use_container_width=True)

        ids = df["id"].tolist()
        excluir_id = st.selectbox("Escolha o ID da receita para excluir", [""] + ids, key="excluir_receita")
        if st.button("Excluir receita"):
            if excluir_id != "":
                excluir_receita(int(excluir_id))
                st.success("Receita excluída.")
                st.rerun()


def tela_composicao_receita():
    st.subheader("Montar receita com ingredientes")

    receitas_df = listar_receitas()
    ingredientes_df = listar_ingredientes()

    if receitas_df.empty:
        st.info("Cadastre pelo menos uma receita antes.")
        return

    if ingredientes_df.empty:
        st.info("Cadastre ingredientes antes de montar a receita.")
        return

    receita_nome = st.selectbox("Escolha a receita", receitas_df["nome"].tolist())
    receita_id = int(receitas_df.loc[receitas_df["nome"] == receita_nome, "id"].iloc[0])

    with st.form("form_item_receita", clear_on_submit=True):
        ingrediente_nome = st.selectbox("Ingrediente", ingredientes_df["nome"].tolist())
        quantidade_g = st.number_input("Quantidade em gramas", min_value=0.0, step=1.0, format="%.0f")
        salvar_item = st.form_submit_button("Adicionar / atualizar ingrediente na receita")

        if salvar_item:
            ingrediente_id = int(ingredientes_df.loc[ingredientes_df["nome"] == ingrediente_nome, "id"].iloc[0])
            adicionar_item_receita(receita_id, ingrediente_id, quantidade_g)
            st.success("Ingrediente adicionado/atualizado na receita.")

    itens_df = listar_itens_receita(receita_id)
    st.markdown("### Itens da receita")
    if itens_df.empty:
        st.info("Essa receita ainda não tem ingredientes.")
    else:
        st.dataframe(itens_df, use_container_width=True)

        item_ids = itens_df["id"].tolist()
        excluir_item_id = st.selectbox("Escolha o ID do item para remover", [""] + item_ids, key="excluir_item_receita")
        if st.button("Remover item da receita"):
            if excluir_item_id != "":
                remover_item_receita(int(excluir_item_id))
                st.success("Item removido.")
                st.rerun()


def tela_calculo():
    st.subheader("Cálculo completo da receita")

    receitas_df = listar_receitas()
    if receitas_df.empty:
        st.info("Cadastre uma receita primeiro.")
        return

    receita_nome = st.selectbox("Selecione a receita para calcular", receitas_df["nome"].tolist(), key="calculo_receita")
    receita_id = int(receitas_df.loc[receitas_df["nome"] == receita_nome, "id"].iloc[0])

    resultado = calcular_custos_receita(receita_id)
    if resultado is None:
        st.error("Não foi possível calcular a receita.")
        return

    itens_df = resultado["itens"]
    receita = resultado["receita"]

    st.markdown("### Ingredientes da receita")
    if itens_df.empty:
        st.warning("Essa receita não possui ingredientes cadastrados.")
        return

    st.dataframe(itens_df, use_container_width=True)

    st.markdown("### Resumo de custos")
    c1, c2, c3 = st.columns(3)
    c1.metric("Custo ingredientes", f"R$ {resultado['custo_ingredientes']:.2f}")
    c2.metric("Custo perdas", f"R$ {resultado['custo_perdas']:.2f}")
    c3.metric("Custo total receita", f"R$ {resultado['custo_total_receita']:.2f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Custo por kg", f"R$ {resultado['custo_por_kg']:.2f}")
    c5.metric("Custo por cuba", f"R$ {resultado['custo_por_cuba']:.2f}")
    c6.metric("Custo por bola", f"R$ {resultado['custo_por_bola']:.2f}")

    c7, c8, c9 = st.columns(3)
    c7.metric("Rendimento final", f"{float(receita['rendimento_final_kg']):.2f} kg")
    c8.metric("Cubas por receita", f"{resultado['cubas_por_receita']:.2f}")
    c9.metric("Bolas totais", f"{resultado['bolas_totais_receita']:.0f}")

    st.markdown("### Custos adicionais informados")
    adicionais = pd.DataFrame([
        {"Tipo": "Embalagem", "Valor (R$)": float(receita['embalagem_custo'] or 0)},
        {"Tipo": "Mão de obra", "Valor (R$)": float(receita['mao_obra_custo'] or 0)},
        {"Tipo": "Energia", "Valor (R$)": float(receita['energia_custo'] or 0)},
        {"Tipo": "Outros", "Valor (R$)": float(receita['outros_custos'] or 0)},
    ])
    st.dataframe(adicionais, use_container_width=True)

    st.markdown("### Simulador de preço de venda")
    multiplicador = st.number_input("Multiplicador", min_value=1.0, value=3.5, step=0.1, format="%.2f")
    preco_bola = sugerir_preco(resultado["custo_por_bola"], multiplicador)
    preco_kg = sugerir_preco(resultado["custo_por_kg"], multiplicador)
    preco_cuba = sugerir_preco(resultado["custo_por_cuba"], multiplicador)

    s1, s2, s3 = st.columns(3)
    s1.metric("Preço sugerido por bola", f"R$ {preco_bola:.2f}")
    s2.metric("Preço sugerido por kg", f"R$ {preco_kg:.2f}")
    s3.metric("Preço sugerido por cuba", f"R$ {preco_cuba:.2f}")

    margem_bola = preco_bola - resultado["custo_por_bola"]
    margem_kg = preco_kg - resultado["custo_por_kg"]
    margem_cuba = preco_cuba - resultado["custo_por_cuba"]

    st.markdown("### Margem bruta estimada")
    m1, m2, m3 = st.columns(3)
    m1.metric("Margem por bola", f"R$ {margem_bola:.2f}")
    m2.metric("Margem por kg", f"R$ {margem_kg:.2f}")
    m3.metric("Margem por cuba", f"R$ {margem_cuba:.2f}")


# =========================
# APP PRINCIPAL
# =========================

def main():
    st.set_page_config(page_title="Sistema de Custo do Gelato", layout="wide")
    init_db()

    st.title("Sistema de Custo Automático para Gelatos")
    st.caption("Cadastro de ingredientes, receitas e cálculo completo de custo")

    menu = st.sidebar.radio(
        "Menu",
        [
            "1. Ingredientes",
            "2. Receitas",
            "3. Montar Receita",
            "4. Calcular Custos",
        ]
    )

    if menu == "1. Ingredientes":
        tela_ingredientes()
    elif menu == "2. Receitas":
        tela_receitas()
    elif menu == "3. Montar Receita":
        tela_composicao_receita()
    elif menu == "4. Calcular Custos":
        tela_calculo()


if __name__ == "__main__":
    main()
