import datetime
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Control de Trading - Opciones Binarias",
    page_icon="📈",
    layout="wide",
)


def get_connection():
    conn = sqlite3.connect("trading_journal.db", check_same_thread=False)
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            saldo_inicial REAL,
            saldo_actual REAL,
            pct_meta REAL,
            pct_operacion REAL
        )
    """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id INTEGER,
            fecha TEXT,
            saldo_inicial REAL,
            meta_monto REAL,
            monto_operacion REAL,
            ganadas INTEGER,
            perdidas INTEGER,
            resultado_monto REAL,
            saldo_final REAL,
            FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
        )
    """
    )
    c.execute(
        "INSERT OR IGNORE INTO cuentas (id, nombre, saldo_inicial, saldo_actual, pct_meta, pct_operacion) VALUES (1, 'Cuenta Principal', 100.0, 100.0, 5.0, 3.0)"
    )
    c.execute(
        "INSERT OR IGNORE INTO cuentas (id, nombre, saldo_inicial, saldo_actual, pct_meta, pct_operacion) VALUES (2, 'Cuenta Secundaria', 50.0, 50.0, 5.0, 3.0)"
    )
    conn.commit()
    conn.close()


init_db()

st.title("📈 Bitácora de Trading - Opciones Binarias")

conn = get_connection()
df_cuentas = pd.read_sql_query("SELECT * FROM cuentas", conn)

# --- BARRA LATERAL: GESTIÓN DE CUENTAS ---
st.sidebar.header("⚙️ Gestión de Cuentas")

cuenta_seleccionada = st.sidebar.selectbox(
    "Selecciona la cuenta activa:", df_cuentas["nombre"]
)

cuenta_info = df_cuentas[df_cuentas["nombre"] == cuenta_seleccionada].iloc[0]
cuenta_id = int(cuenta_info["id"])
saldo_actual = float(cuenta_info["saldo_actual"])
pct_meta = float(cuenta_info["pct_meta"])
pct_operacion = float(cuenta_info["pct_operacion"])

with st.sidebar.expander("➕ Agregar Nueva Cuenta"):
    with st.form("form_nueva_cuenta"):
        nuevo_nombre = st.text_input("Nombre de la cuenta")
        saldo_base_nueva = st.number_input("Saldo Inicial ($)", value=50.0, step=5.0)
        meta_nueva = st.number_input("% Meta por Sesión", value=5.0, step=0.5)
        op_nueva = st.number_input("% Inversión por Operación", value=3.0, step=0.5)
        btn_crear_cuenta = st.form_submit_button("Crear Cuenta")

        if btn_crear_cuenta and nuevo_nombre:
            try:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO cuentas (nombre, saldo_inicial, saldo_actual, pct_meta, pct_operacion)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        nuevo_nombre,
                        saldo_base_nueva,
                        saldo_base_nueva,
                        meta_nueva,
                        op_nueva,
                    ),
                )
                conn.commit()
                st.success(f"¡Cuenta '{nuevo_nombre}' creada con éxito!")
                st.rerun()
            except Exception as e:
                st.error("Ese nombre de cuenta ya existe.")

with st.sidebar.expander("✏️ Editar Cuenta Activa"):
    nuevo_saldo = st.number_input(
        "Ajustar Saldo Actual ($)", value=saldo_actual, step=5.0
    )
    nuevo_pct_meta = st.number_input(
        "% Meta por Sesión", value=pct_meta, step=0.5
    )
    nuevo_pct_op = st.number_input(
        "% Inversión por Operación", value=pct_operacion, step=0.5
    )

    if st.button("Guardar Cambios de Cuenta"):
        c = conn.cursor()
        c.execute(
            """
            UPDATE cuentas 
            SET saldo_actual = ?, pct_meta = ?, pct_operacion = ?
            WHERE id = ?
        """,
            (nuevo_saldo, nuevo_pct_meta, nuevo_pct_op, cuenta_id),
        )
        conn.commit()
        st.sidebar.success("¡Parámetros actualizados!")
        st.rerun()

# --- CÁLCULO DE METAS ---
ganancia_meta_dolares = saldo_actual * (pct_meta / 100.0)
saldo_meta_total = saldo_actual + ganancia_meta_dolares
monto_por_op = saldo_actual * (pct_operacion / 100.0)

st.subheader(f"📊 Panel Activo: {cuenta_seleccionada}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Saldo Actual", f"${saldo_actual:.2f}")
col2.metric(
    f"Meta de Sesión ({pct_meta}%)",
    f"${saldo_meta_total:.2f}",
    delta=f"+${ganancia_meta_dolares:.2f}",
)
col3.metric(f"Inversión por Trade ({pct_operacion}%)", f"${monto_por_op:.2f}")

df_sesiones_actual = pd.read_sql_query(
    f"SELECT * FROM sesiones WHERE cuenta_id = {cuenta_id}", conn
)
sesiones_ganadas_total = len(df_sesiones_actual)
col4.metric("Total Sesiones Registradas", sesiones_ganadas_total)

st.divider()

# --- PESTAÑAS DE NAVEGACIÓN ---
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 Registrar Sesión",
        "📊 Historial y Estadísticas",
        "📈 Proyección de Interés Compuesto",
        "⚙️ Gestionar / Borrar Registros",
    ]
)

with tab1:
    st.subheader("Formulario de Cierre de Sesión")
    st.info(
        f"💡 Tienes un saldo de **${saldo_actual:.2f}**. Para cumplir tu meta del **{pct_meta}%**, tu objetivo es terminar la sesión con **${saldo_meta_total:.2f}** (ganancia neta de **+${ganancia_meta_dolares:.2f}**). Cada operativa sugerida es de **${monto_por_op:.2f}**."
    )

    with st.form("form_sesion"):
        fecha_sesion = st.date_input("Fecha", datetime.date.today())
        cols_form1, cols_form2 = st.columns(2)

        with cols_form1:
            operaciones_ganadas = st.number_input(
                "Operaciones Ganadas (ITM)", min_value=0, value=0, step=1
            )
        with cols_form2:
            operaciones_perdidas = st.number_input(
                "Operaciones Perdidas (OTM)", min_value=0, value=0, step=1
            )

        resultado_neto = st.number_input(
            "Ganancia / Pérdida Neta Final ($)",
            value=0.0,
            step=1.0,
            help="Coloca valor positivo si ganaste o negativo si quedaste en pérdida",
        )

        btn_guardar = st.form_submit_button("💾 Guardar Registro de Sesión")

    if btn_guardar:
        nuevo_saldo_final = saldo_actual + resultado_neto
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO sesiones (cuenta_id, fecha, saldo_inicial, meta_monto, monto_operacion, ganadas, perdidas, resultado_monto, saldo_final)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                cuenta_id,
                str(fecha_sesion),
                saldo_actual,
                ganancia_meta_dolares,
                monto_por_op,
                operaciones_ganadas,
                operaciones_perdidas,
                resultado_neto,
                nuevo_saldo_final,
            ),
        )

        c.execute(
            "UPDATE cuentas SET saldo_actual = ? WHERE id = ?",
            (nuevo_saldo_final, cuenta_id),
        )

        conn.commit()
        st.success(
            f"¡Sesión guardada con éxito! Nuevo saldo de la cuenta: ${nuevo_saldo_final:.2f}"
        )
        st.rerun()

with tab2:
    st.subheader(f"Avance y Estadísticas de {cuenta_seleccionada}")

    df_sesiones = pd.read_sql_query(
        f"SELECT * FROM sesiones WHERE cuenta_id = {cuenta_id} ORDER BY id ASC",
        conn,
    )

    if df_sesiones.empty:
        st.info("Aún no hay sesiones registradas para esta cuenta.")
    else:
        fig_curva = px.line(
            df_sesiones,
            x=df_sesiones.index + 1,
            y="saldo_final",
            markers=True,
            title=f"Curva de Crecimiento - {cuenta_seleccionada}",
            labels={"x": "Número de Sesión", "saldo_final": "Saldo ($)"},
        )
        st.plotly_chart(fig_curva, use_container_width=True)

        total_trades = (
            df_sesiones["ganadas"].sum() + df_sesiones["perdidas"].sum()
        )
        total_itm = df_sesiones["ganadas"].sum()
        winrate = (total_itm / total_trades * 1000) if total_trades > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Sesiones Ejecutadas", len(df_sesiones))
        m2.metric("Total Operaciones", total_trades)
        m3.metric("Win Rate (Efectividad)", f"{winrate:.1f}%")

        st.write("### Tabla de Registros")
        st.dataframe(df_sesiones, use_container_width=True)

with tab3:
    st.subheader(
        f"📈 Proyección Teórica de Interés Compuesto ({cuenta_seleccionada})"
    )
    st.info(
        f"Esta tabla muestra cómo crecería tu capital actual (**${saldo_actual:.2f}**) sesión a sesión si cumples de manera perfecta la meta del **{pct_meta}%** por sesión."
    )

    num_sesiones_proyeccion = st.slider(
        "Número de sesiones a proyectar:", 10, 100, 30
    )

    # Calcular la proyección matemática
    datos_proyeccion = []
    capital_proyectado = saldo_actual
    for i in range(1, num_sesiones_proyeccion + 1):
        saldo_inicial_s = capital_proyectado
        meta_s = saldo_inicial_s * (pct_meta / 100.0)
        saldo_final_s = saldo_inicial_s + meta_s
        datos_proyeccion.append(
            {
                "Sesión": f"Sesión {i}",
                "Saldo Inicial ($)": round(saldo_inicial_s, 2),
                "Meta Ganancia ($)": round(meta_s, 2),
                "Saldo Final Esperado ($)": round(saldo_final_s, 2),
            }
        )
        capital_proyectado = saldo_final_s

    df_proj = pd.DataFrame(datos_proyeccion)
    st.dataframe(df_proj, use_container_width=True)

with tab4:
    st.subheader("⚙️ Eliminar Registro Erróneo")
    st.warning(
        "⚠️ Si te equivocaste en una sesión, puedes seleccionarla y eliminarla aquí."
    )

    df_sesiones_borrar = pd.read_sql_query(
        f"SELECT id, fecha, saldo_inicial, resultado_monto, saldo_final FROM sesiones WHERE cuenta_id = {cuenta_id} ORDER BY id DESC",
        conn,
    )

    if df_sesiones_borrar.empty:
        st.info("No hay registros para eliminar en esta cuenta.")
    else:
        sesion_a_borrar = st.selectbox(
            "Selecciona la sesión que deseas eliminar:",
            df_sesiones_borrar.apply(
                lambda row: f"ID: {row['id']} | Fecha: {row['fecha']} | Resultado: ${row['resultado_monto']}",
                axis=1,
            ),
        )

        if st.button("🗑️ Eliminar Sesión Seleccionada", type="primary"):
            id_extraido = int(
                sesion_a_borrar.split("|")[0].replace("ID:", "").strip()
            )

            c = conn.cursor()
            c.execute("DELETE FROM sesiones WHERE id = ?", (id_extraido,))
            conn.commit()
            st.success(
                f"¡Sesión ID {id_extraido} eliminada correctamente! Recuerda verificar tu saldo actual en la barra lateral."
            )
            st.rerun()

conn.close()
